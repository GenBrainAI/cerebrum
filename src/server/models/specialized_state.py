from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
from uuid import UUID, uuid4

class StateType(str, Enum):
    TASK_GENERATION = "task_generation"
    TOOL_GENERATION = "tool_generation"
    AGENTIC_FRAMEWORK = "agentic_framework"

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
            ToolGenerationState: StateType.TOOL_GENERATION,
            AgenticFrameworkState: StateType.AGENTIC_FRAMEWORK
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
    
class ToolGenerationState(SpecializedState):
    """State for tool generation processes"""
    tool_templates: Dict[str, Any] = Field(default_factory=dict)
    registered_tools: List[str] = Field(default_factory=list)

class AgenticFrameworkState(SpecializedState):
    """State for agentic framework configuration"""
    framework_config: Dict[str, Any] = Field(default_factory=dict)
    active_agents: List[str] = Field(default_factory=list) 