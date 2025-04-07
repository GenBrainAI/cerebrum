import pytest
from unittest.mock import patch, mock_open
import json
import os
from pathlib import Path

from src.server.demos.task_tree_demo import create_multi_plugin_task_tree, save_task_tree_demo_state

def test_create_multi_plugin_task_tree():
    """Test that the multi-plugin task tree is created correctly."""
    persistence_model, tasksmanager_id = create_multi_plugin_task_tree()
    
    tasksmanagers = persistence_model.tasksmanagers.list()
    assert len(tasksmanagers) == 1
    assert tasksmanagers[0].id == tasksmanager_id
    
    tasks = persistence_model.tasks.list()
    assert len(tasks) >= 5  # Root + 3 level 1 + 1 level 2
    
    root_task = persistence_model.tasks.read("research_project")
    assert root_task is not None
    assert root_task.name == "Research Project"
    assert root_task.plugin == "crewai"
    
    level1_tasks = [t for t in tasks if t.parent_id == "research_project"]
    assert len(level1_tasks) == 3
    
    market_analysis = persistence_model.tasks.read("market_analysis")
    assert "data_collection" in market_analysis.input_from_tasks
    
    report_task = persistence_model.tasks.read("report_generation")
    assert "market_analysis" in report_task.input_from_tasks
    assert "technical_research" in report_task.input_from_tasks
    
    tree_collection = persistence_model.collection("task_trees")
    tree_metadata = tree_collection.read("research_pipeline")
    assert tree_metadata is not None
    assert tree_metadata["root_task_id"] == "research_project"

@pytest.mark.asyncio
async def test_save_task_tree_demo_state(tmp_path):
    """Test that the task tree demo state is saved correctly."""
    with patch("src.server.demos.task_tree_demo.Path") as mock_path, \
         patch("builtins.open", mock_open()) as mock_file:
        
        mock_path.return_value = tmp_path
        mock_path.mkdir.return_value = None
        
        state_file = save_task_tree_demo_state()
        
        assert state_file is not None
        assert mock_file.call_count >= 1
        
        args, kwargs = mock_file().write.call_args
        assert "context_state" in args[0]
        assert "current_tasksmanager_id" in args[0]
        assert "current_task_id" in args[0]
        assert "research_project" in args[0]
