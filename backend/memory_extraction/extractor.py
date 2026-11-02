"""Orchestration and validation for business-memory extraction."""
import logging
from typing import Any

from pydantic import ValidationError

from .config import settings
from .llm_client import LLMClient, LLMConfigurationError, LLMResponseError
from .schemas import (
    EntityMention, ExtractionRequest, ExtractionResponse, ExtractedMemory,
)

logger = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    pass


class MemoryExtractor:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client or LLMClient()

    def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        if len(request.extracted_text) > settings.max_input_characters:
            raise ExtractionError(
                f"Input exceeds the maximum of {settings.max_input_characters} characters."
            )
        try:
            try:
                raw = self.llm_client.generate_json(
                    request.extracted_text, request.filename, request.source_type
                )
            except (LLMConfigurationError, LLMResponseError) as exc:
                logger.info("LLM generation unconfigured or failed (%s); using heuristic extraction.", exc)
                raw = self._heuristic_extract(request.extracted_text, request.filename, request.source_type)
            except Exception as exc:
                logger.warning("Unexpected error in LLM generation (%s); trying heuristic extraction.", exc)
                try:
                    raw = self._heuristic_extract(request.extracted_text, request.filename, request.source_type)
                except Exception:
                    raise ExtractionError(str(exc)) from exc

            if not isinstance(raw, dict):
                raise ExtractionError("LLM response must be a JSON object.")
            raw_memories = raw.get("memories", [])
            raw_entities = raw.get("entities", [])
            if not isinstance(raw_memories, list) or not isinstance(raw_entities, list):
                raise ExtractionError("LLM response 'memories' and 'entities' must be arrays.")

            memories: list[ExtractedMemory] = []
            for item in raw_memories:
                # Skip None, empty strings, empty dicts, and non-dict/non-str types
                if not item:
                    continue
                if isinstance(item, str) and not item.strip():
                    continue
                if not isinstance(item, (str, dict)):
                    logger.warning("Skipping unexpected memory item type %r: %s", type(item).__name__, item)
                    continue
                try:
                    memories.append(ExtractedMemory.model_validate(item))
                except ValidationError as exc:
                    raise ExtractionError(str(exc)) from exc
                except Exception as exc:
                    logger.warning("Skipping malformed memory item %r: %s", item, exc)

            entities: list[EntityMention] = []
            for item in raw_entities:
                # Skip None, empty strings, empty dicts, and non-dict/non-str types
                if not item:
                    continue
                if isinstance(item, str) and not item.strip():
                    continue
                if not isinstance(item, (str, dict)):
                    logger.warning("Skipping unexpected entity item type %r: %s", type(item).__name__, item)
                    continue
                try:
                    entities.append(EntityMention.model_validate(item))
                except Exception as exc:
                    logger.warning("Skipping malformed entity item %r: %s", item, exc)

            # Retain entities in each relevant memory's metadata and output top-level entities.
            known = {(e.entity_type.value, e.name.casefold()) for e in entities}
            for memory in memories:
                for entity in memory.entities:
                    key = (entity.entity_type.value, entity.name.casefold())
                    if key not in known:
                        entities.append(entity)
                        known.add(key)

            raw_summary = raw.get("source_summary") or raw.get("summary")
            if raw_summary and isinstance(raw_summary, str) and raw_summary.strip():
                source_summary = raw_summary.strip()
            elif memories:
                types = list(dict.fromkeys(m.memory_type.value.replace("_", " ") for m in memories))
                source_summary = f"Identified {len(memories)} business items ({', '.join(types[:3])})."
            else:
                source_summary = f"Extracted {len(memories)} business memories from source."

            return ExtractionResponse(
                company_id=request.company_id,
                source_id=request.source_id,
                memories=memories,
                entities=entities,
                memories_count=len(memories),
                source_summary=source_summary,
                module3_payloads=[
                    memory.to_memory_create_payload(request) for memory in memories
                ],
            )
        except (ValidationError, LLMConfigurationError, LLMResponseError) as exc:
            raise ExtractionError(str(exc)) from exc


    def _heuristic_extract(
        self, text: str, filename: str | None = None, source_type: str | None = None
    ) -> dict[str, Any]:
        """Deterministic heuristic extraction fallback for structured documents, notes, and transcripts."""
        import re
        from .schemas import MemoryType, EntityType

        memories: list[dict[str, Any]] = []
        entities: list[dict[str, Any]] = []

        # 1. Attendees extraction
        att_m = re.search(r"Attendees:\s*([^\n]+)", text, re.IGNORECASE)
        if att_m:
            for att in re.split(r"[,;]", att_m.group(1)):
                clean_name = re.sub(r"\(.*?\)", "", att).strip()
                if clean_name and len(clean_name) > 2:
                    entities.append({"name": clean_name, "entity_type": EntityType.PERSON.value})

        # 2. Organization extraction
        org_m = re.search(r"Organization:\s*([^\n\(]+)", text, re.IGNORECASE)
        if org_m:
            org_name = org_m.group(1).strip()
            if org_name:
                entities.append({"name": org_name, "entity_type": EntityType.ORGANIZATION.value})

        known_people = [e["name"] for e in entities if e.get("entity_type") == EntityType.PERSON.value]

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        current_section = "General"

        for line in lines:
            # Header check
            sec_m = re.match(r"^(\d+[\.\)]|[A-Z\s]{3,}:)\s*(.+)$", line)
            if sec_m and len(line) < 80:
                current_section = line.strip()
                continue

            # Skip metadata headers
            if re.match(r"^(Date|Attendees|Organization|Title):\s*", line, re.IGNORECASE):
                continue

            clean_item = re.sub(r"^([-\*•\d\.]+|\(\d+\))\s*", "", line).strip()
            if len(clean_item) < 15:
                continue

            sec_lower = current_section.lower()
            item_lower = clean_item.lower()

            # Classify memory type
            if any(w in sec_lower for w in ["summary", "overview", "adjournment", "next steps"]):
                m_type = MemoryType.MEETING_DISCUSSION.value
            elif any(w in sec_lower for w in ["decision", "architectural", "approved"]) or any(w in item_lower for w in ["decided", "decision", "approved mandating", "agreed on"]):
                m_type = MemoryType.DECISION.value
            elif any(w in sec_lower for w in ["requirement", "client requirement"]) or any(w in item_lower for w in ["requires", "requirement", "must support", "must be strictly enforced"]):
                m_type = MemoryType.CLIENT_REQUIREMENT.value
            elif any(w in sec_lower for w in ["commitment", "action item", "assigned"]) or any(w in item_lower for w in ["committed to", "commitment", "will deliver", "assigned to", "responsible for"]):
                m_type = MemoryType.EMPLOYEE_COMMITMENT.value
            elif "deadline" in sec_lower or "deadline" in item_lower:
                m_type = MemoryType.IMPORTANT_DEADLINE.value
            else:
                m_type = MemoryType.GENERAL_INFO.value

            colon_m = re.match(r"^([^:]{4,75}):\s*(.+)$", clean_item)
            if colon_m:
                title = colon_m.group(1).strip()
                content = colon_m.group(2).strip()
            else:
                title = clean_item[:60]
                content = clean_item

            person = None
            assignee_m = re.search(r"\(Assignee:\s*([^,\)]+)", clean_item, re.IGNORECASE)
            if assignee_m:
                person = assignee_m.group(1).strip()
            else:
                for p_name in known_people:
                    first_name = p_name.split()[0].lower()
                    if first_name in item_lower or p_name.lower() in item_lower:
                        person = p_name
                        break

            deadline = None
            by_m = re.search(r"(?:by|due|starting in)\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s+\d{4})?|Q\d\s+\d{4}|\d{4}-\d{2}-\d{2})", clean_item, re.IGNORECASE)
            if by_m:
                deadline = by_m.group(1).strip()

            tags = []
            if m_type == MemoryType.DECISION.value:
                tags.append("decision")
            elif m_type == MemoryType.EMPLOYEE_COMMITMENT.value:
                tags.append("commitment")
            elif m_type == MemoryType.CLIENT_REQUIREMENT.value:
                tags.append("requirement")

            for tech in ["postgresql", "pgvector", "supabase", "okta", "gemini", "groq", "whisper", "aes-256", "soc-2"]:
                if tech in item_lower:
                    tags.append(tech)

            memories.append({
                "memory_type": m_type,
                "title": title,
                "content": content,
                "person": person,
                "deadline": deadline,
                "confidence": 0.95,
                "tags": tags,
                "entities": [{"name": person, "entity_type": EntityType.PERSON.value}] if person else [],
                "meta_info": {
                    "section": current_section,
                    "assignee": person,
                    "deadline": deadline
                }
            })

        if not memories and text.strip():
            memories.append({
                "memory_type": MemoryType.GENERAL_INFO.value,
                "title": text[:60].strip(),
                "content": text.strip(),
                "confidence": 0.85,
                "tags": ["general"],
                "entities": [],
                "meta_info": {}
            })

        source_summary = f"Extracted {len(memories)} business memories from source text."

        return {
            "memories": memories,
            "entities": entities,
            "source_summary": source_summary
        }


memory_extractor = MemoryExtractor()
