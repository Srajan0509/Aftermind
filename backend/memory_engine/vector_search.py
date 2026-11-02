import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

from .models import Memory, Source, Project, Company, is_postgres
from .schemas import MemoryResponse, SearchResultItem
from .embedding_service import embedding_service

logger = logging.getLogger("memory_engine.vector_search")


class VectorSearchEngine:
    """
    Vector similarity search engine supporting PostgreSQL + pgvector and SQLite fallback.
    Enforces strict multi-tenant isolation by requiring company_id on every search.
    """

    def search(
        self,
        db: Session,
        query: str,
        company_id: str,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.30
    ) -> List[SearchResultItem]:
        """
        Execute semantic vector similarity search scoped to a specific company.
        """
        # Generate query vector
        query_vector = embedding_service.generate_embedding(query)

        if is_postgres:
            return self._search_postgres(
                db=db,
                query_vector=query_vector,
                company_id=company_id,
                project_id=project_id,
                memory_type=memory_type,
                status=status,
                limit=limit,
                min_similarity=min_similarity
            )
        else:
            return self._search_in_memory(
                db=db,
                query_vector=query_vector,
                company_id=company_id,
                project_id=project_id,
                memory_type=memory_type,
                status=status,
                limit=limit,
                min_similarity=min_similarity
            )

    def _search_postgres(
        self,
        db: Session,
        query_vector: List[float],
        company_id: str,
        project_id: Optional[str],
        memory_type: Optional[str],
        status: Optional[str],
        limit: int,
        min_similarity: float
    ) -> List[SearchResultItem]:
        """pgvector native cosine distance search."""
        try:
            vector_str = "[" + ",".join(map(str, query_vector)) + "]"
            
            # Construct parameterized pgvector query
            sql = """
                SELECT m.id, m.company_id, m.project_id, m.source_id, m.author_id,
                       m.memory_type, m.title, m.content, m.status, m.confidence,
                       m.previous_memory_id, m.change_reason, m.tags, m.meta_info,
                       m.created_at, m.updated_at,
                       s.title AS source_title, s.source_type,
                       p.name AS project_name, c.name AS company_name,
                       1 - (m.embedding <=> CAST(:query_vector AS vector)) AS similarity
                FROM memories m
                LEFT JOIN sources s ON m.source_id = s.id
                LEFT JOIN companies c ON m.company_id = c.id
                LEFT JOIN projects p ON m.project_id = p.id
                WHERE m.company_id = :company_id
                  AND m.embedding IS NOT NULL
            """
            params: Dict[str, Any] = {
                "query_vector": vector_str,
                "company_id": company_id
            }

            if project_id:
                sql += " AND m.project_id = :project_id"
                params["project_id"] = project_id
            if memory_type:
                sql += " AND m.memory_type = :memory_type"
                params["memory_type"] = memory_type
            if status:
                sql += " AND m.status = :status"
                params["status"] = status

            sql += " ORDER BY similarity DESC LIMIT :limit"
            params["limit"] = limit

            results = db.execute(text(sql), params).fetchall()

            search_items = []
            for row in results:
                similarity = float(row.similarity) if row.similarity is not None else 0.0
                if similarity < min_similarity:
                    continue

                mem_resp = MemoryResponse(
                    id=row.id,
                    company_id=row.company_id,
                    project_id=row.project_id,
                    source_id=row.source_id,
                    author_id=row.author_id,
                    memory_type=row.memory_type,
                    title=row.title,
                    content=row.content,
                    status=row.status,
                    confidence=row.confidence,
                    previous_memory_id=row.previous_memory_id,
                    change_reason=row.change_reason,
                    tags=row.tags or [],
                    meta_info=row.meta_info or {},
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    source_title=row.source_title,
                    source_type=row.source_type,
                    project_name=row.project_name,
                    company_name=row.company_name
                )
                search_items.append(
                    SearchResultItem(
                        memory=mem_resp,
                        similarity_score=round(similarity, 4),
                        source_reference={
                            "source_id": row.source_id,
                            "source_title": row.source_title,
                            "source_type": row.source_type
                        }
                    )
                )
            return search_items
        except Exception as e:
            logger.warning(f"PostgreSQL pgvector search failed ({e}), rolling back and falling back to memory search.")
            try:
                db.rollback()
            except Exception:
                pass
            return self._search_in_memory(
                db=db,
                query_vector=query_vector,
                company_id=company_id,
                project_id=project_id,
                memory_type=memory_type,
                status=status,
                limit=limit,
                min_similarity=min_similarity
            )

    def _search_in_memory(
        self,
        db: Session,
        query_vector: List[float],
        company_id: str,
        project_id: Optional[str],
        memory_type: Optional[str],
        status: Optional[str],
        limit: int,
        min_similarity: float
    ) -> List[SearchResultItem]:
        """In-memory cosine similarity search for SQLite or test environments."""
        try:
            query = db.query(Memory).filter(Memory.company_id == company_id)

            if project_id:
                query = query.filter(Memory.project_id == project_id)
            if memory_type:
                query = query.filter(Memory.memory_type == memory_type)
            if status:
                query = query.filter(Memory.status == status)

            candidates = query.all()
            if not candidates:
                return []

            q_vec = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return []

            import json
            scored_items = []
            for mem in candidates:
                if not mem.embedding:
                    continue

                raw_emb = mem.embedding
                if isinstance(raw_emb, str):
                    try:
                        raw_emb = json.loads(raw_emb)
                    except Exception:
                        continue

                try:
                    mem_vec = np.array(raw_emb, dtype=np.float32)
                except Exception:
                    continue
                m_norm = np.linalg.norm(mem_vec)
                if m_norm == 0:
                    continue

                similarity = float(np.dot(q_vec, mem_vec) / (q_norm * m_norm))

                if similarity >= min_similarity:
                    source_title = mem.source.title if mem.source else None
                    source_type = mem.source.source_type if mem.source else None
                    project_name = mem.project.name if mem.project else None
                    company_name = mem.company.name if mem.company else None

                    mem_resp = MemoryResponse(
                        id=mem.id,
                        company_id=mem.company_id,
                        project_id=mem.project_id,
                        source_id=mem.source_id,
                        author_id=mem.author_id,
                        memory_type=mem.memory_type,
                        title=mem.title,
                        content=mem.content,
                        status=mem.status,
                        confidence=mem.confidence,
                        previous_memory_id=mem.previous_memory_id,
                        change_reason=mem.change_reason,
                        tags=mem.tags or [],
                        meta_info=mem.meta_info or {},
                        created_at=mem.created_at,
                        updated_at=mem.updated_at,
                        source_title=source_title,
                        source_type=source_type,
                        project_name=project_name,
                        company_name=company_name
                    )

                    scored_items.append((similarity, mem_resp, {
                        "source_id": mem.source_id,
                        "source_title": source_title,
                        "source_type": source_type
                    }))

            # Sort descending by similarity
            scored_items.sort(key=lambda x: x[0], reverse=True)
            top_candidates = scored_items[:limit]

            return [
                SearchResultItem(
                    memory=item[1],
                    similarity_score=round(item[0], 4),
                    source_reference=item[2]
                )
                for item in top_candidates
            ]
        except Exception as e:
            logger.warning(f"In-memory search encountered error ({e}); returning empty list.")
            try:
                db.rollback()
            except Exception:
                pass
            return []


vector_search_engine = VectorSearchEngine()
