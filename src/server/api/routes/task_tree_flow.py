"""
Task Tree Flow API Routes

This module provides API endpoints for managing task tree flows with transformation capabilities.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path

from src.server.schemas.task_tree_flow import (
    TaskTreeFlowCreate, TaskTreeFlowUpdate, TaskTreeFlowResponse,
    TaskNodeCreate, TaskNodeUpdate, TaskNodeResponse,
    TransformerCreate, TransformerUpdate,
    AggregatorCreate, AggregatorUpdate,
    ExecutionConfigCreate, ExecutionConfigUpdate,
    ExecuteTreeRequest, ExecuteNodeRequest
)
from src.server.controllers.task_tree_flow import TaskTreeFlowManager
from src.server.controllers.prompt_transformer import PromptTransformer
from src.server.models.task_tree_flow import ExecutionConfig, TaskTreeFlow
from src.server.persistence.dependencies import get_persistence_model

router = APIRouter(prefix="/tasksmanager", tags=["task_tree_flow"])


@router.post("/{tasksmanager_id}/tree_flow", response_model=TaskTreeFlowResponse)
async def create_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow: TaskTreeFlowCreate = Body(..., description="Tree flow to create"),
    persistence_model=Depends(get_persistence_model)
):
    """Create a new task tree flow."""
    # Check if tasks manager exists
    tasks_manager = persistence_model.tasksmanagers.read(tasksmanager_id)
    if not tasks_manager:
        raise HTTPException(status_code=404, detail=f"Tasks manager {tasksmanager_id} not found")
    
    # Create tree flow model
    tree_flow_model = TaskTreeFlow(
        id=tree_flow.id,
        name=tree_flow.name,
        description=tree_flow.description,
        tasksmanager_id=tasksmanager_id,
        nodes={},
        roots=[],
        execution_groups={}
    )
    
    # Save to persistence model
    persistence_model.collection("tree_flows").create(tree_flow_model)
    
    return tree_flow_model


@router.get("/{tasksmanager_id}/tree_flow/{tree_flow_id}", response_model=TaskTreeFlowResponse)
async def get_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    persistence_model=Depends(get_persistence_model)
):
    """Get a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    return tree_flow


@router.put("/{tasksmanager_id}/tree_flow/{tree_flow_id}", response_model=TaskTreeFlowResponse)
async def update_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    tree_flow_update: TaskTreeFlowUpdate = Body(..., description="Tree flow update"),
    persistence_model=Depends(get_persistence_model)
):
    """Update a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Update fields
    if tree_flow_update.name is not None:
        tree_flow.name = tree_flow_update.name
    if tree_flow_update.description is not None:
        tree_flow.description = tree_flow_update.description
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return tree_flow


@router.delete("/{tasksmanager_id}/tree_flow/{tree_flow_id}")
async def delete_tree_flow(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    persistence_model=Depends(get_persistence_model)
):
    """Delete a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Delete from persistence model
    persistence_model.collection("tree_flows").delete(tree_flow_id)
    
    return {"message": f"Tree flow {tree_flow_id} deleted"}


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node", response_model=TaskNodeResponse)
async def create_node(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    node: TaskNodeCreate = Body(..., description="Node to create"),
    persistence_model=Depends(get_persistence_model)
):
    """Create a node in a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if task exists
    task = persistence_model.tasks.read(node.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {node.task_id} not found")
    
    # Create node
    tree_node = tree_flow.add_node(
        task_id=node.task_id,
        name=node.name or task.name,
        description=node.description or task.description,
        aggregator_type=node.aggregator_type,
        transformer=node.transformer,
        execution_config=node.execution_config
    )
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return tree_node


@router.put("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}", response_model=TaskNodeResponse)
async def update_node(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    node_update: TaskNodeUpdate = Body(..., description="Node update"),
    persistence_model=Depends(get_persistence_model)
):
    """Update a node in a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Update node
    node = tree_flow.nodes[task_id]
    if node_update.name is not None:
        node.name = node_update.name
    if node_update.description is not None:
        node.description = node_update.description
    if node_update.aggregator_type is not None:
        node.aggregator_type = node_update.aggregator_type
    if node_update.transformer is not None:
        node.transformer = node_update.transformer
    if node_update.execution_config is not None:
        node.execution_config = node_update.execution_config
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return node


