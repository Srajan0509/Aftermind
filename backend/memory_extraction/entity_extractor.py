"""Helpers for accessing entity mentions from extraction results."""
from .schemas import EntityMention, ExtractedMemory


def collect_entities(memories: list[ExtractedMemory]) -> list[EntityMention]:
    """Return unique entity mentions, preserving first-seen order."""
    output: list[EntityMention] = []
    seen: set[tuple[str, str]] = set()
    for memory in memories:
        for entity in memory.entities:
            key = (entity.entity_type.value, entity.name.casefold())
            if key not in seen:
                seen.add(key)
                output.append(entity)
    return output
