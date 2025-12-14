-- Chat history table - stores conversations between users and AI
CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    role VARCHAR(20) NOT NULL 
        CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    system_prompt VARCHAR(100),
    tools_used JSONB,
    tool_results JSONB,
    rag_sources JSONB,  -- Document sources retrieved by RAG
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for chat_history table
CREATE INDEX idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_history_created_at ON chat_history(created_at);
CREATE INDEX idx_chat_history_system_prompt ON chat_history(system_prompt);
CREATE INDEX idx_chat_history_role ON chat_history(role);