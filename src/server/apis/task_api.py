from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Response,
    status,
    Query,
)

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
async def delete_task(
    id: int = Path(..., description="ID of the task to delete"),
) -> None:
    try:
        persistence_model.tasks.delete(str(id))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/task/{id}",
    responses={
        200: {"model": Task, "description": "Task found"},
        404: {"model": Error, "description": "Task not found"},
        500: {"model": Error, "description": "Huston we have a problem"},
    },
    tags=["default"],
    summary="Get task by ID",
    response_model_by_alias=True,
)
async def get_task_by_id(
    id: str = Path(..., description="ID of the task to get"),
) -> Task:
    try:
        task = persistence_model.tasks.read(id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task
    except HTTPException as e:
        raise
    except Exception as e:
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
    status: str = Query(None, description="Filter tasksmanagers by status", alias="status"),
    page: int = Query(1, description="Page number for pagination", alias="page"),
    page_size: int = Query(10, description="Number of items per page", alias="pageSize"),
) -> ListTasksManagers:
    try:
        all_tasksmanagers = persistence_model.tasksmanagers.list()
        result_page = ListTasksManagers(tasksmanagers=all_tasksmanagers)
        return result_page
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/tasksmanager/{id}",
    responses={
        200: {"model": TasksManager, "description": "TasksManager requsted by id"},
        400: {"model": Error, "description": "Bad request"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="get tasksmanager details",
    response_model_by_alias=True,
)
async def get_tasksmanager(
    id: str = Path(..., description="ID of the tasksmanager to retrieve"),
) -> TasksManager:
    try:
        return persistence_model.tasksmanagers.read(id)
    except Exception as e:
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
async def post_create_tasksmanager(
    tasksmanager: TasksManager = Body(None, description=""),
) -> TasksManager:
    try:
        tm = await create_tasksmanager(tasksmanager)
        return Response(
            content=tm.json(),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/tasksmanager/{id}",
    responses={
        204: {"description": "TasksManager deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="Delete a tasksmanager",
    response_model_by_alias=True,
)
async def delete_tasksmanager(
    id: int = Path(..., description="ID of the tasksmanager to delete"),
) -> None:
    try:
        persistence_model.tasksmanagers.delete(str(id))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch(
    "/tasksmanager/{id}",
    responses={
        200: {"model": TasksManager, "description": "TasksManager updated"},
        400: {"model": Error, "description": "Bad request"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="Update tasksmanager details",
    response_model_by_alias=True,
)
async def update_tasksmanager(
    id: int = Path(..., description="ID of the tasksmanager to update"),
    tasksmanager: TasksManager = Body(None, description=""),
) -> TasksManager:
    try:
        return persistence_model.tasksmanagers.update(str(id), tasksmanager)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/task/{tasksmanager_id}/{task_id}/run",
    responses = {
        202: {"description": "Run completed successfully."},
        400: {"description": "Invalid input or organization not found."},
    },
    tags=["run"],
    summary="run an tasksmanager task."
  )
async def run_task(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    task_id: str = Path(..., description="ID of the task"),
    run_task_body: RunTask = Body(..., description="Task run information")
    ):
        task = persistence_model.tasks.read(task_id)
        if task is None or task.tasksmanager_id != tasksmanager_id:
            raise HTTPException(status_code=404, detail="Task not found or tasksmanager does not match")

        #Egbert: Add the crew ai runnig if it is exist in the task.abs
        # than we should think to run the tast after that 

        response = await task_runner.completion(tasksmanager_id=tasksmanager_id, task_id=task_id, messages=run_task_body.messages)

        return Response(
            content=response,
            status_code=status.HTTP_202_ACCEPTED,
            media_type="application/json",
        )

@router.patch(
    "/tasksmanager/{id}",
    responses={
        200: {"model": TasksManager, "description": "TasksManager updated"},
        400: {"model": Error, "description": "Bad request"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "TasksManager not found"},
    },
    tags=["default"],
    summary="Update tasksmanager details",
    response_model_by_alias=True,
)

async def update_tasksmanager(
    id: int = Path(..., description="ID of the tasksmanager to update"),
    tasksmanager: TasksManager = Body(None, description=""),
) -> TasksManager:
    try:
        return persistence_model.tasksmanagers.update(str(id), tasksmanager)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


