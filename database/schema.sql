-- Enterprise Document Intelligence Platform - Database Schema
-- PostgreSQL 14+

-- Enable required-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "vector";  -- Not needed, using ChromaDB for vectors  -- pgvector for embeddings (optional if using external vector DB)

-- Documents table: stores main document metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100),
    
    -- Document classification
    document_type VARCHAR(100),  -- contract, sop, official_document, report, etc.
    
    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_date TIMESTAMP WITH TIME ZONE,
    
    -- Extracted metadata (JSON format)
    doc_metadata JSONB,  -- {title, date, parties, amounts, effective_date, summary, sections, etc.}
    
    -- Full text content
    full_text TEXT,
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Indexes
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes for documents table
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_upload_date ON documents(upload_date DESC);
CREATE INDEX idx_documents_metadata ON documents USING GIN(doc_metadata);
CREATE INDEX idx_documents_full_text ON documents USING GIN(to_tsvector('english', full_text));

-- Chunks table: stores text chunks for RAG
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    
    -- Embedding vector (if using pgvector)
    -- embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    
    -- Chunk metadata
    chunk_metadata JSONB,  -- {page_number, section, position, etc.}
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_document_chunk UNIQUE(document_id, chunk_index)
);

-- Indexes for chunks table
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON chunks(chunk_index);
-- CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops);  -- if using pgvector

-- Extraction templates: configurable schemas for different document types
CREATE TABLE extraction_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(200) NOT NULL UNIQUE,
    document_type VARCHAR(100) NOT NULL,
    
    -- JSON schema for extraction
    schema JSONB NOT NULL,  -- {fields: [{name, type, description, required}]}
    
    -- LLM prompt template
    system_prompt TEXT,
    user_prompt_template TEXT,
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,  -- higher priority templates are tried first
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- Indexes for extraction_templates
CREATE INDEX idx_extraction_templates_document_type ON extraction_templates(document_type);
CREATE INDEX idx_extraction_templates_active ON extraction_templates(is_active);

-- Query logs: track user queries and system responses
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Query details
    query_text TEXT NOT NULL,
    query_embedding_id VARCHAR(200),  -- reference to vector DB if needed
    
    -- Search parameters
    top_k INTEGER DEFAULT 4,
    filters JSONB,  -- {document_type, date_range, etc.}
    
    -- Results
    retrieved_chunks JSONB,  -- [{document_id, chunk_id, score}]
    answer_text TEXT,
    sources JSONB,  -- [{document_id, chunk_index, text, score}]
    
    -- Performance metrics
    retrieval_time_ms INTEGER,
    llm_time_ms INTEGER,
    total_time_ms INTEGER,
    
    -- User info
    user_id VARCHAR(100),
    session_id VARCHAR(200),
    
    -- Feedback
    user_rating INTEGER,  -- 1-5 stars
    user_feedback TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query_logs
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);

-- Processing jobs: track background processing tasks
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,  -- document_upload, batch_process, reindex, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'queued',  -- queued, running, completed, failed
    
    -- Job details
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    
    -- Progress tracking
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_job_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

-- Indexes for processing_jobs
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at DESC);

-- System configuration table
CREATE TABLE system_config (
    key VARCHAR(200) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Insert default configuration
INSERT INTO system_config (key, value, description) VALUES
('chunk_size', '1000', 'Default chunk size for text splitting'),
('chunk_overlap', '200', 'Overlap between chunks in characters'),
('max_file_size_mb', '50', 'Maximum file size for upload in MB'),
('supported_formats', '["pdf", "docx", "txt", "doc"]', 'Supported document formats'),
('default_top_k', '4', 'Default number of chunks to retrieve for RAG'),
('llm_model', '"gpt-4o-mini"', 'Default LLM model for extraction and QA'),
('embedding_model', '"text-embedding-3-small"', 'Default embedding model');

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extraction_templates_updated_at BEFORE UPDATE ON extraction_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries

-- Active documents summary
CREATE VIEW v_documents_summary AS
SELECT 
    document_type,
    status,
    COUNT(*) as count,
    SUM(file_size_bytes) as total_size_bytes,
    AVG(file_size_bytes) as avg_size_bytes,
    MAX(upload_date) as latest_upload
FROM documents
GROUP BY document_type, status;

-- Recent queries with performance
CREATE VIEW v_recent_queries AS
SELECT 
    id,
    query_text,
    answer_text,
    total_time_ms,
    user_rating,
    created_at
FROM query_logs
ORDER BY created_at DESC
LIMIT 100;

-- Document processing statistics
CREATE VIEW v_processing_stats AS
SELECT 
    DATE(upload_date) as date,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (processed_date - upload_date))) as avg_processing_time_seconds
FROM documents
WHERE upload_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(upload_date), status
ORDER BY date DESC;
