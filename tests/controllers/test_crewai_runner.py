"""
Unit tests for the CrewAI runner and sanitization functionality.
"""

import asyncio
import datetime
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.controllers import crew_runner
from src.server.controllers.crew_runner import sanitize_data, run_crew_task
from src.server.controllers.task_runner import TaskRunner
from src.server.models.agent import CrewAIConfig, CreateCrewRequest
from src.server.models.message import Message
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory


class TestCrewAISanitization(unittest.TestCase):
    """Test suite for sanitizing data for CrewAI."""

    def test_sanitize_basic_types(self):
        """Test sanitizing basic data types."""
        # Test string
        self.assertEqual(crew_runner.sanitize_data("test string"), "test string")
        
        # Test numbers
        self.assertEqual(crew_runner.sanitize_data(42), 42)
        self.assertEqual(crew_runner.sanitize_data(3.14), 3.14)
        
        # Test booleans
        self.assertEqual(crew_runner.sanitize_data(True), True)
        self.assertEqual(crew_runner.sanitize_data(False), False)
        
        # Test None
        self.assertEqual(crew_runner.sanitize_data(None), None)

    def test_sanitize_datetime(self):
        """Test sanitizing datetime objects."""
        # Create a datetime object
        now = datetime.datetime.now()
        
        # Sanitize and verify it's converted to a string
        sanitized = crew_runner.sanitize_data(now)
        self.assertIsInstance(sanitized, str)
        self.assertEqual(sanitized, str(now))
        
        # Test with date
        today = datetime.date.today()
        sanitized_date = crew_runner.sanitize_data(today)
        self.assertIsInstance(sanitized_date, str)
        self.assertEqual(sanitized_date, str(today))

    def test_sanitize_nested_structures(self):
        """Test sanitizing nested data structures."""
        # Create a datetime object
        now = datetime.datetime.now()
        
        # Create a nested dictionary with various types
        data = {
            "string": "test",
            "number": 123,
            "date": now,
            "list": [1, "two", now],
            "nested": {
                "inner": now,
                "values": [now, "string"]
            }
        }
        
        # Sanitize the data
        sanitized = crew_runner.sanitize_data(data)
        
        # Verify the structure is maintained but datetimes are converted
        self.assertEqual(sanitized["string"], "test")
        self.assertEqual(sanitized["number"], 123)
        self.assertEqual(sanitized["date"], str(now))
        self.assertEqual(sanitized["list"][0], 1)
        self.assertEqual(sanitized["list"][1], "two")
        self.assertEqual(sanitized["list"][2], str(now))
        self.assertEqual(sanitized["nested"]["inner"], str(now))
        self.assertEqual(sanitized["nested"]["values"][0], str(now))
        self.assertEqual(sanitized["nested"]["values"][1], "string")

    def test_sanitize_complex_objects(self):
        """Test sanitizing complex objects (non-basic types)."""
        # Create a custom class
        class TestObject:
            def __str__(self):
                return "TestObject instance"
        
        # Create an instance
        obj = TestObject()
        
        # Sanitize and verify it's converted to a string
        sanitized = crew_runner.sanitize_data(obj)
        self.assertEqual(sanitized, "TestObject instance")
        
        # Test with a nested structure containing a complex object
        data = {
            "name": "test",
            "object": obj,
            "list": [1, obj]
        }
        
        sanitized = crew_runner.sanitize_data(data)
        self.assertEqual(sanitized["name"], "test")
        self.assertEqual(sanitized["object"], "TestObject instance")
        self.assertEqual(sanitized["list"][0], 1)
        self.assertEqual(sanitized["list"][1], "TestObject instance")


class TestCrewAIResponseFormatting(unittest.TestCase):
    """Test suite for formatting CrewAI responses."""
    
    def test_format_string_response(self):
        """Test formatting string responses."""
        # Test simple string
        response = "Hello world"
        formatted = crew_runner.format_response(response)
        self.assertEqual(formatted, "Hello world")
        
        # Test string with JSON content
        json_str = '{"key": "value"}'
        formatted = crew_runner.format_response(json_str)
        self.assertEqual(formatted, json_str)
    
    def test_format_dict_response(self):
        """Test formatting dictionary responses."""
        # Test simple dictionary
        response = {"key": "value", "number": 123}
        formatted = crew_runner.format_response(response)
        self.assertEqual(formatted, json.dumps(response))
        
        # Test nested dictionary
        response = {
            "key": "value",
            "nested": {
                "inner": "value"
            }
        }
        formatted = crew_runner.format_response(response)
        self.assertEqual(formatted, json.dumps(response))
    
    def test_format_non_serializable_response(self):
        """Test formatting responses with non-serializable content."""
        # Create a non-serializable object
        class TestObject:
            def __str__(self):
                return "TestObject"
        
        obj = TestObject()
        
        # Test direct object
        formatted = crew_runner.format_response(obj)
        self.assertEqual(formatted, "TestObject")
        
        # Test dictionary with non-serializable value
        response = {
            "key": "value",
            "object": obj
        }
        formatted = crew_runner.format_response(response)
        self.assertTrue("key" in formatted)
        self.assertTrue("value" in formatted)
        # The exact format may vary, but it should handle the non-serializable object


