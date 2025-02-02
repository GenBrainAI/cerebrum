"""
Test suite for the agent framework plugin system.
Tests plugin loading, initialization, and execution.
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any
from src.server.plugins.base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.crewai_plugin import CrewAIPlugin, CrewAIPluginConfig

logger = logging.getLogger(__name__)

# Test plugin for verification
class TestPlugin(AgentFrameworkPlugin):
    """Test plugin implementation."""
    
    def __init__(self, config: AgentFrameworkConfig):
        super().__init__(config)
        self.config = config
        self._is_initialized = False
    
    async def initialize(self) -> bool:
        self._is_initialized = True
        return True
    
    async def shutdown(self) -> bool:
        self._is_initialized = False
        return True
    
    async def create_agent(self, config: Dict[str, Any]) -> Any:
        return {"type": "test_agent", "config": config}
    
    async def execute_task(self, agent: Any, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "completed",
            "result": f"Executed {task['name']} with {agent['type']}"
        }
    
    def get_capabilities(self) -> list:
        return ["test_capability"]
        
    @property
    def name(self) -> str:
        return self.config.name
        
    @property
    def version(self) -> str:
        return self.config.version

@pytest.fixture
async def plugin_manager():
    """Create a plugin manager for testing."""
    manager = PluginManager()
    yield manager
    await manager.shutdown_all()

@pytest.fixture
def test_plugin_config():
    """Create a test plugin configuration."""
    return AgentFrameworkConfig(
        name="test_plugin",
        version="1.0.0",
        description="Test plugin for verification"
    )

@pytest.fixture
def crewai_plugin_config():
    """Create a CrewAI plugin configuration."""
    return CrewAIPluginConfig(
        name="crewai",
        version="1.0.0",
        description="CrewAI framework plugin",
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=2000
    )

@pytest.mark.asyncio
async def test_plugin_loading(plugin_manager, test_plugin_config):
    """Test plugin loading and initialization."""
    try:
        logger.info("Testing plugin loading...")
        
        # Create test plugin
        plugin = TestPlugin(test_plugin_config)
        assert not plugin.is_initialized, "Plugin should not be initialized"
        
        # Initialize plugin
        success = await plugin.initialize()
        assert success, "Plugin initialization failed"
        assert plugin.is_initialized, "Plugin should be initialized"
        assert plugin.name == test_plugin_config.name, "Plugin name mismatch"
        assert plugin.version == test_plugin_config.version, "Plugin version mismatch"
        
        logger.info("✅ Plugin loading test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_crewai_plugin_loading(plugin_manager, crewai_plugin_config):
    """Test CrewAI plugin loading and initialization."""
    try:
        logger.info("Testing CrewAI plugin loading...")
        
        # Create CrewAI plugin
        plugin = CrewAIPlugin(crewai_plugin_config)
        assert not plugin.is_initialized, "Plugin should not be initialized"
        
        # Initialize plugin
        success = await plugin.initialize()
        assert success, "Plugin initialization failed"
        assert plugin.is_initialized, "Plugin should be initialized"
        
        # Verify CrewAI specific configuration
        assert plugin.config.settings.get('model') == "gpt-4o-mini", "Incorrect model configuration"
        assert plugin.config.settings.get('temperature') == 0.7, "Incorrect temperature configuration"
        
        # Verify capabilities
        capabilities = plugin.get_capabilities()
        assert "agent_creation" in capabilities, "Missing capability"
        assert "task_execution" in capabilities, "Missing capability"
        assert "llm_integration" in capabilities, "Missing capability"
        
        logger.info("✅ CrewAI plugin loading test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_plugin_execution(plugin_manager, test_plugin_config):
    """Test plugin task execution."""
    try:
        logger.info("Testing plugin execution...")
        
        # Create and initialize plugin
        plugin = TestPlugin(test_plugin_config)
        await plugin.initialize()
        
        # Create test agent
        agent_config = {
            "name": "test_agent",
            "role": "tester"
        }
        agent = await plugin.create_agent(agent_config)
        assert agent["type"] == "test_agent", "Agent creation failed"
        
        # Execute test task
        task = {
            "name": "test_task",
            "description": "Test task execution"
        }
        result = await plugin.execute_task(agent, task)
        assert result["status"] == "completed", "Task execution failed"
        assert "Executed test_task" in result["result"], "Unexpected task result"
        
        logger.info("✅ Plugin execution test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_plugin_manager_operations(plugin_manager, test_plugin_config, crewai_plugin_config):
    """Test plugin manager operations."""
    try:
        logger.info("Testing plugin manager operations...")
        
        # Get plugins directory
        plugins_dir = Path(__file__).parent.parent.parent / "src" / "server" / "plugins"
        
        # Load test plugin
        test_plugin_path = plugins_dir / "test_plugin.py"
        success = await plugin_manager.load_plugin(str(test_plugin_path), test_plugin_config)
        assert success, "Failed to load test plugin"
        
        # Load CrewAI plugin
        crewai_plugin_path = plugins_dir / "crewai_plugin.py"
        success = await plugin_manager.load_plugin(str(crewai_plugin_path), crewai_plugin_config)
        assert success, "Failed to load CrewAI plugin"
        
        # List plugins
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == 2, "Incorrect number of plugins loaded"
        
        # Get specific plugin
        test_plugin = plugin_manager.get_plugin("test_plugin")
        assert test_plugin is not None, "Failed to get test plugin"
        assert test_plugin.is_initialized, "Plugin not initialized"
        
        # Unload plugin
        success = await plugin_manager.unload_plugin("test_plugin")
        assert success, "Failed to unload test plugin"
        
        # Verify plugin was unloaded
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == 1, "Plugin not properly unloaded"
        
        logger.info("✅ Plugin manager operations test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_plugin_error_handling(plugin_manager):
    """Test plugin error handling."""
    try:
        logger.info("Testing plugin error handling...")
        
        # Try to load non-existent plugin
        success = await plugin_manager.load_plugin(
            "non_existent_plugin",
            AgentFrameworkConfig(
                name="invalid",
                version="1.0.0",
                description="Invalid plugin"
            )
        )
        assert not success, "Should fail to load non-existent plugin"
        
        # Try to get non-existent plugin
        plugin = plugin_manager.get_plugin("invalid")
        assert plugin is None, "Should return None for non-existent plugin"
        
        # Try to unload non-existent plugin
        success = await plugin_manager.unload_plugin("invalid")
        assert not success, "Should fail to unload non-existent plugin"
        
        logger.info("✅ Plugin error handling test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise 