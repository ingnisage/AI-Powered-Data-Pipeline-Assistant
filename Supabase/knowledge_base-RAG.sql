-- 知识库表 - 智能缓存的文档向量存储
CREATE TABLE knowledge_base (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE,  -- 内容去重
    embedding VECTOR(1536),           -- pgvector 向量字段
    
    -- 来源信息
    source_type VARCHAR(50) NOT NULL 
        CHECK (source_type IN ('stackoverflow', 'official_doc', 'internal', 'github', 'confluence')),
    source_url VARCHAR(500),
    title VARCHAR(500),
    
    -- 缓存管理
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    first_cached TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,           -- 动态内容过期时间
    
    -- 质量指标
    relevance_score FLOAT DEFAULT 0,
    authority_score FLOAT DEFAULT 0,  -- 来源权威性
    user_feedback_score FLOAT DEFAULT 0,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 知识库表索引（向量搜索优化）
CREATE INDEX idx_kb_embedding ON knowledge_base 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
    
CREATE INDEX idx_kb_source_type ON knowledge_base(source_type);
CREATE INDEX idx_kb_expires_at ON knowledge_base(expires_at);
CREATE INDEX idx_kb_access_count ON knowledge_base(access_count DESC);
CREATE INDEX idx_kb_content_hash ON knowledge_base(content_hash);
CREATE INDEX idx_kb_relevance_score ON knowledge_base(relevance_score DESC);
CREATE INDEX idx_kb_last_accessed ON knowledge_base(last_accessed DESC);