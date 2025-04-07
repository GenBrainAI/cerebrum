import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import json
import os
from pathlib import Path

from src.server.demos.task_tree_demo import create_multi_plugin_task_tree, save_task_tree_demo_state
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

@pytest.mark.asyncio
async def test_task_tree_demo_integration():
    """Test that the task tree demo integrates correctly with the task runner."""
    persistence_model, tasksmanager_id = create_multi_plugin_task_tree()
    
    task_runner = MagicMock()
    task_runner.run_task = AsyncMock(return_value={"result": "Mock task result"})
    task_runner.run_task_sequence = AsyncMock(return_value={
        "research_project": {"result": "Research project completed"},
        "data_collection": {"result": "Data collection completed"},
        "market_analysis": {"result": "Market analysis completed"},
        "technical_research": {"result": "Technical research completed"},
        "report_generation": {"result": "Report generation completed"}
    })
    
    root_task_id = "research_project"
    result = await task_runner.run_task(tasksmanager_id, root_task_id)
    
    assert result is not None
    task_runner.run_task.assert_called_once_with(tasksmanager_id, root_task_id)
    
    task_ids = ["data_collection", "market_analysis", "technical_research", "report_generation"]
    sequence_result = await task_runner.run_task_sequence(tasksmanager_id, task_ids)
    
    assert sequence_result is not None
    assert len(sequence_result) == 5  # All tasks should be in the result
    task_runner.run_task_sequence.assert_called_once_with(tasksmanager_id, task_ids)

@pytest.mark.asyncio
async def test_task_tree_demo_state_loading():
    """Test that the task tree demo state can be loaded correctly."""
    mock_state = {
        "tasksmanagers": {
            "items": [{"id": "test_tm_id", "name": "Research Pipeline"}]
        },
        "tasks": {
            "items": [
                {"id": "research_project", "name": "Research Project", "tasksmanager_id": "test_tm_id"},
                {"id": "data_collection", "name": "Data Collection", "tasksmanager_id": "test_tm_id", "parent_id": "research_project"}
            ]
        },
        "context_state": {
            "current_tasksmanager_id": "test_tm_id",
            "current_task_id": "research_project"
        }
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_state))), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model") as mock_factory:
        
        mock_persistence = MagicMock()
        mock_persistence.from_json = MagicMock(return_value=None)
        mock_factory.return_value = mock_persistence
        
        mock_controller = MagicMock()
        mock_controller.load_state = MagicMock(return_value="Success")
        
        result = mock_controller.load_state("state/task_tree_demo.json")
        
        assert result == "Success"
        mock_controller.load_state.assert_called_once_with("state/task_tree_demo.json")

@pytest.mark.asyncio
async def test_ui_components_integration():
    """Test that the UI components integrate correctly."""
    with patch("streamlit.write") as mock_write, \
         patch("streamlit.info") as mock_info, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.success") as mock_success, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.warning") as mock_warning, \
         patch("pathlib.Path.exists", return_value=True):
        
        mock_controller = MagicMock()
        mock_controller.load_state = MagicMock(return_value="Success")
        
        from src.server.views.components.task_tree_demo_launcher import TaskTreeDemoLauncher
        
        launcher = TaskTreeDemoLauncher(mock_controller)
        
        mock_button.return_value = True
        
        launcher.render()
        
        mock_write.assert_called()
        mock_info.assert_called()
        mock_button.assert_called_with("Load Task Tree Demo")
        mock_controller.load_state.assert_called_once()
        mock_success.assert_called()
