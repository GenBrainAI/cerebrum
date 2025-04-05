"""
Unit tests for task tree demo setup.
"""

import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.state_setup.task_tree_demo import setup_task_tree_demo_state
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

@pytest.mark.asyncio
async def test_task_tree_demo_setup():
    """Test that the task tree demo setup creates the expected state structure."""
    # Mock saving state to file
    with patch('builtins.open', MagicMock()):
        with patch('json.dump', MagicMock()):
            # Run setup
            result = await setup_task_tree_demo_state()
            
            # Check results
            assert "tasksmanager_id" in result
            assert "root_task_id" in result
            assert "data_acquisition_task_id" in result
            assert "market_analysis_task_id" in result
            assert "technical_analysis_task_id" in result
            assert "report_generation_task_id" in result
            
            # Verify tasks were created
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            
            # Verify task manager was created
            tasksmanager = persistence_model.tasksmanagers.read(result["tasksmanager_id"])
            assert tasksmanager is not None
            assert tasksmanager.name == "Data Processing Pipeline"
            
            # Verify root task was created
            root_task = persistence_model.tasks.read(result["root_task_id"])
            assert root_task is not None
            assert root_task.name == "Data Pipeline Coordinator"
            
            # Verify child tasks
            data_acquisition = persistence_model.tasks.read(result["data_acquisition_task_id"])
            assert data_acquisition is not None
            
            # Debug output to see what attributes are available
            print("\nData Acquisition Task Attributes:")
            print(f"  Type: {type(data_acquisition)}")
            if hasattr(data_acquisition, 'framework'):
                print(f"  Framework: {data_acquisition.framework}")
            if hasattr(data_acquisition, 'dict'):
                print(f"  Dict keys: {data_acquisition.dict().keys()}")
            
            # Updated check for task attribute that exists
            assert data_acquisition.name == "Data Acquisition"
            assert data_acquisition.framework == "crewai"
            assert data_acquisition.crewai_config_id is not None
            
            # Verify task with dependencies
            report_generation = persistence_model.tasks.read(result["report_generation_task_id"])
            assert report_generation is not None
            assert "market_analysis_task_id" in result
            assert "technical_analysis_task_id" in result
            assert result["market_analysis_task_id"] in report_generation.input_from_tasks
            assert result["technical_analysis_task_id"] in report_generation.input_from_tasks
            
            # Verify the root task has the task tree metadata
            assert hasattr(root_task, 'config')
            assert 'task_tree' in root_task.config
            assert root_task.config['task_tree']['name'] == "Data Processing Pipeline"

@pytest.mark.parametrize("tree_exists", [True, False])
def test_task_tree_demo_component(tree_exists):
    """Test the task tree demo component with and without existing state."""
    from src.server.views.components.task_tree_demo_component import TaskTreeDemoComponent
    
    # Mock controller
    mock_controller = MagicMock()
    mock_controller.load_state.return_value = "State loaded successfully"
    
    # Mock Path.exists
    with patch('pathlib.Path.exists', return_value=tree_exists):
        # Mock streamlit
        with patch('streamlit.write'), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.success'), \
             patch('streamlit.error'), \
             patch('streamlit.warning'), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.spinner'), \
             patch('streamlit.rerun'), \
             patch('streamlit.image'):
            
            # Test component
            component = TaskTreeDemoComponent(mock_controller)
            component.render()
            
            # If tree exists, should try to load it
            if tree_exists:
                mock_controller.load_state.assert_called_once()

@pytest.mark.asyncio
async def test_visualization_data_flow():
    """Test the data flow connections in the task tree setup."""
    # Mock saving state to file
    with patch('builtins.open', MagicMock()) as mock_open:
        with patch('json.dump', MagicMock()) as mock_dump:
            # Run setup
            result = await setup_task_tree_demo_state()
            
            # Verify persistence model
            persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            
            # Verify root task was created
            root_task = persistence_model.tasks.read(result["root_task_id"])
            assert root_task is not None
            assert root_task.name == "Data Pipeline Coordinator"
            
            # Check for config on root task that contains the tree metadata
            assert hasattr(root_task, 'config')
            assert 'task_tree' in root_task.config
            assert root_task.config['task_tree']['name'] == "Data Processing Pipeline"
            
            # Check for data flow in the config
            assert 'data_flow' in root_task.config['task_tree']
            data_flow = root_task.config['task_tree']['data_flow']
            assert len(data_flow) == 4
            
            # Check specific connections
            connections = {(flow["from"], flow["to"]) for flow in data_flow}
            assert ("data_acquisition", "market_analysis") in connections
            assert ("data_acquisition", "technical_analysis") in connections
            assert ("market_analysis", "report_generation") in connections
            assert ("technical_analysis", "report_generation") in connections 