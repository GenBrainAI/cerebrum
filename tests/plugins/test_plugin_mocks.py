"""
Tests for plugin system using mocked responses.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.server.plugins.discovery import PluginRegistry
from src.server.plugins.base_plugin import AgentConfig, AgentOutput, AgentRole

# Mock responses for different frameworks
MOCK_CREWAI_RESPONSE = {
    "content": "Created job posting for Software Engineer position...",
    "status": "completed",
    "metadata": {
        "framework": "crewai",
        "agent_role": "writer",
        "model": "gpt-4"
    }
}

MOCK_SMOLAGENTS_RESPONSE = {
    "output": "Retrieved relevant documentation...",
    "output_format": "text",
    "artifacts": [{"type": "code", "content": "def example(): pass"}],
    "tools_used": ["document_retriever", "code_generator"]
}

MOCK_SWARM_RESPONSE = {
    "messages": [
        {"role": "assistant", "content": "Found available flights..."},
        {"role": "user", "content": "Book the first option"},
        {"role": "assistant", "content": "Booking confirmed for flight XY123"}
    ],
    "context_variables": {
        "flight_number": "XY123",
        "departure": "LAX",
        "arrival": "JFK"
    }
}

@pytest.fixture
def mock_plugin_registry():
    """Create a mocked plugin registry."""
    with patch("src.server.plugins.discovery.PluginRegistry") as MockRegistry:
        registry = MockRegistry()
        registry.discover_plugins = AsyncMock(return_value=["job_posting", "rag_assistant", "airline"])
        registry.get_plugin_class = Mock()
        yield registry

@pytest.fixture
def mock_crewai_plugin():
    """Create a mocked CrewAI plugin."""
    plugin = Mock()
    plugin.initialize = AsyncMock(return_value=True)
    plugin.shutdown = AsyncMock(return_value=True)
    plugin.create_agent = AsyncMock(return_value="agent_1")
    plugin.execute_task = AsyncMock(return_value=AgentOutput(**MOCK_CREWAI_RESPONSE))
    plugin.get_capabilities = Mock(return_value=[
        "job_posting_generation",
        "role_analysis",
        "market_research"
    ])
    return plugin

@pytest.fixture
def mock_smolagents_plugin():
    """Create a mocked SmolAgents plugin."""
    plugin = Mock()
    plugin.initialize = AsyncMock(return_value=True)
    plugin.shutdown = AsyncMock(return_value=True)
    plugin.create_agent = AsyncMock(return_value="agent_2")
    plugin.execute_task = AsyncMock(return_value=AgentOutput(
        content=MOCK_SMOLAGENTS_RESPONSE["output"],
        format=MOCK_SMOLAGENTS_RESPONSE["output_format"],
        artifacts=MOCK_SMOLAGENTS_RESPONSE["artifacts"],
        status="completed",
        metadata={"tools_used": MOCK_SMOLAGENTS_RESPONSE["tools_used"]}
    ))
    plugin.get_capabilities = Mock(return_value=[
        "document_retrieval",
        "code_generation"
    ])
    return plugin

@pytest.fixture
def mock_swarm_plugin():
    """Create a mocked Swarm plugin."""
    plugin = Mock()
    plugin.initialize = AsyncMock(return_value=True)
    plugin.shutdown = AsyncMock(return_value=True)
    plugin.create_agent = AsyncMock(return_value="agent_3")
    plugin.execute_task = AsyncMock(return_value=AgentOutput(
        content=MOCK_SWARM_RESPONSE["messages"][-1]["content"],
        status="completed",
        format="text",
        metadata={"context": MOCK_SWARM_RESPONSE["context_variables"]}
    ))
    plugin.get_capabilities = Mock(return_value=[
        "flight_search",
        "booking_assistance"
    ])
    return plugin

@pytest.mark.asyncio
async def test_job_posting_workflow(mock_plugin_registry, mock_crewai_plugin):
    """Test complete job posting workflow with mocked responses."""
    mock_plugin_registry.get_plugin_class.return_value = mock_crewai_plugin
    
    # Initialize plugin
    plugin = mock_crewai_plugin
    assert await plugin.initialize()
    
    # Create agent
    config = AgentConfig(
        role=AgentRole.USER_PROXY,
        model="gpt-4",
        instructions="Create compelling job descriptions",
        tools=[]
    )
    agent_id = await plugin.create_agent(config)
    assert agent_id == "agent_1"
    
    # Execute task
    task = {
        "description": "Create job posting for Senior Engineer",
        "context": {"company": "Tech Corp"}
    }
    result = await plugin.execute_task(agent_id, task)
    
    assert result.status == "completed"
    assert "job posting" in result.content.lower()
    assert result.metadata["framework"] == "crewai"

@pytest.mark.asyncio
async def test_rag_workflow(mock_plugin_registry, mock_smolagents_plugin):
    """Test complete RAG workflow with mocked responses."""
    mock_plugin_registry.get_plugin_class.return_value = mock_smolagents_plugin
    
    # Initialize plugin
    plugin = mock_smolagents_plugin
    assert await plugin.initialize()
    
    # Create agent
    config = AgentConfig(
        role=AgentRole.CODE_AGENT,
        model="gpt-4",
        instructions="Generate code based on documentation",
        tools=[]
    )
    agent_id = await plugin.create_agent(config)
    assert agent_id == "agent_2"
    
    # Execute task
    task = {
        "description": "Generate Python function",
        "context": {"docs": "API documentation"}
    }
    result = await plugin.execute_task(agent_id, task)
    
    assert result.status == "completed"
    assert len(result.artifacts) > 0
    assert result.artifacts[0]["type"] == "code"

@pytest.mark.asyncio
async def test_airline_workflow(mock_plugin_registry, mock_swarm_plugin):
    """Test complete airline booking workflow with mocked responses."""
    mock_plugin_registry.get_plugin_class.return_value = mock_swarm_plugin
    
    # Initialize plugin
    plugin = mock_swarm_plugin
    assert await plugin.initialize()
    
    # Create agent
    config = AgentConfig(
        role=AgentRole.ASSISTANT,
        model="gpt-4",
        instructions="Help with flight booking",
        tools=[]
    )
    agent_id = await plugin.create_agent(config)
    assert agent_id == "agent_3"
    
    # Execute task
    task = {
        "description": "Book flight from LAX to JFK",
        "context": {"date": "2024-06-01"}
    }
    result = await plugin.execute_task(agent_id, task)
    
    assert result.status == "completed"
    assert "XY123" in result.metadata["context"]["flight_number"]

@pytest.mark.asyncio
async def test_error_handling(mock_plugin_registry, mock_crewai_plugin):
    """Test error handling with mocked failures."""
    mock_plugin_registry.get_plugin_class.return_value = mock_crewai_plugin
    
    # Simulate initialization failure
    mock_crewai_plugin.initialize.return_value = False
    plugin = mock_crewai_plugin
    assert not await plugin.initialize()
    
    # Simulate agent creation failure
    mock_crewai_plugin.create_agent.side_effect = Exception("Failed to create agent")
    with pytest.raises(Exception):
        await plugin.create_agent(AgentConfig(
            role=AgentRole.ASSISTANT,
            model="gpt-4",
            instructions="test",
            tools=[]
        ))
    
    # Simulate task execution failure
    mock_crewai_plugin.execute_task.side_effect = Exception("Task execution failed")
    with pytest.raises(Exception):
        await plugin.execute_task("agent_1", {"description": "test"}) 