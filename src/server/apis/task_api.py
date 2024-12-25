from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Response,
    status,
    Query,
)
from typing import Dict, Any, List, Optional
import logging

from ..models.task import Task
from ..models.list_tasks_managers import ListTasksManagers
from ..models.custom_exceptions import *
from ..models.run_task import RunTask
from ..models.tasks_manager import TasksManager
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.task_runner import TaskRunner
from ..models.error import Error
from ..controllers.tasks_tree_controller import (
    TaskTreeManager, ExecutionConfig,
    ExecutionStrategy
)
from pydantic import BaseModel

router = APIRouter()

# Keep global persistence model for backward compatibility
persistence_model = PersistenceModelFactory.persistence_model("inmemory")

#TODO: should be part of the persistence model
tasksmanager_trees: Dict[str, TaskTreeManager] = {}

# Additional request models for tree operations
class TaskTreeRelation(BaseModel):
    parent_id: str
    child_id: str
    execution_strategy: str = ExecutionStrategy.SEQUENTIAL.value

    def get_strategy(self) -> ExecutionStrategy:
        """Get the execution strategy enum"""
        return ExecutionStrategy(self.execution_strategy)

class TreeExecutionConfig(BaseModel):
    strategy: str = ExecutionStrategy.SEQUENTIAL.value
    execute_children: bool = True
    propagate_context: bool = True
    max_retries: int = 3
    timeout: float = 60.0

    def to_execution_config(self) -> ExecutionConfig:
        """Convert to ExecutionConfig with proper enum handling"""
        return ExecutionConfig(
            strategy=ExecutionStrategy(self.strategy),
            execute_children=self.execute_children,
            propagate_context=self.propagate_context,
            max_retries=self.max_retries,
            timeout=self.timeout
        )

