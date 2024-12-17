from pydantic import Field
from datetime import datetime
# from autogen import AssistantAgent, UserProxyAgent
# from autogen.agentchat.agent import LLMAgent
# from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
# from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
# from autogen.agentchat.contrib.math_user_proxy_agent import MathUserProxyAgent
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic import Field

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

class ToolModel(BaseModel):
    name: str
    description: str

class AgentModel(BaseModel):
    role: str
    goal: str
    backstory: str
    tools: List[ToolModel]
    class_tools: Optional[List[ToolModel]] = None


class TaskModel(BaseModel):
    description: str
    expected_output: str
    agent_role: str


class CreateCrewRequest(BaseModel):
    description: str
    agents: List[AgentModel]
    tasks: List[TaskModel]
    tools_proxy_collection: Optional[ToolsProxyCollection] = None


class CrewAIConfig(BaseModel):
    id: Optional[str] = Field(alias="id", default=None)
    create_crew: Optional[CreateCrewRequest] = Field(alias="create_crew", default=None)
    created_at: Optional[datetime] = Field(alias="created_at", default=None)
    updated_at: Optional[datetime] = Field(alias="updated_at", default=None)


# Accepted file formats for that can be stored in
# a vector database instance
# from autogen.retrieve_utils import TEXT_FORMATS


# config_list = [
#     {"model": "gpt-4", "api_key": os.environ.get("OPENAI_API_KEY"), "api_type": "openai"},
# ]

# # Enum for agent types
# class AgentType(str, Enum):
#     ASSISTANT_AGENT = "AssistantAgent"
#     USER_PROXY_AGENT = "UserProxyAgent"
#     RETRIEVE_ASSISTANT_AGENT = "RetrieveAssistantAgent"
#     RETRIEVE_USER_PROXY_AGENT = "RetrieveUserProxyAgent"
#     MATH_USER_PROXY_AGENT = "MathUserProxyAgent"

# # Pydantic models for configurations
# class LLMConfig(BaseModel):
#     timeout: int
#     seed: int
#     config_list: List[Dict]

# class CodeExecutionConfig(BaseModel):
#     use_docker: bool
#     last_n_messages: Optional[int] = None
#     work_dir: Optional[str] = None

# # Base agent model
# class BaseAgent(BaseModel):
#     name: str
#     type: AgentType

# # Specific agent models
# class RetrieveAssistantAgent(BaseAgent):
#     llm_config: Optional[Union[Dict, Literal[False]]] = None
#     system_message: Optional[str] = None

# class RetrieveUserProxyAgent(BaseAgent):
#     human_input_mode: str
#     is_termination_msg: Optional[str] = None
#     code_execution_config: CodeExecutionConfig

# class MathUserProxyAgent(RetrieveUserProxyAgent):
#     pass

# # Union type for agents
# Agent = Union[
#     RetrieveAssistantAgent,
#     RetrieveUserProxyAgent,
#     MathUserProxyAgent
# ]

# # Chat task model
# class ChatTask(BaseModel):
#     chat_id: int
#     recipient: BaseAgent
#     message: str
#     silent: Optional[bool] = None
#     summary_method: Optional[str] = None
#     prerequisites: Optional[List[int]] = None
#     carryover: Optional[Union[str, List[str]]] = None

# class GroupChat(BaseModel):
#     agents: List[BaseAgent]
#     messages: List[Dict[str, Any]]
#     max_round: int

# class GroupChatManager(BaseModel):
#     groupchat: GroupChat
#     llm_config: LLMConfig

# class AutogenConfig(BaseModel):
#     agents: List[Agent]
#     tasks: List[ChatTask]
#     groupchat: Optional[GroupChat] = None
#     groupchat_manager: Optional[GroupChatManager] = None

# # Helper function to parse agents
# def create_agent(agent_data: Dict) -> Agent:
#     agent_type = AgentType(agent_data.pop("type"))
#     if agent_type == AgentType.ASSISTANT_AGENT:
#         return RetrieveAssistantAgent(**agent_data)
#     elif agent_type == AgentType.USER_PROXY_AGENT:
#         return RetrieveUserProxyAgent(**agent_data)
#     elif agent_type == AgentType.RETRIEVE_ASSISTANT_AGENT:
#         return RetrieveAssistantAgent(**agent_data)
#     elif agent_type == AgentType.RETRIEVE_USER_PROXY_AGENT:
#         return RetrieveUserProxyAgent(**agent_data)
#     elif agent_type == AgentType.MATH_USER_PROXY_AGENT:
#         return MathUserProxyAgent(**agent_data)
#     else:
#         raise ValueError(f"Unsupported agent type: {agent_type}")

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

