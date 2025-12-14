-- 日志表 - 系统运行日志和审计
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL 
        CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    source VARCHAR(100) DEFAULT 'system',
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    component VARCHAR(100),
    duration_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 日志表索引
CREATE INDEX idx_logs_time ON logs(time DESC);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_source ON logs(source);
CREATE INDEX idx_logs_component ON logs(component);
CREATE INDEX idx_logs_session_id ON logs(session_id);
CREATE INDEX idx_logs_user_id ON logs(user_id);