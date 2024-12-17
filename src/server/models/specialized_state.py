from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass, field

class StateType(str, Enum):
    TASK_GENERATION = "task_generation"
    TOOL_MANAGEMENT = "tool_management"
    AGENT_FRAMEWORK = "agent_framework"

class StateMetadata(BaseModel):
    """Metadata for state tracking"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class SpecializedState(BaseModel):
    """Base model for specialized state management"""
    id: UUID = Field(default_factory=uuid4)
    state_type: StateType
    name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: StateMetadata = Field(default_factory=StateMetadata)
    parent_id: Optional[UUID] = None

    @validator('state_type')
    def validate_state_type(cls, v):
        """Validate state type matches the class."""
        expected_type = {
            TaskGenerationState: StateType.TASK_GENERATION,
            ToolManagementState: StateType.TOOL_MANAGEMENT,
            AgentFrameworkState: StateType.AGENT_FRAMEWORK
        }.get(cls)
        
        if expected_type and v != expected_type:
            raise ValueError(f"Invalid state type {v} for {cls.__name__}")
        return v

    async def update(self, data: Dict[str, Any]) -> None:
        """Update state data asynchronously"""
        self.data.update(data)
        self.metadata.updated_at = datetime.now()

class TaskGenerationState(SpecializedState):
    """State for task generation processes"""
    task_templates: Dict[str, Any] = Field(default_factory=dict)
    active_tasks: List[str] = Field(default_factory=list)
    last_created_task: Optional[str] = None
    total_tasks: int = 0
    
class ToolManagementState(SpecializedState):
    """State for tool management processes"""
    tool_templates: Dict[str, Any] = Field(default_factory=dict)
    registered_tools: List[str] = Field(default_factory=list)
    active_tools: List[str] = Field(default_factory=list)
    last_created_tool: Optional[str] = None
    total_tools: int = 0

class AgentFrameworkState(SpecializedState):
    """Specialized state for agent framework configuration."""
    active_view: str = Field(default="agentic_config")
    selected_agentic: Optional[Dict[str, Any]] = Field(default=None)
    frameworks: List[Any] = Field(default_factory=list)
    task_context: Dict[str, Any] = Field(default_factory=dict)

    def get_frameworks(self) -> List[Dict[str, Any]]:
        """Get list of configured frameworks."""
        return self.frameworks

    def add_framework(self, framework: Dict[str, Any]) -> None:
        """Add a new framework configuration."""
        self.frameworks.append(framework)

    def update_task_context(self, task_id: str, manager_id: str) -> None:
        """Update the task context."""
        self.task_context = {
            "task_id": task_id,
            "manager_id": manager_id
        }

    def clear_task_context(self) -> None:
        """Clear the task context."""
        self.task_context = {}

    class Config:
        arbitrary_types_allowed = True