# search_clients.py

import os
import re
import html
import asyncio
import hashlib
import httpx
import tenacity
from httpx import Limits
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

# Import async-aware caching decorator
from backend.utils.caching import cached

# Global rate limiting configuration for all HTTP clients
GLOBAL_LIMITS = Limits(
    max_keepalive_connections=10,
    max_connections=50
)

# Standard User-Agent for all requests
USER_AGENT = "AI-Workbench/1.0 (+https://github.com/ingnisage/AI-Powered-Data-Pipeline-Assistant)"

# Import save_log from backend.utils
try:
    from backend.utils import save_log
except ImportError:
    # Fallback: if running from search module context
    import sys
    if 'backend' in sys.modules or 'backend.utils' in sys.modules:
        from backend.utils import save_log
    else:
        # Minimal fallback implementation
        def save_log(level: str, message: str, source: str = "search", component: str = "client"):
            print(f"[{level}] {source}/{component}: {message}") 


# ==================== Retry Helper ====================
def _make_retry_decorator():
    """Create a retry decorator for HTTP requests with exponential backoff."""
    return tenacity.retry(
        retry=tenacity.retry_if_exception_type((
            httpx.HTTPStatusError,
            httpx.ReadTimeout,
            httpx.ConnectError,
            httpx.NetworkError
        )),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        stop=tenacity.stop_after_attempt(3),
        reraise=True,
        before_sleep=lambda retry_state: save_log(
            "WARNING",
            f"Request failed, retrying ({retry_state.attempt_number}/3): {retry_state.outcome.exception()}",
            component="http_retry"
        )
    )

HTTP_RETRY = _make_retry_decorator()


@dataclass
class Document:
    """Standardized document structure for content aggregation."""
    content: str
    title: str
    source_type: str
    source_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    # The embedding will be added by the VectorStoreService

