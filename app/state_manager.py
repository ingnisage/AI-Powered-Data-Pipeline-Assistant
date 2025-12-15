# state_manager.py - State Management Layer
"""
Business logic for managing application state.
Handles task management, message formatting, and data transformations.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dateutil import parser as date_parser
from backend.services.config import config

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    ZoneInfo = None

logger = logging.getLogger(__name__)

# Cache timezone object for performance
_cached_timezone: Optional[Any] = None


class TaskManager:
    """Manages task-related business logic."""
    
    # Task status priority for sorting
    STATUS_ORDER: Dict[str, int] = {
        "Pending": 1,
        "In Progress": 2,
        "Completed": 3,
        "Failed": 4
    }
    
    @staticmethod
    def deduplicate(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate tasks by ID, preserving order.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Deduplicated list of tasks, preserving original order
        """
        seen: Set[Any] = set()
        unique: List[Dict[str, Any]] = []
        
        for task in tasks:
            task_id = task.get("id")
            if task_id is None or task_id not in seen:
                unique.append(task)
                if task_id is not None:
                    seen.add(task_id)
        
        logger.debug(f"Deduplicated {len(tasks)} tasks to {len(unique)} unique tasks")
        return unique
    
    @staticmethod
    def sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort tasks by status priority, creation time, and name.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Sorted list of tasks
        """
        def sort_key(t: Dict[str, Any]) -> tuple:
            """Generate sort key for a task."""
            status = t.get("status") or ""
            created_at = t.get("created_at") or ""
            name = t.get("name") or ""
            return (TaskManager.STATUS_ORDER.get(status, 99), created_at, name)
        
        sorted_tasks = sorted(tasks, key=sort_key)
        logger.debug(f"Sorted {len(tasks)} tasks by status priority")
        return sorted_tasks
    
    @staticmethod
    def upsert_task(tasks: List[Dict[str, Any]], new_task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Insert or update a task in the task list by ID.
        
        Args:
            tasks: Existing list of tasks
            new_task: Task to insert or update
            
        Returns:
            Updated task list
        """
        if not new_task:
            logger.warning("Attempted to upsert empty task")
            return tasks
        
        task_id = new_task.get("id")
        
        if task_id is None:
            # No ID, just append (caller should avoid this)
            logger.warning("Upserting task without ID")
            return tasks + [new_task]
        
        # Try to update existing task
        for i, task in enumerate(tasks):
            if task.get("id") == task_id:
                tasks[i] = new_task
                logger.debug(f"Updated existing task: {task_id}")
                return tasks
        
        # Task not found, append
        logger.debug(f"Inserted new task: {task_id}")
        return tasks + [new_task]


class MessageFormatter:
    """Handles message and data formatting."""
    
    @staticmethod
    def convert_chat_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert chat history from DB format to UI format.
        
        Args:
            messages: Messages from backend in DB format
            
        Returns:
            Messages in UI format
        """
        ui_messages = []
        
        for msg in messages:
            ui_msg = {
                "role": msg.get("role"),
                "content": msg.get("content", ""),
            }
            
            # Add tools_used if available
            tools_used = msg.get("tools_used")
            if tools_used:
                ui_msg["tools_used"] = tools_used
            
            ui_messages.append(ui_msg)
        
        logger.debug(f"Converted {len(messages)} messages to UI format")
        return ui_messages
    
    @staticmethod
    def get_timezone(tz_name: str = None) -> Optional[Any]:
        """Get timezone object with caching for performance.
        
        Args:
            tz_name: Timezone name (e.g., 'America/New_York')
            
        Returns:
            ZoneInfo object if available and valid, None otherwise
        """
        global _cached_timezone
        
        # Use config default if not specified
        if tz_name is None:
            tz_name = config.DEFAULT_TIMEZONE
        
        if _cached_timezone is None and ZoneInfo is not None:
            try:
                _cached_timezone = ZoneInfo(tz_name)
                logger.debug(f"Cached timezone: {tz_name}")
            except Exception as e:
                logger.warning(f"Failed to create timezone {tz_name}: {e}")
                return None
        
        return _cached_timezone
    
    @staticmethod
    def reset_timezone_cache() -> None:
        """Reset the cached timezone object.
        
        Should be called when timezone preference changes.
        """
        global _cached_timezone
        _cached_timezone = None
        logger.debug("Timezone cache reset")
    
    @staticmethod
    def format_timestamp(raw_time: str, tz_name: str = None) -> str:
        """Convert ISO timestamp to specified timezone with robust parsing.
        
        Uses dateutil.parser for flexible date parsing and supports timezone
        conversion with caching for performance.
        
        Args:
            raw_time: ISO format timestamp string (UTC or with timezone info)
            tz_name: Target timezone name (default: from config.DEFAULT_TIMEZONE)
            
        Returns:
            Formatted time string in target timezone with timezone abbreviation,
            or original string if parsing fails
            
        Examples:
            >>> format_timestamp("2024-01-15T10:30:00Z")
            "2024-01-15 05:30:00 EST"
        """
        if not raw_time:
            return ""
        
        # Use config default if not specified
        if tz_name is None:
            tz_name = config.DEFAULT_TIMEZONE
        
        try:
            # Use dateutil.parser for robust ISO format parsing
            dt = date_parser.isoparse(raw_time.replace("Z", "+00:00"))
            
            # Convert to target timezone if available
            target_tz = MessageFormatter.get_timezone(tz_name)
            if dt.tzinfo is not None and target_tz is not None:
                dt_local = dt.astimezone(target_tz)
                # Include timezone abbreviation for clarity (EST, EDT, etc.)
                return dt_local.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            # Fallback: format without timezone conversion
            return dt.strftime("%Y-%m-%d %H:%M:%S")
            
        except (ValueError, TypeError, AttributeError) as e:
            # Log parsing errors for debugging
            logger.debug(f"Failed to parse timestamp '{raw_time}': {e}")
            return raw_time  # Return original on parse failure


class LogManager:
    """Manages log display and filtering."""
    
    @staticmethod
    def get_display_logs(logs: List[Dict[str, Any]], max_count: int = None) -> List[Dict[str, Any]]:
        """Get logs for display with limit and sorting.
        
        Args:
            logs: All available logs
            max_count: Maximum number of logs to return (default: from config)
            
        Returns:
            Sorted and limited log list
        """
        if max_count is None:
            max_count = config.MAX_LOGS_DISPLAY
        
        # Take last N logs and sort by time (newest first)
        recent_logs = logs[-max_count:] if len(logs) > max_count else logs
        sorted_logs = sorted(
            recent_logs,
            key=lambda l: l.get("time") or "",
            reverse=True
        )
        
        logger.debug(f"Retrieved {len(sorted_logs)} logs for display")
        return sorted_logs
    
    @staticmethod
    def get_log_emoji(level: str) -> str:
        """Get emoji for log level.
        
        Args:
            level: Log level (INFO, WARNING, ERROR)
            
        Returns:
            Emoji string
        """
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        return emoji_map.get(level, "📝")
