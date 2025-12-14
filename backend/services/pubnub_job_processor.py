# backend/services/pubnub_job_processor.py - Improved Job Processor
"""
Improved PubNub job processor with proper dependency injection.
"""

import json
import logging
import time
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, Any, Tuple

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
import openai
import tenacity

from backend.utils.logging_sanitizer import sanitize_log_message
from .exceptions import handle_exception, ProcessingError, NetworkError, ServiceInitializationError
from .retry import retry_with_backoff, API_RETRY_CONFIG
from .monitoring import monitored_operation, performance_counters
from .resource_manager import resource_manager

logger = logging.getLogger(__name__)


class JobProcessor:
    """Processes job requests from PubNub queue with proper dependency injection."""
    
    def __init__(
        self,
        openai_client=None,
        supabase_client=None,
        publish_fn=None
    ):
        """Initialize job processor with dependencies.
        
        Args:
            openai_client: OpenAI client for AI processing
            supabase_client: Supabase client for database operations
            publish_fn: Function for publishing real-time updates
        """
        self.openai_client = openai_client
        self.supabase_client = supabase_client
        self.publish = publish_fn
        
        # Register resources with resource manager
        if openai_client:
            resource_manager.register_resource("job_processor_openai_client", openai_client, "client")
        if supabase_client:
            resource_manager.register_resource("job_processor_supabase_client", supabase_client, "client")
        
        logger.info("JobProcessor initialized with dependency injection and resource management")
    
    def query_job_context(self, job_id: str, job_description: str = None) -> dict:
        """Query job context from Supabase using embeddings.
        
        Args:
            job_id: The ID of the job
            job_description: Optional job description for semantic search
            
        Returns:
            Dictionary containing job context
        """
        if not self.supabase_client:
            return {'error': 'Supabase client not configured'}
            
        try:
            # If we have a job_id, query directly
            if job_id:
                response = self.supabase_client.table('rag_content').select("*").eq('document_id', job_id).eq('document_type', 'job').execute()
                if response.data and len(response.data) > 0:
                    return {
                        'job_id': job_id,
                        'context': response.data[0].get('context', ''),
                        'metadata': response.data[0]
                    }
            
            # If we have a job description, use embeddings for semantic search
            if job_description and self.openai_client:
                embedding_response = self.openai_client.embeddings.create(
                    input=job_description,
                    model='text-embedding-3-small'
                )
                query_embedding = embedding_response.data[0].embedding
                
                # Query using the RPC function
                rag_results = self.supabase_client.rpc(
                    'match_documents_by_document_type',
                    {
                        'query_embedding': query_embedding,
                        'match_count': 1,
                        'query_document_type': 'job'
                    }
                ).execute()
                
                if rag_results.data and len(rag_results.data) > 0:
                    return {
                        'job_id': rag_results.data[0].get('document_id', ''),
                        'context': rag_results.data[0].get('context', ''),
                        'similarity': rag_results.data[0].get('similarity', 0),
                        'metadata': rag_results.data[0]
                    }
            
            return {'error': 'No job context found'}
            
        except Exception as e:
            error_msg = f"Error querying job context: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {'error': error_msg}
    
    @retry_with_backoff(config=API_RETRY_CONFIG)
    def process_with_openai(self, job_context: dict, user_query: str) -> str:
        """Process the job context and user query with OpenAI.
        
        Retries up to 5 times on RateLimitError or APIError with exponential backoff
        (4s → 8s → 16s → 32s → 60s max).
        
        Args:
            job_context: Dictionary containing job information
            user_query: The user's question or request
            
        Returns:
            OpenAI response text
        """
        if not self.openai_client:
            raise Exception("OpenAI client not configured")
            
        try:
            context_text = job_context.get('context', '')
            
            system_prompt = f"""You are an expert job matching assistant. Use the following job context to answer questions:

{context_text}

Provide helpful, accurate information about the job based on the context provided. Be concise"""
            
            completion = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0
            )
            
            return completion.choices[0].message.content
            
        except (openai.RateLimitError, openai.APIError) as e:
            logger.warning(f"OpenAI API error (will retry): {e}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            error_msg = f"Error processing with OpenAI: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def store_response(self, job_id: str, user_query: str, response: str, metadata: dict = None) -> dict:
        """Store the AI response in Supabase.
        
        Args:
            job_id: The job ID
            user_query: The original user query
            response: The AI response
            metadata: Additional metadata
            
        Returns:
            Dictionary with the inserted record
        """
        if not self.supabase_client:
            raise Exception("Supabase client not configured")
            
        try:
            record = {
                'job_id': job_id,
                'user_query': user_query,
                'ai_response': response,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase_client.table('job_responses').insert(record).execute()
            
            if result.data:
                logger.info(f"Response stored successfully with ID: {result.data[0].get('id')}")
                return result.data[0]
            else:
                raise Exception("Failed to store response in Supabase")
                
        except Exception as e:
            error_msg = f"Error storing response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def process_job_request(self, message: dict) -> dict:
        """Main processing function for job requests.
        
        Args:
            message: The message received from PubNub
            
        Returns:
            Dictionary containing the response reference
        """
        with monitored_operation("job_processor.process_job_request", 
                               {"job_id": message.get('job_id'), "request_id": message.get('request_id')},
                               self.supabase_client):
            try:
                job_id = message.get('job_id')
                job_description = message.get('job_description')
                user_query = message.get('query', 'Tell me about this job')
                
                logger.info(f"Processing job request - job_id: {job_id}, query: {sanitize_log_message(user_query[:50])}")
                performance_counters.increment("job_requests_processed")
                
                # Step 1: Query job context
                job_context = self.query_job_context(job_id, job_description)
                if 'error' in job_context:
                    error_details = job_context['error']
                    logger.error(f"Failed to query job context: {error_details}")
                    performance_counters.increment("job_context_errors")
                    return {
                        'status': 'error',
                        'error': str(error_details),
                        'request_id': message.get('request_id')
                    }
                
                # Step 2: Process with OpenAI
                try:
                    ai_response = self.process_with_openai(job_context, user_query)
                    performance_counters.increment("openai_processing_success")
                except Exception as e:
                    logger.error(f"OpenAI processing failed: {str(e)}", exc_info=True)
                    performance_counters.increment("openai_processing_errors")
                    raise ProcessingError("OpenAI processing", str(e))
                
                # Step 3: Store in Supabase
                try:
                    stored_record = self.store_response(
                        job_id=job_context.get('job_id', job_id),
                        user_query=user_query,
                        response=ai_response,
                        metadata={
                            'similarity': job_context.get('similarity'),
                            'request_id': message.get('request_id'),
                            'original_job_id': job_id
                        }
                    )
                    performance_counters.increment("job_responses_stored")
                except Exception as e:
                    logger.error(f"Failed to store response: {str(e)}", exc_info=True)
                    performance_counters.increment("job_response_storage_errors")
                    raise ProcessingError("response storage", str(e))
                
                # Step 4: Return reference
                performance_counters.increment("job_requests_completed")
                return {
                    'status': 'success',
                    'response_id': stored_record.get('id'),
                    'job_id': job_context.get('job_id'),
                    'request_id': message.get('request_id'),
                    'response': ai_response,
                    'timestamp': stored_record.get('created_at')
                }
                
            except Exception as e:
                # Handle all exceptions with our standardized handler
                error_response = handle_exception(e, context="process_job_request", component="JobProcessor")
                logger.error(f"Job processing failed: {error_response}", exc_info=True)
                performance_counters.increment("job_processing_errors")
                
                return {
                    'status': 'error',
                    'error': str(e),
                    'error_details': error_response.get("error", {}),
                    'request_id': message.get('request_id')
                }


class PubNubJobListener(SubscribeCallback):
    """PubNub callback handler for job requests with message deduplication."""
    
    def __init__(
        self, 
        pubnub_client: PubNub, 
        response_channel: str,
        job_processor: JobProcessor
    ):
        """Initialize listener with dependencies.
        
        Args:
            pubnub_client: PubNub client instance
            response_channel: Channel to publish responses to
            job_processor: JobProcessor instance
        """
        self.pubnub = pubnub_client
        self.response_channel = response_channel
        self.processor = job_processor
        # Deduplication cache: request_id → timestamp (5-minute TTL window)
        self.seen_requests = defaultdict(float)
        self.dedup_window = 300  # 5 minutes in seconds
        
        logger.info("PubNubJobListener initialized")
    
    def is_duplicate(self, request_id: str) -> bool:
        """Check if request_id was seen within the dedup window (5 min).
        
        Returns:
            True if duplicate, False otherwise
        """
        if not request_id:
            return False
        now = time.time()
        if request_id in self.seen_requests:
            if now - self.seen_requests[request_id] < self.dedup_window:
                logger.warning(f"Duplicate request detected: {request_id}")
                return True
        self.seen_requests[request_id] = now
        return False
    
    def status(self, pubnub, status):
        """Handle PubNub status events."""
        if status.category == PNStatusCategory.PNConnectedCategory:
            logger.info("Connected to PubNub")
        elif status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            logger.warning("Disconnected from PubNub")
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            logger.info("Reconnected to PubNub")
    
    def message(self, pubnub, message):
        """Handle incoming messages from PubNub.
        
        Args:
            pubnub: PubNub instance
            message: Incoming message
        """
        try:
            logger.info(f"Received message: {message.message}")
            
            job = message.message if isinstance(message.message, dict) else {}
            request_id = job.get('request_id')
            
            # Check for duplicates and skip if already processed recently
            if self.is_duplicate(request_id):
                logger.info(f"Skipping duplicate request: {request_id}")
                return
            
            # Delegate all messages to the JobProcessor for handling
            response = self.processor.process_job_request(job)
            self.publish_response(response)
            return
            
        except Exception as e:
            logger.exception(f"Unhandled error handling message: {e}")
            # Attempt to extract request_id safely
            try:
                req_id = message.message.get('request_id') if isinstance(message.message, dict) else None
            except Exception:
                req_id = None
            self.publish_response({
                'status': 'error',
                'error': str(e),
                'request_id': req_id
            })
    
    def publish_response(self, response: dict):
        """Publish response to PubNub response channel.
        
        Args:
            response: Response dictionary to publish
        """
        try:
            self.pubnub.publish()\
                .channel(self.response_channel)\
                .message(response)\
                .pn_async(lambda result, status: None)  # Fire-and-forget
            
            logger.debug(f"Response queued for publish to {self.response_channel}: {response.get('status')}")
            
        except Exception as e:
            logger.error(f"Failed to publish response (non-critical): {e}")


def create_pubnub_job_processor(
    openai_client=None,
    supabase_client=None,
    publish_fn=None,
    pubnub_config: Optional[Dict[str, str]] = None
) -> Tuple[PubNub, PubNubJobListener]:
    """Factory function to create a PubNub job processor with proper dependency injection.
    
    Args:
        openai_client: OpenAI client
        supabase_client: Supabase client
        publish_fn: Publishing function
        pubnub_config: PubNub configuration dictionary
        
    Returns:
        Tuple of (PubNub client, PubNubJobListener)
    """
    # Create job processor with dependencies
    job_processor = JobProcessor(
        openai_client=openai_client,
        supabase_client=supabase_client,
        publish_fn=publish_fn
    )
    
    # Configure PubNub
    if pubnub_config is None:
        pubnub_config = {
            "publish_key": "demo",
            "subscribe_key": "demo",
            "user_id": "job-processor-worker-01"
        }
    
    pnconfig = PNConfiguration()
    pnconfig.publish_key = pubnub_config.get("publish_key", "demo")
    pnconfig.subscribe_key = pubnub_config.get("subscribe_key", "demo")
    pnconfig.user_id = pubnub_config.get("user_id", "job-processor-worker-01")
    pnconfig.daemon = True  # Important: allows process to exit cleanly
    
    pubnub_client = PubNub(pnconfig)
    
    # Register PubNub client with resource manager
    resource_manager.register_resource("pubnub_client", pubnub_client, "client", 
                                     finalizer=lambda: pubnub_client.stop())
    
    # Create listener
    listener = PubNubJobListener(
        pubnub_client=pubnub_client,
        response_channel=pubnub_config.get("response_channel", "job-responses"),
        job_processor=job_processor
    )
    
    # Register listener with resource manager
    resource_manager.register_resource("pubnub_listener", listener, "listener")
    
    # Add listener to PubNub client
    pubnub_client.add_listener(listener)
    
    logger.info("PubNub job processor created with dependency injection and resource management")
    return pubnub_client, listener