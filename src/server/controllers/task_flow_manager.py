"""
Task Flow Manager

This module provides a TaskFlowManager class for managing and executing
a flat list of tasks with transformations between them.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable, TYPE_CHECKING
from uuid import uuid4
import logging
from pydantic import BaseModel, Field, ConfigDict

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.server.persistence.persistence_model import PersistenceModelBase

from src.server.controllers.prompt_transformer import PromptTransformer, MessageTransformer

# Remove the circular import
# from src.server.controllers.task_runner import TaskRunner

logger = logging.getLogger(__name__)

class TaskFlowStep(BaseModel):
    """
    A step in a task flow, consisting of a task and optional transformations.
    """
    
    task_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    transformer: Optional[PromptTransformer] = None
    pre_execute_hook: Optional[Callable] = None
    post_execute_hook: Optional[Callable] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_duration: Optional[float] = None
    
    # Allow arbitrary types
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def mark_started(self):
        """Mark the step as started."""
        self.status = "started"
        self.started_at = datetime.now()
        
    def mark_completed(self, result: Dict[str, Any]):
        """Mark the step as completed with the given result."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now()
        if self.started_at:
            self.execution_duration = (self.completed_at - self.started_at).total_seconds()
        
    def mark_failed(self, error: str):
        """Mark the step as failed with the given error."""
        self.status = "failed"
        self.error = error
        self.result = {"error": error}
        self.completed_at = datetime.now()
        if self.started_at:
            self.execution_duration = (self.completed_at - self.started_at).total_seconds()


class TaskFlow(BaseModel):
    """
    A flow of tasks with transformations between them.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    tasksmanager_id: str
    steps: List[TaskFlowStep] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    session_id: str = Field(default_factory=lambda: str(uuid4()))

    def add_step(self, step: TaskFlowStep) -> "TaskFlow":
        """
        Add a step to the flow.
        
        Args:
            step: The step to add
            
        Returns:
            The flow instance for chaining
        """
        self.steps.append(step)
        self.updated_at = datetime.now()
        return self
        
    def add_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        transformer: Optional[PromptTransformer] = None
    ) -> "TaskFlow":
        """
        Add a task to the flow.
        
        Args:
            task_id: The ID of the task to add
            name: Optional name for the step
            transformer: Optional transformer for the step
            
        Returns:
            The flow instance for chaining
        """
        step = TaskFlowStep(task_id=task_id, name=name, transformer=transformer)
        return self.add_step(step)
        
    def get_step(self, index: int) -> Optional[TaskFlowStep]:
        """
        Get a step by index.
        
        Args:
            index: The index of the step to get
            
        Returns:
            The step at the given index, or None if the index is out of range
        """
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None
        
    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get the results of all completed steps.
        
        Returns:
            A list of dictionaries with step information and results
        """
        return [
            {
                "task_id": step.task_id,
                "name": step.name,
                "status": step.status,
                "result": step.result,
                "error": step.error,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "execution_duration": step.execution_duration
            }
            for step in self.steps
        ]
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the flow to a dictionary.
        
        Returns:
            A dictionary representation of the flow
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasksmanager_id": self.tasksmanager_id,
            "steps": [
                {
                    "task_id": step.task_id,
                    "name": step.name,
                    "description": step.description,
                    "status": step.status,
                    "has_transformer": step.transformer is not None,
                    "has_pre_execute_hook": step.pre_execute_hook is not None,
                    "has_post_execute_hook": step.post_execute_hook is not None
                }
                for step in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "session_id": self.session_id
        }


