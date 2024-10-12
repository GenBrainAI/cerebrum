from pydantic import Field
from datetime import datetime
# from autogen import AssistantAgent, UserProxyAgent
# from autogen.agentchat.agent import LLMAgent
# from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
# from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
# from autogen.agentchat.contrib.math_user_proxy_agent import MathUserProxyAgent
from typing import List, Optional

from pydantic import BaseModel
from pydantic import Field


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


# Example JSON configuration for testing
config_json = """
{
    "agents": [
        {
            "name": "Assistant_1",
            "type": "AssistantAgent",
            "llm_config": {
                "timeout": 600,
                "seed": 42,
                "config_list": [
                    {"model": "example_model"}
                ]
            }
        },
        {
            "name": "Assistant_2",
            "type": "AssistantAgent",
            "llm_config": {
                "timeout": 600,
                "seed": 42,
                "config_list": [
                    {"model": "example_model"}
                ]
            }
        },
        {
            "name": "Writer",
            "type": "AssistantAgent",
            "system_message": "You are a professional writer, known for your insightful and engaging articles. You transform complex concepts into compelling narratives.",
            "llm_config": {
                "timeout": 600,
                "seed": 42,
                "config_list": [
                    {"model": "example_model"}
                ]
            }
        },
        {
            "name": "Reviewer",
            "type": "AssistantAgent",
            "system_message": "You are a compliance reviewer, known for your thoroughness and commitment to standards. Your task is to scrutinize content for any harmful elements or regulatory violations, ensuring all materials align with required guidelines. You must review carefully, identify potential issues, and maintain the integrity of the organization. Your role demands fairness, a deep understanding of regulations, and a focus on protecting against harm while upholding a culture of responsibility.",
            "llm_config": {
                "timeout": 600,
                "seed": 42,
                "config_list": [
                    {"model": "example_model"}
                ]
            }
        },
        {
            "name": "User",
            "type": "UserProxyAgent",
            "human_input_mode": "NEVER",
            "is_termination_msg": "lambda x: x.get('content', '').find('TERMINATE') >= 0",
            "code_execution_config": {
                "last_n_messages": 1,
                "work_dir": "tasks",
                "use_docker": false
            }
        }
    ],
    "tasks": [
        {
            "chat_id": 1,
            "recipient": {
                "name": "Assistant_1",
                "type": "AssistantAgent",
                "llm_config": {
                    "timeout": 600,
                    "seed": 42,
                    "config_list": [
                        {"model": "example_model"}
                    ]
                }
            },
            "message": "What are the current stock prices of NVDA and TESLA, and how is the performance over the past month in terms of percentage change?",
            "silent": false,
            "summary_method": "reflection_with_llm"
        },
        {
            "chat_id": 2,
            "prerequisites": [1],
            "recipient": {
                "name": "Assistant_2",
                "type": "AssistantAgent",
                "llm_config": {
                    "timeout": 600,
                    "seed": 42,
                    "config_list": [
                        {"model": "example_model"}
                    ]
                }
            },
            "message": "Investigate possible reasons of the stock performance.",
            "silent": false,
            "summary_method": "reflection_with_llm"
        },
        {
            "chat_id": 3,
            "prerequisites": [1],
            "recipient": {
                "name": "Assistant_1",
                "type": "AssistantAgent",
                "llm_config": {
                    "timeout": 600,
                    "seed": 42,
                    "config_list": [
                        {"model": "example_model"}
                    ]
                }
            },
            "message": "What are the possible future trends for these stocks?",
            "silent": false,
            "summary_method": "reflection_with_llm"
        },
        {
            "chat_id": 4,
            "prerequisites": [1, 2, 3],
            "recipient": {
                "name": "Writer",
                "type": "AssistantAgent",
                "system_message": "You are a professional writer, known for your insightful and engaging articles. You transform complex concepts into compelling narratives.",
                "llm_config": {
                    "timeout": 600,
                    "seed": 42,
                    "config_list": [
                        {"model": "example_model"}
                    ]
                }
            },
            "message": "Develop an engaging blog post using any information provided.",
            "carryover": "I want to include a figure or a table of data in the blogpost."
        }
    ]
}
"""
