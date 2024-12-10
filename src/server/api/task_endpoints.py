from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from src.server.context.context_provider import ContextProvider
from src.server.controllers.task_runner import TaskRunner
from src.server.models.task_models import ExecuteTasksRequest

router = APIRouter()

@router.post("/tasks/execute")
async def execute_task_sequence(
    request: ExecuteTasksRequest,
    context_provider: ContextProvider = Depends(get_context_provider),
    task_runner: TaskRunner = Depends(get_task_runner)
):
    """Execute a sequence of tasks with context"""
    try:
        # Prepare initial context
        initial_context = {
            "input_data": request.input_data,
            "metadata": request.metadata
        }
        
        # Enhance context
        enhanced_context = await context_provider.enhance_task_context(
            request.task_ids[0],
            initial_context
        )
        
        # Execute tasks
        responses = await task_runner.run_sequential_tasks(
            request.task_ids,
            enhanced_context
        )
        
        return {
            "status": "success",
            "responses": responses
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Task execution failed: {str(e)}"
        ) 