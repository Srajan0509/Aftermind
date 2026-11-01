"""Commitment-focused view over the shared extraction engine."""
from .schemas import ExtractedMemory, MemoryType


def extract_commitments(memories: list[ExtractedMemory]) -> list[ExtractedMemory]:
    return [
        item for item in memories
        if item.memory_type == MemoryType.EMPLOYEE_COMMITMENT
    ]
