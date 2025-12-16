# AI-Powered Data Pipeline Assistant

This project is an AI-powered assistant designed to help data engineers and analysts troubleshoot and optimize their data pipelines. It provides intelligent assistance for common issues like Spark job failures, memory errors, performance bottlenecks, and more.

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
7. [Detailed Documentation](#detailed-documentation)
8. [Testing](#testing)
9. [Contributing](#contributing)
10. [License](#license)

## Project Overview

The AI-Powered Data Pipeline Assistant is a comprehensive tool that combines AI assistance with real-time monitoring and troubleshooting capabilities for data pipelines. It leverages OpenAI's GPT models, Supabase for data storage, and PubNub for real-time communication.

## Features

- **AI-Powered Assistance**: Get intelligent help for data pipeline issues
- **Real-Time Monitoring**: Monitor pipeline execution and performance
- **Task Management**: Track and manage data pipeline tasks
- **Log Analysis**: Analyze logs to identify issues and patterns
- **Search Functionality**: Search across knowledge bases for solutions
  - StackOverflow and GitHub: Real API integrations
  - Official Documentation and Spark Docs: Placeholder implementations (see note below)
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

## Detailed Documentation

For comprehensive documentation on all aspects of the project, please refer to the [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) file, which contains:

- Authentication System Improvements
- Search Functionality Implementation
- Rate Limiting Modules
- Monitoring Modules
- Fixes Summary
- And much more...

## Testing

The project includes a comprehensive test suite to verify functionality. Tests are located in the `tests/` directory.

### Running Tests

```bash
# Run all tests
python tests/run_tests.py

# Run specific test file
python tests/test_auth.py

# Run tests with unittest
python -m unittest discover tests
```

See [tests/README.md](tests/README.md) for more detailed information about running and writing tests.

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

## Packaging for Submission

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