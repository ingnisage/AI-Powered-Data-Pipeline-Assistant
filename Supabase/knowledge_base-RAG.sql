-- Knowledge base table - intelligent cached document vector store
CREATE TABLE knowledge_base (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE,  -- Content de-duplication
    embedding VECTOR(1536),           -- pgvector vector field
    
    -- Source information
    source_type VARCHAR(50) NOT NULL 
        CHECK (source_type IN ('stackoverflow', 'official_doc', 'internal', 'github', 'confluence', 'spark_docs')),
    source_url VARCHAR(500),
    title VARCHAR(500),
    
    -- Cache management
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    first_cached TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,           -- Expiration time for dynamic content
    
    -- Quality metrics
    relevance_score FLOAT DEFAULT 0,
    authority_score FLOAT DEFAULT 0,  -- Source authority
    user_feedback_score FLOAT DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for knowledge_base table (optimized for vector search)
CREATE INDEX idx_kb_embedding ON knowledge_base 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
    
CREATE INDEX idx_kb_source_type ON knowledge_base(source_type);
CREATE INDEX idx_kb_expires_at ON knowledge_base(expires_at);
CREATE INDEX idx_kb_access_count ON knowledge_base(access_count DESC);
CREATE INDEX idx_kb_content_hash ON knowledge_base(content_hash);
CREATE INDEX idx_kb_relevance_score ON knowledge_base(relevance_score DESC);
CREATE INDEX idx_kb_last_accessed ON knowledge_base(last_accessed DESC);

-- RPC function for general document matching using vector similarity
CREATE OR REPLACE FUNCTION match_documents(query_embedding vector(1536), match_count int, filter_source text DEFAULT NULL)
RETURNS TABLE(
    id bigint,
    content text,
    content_hash varchar(64),
    source_type varchar(50),
    source_url varchar(500),
    title varchar(500),
    similarity float
)
LANGUAGE sql
AS $$
    SELECT
        knowledge_base.id,
        knowledge_base.content,
        knowledge_base.content_hash,
        knowledge_base.source_type,
        knowledge_base.source_url,
        knowledge_base.title,
        (knowledge_base.embedding <=> query_embedding) AS similarity
    FROM knowledge_base
    WHERE (filter_source IS NULL OR knowledge_base.source_type = filter_source)
    ORDER BY knowledge_base.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- RPC function for document matching by document type (used by PubNub job processor)
CREATE OR REPLACE FUNCTION match_documents_by_document_type(query_embedding vector(1536), match_count int, query_document_type text)
RETURNS TABLE(
    id bigint,
    content text,
    content_hash varchar(64),
    source_type varchar(50),
    source_url varchar(500),
    title varchar(500),
    similarity float
)
LANGUAGE sql
AS $$
    SELECT
        knowledge_base.id,
        knowledge_base.content,
        knowledge_base.content_hash,
        knowledge_base.source_type,
        knowledge_base.source_url,
        knowledge_base.title,
        (knowledge_base.embedding <=> query_embedding) AS similarity
    FROM knowledge_base
    WHERE knowledge_base.source_type = query_document_type
    ORDER BY knowledge_base.embedding <=> query_embedding
    LIMIT match_count;
$$;