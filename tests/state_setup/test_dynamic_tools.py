import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.agent import CrewAIConfig
from src.server.controllers.agents_controller import CreateCrewRequest, AgentModel
from src.server.models.agent import ToolModel
from src.server.models.persistence_models import StorageType
from src.state_setup.dynamic_tools import (
    setup_dynamic_tools_state,
    save_persistence_state,
    load_persistence_state
)

@pytest.fixture
def persistence_model():
    """Create a fresh in-memory persistence model for each test."""
    model = PersistenceModelFactory.persistence_model("inmemory")
    # Initialize collections that might not exist
    if not hasattr(model, 'crewai_config'):
        model.crewai_config = []
    return model

@pytest.fixture
def temp_state_file(tmp_path):
    """Create a temporary state file path."""
    return str(tmp_path / "test_state.json")

@pytest.fixture
def mock_crewai_config():
    """Create a mock CrewAI configuration."""
    return CrewAIConfig(
        id="test-config-id",
        create_crew=CreateCrewRequest(
            description="Test crew configuration",
            agents=[
                AgentModel(
                    name="Test Agent",
                    role="Test Role",
                    goal="Test Goal",
                    backstory="Test Backstory",
                    tools=[ToolModel(name="internal_file_tools", description="Test tool")]
                )
            ],
            tasks=[
                {
                    "name": "Test Task",
                    "description": "Test task description",
                    "agent_role": "Test Role",
                    "expected_output": "Test output",
                    "tools": [ToolModel(name="internal_file_tools", description="Test tool")]
                }
            ]
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

def test_save_and_load_persistence_state(persistence_model, temp_state_file):
    """Test saving and loading persistence state to/from JSON."""
    # Setup initial state
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        setup_dynamic_tools_state(persistence_model, temp_state_file)
    
    # Verify state was saved
    assert Path(temp_state_file).exists()
    
    # Load state into new persistence model
    new_model = PersistenceModelFactory.persistence_model("inmemory")
    if not hasattr(new_model, 'crewai_config'):
        new_model.crewai_config = []
    
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        load_persistence_state(new_model, temp_state_file)
    
    # Verify state was loaded correctly
    assert len(new_model.tools.list()) == len(persistence_model.tools.list())
    assert len(new_model.tasks.list()) == len(persistence_model.tasks.list())
    assert len(new_model.curried_proxies.list()) == len(persistence_model.curried_proxies.list())

def test_setup_dynamic_tools_state_creates_components(persistence_model, temp_state_file):
    """Test that setup_dynamic_tools_state creates all necessary components."""
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        result = setup_dynamic_tools_state(persistence_model, temp_state_file)
    
    # Verify returned IDs
    assert 'curried_proxy_id' in result
    assert 'tasksmanager_id' in result
    assert 'task_id' in result
    
    # Verify components were created
    assert len(persistence_model.curried_proxies.list()) == 1
    assert len(persistence_model.tasksmanagers.list()) == 1
    assert len(persistence_model.tasks.list()) == 1
    assert len(persistence_model.crewai_config.list()) == 1  # New assertion for CrewAI config

    # Verify task has correct framework and config
    task = persistence_model.tasks.list()[0]
    assert task.framework == "crewai"
    assert task.crewai_config_id is not None

def test_setup_dynamic_tools_state_reuses_components(persistence_model, temp_state_file):
    """Test that setup_dynamic_tools_state reuses existing components."""
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        
        # First setup
        first_result = setup_dynamic_tools_state(persistence_model, temp_state_file)
        
        # Second setup
        second_result = setup_dynamic_tools_state(persistence_model, temp_state_file)
    
    # Verify same IDs are returned
    assert first_result['curried_proxy_id'] == second_result['curried_proxy_id']
    assert first_result['tasksmanager_id'] == second_result['tasksmanager_id']
    assert first_result['task_id'] == second_result['task_id']
    
    # Verify no duplicate components were created
    assert len(persistence_model.curried_proxies.list()) == 1
    assert len(persistence_model.tasksmanagers.list()) == 1
    assert len(persistence_model.tasks.list()) == 1
    assert len(persistence_model.crewai_config.list()) == 1  # New assertion for CrewAI config

def test_setup_dynamic_tools_state_handles_missing_state_file(persistence_model, temp_state_file):
    """Test that setup works when state file doesn't exist."""
    # Ensure state file doesn't exist
    if Path(temp_state_file).exists():
        Path(temp_state_file).unlink()
    
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        result = setup_dynamic_tools_state(persistence_model, temp_state_file)
    
    # Verify components were created
    assert 'curried_proxy_id' in result
    assert 'tasksmanager_id' in result
    assert 'task_id' in result
    
    # Verify state file was created
    assert Path(temp_state_file).exists()

def test_setup_dynamic_tools_state_handles_invalid_state_file(persistence_model, temp_state_file):
    """Test that setup handles invalid state file gracefully."""
    # Create invalid state file
    with open(temp_state_file, 'w') as f:
        f.write("invalid json")
    
    with patch('src.state_setup.dynamic_tools.StorageLocation') as mock_storage_location:
        mock_storage_location.return_value.type = StorageType.file
        mock_storage_location.return_value.location = str(Path(temp_state_file).parent)
        mock_storage_location.return_value.state_name = Path(temp_state_file).name
        result = setup_dynamic_tools_state(persistence_model, temp_state_file)
    
    # Verify components were created despite invalid file
    assert 'curried_proxy_id' in result
    assert 'tasksmanager_id' in result
    assert 'task_id' in result
    
    # Verify CrewAI config was created
    assert len(persistence_model.crewai_config.list()) == 1 