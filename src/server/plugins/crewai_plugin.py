"""
CrewAI plugin implementation.
Integrates CrewAI framework with the plugin system.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from src.server.plugins.base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig
from src.server.models.agent import CrewAIConfig
from src.server.tools.tools_catalog import ToolsCatalog

logger = logging.getLogger(__name__)

class CrewAIPluginConfig(AgentFrameworkConfig):
    """Configuration for the CrewAI plugin."""
    model: str = Field(default="gpt-4", description="Model to use for agents")
    temperature: float = Field(default=0.7, description="Temperature for model responses")
    max_tokens: int = Field(default=4000, description="Maximum tokens for model responses")
    verbose: bool = Field(default=True, description="Whether to enable verbose logging")

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

class CrewAIPlugin(AgentFrameworkPlugin):
    """CrewAI framework plugin implementation."""
    
    def __init__(self, config: CrewAIPluginConfig):
        super().__init__(config)
        self.config = config
        self._crews: Dict[str, Crew] = {}
    
    @property
    def name(self) -> str:
        """Get CrewAI plugin name."""
        return "crewai"
    
    async def initialize(self) -> bool:
        """Initialize CrewAI plugin."""
        try:
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize CrewAI plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown CrewAI plugin."""
        try:
            self._crews.clear()
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown CrewAI plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: Dict[str, Any]) -> Any:
        """Create a CrewAI agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Extract agent configuration from CrewAI config
            crew_config = config.get('create_crew')
            if not crew_config:
                raise Exception("Missing create_crew configuration")

            # Find agent configuration for the task
            agent_role = config.get('agent_role')
            agent_config = None
            for agent in crew_config.get('agents', []):
                if agent.get('role') == agent_role:
                    agent_config = agent
                    break

            if not agent_config:
                raise Exception(f"Agent role '{agent_role}' not found in configuration")

            # Create agent with tools
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=agent_config['backstory'],
                tools=agent_config.get('tools', []),
                llm_config={
                    'model': self.config.model,
                    'temperature': self.config.temperature,
                    'max_tokens': self.config.max_tokens
                }
            )
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    async def execute_task(self, agent: Any, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using the CrewAI agent."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Create crew with single agent
            crew = Crew(
                agents=[agent],
                tasks=[
                    Task(
                        description=task['description'],
                        agent=agent
                    )
                ],
                verbose=self.config.verbose
            )

            # Execute task
            result = await crew.run()
            
            return {
                "status": "completed",
                "result": result,
                "generated_tool": {
                    "name": task.get('input_data', {}).get('tool_request', {}).get('name', ''),
                    "description": str(result)
                }
            }

        except Exception as e:
            logger.error(f"Failed to execute task: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this plugin."""
        return [
            "agent_creation",
            "task_execution",
            "llm_integration",
            "Tool integration",
            "Multi-agent collaboration"
        ]
    
    @property
    def version(self) -> str:
        """Get CrewAI plugin version."""
        return "1.0.0" 