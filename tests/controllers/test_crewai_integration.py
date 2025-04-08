"""
Unit tests for CrewAI integration with TaskRunner.
Tests the execution flow in test_task.py but using proper mocking.
"""

import os
import sys
import json
import pytest
import pytest_asyncio
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import modules to test
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.message import Message
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.agent import CrewAIConfig, AgentModel, TaskModel, Process, CreateCrewRequest
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.crewai_plugin import CrewAIPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig


@pytest_asyncio.fixture
async def mock_persistence_model():
    """Create a mock persistence model for testing."""
    mock = MagicMock(spec=InMemoryPersistenceModel)
    
    # Setup basic collections
    mock.tasks = MagicMock()
    mock.tasks.read = MagicMock()
    mock.tasks.update = MagicMock()
    
    mock.tasksmanagers = MagicMock()
    mock.tasksmanagers.read = MagicMock()
    
    mock.crewai_config = MagicMock()
    mock.crewai_config.read = MagicMock()
    
    mock.curried_proxies = MagicMock()
    mock.curried_proxies.read = MagicMock()
    
    # Set up reset method
    mock.reset = MagicMock()
    
    return mock


@pytest_asyncio.fixture
async def mock_task():
    """Create a mock task for testing."""
    task = MagicMock(spec=Task)
    task.id = "test-task-id"
    task.name = "Recommend Music Festivals"
    task.description = "Get personalized music festival recommendations based on preferences"
    task.tasksmanager_id = "test-manager-id"
    task.framework = "crewai"
    task.crewai_config_id = "test-config-id"
    task.curried_proxy_id = "test-proxy-id"
    task.messages = []
    task.inputs = {}
    task.status = "pending"
    task.human_input = False  # Set this to False for tests
    task.expected_output = "A list of music festivals matching the user's preferences"
    return task


@pytest_asyncio.fixture
async def mock_tasksmanager():
    """Create a mock task manager for testing."""
    manager = MagicMock(spec=TasksManager)
    manager.id = "test-manager-id"
    manager.name = "Concert Travel Planner"
    manager.system_prompt = "You are a helpful assistant specializing in concert and music festival planning."
    return manager


@pytest_asyncio.fixture
async def mock_crewai_config():
    """Create a mock CrewAI configuration for testing."""
    config = MagicMock(spec=CrewAIConfig)
    config.id = "test-config-id"
    
    # Create CreateCrewRequest with agents and tasks
    config.create_crew = MagicMock(spec=CreateCrewRequest)
    config.create_crew.description = "A crew specializing in planning concert trips"
    config.create_crew.process = Process.sequential
    
    # Mock agents
    agent = MagicMock(spec=AgentModel)
    agent.role = "Concert Planner"
    agent.goal = "Find the best concerts matching the user's preferences"
    agent.backstory = "You are an experienced concert finder with deep knowledge of venues, artists, and performances."
    agent.tools = []
    config.create_crew.agents = [agent]
    
    # Mock tasks
    task = MagicMock(spec=TaskModel)
    task.description = "Research concerts and music festivals that match the user's preferences."
    task.expected_output = "A list of relevant concerts and music festivals"
    task.agent_role = "Concert Planner"
    config.create_crew.tasks = [task]
    
    # Mock allowed tools
    config.create_crew.allowed_tools = ["brave_search", "web_search"]
    
    return config


@pytest_asyncio.fixture
async def mock_curried_proxy():
    """Create a mock curried proxy for testing."""
    proxy = MagicMock(spec=CurriedProxy)
    proxy.id = "test-proxy-id"
    proxy.name = "Concert Travel Planner Tools"
    proxy.export_to_crewai = AsyncMock(return_value=[])
    return proxy


@pytest_asyncio.fixture
async def mock_plugin_manager():
    """Create a mock plugin manager for testing."""
    manager = MagicMock(spec=PluginManager)
    manager.initialize = AsyncMock(return_value=True)
    manager.load_plugin = AsyncMock(return_value=True)
    manager.execute_task = AsyncMock(return_value="Mock plugin task execution result")
    return manager


