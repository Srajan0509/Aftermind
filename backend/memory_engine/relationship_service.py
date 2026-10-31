import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from .models import Memory, MemoryRelationship, Company, Project, Person, Source
from .schemas import (
    MemoryRelationshipCreate,
    MemoryRelationshipResponse,
    MemoryResponse,
    MemoryStatus,
    RelationshipType
)

logger = logging.getLogger("memory_engine.relationship_service")


class RelationshipService:
    """
    Manages relationships and graph connections between memories, sources, projects, and people.
    Tracks decision evolution, superseding logic, and knowledge associations.
    """

    def create_relationship(
        self,
        db: Session,
        req: MemoryRelationshipCreate
    ) -> MemoryRelationshipResponse:
        """Create an explicit directed relationship between two memories."""
        from_mem = db.query(Memory).filter(Memory.id == req.from_memory_id).first()
        to_mem = db.query(Memory).filter(Memory.id == req.to_memory_id).first()

        if not from_mem or not to_mem:
            raise ValueError("Both from_memory_id and to_memory_id must exist.")

        # Ensure both memories belong to the same company
        if from_mem.company_id != to_mem.company_id:
            raise ValueError("Cross-company relationships are prohibited.")

        rel = MemoryRelationship(
            from_memory_id=req.from_memory_id,
            to_memory_id=req.to_memory_id,
            relationship_type=req.relationship_type.value,
            description=req.description,
            confidence=req.confidence
        )
        db.add(rel)

        # If the relationship is 'supersedes', mark the previous memory as superseded
        if req.relationship_type == RelationshipType.SUPERSEDES:
            to_mem.status = MemoryStatus.SUPERSEDED.value
            from_mem.previous_memory_id = to_mem.id
            if not from_mem.change_reason and req.description:
                from_mem.change_reason = req.description

        db.commit()
        db.refresh(rel)
        return MemoryRelationshipResponse.model_validate(rel)

    def link_superseded_memory(
        self,
        db: Session,
        new_memory: Memory,
        previous_memory_id: str,
        change_reason: Optional[str] = None
    ) -> Optional[MemoryRelationship]:
        """
        Helper called during memory ingestion when previous_memory_id is provided.
        Updates the old memory status to superseded and creates a relationship record.
        """
        prev_mem = db.query(Memory).filter(
            Memory.id == previous_memory_id,
            Memory.company_id == new_memory.company_id
        ).first()

        if not prev_mem:
            logger.warning(f"Previous memory {previous_memory_id} not found for company {new_memory.company_id}")
            return None

        # Mark previous memory as superseded
        prev_mem.status = MemoryStatus.SUPERSEDED.value
        new_memory.previous_memory_id = prev_mem.id
        new_memory.change_reason = change_reason or f"Superseded by new decision in {new_memory.title}"

        rel = MemoryRelationship(
            from_memory_id=new_memory.id,
            to_memory_id=prev_mem.id,
            relationship_type=RelationshipType.SUPERSEDES.value,
            description=change_reason or "Supersedes previous decision/requirement",
            confidence=1.0
        )
        db.add(rel)
        db.commit()
        return rel

    def get_memory_timeline(self, db: Session, memory_id: str) -> List[Memory]:
        """
        Traverse the backward and forward history chain of a memory.
        Returns the full chronological evolution of a decision or commitment.
        """
        mem = db.query(Memory).filter(Memory.id == memory_id).first()
        if not mem:
            return []

        company_id = mem.company_id

        # 1. Walk backwards along previous_memory_id
        ancestors = []
        curr = mem
        visited = {curr.id}
        while curr.previous_memory_id:
            parent = db.query(Memory).filter(
                Memory.id == curr.previous_memory_id,
                Memory.company_id == company_id
            ).first()
            if not parent or parent.id in visited:
                break
            visited.add(parent.id)
            ancestors.append(parent)
            curr = parent

        ancestors.reverse()  # Oldest first

        # 2. Walk forwards along superseded_by
        descendants = []
        curr = mem
        while True:
            child = db.query(Memory).filter(
                Memory.previous_memory_id == curr.id,
                Memory.company_id == company_id
            ).first()
            if not child or child.id in visited:
                break
            visited.add(child.id)
            descendants.append(child)
            curr = child

        return ancestors + [mem] + descendants

    def get_memory_relationships(
        self,
        db: Session,
        memory_id: str
    ) -> List[MemoryRelationshipResponse]:
        """Fetch all relationships originating from or pointing to this memory."""
        rels = db.query(MemoryRelationship).filter(
            (MemoryRelationship.from_memory_id == memory_id) |
            (MemoryRelationship.to_memory_id == memory_id)
        ).all()
        return [MemoryRelationshipResponse.model_validate(r) for r in rels]


relationship_service = RelationshipService()