@router.delete("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}")
async def delete_node(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    persistence_model=Depends(get_persistence_model)
):
    """Delete a node from a task tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Remove node
    tree_flow.remove_node(task_id)
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return {"message": f"Node {task_id} deleted from tree flow {tree_flow_id}"}


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/relationship")
async def add_relationship(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    parent_id: str = Query(..., description="ID of the parent task"),
    child_id: str = Query(..., description="ID of the child task"),
    persistence_model=Depends(get_persistence_model)
):
    """Add a parent-child relationship between nodes."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if nodes exist
    if parent_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {parent_id} not found in tree flow {tree_flow_id}")
    if child_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {child_id} not found in tree flow {tree_flow_id}")
    
    # Add relationship
    tree_flow.add_relationship(parent_id, child_id)
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return {"message": f"Relationship added between {parent_id} and {child_id}"}


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/dependency")
async def add_dependency(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Query(..., description="ID of the dependent task"),
    dependency_id: str = Query(..., description="ID of the dependency task"),
    persistence_model=Depends(get_persistence_model)
):
    """Add a dependency relationship between nodes."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if nodes exist
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    if dependency_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {dependency_id} not found in tree flow {tree_flow_id}")
    
    # Add dependency
    tree_flow.add_dependency(task_id, dependency_id)
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return {"message": f"Dependency added between {task_id} and {dependency_id}"}


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}/transformer", response_model=Dict)
async def set_transformer(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    transformer: TransformerCreate = Body(..., description="Transformer to set"),
    persistence_model=Depends(get_persistence_model)
):
    """Set a transformer for a node."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Set transformer
    tree_flow.nodes[task_id].transformer = transformer
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return {"message": f"Transformer set for node {task_id}"}


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}/aggregator", response_model=str)
async def set_aggregator(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    aggregator: AggregatorCreate = Body(..., description="Aggregator to set"),
    persistence_model=Depends(get_persistence_model)
):
    """Set an aggregator for a node."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Set aggregator
    tree_flow.nodes[task_id].aggregator_type = aggregator.aggregator_type
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return aggregator.aggregator_type


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}/execution_config", response_model=Dict)
async def set_execution_config(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    execution_config: ExecutionConfigCreate = Body(..., description="Execution config to set"),
    persistence_model=Depends(get_persistence_model)
):
    """Set an execution configuration for a node."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Set execution config
    tree_flow.nodes[task_id].execution_config = execution_config.dict()
    
    # Save to persistence model
    persistence_model.collection("tree_flows").update(tree_flow_id, tree_flow)
    
    return execution_config.dict()


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/execute", response_model=Dict[str, str])
async def execute_tree(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    request: ExecuteTreeRequest = Body(..., description="Execution request"),
    persistence_model=Depends(get_persistence_model)
):
    """Execute the entire tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Create manager
    manager = TaskTreeFlowManager(None, persistence_model)
    await manager.initialize()
    
    # Create from model
    manager.create_from_model(tree_flow_id)
    
    # Execute tree
    result = await manager.execute_tree(request.context)
    
    # Update the tree flow in the persistence model
    updated_tree = manager.to_model()
    updated_tree.id = tree_flow_id  # Preserve the original ID
    persistence_model.collection("tree_flows").update(tree_flow_id, updated_tree)
    
    return result


@router.post("/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{task_id}/execute", response_model=str)
async def execute_node(
    tasksmanager_id: str = Path(..., description="ID of the tasks manager"),
    tree_flow_id: str = Path(..., description="ID of the tree flow"),
    task_id: str = Path(..., description="ID of the task"),
    request: ExecuteNodeRequest = Body(..., description="Execution request"),
    persistence_model=Depends(get_persistence_model)
):
    """Execute a specific node in the tree flow."""
    # Check if tree flow exists
    tree_flow = persistence_model.collection("tree_flows").read(tree_flow_id)
    if not tree_flow:
        raise HTTPException(status_code=404, detail=f"Tree flow {tree_flow_id} not found")
    
    # Check if node exists
    if task_id not in tree_flow.nodes:
        raise HTTPException(status_code=404, detail=f"Node {task_id} not found in tree flow {tree_flow_id}")
    
    # Create manager
    manager = TaskTreeFlowManager(None, persistence_model)
    await manager.initialize()
    
    # Create from model
    manager.create_from_model(tree_flow_id)
    
    # Execute node
    result = await manager.execute_node(task_id, request.context)
    
    # Update the tree flow in the persistence model
    updated_tree = manager.to_model()
    updated_tree.id = tree_flow_id  # Preserve the original ID
    persistence_model.collection("tree_flows").update(tree_flow_id, updated_tree)
    
    return result


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