@pytest.mark.asyncio
class TestCrewAITaskExecution:
    """Test CrewAI task execution through TaskRunner."""
    
    async def test_task_runner_initialization(self, mock_persistence_model, mock_plugin_manager):
        """Test that TaskRunner correctly initializes the plugin manager and loads the CrewAI plugin."""
        # Create a task runner with the mock persistence model
        task_runner = TaskRunner(mock_persistence_model)
        
        # Patch the PluginManager initialization
        with patch('src.server.plugins.plugin_manager.PluginManager', return_value=mock_plugin_manager):
            # Initialize task runner
            await task_runner.initialize()
            
            # Assertions
            assert task_runner._initialized is True
    
    async def test_run_crewai_task(
        self,
        mock_persistence_model,
        mock_task,
        mock_tasksmanager,
        mock_crewai_config,
        mock_curried_proxy,
        mock_plugin_manager
    ):
        """Test running a CrewAI task through the TaskRunner."""
        # Setup persistence model returns
        mock_persistence_model.tasks.read.return_value = mock_task
        mock_persistence_model.tasksmanagers.read.return_value = mock_tasksmanager
        mock_persistence_model.crewai_config.read.return_value = mock_crewai_config
        mock_persistence_model.curried_proxies.read.return_value = mock_curried_proxy
        
        # Create task runner and patch plugin manager
        task_runner = TaskRunner(mock_persistence_model)
        
        # Use patch to mock _run_crewai_task directly instead of relying on plugin
        with patch.object(task_runner, '_run_crewai_task', new_callable=AsyncMock) as mock_run_crewai_task:
            # Set up mock return value
            mock_run_crewai_task.return_value = {
                "status": "success",
                "response": "CrewAI task executed successfully"
            }
            
            # Mark as initialized
            task_runner._initialized = True
            
            # Prepare running parameters
            running_extra_params = {
                "query": "I'm looking for popular music festivals in Europe 2025"
            }
            
            # Run task
            result = await task_runner.run_task(
                tasksmanager_id=mock_tasksmanager.id,
                task_id=mock_task.id,
                running_extra_params=running_extra_params
            )
            
            # Assertions
            assert result is not None
            assert result["status"] == "success"
            assert result["response"] == "CrewAI task executed successfully"
            
            # Verify persistence model interactions
            mock_persistence_model.tasks.read.assert_called_with(mock_task.id)
            mock_persistence_model.tasksmanagers.read.assert_called_with(mock_tasksmanager.id)
            
            # Verify _run_crewai_task was called
            mock_run_crewai_task.assert_called_once()
    
    async def test_sanitize_template_vars(self, mock_persistence_model, mock_task, mock_plugin_manager):
        """Test that template variables are correctly sanitized before being passed to CrewAI."""
        # Setup
        mock_task.description = "Find concerts in {location} for {artist}"
        mock_persistence_model.tasks.read.return_value = mock_task
        mock_persistence_model.tasks.update.return_value = mock_task
        
        # Setup plugin manager
        with patch('src.server.plugins.plugin_manager.PluginManager', return_value=mock_plugin_manager):
            # Create task runner
            task_runner = TaskRunner(mock_persistence_model)
            
            # Initialize task runner
            await task_runner.initialize()
            
            # Test _sanitize_for_crewai method directly
            template_vars = {
                "location": "Paris",
                "artist": "Taylor Swift"
            }
            
            sanitized = task_runner._sanitize_for_crewai(template_vars)
            
            # Assertions
            assert sanitized["location"] == "Paris"
            assert sanitized["artist"] == "Taylor Swift"
            
            # Test with datetime
            from datetime import datetime
            date_obj = datetime.now()
            template_vars["date"] = date_obj
            
            sanitized = task_runner._sanitize_for_crewai(template_vars)
            
            # Assert date is converted to string
            assert isinstance(sanitized["date"], str)
            
            # Test with complex object
            class TestObj:
                def __str__(self):
                    return "test object"
            
            template_vars["complex"] = TestObj()
            
            sanitized = task_runner._sanitize_for_crewai(template_vars)
            
            # Assert complex object is converted to string
            assert sanitized["complex"] == "test object"

    @patch('src.server.plugins.crewai_plugin.CrewAIPlugin.run_task')
    async def test_crew_runner_integration(
        self,
        mock_plugin_run_task,
        mock_persistence_model,
        mock_task,
        mock_tasksmanager,
        mock_crewai_config,
        mock_curried_proxy,
        mock_plugin_manager
    ):
        """Test integration with crew_runner."""
        # Setup persistence model returns
        mock_persistence_model.tasks.read.return_value = mock_task
        mock_persistence_model.tasksmanagers.read.return_value = mock_tasksmanager
        mock_persistence_model.crewai_config.read.return_value = mock_crewai_config
        mock_persistence_model.curried_proxies.read.return_value = mock_curried_proxy
        
        # Configure plugin_run_task mock
        mock_plugin_run_task.return_value = "Mock CrewAI task execution result with recommendations for music festivals"
        
        # Create task runner
        task_runner = TaskRunner(mock_persistence_model)
        
        # Mock plugin manager and get_plugin to return a mock plugin
        mock_plugin = MagicMock()
        mock_plugin.run_task = mock_plugin_run_task
        mock_plugin_manager.get_plugin.return_value = mock_plugin
        task_runner.plugin_manager = mock_plugin_manager
        
        # Set initialized flag
        task_runner._initialized = True
        
        # Prepare running parameters
        running_extra_params = {
            "query": "I'm looking for popular music festivals in Europe 2025"
        }
        
        # Run task
        result = await task_runner.run_task(
            tasksmanager_id=mock_tasksmanager.id,
            task_id=mock_task.id,
            running_extra_params=running_extra_params
        )
        
        # Assertions
        assert result is not None
        assert result.get("status") == "completed"
        
        # Verify plugin.get_plugin was called with "crewai"
        mock_plugin_manager.get_plugin.assert_called_with("crewai")
        
        # Verify plugin.run_task was called
        mock_plugin_run_task.assert_called_once()


@pytest.mark.asyncio
async def test_persistence_model_factory_initialization():
    """Test that PersistenceModelFactory correctly initializes."""
    from src.server.persistence.persistence_model_factory import PersistenceModelFactory
    
    # Attempt to create a persistence model through the factory
    persistence_model = PersistenceModelFactory().persistence_model()
    
    # Assertions
    assert persistence_model is not None
    assert hasattr(persistence_model, 'tasks')
    assert hasattr(persistence_model, 'tasksmanagers')
    assert hasattr(persistence_model, 'crewai_config')
    assert hasattr(persistence_model, 'curried_proxies')


@pytest.mark.asyncio
async def test_crewai_plugin_initialization():
    """Test that CrewAIPlugin correctly initializes."""
    # Create plugin config
    config = AgentFrameworkConfig(
        name="crewai",
        version="1.0.0",
        description="CrewAI framework plugin",
        settings={
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    )
    
    # Create the plugin
    plugin = CrewAIPlugin(config)
    
    # Initialize
    result = await plugin.initialize()
    
    # Assertions
    assert result is True
    assert plugin._is_initialized is True 