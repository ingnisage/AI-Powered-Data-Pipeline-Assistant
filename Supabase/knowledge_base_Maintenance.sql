-- 知识库维护函数：清理过期内容
CREATE OR REPLACE FUNCTION cleanup_expired_knowledge()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM knowledge_base 
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 更新访问统计的函数
CREATE OR REPLACE FUNCTION increment_access_count(kb_id BIGINT)
RETURNS VOID AS $$
BEGIN
    UPDATE knowledge_base 
    SET access_count = access_count + 1, last_accessed = NOW()
    WHERE id = kb_id;
END;
$$ LANGUAGE plpgsql;