"""
Unit tests for CrewAI task execution and handling.
"""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

import pytest
from crewai import Agent, Crew, Task

from src.server.controllers import crew_runner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory


class TestCrewAITask(unittest.TestCase):
    """Test suite for CrewAI task execution and handling."""

    def setUp(self):
        """Set up test environment."""
        # Mock persistence model
        self.persistence_mock = MagicMock()
        self.persistence_mock.get.return_value = None
        self.persistence_mock.create.return_value = {"id": "test_id"}
        self.persistence_mock.read.return_value = None
        
        # Patch the factory to return our mock
        patcher = patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
        self.addCleanup(patcher.stop)
        self.mock_factory = patcher.start()
        self.mock_factory.return_value = self.persistence_mock

    def test_sanitize_data(self):
        """Test sanitization of CrewAI output data."""
        from datetime import datetime
        
        # Test with simple string
        self.assertEqual(crew_runner.sanitize_data("test"), "test")
        
        # Test with dict
        data = {"result": "test result", "extra": "info"}
        self.assertEqual(crew_runner.sanitize_data(data), data)
        
        # Test with datetime
        now = datetime.now()
        self.assertEqual(crew_runner.sanitize_data(now), str(now))
        
        # Test with nested structure
        nested = {
            "date": now,
            "items": [1, "two", 3.0],
            "metadata": {
                "created_at": now
            }
        }
        expected = {
            "date": str(now),
            "items": [1, "two", 3.0],
            "metadata": {
                "created_at": str(now)
            }
        }
        self.assertEqual(crew_runner.sanitize_data(nested), expected)
        
        # Test with custom object
        class TestObj:
            def __str__(self):
                return "test object"
        
        test_obj = TestObj()
        self.assertEqual(crew_runner.sanitize_data(test_obj), "test object")

    def test_format_response(self):
        """Test formatting of CrewAI responses."""
        # Test with simple string
        self.assertEqual(crew_runner.format_response("test"), "test")
        
        # Test with JSON string
        json_str = '{"result": "success"}'
        self.assertEqual(crew_runner.format_response(json_str), json_str)
        
        # Test with dict
        data = {"result": "success", "data": [1, 2, 3]}
        self.assertEqual(crew_runner.format_response(data), json.dumps(data))
        
        # Test with non-serializable object
        class TestObj:
            def __str__(self):
                return "test object"
        
        self.assertEqual(crew_runner.format_response(TestObj()), "test object")
        
        # Test with dict containing non-serializable object
        data_with_nonserial = {"result": "success", "obj": TestObj()}
        result = crew_runner.format_response(data_with_nonserial)
        self.assertTrue('"result": "success"' in result)


