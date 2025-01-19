import pytest
from unittest.mock import Mock, patch, PropertyMock
from fastapi import HTTPException
from crewai_tools import WebsiteSearchTool, SerperDevTool, FileReadTool

from src.server.apis.agents_api import initialize_agent_tools
from src.server.models.agent import AgentModel, ToolModel, CreateCrewRequest, TaskModel
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.agent import CrewAIConfig
from src.server.tools.tools_catalog import (
    ToolMetadata,
    ToolType,
    ReturnInfo,
    tools_catalog
)
from src.server.apis.agents_api import create_crewai

@pytest.fixture(autouse=True)
def cleanup_tools():
    """Cleanup fixture that runs automatically before and after each test."""
    tools_catalog.reset()
    yield
    tools_catalog.reset()

@pytest.fixture(autouse=True)
def register_crewai_tools():
    """Register CrewAI tools before running tests."""
    website_tool = WebsiteSearchTool()
    serper_tool = SerperDevTool()
    file_read_tool = FileReadTool()
    tools_catalog.register_ai_tool(website_tool, "WebsiteSearchTool")
    tools_catalog.register_ai_tool(serper_tool, "SerperDevTool")
    tools_catalog.register_ai_tool(file_read_tool, "FileReadTool")
    yield

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
    mock_catalog.list_tools.return_value = {"TestTool", "TestTool.method1", "TestTool.method2"}
    
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
    
    # Create a set of available tools including our test tool
    available_tools = {"TestTool", "TestTool.method1", "TestTool.method2"}
    
    # Patch the tools_catalog instance methods
    with patch('src.server.apis.agents_api.tools_catalog') as mock_catalog:
        # Set up the mock methods
        mock_catalog.get_tool = mock_tools_catalog.get_tool
        mock_catalog.get_tool_instance = mock_tools_catalog.get_tool_instance
        mock_catalog.list_tools.return_value = available_tools
        
        # Test the function
        await initialize_agent_tools(agent, curried_proxy)
        
        # Verify the tool was properly added
        mock_catalog.get_tool.assert_called_once_with("TestTool")
        mock_catalog.get_tool_instance.assert_called_once_with("TestTool")
        assert "TestTool" in curried_proxy.list_tools()

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
    
    # Patch both the ToolFactory class and tools_catalog
    # Note the updated import path for ToolFactory
    with patch('src.server.tools.tool_factory.ToolFactory') as MockToolFactory, \
         patch('src.server.apis.agents_api.tools_catalog') as mock_catalog:
        
        # Setup the mock tool factory
        mock_factory_instance = Mock()
        MockToolFactory.return_value = mock_factory_instance
        mock_factory_instance.set_curried_proxy = Mock()
        
        # Set up ToolFactory.TOOLS as a class attribute
        MockToolFactory.TOOLS = {'TestClassTool': mock_tool_class}
        
        # Setup mock catalog
        mock_catalog.list_tools.return_value = {"TestClassTool"}
        
        # Test the function
        await initialize_agent_tools(agent, curried_proxy)
        
        # Verify ToolFactory was constructed correctly
        MockToolFactory.assert_called_once_with("TestClassTool", curried_proxy)
        mock_factory_instance.set_curried_proxy.assert_called_once()
        
        # Add some debug prints
        print(f"MockToolFactory.call_count: {MockToolFactory.call_count}")
        print(f"mock_factory_instance.set_curried_proxy.call_count: {mock_factory_instance.set_curried_proxy.call_count}")


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

    # Create mock proxy
    mock_proxy = Mock()
    mock_proxy.id = "test-proxy-id"
    type(mock_proxy).id = PropertyMock(return_value="test-proxy-id")

    # Create mock config with fixed ID
    mock_config = Mock()
    mock_config.id = "test-config-id"
    type(mock_config).id = PropertyMock(return_value="test-config-id")

    # Set up patches
    with patch('src.server.apis.agents_api.PersistenceModelFactory') as mock_factory_class, \
         patch('src.server.apis.agents_api.create_crew') as mock_create_crew, \
         patch('src.server.apis.agents_api.tools_catalog') as mock_catalog, \
         patch('src.server.apis.agents_api.persistence_model') as mock_persistence_model:  # Add this line

        # Setup mock catalog with available tools
        mock_catalog.list_tools.return_value = {"TestTool"}
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

        # Mock the create_crew function
        mock_create_crew.return_value = Mock()

        # Configure the persistence model mocks
        mock_persistence_model.crewai_config.create.return_value = mock_config
        mock_persistence_model.curried_proxies.create.return_value = mock_proxy

        # Run test and verify results
        response = await create_crewai(request)

        # Verify response
        assert response["message"] == "Crew created"
        assert response["crew_id"] == "test-config-id"
        assert response["curried_proxy_id"] == "test-proxy-id"
        assert response["context_enhanced"] is False

        # Verify the correct calls were made
        mock_persistence_model.crewai_config.create.assert_called_once()
        mock_persistence_model.curried_proxies.create.assert_called_once()
        mock_create_crew.assert_called_once()


@pytest.mark.asyncio
async def test_agent_tool_name_validation():
    """Test that incorrect tool names are properly caught and reported."""
    request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="TestAgent",
                goal="Test Goal",
                backstory="Test Backstory",
                tools=[
                    ToolModel(name="SeperDevTool", description="Incorrectly spelled tool")  # Intentional typo
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

    with pytest.raises(HTTPException) as exc_info:
        await create_crewai(request)
    
    # Verify the error message contains helpful information
    error_msg = str(exc_info.value.detail)
    assert exc_info.value.status_code == 400
    assert "SeperDevTool" in error_msg
    assert "SerperDevTool" in error_msg  # Should suggest the correct spelling
    assert "Did you mean" in error_msg

    # Test with completely invalid tool name
    request.agents[0].tools[0].name = "NonExistentTool"
    with pytest.raises(HTTPException) as exc_info:
        await create_crewai(request)
    
    error_msg = str(exc_info.value.detail)
    assert exc_info.value.status_code == 400
    assert "NonExistentTool" in error_msg
    assert "Available tools" in error_msg  # Should list available tools