class StackOverflowClient:
    """Handles searching and parsing StackExchange results with rate limiting and retries."""
    
    BASE_URL = "https://api.stackexchange.com/2.3/search/advanced"
    
    def __init__(self):
        """Initialize the client with a semaphore for concurrency control."""
        self._semaphore = asyncio.Semaphore(5)  # Max 5 concurrent SO requests
    
    def _clean_html(self, body_html: str) -> str:
        """Robustly clean HTML content using BeautifulSoup."""
        soup = BeautifulSoup(body_html, 'html.parser')
        # Remove code blocks, which often contain non-searchable or overly long content
        for code in soup.find_all('code'):
            code.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        return html.unescape(text)
    
    @HTTP_RETRY
    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with automatic retry on transient failures."""
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response

    async def search(self, query: str, max_results: int) -> List[Document]:
        """Asynchronously search StackOverflow with concurrency limits."""
        async with self._semaphore:  # Enforce max 5 concurrent requests
            params = {
                "order": "desc",
                "sort": "relevance",
                "q": query,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": max_results,
            }
            
            async with httpx.AsyncClient(
                timeout=15,
                limits=GLOBAL_LIMITS,
                headers={"User-Agent": USER_AGENT}
            ) as client:
                try:
                    resp = await self._fetch_with_retry(client, self.BASE_URL, params=params)
                    items = resp.json().get("items", [])
                except httpx.HTTPError as e:
                    save_log("ERROR", f"StackOverflow API request failed after retries: {e}", source="stackoverflow_client", component="search_client")
                    return []
                except Exception as e:
                    save_log("ERROR", f"StackOverflow API unexpected error: {e}", source="stackoverflow_client", component="search_client")
                    return []

        docs: List[Document] = []
        for item in items:
            title = item.get("title", "")
            body_html = item.get("body", "")
            
            # Data cleaning
            body_text = self._clean_html(body_html)
            content = f"StackOverflow question: {title}\n\n{body_text}"
            
            docs.append(Document(
                content=content,
                title=title,
                source_type="stackoverflow",
                source_url=item.get("link"),
                metadata={
                    "question_id": item.get("question_id"),
                    "tags": item.get("tags", []),
                    "is_answered": item.get("is_answered"),
                    "score": item.get("score", 0),
                },
            ))
        return docs

class GitHubClient:
    """Handles searching GitHub repositories, issues, PRs, and code with rate limiting and retries."""
    
    BASE_URL = "https://api.github.com/search"
    
    def __init__(self):
        """Initialize the client with a semaphore for concurrency control."""
        self._semaphore = asyncio.Semaphore(3)  # Max 3 concurrent GitHub requests (strict rate limit)
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT
        }
        gh_token = os.getenv("GITHUB_TOKEN")
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"
        return headers
    
    @HTTP_RETRY
    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with automatic retry on transient failures."""
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response

    async def search(self, query: str, max_results: int) -> List[Document]:
        """Asynchronously search GitHub (repositories, issues, code) with concurrency limits."""
        async with self._semaphore:  # Enforce max 3 concurrent requests
            headers = self._get_headers()
            docs: List[Document] = []

            # Search across multiple types: code, repositories, and issues
            search_types = [
                ("code", f"{self.BASE_URL}/code"),
                ("repositories", f"{self.BASE_URL}/repositories"),
                ("issues", f"{self.BASE_URL}/issues"),
            ]

            async with httpx.AsyncClient(
                timeout=10,
                limits=GLOBAL_LIMITS,
                headers=headers
            ) as client:
                for search_type, endpoint in search_types:
                    try:
                        # Build query with sort for relevance
                        params = {
                            "q": query,
                            "per_page": max(3, max_results // 3),  # Split results across 3 types
                            "sort": "stars" if search_type == "repositories" else "relevance",
                        }
                        
                        r = await self._fetch_with_retry(client, endpoint, params=params)
                        items = r.json().get("items", [])
                        
                        for item in items:
                            if search_type == "code":
                                # Code search result
                                title = f"{item.get('name')} in {item.get('repository', {}).get('full_name', 'unknown')}"
                                url = item.get("html_url", "")
                                content = f"GitHub code: {title}\n\nPath: {item.get('path')}\n\nURL: {url}"
                                docs.append(Document(
                                    content=content,
                                    title=title,
                                    source_type="github",
                                    source_url=url,
                                    metadata={
                                        "type": "code",
                                        "language": item.get("language"),
                                        "path": item.get("path"),
                                        "repository": item.get("repository", {}).get("full_name"),
                                    },
                                ))
                            elif search_type == "repositories":
                                # Repository search result
                                title = item.get("full_name", "unknown_repo")
                                url = item.get("html_url", "")
                                content = f"GitHub repo: {title}\n\nDescription: {item.get('description', 'N/A')}\n\nURL: {url}"
                                docs.append(Document(
                                    content=content,
                                    title=title,
                                    source_type="github",
                                    source_url=url,
                                    metadata={
                                        "type": "repository",
                                        "stars": item.get("stargazers_count", 0),
                                        "language": item.get("language"),
                                        "description": item.get("description"),
                                    },
                                ))
                            else:  # issues
                                # Issue/PR search result
                                title = item.get("title", "unknown_issue")
                                url = item.get("html_url", "")
                                content = f"GitHub issue: {title}\n\nBody: {item.get('body', 'N/A')}\n\nURL: {url}"
                                docs.append(Document(
                                    content=content,
                                    title=title,
                                    source_type="github",
                                    source_url=url,
                                    metadata={
                                        "type": "issue",
                                        "state": item.get("state"),
                                        "score": item.get("score", 0),
                                    },
                                ))
                    except httpx.HTTPError as e:
                        save_log("WARNING", f"GitHub {search_type} search failed: {e}", source="github_client", component="search_client")
                        continue
                    except Exception as e:
                        save_log("WARNING", f"GitHub {search_type} parsing failed: {e}", source="github_client", component="search_client")
                        continue

        return docs[:max_results]  # Limit total results

class OfficialDocsClient:
    """Handles simple scraping of official documentation search results with rate limiting and retries.
    
    NOTE: This client returns placeholder results. In a production environment, 
    this would use a proper documentation search API."""
    
    def __init__(self):
        """Initialize the client with a semaphore for concurrency control."""
        self._semaphore = asyncio.Semaphore(4)  # Max 4 concurrent doc scraping requests
    
    async def search(self, query: str, max_results: int) -> List[Document]:
        """Asynchronously search docs with rate limiting."""
        async with self._semaphore:  # Enforce max 4 concurrent doc scraping ops
            docs: List[Document] = []
            
            try:
                # For Spark-specific queries, use placeholder approach
                if "spark" in query.lower():
                    # Simple placeholder approach for Spark docs with unique URL
                    import hashlib
                    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
                    content = f"Apache Spark documentation related to: {query}\n\nThis is a placeholder result. In a production environment, this would contain actual Spark documentation content."
                    docs.append(Document(
                        content=content,
                        title=f"Apache Spark Documentation: {query}",
                        source_type="spark_docs",
                        source_url=f"https://spark.apache.org/docs/result-{query_hash}.html",
                        metadata={},
                    ))
                else:
                    # Generic documentation search - return a placeholder document with unique URL
                    # In a production environment, this would use a proper search API
                    import hashlib
                    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
                    content = f"Documentation related to: {query}\n\nThis is a placeholder result. In a production environment, this would contain actual documentation content from various sources."
                    docs.append(Document(
                        content=content,
                        title=f"Documentation Result: {query}",
                        source_type="official_doc",
                        source_url=f"https://example.com/docs/{query_hash}",
                        metadata={},
                    ))

            except Exception as e:
                save_log("ERROR", f"Official docs search failed: {e}", source="docs_client", component="search_client")

        return docs


# ==================== Caching Layer (LRU Cache) ====================
# Cache search results to avoid repeated API calls for identical queries

def _cache_key(source: str, query: str, max_results: int) -> str:
    """Generate a cache key for a search query."""
    key = f"{source}:{query}:{max_results}"
    return hashlib.sha256(key.encode()).hexdigest()


# Lazy instantiation of clients for caching (instantiate only when needed)
_stackoverflow_client = None
_github_client = None
_official_docs_client = None

def _get_stackoverflow_client():
    """Get or create StackOverflow client."""
    global _stackoverflow_client
    if _stackoverflow_client is None:
        _stackoverflow_client = StackOverflowClient()
    return _stackoverflow_client

def _get_github_client():
    """Get or create GitHub client."""
    global _github_client
    if _github_client is None:
        _github_client = GitHubClient()
    return _github_client

def _get_official_docs_client():
    """Get or create Official Docs client."""
    global _official_docs_client
    if _official_docs_client is None:
        _official_docs_client = OfficialDocsClient()
    return _official_docs_client


@cached(namespace="search", ttl=300)
async def search_stackoverflow_cached(query: str, max_results: int = 5) -> tuple:
    """
    Cached wrapper for StackOverflow search.
    
    Note: lru_cache doesn't work directly with async functions returning lists,
    so we convert results to JSON-serializable tuples for caching.
    """
    client = _get_stackoverflow_client()
    docs = await client.search(query, max_results)
    # Convert Document objects to tuples for caching
    import json
    return tuple((d.content, d.title, d.source_type, d.source_url, json.dumps(d.metadata)) for d in docs)


@cached(namespace="search", ttl=300)
async def search_github_cached(query: str, max_results: int = 5) -> tuple:
    """
    Cached wrapper for GitHub search.
    
    Note: lru_cache doesn't work directly with async functions returning lists,
    so we convert results to JSON-serializable tuples for caching.
    """
    client = _get_github_client()
    docs = await client.search(query, max_results)
    # Convert Document objects to tuples for caching
    import json
    return tuple((d.content, d.title, d.source_type, d.source_url, json.dumps(d.metadata)) for d in docs)


@cached(namespace="search", ttl=300)
async def search_official_docs_cached(query: str, max_results: int = 5) -> tuple:
    """
    Cached wrapper for Official Docs search.
    
    Note: lru_cache doesn't work directly with async functions returning lists,
    so we convert results to JSON-serializable tuples for caching.
    """
    client = _get_official_docs_client()
    docs = await client.search(query, max_results)
    # Convert Document objects to tuples for caching
    import json
    return tuple((d.content, d.title, d.source_type, d.source_url, json.dumps(d.metadata)) for d in docs)


def _convert_cached_tuple_to_documents(cached_tuple: tuple) -> List[Document]:
    """Convert cached tuple back to Document objects."""
    import json
    docs = []
    for content, title, source_type, source_url, metadata_str in cached_tuple:
        try:
            metadata = json.loads(metadata_str)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        docs.append(Document(
            content=content,
            title=title,
            source_type=source_type,
            source_url=source_url,
            metadata=metadata
        ))
    return docs


# Cache statistics helper (for monitoring)
def get_cache_info() -> Dict[str, Any]:
    """Get cache statistics for all cached search functions."""
    # Get global cache stats since individual decorated functions don't expose cache info
    from backend.utils.caching import get_cache
    cache = get_cache()
    return {
        "global_cache_stats": cache.get_stats()
    }


def clear_all_caches():
    """Clear all search result caches."""
    # Clear the search namespace in the global cache
    from backend.utils.caching import get_cache
    cache = get_cache()
    cache.clear(namespace="search")
    save_log("INFO", "All search caches cleared", component="cache")