@pytest.mark.asyncio
class TestCrewAITaskAsync:
    """Async tests for CrewAI task execution."""

    @pytest.fixture
    def persistence_mock(self):
        """Create a mock persistence model."""
        mock = MagicMock()
        
        # Configure collections
        mock.tasks = MagicMock()
        mock.tasks.read.return_value = None
        mock.tasks.update.return_value = True
        
        mock.crewai_config = MagicMock()
        mock.crewai_config.read.return_value = None
        
        mock.curried_proxies = MagicMock()
        mock.curried_proxies.read.return_value = None
        
        return mock

    @pytest.fixture
    def task_data(self):
        """Create mock task data."""
        task = MagicMock()
        task.id = "test_task"
        task.name = "Test Task"
        task.description = "Test description"
        task.crewai_config_id = "test_config"
        task.framework = "crewai"
        task.human_input = False
        task.agent_role = None  # Will be set in individual tests if needed
        task.curried_proxy_id = "test_proxy_id"
        task.input_data = {"query": "test query"}
        task.execution_logs = []
        return task

    @pytest.fixture
    def crewai_config(self):
        """Create mock CrewAI configuration."""
        config = MagicMock()
        config.id = "test_config"
        config.name = "Test Configuration"
        config.agents = [
            MagicMock(role="Researcher"),
            MagicMock(role="Writer")
        ]
        
        # Mock the create_crew attribute needed by some functions
        config.create_crew = MagicMock()
        config.create_crew.allowed_tools = ["brave_search", "web_search"]
        config.create_crew.agents = config.agents
        
        return config

    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    @patch('src.server.controllers.agents_controller.create_crew')
    @patch('src.server.controllers.curried_proxy.CurriedProxy')
    @patch('src.server.controllers.crew_runner.human_input_tool')
    async def test_run_crew_task(self, mock_human_tool, mock_curried_proxy_class, mock_create_crew, mock_factory, persistence_mock, task_data, crewai_config):
        """Test the run_crew_task function."""
        # Configure mocks
        mock_factory.return_value = persistence_mock
        persistence_mock.tasks.read.return_value = task_data
        persistence_mock.crewai_config.read.return_value = crewai_config
        
        # Setup human input tool
        task_data.human_input = True
        
        # Setup mock CurriedProxy instance
        mock_curried_proxy = MagicMock()
        mock_curried_proxy.tools = {}
        mock_curried_proxy.add_tool = MagicMock()
        mock_curried_proxy_class.return_value = mock_curried_proxy
        
        # Ensure curried proxy is found (or not found to test creation path)
        persistence_mock.curried_proxies.read.return_value = None
        
        # Mock the crew
        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = "Task executed successfully"
        mock_create_crew.return_value = mock_crew
        
        # Call the method
        result = await crew_runner.run_crew_task(task_data.id, {"query": "test query"}, persistence_mock)
        
        # Assertions
        assert result["status"] == "success"
        assert result["response"] == "Task executed successfully"
        persistence_mock.tasks.read.assert_called_once_with(task_data.id)
        persistence_mock.crewai_config.read.assert_called_once_with(task_data.crewai_config_id)
        mock_create_crew.assert_called_once()
        persistence_mock.tasks.update.assert_called()
        
        # Verify human input tool was added
        mock_curried_proxy.add_tool.assert_called_with('human_input', mock_human_tool)

    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_run_crew_task_not_found(self, mock_factory, persistence_mock):
        """Test run_crew_task when task is not found."""
        # Configure mocks
        mock_factory.return_value = persistence_mock
        persistence_mock.tasks.read.return_value = None
        
        # Call the method
        result = await crew_runner.run_crew_task("nonexistent_task")
        
        # Assertions
        assert result["status"] == "failed"
        assert "not found" in result["error"]
        persistence_mock.tasks.read.assert_called_once_with("nonexistent_task")

    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_run_crew_task_missing_config(self, mock_factory, persistence_mock, task_data):
        """Test run_crew_task when config is missing."""
        # Configure mocks
        mock_factory.return_value = persistence_mock
        task_data.crewai_config_id = None
        persistence_mock.tasks.read.return_value = task_data
        
        # Call the method
        result = await crew_runner.run_crew_task(task_data.id)
        
        # Assertions
        assert result["status"] == "failed"
        assert "CrewAI configuration ID not found" in result["error"]
        persistence_mock.tasks.read.assert_called_once_with(task_data.id)

    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_run_crew_task_config_not_found(self, mock_factory, persistence_mock, task_data):
        """Test run_crew_task when config is not found."""
        # Configure mocks
        mock_factory.return_value = persistence_mock
        persistence_mock.tasks.read.return_value = task_data
        persistence_mock.crewai_config.read.return_value = None
        
        # Call the method
        result = await crew_runner.run_crew_task(task_data.id)
        
        # Assertions
        assert result["status"] == "failed"
        assert "CrewAI configuration" in result["error"] and "not found" in result["error"]
        persistence_mock.tasks.read.assert_called_once_with(task_data.id)
        persistence_mock.crewai_config.read.assert_called_once_with(task_data.crewai_config_id)

    # Much simpler approach using monkeypatch
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_run_crew_task(self, mock_factory, persistence_mock, task_data, crewai_config, monkeypatch):
        """Test the run_crew_task function using monkeypatch to avoid internal implementation details."""
        # Set up mocks
        persistence_mock.tasks.read.return_value = task_data
        persistence_mock.crewai_config.read.return_value = crewai_config
        mock_factory.return_value = persistence_mock
        
        # Set the agent_role to a valid role from the available roles in crewai_config
        task_data.agent_role = "Researcher"
        task_data.framework = "crewai"
        
        # Use monkeypatch to replace functions that might be causing issues
        async def mock_create_crew(*args, **kwargs):
            mock_crew = MagicMock()
            # Create a normal method that returns a value instead of a coroutine
            mock_crew.kickoff = MagicMock(return_value="Task executed successfully")
            return mock_crew
            
        # Apply monkeypatch
        monkeypatch.setattr('src.server.controllers.agents_controller.create_crew', mock_create_crew)
        
        # We also need to monkeypatch CurriedProxy to avoid issues with the tools attribute
        class MockCurriedProxy:
            def __init__(self):
                self.tools = {}
                
            def add_tool(self, name, tool):
                self.tools[name] = tool
                
            async def export_to_crewai(self, allowed_tools=None):
                return []
                
        monkeypatch.setattr('src.server.controllers.crew_runner.CurriedProxy', MockCurriedProxy)
        
        # Call the function
        result = await crew_runner.run_crew_task(task_data.id, {"query": "test query"}, persistence_mock)
        
        # Assertions
        assert result["status"] == "success"
        assert result["response"] == "Task executed successfully"
        persistence_mock.tasks.read.assert_called_once_with(task_data.id)
        persistence_mock.crewai_config.read.assert_called_once_with(task_data.crewai_config_id)


if __name__ == "__main__":
    unittest.main() 