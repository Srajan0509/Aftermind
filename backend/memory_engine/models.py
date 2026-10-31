import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base, engine

# Check for PostgreSQL vs SQLite
is_postgres = "postgresql" in str(engine.url)

if is_postgres:
    try:
        from pgvector.sqlalchemy import Vector
        VectorType = Vector(1536)
    except ImportError:
        VectorType = JSON
else:
    VectorType = JSON


class Company(Base):
    """Client or organization tenant in AFTERMIND."""
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    people = relationship("Person", back_populates="company", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="company", cascade="all, delete-orphan")


class Project(Base):
    """Project entity associated with a company."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="projects")
    sources = relationship("Source", back_populates="project")
    memories = relationship("Memory", back_populates="project")


class Person(Base):
    """Individual person (employee, client contact, stakeholder) in AFTERMIND."""
    __tablename__ = "people"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    role = Column(String(100), nullable=True)  # e.g., 'Product Manager', 'Client Lead'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="people")
    authored_sources = relationship("Source", back_populates="author")
    authored_memories = relationship("Memory", back_populates="author")


class Source(Base):
    """
    Original source of business information (meeting recording, conversation, voice note, or document).
    Preserves raw content for complete source traceability.
    """
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(String(36), ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)  # meeting, voice_note, document, email, chat
    raw_content = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=True)
    meta_info = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    company = relationship("Company", back_populates="sources")
    project = relationship("Project", back_populates="sources")
    author = relationship("Person", back_populates="authored_sources")
    memories = relationship("Memory", back_populates="source", cascade="all, delete-orphan")


class Memory(Base):
    """
    Atomic business memory (decision, requirement, commitment, deadline, discussion item).
    Features pgvector embeddings, version history, and source traceability.
    """
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("people.id", ondelete="SET NULL"), nullable=True)

    # Memory classification
    # 'decision', 'client_requirement', 'employee_commitment', 'important_deadline', 'meeting_discussion', 'general_info'
    memory_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    # Status tracking for decisions and commitments: 'active', 'superseded', 'modified', 'completed', 'cancelled'
    status = Column(String(50), default="active", index=True)
    confidence = Column(Float, default=0.95)

    # Decision History & Evolution
    previous_memory_id = Column(String(36), ForeignKey("memories.id", ondelete="SET NULL"), nullable=True, index=True)
    change_reason = Column(Text, nullable=True)

    tags = Column(JSON, nullable=True, default=list)
    meta_info = Column(JSON, nullable=True, default=dict)
    
    # Vector embedding for semantic search
    embedding = Column(VectorType, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="memories")
    project = relationship("Project", back_populates="memories")
    source = relationship("Source", back_populates="memories")
    author = relationship("Person", back_populates="authored_memories")
    
    # Self-referential relationship for memory history
    previous_memory = relationship("Memory", remote_side=[id], backref="superseded_by")

    # Directed relationships to other memories
    relationships_from = relationship(
        "MemoryRelationship",
        foreign_keys="MemoryRelationship.from_memory_id",
        back_populates="from_memory",
        cascade="all, delete-orphan"
    )
    relationships_to = relationship(
        "MemoryRelationship",
        foreign_keys="MemoryRelationship.to_memory_id",
        back_populates="to_memory",
        cascade="all, delete-orphan"
    )


class MemoryRelationship(Base):
    """
    Connects memories in a knowledge graph (e.g., supersedes, relates_to, depends_on, updates).
    """
    __tablename__ = "memory_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_memory_id = Column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    to_memory_id = Column(String(36), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationship types: 'supersedes', 'updates', 'contradicts', 'depends_on', 'relates_to', 'derived_from'
    relationship_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    from_memory = relationship("Memory", foreign_keys=[from_memory_id], back_populates="relationships_from")
    to_memory = relationship("Memory", foreign_keys=[to_memory_id], back_populates="relationships_to")
