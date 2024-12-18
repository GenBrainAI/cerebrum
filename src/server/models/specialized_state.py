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
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self,
                 state_type: StateType = StateType.TASK_GENERATION,
                 name: str = "",
                 data: Dict[str, Any] = None,
                 metadata: StateMetadata = None,
                 task_templates: Dict[str, Any] = None,
                 active_tasks: List[str] = None,
                 parent_id: Optional[UUID] = None,
                 id: Optional[UUID] = None):
        super().__init__(
            id=id or uuid4(),
            state_type=state_type,
            name=name,
            data=data or {},
            metadata=metadata or StateMetadata(),
            parent_id=parent_id
        )
        self.task_templates = task_templates or {}
        self.active_tasks = active_tasks or []
        self.last_created_task = None
        self.total_tasks = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation."""
        base_dict = super().dict()
        return {
            **base_dict,
            "task_templates": self.task_templates,
            "active_tasks": self.active_tasks,
            "last_created_task": self.last_created_task,
            "total_tasks": self.total_tasks
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGenerationState':
        """Create state instance from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            state_type=StateType(data["state_type"]),
            name=data["name"],
            data=data.get("data", {}),
            metadata=StateMetadata(**data.get("metadata", {})),
            task_templates=data.get("task_templates", {}),
            active_tasks=data.get("active_tasks", []),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None
        )

class ToolManagementState(SpecializedState):
    """State for tool management processes"""
    tool_templates: Dict[str, Any] = Field(default_factory=dict)
    registered_tools: List[str] = Field(default_factory=list)
    active_tools: List[str] = Field(default_factory=list)
    last_created_tool: Optional[str] = None
    total_tools: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self,
                 state_type: StateType = StateType.TOOL_MANAGEMENT,
                 name: str = "",
                 data: Dict[str, Any] = None,
                 metadata: StateMetadata = None,
                 tool_templates: Dict[str, Any] = None,
                 registered_tools: List[str] = None,
                 active_tools: List[str] = None,
                 parent_id: Optional[UUID] = None,
                 id: Optional[UUID] = None):
        super().__init__(
            id=id or uuid4(),
            state_type=state_type,
            name=name,
            data=data or {},
            metadata=metadata or StateMetadata(),
            parent_id=parent_id
        )
        self.tool_templates = tool_templates or {}
        self.registered_tools = registered_tools or []
        self.active_tools = active_tools or []
        self.last_created_tool = None
        self.total_tools = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation."""
        base_dict = super().dict()
        return {
            **base_dict,
            "tool_templates": self.tool_templates,
            "registered_tools": self.registered_tools,
            "active_tools": self.active_tools,
            "last_created_tool": self.last_created_tool,
            "total_tools": self.total_tools
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolManagementState':
        """Create state instance from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            state_type=StateType(data["state_type"]),
            name=data["name"],
            data=data.get("data", {}),
            metadata=StateMetadata(**data.get("metadata", {})),
            tool_templates=data.get("tool_templates", {}),
            registered_tools=data.get("registered_tools", []),
            active_tools=data.get("active_tools", []),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None
        )

@dataclass
class AgentFrameworkState(SpecializedState):
    """Specialized state for agent framework configuration."""
    active_view: str = "agentic_config"
    selected_agentic: Optional[Dict[str, Any]] = field(default=None)
    frameworks: List[Dict[str, Any]] = field(default_factory=list)
    task_context: Dict[str, Any] = field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, 
                 state_type: StateType = StateType.AGENT_FRAMEWORK,
                 name: str = "",
                 data: Dict[str, Any] = None,
                 metadata: StateMetadata = None,
                 frameworks: List[Dict[str, Any]] = None,
                 task_context: Optional[Dict[str, Any]] = None,
                 parent_id: Optional[UUID] = None,
                 id: Optional[UUID] = None):
        super().__init__(
            id=id or uuid4(),
            state_type=state_type,
            name=name,
            data=data or {},
            metadata=metadata or StateMetadata(),
            parent_id=parent_id
        )
        self.frameworks = frameworks or []
        self.task_context = task_context or {}
        self.active_view = "agentic_config"
        self.selected_agentic = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation."""
        base_dict = super().dict()
        return {
            **base_dict,
            "active_view": self.active_view,
            "selected_agentic": self.selected_agentic,
            "frameworks": self.frameworks,
            "task_context": self.task_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentFrameworkState':
        """Create state instance from dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            state_type=StateType(data["state_type"]),
            name=data["name"],
            data=data.get("data", {}),
            metadata=StateMetadata(**data.get("metadata", {})),
            frameworks=data.get("frameworks", []),
            task_context=data.get("task_context"),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None
        )

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