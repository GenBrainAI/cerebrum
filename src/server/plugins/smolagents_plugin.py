"""
SmolAgents plugin implementation.
Integrates HuggingFace's SmolAgents framework with the plugin system.
"""

import logging
from typing import Dict, Any, List, Optional
from smolagents import CodeAgent, ToolCallingAgent, AgentResponse
from ..plugins.base_plugin import AgentFrameworkPlugin, AgentConfig, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

class SmolAgentsPlugin(AgentFrameworkPlugin):
    """SmolAgents framework plugin implementation."""
    
    async def initialize(self) -> bool:
        """Initialize SmolAgents plugin."""
        try:
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SmolAgents plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown SmolAgents plugin."""
        try:
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown SmolAgents plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: AgentConfig) -> Any:
        """Create a SmolAgents agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Create appropriate agent based on role
            if config.role == AgentRole.CODE_AGENT:
                agent = CodeAgent(
                    model=config.model,
                    instructions=config.instructions,
                    tools=config.tools
                )
            elif config.role == AgentRole.TOOL_AGENT:
                agent = ToolCallingAgent(
                    model=config.model,
                    instructions=config.instructions,
                    tools=config.tools
                )
            else:
                raise ValueError(f"Unsupported role: {config.role}")

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
        """Execute a task using the SmolAgents agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Prepare task input
            task_input = {
                "description": task["description"],
                "context": context or {}
            }
            
            # Execute task
            response: AgentResponse = await agent.execute(
                task_input=task_input,
                stream=stream
            )
            
            # Convert result to standardized output
            return AgentOutput(
                content=response.output,
                status="completed",
                format=response.output_format,
                artifacts=response.artifacts,
                metadata={
                    "framework": "smolagents",
                    "agent_type": agent.__class__.__name__,
                    "model": agent.model,
                    "tools_used": response.tools_used
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
            "code_generation",
            "tool_calling",
            "streaming",
            "artifact_generation",
            "multi_format_output"
        ] 