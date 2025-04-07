"""
Test suite for CrewAI integration with task tree.
Tests the execution of CrewAI tasks within the task tree structure.
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any, List
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.task_runner import TaskRunner
from src.server.models.agent import CrewAIConfig, CreateCrewRequest
from src.server.models.tasktree import TaskTree, TaskNode
import uuid
from unittest.mock import MagicMock, patch
from src.models.crewai_config import CrewAIAgentModel, CrewAIConfigModel, CrewAITaskModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.tasktree.task_manager import TaskManager

logger = logging.getLogger(__name__)

@pytest.fixture
def persistence_model():
    """Create an in-memory persistence model for testing."""
    return InMemoryPersistenceModel()

@pytest.fixture
def crewai_config():
    """Create a sample CrewAI configuration with tasks and agents."""
    # Create three tasks
    tasks = [
        CrewAITaskModel(
            id=str(uuid.uuid4()),
            name=f"Task {i}",
            description=f"Description for task {i}",
            expected_output=f"Expected output for task {i}"
        )
        for i in range(1, 4)
    ]

    # Create three agents
    agents = [
        CrewAIAgentModel(
            id=str(uuid.uuid4()),
            name=f"Agent {i}",
            role=f"Role {i}",
            goal=f"Goal for agent {i}",
            backstory=f"Backstory for agent {i}",
            verbose=True,
            allow_delegation=False,
            tools=[]
        )
        for i in range(1, 4)
    ]

    # Assign agents to tasks
    for i, task in enumerate(tasks):
        task.agent = agents[i].id

    # Create the CrewAI configuration
    config = CrewAIConfigModel(
        id=str(uuid.uuid4()),
        name="Test CrewAI Configuration",
        description="Configuration for testing CrewAI in task trees",
        tasks=tasks,
        agents=agents,
        process={},
        verbose=True
    )

    return config

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
def test_crewai_task_tree_creation(mock_persistence_model, persistence_model, crewai_config):
    """Test creating a task tree with CrewAI tasks."""
    logger.info("Testing CrewAI task tree creation")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    task_manager = TaskManager()
    
    # Create parent task with CrewAI framework
    parent_task = task_manager.create_task(
        name="Parent Task",
        description="A parent task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id
    )
    
    # Create child tasks with CrewAI framework
    child_task1 = task_manager.create_task(
        name="Child Task 1",
        description="First child task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        parent_id=parent_task.id
    )
    
    child_task2 = task_manager.create_task(
        name="Child Task 2",
        description="Second child task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        parent_id=parent_task.id
    )
    
    # Get the task tree
    task_tree = task_manager.get_task_tree()
    
    # Validate the tree structure
    assert len(task_tree.roots) == 1, "Should have one root node"
    assert len(task_tree.roots[0].children) == 2, "Root should have two children"
    assert task_tree.parent_of(child_task1.id) == parent_task.id, "Child 1 parent should be parent task"
    assert task_tree.parent_of(child_task2.id) == parent_task.id, "Child 2 parent should be parent task"
    
    # Validate task attributes
    assert task_tree.roots[0].task.framework == "crewai", "Root task should have crewai framework"
    assert task_tree.roots[0].task.crewai_config_id == crewai_config.id, "Root task should have crewai config ID"
    
    logger.info("CrewAI task tree creation test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
def test_crewai_task_tree_execution(mock_persistence_model, persistence_model, crewai_config):
    """Test executing CrewAI tasks in a task tree."""
    logger.info("Testing CrewAI task tree execution")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    task_manager = TaskManager()
    
    # Create tasks with dependencies
    task1 = task_manager.create_task(
        name="Task 1",
        description="First task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id
    )
    
    task2 = task_manager.create_task(
        name="Task 2",
        description="Second task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        dependencies=[task1.id]
    )
    
    task3 = task_manager.create_task(
        name="Task 3",
        description="Third task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        dependencies=[task2.id]
    )
    
    # Construct a task tree with sequential dependencies
    task_tree = task_manager.get_task_tree()
    
    # Validate tree structure
    assert len(task_tree.roots) == 1, "Should have one root node"
    assert len(task_tree.get_all_nodes()) == 3, "Should have three nodes total"
    
    # Create a task runner
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure the mock to return a successful result
        mock_run_crew_task.return_value = {
            "status": "success", 
            "response": "Mocked CrewAI task execution result"
        }
        
        # Create the task runner
        task_runner = TaskRunner(task_tree)
        
        # Run the tasks
        task_results = task_runner.run_tasks({})
        
        # Validate that all tasks were executed
        assert len(task_results) == 3, "Should have results for all three tasks"
        assert mock_run_crew_task.call_count == 3, "run_crew_task should be called for each task"
        
        # Validate execution order based on dependencies
        call_order = [call[0][0] for call in mock_run_crew_task.call_args_list]
        assert call_order[0] == task1.id, "Task 1 should be executed first"
        assert call_order[1] == task2.id, "Task 2 should be executed second"
        assert call_order[2] == task3.id, "Task 3 should be executed third"
    
    logger.info("CrewAI task tree execution test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
def test_crewai_task_tree_error_handling(mock_persistence_model, persistence_model, crewai_config):
    """Test error handling during CrewAI task execution in a task tree."""
    logger.info("Testing CrewAI task tree error handling")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    task_manager = TaskManager()
    
    # Create a task tree with two tasks
    task1 = task_manager.create_task(
        name="Task 1",
        description="First task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id
    )
    
    task2 = task_manager.create_task(
        name="Task 2",
        description="Second task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        dependencies=[task1.id]
    )
    
    # Get the task tree
    task_tree = task_manager.get_task_tree()
    
    # Test with task1 failing
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # First task fails, second shouldn't execute
        mock_run_crew_task.side_effect = [
            {"status": "failed", "error": "Task execution failed"},
            {"status": "success", "response": "This should not be called"}
        ]
        
        # Create the task runner
        task_runner = TaskRunner(task_tree)
        
        # Run the tasks
        task_results = task_runner.run_tasks({})
        
        # Validate results
        assert len(task_results) == 1, "Should only have result for first task"
        assert task_results[task1.id]["status"] == "failed", "Task 1 should have failed status"
        assert task1.id in task_results and task2.id not in task_results, "Only Task 1 should have results"
        assert mock_run_crew_task.call_count == 1, "Only first task should be executed"
        
        assert "Agent role" in str(
            task_results[task1.id].get("error", "")
        ), "Error should mention an invalid agent role"
    
    logger.info("CrewAI task tree error handling test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
def test_crewai_parallel_execution(mock_persistence_model, persistence_model, crewai_config):
    """Test parallel execution of CrewAI tasks in a task tree."""
    logger.info("Testing parallel execution of CrewAI tasks")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    task_manager = TaskManager()
    
    # Create a parent task
    parent_task = task_manager.create_task(
        name="Parent Task",
        description="Parent task with parallel children",
        execution_strategy="parallel"
    )
    
    # Create three child tasks that will execute in parallel
    child_tasks = []
    for i in range(3):
        child = task_manager.create_task(
            name=f"Child Task {i+1}",
            description=f"Child task {i+1} using CrewAI",
            framework="crewai",
            crewai_config_id=crewai_config.id,
            parent_id=parent_task.id
        )
        child_tasks.append(child)
    
    # Get the task tree
    task_tree = task_manager.get_task_tree()
    
    # Validate tree structure
    assert len(task_tree.roots) == 1, "Should have one root node"
    assert len(task_tree.roots[0].children) == 3, "Root should have three children"
    assert task_tree.roots[0].task.execution_strategy == "parallel", "Root should have parallel execution strategy"
    
    # Test parallel execution
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure mock to return successful results
        mock_run_crew_task.return_value = {
            "status": "success",
            "response": "Mocked CrewAI parallel task result"
        }
        
        # Create the task runner
        task_runner = TaskRunner(task_tree)
        
        # Run the tasks
        task_results = task_runner.run_tasks({})
        
        # Validate results
        assert len(task_results) == 4, "Should have results for parent and all three children"
        assert mock_run_crew_task.call_count == 3, "run_crew_task should be called for each child task"
        
        # Verify all child tasks have results
        for child in child_tasks:
            assert child.id in task_results, f"Task {child.id} should have results"
            assert task_results[child.id]["status"] == "success", f"Task {child.id} should have succeeded"
    
    logger.info("Parallel execution of CrewAI tasks test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
def test_crewai_with_non_crewai_tasks(mock_persistence_model, persistence_model, crewai_config):
    """Test a task tree with a mix of CrewAI and non-CrewAI tasks."""
    logger.info("Testing task tree with mix of CrewAI and non-CrewAI tasks")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    task_manager = TaskManager()
    
    # Create a parent task (non-CrewAI)
    parent_task = task_manager.create_task(
        name="Parent Task",
        description="Non-CrewAI parent task"
    )
    
    # Create a CrewAI child task
    crewai_task = task_manager.create_task(
        name="CrewAI Task",
        description="Child task using CrewAI",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        parent_id=parent_task.id
    )
    
    # Create a non-CrewAI child task
    normal_task = task_manager.create_task(
        name="Normal Task",
        description="Child task without CrewAI",
        parent_id=parent_task.id
    )
    
    # Create a child task of the CrewAI task
    crewai_child = task_manager.create_task(
        name="CrewAI Child",
        description="Child of the CrewAI task",
        framework="crewai",
        crewai_config_id=crewai_config.id,
        parent_id=crewai_task.id
    )
    
    # Get the task tree
    task_tree = task_manager.get_task_tree()
    
    # Validate tree structure
    assert len(task_tree.roots) == 1, "Should have one root node"
    assert len(task_tree.roots[0].children) == 2, "Root should have two children"
    assert len(task_tree.get_node_by_id(crewai_task.id).children) == 1, "CrewAI task should have one child"
    
    # Test execution with mixed task types
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure mock to return successful results
        mock_run_crew_task.return_value = {
            "status": "success",
            "response": "Mocked CrewAI task result"
        }
        
        # Create a mock for running normal tasks
        with patch.object(TaskNode, 'run') as mock_run:
            # Let normal task execution use the default implementation
            mock_run.side_effect = lambda *args, **kwargs: TaskNode.run(task_tree.get_node_by_id(normal_task.id), *args, **kwargs)
            
            # Create the task runner
            task_runner = TaskRunner(task_tree)
            
            # Run the tasks
            task_results = task_runner.run_tasks({})
            
            # Validate results
            assert len(task_results) == 4, "Should have results for all four tasks"
            assert mock_run_crew_task.call_count == 2, "run_crew_task should be called for the two CrewAI tasks"
            
            # Verify all tasks have results
            for task_id in [parent_task.id, crewai_task.id, normal_task.id, crewai_child.id]:
                assert task_id in task_results, f"Task {task_id} should have results"
                assert task_results[task_id]["status"] == "success", f"Task {task_id} should have succeeded"
    
    logger.info("Mixed task types test successful") 
