# backend/api/routes/tasks.py - Task Management Endpoints
"""
Task-related API endpoints.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Union
import logging

from backend.models.interaction import NewTask, TaskUpdate
from backend.auth.security import verify_api_key_dependency
from backend.core.dependencies import get_supabase_client, retry_supabase_operation
from backend.db.optimized_queries import OptimizedQueries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Define response models inline since they're not in the interaction.py file
class TaskResponse(BaseModel):
    id: Union[str, int]  # Accept both string and integer IDs
    name: str
    status: str = "In Progress"
    progress: int = 0
    description: Optional[str] = None
    priority: Optional[str] = "Medium"
    assigned_to: Optional[str] = None
    created_at: str
    updated_at: str

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]

@router.get("/", response_model=TaskListResponse)
@retry_supabase_operation(max_retries=2)
async def get_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of tasks per page"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by task priority"),
    supabase_client = Depends(get_supabase_client)
):
    """Get all tasks from database with pagination and filtering."""
    try:
        logger.info(f"Fetching tasks - page: {page}, page_size: {page_size}")
        logger.info(f"Filters - status: {status}, priority: {priority}")
        logger.info(f"Supabase client available: {supabase_client is not None}")
        
        if supabase_client:
            # Prepare filters
            filters = {}
            if status:
                filters["status"] = status
            if priority:
                filters["priority"] = priority
            
            # Use optimized query with pagination
            result = await OptimizedQueries.get_tasks_optimized(
                supabase_client=supabase_client,
                page=page,
                page_size=page_size,
                filters=filters
            )
            
            logger.info(f"Successfully fetched {result['total_count']} tasks from database")
            logger.info(f"Has more tasks: {result['has_more']}")
            
            # Return tasks in the expected format
            return TaskListResponse(tasks=result["tasks"])
        else:
            logger.warning("Supabase client not available")
            return TaskListResponse(tasks=[])
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}", exc_info=True)
        # Provide more specific error information
        error_detail = f"Failed to fetch tasks: {str(e)}"
        if "connection" in str(e).lower():
            error_detail = "Database connection failed. Please check your network connection and try again."
        elif "timeout" in str(e).lower():
            error_detail = "Database timeout: The request took too long to complete. Please try again later."
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/", response_model=TaskResponse, dependencies=[Depends(verify_api_key_dependency)])
async def create_task(
    task: NewTask,
    supabase_client = Depends(get_supabase_client)
):
    """Create a new task in database."""
    try:
        logger.info(f"Creating new task: {task.name}")
        logger.info(f"Task data: {task.dict()}")
        if supabase_client:
            task_data = {
                "name": task.name,
                "status": "In Progress",  # Changed from "Not Started" to avoid constraint issues
                "progress": 0,
                "description": getattr(task, 'description', ''),
                "assigned_to": getattr(task, 'assigned_to', None),
                "priority": getattr(task, 'priority', 'Medium')
            }
            
            logger.info(f"Inserting task data into Supabase: {task_data}")
            response = supabase_client.table("tasks").insert(task_data).execute()
            logger.info(f"Supabase response: {response}")
            if response and response.data:
                created_task = response.data[0]
                logger.info(f"Created task data: {created_task}")
                # Convert task ID to string to match the model expectation
                if 'id' in created_task and isinstance(created_task['id'], int):
                    created_task['id'] = str(created_task['id'])
                logger.info(f"Successfully created task: {created_task['id']}")
                return TaskResponse(**created_task)
            else:
                error_msg = "Failed to create task in database - no data returned"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        else:
            logger.error("Supabase client not available")
            raise HTTPException(status_code=500, detail="Database not available")
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        # Provide more specific error information
        error_detail = f"Failed to create task: {str(e)}"
        if "constraint" in str(e).lower():
            error_detail = "Database constraint violation. Check task data."
        elif "connection" in str(e).lower():
            error_detail = "Database connection failed."
        raise HTTPException(status_code=500, detail=error_detail)

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