from pydantic import Field, BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from enum import Enum

from .base_model import BaseModel as CerebrumBaseModel
from .tools_descriptors import ToolMetadata

class Process(str, Enum):
    """Process type for crew execution.
    
    Attributes:
        sequential: Execute tasks in sequence without manager oversight
        hierarchical: Execute tasks with manager oversight and review
    """
    sequential = "sequential"
    hierarchical = "hierarchical"

class ToolModel(BaseModel):
    """Model for tool configuration."""
    name: str
    description: str

class AgentTool(BaseModel):
    """Tool model for CrewAI agents."""
    name: str
    description: Optional[str] = None

class AgentModel(BaseModel):
    """Model for agent configuration."""
    role: str
    goal: str
    backstory: str
    tools: List[AgentTool] = []
    llm_model: Optional[str] = "OpenAIGPT4"
    verbose: bool = True
    allow_delegation: bool = True

    def __init__(self, **data):
        """Initialize with critical search tool instructions added to backstory."""
        # Check if backstory exists and append critical format instructions
        if "backstory" in data:
            critical_instructions = (
                "\n\n⚠️ CRITICAL TOOL INSTRUCTION: When using search tools or SerperDevTool, "
                "you MUST format your parameters as a dictionary with 'search_query' as the key. "
                "Example: {'search_query': 'your search terms'} or {'search_query': 'events in Paris', 'kwargs': {}}. "
                "NEVER pass just the string 'search_query' as a parameter value."
                "\n\nExample correct usage: search({'search_query': 'concerts in New York'})"
                "\nExample INCORRECT usage: search('search_query') <- THIS WILL FAIL"
            )
            data["backstory"] = data["backstory"] + critical_instructions
        super().__init__(**data)

class TaskModel(BaseModel):
    """Model for task configuration."""
    description: str
    expected_output: str
    agent_role: str
    human_input: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ToolSpec(BaseModel):
    name: str
    type: str = "function"

class ToolsetSpec(BaseModel):
    id: str
    name: str

class ObjectToolSpec(BaseModel):
    name: str
    object_type: str  # e.g., "github_tool"

class ToolsProxyCollection(BaseModel):
    toolsets: List[ToolsetSpec] = Field(default_factory=list)
    functions: List[ToolSpec] = Field(default_factory=list)
    objects: List[ObjectToolSpec] = Field(default_factory=list)

class CreateCrewRequest(BaseModel):
    """Request model for creating a crew with process selection."""
    description: str
    process: Process = Process.sequential  # Default to sequential process
    agents: List[AgentModel]
    tasks: List[TaskModel]
    tools_proxy_collection: Optional[ToolsProxyCollection] = None
    allowed_tools: Optional[List[str]] = None  # Add allowed_tools field
    model_config = ConfigDict(arbitrary_types_allowed=True)

@dataclass
class Role:
    """Represents a role with associated capabilities and permissions."""
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

@dataclass
class Agentic:
    """
    Represents an agentic entity with defined roles, capabilities, and configurations.
    An agentic is an agent with specific roles and responsibilities.
    """
    name: str
    description: str
    id: UUID = field(default_factory=uuid4)
    role: Optional[Role] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def set_role(self, name: str, description: str, capabilities: List[str], permissions: List[str]) -> None:
        """Set or update the role of the agentic."""
        self.role = Role(
            name=name,
            description=description,
            capabilities=capabilities,
            permissions=permissions
        )

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update the configuration dictionary."""
        self.config.update(config)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the agentic to a dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "role": {
                "name": self.role.name,
                "description": self.role.description,
                "capabilities": self.role.capabilities,
                "permissions": self.role.permissions
            } if self.role else None,
            "config": self.config
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agentic':
        """Create an Agentic instance from a dictionary."""
        agentic = cls(
            name=data["name"],
            description=data["description"],
        )
        agentic.id = UUID(data["id"]) if isinstance(data["id"], str) else data["id"]
        
        if data.get("role"):
            agentic.set_role(
                name=data["role"]["name"],
                description=data["role"]["description"],
                capabilities=data["role"]["capabilities"],
                permissions=data["role"]["permissions"]
            )
        
        if data.get("config"):
            agentic.config = data["config"]
            
        return agentic

class CrewAIConfig(CerebrumBaseModel):
    """Configuration for CrewAI."""
    id: UUID = Field(default_factory=uuid4)
    create_crew: CreateCrewRequest
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = ConfigDict(arbitrary_types_allowed=True)

class CrewConfiguration(BaseModel):
    """Configuration class for CrewAI setup."""
    agents: List[AgentModel]
    tasks: List[TaskModel]

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary format."""
        return {
            "agents": [agent.model_dump() for agent in self.agents],
            "tasks": [task.model_dump() for task in self.tasks]
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> "CrewConfiguration":
        """Create configuration from dictionary format."""
        return cls(
            agents=[AgentModel.model_validate(agent_data) for agent_data in data["agents"]],
            tasks=[TaskModel.model_validate(task_data) for task_data in data["tasks"]]
        )

