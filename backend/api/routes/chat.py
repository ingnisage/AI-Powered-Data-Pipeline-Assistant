# backend/api/routes/chat.py - Chat Endpoints
"""
Chat-related API endpoints with proper error handling and logging.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging
from datetime import datetime

from backend.models.interaction import ChatMessage
from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_openai_client, get_supabase_client, get_container
from backend.core.guardrails import contains_pii, rate_limiter  # Added imports for PII detection and rate limiting
from backend.utils.logging_helpers import log_and_publish
from backend.utils.profanity_filter import validate_content  # Added import for profanity filter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatHistoryResponse(BaseModel):
    messages: List[dict]

class ChatResponse(BaseModel):
    """Standardized chat response model."""
    answer: str
    tools_used: list = []

def publish_fn(channel: str, data: Dict[str, Any]) -> None:
    """Mock publish function for testing."""
    logger.debug(f"Publishing to channel {channel}: {data}")

@router.get("/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(limit: int = 10, supabase_client = Depends(get_supabase_client)):
    """Get chat history from database."""
    try:
        logger.info(f"Fetching chat history with limit {limit}")
        logger.info(f"Supabase client available: {supabase_client is not None}")
        
        # Fetch chat history from database
        if supabase_client:
            logger.info("Executing Supabase query for chat history")
            response = supabase_client.table("chat_history").select("*").order("created_at", desc=True).limit(limit).execute()
            logger.info(f"Supabase response received: {response is not None}")
            messages = response.data if response and hasattr(response, 'data') else []
            logger.info(f"Successfully fetched {len(messages)} chat messages from database")
            return ChatHistoryResponse(messages=messages)
        else:
            logger.warning("Supabase client not available")
            return ChatHistoryResponse(messages=[])
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}", exc_info=True)
        return ChatHistoryResponse(messages=[])

@router.post("/", response_model=ChatResponse, dependencies=[Depends(verify_api_key_dependency)])
async def chat(
    msg: ChatMessage,
    openai_client = Depends(get_openai_client),
    supabase_client = Depends(get_supabase_client),
    container = Depends(get_container)
):
    """Process a chat message and return AI response."""
    try:
        logger.info(f"Processing chat message: {msg.message[:100]}...")
        
        # Validate content for profanity before processing
        is_appropriate, error_msg = validate_content(msg.message)
        if not is_appropriate:
            logger.warning(f"Inappropriate content detected: {msg.message[:50]}...")
            # Return a friendly error response without creating a task
            return ChatResponse(
                answer="I'm sorry, but I can't process that message. Please use appropriate language.",
                tools_used=[]
            )
        
        # Check for PII in the message
        if contains_pii(msg.message):
            logger.warning(f"PII detected in message: {msg.message[:50]}...")
            # Return a friendly error response without creating a task
            return ChatResponse(
                answer="I'm sorry, but I can't process that message as it contains sensitive information.",
                tools_used=[]
            )
        
        # Apply rate limiting based on user ID or session ID
        user_identifier = msg.user_id or msg.session_id or "anonymous"
        is_allowed, seconds_until_reset = rate_limiter.allow(user_identifier)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user: {user_identifier}")
            # Return a friendly error response without creating a task
            return ChatResponse(
                answer=f"I'm sorry, but you've exceeded the rate limit. Please wait {seconds_until_reset} seconds before sending another message.",
                tools_used=[]
            )
        
        # Get the actual publish function from the container
        pubnub_client = container.get_pubnub_client()
        
        def publish_fn(channel: str, data: Dict[str, Any]) -> None:
            """Publish message to PubNub channel."""
            if pubnub_client:
                try:
                    result = pubnub_client.publish().channel(channel).message(data).sync()
                    logger.info(f"Successfully published to PubNub channel: {channel}")
                    return result
                except Exception as e:
                    logger.warning(f"Failed to publish to PubNub channel {channel}: {e}")
            else:
                logger.warning("PubNub client not available for publishing")
        
        from backend.services.chat_processor import ChatProcessor
        
        chat_processor = ChatProcessor(
            openai_client=openai_client,
            supabase_client=supabase_client,
            search_service=container.get_search_service(),
            vector_service=container.get_vector_service(),
            publish_fn=publish_fn  # Pass the publish function to the chat processor
        )
        
        # Process the chat message
        response_data = await chat_processor.process_chat(
            user_msg=msg.message,
            system_prompt_key=getattr(msg, 'system_prompt', 'general'),
            use_tools=getattr(msg, 'use_tools', False),
            search_source=getattr(msg, 'search_source', None)
        )
        
        # Extract tools used from the response
        tools_used = [r.get("tool_name") for r in response_data.get("tool_results", []) if r.get("tool_name")]
        
        # Create a task from the chat interaction (only if content is appropriate)
        task_name = f"Chat: {msg.message[:50]}..." if len(msg.message) > 50 else f"Chat: {msg.message}"
        task_description = f"Chat interaction with AI assistant. User said: {msg.message}"
        
        logger.info(f"Attempting to create task from chat: {task_name}")
        
        try:
            if supabase_client:
                task_data = {
                    "name": task_name,
                    "description": task_description,
                    "status": "In Progress",  # Using a value that actually works in the database
                    "progress": 0  # Setting progress to 0 for "In Progress" status
                }
                logger.info(f"Attempting to create task with data: {task_data}")
                task_response = supabase_client.table("tasks").insert(task_data).execute()
                logger.info(f"Task insert response: {task_response}")
                if not task_response or not task_response.data:
                    logger.warning("Task creation failed - no data returned from Supabase")
                    return  # Skip task publishing if creation failed
                
                task_id = task_response.data[0]["id"] if task_response and task_response.data else None
                logger.info(f"Task ID extracted: {task_id}")
                
                # Publish task creation to tasks channel with proper structure
                if pubnub_client:
                    try:
                        # Get the full task data from the response
                        task_record = task_response.data[0] if task_response and task_response.data else {}
                        logger.info(f"Task record extracted: {task_record}")
                        
                        # Ensure task ID is a string to match frontend expectations
                        task_id_str = str(task_record.get("id", task_id)) if task_record.get("id", task_id) is not None else None
                        
                        # Create task payload matching the TaskResponse model structure
                        task_payload = {
                            "type": "created",
                            "task": {
                                "id": task_id_str,
                                "name": task_record.get("name", task_name),
                                "status": task_record.get("status", "In Progress"),  # Using a value that actually works
                                "progress": task_record.get("progress", 0),
                                "description": task_record.get("description", task_description),
                                "created_at": task_record.get("created_at", datetime.now().isoformat() + "Z"),
                                "updated_at": task_record.get("updated_at", datetime.now().isoformat() + "Z")
                            }
                        }
                        logger.info(f"Task payload to be published: {task_payload}")
                        publish_result = pubnub_client.publish().channel("tasks").message(task_payload).sync()
                        logger.info(f"Task creation published to PubNub, result: {publish_result}")
                        logger.info("Task creation published to PubNub")
                    except Exception as e:
                        logger.warning(f"Failed to publish task creation to PubNub: {e}")
                
                logger.info(f"Task created from chat interaction: {task_name}")
        except Exception as e:
            logger.warning(f"Failed to create task from chat interaction: {e}")
        
        # Log successful chat interaction and publish to logs channel
        log_and_publish(
            level="INFO",
            message=f"Chat processed successfully: {msg.message[:100]}...",
            source="chat",
            component="chat_endpoint",
            metadata={},  # Ensure we pass an empty dict instead of None
            supabase_client=supabase_client,
            publish_channel="logs",  # Publish to the logs channel
            publish_fn=publish_fn
        )
        
        # Return the response in the expected format
        return ChatResponse(
            answer=response_data["answer"],
            tools_used=tools_used
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        # Log error and publish to logs channel
        log_and_publish(
            level="ERROR",
            message=f"Error processing chat: {str(e)}",
            source="chat",
            component="chat_endpoint",
            metadata={},  # Ensure we pass an empty dict instead of None
            supabase_client=supabase_client,
            publish_channel="logs",  # Publish to the logs channel
            publish_fn=publish_fn
        )
        # Return a simple error response instead of raising an exception
        return ChatResponse(
            answer="Sorry, I encountered an error processing your message.",
            tools_used=[]
        )