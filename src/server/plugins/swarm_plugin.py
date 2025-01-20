"""
Swarm plugin implementation.
Integrates OpenAI's Swarm framework with the plugin system.
"""

import logging
from typing import Dict, Any, List, Optional
from swarm import Swarm, Agent as SwarmAgent
from ..plugins.base_plugin import AgentFrameworkPlugin, AgentConfig, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

class SwarmPlugin(AgentFrameworkPlugin):
    """Swarm framework plugin implementation."""
    
    async def initialize(self) -> bool:
        """Initialize Swarm plugin."""
        try:
            self._client = Swarm()
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Swarm plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown Swarm plugin."""
        try:
            self._client = None
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown Swarm plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: AgentConfig) -> Any:
        """Create a Swarm agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Convert tools to Swarm functions
            functions = []
            for tool in config.tools:
                if callable(tool.get("function")):
                    functions.append(tool["function"])

            # Create Swarm agent
            agent = SwarmAgent(
                name=f"agent_{config.role.value}",
                model=config.model,
                instructions=config.instructions,
                functions=functions
            )

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
        """Execute a task using the Swarm agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Prepare messages
            messages = [{"role": "user", "content": task["description"]}]
            
            # Add context if provided
            if context:
                messages.insert(0, {"role": "system", "content": str(context)})

            # Execute task
            response = await self._client.run(
                agent=agent,
                messages=messages,
                context_variables=context or {},
                stream=stream
            )
            
            # Convert result to standardized output
            return AgentOutput(
                content=response.messages[-1]["content"] if response.messages else "",
                status="completed",
                format="text",
                metadata={
                    "framework": "swarm",
                    "agent_name": agent.name,
                    "model": agent.model,
                    "context_variables": response.context_variables
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
            "function_calling",
            "agent_handoff",
            "context_variables",
            "streaming",
            "tool_use"
        ] 