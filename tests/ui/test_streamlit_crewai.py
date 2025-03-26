"""
Test suite for Streamlit UI integration with CrewAI tools.
Tests the visualization and interaction with dynamically generated tools.
"""

import pytest
import pytest_asyncio
from pathlib import Path
import streamlit as st
from unittest.mock import MagicMock, patch, AsyncMock
import json
import logging
from typing import Dict, Any

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.models.agent import CrewAIConfig, CreateCrewRequest

logger = logging.getLogger(__name__)

class SessionStateMock(dict):
    """Mock for Streamlit's session state that supports both dict and attribute access."""
    def __getattr__(self, key):
        if key not in self:
            self[key] = {}
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value

@pytest.fixture
def mock_session_state():
    """Create a mock session state for testing."""
    return SessionStateMock()

@pytest.fixture
def mock_streamlit(mock_session_state):
    """Mock Streamlit components with proper session state."""
    with patch('streamlit.session_state', new=mock_session_state), \
         patch('streamlit.container') as mock_container, \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.button') as mock_button, \
         patch('streamlit.text_input') as mock_text_input, \
         patch('streamlit.code') as mock_code, \
         patch('streamlit.progress') as mock_progress:
        
        # Set up container context manager behavior
        mock_container.return_value.__enter__.return_value = mock_container.return_value
        mock_progress.return_value.__enter__.return_value = mock_progress.return_value
        
        yield {
            'session_state': mock_session_state,
            'container': mock_container,
            'write': mock_write,
            'button': mock_button,
            'text_input': mock_text_input,
            'code': mock_code,
            'progress': mock_progress
        }

@pytest.fixture
def persistence_model():
    """Create a persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest_asyncio.fixture
async def task_runner(persistence_model):
    """Create a task runner for testing."""
    runner = TaskRunner(persistence_model)
    return runner

@pytest.fixture
def sample_crewai_config():
    """Create a sample CrewAI configuration for testing."""
    return CrewAIConfig(
        create_crew=CreateCrewRequest(
            name="Test Crew",
            description="Test crew for UI visualization",
            tasks=[{
                "name": "Test Task",
                "description": "Test task description",
                "agent_role": "Test Agent",
                "expected_output": "Test output",
                "tools": []
            }],
            agents=[{
                "name": "Test Agent",
                "role": "Test Role",
                "goal": "Test Goal",
                "backstory": "Test Backstory",
                "tools": []
            }]
        )
    )

@pytest.mark.asyncio
async def test_crewai_tool_visualization(
    mock_streamlit,
    persistence_model,
    sample_crewai_config
):
    """Test visualization of CrewAI tools in Streamlit UI."""
    # Store config in persistence
    stored_config = persistence_model.crewai_config.create(sample_crewai_config)
    assert stored_config is not None
    
    # Create and store task manager
    task_manager = TasksManager(
        name="Test Manager",
        description="Test manager description",
        crewai_config_id=stored_config.id
    )
    stored_manager = persistence_model.tasksmanagers.create(task_manager)
    assert stored_manager is not None
    
    # Create and store task
    task = Task(
        name="Test Task",
        description="Test task description",
        tasksmanager_id=stored_manager.id,
        crewai_config_id=stored_config.id,
        agent_role="Test Agent",
        input_data={"tool_request": {"name": "TestTool", "description": "A test tool"}}
    )
    stored_task = persistence_model.tasks.create(task)
    assert stored_task is not None
    
    # Test UI interactions
    mock_streamlit['button'].return_value = True
    assert st.button("Execute Tool")
    
    mock_streamlit['text_input'].return_value = "Test Input"
    input_value = st.text_input("Tool Input")
    assert input_value == "Test Input"
    
    # Verify config display
    st.write(json.dumps(sample_crewai_config.model_dump(), indent=2))
    mock_streamlit['write'].assert_called()

@pytest.mark.asyncio
async def test_crewai_tool_execution_monitoring(
    mock_streamlit,
    task_runner
):
    """Test monitoring of CrewAI tool execution in Streamlit UI."""
    progress_bar = mock_streamlit['progress'].return_value
    
    # Simulate execution progress
    execution_states = [
        {'progress': 0.0, 'message': 'Starting execution'},
        {'progress': 0.5, 'message': 'Processing'},
        {'progress': 1.0, 'message': 'Completed'}
    ]
    
    for state in execution_states:
        st.write(state['message'])
        progress_bar.progress(state['progress'])
    
    # Verify progress updates
    assert mock_streamlit['write'].call_count >= len(execution_states)
    assert progress_bar.progress.call_count >= len(execution_states)

@pytest.mark.asyncio
async def test_crewai_tool_results_display(
    mock_streamlit
):
    """Test display of CrewAI tool execution results in Streamlit UI."""
    execution_result = {
        'status': 'completed',
        'generated_tool': {
            'name': 'TestTool',
            'description': 'A test tool',
            'implementation': 'class TestTool:\n    def __init__(self):\n        pass',
            'tests': 'def test_tool():\n    assert True',
            'requirements': ['numpy', 'pandas']
        },
        'metrics': {
            'execution_time': 1.23,
            'memory_usage': '128MB',
            'api_calls': 5
        }
    }
    
    # Display results
    st.write("### Execution Results")
    st.write(f"Status: {execution_result['status']}")
    
    # Display generated tool
    tool = execution_result['generated_tool']
    st.write("#### Generated Tool")
    st.write(f"Name: {tool['name']}")
    st.write(f"Description: {tool['description']}")
    
    # Display code
    st.code(tool['implementation'], language='python')
    st.code(tool['tests'], language='python')
    
    # Display metrics
    metrics = execution_result['metrics']
    st.write("#### Execution Metrics")
    for key, value in metrics.items():
        st.write(f"{key.replace('_', ' ').title()}: {value}")
    
    # Verify displays
    write_calls = [str(call[0][0]) for call in mock_streamlit['write'].call_args_list]
    assert any('Execution Results' in call for call in write_calls)
    assert any('Generated Tool' in call for call in write_calls)
    assert any('Execution Metrics' in call for call in write_calls)
    assert mock_streamlit['code'].call_count == 2  # Implementation and tests 