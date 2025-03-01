"""
Task Tree Flow Models

This module provides models for the Task Tree Flow feature.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class TaskStatus(str, Enum):
    """Status of a task node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStrategy(str, Enum):
    """Strategy for executing child tasks."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PARALLEL_WITH_LIMIT = "parallel_with_limit"


class TaskNodeState(BaseModel):
    """State of a task node."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    transformation_applied: bool = False
    transformation_details: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    
    def __getitem__(self, key: str) -> Any:
        """Make the state subscriptable."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"TaskNodeState has no attribute '{key}'")
    
    def start_execution(self) -> None:
        """Mark the task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete_execution(self, result: str) -> None:
        """Mark the task as completed."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
    
    def fail_execution(self, error: str) -> None:
        """Mark the task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def record_transformation(self, original: str, transformed: str) -> None:
        """Record transformation details."""
        self.transformation_applied = True
        self.transformation_details = {
            "original": original,
            "transformed": transformed,
            "timestamp": datetime.now().isoformat()
        }


class ExecutionConfig(BaseModel):
    """Configuration for task execution."""
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    max_concurrency: Optional[int] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    fail_fast: bool = False
    execute_children: bool = True
    propagate_context: bool = True


class TaskTreeFlowNode(BaseModel):
    """Node in a task tree flow."""
    task_id: str
    name: str
    description: Optional[str] = None
    aggregator_type: Union[str, Dict[str, Any]] = "all"
    transformer: Optional[Dict[str, Any]] = None
    execution_config: Optional[Dict[str, Any]] = None
    children: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    state: Optional[Dict[str, Any]] = None


class TaskTreeFlow(BaseModel):
    """Task tree flow model."""
    id: str
    name: str
    description: Optional[str] = None
    tasksmanager_id: str
    nodes: Dict[str, TaskTreeFlowNode] = Field(default_factory=dict)
    roots: List[str] = Field(default_factory=list)
    execution_groups: Dict[str, List[str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_roots(self) -> List[TaskTreeFlowNode]:
        """Get all root nodes."""
        return [self.nodes[root_id] for root_id in self.roots if root_id in self.nodes] 