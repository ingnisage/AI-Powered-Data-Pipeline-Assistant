# backend/services/chat_processor.py - Improved Chat Processor
"""
Improved chat processor with proper dependency injection and alignment with backend patterns.
"""

import json
import logging
import asyncio
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime

from openai import OpenAI
from backend.tools.executor import ModularToolExecutor
from backend.utils.sanitization import sanitize_for_log, sanitize_for_display
from backend.models.logging import LogBuilder, ChatMessageBuilder
from backend.utils.logging_sanitizer import sanitize_log_message
from backend.services.config import config

from .exceptions import handle_exception, ProcessingError, NetworkError
from .retry import retry_with_backoff, API_RETRY_CONFIG
from .monitoring import monitored_operation
from backend.core.performance_monitoring import performance_counters
from .resource_manager import resource_manager

logger = logging.getLogger(__name__)


class ChatProcessor:
    """Improved chat processor with proper dependency injection."""
    
    def __init__(
        self,
        openai_client: Optional[OpenAI],
        supabase_client: Optional[Any] = None,
        search_service: Optional[Any] = None,
        vector_service: Optional[Any] = None,
        publish_fn: Optional[Any] = None,
        system_prompts: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize chat processor with proper dependency injection.
        
        Args:
            openai_client: OpenAI client for AI completions
            supabase_client: Supabase client for database operations
            search_service: Search service for knowledge retrieval
            vector_service: Vector service for embeddings
            publish_fn: Function for publishing real-time updates
            system_prompts: Custom system prompts
        """
        self.openai_client = openai_client
        self.supabase_client = supabase_client
        self.publish = publish_fn
        
        # Register resources with resource manager
        if openai_client:
            resource_manager.register_resource("chat_processor_openai_client", openai_client, "client")
        if supabase_client:
            resource_manager.register_resource("chat_processor_supabase_client", supabase_client, "client")
        
        # Initialize tool executor with proper dependencies
        self.tool_executor = ModularToolExecutor(
            openai_client=openai_client,
            search_service=search_service,
            vector_service=vector_service,
            supabase_client=supabase_client
        )
        
        # Register tool executor resource
        resource_manager.register_resource("chat_processor_tool_executor", self.tool_executor, "service")
        
        # Default prompts for specific roles
        self.SYSTEM_PROMPTS = system_prompts or {
            "data_engineer": "You are an expert data engineer specializing in data pipeline design, ETL processes, database optimization, and distributed systems. Provide technical solutions for data infrastructure challenges.",
            "ml_engineer": "You are an experienced machine learning engineer specializing in model development, deployment, and MLOps. Provide guidance on ML algorithms, frameworks, and production ML systems.",
            "analyst": "You are a skilled data analyst specializing in data interpretation, visualization, and business insights. Help users understand data patterns and derive actionable recommendations."
        }
        
        logger.info("ChatProcessor initialized with dependency injection and resource management")
    
    async def process_chat(
        self,
        user_msg: str,
        system_prompt_key: str = "general",
        use_tools: bool = False,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        search_source: Optional[str] = None,
    ) -> Dict:
        """Process a chat message with proper error handling and logging.
        
        Args:
            user_msg: User's message
            system_prompt_key: Which system prompt to use
            use_tools: Whether to enable tool usage
            session_id: Session identifier
            user_id: User identifier
            search_source: Optional search source restriction
            
        Returns:
            Dictionary with AI response and metadata
        """

        with monitored_operation("chat_processor.process_chat", 
                               {"session_id": session_id, "user_id": user_id},
                               self.supabase_client):
            try:
                logger.info(f"Processing chat message: {sanitize_log_message(user_msg[:50])}...")
                
                # Increment performance counter
                performance_counters.increment("chat_messages_processed")
                
                # Sanitize input
                sanitized_msg = sanitize_for_log(user_msg)
                
                # Build chat message entry
                chat_entry = ChatMessageBuilder.user_message(
                    content=sanitized_msg,
                    session_id=session_id if session_id is not None else "default_session",
                    user_id=user_id,
                    system_prompt=system_prompt_key
                )
                
                # Save user message to database
                if self.supabase_client:
                    try:
                        self.supabase_client.table("chat_history").insert(
                            chat_entry.to_dict()
                        ).execute()
                        logger.debug("User message saved to database")
                        performance_counters.increment("chat_messages_saved")
                    except Exception as e:
                        logger.warning(f"Failed to save user message: {e}")
                        performance_counters.increment("chat_message_save_errors")
                
                # Process with AI
                response_data = {
                    "answer": "",
                    "tool_results": [],
                    "sources": [],
                    "tokens_used": 0
                }
                
                # Build system/user messages for the LLM
                system_prompt = self.SYSTEM_PROMPTS.get(system_prompt_key, self.SYSTEM_PROMPTS.get("general"))
                # If no specific prompt found, use a default one
                if system_prompt is None:
                    system_prompt = "You are a helpful AI assistant."
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ]
                
                # If frontend requested a specific search source, bypass LLM and call smart_search directly
                if search_source:
                    response_data = await self._handle_direct_search(user_msg, search_source, session_id, user_id)
                else:
                    # Call the model
                    if not self.openai_client:
                        response_data["answer"] = "OpenAI client not configured."
                        logger.error("OpenAI client missing in ChatProcessor")
                        performance_counters.increment("openai_client_missing_errors")
                    else:
                        try:
                            openai_client = self.openai_client
                            
                            # Call OpenAI API with structured output
                            response = openai_client.chat.completions.create(
                                model=config.DEFAULT_MODEL,  # Use centralized config
                                messages=messages,
                                temperature=0.7,
                                max_tokens=1000
                                # Removed response_format to avoid OpenAI's JSON requirement
                            )

                            response_message = response.choices[0].message
                            response_data["answer"] = getattr(response_message, "content", "") or ""
                            
                            # Record usage
                            usage = getattr(response, "usage", None)
                            if usage:
                                response_data["tokens_used"] = (
                                    getattr(usage, "prompt_tokens", 0) + 
                                    getattr(usage, "completion_tokens", 0)
                                )
                                
                            # Record performance metrics
                            if usage:
                                performance_counters.record_timing("openai_api_call", 
                                                                 response_data["tokens_used"] / 1000.0)  # Approximate timing
                                
                        except Exception as e:
                            error_msg = f"LLM call failed: {str(e)}"
                            response_data["answer"] = error_msg
                            logger.error(error_msg, exc_info=True)
                            performance_counters.increment("openai_api_errors")
                            # Re-raise to be handled by outer exception handler
                            raise ProcessingError("LLM call", str(e))
                
                # Build assistant response entry
                assistant_entry = ChatMessageBuilder.assistant_message(
                    content=sanitize_for_display(response_data["answer"]),
                    session_id=session_id if session_id is not None else "default_session",
                    user_id=user_id,
                    system_prompt=system_prompt_key,
                    tools_used=[r.get("tool_name") for r in response_data["tool_results"]],
                    tool_results=response_data["tool_results"],
                    tokens_used=response_data["tokens_used"]
                )
                
                # Save assistant response
                if self.supabase_client:
                    try:
                        self.supabase_client.table("chat_history").insert(
                            assistant_entry.to_dict()
                        ).execute()
                        logger.debug("Assistant response saved to database")
                        performance_counters.increment("assistant_responses_saved")
                    except Exception as e:
                        logger.warning(f"Failed to save assistant response: {e}")
                        performance_counters.increment("assistant_response_save_errors")
                
                # Publish real-time update
                if self.publish:
                    try:
                        self.publish("chat", {
                            "session_id": session_id if session_id is not None else "default",
                            "message": sanitize_for_display(response_data["answer"][:400])
                        })
                        logger.debug("Real-time update published")
                        performance_counters.increment("real_time_updates_published")
                    except Exception as e:
                        logger.warning(f"Failed to publish real-time update: {e}")
                        performance_counters.increment("real_time_update_errors")
                
                logger.info("Chat processing completed")
                return response_data
                
            except Exception as e:
                # Handle all exceptions with our standardized handler
                error_response = handle_exception(e, context="process_chat", component="ChatProcessor")
                logger.error(f"Chat processing failed: {error_response}", exc_info=True)
                performance_counters.increment("chat_processing_errors")
                
                # Return error information in the same format as success response
                return {
                    "answer": f"Sorry, I encountered an error processing your request: {str(e)}",
                    "tool_results": [],
                    "sources": [],
                    "tokens_used": 0,
                    "error": error_response.get("error", {})
                }
    
    async def _handle_direct_search(
        self, 
        user_msg: str, 
        search_source: str, 
        session_id: Optional[str], 
        user_id: Optional[str]
    ) -> Dict:
        """Handle direct search requests bypassing the LLM.
        
        Args:
            user_msg: User's message
            search_source: Search source to use
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Dictionary with search results
        """
        logger.info(f"Handling direct search for source: {search_source}")
        
        # Normalize frontend labels to internal source keys
        src_map = {
            "Ask AI": None,
            "ask_ai": None,
            "StackOverflow": "stackoverflow",
            "GitHub": "github",
            "Spark Docs": "spark_docs",
            "official_doc": "official_doc",
            "stackoverflow": "stackoverflow",
            "github": "github",
        }
        requested = src_map.get(search_source, None)
        
        if requested is not None:
            try:
                # Call smart_search via tool executor
                args = {
                    "query": user_msg, 
                    "context": "all", 
                    "max_total_results": 5, 
                    "source": requested
                }
                
                tool_result = await self.tool_executor.execute_tool_call("smart_search", args)
                
                # Build assistant text from results
                results = tool_result.get("results", []) if isinstance(tool_result, dict) else []
                if not results:
                    assistant_text = "I couldn't find results for that query."
                else:
                    lines = ["Here are the top results I found:"]
                    for r in results[:5]:
                        title = r.get("title") or r.get("url")
                        url = r.get("url")
                        lines.append(f"- {title} ({url})")
                    assistant_text = "\n".join(lines)
                
                tool_results = [{
                    "tool_name": "smart_search", 
                    "arguments": args, 
                    "result": tool_result
                }]
                
                return {
                    "answer": assistant_text,
                    "tool_results": tool_results,
                    "sources": [],
                    "tokens_used": 0
                }
                
            except Exception as e:
                logger.error(f"Direct search failed: {e}", exc_info=True)
                return {
                    "answer": f"Search failed: {str(e)}",
                    "tool_results": [],
                    "sources": [],
                    "tokens_used": 0
                }
        
        # If no specific source requested, fall back to normal processing
        return {
            "answer": "",
            "tool_results": [],
            "sources": [],
            "tokens_used": 0
        }