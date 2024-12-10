from typing import Optional, List, Dict
from fastapi import APIRouter, Path, Body, HTTPException, Query
from fastapi.responses import JSONResponse
from uuid import UUID

from ..context.context_provider import ContextProvider

router = APIRouter()
context_provider = ContextProvider()

@router.patch(
    "/task/{task_id}/context/config",
    summary="Update task context configuration"
)
async def update_task_context_config(
    task_id: str = Path(..., description="ID of the task"),
    use_context: Optional[bool] = Body(None, description="Whether to use context"),
    inherit_manager_context: Optional[bool] = Body(None, description="Whether to use manager context")
):
    """Update task's context configuration."""
    try:
        updated = await context_provider.update_task_context_config(
            task_id=task_id,
            use_context=use_context,
            inherit_manager_context=inherit_manager_context
        )
        
        if updated:
            return {"message": "Context configuration updated successfully"}
        raise HTTPException(status_code=404, detail="Task context not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/task/{task_id}/context/config",
    summary="Get task context configuration"
)
async def get_task_context_config(
    task_id: str = Path(..., description="ID of the task")
):
    """Get task's context configuration."""
    try:
        task_context = context_provider.task_context_manager.get_task_context(task_id)
        if not task_context:
            raise HTTPException(status_code=404, detail="Task context not found")
            
        return {
            "use_context": task_context.use_context,
            "inherit_manager_context": task_context.inherit_manager_context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/task/{task_id}/contexts",
    summary="Get all contexts for a task"
)
async def get_task_contexts(
    task_id: str = Path(..., description="ID of the task"),
    query: Optional[str] = Query(None, description="Search query for context"),
    context_types: Optional[List[str]] = Query(None, description="Filter by context types"),
    limit: int = Query(5, description="Maximum number of contexts to return")
):
    """Get all contexts associated with a task."""
    try:
        contexts = await context_provider.get_task_contexts(
            task_id=task_id,
            query=query,
            context_types=context_types,
            limit=limit
        )
        return contexts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/task/{task_id}/context",
    summary="Add context to task"
)
async def add_task_context(
    task_id: str = Path(..., description="ID of the task"),
    type: str = Body(..., description="Context type (vector, knowledge, system)"),
    source_id: str = Body(..., description="ID of the context source"),
    priority: int = Body(0, description="Context priority"),
    metadata: Optional[Dict] = Body(None, description="Additional metadata")
):
    """Add a new context reference to a task."""
    try:
        context_ref = await context_provider.add_context_to_task(
            task_id=task_id,
            type=type,
            source_id=source_id,
            priority=priority,
            metadata=metadata
        )
        return context_ref
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/task/{task_id}/context/{context_id}",
    summary="Remove context from task"
)
async def remove_task_context(
    task_id: str = Path(..., description="ID of the task"),
    context_id: UUID = Path(..., description="ID of the context reference")
):
    """Remove a context reference from a task."""
    try:
        task_context = context_provider.task_context_manager.get_task_context(task_id)
        if not task_context:
            raise HTTPException(status_code=404, detail="Task context not found")
            
        if task_context.remove_context(context_id):
            return {"message": "Context removed successfully"}
        raise HTTPException(status_code=404, detail="Context reference not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/task/{task_id}/context/{context_id}",
    summary="Update context reference"
)
async def update_task_context_reference(
    task_id: str = Path(..., description="ID of the task"),
    context_id: UUID = Path(..., description="ID of the context reference"),
    priority: Optional[int] = Body(None, description="New priority"),
    metadata: Optional[Dict] = Body(None, description="Updated metadata")
):
    """Update a context reference's priority or metadata."""
    try:
        updated = await context_provider.update_task_context(
            task_id=task_id,
            context_id=context_id,
            priority=priority,
            metadata=metadata
        )
        
        if updated:
            return {"message": "Context reference updated successfully"}
        raise HTTPException(status_code=404, detail="Context reference not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
