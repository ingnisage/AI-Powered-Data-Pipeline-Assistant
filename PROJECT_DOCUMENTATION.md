# AI-Powered Data Pipeline Assistant - Project Documentation

This document consolidates all the important documentation for the AI-Powered Data Pipeline Assistant project.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Configuration](#configuration)
   - [Running the Application](#running-the-application)
5. [Usage](#usage)
6. [API Documentation](#api-documentation)
7. [Authentication System](#authentication-system)
8. [Search Functionality](#search-functionality)
9. [Rate Limiting](#rate-limiting)
10. [Monitoring](#monitoring)
11. [Fixes Summary](#fixes-summary)
12. [Deployment](#deployment)
13. [Contributing](#contributing)
14. [License](#license)

---

## Project Overview

The AI-Powered Data Pipeline Assistant is a comprehensive tool that combines AI assistance with real-time monitoring and troubleshooting capabilities for data pipelines. It leverages OpenAI's GPT models, Supabase for data storage, and PubNub for real-time communication.

## Features

- **AI-Powered Assistance**: Get intelligent help for data pipeline issues
- **Real-Time Monitoring**: Monitor pipeline execution and performance
- **Task Management**: Track and manage data pipeline tasks
- **Log Analysis**: Analyze logs to identify issues and patterns
- **Search Functionality**: Search across knowledge bases for solutions
  - StackOverflow and GitHub: Real API integrations
  - Official Documentation and Spark Docs: Placeholder implementations
- **Responsive Web Interface**: User-friendly Streamlit interface

## Architecture

The system follows a modular architecture with the following components:

- **Frontend**: Streamlit-based web interface
- **Backend**: FastAPI-based REST API
- **Database**: Supabase for data storage
- **AI Engine**: OpenAI GPT models for intelligent assistance
- **Real-Time Communication**: PubNub for live updates

## Getting Started

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- OpenAI API key
- Supabase account and credentials
- PubNub account and credentials

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ai-powered-data-pipeline-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Set the following environment variables:

- `ENVIRONMENT`: Set to "development" for local testing (allows requests without API key), or "production" for strict authentication
- `BACKEND_API_KEY`: Authentication key for backend access (required in production)
- `OPENAI_API_KEY`: OpenAI API key for AI assistance
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase project key
- `PUBNUB_PUBLISH_KEY`: PubNub publish key
- `PUBNUB_SUBSCRIBE_KEY`: PubNub subscribe key

### Supabase Setup

To use the vector search functionality, you need to:

1. Enable the pgvector extension in your Supabase project
2. Run the SQL scripts in the `Supabase/` directory to create the necessary tables and functions:
   - `knowledge_base-RAG.sql`: Creates the knowledge base table with vector support and RPC functions
   - `tasks.sql`: Creates the tasks table
   - `chat_history.sql`: Creates the chat history table
   - Other SQL files for additional features

The vector search functionality requires:
- pgvector extension enabled
- A `knowledge_base` table with a `VECTOR(1536)` column for embeddings
- RPC functions for vector similarity search

### Running the Application

#### Local Development (Easy Testing Mode)
For local development, the system automatically enables a development mode that allows requests without an API key:

1. Start the backend server:
   ```bash
   ENVIRONMENT=development OPENAI_API_KEY=your-openai-key python main.py
   ```

2. In a separate terminal, start the frontend:
   ```bash
   ENVIRONMENT=development streamlit run app/app.py
   ```

#### Production Mode (Strict Authentication)
For production deployment, you must provide a valid API key:

1. Start the backend server:
   ```bash
   ENVIRONMENT=production BACKEND_API_KEY=your-api-key OPENAI_API_KEY=your-openai-key python main.py
   ```

2. In a separate terminal, start the frontend:
   ```bash
   ENVIRONMENT=production BACKEND_API_KEY=your-api-key streamlit run app/app.py
   ```

3. Access the application at `http://localhost:8501`

## Usage

1. Navigate to the web interface
2. Use the chat functionality to ask questions about data pipeline issues
3. View and manage tasks in the task board
4. Monitor logs for real-time insights
5. Search knowledge bases for solutions to common problems

## API Documentation

The backend provides a REST API with the following endpoints:

- `/chat/` - Chat with the AI assistant
- `/tasks/` - Manage tasks
- `/logs/` - Access log data
- `/search/` - Search knowledge bases

Detailed API documentation is available when the backend server is running at `/docs`.

## Authentication System

### Problem Statement
The original authentication system was too strict for local development, requiring a valid `BACKEND_API_KEY` even during development. This made it difficult for developers to test the application locally without setting up proper environment variables.

### Solution
The improved authentication system introduces an environment-based approach that automatically adapts to the current environment:

1. **Development Mode**: Relaxed authentication that allows requests without API keys
2. **Production Mode**: Strict authentication that requires valid API keys

### Changes Made

1. **Security Manager Enhancement** (`backend/auth/security.py`):
   - Added support for detecting the environment mode via `ENVIRONMENT` environment variable
   - In development mode, automatically creates a default API key for testing
   - In development mode, allows requests without API keys
   - Maintains strict authentication in production mode

2. **Environment Configuration** (`.env.example`):
   - Added `ENVIRONMENT` variable with default value of "development"
   - Updated documentation to explain the purpose of this variable

3. **Streamlit App Updates** (`app/app.py`):
   - Added environment detection in the frontend
   - Automatically uses appropriate API key handling based on environment
   - Provides better user feedback about authentication status

### How to Use

#### Local Development (Easy Testing)
1. Set environment variable:
   ```bash
   export ENVIRONMENT=development
   ```

2. Run backend:
   ```bash
   ENVIRONMENT=development OPENAI_API_KEY=your-openai-key python main.py
   ```

3. Run frontend:
   ```bash
   ENVIRONMENT=development streamlit run app/app.py
   ```

In this mode, the application will:
- Allow requests without API keys
- Automatically use a default development API key
- Provide a smooth development experience

#### Production Deployment (Strict Security)
1. Set environment variables:
   ```bash
   export ENVIRONMENT=production
   export BACKEND_API_KEY=your-secure-api-key
   ```

2. Run backend:
   ```bash
   ENVIRONMENT=production BACKEND_API_KEY=your-api-key OPENAI_API_KEY=your-openai-key python main.py
   ```

3. Run frontend:
   ```bash
   ENVIRONMENT=production BACKEND_API_KEY=your-api-key streamlit run app/app.py
   ```

In this mode, the application will:
- Require valid API keys for all requests
- Reject requests without proper authentication
- Maintain enterprise-grade security

## Search Functionality

### Overview
This document describes the implementation of the search functionality in the AI Workbench application, which enables searching across multiple knowledge sources including StackOverflow, GitHub, and official documentation, with integration to a vector database for semantic search capabilities.

### Architecture

#### Components
1. **Search Clients** - Handle fetching data from external sources
2. **Search Service** - Orchestrates searches across multiple sources and manages the vector database
3. **Vector Service** - Handles embedding generation and database operations
4. **API Routes** - Exposes search functionality via REST endpoints
5. **Frontend Integration** - Provides UI for search functionality

#### Data Flow
1. User submits search query through frontend or API
2. Search service routes query to appropriate external sources
3. Results are fetched from external APIs (StackExchange, GitHub, etc.)
4. Documents are converted to standardized format
5. Embeddings are generated using OpenAI API
6. Documents are upserted into Supabase vector database
7. Results are returned to user with metadata

### Implementation Details

#### Search Sources
- **StackOverflow**: Uses StackExchange API v2.3 for technical Q&A
- **GitHub**: Searches repositories, code, and issues using GitHub API
- **Official Documentation**: Scrapes documentation sites with fallback to DuckDuckGo
- **Spark Docs**: Specifically targets Apache Spark documentation

#### Vector Database Integration
The knowledge base is stored in a Supabase table with pgvector extension:
- **Table**: `knowledge_base`
- **Key Fields**: 
  - `content`: Document content
  - `embedding`: Vector embedding (1536 dimensions)
  - `source_type`: Source identifier (stackoverflow, github, etc.)
  - `source_url`: Original URL
  - `title`: Document title

#### API Endpoints
- **POST `/search/`**: Main search endpoint
  - Parameters: query, source, max_results
  - Returns: Formatted search results with metadata

#### Frontend Integration
- **Search Tab**: Dedicated UI for knowledge searches
- **Source Selection**: Dropdown to filter by source type
- **Results Display**: Expandable cards with source links and content previews

## Rate Limiting

### Module Overview

#### 1. `backend/auth/mcp_rate_limiter.py` - MCP-Specific Rate Limiting
**Purpose**: Rate limiting for MCP tools to prevent resource exhaustion.
**Features**:
- Tool-specific rate limits
- Configurable limits per tool
- Per-identifier tracking (IP, session, etc.)

**Used by**:
- Main MCP server (`backend/mcp/mcp_server.py`)

#### 2. `backend/auth/fallback_rate_limiter.py` - Fallback MCP Rate Limiting
**Purpose**: Rate limiter for fallback MCP server with no external dependencies.
**Features**:
- Same functionality as MCP rate limiter but designed for fallback scenarios
- No external dependencies
- Resilient implementation for fallback situations

**Used by**:
- Fallback MCP server (`backend/mcp/mcp_server_fallback.py`)

#### 3. `backend/core/guardrails.py` - Guardrails Rate Limiter
**Purpose**: Simple rate limiter as part of guardrails for chat API protection.
**Features**:
- Integrated with PII detection
- Simple in-memory rate limiting
- Designed specifically for chat API protection

**Used by**:
- Chat API route (`backend/api/routes/chat.py`)

### Usage Guidelines
1. **For MCP tool rate limiting**: Use `backend/auth/mcp_rate_limiter.py` (main server) or `backend/auth/fallback_rate_limiter.py` (fallback server)
2. **For chat API protection**: Use the rate limiter in `backend/core/guardrails.py`

## Monitoring

### Module Overview

#### 1. `backend/core/monitoring.py` - MCP Server Monitoring
**Purpose**: Simple monitoring for tracking MCP server usage.
**Features**:
- Counters for requests to main vs fallback servers
- Tool-specific counters
- Status counters (success, error, rate_limited, etc.)

**Used by**:
- Main MCP server (`backend/mcp/mcp_server.py`)
- Fallback MCP server (`backend/mcp/mcp_server_fallback.py`)
- Monitoring API endpoint (`backend/api/routes/monitoring.py`)

#### 2. `backend/core/performance_monitoring.py` - General Performance Monitoring
**Purpose**: General performance monitoring utilities.
**Features**:
- Operation metrics collection
- Performance counters
- Context managers for monitoring operations
- Function decorators for automatic monitoring

**Used by**:
- Services that need to track operation performance
- Components that require detailed timing information

#### 3. `backend/services/monitoring.py` - Service-Level Monitoring
**Purpose**: Service-specific monitoring with enhanced features like Supabase logging.
**Features**:
- Wrapper around general performance monitoring with service-specific enhancements
- Integration with Supabase for persistent logging
- Health check utilities

**Used by**:
- Chat processor (`backend/services/chat_processor.py`)
- PubNub job processor (`backend/services/pubnub_job_processor.py`)

#### 4. `backend/api/routes/monitoring.py` - Monitoring API Endpoint
**Purpose**: Exposes MCP statistics via API endpoints.
**Features**:
- GET endpoint for retrieving MCP statistics
- POST endpoint for resetting MCP statistics

**Used by**:
- API routing system

## Fixes Summary

This document summarizes all the fixes implemented to address the feedback provided.

### 1. MCP Parameter Mismatch Fix
**Issue**: MCP servers were passing the wrong parameter to SearchAdapter (source vs context)

**Files Modified**:
- `backend/mcp/mcp_server.py`
- `backend/mcp/mcp_server_fallback.py`

**Changes Made**:
- Changed `context=validated_args.source` to `source=validated_args.source` in both MCP servers
- This ensures that tools requesting a specific source will get results from that source, not "all" sources

### 2. InMemoryCache Thread Safety
**Issue**: InMemoryCache claimed to be thread-safe but had no locking mechanisms

**Files Modified**:
- `backend/utils/caching.py`

**Changes Made**:
- Added `threading.RLock()` for thread safety
- Wrapped all cache operations (get, set, delete, clear, cleanup_expired, get_stats) with the lock
- Ensured atomic operations in multi-threaded environments

### 3. OfficialDocsClient Cleanup
**Issue**: OfficialDocsClient had unused helper methods

**Files Modified**:
- `backend/services/search_clients.py`

**Changes Made**:
- Removed unused `_post_with_retry` and `_fetch_snippet_async` methods
- Simplified the class to only include the essential `search` method
- Maintained the placeholder functionality for documentation purposes

### 4. Global Logging Sanitization
**Issue**: Logging sanitization was not globally applied

**Files Modified**:
- `main.py`

**Changes Made**:
- Added code to wrap all existing logging handlers with `SanitizingHandler`
- This ensures consistent redaction of sensitive data across all log messages
- Applied sanitization at the root logger level for comprehensive coverage

### 5. Security Consistency
**Issue**: `/logs/` endpoint was protected by API key, but `/chat/chat-history` was not

**Files Modified**:
- `backend/api/routes/chat.py`

**Changes Made**:
- Added `dependencies=[Depends(verify_api_key_dependency)]` to the `/chat-history` endpoint
- This ensures consistent security protection across all endpoints

### 6. Enhanced Tenacity Retry Logic
**Issue**: Retry logic only covered HTTPStatusError but not network timeouts

**Files Modified**:
- `backend/services/search_clients.py`

**Changes Made**:
- Extended retry conditions to include `httpx.ReadTimeout`, `httpx.ConnectError`, and `httpx.NetworkError`
- This makes the retry mechanism more robust against various network issues

### 7. Vector Upsert Return Shape Improvement
**Issue**: Vector upsert returned results derived from input rows, not Supabase response

**Files Modified**:
- `backend/services/vector_service.py`

**Changes Made**:
- Modified the return value to include data from Supabase's response when available
- Added `id` and `content_hash` fields from the database response
- Maintained backward compatibility with fallback to input-derived results

### 8. Model Names Consistency
**Issue**: Different model names were used in different places ("gpt-4o-mini" and "gpt-4")

**Files Modified**:
- `backend/services/chat_processor.py`
- `backend/services/pubnub_job_processor.py`
- `backend/tools/data_tools.py`

**Changes Made**:
- Centralized model selection using `config.DEFAULT_MODEL` and `config.FALLBACK_MODEL`
- Replaced hardcoded model names with configuration references
- This ensures consistent model usage and easier switching in the future

## Deployment

### Local Development

1. Start the backend server:
   ```bash
   BACKEND_API_KEY=your-api-key OPENAI_API_KEY=your-openai-key python main.py
   ```

2. In a separate terminal, start the frontend:
   ```bash
   BACKEND_API_KEY=your-api-key streamlit run app/app.py
   ```

3. Access the application at `http://localhost:8501`

### Production Deployment (Render)

When deploying to Render or other cloud platforms:

1. Set the following environment variables:
   - `ENVIRONMENT` - Set to "production" for strict authentication
   - `BACKEND_API_KEY` - Your backend API key
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `RENDER_BACKEND_URL` or `BACKEND_URL` - Your production backend URL (e.g., `https://your-backend-service.onrender.com`)

2. The frontend will automatically connect to your production backend when these environment variables are set.

### Packaging for Submission

To create a clean package for submission that excludes the virtual environment and other unnecessary files:

1. Run the packaging script:
   ```bash
   ./package_for_submission.sh
   ```

2. This will create a `capstone_submission.zip` file in the parent directory that contains only the essential project files.

This approach ensures that large binary files from the virtual environment (like `_rust.abi3.so`, `_pydantic_core.cpython-311-darwin.so`, etc.) are not included in your submission.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Search Functionality Note

The search functionality includes both real API integrations and placeholder implementations:

- **StackOverflow and GitHub**: These sources use real APIs (StackExchange API and GitHub API) to fetch actual content.
- **Official Documentation and Spark Docs**: These sources currently return placeholder results with unique URLs. In a production environment, these would be replaced with actual documentation search APIs or web scrapers.

To implement real documentation search, you would need to:
1. Replace the placeholder logic in `backend/services/search_clients.py` in the `OfficialDocsClient` class
2. Add proper API integrations or web scraping logic
3. Update the source type handling in the search service