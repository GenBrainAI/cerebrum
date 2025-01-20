"""
Tests for the job posting plugin implementation.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from src.server.plugins.discovery import PluginRegistry
from src.server.plugins.base_plugin import AgentConfig, AgentRole

@pytest.fixture
async def plugin_registry():
    """Create a plugin registry for testing."""
    registry = PluginRegistry()
    await registry.discover_plugins()
    return registry

@pytest.fixture
def job_posting_config() -> Dict[str, Any]:
    """Sample job posting configuration."""
    return {
        "company_domain": "test.com",
        "company_description": "A test company",
        "hiring_needs": "Software Engineer",
        "specific_benefits": "Health insurance, 401k"
    }

@pytest.mark.asyncio
async def test_plugin_discovery(plugin_registry):
    """Test that the job posting plugin can be discovered."""
    plugins = plugin_registry.list_plugins()
    job_posting = next((p for p in plugins if p.name == "job_posting"), None)
    
    assert job_posting is not None
    assert job_posting.framework == "crewai"
    assert "job_posting_generation" in job_posting.capabilities
    assert "researcher" in job_posting.supported_roles

@pytest.mark.asyncio
async def test_plugin_initialization(plugin_registry):
    """Test plugin initialization."""
    plugin_class = plugin_registry.get_plugin_class("job_posting")
    assert plugin_class is not None
    
    plugin = plugin_class({})
    assert await plugin.initialize() is True
    assert plugin.is_initialized is True

@pytest.mark.asyncio
async def test_agent_creation(plugin_registry):
    """Test creating agents with different roles."""
    plugin_class = plugin_registry.get_plugin_class("job_posting")
    plugin = plugin_class({})
    await plugin.initialize()
    
    # Test researcher role
    researcher_config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Research job market trends",
        tools=[]
    )
    researcher_id = await plugin.create_agent(researcher_config)
    assert researcher_id is not None
    
    # Test writer role
    writer_config = AgentConfig(
        role=AgentRole.USER_PROXY,
        model="gpt-4",
        instructions="Write compelling job descriptions",
        tools=[]
    )
    writer_id = await plugin.create_agent(writer_config)
    assert writer_id is not None

@pytest.mark.asyncio
async def test_task_execution(plugin_registry, job_posting_config):
    """Test executing a job posting task."""
    plugin_class = plugin_registry.get_plugin_class("job_posting")
    plugin = plugin_class(job_posting_config)
    await plugin.initialize()
    
    # Create agent
    agent_config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Create a job posting",
        tools=[]
    )
    agent_id = await plugin.create_agent(agent_config)
    
    # Execute task
    task = {
        "description": "Create a job posting for a Software Engineer position",
        "context": job_posting_config
    }
    result = await plugin.execute_task(agent_id, task)
    
    assert result.status == "completed"
    assert result.content != ""
    assert result.metadata["framework"] == "crewai"

@pytest.mark.asyncio
async def test_error_handling(plugin_registry):
    """Test error handling in the plugin."""
    plugin_class = plugin_registry.get_plugin_class("job_posting")
    plugin = plugin_class({})
    
    # Test uninitialized plugin
    with pytest.raises(Exception):
        await plugin.create_agent(AgentConfig(
            role=AgentRole.ASSISTANT,
            model="gpt-4",
            instructions="test",
            tools=[]
        ))
    
    # Test invalid agent ID
    await plugin.initialize()
    with pytest.raises(ValueError):
        await plugin.execute_task("invalid_id", {"description": "test"})

@pytest.mark.asyncio
async def test_plugin_capabilities(plugin_registry):
    """Test plugin capabilities reporting."""
    plugins = plugin_registry.get_plugins_by_capability("job_posting_generation")
    assert "job_posting" in plugins
    
    plugins = plugin_registry.get_plugins_by_framework("crewai")
    assert "job_posting" in plugins 