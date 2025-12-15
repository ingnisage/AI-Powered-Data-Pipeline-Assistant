# api_client.py - API Client Layer
"""
Centralized API client for backend communication.
Handles all HTTP requests with proper error handling, timeouts, and logging.
"""

import requests
import logging
import sys
import os
from typing import Dict, List, Optional, Any, Tuple

# Add the project root to Python path to ensure proper imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.config import config

logger = logging.getLogger(__name__)

# Get API key from environment or use default
API_KEY = os.getenv("BACKEND_API_KEY", "test-api-key")

class WorkbenchAPIError(Exception):
    """Base exception for API errors."""
    pass


class WorkbenchAPI:
    """Client for interacting with the AI Workbench backend API."""
    
    def __init__(self, base_url: str):
        """Initialize API client.
        
        Args:
            base_url: Base URL of the backend API
        """
        self.base_url = base_url.rstrip('/')
        logger.info(f"Initialized WorkbenchAPI with base URL: {self.base_url}")
    
    # =================================== TASK OPERATIONS ===================================
    
    def get_tasks(self) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Fetch all tasks from the backend.
        
        Returns:
            Tuple of (success, tasks_list, error_message)
        """
        try:
            logger.info(f"Attempting to fetch tasks from: {self.base_url}/api/tasks/")
            r = requests.get(
                f"{self.base_url}/api/tasks/",
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_SHORT
            )
            r.raise_for_status()
            tasks = r.json().get("tasks", [])
            logger.info(f"Successfully fetched {len(tasks)} tasks")
            return True, tasks, None
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to backend at {self.base_url}"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Task fetch request timed out"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch tasks: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid task data format: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def create_task(self, name: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Create a new task.
        
        Args:
            name: Task name
            
        Returns:
            Tuple of (success, task_dict, error_message)
        """
        try:
            r = requests.post(
                f"{self.base_url}/api/tasks/",
                json={"name": name},
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_TASK_OPS
            )
            r.raise_for_status()
            
            if r.status_code in (200, 201):
                task = r.json().get("task") if r.content else None
                logger.info(f"Successfully created task: {name}")
                return True, task, None
            else:
                error_msg = f"Failed to create task: HTTP {r.status_code}"
                logger.error(error_msg)
                return False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to backend"
            logger.error(f"Task creation connection error to {self.base_url}")
            return False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Request timed out"
            logger.error("Task creation timed out")
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Task creation request exception: {e}")
            return False, None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = "Invalid response from backend"
            logger.error(f"Invalid task creation response: {e}")
            return False, None, error_msg
    
    def update_task(self, task_id: str, status: str, progress: int) -> Tuple[bool, Optional[str]]:
        """Update task status and progress.
        
        Args:
            task_id: Task ID to update
            status: New status
            progress: New progress percentage (0-100)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            payload = {"status": status, "progress": progress}
            logger.info(f"Updating task {task_id} with payload: {payload}")
            r = requests.patch(
                f"{self.base_url}/api/tasks/{task_id}",
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_TASK_OPS
            )
            logger.info(f"Task update response status: {r.status_code}")
            if r.text:
                logger.info(f"Task update response body: {r.text[:200]}")
            r.raise_for_status()
            
            if r.status_code in (200, 201):
                logger.info(f"Successfully updated task {task_id}: {status} ({progress}%)")
                return True, None
            else:
                error_msg = f"Failed to update: HTTP {r.status_code}"
                logger.error(f"Task update failed with status {r.status_code}")
                return False, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to backend"
            logger.error(f"Task update connection error to {self.base_url}")
            return False, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Request timed out"
            logger.error("Task update timed out")
            return False, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Task update request exception: {e}")
            return False, error_msg
    
    # =================================== LOG OPERATIONS ===================================
    
    def get_logs(self) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Fetch logs from the backend.
        
        Returns:
            Tuple of (success, logs_list, error_message)
        """
        try:
            r = requests.get(
                f"{self.base_url}/api/logs/",
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_SHORT
            )
            r.raise_for_status()
            logs = r.json().get("logs", [])
            logger.info(f"Successfully fetched {len(logs)} logs")
            return True, logs, None
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Could not connect to backend at {self.base_url} for logs")
            return False, None, "Connection error"
            
        except requests.exceptions.Timeout:
            logger.warning("Logs fetch request timed out")
            return False, None, "Timeout"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch logs: {e}")
            return False, None, str(e)
    
    # =================================== CHAT OPERATIONS ===================================
    
    def get_chat_history(self, limit: int = 10) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Fetch chat history from the backend.
        
        Args:
            limit: Maximum number of messages to fetch
            
        Returns:
            Tuple of (success, messages_list, error_message)
        """
        try:
            logger.info(f"Attempting to fetch chat history from: {self.base_url}/api/chat/chat-history")
            r = requests.get(
                f"{self.base_url}/api/chat/chat-history",
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_SHORT
            )
            r.raise_for_status()
            
            if r.status_code == 200:
                messages = r.json().get("messages", [])
                logger.info(f"Successfully fetched {len(messages)} chat messages")
                return True, messages, None
            else:
                error_msg = f"Unexpected status code: {r.status_code}"
                logger.warning(error_msg)
                return False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"Could not connect to backend at {self.base_url} for chat history"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Chat history fetch request timed out"
            logger.warning(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch chat history: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid chat history data format: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def send_chat_message(
        self,
        message: str,
        system_prompt: str = "general",
        use_tools: bool = True,
        search_source: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Send a chat message to the backend.
        
        Args:
            message: User message content
            system_prompt: System prompt type
            use_tools: Whether to enable tools
            search_source: Optional search source (stackoverflow, github, official_doc)
            
        Returns:
            Tuple of (success, response_data, error_message)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/",
                json={
                    "message": message,
                    "system_prompt": system_prompt,
                    "use_tools": use_tools,
                    "search_source": search_source
                },
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_LONG
            )
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Chat response received, tools used: {data.get('tools_used', [])}")
                return True, data, None
            else:
                error_msg = f"Failed to get response: HTTP {response.status_code}"
                logger.error(f"Chat request failed with status {response.status_code}")
                return False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to backend. Please check if the server is running."
            logger.error(f"Connection error to {self.base_url}")
            return False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. The backend may be overloaded."
            logger.error("Chat request timed out")
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Chat request exception: {e}")
            return False, None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = "Invalid response from backend"
            logger.error(f"Invalid chat response format: {e}")
            return False, None, error_msg
    
    # =================================== SEARCH OPERATIONS ===================================
    
    def search_knowledge(
        self,
        query: str,
        source: str = "all",
        max_results: int = 5
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Search knowledge sources directly.
        
        Args:
            query: Search query
            source: Source to search (github, stackoverflow, official_doc, spark_docs, all)
            max_results: Maximum number of results to return
            
        Returns:
            Tuple of (success, search_results, error_message)
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/search/",
                json={
                    "query": query,
                    "source": source,
                    "max_results": max_results
                },
                headers={"X-API-Key": API_KEY},
                timeout=config.API_TIMEOUT_TASK_OPS
            )
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Search completed: {data.get('total_results', 0)} results found")
                return True, data, None
            else:
                error_msg = f"Search failed: HTTP {response.status_code}"
                logger.error(f"Search request failed with status {response.status_code}")
                return False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to backend. Please check if the server is running."
            logger.error(f"Connection error to {self.base_url}")
            return False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "Search request timed out. The backend may be overloaded."
            logger.error("Search request timed out")
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Search request failed: {str(e)}"
            logger.error(f"Search request exception: {e}")
            return False, None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = "Invalid response from backend"
            logger.error(f"Invalid search response format: {e}")
            return False, None, error_msg
