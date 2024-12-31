from pydantic import Field, BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4

class ToolModel(BaseModel):
    """Model for tool configuration."""
    name: str
    description: str

class AgentModel(BaseModel):
    """Model for agent configuration."""
    role: str
    goal: str
    backstory: str
    tools: List[ToolModel]
    class_tools: Optional[List[ToolModel]] = None
    verbose: bool = True
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class TaskModel(BaseModel):
    """Model for task configuration."""
    description: str
    expected_output: str
    agent_role: str
    depends_on: Optional[List[str]] = None

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
    description: str
    agents: List[AgentModel]
    tasks: List[TaskModel]
    tools_proxy_collection: Optional[ToolsProxyCollection] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class CrewAIConfig(BaseModel):
    id: Optional[str] = Field(alias="id", default=None)
    create_crew: Optional[CreateCrewRequest] = Field(alias="create_crew", default=None)
    created_at: Optional[datetime] = Field(alias="created_at", default=None)
    updated_at: Optional[datetime] = Field(alias="updated_at", default=None)

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