class TreeOperationError(Exception):
    """Custom exception for tree operations"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

async def get_task_runner():
    """Dependency to get initialized task runner."""
    # Use the global persistence model to maintain consistency
    task_runner = TaskRunner(persistence_model)
    await task_runner.initialize()  # Initialize context provider
    return task_runner

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
    If the task is part of a tree, it will execute according to the tree configuration
    while maintaining the tasksmanager's context and configuration.
    """
    try:
        # Initialize task runner with context
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()
        
        # Check if task is part of a tree for this tasksmanager
        tree_manager = tasksmanager_trees.get(tasksmanager_id)
        if tree_manager and task_id in tree_manager.nodes:
            node = tree_manager.nodes[task_id]
            
            # Merge tasksmanager context with run context
            context = run_task_body.running_extra_params or {}
            context.update({
                "tasksmanager_id": tasksmanager_id,
                "messages": run_task_body.messages if run_task_body.messages else []
            })
            
            # Get task and wrap it in executor
            task = persistence_model.tasks.read(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Update node's task with executor
            node.task = task_runner.wrap_task(task)
            
            # Execute as part of tree
            result = await node.run(context)
            return {
                "result": result,
                "tree_execution": True,
                "execution_stats": node.get_execution_stats()
            }
        
        # Regular task execution
        running_extra_params = run_task_body.running_extra_params or {}
        if run_task_body.messages:
            running_extra_params['messages'] = run_task_body.messages
        
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

# Modified tree operation endpoints
@router.post("/tasksmanager/{tasksmanager_id}/task/{task_id}/tree/root")
async def set_task_as_root(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    task_id: str = Path(..., description="ID of the task to set as root"),
) -> Dict[str, str]:
    """Set an existing task as the root of a task tree within a tasksmanager."""
    try:
        # Initialize task runner
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()

        # Verify tasksmanager exists
        tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise TreeOperationError(
                message="TasksManager not found",
                details={"tasksmanager_id": tasksmanager_id}
            )

        # Get task from persistence and verify it belongs to this manager
        task = persistence_model.tasks.read(task_id)
        if not task:
            raise TreeOperationError(
                message="Task not found",
                details={"task_id": task_id}
            )
        if task.tasksmanager_id != tasksmanager_id:
            raise TreeOperationError(
                message="Task doesn't belong to this manager",
                details={
                    "task_id": task_id,
                    "task_manager_id": task.tasksmanager_id,
                    "requested_manager_id": tasksmanager_id
                }
            )
        
        # Get or create tree manager for this tasksmanager
        if tasksmanager_id not in tasksmanager_trees:
            tasksmanager_trees[tasksmanager_id] = TaskTreeManager()
        tree_manager = tasksmanager_trees[tasksmanager_id]
        
        # Check if task is already in another tree
        if task_id in tree_manager.nodes:
            raise TreeOperationError(
                message="Task is already part of a tree",
                details={"task_id": task_id}
            )
        
        # Create node with wrapped task and set as root
        task_executor = task_runner.wrap_task(task)
        node = tree_manager.create_node(task_executor)
        try:
            tree_manager.set_as_root(task_id)
        except Exception as e:
            raise TreeOperationError(
                message="Failed to set task as root",
                details={"error": str(e)}
            )
        
        return {
            "status": "success",
            "tasksmanager_id": tasksmanager_id,
            "root_id": task_id
        }
    except TreeOperationError as e:
        logging.error(f"Tree operation error: {e.message}", extra=e.details)
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "details": e.details}
        )
    except Exception as e:
        logging.error(f"Unexpected error setting task as root: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )

@router.post("/tasksmanager/{tasksmanager_id}/task/tree/relation")
async def add_task_relation(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    relation: TaskTreeRelation = Body(..., description="Task relationship details"),
) -> Dict[str, str]:
    """Add a parent-child relationship between tasks within a tasksmanager."""
    try:
        # Initialize task runner
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()

        # Verify tasksmanager exists
        tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise TreeOperationError(
                message="TasksManager not found",
                details={"tasksmanager_id": tasksmanager_id}
            )

        # Get tree manager for this tasksmanager
        tree_manager = tasksmanager_trees.get(tasksmanager_id)
        if not tree_manager:
            raise TreeOperationError(
                message="No task tree exists for this manager",
                details={"tasksmanager_id": tasksmanager_id}
            )

        # Verify both tasks exist and belong to this manager
        parent_task = persistence_model.tasks.read(relation.parent_id)
        child_task = persistence_model.tasks.read(relation.child_id)
        
        if not parent_task or not child_task:
            raise TreeOperationError(
                message="One or both tasks not found",
                details={
                    "parent_id": relation.parent_id,
                    "child_id": relation.child_id,
                    "parent_exists": bool(parent_task),
                    "child_exists": bool(child_task)
                }
            )
        
        if parent_task.tasksmanager_id != tasksmanager_id:
            raise TreeOperationError(
                message="Parent task doesn't belong to this manager",
                details={
                    "parent_id": relation.parent_id,
                    "parent_manager_id": parent_task.tasksmanager_id,
                    "requested_manager_id": tasksmanager_id
                }
            )
            
        if child_task.tasksmanager_id != tasksmanager_id:
            raise TreeOperationError(
                message="Child task doesn't belong to this manager",
                details={
                    "child_id": relation.child_id,
                    "child_manager_id": child_task.tasksmanager_id,
                    "requested_manager_id": tasksmanager_id
                }
            )
        
        # Create nodes if they don't exist in tree
        if relation.parent_id not in tree_manager.nodes:
            parent_executor = task_runner.wrap_task(parent_task)
            tree_manager.create_node(parent_executor)
        if relation.child_id not in tree_manager.nodes:
            child_executor = task_runner.wrap_task(child_task)
            tree_manager.create_node(child_executor)
        
        # Add relationship
        try:
            tree_manager.add_child(relation.parent_id, relation.child_id)
        except Exception as e:
            raise TreeOperationError(
                message="Failed to add child to parent",
                details={
                    "parent_id": relation.parent_id,
                    "child_id": relation.child_id,
                    "error": str(e)
                }
            )
        
        # Configure execution strategy
        try:
            parent_node = tree_manager.nodes[relation.parent_id]
            parent_node.execution_config.strategy = relation.get_strategy()
        except Exception as e:
            raise TreeOperationError(
                message="Failed to configure execution strategy",
                details={
                    "parent_id": relation.parent_id,
                    "strategy": relation.get_strategy().value,
                    "error": str(e)
                }
            )
        
        return {
            "status": "success",
            "tasksmanager_id": tasksmanager_id,
            "parent_id": relation.parent_id,
            "child_id": relation.child_id
        }
    except TreeOperationError as e:
        logging.error(f"Tree operation error: {e.message}", extra=e.details)
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "details": e.details}
        )
    except Exception as e:
        logging.error(f"Unexpected error adding task relation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )

@router.post("/tasksmanager/{tasksmanager_id}/task/{task_id}/tree/config")
async def configure_task_execution(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    task_id: str = Path(..., description="ID of the task to configure"),
    config: TreeExecutionConfig = Body(..., description="Execution configuration"),
) -> Dict[str, Any]:
    """Configure execution parameters for a task in the tree."""
    try:
        # Verify tasksmanager exists
        tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise TreeOperationError(
                message="TasksManager not found",
                details={"tasksmanager_id": tasksmanager_id}
            )

        # Get tree manager for this tasksmanager
        tree_manager = tasksmanager_trees.get(tasksmanager_id)
        if not tree_manager:
            raise TreeOperationError(
                message="No task tree exists for this manager",
                details={"tasksmanager_id": tasksmanager_id}
            )

        node = tree_manager.nodes.get(task_id)
        if not node:
            raise TreeOperationError(
                message="Task not found in tree",
                details={
                    "task_id": task_id,
                    "available_nodes": list(tree_manager.nodes.keys())
                }
            )
        
        # Update execution configuration using the conversion method
        try:
            node.execution_config = config.to_execution_config()
        except Exception as e:
            raise TreeOperationError(
                message="Failed to update execution configuration",
                details={
                    "task_id": task_id,
                    "config": config.dict(),
                    "error": str(e)
                }
            )
        
        return {
            "status": "success",
            "tasksmanager_id": tasksmanager_id,
            "task_id": task_id,
            "config": {
                "strategy": node.execution_config.strategy.value,
                "execute_children": node.execution_config.execute_children,
                "propagate_context": node.execution_config.propagate_context,
                "max_retries": node.execution_config.max_retries,
                "timeout": node.execution_config.timeout
            }
        }
    except TreeOperationError as e:
        logging.error(f"Tree operation error: {e.message}", extra=e.details)
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "details": e.details}
        )
    except Exception as e:
        logging.error(f"Unexpected error configuring task execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )

@router.get("/tasksmanager/{tasksmanager_id}/task/{task_id}/tree/status")
async def get_task_tree_status(
    tasksmanager_id: str = Path(..., description="ID of the tasksmanager"),
    task_id: str = Path(..., description="ID of the task"),
) -> Dict[str, Any]:
    """Get the execution status and structure of a task tree."""
    try:
        # Verify tasksmanager exists
        tasksmanager = persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise HTTPException(status_code=400, detail={"message": "TasksManager not found"})

        # Get tree manager for this tasksmanager
        tree_manager = tasksmanager_trees.get(tasksmanager_id)
        if not tree_manager:
            raise HTTPException(status_code=400, detail={"message": "No task tree exists for this manager"})

        node = tree_manager.nodes.get(task_id)
        if not node:
            raise HTTPException(status_code=400, detail={"message": "Task not found in tree"})
        
        def get_node_info(node):
            return {
                "id": node.task.id,
                "name": node.task.name,
                "status": node.state.status.value,
                "children": [get_node_info(child) for child in node.children],
                "execution_stats": node.get_execution_stats(),
                "tasksmanager_config": {
                    "model": tasksmanager.model,
                    "toolsets": [ts for ts in tasksmanager.toolsets] if tasksmanager.toolsets else []
                }
            }
        
        return get_node_info(node)
    except HTTPException as he:
        logging.error(f"HTTP error in get_task_tree_status: {he.detail}")
        raise he
    except Exception as e:
        logging.error(f"Error getting task tree status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})
