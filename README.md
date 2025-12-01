🚀 AI-Powered Data Pipeline Assistant
Hybrid RAG + Agents for Modern Data Engineering Workflows
📌 Overview

AI-Powered Data Pipeline Assistant is an intelligent debugging and automation system designed for data engineers.
It analyzes logs, SQL queries, Airflow DAGs, Spark jobs, and pipeline configs — and provides root-cause analysis, fix suggestions, and auto-generated remediation steps.

Built with a Hybrid RAG architecture, the system combines:

✅ Static curated knowledge stored in Supabase (pgvector)
✅ Dynamic per-request vectors stored locally in FAISS (in-memory)
✅ On-demand retrieval from official docs, StackOverflow, and internal repos
✅ Agents that execute real tools (SQL validator, config checker, DAG parser, log analyzer)

This makes the assistant far more powerful than a normal chatbot.

🧠 Key Features
🔍 1. Intelligent Data Pipeline Debugging

Upload logs, SQL, config files, or DAGs — the system identifies the problem and proposes actionable fixes.

🔄 2. Hybrid RAG Retrieval

Fast vector search from curated knowledge in Supabase

Dynamic vector search via FAISS (session temporary store)

Fresh data from official docs & StackOverflow

🤖 3. Agent-Based Automation

Tools include:

SQL Analysis Tool

Data Schema Comparator

Airflow DAG Linter

Spark Job Troubleshooter

Log Pattern Analyzer

Pipeline Health Reporter

📚 4. Lightweight Knowledge Base

Short curated chunks:

Airflow errors

Spark exceptions

Common ETL design patterns

SQL tuning tips

Cloud warehouse best practices (Snowflake/BigQuery)

Minimal size → minimal cost.

📦 5. Real-Time Streaming Responses

PubNub + Streamlit for a responsive UI.

🏗️ System Architecture
🔷 High-Level Diagram (Hybrid RAG)
flowchart TB

    %% Users & Frontend
    U[User] --> S[Streamlit Frontend]
    S --> |HTTP Requests| F[FastAPI Backend]

    %% AI Core Services
    F --> O[OpenAI API]
    F --> AG[Agent Orchestrator]

    %% RAG Engine
    AG --> R[RAG Engine]

    %% External Data Sources
    R --> SO[StackOverflow API]
    R --> OD[Official Docs Fetcher]
    R --> ID[Internal Repos]

    %% Real-time Communication
    F --> P[PubNub WebSocket]
    P --> S

    %% Database Layer
    subgraph "Supabase Database"
        T[tasks]
        CH[chat_history] 
        L[logs]
        TE[tool_executions]

        subgraph "Persistent KB (pgvector)"
            KB[knowledge_base]
        end
    end

    subgraph "Local In-Memory Vector Store"
        KB_TMP[FAISS Temporary Vectors<br/>- session scoped<br/>- auto-cleans]
    end

    %% Backend writes/reads DB
    F --> T
    F --> CH
    F --> L
    F --> TE

    %% Hybrid RAG flow
    R --> KB
    KB --> |Static Vector Search| R
    R --> KB_TMP
    KB_TMP --> |Dynamic Vector Search| R

    %% Styling
    classDef frontend fill:#d9f1ff
    classDef backend fill:#efe1ff
    classDef database fill:#e7ffe7
    classDef external fill:#fff4db
    classDef temp fill:#ffe7e7

    class U,S frontend
    class F,AG,R,P backend
    class T,CH,L,TE,KB temp
    class KB database
    class KB_TMP temp
    class SO,OD,ID external

🔍 How Hybrid RAG Works
1. Static Retrieval (Supabase pgvector)

Stores curated, stable chunks

Small & cheap to maintain

Fast pgvector search

Used for:

Common ETL fixes

SQL tuning patterns

Known Airflow/Spark error patterns

2. Dynamic Retrieval (FAISS In-Memory)

Used when user uploads:

Logs

DAG files

SQL scripts

Config YAML

Error messages

Or when the system fetches:

StackOverflow answers

Official docs

Internal repos

