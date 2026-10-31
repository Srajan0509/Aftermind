"""Orchestration and validation for business-memory extraction."""
from typing import Any

from pydantic import ValidationError

from .config import settings
from .llm_client import LLMClient, LLMConfigurationError, LLMResponseError
from .schemas import (
    EntityMention, ExtractionRequest, ExtractionResponse, ExtractedMemory,
)


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
            raw = self.llm_client.generate_json(
                request.extracted_text, request.filename, request.source_type
            )
            if not isinstance(raw, dict):
                raise ExtractionError("LLM response must be a JSON object.")
            raw_memories = raw.get("memories", [])
            raw_entities = raw.get("entities", [])
            if not isinstance(raw_memories, list) or not isinstance(raw_entities, list):
                raise ExtractionError("LLM response 'memories' and 'entities' must be arrays.")

            memories = [ExtractedMemory.model_validate(item) for item in raw_memories]
            entities = [EntityMention.model_validate(item) for item in raw_entities]

            # Retain entities in each relevant memory's metadata and output top-level entities.
            known = {(e.entity_type.value, e.name.casefold()) for e in entities}
            for memory in memories:
                for entity in memory.entities:
                    key = (entity.entity_type.value, entity.name.casefold())
                    if key not in known:
                        entities.append(entity)
                        known.add(key)

            return ExtractionResponse(
                company_id=request.company_id,
                source_id=request.source_id,
                memories=memories,
                entities=entities,
                memories_count=len(memories),
                module3_payloads=[
                    memory.to_memory_create_payload(request) for memory in memories
                ],
            )
        except (ValidationError, LLMConfigurationError, LLMResponseError) as exc:
            raise ExtractionError(str(exc)) from exc


memory_extractor = MemoryExtractor()
