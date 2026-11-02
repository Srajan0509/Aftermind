import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import httpx

from .config import memory_config
from .schemas import RAGChatRequest, RAGChatResponse, SourceReference
from .vector_search import vector_search_engine

logger = logging.getLogger("memory_engine.rag_engine")


class RAGEngine:
    """
    Retrieval-Augmented Generation (RAG) engine for business memory queries.
    Retrieves company-isolated memories, constructs grounded context, and answers with source references.
    """

    def __init__(self):
        self.openai_key = memory_config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.gemini_key = memory_config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.groq_key = memory_config.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        self.openrouter_key = memory_config.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        self.llm_provider = memory_config.LLM_PROVIDER

    def answer_question(self, db: Session, req: RAGChatRequest) -> RAGChatResponse:
        """
        Executes end-to-end RAG pipeline:
        1. Semantic Search
        2. Filter out superseded memories if requested
        3. Check availability threshold
        4. Grounded Context Construction
        5. LLM Answer Generation with Source Citations
        """
        question_text = (req.question or req.query or "").strip()
        if not question_text:
            return RAGChatResponse(
                question="",
                answer="Please enter a question about your business memories or commitments.",
                sources=[],
                retrieved_memories_count=0,
                is_grounded=False
            )

        company_id = req.company_id or "default-org"

        # Step 1 & 2: Vector Search scoped to company_id
        search_results = vector_search_engine.search(
            db=db,
            query=question_text,
            company_id=company_id,
            project_id=req.project_id,
            limit=req.limit,
            min_similarity=memory_config.SIMILARITY_THRESHOLD
        )

        if not req.include_superseded:
            search_results = [r for r in search_results if r.memory.status != "superseded"]

        # Step 3: Check sources table fallback if memories table is empty or had no matches
        if not search_results:
            try:
                from .models import Source
                from .vector_search import normalize_query_text
                sources_query = db.query(Source).filter(Source.company_id == company_id).order_by(Source.created_at.desc()).all()
                if sources_query:
                    import re
                    norm_q = normalize_query_text(question_text)
                    stop_words = {"give", "info", "related", "with", "from", "what", "show", "tell", "about", "have", "you", "does", "latest", "recent", "this", "that", "there", "the", "and"}
                    query_tokens = [w for w in re.findall(r"\w+", norm_q) if len(w) > 2 and w not in stop_words]

                    matched_source = None
                    matching_lines = []
                    for src in sources_query:
                        c_low = (src.raw_content or "").lower()
                        t_low = (src.title or "").lower()
                        if any(tok in c_low or tok in t_low for tok in query_tokens) or ("decision" in norm_q and "decision" in c_low):
                            matched_source = src
                            lines = [l.strip() for l in (src.raw_content or "").split("\n") if l.strip()]
                            for l in lines:
                                l_low = l.lower()
                                if any(tok in l_low for tok in query_tokens) or ("decision" in norm_q and any(k in l_low for k in ["decision", "decided", "approved"])):
                                    matching_lines.append(l)
                            if matching_lines:
                                break

                    if matched_source and matching_lines:
                        snippet_text = "\n".join(f"- {ml}" for ml in matching_lines[:5])
                        answer_text = (
                            f"Based on your ingested document '{matched_source.title}':\n\n"
                            f"{snippet_text}\n\n"
                            f"*Note: You can click 'Send to Module 2 (Extraction)' to automatically save these as structured business decisions and commitments for tracking.*"
                        )
                        return RAGChatResponse(
                            question=question_text,
                            answer=answer_text,
                            sources=[SourceReference(
                                source_id=matched_source.id,
                                source_title=matched_source.title,
                                source_type=matched_source.source_type,
                                memory_id=f"src-{matched_source.id}",
                                memory_title=matched_source.title,
                                memory_type="document",
                                content_snippet=snippet_text[:200]
                            )],
                            retrieved_memories_count=len(matching_lines[:5]),
                            is_grounded=True
                        )
            except Exception as src_err:
                logger.warning(f"Fallback source query failed: {src_err}")

            return RAGChatResponse(
                question=question_text,
                answer="I could not find any recorded business memories or discussions regarding this query for your company.",
                sources=[],
                retrieved_memories_count=0,
                is_grounded=False
            )

        # Step 4: Extract source references
        source_refs: List[SourceReference] = []
        context_blocks: List[str] = []

        for idx, res in enumerate(search_results, start=1):
            mem = res.memory
            s_title = mem.source_title or "Unspecified Source"
            s_type = mem.source_type or "document"
            m_type = mem.memory_type or "general_info"

            created_val = mem.created_at
            if hasattr(created_val, "strftime"):
                date_str = created_val.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = str(created_val or "")

            snippet = (mem.content[:200] + ("..." if len(mem.content) > 200 else "")) if mem.content else ""

            source_refs.append(
                SourceReference(
                    source_id=mem.source_id or f"src-{mem.id}",
                    source_title=s_title,
                    source_type=s_type,
                    memory_id=mem.id,
                    memory_title=mem.title,
                    memory_type=m_type,
                    content_snippet=snippet,
                    timestamp=created_val if hasattr(created_val, "strftime") else None
                )
            )

            context_blocks.append(
                f"[Memory {idx}] (ID: {mem.id})\n"
                f"Title: {mem.title}\n"
                f"Type: {m_type.upper()}\n"
                f"Status: {mem.status}\n"
                f"Source: {s_title} ({s_type})\n"
                f"Project: {mem.project_name or 'General'}\n"
                f"Date: {date_str}\n"
                f"Content: {mem.content}\n"
                + (f"Change Reason: {mem.change_reason}\n" if mem.change_reason else "")
            )

        context_str = "\n\n".join(context_blocks)

        # Step 5: Generate LLM answer with fallback
        try:
            answer = self._generate_llm_answer(question=question_text, context=context_str, source_refs=source_refs)
        except Exception as e:
            logger.warning(f"LLM answer generation failed ({e}), using grounded synthesizer fallback.")
            answer = self._synthesize_grounded_answer(question=question_text, context=context_str, source_refs=source_refs)

        return RAGChatResponse(
            question=question_text,
            answer=answer or "No answer could be generated from available records.",
            sources=source_refs,
            retrieved_memories_count=len(search_results),
            is_grounded=True
        )

    def _generate_llm_answer(self, question: str, context: str, source_refs: List[SourceReference]) -> str:
        """Call Gemini or OpenAI, or fall back to structured grounded synthesizer."""
        # 1. Try Gemini
        if (self.llm_provider in ["auto", "gemini"]) and self.gemini_key:
            try:
                system_instruction = (
                    "You are AFTERMIND AI, an intelligent business memory assistant.\n"
                    "Your job is to answer employee and stakeholder questions accurately using ONLY the business memories provided.\n"
                    "Rules:\n"
                    "1. Rely strictly on the facts in the context.\n"
                    "2. Cite your sources in the text (e.g. '[Source: Meeting 1]').\n"
                    "3. If information is missing or unclear, clearly state that it is not found in the records.\n"
                    "4. Be concise, professional, and clear."
                )
                prompt = f"{system_instruction}\n\nBUSINESS MEMORY CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"

                resp = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}")

        # 2. Try OpenAI
        if (self.llm_provider in ["auto", "openai"]) and self.openai_key:
            try:
                resp = httpx.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are AFTERMIND AI. Answer user questions using ONLY the provided business memories. Always cite sources (e.g., [Source: Meeting Title])."
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {question}"
                            }
                        ],
                        "temperature": 0.2
                    },
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.warning(f"OpenAI generation failed: {e}")

        # 3. Try Groq
        if (self.llm_provider in ["auto", "groq"]) and self.groq_key:
            try:
                resp = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_key}"},
                    json={
                        "model": memory_config.GROQ_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are AFTERMIND AI. Answer user questions using ONLY the provided business memories. Always cite sources (e.g., [Source: Meeting Title])."
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {question}"
                            }
                        ],
                        "temperature": 0.2
                    },
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.warning(f"Groq generation failed: {e}")

        # 4. Try OpenRouter
        if (self.llm_provider in ["auto", "openrouter"]) and self.openrouter_key:
            try:
                resp = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "AFTERMIND"
                    },
                    json={
                        "model": memory_config.OPENROUTER_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are AFTERMIND AI. Answer user questions using ONLY the provided business memories. Always cite sources (e.g., [Source: Meeting Title])."
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {question}"
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": 1000
                    },
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.warning(f"OpenRouter generation failed: {e}")

        # 5. Grounded Synthesizer (Fallback when API keys are not yet provided)
        return self._synthesize_grounded_answer(question=question, context=context, source_refs=source_refs)

    def _synthesize_grounded_answer(self, question: str, context: str, source_refs: List[SourceReference]) -> str:
        """
        Deterministic, grounded answer synthesizer.
        Extracts key findings from the retrieved memories and formats them with source citations.
        """
        top_ref = source_refs[0]
        citations = ", ".join(f"'{ref.source_title}'" for ref in source_refs[:3])

        answer_lines = [
            f"Based on the recorded memories from {citations}:",
            f"- **{top_ref.memory_title}** ({top_ref.memory_type.replace('_', ' ').title()}): {top_ref.content_snippet}"
        ]

        if len(source_refs) > 1:
            for ref in source_refs[1:3]:
                answer_lines.append(
                    f"- **{ref.memory_title}** [{ref.source_title}]: {ref.content_snippet}"
                )

        return "\n".join(answer_lines)


rag_engine = RAGEngine()