@pytest.mark.asyncio
class TestRunCrewTask:
    """Test suite for the run_crew_task function."""
    
    @pytest.fixture
    def mock_persistence(self):
        """Create a mock persistence model."""
        mock = MagicMock()
        
        # Configure tasks collection
        mock.tasks = MagicMock()
        mock.tasks.read = MagicMock()
        mock.tasks.update = MagicMock()
        
        # Configure crewai_config collection
        mock.crewai_config = MagicMock()
        mock.crewai_config.read = MagicMock()
        
        # Configure curried_proxies collection
        mock.curried_proxies = MagicMock()
        mock.curried_proxies.read = MagicMock()
        
        return mock
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        task = MagicMock()
        task.id = "test_task_id"
        task.name = "Test Task"
        task.framework = "crewai"
        task.crewai_config_id = "test_config_id"
        task.curried_proxy_id = "test_proxy_id"
        task.execution_logs = []
        return task
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock CrewAI configuration."""
        config = MagicMock()
        config.id = "test_config_id"
        config.name = "Test Config"
        config.agents = [MagicMock(), MagicMock()]
        return config
    
    @patch('src.server.controllers.agents_controller.create_crew')
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_successful_crew_task_execution(self, mock_factory, mock_create_crew, 
                                                 mock_persistence, mock_task, mock_config):
        """Test successful execution of a CrewAI task."""
        # Configure mocks
        mock_factory.return_value = mock_persistence
        mock_persistence.tasks.read.return_value = mock_task
        mock_persistence.crewai_config.read.return_value = mock_config
        
        # Mock crew execution
        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = "Task result"
        mock_create_crew.return_value = mock_crew
        
        # Execute the function
        result = await crew_runner.run_crew_task(mock_task.id, {"param": "value"})
        
        # Verify the result
        assert result["status"] == "success"
        assert result["response"] == "Task result"
        
        # Verify the interactions
        mock_persistence.tasks.read.assert_called_once_with(mock_task.id)
        mock_persistence.crewai_config.read.assert_called_once_with(mock_task.crewai_config_id)
        mock_create_crew.assert_called_once()
        
        # Verify task update was called
        assert mock_persistence.tasks.update.call_count >= 1
    
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_task_not_found(self, mock_factory, mock_persistence):
        """Test handling when task is not found."""
        # Configure mocks
        mock_factory.return_value = mock_persistence
        mock_persistence.tasks.read.return_value = None
        
        # Execute the function
        result = await crew_runner.run_crew_task("nonexistent_task")
        
        # Verify the result
        assert result["status"] == "failed"
        assert "not found" in result["error"]
        
        # Verify the interactions
        mock_persistence.tasks.read.assert_called_once_with("nonexistent_task")
        mock_persistence.tasks.update.assert_not_called()
    
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_missing_config_id(self, mock_factory, mock_persistence, mock_task):
        """Test handling when CrewAI config ID is missing."""
        # Configure mocks
        mock_factory.return_value = mock_persistence
        task_without_config = MagicMock()
        task_without_config.id = mock_task.id
        task_without_config.name = mock_task.name
        task_without_config.crewai_config_id = None
        task_without_config.execution_logs = []
        
        mock_persistence.tasks.read.return_value = task_without_config
        
        # Execute the function
        result = await crew_runner.run_crew_task(mock_task.id)
        
        # Verify the result
        assert result["status"] == "failed"
        assert "CrewAI configuration ID not found" in result["error"]
        
        # Verify the interactions
        mock_persistence.tasks.read.assert_called_once_with(mock_task.id)
        assert mock_persistence.tasks.update.call_count >= 1
    
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_config_not_found(self, mock_factory, mock_persistence, mock_task):
        """Test handling when CrewAI config is not found."""
        # Configure mocks
        mock_factory.return_value = mock_persistence
        mock_persistence.tasks.read.return_value = mock_task
        mock_persistence.crewai_config.read.return_value = None
        
        # Execute the function
        result = await crew_runner.run_crew_task(mock_task.id)
        
        # Verify the result
        assert result["status"] == "failed"
        assert "CrewAI configuration" in result["error"] and "not found" in result["error"]
        
        # Verify the interactions
        mock_persistence.tasks.read.assert_called_once_with(mock_task.id)
        mock_persistence.crewai_config.read.assert_called_once_with(mock_task.crewai_config_id)
        assert mock_persistence.tasks.update.call_count >= 1
    
    @patch('src.server.controllers.agents_controller.create_crew')
    @patch('src.server.controllers.crew_runner.PersistenceModelFactory.persistence_model')
    async def test_execution_error(self, mock_factory, mock_create_crew, 
                                  mock_persistence, mock_task, mock_config):
        """Test handling of execution errors."""
        # Configure mocks
        mock_factory.return_value = mock_persistence
        mock_persistence.tasks.read.return_value = mock_task
        mock_persistence.crewai_config.read.return_value = mock_config
        
        # Mock crew execution to raise an exception
        mock_create_crew.side_effect = Exception("Test error")
        
        # Execute the function
        result = await crew_runner.run_crew_task(mock_task.id)
        
        # Verify the result
        assert result["status"] == "failed"
        assert "error" in result
        assert "Test error" in result["error"]
        
        # Verify the interactions
        mock_persistence.tasks.read.assert_called_once_with(mock_task.id)
        mock_persistence.crewai_config.read.assert_called_once_with(mock_task.crewai_config_id)
        mock_create_crew.assert_called_once()
        assert mock_persistence.tasks.update.call_count >= 1


if __name__ == "__main__":
    unittest.main() 