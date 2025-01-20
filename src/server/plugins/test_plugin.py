"""Test plugin implementation for plugin system testing."""

import logging
from typing import Dict, Any, List
from src.server.plugins.base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

logger = logging.getLogger(__name__)

class TestPlugin(AgentFrameworkPlugin):
    """Test plugin implementation."""
    
    def __init__(self, config: AgentFrameworkConfig):
        super().__init__(config)
        self._is_initialized = False
        self._config = config

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def version(self) -> str:
        return self._config.version
    
    async def initialize(self) -> bool:
        """Initialize the test plugin."""
        try:
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize test plugin: {str(e)}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the test plugin."""
        try:
            self._is_initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown test plugin: {str(e)}")
            return False
    
    async def create_agent(self, config: Dict[str, Any]) -> Any:
        """Create a test agent."""
        return {"type": "test_agent", "config": config}
    
    async def execute_task(self, agent: Any, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test task."""
        return {
            "status": "completed",
            "result": f"Executed {task.get('name', 'unknown')} with {agent['type']}"
        }
    
    def get_capabilities(self) -> List[str]:
        """Get test plugin capabilities."""
        return ["test_capability"] 