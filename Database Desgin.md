-- 首先启用 vector 扩展（Supabase 中需要）
CREATE EXTENSION IF NOT EXISTS vector;

User → Streamlit UI → FastAPI  
                   ↓  
             Guardrails  
                   ↓  
           Agent / Orchestrator  
                   ↓  
           Redis Queue (async)  
         ↙         ↓         ↘  
 Embed Worker   Tool Worker   Log Worker  
      ↓            ↓             ↓  
 Vector DB ← KB Metadata → Supabase  
 
 External Docs → Ingestion Pipeline → Vector DB