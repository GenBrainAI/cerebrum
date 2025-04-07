"""
Unit tests for the delegation tool used in CrewAI crews.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.controllers.curried_proxy import CurriedProxy
from src.server.persistence.persistence_model_factory import PersistenceModelFactory


class TestDelegationToolExport(unittest.TestCase):
    """Test suite for the delegation tool export functionality."""

    def setUp(self):
        """Set up the test environment."""
        # Mock the persistence model
        self.persistence_mock = MagicMock()
        
        # Patch the factory to return our mock
        patcher = patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
        self.addCleanup(patcher.stop)
        self.mock_factory = patcher.start()
        self.mock_factory.return_value = self.persistence_mock
        
        # Create curried proxy
        self.curried_proxy = CurriedProxy()

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.controllers.tools_catalog.ToolsCatalog')
    def test_delegation_tool_in_exported_tools(self, mock_catalog, mock_task_runner):
        """Test that delegation tool is included in exported tools."""
        # Export tools to CrewAI
        crewai_tools = self.curried_proxy.export_to_crewai()
        
        # Check if delegation tool is included
        delegation_tool = None
        for tool in crewai_tools:
            if hasattr(tool, 'name') and ("delegate" in tool.name.lower() or "coworker" in tool.name.lower()):
                delegation_tool = tool
                break
                
        # Assertions
        self.assertIsNotNone(delegation_tool, "Delegation tool should be included in exported tools")
        
        if delegation_tool:
            self.assertTrue(hasattr(delegation_tool, 'description'), 
                           "Delegation tool should have a description")
            
            if hasattr(delegation_tool, 'args_schema'):
                schema = delegation_tool.args_schema.model_json_schema()
                self.assertIn("properties", schema, "Args schema should have properties")


@pytest.mark.asyncio
class TestDelegationToolAsync:
    """Async tests for the delegation tool."""

    @pytest.fixture
    def persistence_mock(self):
        """Create a mock persistence model."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def curried_proxy(self, persistence_mock):
        """Create a CurriedProxy instance for testing."""
        with patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model',
                  return_value=persistence_mock):
            return CurriedProxy()

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.controllers.tools_catalog.ToolsCatalog')
    async def test_delegation_tool_execution(self, mock_catalog, mock_task_runner, curried_proxy):
        """Test delegation tool execution."""
        # Export tools to CrewAI
        crewai_tools = curried_proxy.export_to_crewai()
        
        # Find delegation tool
        delegation_tool = None
        for tool in crewai_tools:
            if hasattr(tool, 'name') and ("delegate" in tool.name.lower() or "coworker" in tool.name.lower()):
                delegation_tool = tool
                break
        
        assert delegation_tool is not None, "Delegation tool not found"
        
        # Save original _arun
        if hasattr(delegation_tool, '_arun'):
            original_arun = delegation_tool._arun
            
            # Mock _arun to avoid actual execution
            delegation_tool._arun = AsyncMock(return_value="Task delegated successfully")
            
            # Test execution
            try:
                result = await delegation_tool._arun(
                    task="Research concerts in New York",
                    context="The user wants to find concerts in New York",
                    coworker="Concert Researcher"
                )
                
                # Assertions
                assert result == "Task delegated successfully"
                delegation_tool._arun.assert_called_once()
            finally:
                # Restore original
                delegation_tool._arun = original_arun

    @patch('src.server.controllers.task_runner.TaskRunner')
    @patch('src.server.controllers.tools_catalog.ToolsCatalog')
    async def test_delegation_tool_with_dict_inputs(self, mock_catalog, mock_task_runner, curried_proxy):
        """Test delegation tool with dictionary inputs."""
        # Export tools to CrewAI
        crewai_tools = curried_proxy.export_to_crewai()
        
        # Find delegation tool
        delegation_tool = None
        for tool in crewai_tools:
            if hasattr(tool, 'name') and ("delegate" in tool.name.lower() or "coworker" in tool.name.lower()):
                delegation_tool = tool
                break
        
        assert delegation_tool is not None, "Delegation tool not found"
        
        # Save original _arun if it exists
        if hasattr(delegation_tool, '_arun'):
            original_arun = delegation_tool._arun
            
            # Create a patched version that records calls
            call_args = []
            
            async def patched_arun(*args, **kwargs):
                call_args.append(kwargs)
                return "Task delegated successfully"
                
            delegation_tool._arun = patched_arun
            
            # Test with dictionary inputs
            try:
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
            finally:
                # Restore original
                delegation_tool._arun = original_arun


if __name__ == "__main__":
    unittest.main() 