-- Tasks table - manage tasks in the AI workbench
CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Not Started' 
        CHECK (status IN ('Not Started', 'In Progress', 'Completed', 'Failed')),
    progress INTEGER NOT NULL DEFAULT 0 
        CHECK (progress >= 0 AND progress <= 100),
    assigned_to VARCHAR(255),
    priority VARCHAR(20) DEFAULT 'Medium' 
        CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    description TEXT,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for tasks table
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_progress ON tasks(progress);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);

-- Trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();