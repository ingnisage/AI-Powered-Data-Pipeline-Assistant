# search_service.py

import asyncio
import time
import sys
from typing import List, Dict, Any, Optional
from functools import lru_cache
import nest_asyncio

# Apply nest_asyncio to allow asyncio.run() in nested event loops
try:
    nest_asyncio.apply()
except RuntimeError:
    # Already applied, or running in non-nested context
    pass

# Import refactored components
from backend.services.search_clients import StackOverflowClient, GitHubClient, OfficialDocsClient, Document 
from backend.services.vector_service import VectorStoreService

# Import save_log from backend.utils
try:
    from backend.utils import save_log
except ImportError:
    # Fallback: if running from search module context
    def save_log(level: str, message: str, source: str = "search", component: str = "search_service"):
        print(f"[{level}] {source}/{component}: {message}")

class SearchService:
    """
    Orchestrates searches across multiple sources, manages context detection, 
    and handles caching/upserting via the VectorStoreService.
    """

    def __init__(self, openai_client: Optional[Any] = None, supabase_client: Optional[Any] = None):
        # Clients for I/O and vector operations
        self.so_client = StackOverflowClient()
        self.gh_client = GitHubClient()
        self.docs_client = OfficialDocsClient()
        
        # Service for RAG/Persistence
        if openai_client and supabase_client:
            self.vector_service = VectorStoreService(openai_client, supabase_client)
        else:
            self.vector_service = None
            save_log("WARN", "VectorStoreService is disabled due to missing clients.", source="search_service")

    async def search_stackoverflow_and_cache_async(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Search StackOverflow and upsert results asynchronously."""
        if not self.vector_service:
            msg = "VectorStoreService (OpenAI/Supabase) is not configured"
            save_log("WARN", msg, source="search", component="search_service")
            return {"error": msg, "results": []}
            
        try:
            # Directly await async search client
            docs = await self.so_client.search(query, max_results)
            
            if not docs:
                save_log("INFO", f"No StackOverflow results for query: {query}", source="search", component="search_service")
                return {"results": [], "message": "No StackOverflow results found."}
            
            # Embed and Upsert (RAG/Persistence) asynchronously
            upsert_result = await self.vector_service.upsert_documents_async(docs)
            
            # upsert_result has structure: {"results": [...], "message": "..."}
            # Extract and format as expected by search_smart_async
            formatted_results = []
            for doc in docs:
                formatted_results.append({
                    "title": doc.title,
                    "url": doc.source_url,
                    "score": doc.metadata.get("score", 0),
                })
            
            return {"results": formatted_results, "message": f"Found {len(formatted_results)} StackOverflow results"}
            
        except Exception as e:
            error_msg = f"StackOverflow search/cache failed: {e}"
            save_log("ERROR", error_msg, source="search", component="search_service")
            return {"error": error_msg, "results": []}

    async def search_github_async(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Search GitHub and upsert results asynchronously."""
        if not self.vector_service:
            msg = "VectorStoreService (OpenAI/Supabase) is not configured"
            save_log("WARN", msg, source="search", component="search_service")
            return {"error": msg, "results": []}
            
        try:
            # Directly await async search client
            docs = await self.gh_client.search(query, max_results)
                    
            if not docs:
                save_log("INFO", f"No GitHub results for query: {query}", source="search", component="search_service")
                return {"results": [], "message": "No GitHub results found."}
            
            # Embed and Upsert (RAG/Persistence) asynchronously
            upsert_result = await self.vector_service.upsert_documents_async(docs)
            
            # Extract and format as expected by search_smart_async
            formatted_results = []
            for doc in docs:
                formatted_results.append({
                    "title": doc.title,
                    "url": doc.source_url,
                    "score": doc.metadata.get("score", 0),
                })
            
            return {"results": formatted_results, "message": f"Found {len(formatted_results)} GitHub results"}
        except Exception as e:
            error_msg = f"GitHub search/cache failed: {e}"
            save_log("ERROR", error_msg, source="search", component="search_service")
            return {"error": error_msg, "results": []}

    async def search_official_docs_async(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Search Official Docs and upsert results asynchronously."""
        if not self.vector_service:
            msg = "VectorStoreService (OpenAI/Supabase) is not configured"
            save_log("WARN", msg, source="search", component="search_service")
            return {"error": msg, "results": []}

        try:
            # Directly await async search client
            docs = await self.docs_client.search(query, max_results)
                    
            if not docs:
                save_log("INFO", f"No official docs results for query: {query}", source="search", component="search_service")
                return {"results": [], "message": "No official docs found."}
            
            # Embed and Upsert (RAG/Persistence) asynchronously
            upsert_result = await self.vector_service.upsert_documents_async(docs)
            
            # Extract and format as expected by search_smart_async
            formatted_results = []
            for doc in docs:
                formatted_results.append({
                    "title": doc.title,
                    "url": doc.source_url,
                    "score": doc.metadata.get("score", 0),
                })
            
            return {"results": formatted_results, "message": f"Found {len(formatted_results)} official docs results"}
        except Exception as e:
            error_msg = f"Official docs search/cache failed: {e}"
            save_log("ERROR", error_msg, source="search", component="search_service")
            return {"error": error_msg, "results": []}

    def _auto_detect_context(self, query: str) -> str:
        """Auto-detect search context based on query keywords. (Unchanged, but robust)"""
        query_lower = query.lower()
        
        error_keywords = ["error", "exception", "traceback", "failed", "crash", "bug", "troubleshoot"]
        if any(kw in query_lower for kw in error_keywords):
            return "error"
        
        code_keywords = ["example", "sample", "how to", "tutorial", "implementation", "repo", "pull request", "issue"]
        if any(kw in query_lower for kw in code_keywords):
            return "code_example"
        
        doc_keywords = ["documentation", "docs", "api", "reference", "guide", "manual"]
        if any(kw in query_lower for kw in doc_keywords):
            return "documentation"
        
        practice_keywords = ["best practice", "pattern", "optimization", "performance", "design pattern"]
        if any(kw in query_lower for kw in practice_keywords):
            return "best_practice"
        
        return "all"

    def _merge_and_rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Merge, deduplicate, and rank search results."""
        seen_urls = set()
        unique_results = []
        
        # Deduplication
        for result in results:
            url = result.get("url")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            unique_results.append(result)
        
        # Source Priority (Higher is better)
        source_priority = {"stackoverflow": 3.0, "github": 2.0, "official_doc": 1.0}
        
        def score_result(result: Dict[str, Any]) -> float:
            title = result.get("title", "").lower()
            query_terms = query.lower().split()
            
            # Title Match Score (weight 10)
            title_score = sum(1 for term in query_terms if term in title)
            
            # Original Score (StackOverflow/GitHub, scaled down)
            original_score = float(result.get("score", 0) or 0) / 100.0 # Normalize score impact
            
            # Source Priority Score
            source_score = source_priority.get(result.get("source", ""), 0.0)
            
            return (title_score * 10.0) + original_score + source_score
        
        unique_results.sort(key=score_result, reverse=True)
        return unique_results
    
    async def _async_search_and_collect(self, query: str, context: str, max_total_results: int) -> List[Dict[str, Any]]:
        """
        Runs all necessary searches concurrently and collects results.
        This is the core asynchronous improvement.
        """
        
        search_tasks = []
        
        # Determine the maximum number of results to fetch for each source initially
        # A simple split is used here, but a smarter, weighted split could be implemented
        max_per_source = max(1, max_total_results // 3 + 1)

        # Create search tasks - use async methods directly
        if context in ("error", "all"):
            search_tasks.append(self.search_stackoverflow_and_cache_async(query, max_per_source))

        if context in ("code_example", "all"):
            search_tasks.append(self.search_github_async(query, max_per_source))

        if context in ("documentation", "all", "best_practice"):
            search_tasks.append(self.search_official_docs_async(query, max_per_source))

        # Run tasks concurrently
        if not search_tasks:
            return []
            
        raw_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        collected: List[Dict[str, Any]] = []
        for result in raw_results:
            # Handle exceptions from asyncio.gather
            if isinstance(result, Exception):
                save_log("WARN", f"Search task failed: {result}", source="search", component="search_service")
                continue
            
            # Each result is a dict with "results" list and possibly "error"/"message"
            if isinstance(result, dict) and "error" in result:
                continue  # Skip results with errors
            
            if not isinstance(result, dict) or "results" not in result:
                continue
            
            # Extract results from the search response
            for r in result.get("results", []):
                # Clean up HTML entities in title if present
                title = r.get("title", "")
                if isinstance(title, str):
                    import html as html_module
                    title = html_module.unescape(title)
                
                # Determine source from URL
                url = r.get("url", "")
                source = "unknown"
                if url:
                    if "stackoverflow.com" in url:
                        source = "stackoverflow"
                    elif "github.com" in url:
                        source = "github"
                    elif "spark.apache.org" in url or "apache.org" in url:
                        source = "official_doc"
                
                collected.append({
                    "source": source, 
                    "title": title,
                    "url": url, 
                    "score": r.get("score")
                })
                
        return collected
        

    def search_smart(self, query: str, context: str = "all", max_total_results: int = 5, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for backward compatibility.
        Internally calls the async version.
        """
        return asyncio.run(self.search_smart_async(query, context, max_total_results, source))
    
    async def search_smart_async(self, query: str, context: str = "all", max_total_results: int = 5, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronous interface for intelligent multi-source search.
        Searches multiple sources concurrently and merges results.
        If source is specified, only that source is searched (github/stackoverflow/official_doc).
        """
        if context == "auto":
            context = self._auto_detect_context(query)
        
        # Collect results from all sources based on context or restrict to a single source
        collected: List[Dict[str, Any]] = []
        max_per_source = max(1, max_total_results // 3 + 1)
        
        # If source is explicitly specified, only search that source
        if source:
            if source.lower() == "stackoverflow":
                so_result = await self.search_stackoverflow_and_cache_async(query, max_total_results)
                if "error" not in so_result:
                    for r in so_result.get("results", []):
                        title = r.get("title", "")
                        if isinstance(title, str):
                            import html as html_module
                            title = html_module.unescape(title)
                        collected.append({
                            "source": "stackoverflow",
                            "title": title,
                            "url": r.get("url"),
                            "score": r.get("score")
                        })
            elif source.lower() == "github":
                gh_result = await self.search_github_async(query, max_total_results)
                if "error" not in gh_result:
                    for r in gh_result.get("results", []):
                        title = r.get("title", "")
                        if isinstance(title, str):
                            import html as html_module
                            title = html_module.unescape(title)
                        collected.append({
                            "source": "github",
                            "title": title,
                            "url": r.get("url"),
                            "score": r.get("score")
                        })
            elif source.lower() == "official_doc":
                docs_result = await self.search_official_docs_async(query, max_total_results)
                if "error" not in docs_result:
                    for r in docs_result.get("results", []):
                        title = r.get("title", "")
                        if isinstance(title, str):
                            import html as html_module
                            title = html_module.unescape(title)
                        collected.append({
                            "source": "official_doc",
                            "title": title,
                            "url": r.get("url"),
                            "score": r.get("score")
                        })
            # Return single-source results without merging/ranking
            return {"results": collected[:max_total_results], "message": f"Smart search (source={source}) returned {len(collected[:max_total_results])} results."}
        
        # Multi-source search when no specific source is provided
        # Run all searches concurrently
        search_tasks = []
        
        if context in ("error", "all"):
            search_tasks.append(("stackoverflow", self.search_stackoverflow_and_cache_async(query, max_per_source)))

        if context in ("code_example", "all"):
            search_tasks.append(("github", self.search_github_async(query, max_per_source)))

        if context in ("documentation", "all", "best_practice"):
            search_tasks.append(("official_doc", self.search_official_docs_async(query, max_per_source)))

        # Run all tasks concurrently
        if search_tasks:
            results = await asyncio.gather(*[task[1] for task in search_tasks], return_exceptions=True)
            
            for (source_name, _), result in zip(search_tasks, results):
                if isinstance(result, Exception):
                    save_log("WARN", f"Search task failed for {source_name}: {result}", source="search", component="search_service")
                    continue
                
                if "error" in result:
                    continue
                
                for r in result.get("results", []):
                    title = r.get("title", "")
                    if isinstance(title, str):
                        import html as html_module
                        title = html_module.unescape(title)
                    collected.append({
                        "source": source_name,
                        "title": title,
                        "url": r.get("url"),
                        "score": r.get("score")
                    })
        
        # Merge and rank results
        ranked_results = self._merge_and_rank_results(collected, query)

        return {"results": ranked_results[:max_total_results], "message": f"Smart search returned {len(ranked_results[:max_total_results])} results."}


    def search_smart_with_metrics(self, query: str, context: str = "auto", max_total_results: int = 5) -> Dict[str, Any]:
        """Synchronous wrapper for backward compatibility. Intelligent search with performance metrics."""
        return asyncio.run(self.search_smart_with_metrics_async(query, context, max_total_results))
    
    async def search_smart_with_metrics_async(self, query: str, context: str = "auto", max_total_results: int = 5) -> Dict[str, Any]:
        """Asynchronous intelligent search with performance metrics."""
        
        start_time = time.time()
        
        # Auto-detect or use specified context
        auto_detected = context == "auto"
        if auto_detected:
            context = self._auto_detect_context(query)
        
        # Run the search concurrently
        collected = await self._async_search_and_collect(query, context, max_total_results)
        
        # Count results by source
        results_count = {}
        sources_searched = []
        for result in collected:
            source = result.get("source")
            if source and source != "unknown":
                results_count[source] = results_count.get(source, 0) + 1
                sources_searched.append(source)
                
        # Merge and rank results
        ranked_results = self._merge_and_rank_results(collected, query)
        
        end_time = time.time()
        elapsed_ms = round((end_time - start_time) * 1000, 2)
        
        return {
            "results": ranked_results[:max_total_results],
            "metadata": {
                "query": query,
                "context": context,
                "auto_detected": auto_detected,
                "sources_searched": list(set(sources_searched)),
                "results_by_source": results_count,
                "total_time_ms": elapsed_ms,
                "total_results": len(collected),
                "returned_results": min(len(ranked_results), max_total_results)
            },
            "message": f"Found {len(collected)} results from {len(set(sources_searched))} sources in {elapsed_ms}ms"
        }

    def tool_search(self, query: str, source_hint: Optional[str] = None, 
                      max_results: int = 3, cache_results: bool = True) -> Dict[str, Any]:
        """Synchronous wrapper for backward compatibility. Search interface designed for tool invocations."""
        return asyncio.run(self.tool_search_async(query, source_hint, max_results, cache_results))
    
    async def tool_search_async(self, query: str, source_hint: Optional[str] = None, 
                      max_results: int = 3, cache_results: bool = True) -> Dict[str, Any]:
        """Asynchronous search interface designed for tool invocations."""
        
        if source_hint:
            source_map = {
                "stackoverflow": self.search_stackoverflow_and_cache_async,
                "github": self.search_github_async,
                "official_docs": self.search_official_docs_async,
                "spark_docs": lambda q, mr: self.search_official_docs_async(f"spark {q}", mr)
            }
            
            if source_hint in source_map:
                # Run single async search
                result = await source_map[source_hint](query, max_results)
                simplified = []
                for item in result.get("results", []):
                    simplified.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source": source_hint
                    })
                return {
                    "results": simplified[:max_results],
                    "total_found": len(simplified),
                    "sources": [source_hint]
                }
        
        # Otherwise use intelligent search
        result = await self.search_smart_async(query, context="auto", max_total_results=max_results)
        
        # Simplify results for tool consumption
        simplified_results = []
        for item in result.get("results", []):
            simplified_results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "source": item.get("source")
            })
        
        return {
            "results": simplified_results[:max_results],
            "total_found": len(simplified_results),
            "sources": list(set([r["source"] for r in simplified_results]))
        }

    # ==================== Sync wrapper methods for backward compatibility ====================
    def search_stackoverflow_and_cache(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Synchronous wrapper for StackOverflow search."""
        return asyncio.run(self.search_stackoverflow_and_cache_async(query, max_results))

    def search_github(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Synchronous wrapper for GitHub search."""
        return asyncio.run(self.search_github_async(query, max_results))

    def search_official_docs(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Synchronous wrapper for official docs search."""
        return asyncio.run(self.search_official_docs_async(query, max_results))

    def tool_search(self, query: str, source_hint: Optional[str] = None, 
                    max_results: int = 3, cache_results: bool = True) -> Dict[str, Any]:
        """Synchronous wrapper for tool search."""
        return asyncio.run(self.tool_search_async(query, source_hint, max_results, cache_results))