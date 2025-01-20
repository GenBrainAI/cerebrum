"""
Job Posting plugin implementation using CrewAI.
Demonstrates how to wrap a CrewAI-based workflow in the plugin system.
"""

import logging
from typing import Dict, Any, List, Optional
from crewai import Crew, Agent, Task
from ..plugins.base_plugin import AgentFrameworkPlugin, AgentConfig, AgentOutput, AgentRole

logger = logging.getLogger(__name__)

class JobPostingPlugin(AgentFrameworkPlugin):
    """Job Posting plugin using CrewAI framework."""
    
    async def initialize(self) -> bool:
        """Initialize Job Posting plugin."""
        try:
            self._agents = {}
            self._tasks = {}
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Job Posting plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown Job Posting plugin."""
        try:
            self._agents = {}
            self._tasks = {}
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown Job Posting plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: AgentConfig) -> Any:
        """Create a CrewAI agent for job posting."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Map roles to job posting specific roles
            role_mapping = {
                AgentRole.ASSISTANT: "researcher",
                AgentRole.USER_PROXY: "writer",
                AgentRole.TOOL_AGENT: "reviewer"
            }

            # Create CrewAI agent
            agent = Agent(
                role=role_mapping.get(config.role, "assistant"),
                goal=config.instructions,
                backstory="Expert in job posting creation",
                llm_model=config.model,
                tools=config.tools,
                verbose=True
            )

            # Store agent for later use
            agent_id = f"{config.role.value}_{len(self._agents)}"
            self._agents[agent_id] = agent
            return agent_id

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
        """Execute a job posting task using CrewAI."""
        try:
            if not self._is_initialized:
                raise Exception("Plugin not initialized")

            # Get agent instance
            agent_instance = self._agents.get(agent)
            if not agent_instance:
                raise ValueError(f"Agent {agent} not found")

            # Create CrewAI task
            crew_task = Task(
                description=task["description"],
                agent=agent_instance,
                context=context or {}
            )

            # Create and run crew
            crew = Crew(
                agents=[agent_instance],
                tasks=[crew_task],
                verbose=True
            )

            # Execute task
            result = crew.kickoff()
            
            # Convert result to standardized output
            return AgentOutput(
                content=str(result),
                status="completed",
                format="text",
                metadata={
                    "framework": "crewai",
                    "agent_role": agent_instance.role,
                    "model": agent_instance.llm_model
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
            "job_posting_generation",
            "role_analysis",
            "market_research",
            "content_writing",
            "multi_agent_collaboration"
        ]

    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0" 