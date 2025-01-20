"""
AutoGen plugin implementation.
Integrates Microsoft AutoGen framework with the plugin system.
"""

import logging
from typing import Dict, Any, List, Optional
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ..plugins.base_plugin import AgentFrameworkPlugin, AgentConfig, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

class AutoGenPlugin(AgentFrameworkPlugin):
    """AutoGen framework plugin implementation."""
    
    async def initialize(self) -> bool:
        """Initialize AutoGen plugin."""
        try:
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AutoGen plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown AutoGen plugin."""
        try:
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown AutoGen plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: AgentConfig) -> Any:
        """Create an AutoGen agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Create model client
            model_client = OpenAIChatCompletionClient(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )

            # Create appropriate agent based on role
            if config.role == AgentRole.ASSISTANT:
                agent = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    system_message=config.instructions
                )
            elif config.role == AgentRole.USER_PROXY:
                agent = UserProxyAgent(name="user_proxy")
            else:
                raise ValueError(f"Unsupported agent role: {config.role}")

            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    async def execute_task(
        self,
        agent: Any,
        task: Dict[str, Any],
        stream: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """Execute a task using the AutoGen agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Create a group chat with the agent
            team = RoundRobinGroupChat(
                [agent],
                termination_condition=None  # Add appropriate termination condition
            )

            # Execute task
            result = await team.run_stream(task=task["description"]) if stream else await team.run(task=task["description"])
            
            # Convert result to standardized output
            return AgentOutput(
                content=str(result),
                status="completed",
                format="text",
                metadata={
                    "framework": "autogen",
                    "agent_name": agent.name,
                    "model": getattr(agent, "model_client", None) and agent.model_client.model
                }
            )

        except Exception as e:
            logger.error(f"Failed to execute task: {str(e)}")
            return AgentOutput(
                content="",
                status="error",
                error=str(e),
                format="text"
            )
    
    def get_capabilities(self) -> List[str]:
        """Get list of plugin capabilities."""
        return [
            "assistant_agents",
            "user_proxy_agents",
            "group_chat",
            "streaming",
            "tool_use"
        ] 