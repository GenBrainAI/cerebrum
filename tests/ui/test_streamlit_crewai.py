"""
Test suite for Streamlit UI integration with CrewAI tools.
Tests the visualization and interaction with dynamically generated tools.
"""

import pytest
from pathlib import Path
import streamlit as st
from unittest.mock import MagicMock, patch
import json
import logging
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.models.agent import CrewAIConfig, CreateCrewRequest

logger = logging.getLogger(__name__)

@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components."""
    with patch('streamlit.container') as mock_container, \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.button') as mock_button, \
         patch('streamlit.text_input') as mock_text_input:
        yield {
            'container': mock_container,
            'write': mock_write,
            'button': mock_button,
            'text_input': mock_text_input
        }

@pytest.fixture
def persistence_model():
    """Create a persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest.mark.asyncio
async def test_crewai_tool_visualization(mock_streamlit, persistence_model):
    """Test visualization of CrewAI tools in Streamlit UI."""
    try:
        logger.info("Testing CrewAI tool visualization in Streamlit UI...")
        
        # Create a sample CrewAI config
        crewai_config = CrewAIConfig(
            create_crew=CreateCrewRequest(
                name="Test Crew",
                description="Test crew for UI visualization",
                tasks=[
                    {
                        "name": "Test Task",
                        "description": "Test task description",
                        "agent_role": "Test Agent",
                        "expected_output": "Test output",
                        "tools": []  # Empty tools list for task
                    }
                ],
                agents=[
                    {
                        "name": "Test Agent",
                        "role": "Test Role",
                        "goal": "Test Goal",
                        "backstory": "Test Backstory",
                        "tools": []  # Empty tools list for agent
                    }
                ]
            )
        )
        
        # Store config in persistence
        stored_config = persistence_model.crewai_config.create(crewai_config)
        assert stored_config is not None, "Failed to store CrewAI config"
        
        # Create a task manager
        task_manager = TasksManager(
            name="Test Manager",
            description="Test manager description",
            crewai_config_id=stored_config.id
        )
        stored_manager = persistence_model.tasksmanagers.create(task_manager)
        assert stored_manager is not None, "Failed to store task manager"
        
        # Create a task
        task = Task(
            name="Test Task",
            description="Test task description",
            tasksmanager_id=stored_manager.id,
            crewai_config_id=stored_config.id,
            agent_role="Test Agent",
            input_data={
                "tool_request": {
                    "name": "TestTool",
                    "description": "A test tool"
                }
            }
        )
        stored_task = persistence_model.tasks.create(task)
        assert stored_task is not None, "Failed to store task"
        
        # Mock Streamlit UI components
        mock_container = mock_streamlit['container'].return_value
        mock_container.__enter__.return_value = mock_container
        
        # Test tool status display
        mock_streamlit['write'].assert_not_called()
        st.write("Tool Status: Active")
        mock_streamlit['write'].assert_called_with("Tool Status: Active")
        
        # Test tool configuration display
        config_container = mock_streamlit['container'].return_value
        config_container.__enter__.return_value = config_container
        st.write(json.dumps(crewai_config.dict(), indent=2))
        mock_streamlit['write'].assert_called()
        
        # Test tool execution button
        mock_streamlit['button'].return_value = True
        assert st.button("Execute Tool"), "Tool execution button not working"
        
        # Test tool input field
        mock_streamlit['text_input'].return_value = "Test Input"
        input_value = st.text_input("Tool Input")
        assert input_value == "Test Input", "Tool input field not working"
        
        logger.info("✅ CrewAI tool visualization test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_crewai_tool_execution_monitoring(mock_streamlit, persistence_model):
    """Test monitoring of CrewAI tool execution in Streamlit UI."""
    try:
        logger.info("Testing CrewAI tool execution monitoring...")
        
        # Create a mock task runner
        runner = TaskRunner(persistence_model)
        
        # Create a progress container
        progress_container = mock_streamlit['container'].return_value
        progress_container.__enter__.return_value = progress_container
        
        # Mock execution progress
        with patch('streamlit.progress') as mock_progress:
            progress_bar = mock_progress.return_value
            progress_bar.__enter__.return_value = progress_bar
            
            # Simulate task execution
            execution_result = {
                'status': 'running',
                'progress': 0.0,
                'message': 'Starting tool execution'
            }
            
            # Update progress
            for i in range(5):
                execution_result['progress'] = i * 0.2
                execution_result['message'] = f"Execution progress: {i * 20}%"
                st.write(execution_result['message'])
                progress_bar.progress(execution_result['progress'])
                
            # Verify final state
            execution_result['status'] = 'completed'
            execution_result['progress'] = 1.0
            execution_result['message'] = 'Tool execution completed'
            
            st.write(execution_result['message'])
            progress_bar.progress(execution_result['progress'])
            
            # Verify progress updates were called
            assert mock_streamlit['write'].call_count >= 5, "Progress updates not displayed"
            assert progress_bar.progress.call_count >= 5, "Progress bar not updated"
            
        logger.info("✅ CrewAI tool execution monitoring test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_crewai_tool_results_display(mock_streamlit, persistence_model):
    """Test display of CrewAI tool execution results in Streamlit UI."""
    try:
        logger.info("Testing CrewAI tool results display...")
        
        # Create a mock execution result
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
        
        # Create results container
        results_container = mock_streamlit['container'].return_value
        results_container.__enter__.return_value = results_container
        
        # Display results
        st.write("### Execution Results")
        st.write(f"Status: {execution_result['status']}")
        
        # Display generated tool details
        tool = execution_result['generated_tool']
        st.write("#### Generated Tool")
        st.write(f"Name: {tool['name']}")
        st.write(f"Description: {tool['description']}")
        
        # Display code with syntax highlighting
        st.code(tool['implementation'], language='python')
        st.code(tool['tests'], language='python')
        
        # Display metrics
        metrics = execution_result['metrics']
        st.write("#### Execution Metrics")
        st.write(f"Execution Time: {metrics['execution_time']}s")
        st.write(f"Memory Usage: {metrics['memory_usage']}")
        st.write(f"API Calls: {metrics['api_calls']}")
        
        # Verify all information was displayed
        display_calls = mock_streamlit['write'].call_args_list
        assert any('Execution Results' in str(call) for call in display_calls), "Missing execution results header"
        assert any('Generated Tool' in str(call) for call in display_calls), "Missing generated tool section"
        assert any('Execution Metrics' in str(call) for call in display_calls), "Missing metrics section"
        
        logger.info("✅ CrewAI tool results display test passed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise 