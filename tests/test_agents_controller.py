# File: tests/test_agents_controller.py

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
    mock_curried_proxy.get_tool.return_value = mock_tool
    mock_curried_proxy.create_crewai_tool.return_value = mock_tool

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
    assert len(crew.tasks) == 1
    assert isinstance(crew.tasks[0], Task)
    assert crew.tasks[0].description == "Run tests"

    # Verify that get_tool was called
    mock_curried_proxy.get_tool.assert_called_once_with("test_tool")


@pytest.mark.asyncio
async def test_create_crew_missing_agent():
    # Create a mock tool
    mock_tool = MockTool()

    # Mock CurriedProxy
    mock_curried_proxy = create_autospec(CurriedProxy)
    mock_curried_proxy.get_tool.return_value = mock_tool
    mock_curried_proxy.create_crewai_tool.return_value = mock_tool

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
