import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

from src.server.apis.agents_api import initialize_agent_tools
from src.server.models.agent import AgentModel, ToolModel, CreateCrewRequest, TaskModel
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.tools_catalog import (
    ToolsCatalog,
    ToolMetadata,
    ToolType,
    ReturnInfo,
    ParameterInfo,
    tools_catalog
)
from src.server.apis.agents_api import create_crewai

@pytest.fixture
def mock_tools_catalog():
    """Create a mock ToolsCatalog with test tools."""
    test_tool_metadata = ToolMetadata(
        name="TestTool",
        description="A test tool",
        tool_type=ToolType.PYTHON_FUNCTION,
        parameters=[],
        returns=ReturnInfo(
            type_hint="str",
            description="A test return value"
        ),
        original_obj=lambda x: x,
        async_tool=False
    )
    
    # Create a mock for the tools_catalog methods we use
    mock_catalog = Mock()
    mock_catalog.get_tool.return_value = test_tool_metadata
    mock_catalog.get_tool_instance.return_value = lambda x: x
    
    return mock_catalog

@pytest.mark.asyncio
async def test_initialize_agent_tools_successful(mock_tools_catalog):
    """Test successful tool initialization for an agent."""
    agent = AgentModel(
        role="TestAgent",
        goal="Test Goal",
        backstory="Test Backstory",
        tools=[
            ToolModel(name="TestTool", description="Test Description")
        ]
    )
    
    curried_proxy = CurriedProxy()
    
    # Patch the tools_catalog instance methods
    with patch('src.server.apis.agents_api.tools_catalog') as mock_catalog:
        # Set up the mock methods
        mock_catalog.get_tool = mock_tools_catalog.get_tool
        mock_catalog.get_tool_instance = mock_tools_catalog.get_tool_instance
        
        # Test the function
        await initialize_agent_tools(agent, curried_proxy)
        
        # Verify the tool was properly added
        assert "TestTool" in curried_proxy.list_tools()
        mock_catalog.get_tool.assert_called_once_with("TestTool")
        mock_catalog.get_tool_instance.assert_called_once_with("TestTool")

@pytest.mark.asyncio
async def test_initialize_agent_tools_unknown_tool():
    """Test handling of unknown tool requests."""
    agent = AgentModel(
        role="TestAgent",
        goal="Test Goal",
        backstory="Test Backstory",
        tools=[
            ToolModel(name="UnknownTool", description="Test Description")
        ]
    )
    
    curried_proxy = CurriedProxy()
    
    # Patch the tools_catalog instance methods
    with patch('src.server.apis.agents_api.tools_catalog') as mock_catalog:
        mock_catalog.get_tool.return_value = None
        
        # Test that proper exception is raised
        with pytest.raises(HTTPException) as exc_info:
            await initialize_agent_tools(agent, curried_proxy)
        
        assert exc_info.value.status_code == 400
        assert "not found in the catalog" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_initialize_agent_tools_with_class_tools():
    """Test initialization of class-based tools."""
    agent = AgentModel(
        role="TestAgent",
        goal="Test Goal",
        backstory="Test Backstory",
        tools=[],  # Empty list for required tools field
        class_tools=[
            ToolModel(name="TestClassTool", description="Test Class Tool")
        ]
    )
    
    curried_proxy = CurriedProxy()
    
    # Create a mock tool class
    mock_tool_instance = Mock()
    mock_tool_class = Mock(return_value=mock_tool_instance)
    
    # Patch both the ToolFactory class and its instance methods
    with patch('src.server.apis.agents_api.ToolFactory') as MockToolFactory:
        # Setup the mock tool factory instance
        mock_factory_instance = Mock()
        MockToolFactory.return_value = mock_factory_instance
        mock_factory_instance.set_curried_proxy = Mock()
        
        # Register the mock tool
        MockToolFactory.TOOLS = {'TestClassTool': mock_tool_class}
        
        # Test the function
        await initialize_agent_tools(agent, curried_proxy)
        
        # Verify ToolFactory was constructed correctly
        MockToolFactory.assert_called_once_with("TestClassTool", curried_proxy)
        
        # Verify set_curried_proxy was called
        mock_factory_instance.set_curried_proxy.assert_called_once()
        
        # Add debug outputs
        print(f"MockToolFactory call count: {MockToolFactory.call_count}")
        print(f"mock_factory_instance.set_curried_proxy call count: {mock_factory_instance.set_curried_proxy.call_count}")


@pytest.mark.asyncio
async def test_create_crewai_endpoint():
    """Test the CrewAI creation endpoint."""
    
    request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="TestAgent",
                goal="Test Goal",
                backstory="Test Backstory",
                tools=[
                    ToolModel(name="TestTool", description="Test Description")
                ]
            )
        ],
        tasks=[
            TaskModel(
                description="Test Task",
                expected_output="Test Output",
                agent_role="TestAgent"
            )
        ]
    )
    
    # Create mock config with specific ID
    mock_config = Mock()
    mock_config.id = "test-config-id"
    
    # Create mock proxy with specific ID
    mock_proxy = Mock()
    mock_proxy.id = "test-proxy-id"
    
    # Create a mock persistence model with properly configured attributes
    mock_persistence_model = Mock()
    mock_persistence_model.crewai_config = Mock()
    mock_persistence_model.crewai_config.create = Mock(return_value=mock_config)
    mock_persistence_model.curried_proxies = Mock()
    mock_persistence_model.curried_proxies.create = Mock(return_value=mock_proxy)
    
    # Mock the PersistenceModelFactory to return our mock model
    mock_factory = Mock()
    mock_factory._instance = mock_persistence_model
    mock_factory.persistence_model = Mock(return_value=mock_persistence_model)
    
    # Set up all the mocks
    with patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory', mock_factory), \
         patch('src.server.controllers.agents_controller.PersistenceModelFactory', mock_factory), \
         patch('src.server.controllers.agents_controller.create_crew') as mock_create_crew, \
         patch('src.server.apis.agents_api.tools_catalog') as mock_catalog:
        
        # Setup mock catalog
        mock_catalog.get_tool.return_value = ToolMetadata(
            name="TestTool",
            description="A test tool",
            tool_type=ToolType.PYTHON_FUNCTION,
            parameters=[],
            returns=ReturnInfo(
                type_hint="str",
                description="A test return value"
            ),
            original_obj=lambda x: x,
            async_tool=False
        )
        mock_catalog.get_tool_instance.return_value = lambda x: x
        
        # Set create_crew to return None (as it's an async function that we don't need to return anything specific)
        mock_create_crew.return_value = None
        
        # Test the endpoint
        response = await create_crewai(request)
        
        # Verify response
        assert response["message"] == "Crew created"
        assert response["crew_id"] == "test-config-id"
        assert response["curried_proxy_id"] == "test-proxy-id"
        
        # Verify mock calls
        mock_create_crew.assert_called_once()
        mock_persistence_model.crewai_config.create.assert_called_once()
        mock_persistence_model.curried_proxies.create.assert_called_once()
