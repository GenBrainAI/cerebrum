"""
Test the task handover demo setup functionality.

This test verifies that the handover demo state is properly set up with the correct task dependencies.
"""

import pytest
import os
from pathlib import Path
import json
import tempfile
import shutil

from src.state_setup.task_handover_demo import setup_task_handover_demo
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import load_from_storage, save_to_storage

class TestHandoverDemoSetup:
    """Test cases for the handover demo setup."""
    
    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary directory for state files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_demo_setup(self, monkeypatch, temp_state_dir):
        """Test that the demo setup creates the expected tasks and dependencies."""
        # Mock the get_state_dir function to use our temp directory
        monkeypatch.setattr(
            "src.state_setup.task_handover_demo.get_state_dir", 
            lambda: Path(temp_state_dir)
        )
        
        # Run the demo setup
        setup_task_handover_demo()
        
        # Check that the state file was created
        state_file = Path(temp_state_dir) / "task_handover_demo.json"
        assert state_file.exists(), "State file was not created"
        
        # Check that metadata was updated
        metadata_file = Path(temp_state_dir) / "metadata.json"
        assert metadata_file.exists(), "Metadata file was not created"
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            assert "last_used_state" in metadata
            assert metadata["last_used_state"] == "task_handover_demo"
        
        # Read the state file directly instead of using load_from_storage
        with open(state_file, 'r') as f:
            json_str = f.read()
            state_data = json.loads(json_str)
        
        # Check that tasks and tasksmanagers collections exist
        assert "tasksmanagers" in state_data
        assert "tasks" in state_data
        
        # Parse the tasks data
        tasks_data = json.loads(state_data["tasks"])
        tasksmanagers_data = json.loads(state_data["tasksmanagers"])
        
        # Verify task manager 
        assert "handover_demo_tm" in tasksmanagers_data
        assert tasksmanagers_data["handover_demo_tm"]["name"] == "Task Handover Demo"
        
        # Verify that all expected tasks are present
        expected_tasks = [
            "research_task", 
            "analysis_task", 
            "report_task", 
            "data_task", 
            "visualization_task", 
            "summary_task"
        ]
        
        for task_id in expected_tasks:
            assert task_id in tasks_data, f"Task {task_id} not found in state data"
        
        # Verify task dependencies
        # Analysis task depends on research task
        assert "input_from_tasks" in tasks_data["analysis_task"]
        assert "research_task" in tasks_data["analysis_task"]["input_from_tasks"]
        
        # Report task depends on analysis and research
        assert "input_from_tasks" in tasks_data["report_task"]
        assert "analysis_task" in tasks_data["report_task"]["input_from_tasks"]
        assert "research_task" in tasks_data["report_task"]["input_from_tasks"]
        
        # Visualization task depends on data task
        assert "input_from_tasks" in tasks_data["visualization_task"]
        assert "data_task" in tasks_data["visualization_task"]["input_from_tasks"]
        
        # Summary task depends on report and visualization tasks
        assert "input_from_tasks" in tasks_data["summary_task"]
        assert "report_task" in tasks_data["summary_task"]["input_from_tasks"]
        assert "visualization_task" in tasks_data["summary_task"]["input_from_tasks"]
        
        # Verify output_to_tasks relationships
        assert "output_to_tasks" in tasks_data["research_task"]
        assert "analysis_task" in tasks_data["research_task"]["output_to_tasks"]
        
        assert "output_to_tasks" in tasks_data["analysis_task"]
        assert "report_task" in tasks_data["analysis_task"]["output_to_tasks"]
        
        assert "output_to_tasks" in tasks_data["data_task"]
        assert "visualization_task" in tasks_data["data_task"]["output_to_tasks"]
        
        assert "output_to_tasks" in tasks_data["visualization_task"]
        assert "report_task" in tasks_data["visualization_task"]["output_to_tasks"]
    
    def test_task_model_defaults(self):
        """Test that the Task model correctly handles the task handover fields."""
        # Create a basic task without handover fields
        task = Task(
            id="test_task",
            name="Test Task",
            description="Test task description",
            tasksmanager_id="test_tm"
        )
        
        # Verify default values
        assert hasattr(task, 'input_from_tasks')
        assert hasattr(task, 'output_to_tasks')
        assert hasattr(task, 'output_data')
        
        assert task.input_from_tasks == []
        assert task.output_to_tasks == []
        assert task.output_data == {} 