➡️ FAISS stores vectors only for the session
➡️ Cleared after task ends
➡️ Zero cost, ultra-fast search

🗄️ Database Schema (Supabase)
1. knowledge_base (pgvector)

Minimal curated chunks.

2. kb_temp (session-level FAISS)

Not stored in DB, kept in memory.

3. tasks

Tracks long-running jobs.

4. chat_history

Maintains conversation context.

5. tool_executions

Every agent call is logged:

tool used

input

output

latency

6. logs

System + user logs for debugging.

🧪 Hallucination Mitigation / Evaluation

Your evaluator module will cover:

1. Source Score Evaluation

"Is answer backed by KB?"

Scores from 0–1

< 0.6 triggers re-query

2. Consistency Check

LLM answers twice with different seeds → compare embeddings.

3. Tool-grounded verification

If answer is about:

SQL → validate with PostgreSQL

DAG → parse AST

Logs → regex error pattern matching

4. RAG Contrastive Evaluation

Ask LLM:

“Which chunk(s) from retrieval support the answer?”

Compare with actual retrieval list

5. Refusal Logic

If retrieval confidence is low → respond:

“I don’t have enough information. Please upload logs or DAG files.”

🧩 User Interface
Streamlit Screens:

Chat Interface

upload logs/sql/dag/config

select pipeline type (Airflow/Spark/dbt)

Debug Panel
Shows:

retrieved docs

agent tool calls

SQL validation output

DAG dependency graph

Pipeline Report
Auto-generated:

root cause summary

severity

recommended fixes

validation steps

Knowledge Base Inspector
Shows chunks from Supabase + temp FAISS vectors.

⚙️ Project Structure
ai-pipeline-assistant/
│
├── backend/
│   ├── main.py (FastAPI)
│   ├── rag_engine/
│   │   ├── static_retriever.py
│   │   ├── dynamic_retriever.py
│   │   ├── hybrid_rag.py
│   │   └── chunking/
│   ├── agents/
│   │   ├── sql_checker.py
│   │   ├── dag_linter.py
│   │   ├── log_analyzer.py
│   │   └── report_generator.py
│   ├── vectorstores/
│   │   ├── supabase_pgvector.py
│   │   └── faiss_temp_store.py
│   ├── db/
│   │   ├── supabase_client.py
│   │   └── queries.sql
│   └── eval/
│       ├── consistency_test.py
│       ├── source_score.py
│       └── tool_validation.py
│
├── frontend/
│   ├── app.py (Streamlit)
│   ├── components/
│   └── styles/
│
├── docs/
│   ├── architecture.md
│   ├── diagrams/
│   └── evaluations.md
│
├── scripts/
│   ├── ingest_docs.py
│   ├── scrape_stackoverflow.py
│   └── populate_kb.py
│
└── README.md

🚀 Running Locally
1. Start backend
cd backend
uvicorn main:app --reload

2. Start Streamlit UI
cd frontend
streamlit run app.py

📦 Deployment Options
Option A: Render (Free)

Frontend: Streamlit

Backend: FastAPI

Supabase: hosted

Option B: Docker + Railway

One-click PaaS

WebSocket support

Option C: Local Demo

FAISS + Supabase

Perfect for your bootcamp capstone demo

🛣️ Future Enhancements
🔥 1. Automatic pipeline repair

Let agent automatically create a PR with:

DAG fixes

SQL fixes

Config fixes

📊 2. Pipeline Observability Dashboard

Metrics from Airflow/Spark → LLM analysis.

🧩 3. Plugin Marketplace

Add new tools:

dbt model checker

Kafka lag analyzer

Data Quality profiler

🤝 4. Collaboration Mode

Multiple users share same session & temp vector DB.

🎯 Why This Project Is Unique

Most LLM debugging tools are simple chatbots.
Your system is not. It performs:

real tool execution

hybrid dynamic/static retrieval

live scraping of real sources

deep integration with data engineering workflows

full evaluation suite to reduce hallucinations

enterprise-style architecture

This is a capstone worthy of a Senior Data Engineer or ML Engineer.