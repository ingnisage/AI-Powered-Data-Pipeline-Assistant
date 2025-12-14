-- Tool executions table - auditing and analysis of AI tool invocations
CREATE TABLE tool_executions (
    id BIGSERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    execution_time_ms INTEGER,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for tool_executions table
CREATE INDEX idx_tool_executions_tool_name ON tool_executions(tool_name);
CREATE INDEX idx_tool_executions_created_at ON tool_executions(created_at DESC);
CREATE INDEX idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX idx_tool_executions_user_id ON tool_executions(user_id);
CREATE INDEX idx_tool_executions_success ON tool_executions(success);