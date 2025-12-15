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
8. [Contributing](#contributing)
9. [License](#license)

## Project Overview

The AI-Powered Data Pipeline Assistant is a comprehensive tool that combines AI assistance with real-time monitoring and troubleshooting capabilities for data pipelines. It leverages OpenAI's GPT models, Supabase for data storage, and PubNub for real-time communication.

## Features

- **AI-Powered Assistance**: Get intelligent help for data pipeline issues
- **Real-Time Monitoring**: Monitor pipeline execution and performance
- **Task Management**: Track and manage data pipeline tasks
- **Log Analysis**: Analyze logs to identify issues and patterns
- **Search Functionality**: Search across knowledge bases for solutions
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

- `BACKEND_API_KEY`: Authentication key for backend access
- `OPENAI_API_KEY`: OpenAI API key for AI assistance
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase project key
- `PUBNUB_PUBLISH_KEY`: PubNub publish key
- `PUBNUB_SUBSCRIBE_KEY`: PubNub subscribe key

### Running the Application

1. Start the backend server:
   ```bash
   BACKEND_API_KEY=your-api-key OPENAI_API_KEY=your-openai-key python main.py
   ```

2. In a separate terminal, start the frontend:
   ```bash
   BACKEND_API_KEY=your-api-key streamlit run app/app.py
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

- `/api/chat/` - Chat with the AI assistant
- `/api/tasks/` - Manage tasks
- `/api/logs/` - Access log data
- `/api/search/` - Search knowledge bases

Detailed API documentation is available when the backend server is running at `/docs`.

## Detailed Documentation

For comprehensive documentation on all aspects of the project, please refer to the [CONSOLIDATED_DOCUMENTATION.md](CONSOLIDATED_DOCUMENTATION.md) file, which contains:

- AI Workbench V2 Enhancements
- Architecture Improvements
- Code Quality Improvements
- Performance Improvements
- Security Additions
- And much more...

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
   - `BACKEND_API_KEY` - Your backend API key
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `RENDER_BACKEND_URL` or `BACKEND_URL` - Your production backend URL (e.g., `https://your-backend-service.onrender.com`)

2. The frontend will automatically connect to your production backend when these environment variables are set.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.