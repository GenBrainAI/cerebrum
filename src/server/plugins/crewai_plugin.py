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
    def __init__(self, **data):
        if 'name' not in data:
            data['name'] = 'crewai'
        if 'version' not in data:
            data['version'] = '1.0.0'
        if 'description' not in data:
            data['description'] = 'CrewAI framework plugin'
        if 'settings' not in data:
            data['settings'] = {
                'model': 'gpt-4o-mini',
                'temperature': 0.7,
                'max_tokens': 4000,
                'verbose': True
            }
        super().__init__(**data)

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
            agent_role = config.get('agent_role', None)
            if not agent_role:
                # If no specific role is provided, use the first agent's role
                if crew_config.get('agents'):
                    agent_config = crew_config['agents'][0]
                    agent_role = agent_config.get('role')
                else:
                    raise Exception("No agents defined in create_crew configuration")
            else:
                # Find agent configuration for the specified role
                agent_config = None
                for agent in crew_config.get('agents', []):
                    if agent.get('role') == agent_role:
                        agent_config = agent
                        break

                if not agent_config:
                    # Create default agent configuration
                    agent_config = {
                        'role': agent_role,
                        'goal': f"Execute task as {agent_role}",
                        'backstory': f"An expert agent with role {agent_role}",
                        'tools': []
                    }

            # Convert tool dictionaries to actual tool instances
            tools = []
            from langchain.tools import BaseTool, Tool
            from src.server.tools.tools_catalog import ToolsCatalog
            
            # Get the tools catalog
            tools_catalog = ToolsCatalog()
            
            # Process each tool in the agent configuration
            for tool_dict in agent_config.get('tools', []):
                tool_name = tool_dict.get('name')
                if not tool_name:
                    logger.warning(f"Skipping tool without name: {tool_dict}")
                    continue
                
                # Try to get the tool from the catalog
                try:
                    # Check if the tool exists in the catalog using get_tool method
                    tool_metadata = tools_catalog.get_tool(tool_name)
                    if tool_metadata:
                        # Try to get the tool instance
                        tool_instance = tools_catalog.get_tool_instance(tool_name)
                        if tool_instance:
                            # Check if it's already a BaseTool
                            if isinstance(tool_instance, BaseTool):
                                tools.append(tool_instance)
                                logger.info(f"Added BaseTool from catalog: {tool_name}")
                            else:
                                # Create a Tool wrapper for the instance
                                def tool_func(*args, **kwargs):
                                    return tool_instance(*args, **kwargs)
                                
                                tool_instance = Tool(
                                    name=tool_name,
                                    func=tool_func,
                                    description=tool_dict.get('description', f"Tool {tool_name}")
                                )
                                tools.append(tool_instance)
                                logger.info(f"Created Tool wrapper for: {tool_name}")
                        else:
                            # Create a dummy tool
                            def dummy_tool_func(*args, **kwargs):
                                return f"This is a placeholder for {tool_name}. The actual tool functionality is not available."
                            
                            tool_instance = Tool(
                                name=tool_name,
                                func=dummy_tool_func,
                                description=tool_dict.get('description', f"Tool {tool_name}")
                            )
                            tools.append(tool_instance)
                            logger.info(f"Created dummy tool (no instance): {tool_name}")
                    else:
                        # If not in catalog, create a dummy tool
                        def dummy_tool_func(*args, **kwargs):
                            return f"This is a placeholder for {tool_name}. The actual tool functionality is not available."
                        
                        tool_instance = Tool(
                            name=tool_name,
                            func=dummy_tool_func,
                            description=tool_dict.get('description', f"Tool {tool_name}")
                        )
                        tools.append(tool_instance)
                        logger.info(f"Created dummy tool (not in catalog): {tool_name}")
                except Exception as e:
                    logger.error(f"Error creating tool {tool_name}: {str(e)}")
                    # Continue with other tools
            
            # If no tools were successfully created, add a dummy tool to avoid errors
            if not tools:
                def dummy_tool_func(*args, **kwargs):
                    return "This is a placeholder tool. No actual tools were available."
                
                tools.append(Tool(
                    name="DummyTool",
                    func=dummy_tool_func,
                    description="A placeholder tool when no other tools are available"
                ))
                logger.info("Added fallback dummy tool")

            # Create agent with tools
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=agent_config['backstory'],
                tools=tools,  # Use the instantiated tools
                verbose=self.config.settings.get('verbose', True),
                allow_delegation=False,  # Disable delegation for single-agent tasks
                llm_config={
                    'model': self.config.settings.get('model', 'gpt-4o-mini'),
                    'temperature': self.config.settings.get('temperature', 0.7),
                    'max_tokens': self.config.settings.get('max_tokens', 4000)
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

            logger.info(f"Received task data in plugin: {task}")
            logger.info(f"Task type: {type(task)}")
            
            # Print all attributes of task if it's an object
            if hasattr(task, '__dict__'):
                logger.info(f"Task attributes: {dir(task)}")
                logger.info(f"Task __dict__: {task.__dict__}")
            
            # If task is a dictionary, print all keys
            if isinstance(task, dict):
                logger.info(f"Task keys: {task.keys()}")
                logger.info(f"Task values: {task}")

            # Extract task description and tool info
            description = ""
            input_data = {}
            
            # Handle different task input formats
            if isinstance(task, dict):
                description = task.get('description', '')
                input_data = task.get('input_data', {})
                logger.info(f"Task is a dict, description: {description}")
            elif isinstance(task, str):
                description = task
                logger.info(f"Task is a string: {description}")
            else:
                # Try to convert to string
                description = str(task)
                logger.info(f"Task converted to string: {description}")
            
            logger.info(f"Extracted description: {description}")
            
            # Extract tool request data safely
            tool_name = ""
            tool_description = ""
            
            if isinstance(input_data, dict):
                tool_request = input_data.get('tool_request', {})
                if isinstance(tool_request, dict):
                    tool_name = tool_request.get('name', '')
                    tool_description = tool_request.get('description', '')
            
            logger.info(f"Extracted tool info - name: {tool_name}, description: {tool_description}")

            # Create task with expected output
            # CrewAI Task expects a dictionary with specific fields
            task_data = {
                "description": description,
                "agent": agent,
                "expected_output": "A detailed response to the task",
                "context": [
                    f"Tool name: {tool_name}",
                    f"Tool description: {tool_description}"
                ],
                "config": {}  # Empty config to avoid errors
            }
            
            logger.info(f"Created task_data for CrewAI Task: {task_data}")
            
            # Create the Task object by unpacking the dictionary
            try:
                crewai_task = Task(**task_data)
                logger.info(f"Created CrewAI task: {crewai_task}")
            except Exception as e:
                logger.error(f"Error creating CrewAI task: {str(e)}")
                logger.error(f"Task data: {task_data}")
                # Try with a simpler task data
                simple_task_data = {
                    "description": description,
                    "agent": agent,
                    "expected_output": "A detailed response to the task",
                    "config": {}
                }
                logger.info(f"Trying with simpler task data: {simple_task_data}")
                crewai_task = Task(**simple_task_data)
                logger.info(f"Created CrewAI task with simpler data: {crewai_task}")

            # Create crew with single agent
            crew = Crew(
                agents=[agent],
                tasks=[crewai_task],
                verbose=self.config.settings.get('verbose', True),
                process=Process.sequential
            )
            
            logger.info(f"Created crew with agent: {agent}")

            # Execute task and get result
            try:
                logger.info("Starting task execution...")
                result = crew.kickoff()
                logger.info(f"Task execution completed, raw result: {result}")
                
                # Convert result to string if needed
                if not isinstance(result, str):
                    result = str(result)
                    logger.info(f"Converted result to string: {result}")
                
                logger.info(f"Task execution successful, final result: {result}")
                
                # Return success result with generated tool
                return {
                    "status": "success",
                    "result": result,
                    "generated_tool": {
                        "name": tool_name,
                        "description": result
                    }
                }
            except Exception as task_error:
                logger.error(f"Task execution failed with error: {str(task_error)}")
                return {
                    "status": "failed",
                    "error": str(task_error),
                    "result": None,
                    "generated_tool": None
                }

        except Exception as e:
            logger.error(f"Failed to execute task with error: {str(e)}")
            logger.exception(e)  # Print full traceback
            return {
                "status": "failed",
                "error": str(e),
                "result": None,
                "generated_tool": None
            }
    
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