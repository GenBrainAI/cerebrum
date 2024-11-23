from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Response,
    status,
    Query,
)
from typing import Dict, Any
import logging

from ..models.task import Task
from ..models.list_tasks_managers import ListTasksManagers
from ..models.custom_exceptions import *
from ..models.run_task import RunTask
from ..models.toolset import Toolset
from ..models.tasks_manager import TasksManager
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.task_runner import TaskRunner
from ..models.error import Error
from ..controllers.tasks_controller import create_tasksmanager

router = APIRouter()

persistence_model = PersistenceModelFactory.persistence_model("inmemory")
task_runner = TaskRunner(persistence_model)


@router.post(
    "/task",
    responses={
        201: {"model": Task, "description": "Task session created"},
        400: {"model": Error, "description": "Bad request"},
        500: {"model": Error, "description": "Internal server error"},
    },
    tags=["default"],
    summary="Create a new task session",
    response_model_by_alias=True,
)
async def create_task(
    task: Task = Body(None, description=""),
) -> Task:
    try:
        task_created = persistence_model.tasks.create(task)
        return Response(
            content=task_created.json(),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/task/{id}",
    responses={
        200: {"model": Task, "description": "Task found"},
        404: {"model": Error, "description": "Task not found"},
        500: {"model": Error, "description": "Internal server error"},
    },
    tags=["default"],
    summary="Get task by ID",
    response_model_by_alias=True,
)
async def get_task_by_id(id: str = Path(..., description="ID of the task to get")) -> Task:
    """Get a task by its ID."""
    try:
        task = persistence_model.tasks.read(id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/task",
    responses={
        204: {"description": "Task deleted"},
        404: {"model": Error, "description": "Task not found"},
        500: {"model": Error, "description": "Huston we have a problem"},
    },
    tags=["default"],
    summary="Delete task by ID",
    response_model_by_alias=True,
)
@router.delete(
    "/task/{id}",
    responses={
        204: {"description": "Task deleted"},
        404: {"model": Error, "description": "Task not found"},
        500: {"model": Error, "description": "Internal server error"},
    },
    tags=["default"],
    summary="Delete task by ID",
)
async def delete_task(id: str = Path(..., description="ID of the task to delete")) -> None:
    """Delete a task by its ID."""
    try:
        persistence_model.tasks.delete(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logging.error(f"Error deleting task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/task/{tasksmanager_id}/{task_id}/run")
async def run_task(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    task_id: str = Path(..., description="ID of the task"),
    run_task_body: RunTask = Body(..., description="Task run information"),
) -> Dict[str, Any]:
    """
    Run a task with the specified parameters.
    The task can be either a CrewAI task or a standard task with tools.
    """
    try:
        # Prepare running parameters
        running_extra_params = run_task_body.running_extra_params or {}
        if run_task_body.messages:
            running_extra_params['messages'] = run_task_body.messages
        
        # Run the task using the TaskRunner
        response = await task_runner.run_task(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            running_extra_params=running_extra_params
        )
        
        return response
        
    except ValueError as e:
        logging.error(f"Validation error in run_task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logging.error(f"Error running task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/tasksmanager",
    responses={
        200: {"model": ListTasksManagers, "description": "A list of tasksmanagers"},
        400: {"model": Error, "description": "Bad request"},
        500: {"model": Error, "description": "Internal server error"},
    },
    tags=["default"],
    summary="List all tasksmanagers",
    response_model_by_alias=True,
)
async def list_tasks_managers(
    status: str = Query(None, description="Filter tasksmanagers by status"),
    page: int = Query(1, description="Page number for pagination"),
    page_size: int = Query(10, description="Number of items per page"),
) -> ListTasksManagers:
    """List all task managers with optional filtering and pagination."""
    try:
        all_tasksmanagers = persistence_model.tasksmanagers.list()
        return ListTasksManagers(tasksmanagers=all_tasksmanagers)
    except Exception as e:
        logging.error(f"Error listing task managers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post(
    "/tasksmanager",
    responses={
        201: {"model": TasksManager, "description": "TasksManager created"},
        400: {"model": Error, "description": "Bad request"},
        500: {"model": Error, "description": "Internal server error"},
    },
    tags=["default"],
    summary="Create a new tasksmanager",
    response_model_by_alias=True,
)
async def create_tasksmanager(
    tasksmanager: TasksManager = Body(None, description=""),
) -> TasksManager:
    """Create a new task manager."""
    try:
        created = persistence_model.tasksmanagers.create(tasksmanager)
        return Response(
            content=created.json(),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    except Exception as e:
        logging.error(f"Error creating task manager: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/tasksmanager/{id}",
    responses={
        200: {"model": TasksManager, "description": "TasksManager found"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="Get tasksmanager by ID",
    response_model_by_alias=True,
)
async def get_tasksmanager(
    id: str = Path(..., description="ID of the tasksmanager to retrieve"),
) -> TasksManager:
    """Get a task manager by its ID."""
    try:
        tasksmanager = persistence_model.tasksmanagers.read(id)
        if tasksmanager is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TasksManager not found")
        return tasksmanager
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving task manager: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete(
    "/tasksmanager/{id}",
    responses={
        204: {"description": "TasksManager deleted"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="Delete a tasksmanager",
)
async def delete_tasksmanager(
    id: str = Path(..., description="ID of the tasksmanager to delete"),
) -> None:
    """Delete a task manager by its ID."""
    try:
        persistence_model.tasksmanagers.delete(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logging.error(f"Error deleting task manager: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