class TaskFlowManager:
    """
    Manager for creating and executing task flows.
    """
    
    def __init__(self, persistence_model: 'PersistenceModelBase'):
        """
        Initialize a task flow manager.
        
        Args:
            persistence_model: The persistence model to use
        """
        self.persistence_model = persistence_model
        self.task_runner = None  # Will be set during initialize
        self.flows: Dict[str, TaskFlow] = {}
        
    async def initialize(self):
        """Initialize the task flow manager."""
        # Import TaskRunner here to avoid circular imports
        from src.server.controllers.task_runner import TaskRunner
        
        if self.task_runner is None:
            self.task_runner = TaskRunner(self.persistence_model)
            await self.task_runner.initialize()
        logger.info("TaskFlowManager initialized")
            
    def create_flow(
        self,
        name: str,
        description: Optional[str] = None,
        tasksmanager_id: Optional[str] = None
    ) -> TaskFlow:
        """
        Create a new task flow.
        
        Args:
            name: The name of the flow
            description: Optional description for the flow
            tasksmanager_id: Optional ID of the tasks manager for this flow
            
        Returns:
            The created flow
        """
        flow = TaskFlow(name=name, description=description or "", tasksmanager_id=tasksmanager_id or "")
        # Store in memory dictionary for backward compatibility
        self.flows[flow.id] = flow
        # Save to persistence model
        self.persistence_model.task_flows.create(flow)
        return flow
        
    def get_flow(self, flow_id: str) -> Optional[TaskFlow]:
        """
        Get a flow by ID.
        
        Args:
            flow_id: The ID of the flow to get
            
        Returns:
            The flow, or None if not found
        """
        # First check in-memory dictionary
        if flow_id in self.flows:
            return self.flows[flow_id]
        
        # Then check persistence model
        flow = self.persistence_model.task_flows.read(flow_id)
        if flow:
            # Update in-memory dictionary
            self.flows[flow_id] = flow
        
        return flow

    def update_flow(self, flow: TaskFlow) -> None:
        """
        Update a flow in the persistence model.
        
        Args:
            flow: The flow to update
        """
        # Update in-memory dictionary
        self.flows[flow.id] = flow
        
        # Update persistence model
        try:
            self.persistence_model.task_flows.update(flow.id, flow)
        except Exception as e:
            # If the flow doesn't exist in the persistence model yet, create it
            try:
                self.persistence_model.task_flows.create(flow)
            except Exception as inner_e:
                logger.error(f"Failed to update or create flow {flow.id}: {inner_e}")
                raise

    async def execute_flow(
        self,
        flow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a flow with the given context.
        
        Args:
            flow_id: The ID of the flow to execute
            initial_context: Optional initial context for the flow
            session_id: Optional session ID to use for the flow
            
        Returns:
            A dictionary with the flow results
        """
        flow = self.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow with ID {flow_id} not found")
            
        if session_id:
            flow.session_id = session_id
            
        # Use the TaskRunner's run_flow method to execute the flow
        return await self.task_runner.run_flow(
            flow_id=flow_id,
            initial_context=initial_context,
            session_id=session_id
        )
        
    async def execute_flow_step(
        self,
        flow_id: str,
        step_index: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single step in a flow.
        
        Args:
            flow_id: The ID of the flow containing the step
            step_index: The index of the step to execute
            context: Optional context for the step
            
        Returns:
            A dictionary with the step result
        """
        # Import TaskRunner here if needed
        from src.server.controllers.task_runner import TaskRunner
        
        flow = self.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow with ID {flow_id} not found")
            
        step = flow.get_step(step_index)
        if not step:
            raise ValueError(f"Step with index {step_index} not found in flow {flow_id}")
            
        try:
            # Mark step as started
            step.status = "started"
            step.started_at = datetime.now()
            self.update_flow(flow)
            
            # Get the task for this step
            task = self.persistence_model.tasks.read(step.task_id)
            
            # Prepare the context for this step
            step_context = context.copy() if context else {}
            step_context["flow_id"] = flow_id
            step_context["session_id"] = flow.session_id
            
            # Call pre-execute hook if available
            if step.pre_execute_hook:
                hook_result = step.pre_execute_hook(step_context, None, task)
                if hook_result:
                    step_context.update(hook_result)
            
            # Execute the task
            result = await self.task_runner.run_task(
                tasksmanager_id=flow.tasksmanager_id,
                task_id=step.task_id,
                running_extra_params=step_context
            )
            
            # Call post-execute hook if available
            if step.post_execute_hook:
                hook_result = step.post_execute_hook(result, step_context, task)
                if hook_result:
                    result = hook_result
            
            # Mark step as completed
            step.status = "completed"
            step.result = result
            step.completed_at = datetime.now()
            self.update_flow(flow)
            
            return {
                "step_index": step_index,
                "task_id": step.task_id,
                "name": step.name or task.name,
                "result": result,
                "status": "completed"
            }
            
        except Exception as e:
            # Mark step as failed
            step.status = "failed"
            step.result = {"error": str(e)}
            step.completed_at = datetime.now()
            self.update_flow(flow)
            
            return {
                "step_index": step_index,
                "task_id": step.task_id,
                "name": step.name or "Unknown",
                "error": str(e),
                "status": "failed"
            } 