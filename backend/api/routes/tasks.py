# backend/api/routes/tasks.py - Task Management Endpoints
"""
Task-related API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional, Union
from pydantic import BaseModel
import logging

from backend.models.interaction import NewTask, TaskUpdate
from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Define response models inline since they're not in the interaction.py file
class TaskResponse(BaseModel):
    id: Union[str, int]  # Accept both string and integer IDs
    name: str
    status: str = "Not Started"
    progress: int = 0
    description: Optional[str] = None
    priority: Optional[str] = "Medium"
    assigned_to: Optional[str] = None
    created_at: str
    updated_at: str

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]

@router.get("/", response_model=TaskListResponse)
async def get_tasks(supabase_client = Depends(get_supabase_client)):
    """Get all tasks from database."""
    try:
        logger.info("Fetching all tasks")
        if supabase_client:
            response = supabase_client.table("tasks").select("*").order("created_at", desc=True).execute()
            tasks = response.data if response and hasattr(response, 'data') else []
            # Convert task IDs to strings to match the model expectation
            for task in tasks:
                if 'id' in task and isinstance(task['id'], int):
                    task['id'] = str(task['id'])
            logger.info(f"Successfully fetched {len(tasks)} tasks from database")
            return TaskListResponse(tasks=tasks)
        else:
            logger.warning("Supabase client not available")
            return TaskListResponse(tasks=[])
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")

@router.post("/", response_model=TaskResponse, dependencies=[Depends(verify_api_key_dependency)])
async def create_task(
    task: NewTask,
    supabase_client = Depends(get_supabase_client)
):
    """Create a new task in database."""
    try:
        logger.info(f"Creating new task: {task.name}")
        if supabase_client:
            task_data = {
                "name": task.name,
                "status": "In Progress",  # Changed from "Not Started" to avoid constraint issues
                "progress": 0,
                "description": getattr(task, 'description', ''),
                "assigned_to": getattr(task, 'assigned_to', None),
                "priority": getattr(task, 'priority', 'Medium')
            }
            
            response = supabase_client.table("tasks").insert(task_data).execute()
            if response and response.data:
                created_task = response.data[0]
                # Convert task ID to string to match the model expectation
                if 'id' in created_task and isinstance(created_task['id'], int):
                    created_task['id'] = str(created_task['id'])
                logger.info(f"Successfully created task: {created_task['id']}")
                return TaskResponse(**created_task)
            else:
                raise HTTPException(status_code=500, detail="Failed to create task in database")
        else:
            logger.error("Supabase client not available")
            raise HTTPException(status_code=500, detail="Database not available")
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")

@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(verify_api_key_dependency)])
async def update_task(
    task_id: str,
    task: TaskUpdate,
    supabase_client = Depends(get_supabase_client)
):
    """Update an existing task in database."""
    try:
        logger.info(f"Updating task {task_id}: status={task.status}, progress={task.progress}")
        if supabase_client:
            update_data = {}
            if hasattr(task, 'status') and task.status is not None:
                update_data["status"] = task.status
            if hasattr(task, 'progress') and task.progress is not None:
                update_data["progress"] = task.progress
            if hasattr(task, 'description') and task.description is not None:
                update_data["description"] = task.description
            if hasattr(task, 'assigned_to') and task.assigned_to is not None:
                update_data["assigned_to"] = task.assigned_to
            if hasattr(task, 'priority') and task.priority is not None:
                update_data["priority"] = task.priority
            
            if update_data:
                response = supabase_client.table("tasks").update(update_data).eq("id", task_id).execute()
                if response and response.data:
                    updated_task = response.data[0]
                    # Convert task ID to string to match the model expectation
                    if 'id' in updated_task and isinstance(updated_task['id'], int):
                        updated_task['id'] = str(updated_task['id'])
                    logger.info(f"Successfully updated task: {task_id}")
                    return TaskResponse(**updated_task)
                else:
                    raise HTTPException(status_code=404, detail="Task not found")
            else:
                raise HTTPException(status_code=400, detail="No update data provided")
        else:
            logger.error("Supabase client not available")
            raise HTTPException(status_code=500, detail="Database not available")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task")