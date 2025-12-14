-- Check whether all tables were created successfully
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('tasks', 'chat_history', 'logs', 'tool_executions', 'knowledge_base');

-- Initialize mock task data
INSERT INTO tasks (name, status, progress, priority, description) VALUES
('Data Preprocessing', 'Completed', 100, 'High', 'Clean and prepare dataset for model training'),
('Model Training', 'In Progress', 65, 'High', 'Train machine learning model on prepared data'),
('Model Evaluation', 'Pending', 0, 'Medium', 'Evaluate model performance and metrics'),
('Feature Engineering', 'In Progress', 45, 'Medium', 'Create new features from existing data'),
('Data Validation', 'Pending', 0, 'High', 'Validate data quality and integrity');

-- Initialize mock log data
INSERT INTO logs (time, level, message, source, component) VALUES
(NOW() - INTERVAL '1 hour', 'INFO', 'AI Workbench system started successfully', 'system', 'startup'),
(NOW() - INTERVAL '55 minute', 'INFO', 'Connected to OpenAI API', 'system', 'api'),
(NOW() - INTERVAL '50 minute', 'INFO', 'Supabase database connection established', 'system', 'database'),
(NOW() - INTERVAL '45 minute', 'WARNING', 'High memory usage detected', 'system', 'monitoring'),
(NOW() - INTERVAL '30 minute', 'INFO', 'User session started: user_123', 'auth', 'session'),
(NOW() - INTERVAL '25 minute', 'INFO', 'Data preprocessing task completed', 'task', 'execution'),
(NOW() - INTERVAL '20 minute', 'ERROR', 'Failed to connect to external API: timeout', 'api', 'external'),
(NOW() - INTERVAL '15 minute', 'INFO', 'Model training initiated for project X', 'ml', 'training'),
(NOW() - INTERVAL '10 minute', 'INFO', 'RAG knowledge base initialized', 'rag', 'setup'),
(NOW() - INTERVAL '5 minute', 'INFO', 'Tool execution: query_data_source completed', 'tools', 'execution');


