# vector_service.py

import asyncio
import hashlib
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from openai import OpenAIError, RateLimitError, APIError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import the Document dataclass from the client file
# if TYPE_CHECKING is used for type hinting to avoid circular dependencies

# Import save_log from backend.utils
try:
    from backend.utils import save_log
except ImportError:
    # Fallback: if running from search module context
    def save_log(level: str, message: str, source: str = "search", component: str = "vector_service"):
        print(f"[{level}] {source}/{component}: {message}")

if TYPE_CHECKING:
    from backend.services.search_clients import Document  # For type hinting only

class VectorStoreService:
    """Handles embedding generation and upsert operations into Supabase."""

    EMBEDDING_MODEL = "text-embedding-3-small"
    KNOWLEDGE_BASE_TABLE = "knowledge_base"

    def __init__(self, openai_client: Any, supabase_client: Any):
        self.openai_client = openai_client
        self.supabase = supabase_client
        
    def _ensure_supabase(self):
        if not self.supabase:
            raise RuntimeError("Supabase client is not configured for VectorStoreService")
    
    def _ensure_openai(self):
        if not self.openai_client:
            raise RuntimeError("OpenAI client is not configured for VectorStoreService")

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError, APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        stop=stop_after_attempt(4),
        reraise=True
    )
    async def _generate_embeddings_async(self, contents: List[str]) -> Optional[List[List[float]]]:
        """Call OpenAI to generate embeddings asynchronously with batching and exponential backoff.
        
        Batches large requests into chunks of 100 to avoid rate limits.
        Automatically retries on rate limit / API errors with exponential backoff.
        """
        self._ensure_openai()
        try:
            BATCH_SIZE = 100  # Safe for OpenAI rate limits
            all_embeddings = []
            
            # Process in batches to avoid rate limiting
            for i in range(0, len(contents), BATCH_SIZE):
                batch = contents[i:i + BATCH_SIZE]
                loop = asyncio.get_event_loop()
                
                # Run OpenAI call in executor to avoid blocking
                emb_response = await loop.run_in_executor(
                    None,
                    lambda b=batch: self.openai_client.embeddings.create(
                        model=self.EMBEDDING_MODEL, 
                        input=b
                    )
                )
                all_embeddings.extend([it.embedding for it in emb_response.data])
                
                # Log batch completion
                if i + BATCH_SIZE < len(contents):
                    save_log("DEBUG", f"Processed batch {i // BATCH_SIZE + 1}/{(len(contents) + BATCH_SIZE - 1) // BATCH_SIZE}", 
                             source="vector_service", component="embeddings")
            
            return all_embeddings
        except (RateLimitError, APIError, APIConnectionError) as e:
            save_log("ERROR", f"OpenAI API error (will retry): {e}", source="vector_service", component="embeddings")
            raise  # Re-raise for tenacity retry logic
        except Exception as e:
            save_log("ERROR", f"Failed to generate embeddings: {e}", source="vector_service", component="embeddings")
            return None

    async def _upsert_impl_async(self, docs: List['Document']) -> Dict[str, Any]:
        """Internal async implementation: Generate embeddings and upsert documents to knowledge base."""
        try:
            self._ensure_supabase()
        except RuntimeError as e:
            return {"error": str(e), "results": []}

        if not docs:
            return {"results": [], "message": "No documents to upsert."}

        contents = [d.content for d in docs]
        embeddings = await self._generate_embeddings_async(contents)
        
        if not embeddings:
            return {"error": "Failed to generate embeddings", "results": []}
            
        # Prepare rows for upsert
        rows = []
        for doc, emb in zip(docs, embeddings):
            content_hash = hashlib.sha256(doc.content.encode("utf-8")).hexdigest()
            rows.append({
                "content": doc.content,
                "content_hash": content_hash,
                "embedding": emb,
                "source_type": doc.source_type,
                "source_url": doc.source_url,
                "title": doc.title,
                "metadata": doc.metadata,
            })
            
        # Upsert into Supabase asynchronously
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table(self.KNOWLEDGE_BASE_TABLE).upsert(
                    rows, 
                    on_conflict="content_hash"
                ).execute()
            )
            
            saved_count = len(result.data) if result.data else 0
            save_log("INFO", f"Saved {saved_count} docs to knowledge_base (Total: {len(rows)})", 
                     source="vector_service", component="upsert")
                     
        except Exception as e:
            save_log("ERROR", f"Failed to save to knowledge_base: {e}", source="vector_service", component="upsert")
            return {"error": str(e), "results": []}

        # Return results with data from Supabase response when available
        if result.data:
            # Use Supabase response data for more accurate results
            results = [
                {
                    "id": r.get("id"),
                    "title": r.get("title"), 
                    "url": r.get("source_url"), 
                    "score": r.get("metadata", {}).get("score"),
                    "content_hash": r.get("content_hash")
                } 
                for r in result.data
            ]
        else:
            # Fallback to input-derived results if no data from Supabase
            results = [
                {
                    "title": r["title"], 
                    "url": r["source_url"], 
                    "score": r.get("metadata", {}).get("score")
                } 
                for r in rows
            ]
        
        return {"results": results, "message": f"Cached {len(rows)} docs into knowledge_base."}

    # Removed synchronous wrapper to avoid asyncio.run() issues in event loops
    # Use upsert_documents_async() instead
    
    async def upsert_documents_async(self, docs: List['Document'], dry_run: bool = False) -> Dict[str, Any]:
        """Asynchronous version: Generate embeddings and upsert documents.
        
        Args:
            docs: List of Document objects to upsert
            dry_run: If True, return what would be upserted without actually saving
            
        Returns:
            Dict with 'results' and 'message' keys
        """
        if dry_run:
            save_log("INFO", f"[DRY RUN] Would upsert {len(docs)} documents", 
                     source="vector_service", component="upsert")
            return {
                "results": [{"title": d.title, "url": d.source_url} for d in docs],
                "message": f"[DRY RUN] Would have upserted {len(docs)} docs"
            }
        
        return await self._upsert_impl_async(docs)