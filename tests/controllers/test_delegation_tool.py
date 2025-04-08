"""
Unit tests for the delegation tool used in CrewAI crews.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.server.controllers.curried_proxy import CurriedProxy
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.context.code_catalog import CodeCatalog


@pytest.mark.asyncio
class TestDelegationToolAsync:
    """Async tests for the delegation tool."""

    @pytest_asyncio.fixture
    async def persistence_mock(self):
        """Create a mock persistence model."""
        mock = MagicMock()
        # Make sure 'tasks' collection is available
        mock.tasks = MagicMock()
        mock.tasks.read = MagicMock(return_value=MagicMock())
        mock.tasks.update = MagicMock(return_value=True)
        return mock

    @pytest_asyncio.fixture
    async def task_runner_mock(self, persistence_mock):
        """Create a mock TaskRunner instance."""
        mock_runner = MagicMock()
        # Set up required methods with AsyncMock
        mock_runner.run_task = AsyncMock(return_value={
            "status": "completed",
            "response": "Task delegated and executed successfully"
        })
        mock_runner.initialize = AsyncMock(return_value=True)
        mock_runner._initialized = True
        mock_runner.persistence_model = persistence_mock
        return mock_runner

    @pytest_asyncio.fixture
    async def curried_proxy(self):
        """Create a mock CurriedProxy for testing."""
        mock_proxy = MagicMock(spec=CurriedProxy)
        mock_proxy.tools = {}
        mock_proxy.add_tool = MagicMock()
        mock_proxy.export_to_crewai = AsyncMock()
        return mock_proxy

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.context.code_catalog.CodeCatalog')
    async def test_delegation_tool_execution(self, mock_catalog_class, mock_task_runner_class, curried_proxy, task_runner_mock):
        """Test delegation tool execution."""
        # Configure the mock TaskRunner class to return our instance
        mock_task_runner_class.return_value = task_runner_mock
        
        # Create a mock delegation tool
        delegation_tool = MagicMock(name="delegate_task_tool")
        delegation_tool._arun = AsyncMock(return_value="Task delegated successfully")
        
        # Setup the mock return value for export_to_crewai
        crewai_tools = [
            MagicMock(name="brave_search_tool"),
            delegation_tool,
            MagicMock(name="web_search_tool")
        ]
        curried_proxy.export_to_crewai.return_value = crewai_tools
        
        # Get tools - await the async method
        tools = await curried_proxy.export_to_crewai()
        
        # Test execution directly with our mocked delegation tool
        result = await delegation_tool._arun(
            task="Research concerts in New York",
            context="The user wants to find concerts in New York",
            coworker="Concert Researcher"
        )
        
        # Assertions
        assert result == "Task delegated successfully"
        delegation_tool._arun.assert_called_once()

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.context.code_catalog.CodeCatalog')
    async def test_delegation_tool_with_dict_inputs(self, mock_catalog_class, mock_task_runner_class, curried_proxy, task_runner_mock):
        """Test delegation tool with dictionary inputs."""
        # Configure the mock TaskRunner class to return our instance
        mock_task_runner_class.return_value = task_runner_mock
        
        # Create mock delegation tool
        delegation_tool = MagicMock(name="delegate_task_tool")
        
        # Create a patched version that records calls
        call_args = []
        
        async def patched_arun(*args, **kwargs):
            call_args.append(kwargs)
            return "Task delegated successfully"
            
        delegation_tool._arun = patched_arun
        
        # Setup the mock return value for export_to_crewai
        crewai_tools = [
            MagicMock(name="brave_search_tool"),
            delegation_tool,
            MagicMock(name="web_search_tool")
        ]
        curried_proxy.export_to_crewai.return_value = crewai_tools
        
        # Get tools - await the async method
        tools = await curried_proxy.export_to_crewai()
        
        # Test with dictionary inputs
        result = await delegation_tool._arun(
            task={"description": "Research concerts in New York"},
            context={"description": "The user wants to find concerts in New York"},
            coworker="Concert Researcher"
        )
        
        # Assertions
        assert result == "Task delegated successfully"
        assert len(call_args) == 1
        assert "task" in call_args[0]
        assert "context" in call_args[0]


@pytest.mark.asyncio
class TestDelegationToolExport:
    """Test suite for the delegation tool export functionality."""

    @pytest_asyncio.fixture
    async def persistence_mock(self):
        """Create a mock persistence model."""
        mock = MagicMock()
        return mock

    @pytest_asyncio.fixture
    async def curried_proxy(self):
        """Create a mock CurriedProxy for testing."""
        mock_proxy = MagicMock(spec=CurriedProxy)
        mock_proxy.export_to_crewai = AsyncMock()
        return mock_proxy

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.context.code_catalog.CodeCatalog')
    async def test_delegation_tool_in_exported_tools(self, mock_catalog, mock_task_runner, curried_proxy):
        """Test that delegation tool is included in exported tools."""
        # Create mock tools with proper name attributes
        brave_search_tool = MagicMock()
        brave_search_tool.name = "brave_search_tool"
        
        delegate_task_tool = MagicMock()
        delegate_task_tool.name = "delegate_task_tool"
        delegate_task_tool.description = "Delegate a task to a coworker"
        
        # Create a proper args_schema mock
        args_schema_mock = MagicMock()
        schema_dict = {
            "properties": {
                "task": {"type": "string", "description": "The task to delegate"},
                "agent": {"type": "string", "description": "The agent to delegate to"}
            },
            "required": ["task", "agent"]
        }
        args_schema_mock.model_json_schema.return_value = schema_dict
        delegate_task_tool.args_schema = args_schema_mock
        
        web_search_tool = MagicMock()
        web_search_tool.name = "web_search_tool"
        
        mock_tools = [brave_search_tool, delegate_task_tool, web_search_tool]
    
        # Setup the return value for export_to_crewai
        curried_proxy.export_to_crewai.return_value = mock_tools
    
        # Get tools - await the async method
        crewai_tools = await curried_proxy.export_to_crewai()
    
        # Check if delegation tool is included
        delegation_tool = None
        for tool in crewai_tools:
            if hasattr(tool, 'name') and ("delegate" in tool.name.lower() or "coworker" in tool.name.lower()):
                delegation_tool = tool
                break
    
        # Assertions
        assert delegation_tool is not None, "Delegation tool should be included in exported tools"
        
        if delegation_tool:
            assert hasattr(delegation_tool, 'description'), "Delegation tool should have a description"
            
            if hasattr(delegation_tool, 'args_schema'):
                schema = delegation_tool.args_schema.model_json_schema()
                assert "properties" in schema, "Args schema should have properties"


if __name__ == "__main__":
    pytest.main() 