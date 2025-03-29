import pytest
from unittest.mock import MagicMock, patch
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from uuid import UUID

@pytest.mark.asyncio
async def test_get_task_tree_with_handover():
    """Test the get_task_tree_with_handover method."""
    # Setup persistence model with tasksmanager and tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasksmanager
    tm = TasksManager(id="tm1", name="Test Manager")
    persistence_model.tasksmanagers.create(tm)
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Task 1", tasksmanager_id="tm1", description="First task")
    task2 = Task(
        id="task2", 
        name="Task 2", 
        tasksmanager_id="tm1",
        description="Second task",
        input_from_tasks=["task1"]
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create controller
    controller = TaskHierarchyController(persistence_model)
    
    # Get tree with handover
    tree = await controller.get_task_tree_with_handover()
    
    # Assertions
    assert tree is not None
    assert len(tree.children) == 1  # One tasksmanager
    
    tm_node = tree.children[0]
    assert len(tm_node.children) == 2  # Two tasks
    
    # Find task nodes
    task1_node = next((n for n in tm_node.children if n.name == "Task 1"), None)
    task2_node = next((n for n in tm_node.children if n.name == "Task 2"), None)
    
    assert task1_node is not None
    assert task2_node is not None
    
    # Check handover indicators
    assert task2_node.data.get("has_inputs", False) is True
    assert "outputs_to" in task1_node.data
    assert "task2" in task1_node.data["outputs_to"]

@pytest.mark.asyncio
async def test_get_task_tree_with_handover_empty():
    """Test the get_task_tree_with_handover method with an empty persistence model."""
    # Setup empty persistence model
    persistence_model = InMemoryPersistenceModel()
    
    # Create controller
    controller = TaskHierarchyController(persistence_model)
    
    # Get tree with handover
    tree = await controller.get_task_tree_with_handover()
    
    # Assertions
    assert tree is not None
    assert len(tree.children) == 0  # No tasksmanagers 