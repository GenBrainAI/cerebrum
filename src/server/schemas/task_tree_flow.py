"""
Task Tree Flow Schemas

This module provides Pydantic schemas for the Task Tree Flow API.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class TransformerBase(BaseModel):
    """Base schema for transformers."""
    type: str = "prompt"
    instructions: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class TransformerCreate(TransformerBase):
    """Schema for creating a transformer."""
    pass


class TransformerUpdate(TransformerBase):
    """Schema for updating a transformer."""
    pass


class TransformerResponse(TransformerBase):
    """Schema for transformer response."""
    pass


class AggregatorBase(BaseModel):
    """Base schema for aggregators."""
    aggregator_type: str = "all"
    threshold: Optional[float] = None


class AggregatorCreate(AggregatorBase):
    """Schema for creating an aggregator."""
    pass


class AggregatorUpdate(AggregatorBase):
    """Schema for updating an aggregator."""
    pass


class AggregatorResponse(AggregatorBase):
    """Schema for aggregator response."""
    pass


class ExecutionConfigBase(BaseModel):
    """Base schema for execution configurations."""
    strategy: str = "sequential"
    max_concurrency: Optional[int] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    fail_fast: bool = False
    execute_children: bool = True
    propagate_context: bool = True


class ExecutionConfigCreate(ExecutionConfigBase):
    """Schema for creating an execution configuration."""
    pass


class ExecutionConfigUpdate(ExecutionConfigBase):
    """Schema for updating an execution configuration."""
    pass


class ExecutionConfigResponse(ExecutionConfigBase):
    """Schema for execution configuration response."""
    pass


class TaskNodeBase(BaseModel):
    """Base schema for task nodes."""
    task_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    aggregator_type: Optional[str] = "all"
    transformer: Optional[TransformerBase] = None
    execution_config: Optional[ExecutionConfigBase] = None
    children: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class TaskNodeCreate(TaskNodeBase):
    """Schema for creating a task node."""
    pass


class TaskNodeUpdate(BaseModel):
    """Schema for updating a task node."""
    aggregator_type: Optional[str] = None
    transformer: Optional[TransformerBase] = None
    execution_config: Optional[ExecutionConfigBase] = None


class TaskNodeResponse(TaskNodeBase):
    """Schema for task node response."""
    name: str
    description: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


class TaskTreeFlowBase(BaseModel):
    """Base schema for task tree flows."""
    name: str
    description: Optional[str] = None


class TaskTreeFlowCreate(TaskTreeFlowBase):
    """Schema for creating a task tree flow."""
    id: str


class TaskTreeFlowUpdate(BaseModel):
    """Schema for updating a task tree flow."""
    name: Optional[str] = None
    description: Optional[str] = None


class TaskTreeFlowResponse(TaskTreeFlowBase):
    """Schema for task tree flow response."""
    id: str
    tasksmanager_id: str
    nodes: Dict[str, TaskNodeResponse] = Field(default_factory=dict)
    roots: List[str] = Field(default_factory=list)
    execution_groups: Dict[str, List[str]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ExecuteTreeRequest(BaseModel):
    """Schema for executing a tree flow."""
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ExecuteNodeRequest(BaseModel):
    """Schema for executing a node."""
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None 