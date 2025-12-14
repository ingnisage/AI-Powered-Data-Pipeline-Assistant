# backend/utils/logging_helpers.py
"""
Logging helper functions that were previously in ai_workbench_v2/utils.py.
These functions provide convenient wrappers for saving logs and chat messages.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from backend.models.logging import LogBuilder, ChatMessageBuilder
from backend.utils.logging_sanitizer import sanitize_log_message
# Import handle_exception with fallback
try:
    from backend.services.exceptions import handle_exception
except ImportError:
    # Fallback implementation if ai_workbench_v2 is not available
    def handle_exception(exception, context="", component=""):
        """Fallback exception handler."""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Exception in {context} ({component}): {str(exception)}")
        return {"error": str(exception), "context": context, "component": component}

logger = logging.getLogger(__name__)


def save_log(
    level: str,
    message: str,
    source: str = "system",
    component: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    metadata: Optional[dict] = None,
    supabase_client=None,
):
    """Persist logs to Supabase logs table with proper error handling.
    
    Args:
        level: Log level (INFO, ERROR, WARNING, DEBUG)
        message: Log message
        source: Source of the log
        component: Component that generated the log
        user_id: User identifier
        session_id: Session identifier
        duration_ms: Operation duration in milliseconds
        metadata: Additional metadata
        supabase_client: Supabase client for database operations
    """
    if not supabase_client:
        logger.debug("Supabase client not available, skipping log save")
        return
        
    try:
        # Ensure metadata is a dictionary
        if metadata is None:
            metadata = {}
        
        # Create log entry using builder pattern
        # Map string level to LogLevel enum and use appropriate builder method
        from backend.models.logging import LogLevel
        level_enum = LogLevel(level.upper()) if isinstance(level, str) else level
        
        if level_enum == LogLevel.ERROR:
            log_entry = LogBuilder.error(
                message=message,
                source=source,
                component=component,
                user_id=user_id,
                session_id=session_id,
                duration_ms=duration_ms,
                metadata=metadata
            )
        elif level_enum == LogLevel.WARNING:
            log_entry = LogBuilder.warning(
                message=message,
                source=source,
                component=component,
                user_id=user_id,
                session_id=session_id,
                duration_ms=duration_ms,
                metadata=metadata
            )
        elif level_enum == LogLevel.DEBUG:
            log_entry = LogBuilder.debug(
                message=message,
                source=source,
                component=component,
                user_id=user_id,
                session_id=session_id,
                duration_ms=duration_ms,
                metadata=metadata
            )
        else:  # INFO or default
            log_entry = LogBuilder.info(
                message=message,
                source=source,
                component=component,
                user_id=user_id,
                session_id=session_id,
                duration_ms=duration_ms,
                metadata=metadata
            )
        
        # Save to database
        supabase_client.table("logs").insert(log_entry.to_dict()).execute()
        logger.debug(f"Log saved to database: {level} - {sanitize_log_message(message[:50])}")
        
        # Return the log entry for use in publishing
        return log_entry
    except Exception as e:
        # Handle exception with our standardized handler
        try:
            error_response = handle_exception(e, context="save_log", component=component or "utils")
            # Log the error but don't let it break the main flow
            logger.warning(f"Failed to save log to database: {e}", extra=error_response)
        except Exception as handler_error:
            # If the exception handler itself fails, just log the original error
            logger.warning(f"Failed to save log to database: {e}")


def log_and_publish(
    level: str,
    message: str,
    source: str = "system",
    component: Optional[str] = None,
    publish_channel: Optional[str] = None,
    metadata: Optional[dict] = None,
    supabase_client=None,
    publish_fn=None,
):
    """Convenience function: save_log + publish to real-time channel.
    
    Args:
        level: Log level
        message: Log message
        source: Source of the log
        component: Component that generated the log
        publish_channel: Channel to publish to
        metadata: Additional metadata
        supabase_client: Supabase client for database operations
        publish_fn: Function for publishing real-time updates
    """
    # Ensure metadata is a dictionary
    if metadata is None:
        metadata = {}
        
    # Save to database and get the log entry
    log_entry = save_log(
        level=level,
        message=message,
        source=source,
        component=component,
        metadata=metadata,
        supabase_client=supabase_client
    )
    
    # Publish real-time update with complete log data
    if publish_channel and publish_fn and log_entry:
        try:
            # Convert log entry to dict format matching API response
            log_dict = {
                "id": "",  # Will be assigned by frontend or database
                "level": log_entry.level.value,
                "message": log_entry.message,
                "source": log_entry.source.value,
                "timestamp": log_entry.time.isoformat() if log_entry.time else datetime.now().isoformat(),
                "component": log_entry.component
            }
            
            publish_fn(publish_channel, log_dict)
            logger.debug(f"Real-time update published to {publish_channel}")
        except Exception as e:
            # Handle exception with our standardized handler
            try:
                error_response = handle_exception(e, context="log_and_publish", component=component or "utils")
                logger.warning(f"Failed to publish real-time update: {e}", extra=error_response)
            except Exception as handler_error:
                # If the exception handler itself fails, just log the original error
                logger.warning(f"Failed to publish real-time update: {e}")


def save_chat_message(
    role: str,
    content: str,
    system_prompt: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tools_used: Optional[List[str]] = None,
    tool_results: Optional[list] = None,
    rag_sources: Optional[list] = None,
    tokens_used: Optional[int] = None,
    metadata: Optional[dict] = None,
    supabase_client=None,
):
    """Persist a chat message to the chat_history table.
    
    Args:
        role: Message role (user, assistant, system)
        content: Message content
        system_prompt: System prompt used
        session_id: Session identifier
        user_id: User identifier
        tools_used: List of tools used
        tool_results: Tool execution results
        rag_sources: RAG sources used
        tokens_used: Number of tokens used
        metadata: Additional metadata
        supabase_client: Supabase client for database operations
    """
    if not supabase_client:
        logger.debug("Supabase client not available, skipping chat message save")
        return
        
    try:
        # Ensure metadata is a dictionary
        if metadata is None:
            metadata = {}
            
        # Create chat message entry using builder pattern
        # Map string role to ChatMessageRole enum and use appropriate builder method
        from backend.models.logging import ChatMessageRole
        role_enum = ChatMessageRole(role.lower()) if isinstance(role, str) else role
        
        if role_enum == ChatMessageRole.USER:
            chat_entry = ChatMessageBuilder.user_message(
                content=content,
                system_prompt=system_prompt or "data_engineer",
                session_id=session_id,
                user_id=user_id,
                **({'metadata': metadata} if metadata else {})
            )
        elif role_enum == ChatMessageRole.ASSISTANT:
            chat_entry = ChatMessageBuilder.assistant_message(
                content=content,
                system_prompt=system_prompt or "data_engineer",
                session_id=session_id,
                user_id=user_id,
                tools_used=tools_used or [],
                tool_results=tool_results or [],
                tokens_used=tokens_used,
                **({'metadata': metadata} if metadata else {})
            )
        elif role_enum == ChatMessageRole.TOOL:
            chat_entry = ChatMessageBuilder.tool_message(
                content=content,
                session_id=session_id,
                **({'metadata': metadata} if metadata else {})
            )
        else:  # SYSTEM or default
            chat_entry = ChatMessageBuilder.user_message(
                content=content,
                system_prompt=system_prompt or "data_engineer",
                session_id=session_id,
                user_id=user_id,
                **({'metadata': metadata} if metadata else {})
            )
        
        # Save to database
        supabase_client.table("chat_history").insert(chat_entry.to_dict()).execute()
        logger.debug(f"Chat message saved to database: {role} - {sanitize_log_message(content[:50])}")
        
    except Exception as e:
        # Handle exception with our standardized handler
        try:
            error_response = handle_exception(e, context="save_chat_message", component="utils")
            logger.warning(f"Failed to save chat message to database: {e}", extra=error_response)
        except Exception as handler_error:
            # If the exception handler itself fails, just log the original error
            logger.warning(f"Failed to save chat message to database: {e}")