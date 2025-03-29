import pytest
from unittest.mock import MagicMock, patch
from src.server.views.components.handover_info_component import HandoverInfoComponent
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.task import Task

def test_handover_info_component_with_inputs():
    """Test the HandoverInfoComponent with input tasks."""
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Input Task", description="Provider task")
    task2 = Task(
        id="task2", 
        name="Current Task", 
        description="Consumer task",
        input_from_tasks=["task1"],
        input_data={
            "previous_task_outputs": {
                "task1": {"result": "Sample data from task1"}
            }
        }
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.json") as mock_json:
        
        mock_expander.return_value.__enter__.return_value = MagicMock()
        
        # Call render
        component.render("task2")
        
        # Assertions
        mock_subheader.assert_called_once()
        assert mock_write.call_count >= 1  # Called at least once
        assert mock_expander.call_count >= 1  # Called at least once
        assert mock_json.call_count >= 1  # Called at least once

def test_handover_info_component_with_outputs():
    """Test the HandoverInfoComponent with output tasks."""
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasks with dependencies
    task1 = Task(
        id="task1", 
        name="Provider Task", 
        description="Provider task",
        output_data={"result": "Sample data from task1"}
    )
    task2 = Task(
        id="task2", 
        name="Consumer Task", 
        description="Consumer task",
        input_from_tasks=["task1"],
        input_data={
            "previous_task_outputs": {
                "task1": {"result": "Sample data from task1"}
            }
        }
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.json") as mock_json:
        
        mock_expander.return_value.__enter__.return_value = MagicMock()
        
        # Call render
        component.render("task1")
        
        # Assertions
        mock_subheader.assert_called_once()
        assert mock_write.call_count >= 1  # Called at least once
        assert mock_expander.call_count >= 1  # Called at least once
        assert mock_json.call_count >= 1  # Called at least once

def test_handover_info_component_no_handover():
    """Test the HandoverInfoComponent with a task that has no handover relationships."""
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create task with no handover
    task = Task(id="task1", name="Solo Task", description="Task with no handover")
    persistence_model.tasks.create(task)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander:
        
        # Call render
        component.render("task1")
        
        # Assertions
        mock_subheader.assert_not_called()  # Should not be called for tasks without handover
        mock_write.assert_not_called()
        mock_expander.assert_not_called() 