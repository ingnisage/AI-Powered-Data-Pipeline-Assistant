# backend/services/search_service.py - Search Service
"""
Search service that orchestrates searches across multiple sources and manages 
the vector database for RAG (Retrieval-Augmented Generation).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

# Import the search clients and vector service
from backend.services.search_clients import StackOverflowClient, GitHubClient, OfficialDocsClient, Document
from backend.services.vector_service import VectorStoreService
from backend.utils.query_processing import preprocess_search_query

logger = logging.getLogger(__name__)

class SearchService:
    """Main search service that orchestrates searches across multiple sources."""
    
    def __init__(self, openai_client=None, supabase_client=None):
        """Initialize search service with clients.
        
        Args:
            openai_client: OpenAI client for embeddings
            supabase_client: Supabase client for database operations
        """
        self.so_client = StackOverflowClient()
        self.gh_client = GitHubClient()
        self.docs_client = OfficialDocsClient()
        
        # Initialize vector service for RAG if clients are provided
        if openai_client and supabase_client:
            self.vector_service = VectorStoreService(openai_client, supabase_client)
        else:
            self.vector_service = None
            logger.warning("VectorStoreService is disabled due to missing clients")
    
    async def search_stackoverflow(self, query: str, max_results: int = 5) -> List[Document]:
        """Search StackOverflow for relevant results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Document objects
        """
        try:
            docs = await self.so_client.search(query, max_results)
            logger.info(f"Found {len(docs)} StackOverflow results for query: {query[:50]}...")
            return docs
        except Exception as e:
            logger.error(f"Error searching StackOverflow: {e}")
            return []
    
    async def search_github(self, query: str, max_results: int = 5) -> List[Document]:
        """Search GitHub for relevant results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Document objects
        """
        try:
            docs = await self.gh_client.search(query, max_results)
            logger.info(f"Found {len(docs)} GitHub results for query: {query[:50]}...")
            return docs
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
            return []
    
    async def search_spark_docs(self, query: str, max_results: int = 5) -> List[Document]:
        """Search Apache Spark documentation for relevant results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Document objects
        """
        try:
            # Modify query to specifically target Spark documentation
            spark_query = f"spark {query}"
            docs = await self.docs_client.search(spark_query, max_results)
            logger.info(f"Found {len(docs)} Spark docs results for query: {query[:50]}...")
            return docs
        except Exception as e:
            logger.error(f"Error searching Spark docs: {e}")
            return []
    
    async def search_official_docs(self, query: str, max_results: int = 5) -> List[Document]:
        """Search official documentation for relevant results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Document objects
        """
        try:
            docs = await self.docs_client.search(query, max_results)
            logger.info(f"Found {len(docs)} official docs results for query: {query[:50]}...")
            return docs
        except Exception as e:
            logger.error(f"Error searching official docs: {e}")
            return []
    
    async def smart_search(
        self,
        query: str,
        source: str = "all",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Intelligently search across knowledge sources.
        
        Args:
            query: Search query
            source: Source to search (github, stackoverflow, official_doc, spark_docs, all)
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        # Preprocess query to optimize search effectiveness
        processed_query = preprocess_search_query(query)
        logger.info(f"Performing smart search: '{query[:50]}...' -> '{processed_query[:50]}...' (source: {source})")
        
        # Collect documents from specified sources
        all_docs = []
        
        try:
            if source == "stackoverflow":
                docs = await self.search_stackoverflow(processed_query, max_results)
                all_docs.extend(docs)
            elif source == "github":
                docs = await self.search_github(processed_query, max_results)
                all_docs.extend(docs)
            elif source == "official_doc":
                docs = await self.search_official_docs(processed_query, max_results)
                all_docs.extend(docs)
            elif source == "spark_docs":
                docs = await self.search_spark_docs(processed_query, max_results)
                all_docs.extend(docs)
            elif source == "all":
                # Search all sources concurrently
                tasks = [
                    self.search_stackoverflow(processed_query, max_results),
                    self.search_github(processed_query, max_results),
                    self.search_official_docs(processed_query, max_results)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(f"Search task failed: {result}")
                        continue
                    if isinstance(result, list):
                        all_docs.extend(result)
            else:
                raise ValueError(f"Invalid source: {source}")
            
            # Deduplicate results by URL
            seen_urls = set()
            unique_docs = []
            for doc in all_docs:
                if doc.source_url and doc.source_url not in seen_urls:
                    seen_urls.add(doc.source_url)
                    unique_docs.append(doc)
            
            # Limit to max_results
            unique_docs = unique_docs[:max_results]
            
            # Upsert documents to vector database if vector service is available
            if self.vector_service and unique_docs:
                try:
                    await self.vector_service.upsert_documents_async(unique_docs)
                    logger.info(f"Upserted {len(unique_docs)} documents to vector database")
                except Exception as e:
                    logger.error(f"Error upserting documents to vector database: {e}")
            
            # Format results for response
            formatted_results = []
            for doc in unique_docs:
                formatted_results.append({
                    "title": doc.title,
                    "url": doc.source_url,
                    "source": doc.source_type,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "metadata": doc.metadata
                })
            
            logger.info(f"Smart search completed with {len(formatted_results)} results")
            
            return {
                "results": formatted_results,
                "query": query,
                "processed_query": processed_query,
                "source": source,
                "total_results": len(formatted_results),
                "message": f"Found {len(formatted_results)} results from {source}"
            }
            
        except Exception as e:
            logger.error(f"Error during smart search: {e}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    async def search_by_embedding(
        self,
        query: str,
        source: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Search using vector embeddings in the knowledge base.
        
        Args:
            query: Search query
            source: Optional source filter
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        if not self.vector_service:
            raise HTTPException(status_code=500, detail="Vector service not available")
        
        # Preprocess query to optimize search effectiveness
        processed_query = preprocess_search_query(query)
        
        try:
            # Generate embedding for the processed query
            embeddings = await self.vector_service._generate_embeddings_async([processed_query])
            if not embeddings:
                raise HTTPException(status_code=500, detail="Failed to generate query embedding")
            
            query_embedding = embeddings[0]
            
            # Search in Supabase knowledge base
            self.vector_service._ensure_supabase()
            
            # Build the query
            query_builder = self.vector_service.supabase.table(VectorStoreService.KNOWLEDGE_BASE_TABLE)
            
            # Add source filter if specified
            if source:
                query_builder = query_builder.eq("source_type", source)
            
            # Perform vector similarity search
            # Note: This assumes pgvector extension is installed and configured
            response = query_builder.select("*").limit(max_results).execute()
            
            # Format results
            results = []
            if response.data:
                for item in response.data:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("source_url", ""),
                        "source": item.get("source_type", ""),
                        "content": item.get("content", "")[:500] + "..." if len(item.get("content", "")) > 500 else item.get("content", ""),
                        "similarity_score": item.get("similarity_score", 0)  # This would need to be calculated
                    })
            
            return {
                "results": results,
                "query": query,
                "processed_query": processed_query,
                "source": source,
                "total_results": len(results),
                "message": f"Found {len(results)} results from vector search"
            }
            
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")