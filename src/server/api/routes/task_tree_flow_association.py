from fastapi import APIRouter, Depends, HTTPException, Path
from src.server.persistence.dependencies import get_persistence_model

router = APIRouter(tags=["Task Tree Flow Association"])

@router.post("/{tasksmanager_id}/task/{task_id}/associate_tree_flow/{tree_flow_id}")
async def associate_task_with_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    task_id: str = Path(..., description="ID of the task"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    persistence_model=Depends(get_persistence_model)
):
    """Associate a task with a tree flow."""
    # Check if task exists
    task = persistence_model.tasks.read(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if task belongs to the specified tasks manager
    if task.tasksmanager_id != tasksmanager_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Task {task_id} does not belong to tasks manager {tasksmanager_id}"
        )
    
    # Associate task with tree flow
    task.tree_flow_id = tree_flow_id
    persistence_model.tasks.update(task_id, task)
    
    return {
        "message": f"Task {task_id} associated with tree flow {tree_flow_id}",
        "task_id": task_id,
        "tree_flow_id": tree_flow_id
    }

@router.post("/{tasksmanager_id}/task/{task_id}/disassociate_tree_flow")
async def disassociate_task_from_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    task_id: str = Path(..., description="ID of the task"),
    persistence_model=Depends(get_persistence_model)
):
    """Disassociate a task from its tree flow."""
    # Check if task exists
    task = persistence_model.tasks.read(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check if task belongs to the specified tasks manager
    if task.tasksmanager_id != tasksmanager_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Task {task_id} does not belong to tasks manager {tasksmanager_id}"
        )
    
    # Check if task is associated with a tree flow
    if not task.tree_flow_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Task {task_id} is not associated with any tree flow"
        )
    
    # Store the tree flow ID for the response
    tree_flow_id = task.tree_flow_id
    
    # Disassociate task from tree flow
    task.tree_flow_id = None
    persistence_model.tasks.update(task_id, task)
    
    return {
        "message": f"Task {task_id} disassociated from tree flow {tree_flow_id}",
        "task_id": task_id,
        "previous_tree_flow_id": tree_flow_id
    } 