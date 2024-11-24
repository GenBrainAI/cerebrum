import pytest
from unittest.mock import MagicMock, create_autospec
from crewai import Agent, Task, Crew
from crewai_tools import BaseTool
from src.server.controllers.agents_controller import create_crew
from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel, ToolModel
from src.server.controllers.curried_proxy import CurriedProxy
from fastapi import HTTPException
class MockTool(BaseTool):
    name: str = "mock_tool"
    description: str = "A mock tool for testing"

    def _run(self, *args, **kwargs):
        return "Mock tool result"

    async def arun(self, *args, **kwargs):
        return "Mock tool result"

@pytest.mark.asyncio
async def test_create_crew():
    # Create a mock tool
    mock_tool = MockTool()

    # Mock CurriedProxy
    mock_curried_proxy = create_autospec(CurriedProxy)
    mock_curried_proxy.export_to_crewai.return_value = [mock_tool]

    # Create a sample CreateCrewRequest
    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="test_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="Tester"
            )
        ]
    )

    # Call create_crew
    crew = await create_crew(create_crew_request, mock_curried_proxy)

    # Assertions
    assert isinstance(crew, Crew)
    assert len(crew.agents) == 1
    assert isinstance(crew.agents[0], Agent)
    assert crew.agents[0].role == "Tester"
    assert crew.agents[0].goal == "Test the system"
    assert crew.agents[0].backstory == "Experienced QA engineer"
    assert len(crew.tasks) == 1
    assert isinstance(crew.tasks[0], Task)
    assert crew.tasks[0].description == "Run tests"

    # Verify that export_to_crewai was called
    mock_curried_proxy.export_to_crewai.assert_called_once()
    
    # Verify that the agent has the tool
    assert len(crew.agents[0].tools) == 1
    assert isinstance(crew.agents[0].tools[0], BaseTool)
    assert crew.agents[0].tools[0].name == "mock_tool"

@pytest.mark.asyncio
async def test_create_crew_without_proxy():
    """Test creating a crew without a curried proxy"""
    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="test_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="Tester"
            )
        ]
    )

    # Call create_crew without a proxy
    crew = await create_crew(create_crew_request, None)

    # Assertions
    assert isinstance(crew, Crew)
    assert len(crew.agents) == 1
    assert isinstance(crew.agents[0], Agent)
    assert crew.agents[0].role == "Tester"
    assert len(crew.agents[0].tools) == 0  # Should have no tools
    assert len(crew.tasks) == 1
    assert isinstance(crew.tasks[0], Task)
    assert crew.tasks[0].description == "Run tests"

@pytest.mark.asyncio
async def test_create_crew_invalid_agent_role():
    """Test creating a crew with an invalid agent role"""
    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="test_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="NonExistentRole"  # Role that doesn't exist
            )
        ]
    )

    # Test that the appropriate exception is raised
    with pytest.raises(HTTPException) as exc_info:
        await create_crew(create_crew_request, None)
    
    assert exc_info.value.status_code == 400
    assert "Agent role 'NonExistentRole' not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_crew_missing_agent():
    # Create a mock tool
    mock_tool = MockTool()

    # Mock CurriedProxy
    mock_curried_proxy = create_autospec(CurriedProxy)
    mock_curried_proxy.export_to_crewai.return_value = [mock_tool]

    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="test_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="Developer"  # This role doesn't exist
            )
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_crew(create_crew_request, mock_curried_proxy)
        
    exception = exc_info.value
    assert exception.status_code == 400
    assert exception.detail == "Agent role 'Developer' not found."

##### More tests to come

@pytest.mark.asyncio
async def test_create_crew_without_proxy():
    """Test creating a crew without a curried proxy"""
    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="test_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="Tester"
            )
        ]
    )

    # Call create_crew without a proxy
    crew = await create_crew(create_crew_request, None)

    # Assertions
    assert isinstance(crew, Crew)
    assert len(crew.agents) == 1
    assert isinstance(crew.agents[0], Agent)
    assert crew.agents[0].role == "Tester"
    assert len(crew.agents[0].tools) == 0  # Should have no tools
    assert len(crew.tasks) == 1
    assert isinstance(crew.tasks[0], Task)
    assert crew.tasks[0].description == "Run tests"

@pytest.mark.asyncio
async def test_create_crew_with_tools():
    """Test creating a crew with tools properly initialized"""
    # Create a mock tool
    mock_tool = MockTool()

    # Mock CurriedProxy
    mock_curried_proxy = create_autospec(CurriedProxy)
    mock_curried_proxy.export_to_crewai.return_value = [mock_tool]

    create_crew_request = CreateCrewRequest(
        description="Test Crew",
        agents=[
            AgentModel(
                role="Tester",
                goal="Test the system",
                backstory="Experienced QA engineer",
                tools=[ToolModel(name="mock_tool", description="A test tool")]
            )
        ],
        tasks=[
            TaskModel(
                description="Run tests",
                expected_output="Test results",
                agent_role="Tester"
            )
        ]
    )

    # Create the crew
    crew = await create_crew(create_crew_request, mock_curried_proxy)

    # Verify crew creation
    assert isinstance(crew, Crew)
    assert len(crew.agents) == 1
    assert crew.agents[0].role == "Tester"
    
    # Verify tools were properly added
    mock_curried_proxy.export_to_crewai.assert_called_once()
    assert len(crew.agents[0].tools) == 1
    assert isinstance(crew.agents[0].tools[0], BaseTool)
    assert crew.agents[0].tools[0].name == "mock_tool"
