"""
Tests for the job posting plugin implementation.
"""

import pytest
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from src.server.plugins.discovery import PluginRegistry
from src.server.plugins.base_plugin import AgentConfig, AgentRole, AgentOutput
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

logger = logging.getLogger(__name__)

@pytest.fixture
async def plugin_registry(tmp_path):
    """Create a plugin registry for testing."""
    # Create temporary directories for plugins
    installed_dir = tmp_path / "installed"
    examples_dir = tmp_path / "examples"
    installed_dir.mkdir()
    examples_dir.mkdir()
    
    # Create job posting plugin directory structure
    plugin_dir = examples_dir / "job_posting"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").touch()  # Make it a Python package
    
    # Create manifest file
    manifest = {
        "name": "job_posting",
        "version": "1.0.0",
        "description": "CrewAI-based job posting generation plugin",
        "entry_point": "plugin.JobPostingPlugin",
        "framework": "crewai",
        "capabilities": [
            "job_posting_generation",
            "role_analysis",
            "market_research"
        ],
        "supported_roles": ["researcher", "writer", "reviewer"],
        "config_schema": {
            "type": "object",
            "properties": {
                "company_domain": {"type": "string"},
                "company_description": {"type": "string"},
                "hiring_needs": {"type": "string"},
                "specific_benefits": {"type": "string"}
            }
        },
        "dependencies": {
            "crewai": "^0.1.0",
            "openai": "^1.0.0"
        }
    }
    
    with open(plugin_dir / "manifest.json", "w") as f:
        import json
        json.dump(manifest, f)
    
    # Create plugin file
    plugin_code = '''"""Job posting plugin implementation."""
from typing import Dict, Any, List, Optional
from src.server.plugins.base_plugin import AgentFrameworkPlugin, AgentConfig, AgentOutput, AgentRole
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

class JobPostingPlugin(AgentFrameworkPlugin):
    """Job posting plugin implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the plugin with configuration."""
        if config is None:
            config = {
                "name": "job_posting",
                "version": "1.0.0",
                "description": "Job posting plugin",
                "settings": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                "enabled": True,
                "priority": 0
            }
        super().__init__(config)
        self._agents = {}
        self._is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        self._is_initialized = True
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self._is_initialized = False
        return True
    
    async def create_agent(self, config: AgentConfig) -> str:
        """Create an agent."""
        if not self._is_initialized:
            raise Exception("Plugin not initialized")
        agent_id = f"agent_{len(self._agents)}"
        self._agents[agent_id] = config
        return agent_id
    
    async def execute_task(self, agent_id: str, task: Dict[str, Any]) -> AgentOutput:
        """Execute a task."""
        if not self._is_initialized:
            raise Exception("Plugin not initialized")
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found")
        return AgentOutput(
            content="Generated job posting",
            status="completed",
            format="text",
            metadata={"framework": "crewai"}
        )
    
    def get_capabilities(self) -> List[str]:
        """Get plugin capabilities."""
        return ["job_posting_generation", "role_analysis", "market_research"]
    
    @property
    def name(self) -> str:
        """Get plugin name."""
        return "job_posting"
    
    @property
    def version(self) -> str:
        """Get plugin version."""
        return "1.0.0"
'''
    
    with open(plugin_dir / "plugin.py", "w") as f:
        f.write(plugin_code)
    
    # Add plugin directory to Python path
    if str(examples_dir) not in sys.path:
        sys.path.insert(0, str(examples_dir))
    
    # Create and initialize registry
    registry = PluginRegistry(
        installed_plugins_dir=str(installed_dir),
        example_plugins_dir=str(examples_dir)
    )
    
    # Discover plugins
    await registry.discover_plugins()
    
    return registry

@pytest.fixture
def job_posting_config():
    """Create a job posting configuration."""
    return {
        "company_domain": "technology",
        "company_description": "A leading AI company",
        "hiring_needs": "Senior Software Engineer",
        "specific_benefits": "Competitive salary, remote work"
    }

@pytest.mark.asyncio
async def test_plugin_discovery(plugin_registry):
    """Test plugin discovery."""
    plugins = plugin_registry.list_plugins()
    assert "job_posting" in plugins
    assert plugin_registry.is_example_plugin("job_posting")

@pytest.mark.asyncio
async def test_plugin_initialization(plugin_registry, job_posting_config):
    """Test plugin initialization."""
    plugin = plugin_registry.get_plugin("job_posting")
    assert plugin is not None
    assert await plugin.initialize()
    assert plugin.is_initialized

@pytest.mark.asyncio
async def test_agent_creation(plugin_registry, job_posting_config):
    """Test agent creation."""
    plugin = plugin_registry.get_plugin("job_posting")
    assert plugin is not None
    await plugin.initialize()
    
    researcher_config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Research job market",
        tools=[]
    )
    researcher_id = await plugin.create_agent(researcher_config)
    assert researcher_id is not None
    
    writer_config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Write job posting",
        tools=[]
    )
    writer_id = await plugin.create_agent(writer_config)
    assert writer_id is not None

@pytest.mark.asyncio
async def test_task_execution(plugin_registry, job_posting_config):
    """Test task execution."""
    plugin = plugin_registry.get_plugin("job_posting")
    assert plugin is not None
    await plugin.initialize()
    
    agent_config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Write job posting",
        tools=[]
    )
    agent_id = await plugin.create_agent(agent_config)
    
    task = {
        "type": "generate_posting",
        "config": job_posting_config
    }
    
    result = await plugin.execute_task(agent_id, task)
    assert result.status == "completed"
    assert result.content == "Generated job posting"
    assert result.metadata["framework"] == "crewai"

@pytest.mark.asyncio
async def test_error_handling(plugin_registry):
    """Test error handling."""
    plugin = plugin_registry.get_plugin("job_posting")
    assert plugin is not None
    
    # Test uninitialized plugin
    with pytest.raises(Exception, match="Plugin not initialized"):
        await plugin.create_agent(AgentConfig(
            role=AgentRole.ASSISTANT,
            model="gpt-4",
            instructions="",
            tools=[]
        ))
    
    # Test invalid agent ID
    await plugin.initialize()
    with pytest.raises(ValueError, match="Agent invalid_id not found"):
        await plugin.execute_task("invalid_id", {})

@pytest.mark.asyncio
async def test_plugin_capabilities(plugin_registry):
    """Test plugin capabilities."""
    plugin = plugin_registry.get_plugin("job_posting")
    assert plugin is not None
    
    capabilities = plugin.get_capabilities()
    assert "job_posting_generation" in capabilities
    assert "role_analysis" in capabilities
    assert "market_research" in capabilities 