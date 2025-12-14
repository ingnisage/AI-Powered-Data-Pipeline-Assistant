# Search Functionality Implementation

## Overview
This document describes the implementation of the search functionality in the AI Workbench application, which enables searching across multiple knowledge sources including StackOverflow, GitHub, and official documentation, with integration to a vector database for semantic search capabilities.

## Architecture

### Components
1. **Search Clients** - Handle fetching data from external sources
2. **Search Service** - Orchestrates searches across multiple sources and manages the vector database
3. **Vector Service** - Handles embedding generation and database operations
4. **API Routes** - Exposes search functionality via REST endpoints
5. **Frontend Integration** - Provides UI for search functionality

### Data Flow
1. User submits search query through frontend or API
2. Search service routes query to appropriate external sources
3. Results are fetched from external APIs (StackExchange, GitHub, etc.)
4. Documents are converted to standardized format
5. Embeddings are generated using OpenAI API
6. Documents are upserted into Supabase vector database
7. Results are returned to user with metadata

## Implementation Details

### Search Sources
- **StackOverflow**: Uses StackExchange API v2.3 for technical Q&A
- **GitHub**: Searches repositories, code, and issues using GitHub API
- **Official Documentation**: Scrapes documentation sites with fallback to DuckDuckGo
- **Spark Docs**: Specifically targets Apache Spark documentation

### Vector Database Integration
The knowledge base is stored in a Supabase table with pgvector extension:
- **Table**: `knowledge_base`
- **Key Fields**: 
  - `content`: Document content
  - `embedding`: Vector embedding (1536 dimensions)
  - `source_type`: Source identifier (stackoverflow, github, etc.)
  - `source_url`: Original URL
  - `title`: Document title

### API Endpoints
- **POST `/api/search/`**: Main search endpoint
  - Parameters: query, source, max_results
  - Returns: Formatted search results with metadata

### Frontend Integration
- **Search Tab**: Dedicated UI for knowledge searches
- **Source Selection**: Dropdown to filter by source type
- **Results Display**: Expandable cards with source links and content previews

## Usage Examples

### API Usage
```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "python pandas merge",
    "source": "stackoverflow",
    "max_results": 5
  }'
```

### Frontend Usage
1. Navigate to the Search tab
2. Select a source (StackOverflow, GitHub, Spark Docs)
3. Enter a search query
4. Click Search
5. View results with expandable details

## Testing
Several test scripts are available:
- `test_search.py`: Basic search functionality test
- `test_vector_search.py`: Comprehensive test with vector database integration
- `test_api_endpoints.py`: Direct API endpoint testing

## Future Improvements
1. Enhanced caching mechanisms
2. Improved result ranking algorithms
3. Additional source integrations
4. Better error handling and retry logic
5. Advanced filtering and faceting options