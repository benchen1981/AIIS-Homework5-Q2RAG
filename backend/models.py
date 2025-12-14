"""
SQLAlchemy ORM models
"""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from database import Base


class Document(Base):
    """Document metadata table"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100))
    
    # Document classification
    document_type = Column(String(100))
    
    # Processing status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending"
    )
    upload_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_date = Column(TIMESTAMP(timezone=True))
    
    # Extracted metadata
    doc_metadata = Column(JSONB)
    full_text = Column(Text)
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0, server_default="0")
    
    # Audit fields
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100))
    
    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="valid_status"
        ),
    )


class Chunk(Base):
    """Text chunks for RAG"""
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    
    # Chunk metadata
    chunk_metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class ExtractionTemplate(Base):
    """Configurable extraction schemas"""
    __tablename__ = "extraction_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(200), nullable=False, unique=True)
    document_type = Column(String(100), nullable=False)
    
    # JSON schema for extraction
    schema = Column(JSONB, nullable=False)
    
    # LLM prompt templates
    system_prompt = Column(Text)
    user_prompt_template = Column(Text)
    
    # Configuration
    is_active = Column(Boolean, default=True, server_default="true")
    priority = Column(Integer, default=0, server_default="0")
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100))


class QueryLog(Base):
    """Track user queries and responses"""
    __tablename__ = "query_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_embedding_id = Column(String(200))
    
    # Search parameters
    top_k = Column(Integer, default=4)
    filters = Column(JSONB)
    
    # Results
    retrieved_chunks = Column(JSONB)
    answer_text = Column(Text)
    sources = Column(JSONB)
    
    # Performance metrics
    retrieval_time_ms = Column(Integer)
    llm_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    
    # User info
    user_id = Column(String(100))
    session_id = Column(String(200))
    
    # Feedback
    user_rating = Column(Integer)
    user_feedback = Column(Text)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ProcessingJob(Base):
    """Track background processing tasks"""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="queued", server_default="queued")
    
    # Job details
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    error_message = Column(Text)
    
    # Progress tracking
    total_items = Column(Integer)
    processed_items = Column(Integer, default=0, server_default="0")
    failed_items = Column(Integer, default=0, server_default="0")
    
    # Timing
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="valid_job_status"
        ),
    )


class SystemConfig(Base):
    """System configuration key-value store"""
    __tablename__ = "system_config"
    
    key = Column(String(200), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100))
