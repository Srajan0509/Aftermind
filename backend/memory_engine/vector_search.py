import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

from .models import Memory, Source, Project, Company, is_postgres
from .schemas import MemoryResponse, SearchResultItem
from .embedding_service import embedding_service

logger = logging.getLogger("memory_engine.vector_search")


import re

def normalize_query_text(query: str) -> str:
    """Normalize common business query typos and terminology."""
    q = query.lower()
    typos = {
        r"\bdedsion\b": "decision",
        r"\bdesicion\b": "decision",
        r"\bdecison\b": "decision",
        r"\bdecisons\b": "decisions",
        r"\bdedsions\b": "decisions",
        r"\bcomitment\b": "commitment",
        r"\bcomittment\b": "commitment",
        r"\bcommitmnt\b": "commitment",
        r"\bcomitments\b": "commitments",
        r"\bdeadine\b": "deadline",
        r"\bdeadlnes\b": "deadlines",
        r"\brequirment\b": "requirement",
        r"\brequirments\b": "requirements",
        r"\barchitecure\b": "architecture",
        r"\bpostgres\b": "postgresql",
    }
    for pat, rep in typos.items():
        q = re.sub(pat, rep, q)
    return q


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
        norm_query = normalize_query_text(query)
        # Generate query vector with normalized query
        query_vector = embedding_service.generate_embedding(norm_query)

        if is_postgres:
            return self._search_postgres(
                db=db,
                query_vector=query_vector,
                company_id=company_id,
                project_id=project_id,
                memory_type=memory_type,
                status=status,
                limit=limit,
                min_similarity=min_similarity,
                raw_query=norm_query
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
                min_similarity=min_similarity,
                raw_query=norm_query
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
        min_similarity: float,
        raw_query: str = ""
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

            norm_q = (raw_query or "").lower()
            detected_type = memory_type
            if not detected_type:
                if "decision" in norm_q:
                    detected_type = "decision"
                elif "commitment" in norm_q or "assignee" in norm_q:
                    detected_type = "employee_commitment"
                elif "requirement" in norm_q:
                    detected_type = "client_requirement"
                elif "deadline" in norm_q:
                    detected_type = "important_deadline"

            stop_words = {"give", "info", "related", "with", "from", "what", "show", "tell", "about", "have", "you", "does", "latest", "recent", "this", "that", "there", "the", "and"}
            query_tokens = [w for w in re.findall(r"\w+", norm_q) if len(w) > 2 and w not in stop_words]

            scored_pg_items = []
            for row in results:
                similarity = float(row.similarity) if row.similarity is not None else 0.0

                type_bonus = 0.0
                if detected_type and (row.memory_type == detected_type or detected_type in (row.title or "").lower()):
                    type_bonus = 0.35

                keyword_bonus = 0.0
                row_text = f"{row.title or ''} {row.content or ''}".lower()
                for tok in query_tokens:
                    if tok in (row.title or "").lower():
                        keyword_bonus += 0.20
                    elif tok in row_text:
                        keyword_bonus += 0.10
                keyword_bonus = min(0.40, keyword_bonus)

                combined_score = similarity + type_bonus + keyword_bonus

                if combined_score < min_similarity and not (type_bonus > 0 and combined_score >= 0.05) and not (keyword_bonus >= 0.20 and combined_score >= 0.05):
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
                scored_pg_items.append((
                    combined_score,
                    SearchResultItem(
                        memory=mem_resp,
                        similarity_score=round(combined_score, 4),
                        source_reference={
                            "source_id": row.source_id,
                            "source_title": row.source_title,
                            "source_type": row.source_type
                        }
                    )
                ))

            if "latest" in norm_q or "recent" in norm_q:
                scored_pg_items.sort(key=lambda x: (x[0], str(x[1].memory.created_at or "")), reverse=True)
            else:
                scored_pg_items.sort(key=lambda x: x[0], reverse=True)

            return [item[1] for item in scored_pg_items[:limit]]
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
        min_similarity: float,
        raw_query: str = ""
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

                # Hybrid type and keyword matching
                norm_q = (raw_query or "").lower()
                detected_type = memory_type
                if not detected_type:
                    if "decision" in norm_q:
                        detected_type = "decision"
                    elif "commitment" in norm_q or "assignee" in norm_q:
                        detected_type = "employee_commitment"
                    elif "requirement" in norm_q:
                        detected_type = "client_requirement"
                    elif "deadline" in norm_q:
                        detected_type = "important_deadline"

                type_bonus = 0.0
                if detected_type and (mem.memory_type == detected_type or detected_type in (mem.title or "").lower()):
                    type_bonus = 0.35

                keyword_bonus = 0.0
                stop_words = {"give", "info", "related", "with", "from", "what", "show", "tell", "about", "have", "you", "does", "latest", "recent", "this", "that", "there", "the", "and"}
                query_tokens = [w for w in re.findall(r"\w+", norm_q) if len(w) > 2 and w not in stop_words]
                mem_text = f"{mem.title or ''} {mem.content or ''}".lower()
                for tok in query_tokens:
                    if tok in (mem.title or "").lower():
                        keyword_bonus += 0.20
                    elif tok in mem_text:
                        keyword_bonus += 0.10
                keyword_bonus = min(0.40, keyword_bonus)

                combined_score = similarity + type_bonus + keyword_bonus

                if combined_score >= min_similarity or (type_bonus > 0 and combined_score >= 0.05) or (keyword_bonus >= 0.20 and combined_score >= 0.05):
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

                    scored_items.append((combined_score, mem_resp, {
                        "source_id": mem.source_id,
                        "source_title": source_title,
                        "source_type": source_type
                    }))

            # Sort descending by combined_score, with recency boost if latest requested
            if "latest" in (raw_query or "").lower() or "recent" in (raw_query or "").lower():
                scored_items.sort(key=lambda x: (x[0], str(x[1].created_at or "")), reverse=True)
            else:
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
