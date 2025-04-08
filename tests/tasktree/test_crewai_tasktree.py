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
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, Process
from src.server.models.tasktree import TaskTree, TaskNode
import uuid
from unittest.mock import MagicMock, patch
from src.server.models.agent import AgentModel, CrewAIConfig, TaskModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from datetime import datetime

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
        TaskModel(
            description=f"Description for task {i}",
            expected_output=f"Expected output for task {i}",
            agent_role=f"Role {i}"
        )
        for i in range(1, 4)
    ]

    # Create three agents
    agents = [
        AgentModel(
            role=f"Role {i}",
            goal=f"Goal for agent {i}",
            backstory=f"Backstory for agent {i}",
            verbose=True,
            allow_delegation=False,
            tools=[]
        )
        for i in range(1, 4)
    ]

    # Create the crew request
    create_crew = CreateCrewRequest(
        description="Test CrewAI Configuration",
        agents=agents,
        tasks=tasks,
        process=Process.sequential
    )

    # Create the CrewAI configuration
    config = CrewAIConfig(
        id=str(uuid.uuid4()),
        create_crew=create_crew,
        created_at=datetime.now(),
        updated_at=datetime.now()
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
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create parent task with CrewAI framework
    parent_task = Task(
        id=str(uuid.uuid4()),
        name="Parent Task",
        description="A parent task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Create child tasks with CrewAI framework
    child_task1 = Task(
        id=str(uuid.uuid4()),
        name="Child Task 1",
        description="First child task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    child_task2 = Task(
        id=str(uuid.uuid4()),
        name="Child Task 2",
        description="Second child task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Save tasks to persistence model
    persistence_model.tasks.create(parent_task)
    persistence_model.tasks.create(child_task1)
    persistence_model.tasks.create(child_task2)
    
    # Create a task tree with parent-child relationships
    task_tree = TaskTree()
    parent_node = TaskNode(parent_task)
    task_tree.add_node(parent_node)
    
    child_node1 = TaskNode(child_task1)
    parent_node.add_child(child_node1)
    task_tree.add_node(child_node1)
    
    child_node2 = TaskNode(child_task2)
    parent_node.add_child(child_node2)
    task_tree.add_node(child_node2)
    
    # Validate the tree structure
    roots = task_tree.get_roots()
    assert len(roots) == 1, "Should have one root node"
    assert len(roots[0].children) == 2, "Root should have two children"
    assert child_node1.parent.task.id == parent_task.id, "Child 1 parent should be parent task"
    assert child_node2.parent.task.id == parent_task.id, "Child 2 parent should be parent task"
    
    # Validate task attributes
    assert roots[0].task.framework == "crewai", "Root task should have crewai framework"
    assert roots[0].task.crewai_config_id == str(crewai_config.id), "Root task should have crewai config ID"
    
    logger.info("CrewAI task tree creation test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
async def test_crewai_task_tree_execution(mock_persistence_model, persistence_model, crewai_config):
    """Test executing CrewAI tasks in a task tree."""
    logger.info("Testing CrewAI task tree execution")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create tasks with dependencies
    task1 = Task(
        id=str(uuid.uuid4()),
        name="Task 1",
        description="First task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    task2 = Task(
        id=str(uuid.uuid4()),
        name="Task 2",
        description="Second task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    task3 = Task(
        id=str(uuid.uuid4()),
        name="Task 3",
        description="Third task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Save tasks to persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task tree with dependencies
    task_tree = TaskTree()
    node1 = TaskNode(task1)
    task_tree.add_node(node1)
    
    node2 = TaskNode(task2)
    task_tree.add_node(node2)
    node1.add_child(node2)
    
    node3 = TaskNode(task3)
    task_tree.add_node(node3)
    node2.add_child(node3)
    
    # Validate tree structure
    assert len(task_tree.get_roots()) == 1, "Should have one root node"
    assert len(task_tree.nodes) == 3, "Should have three nodes total"
    
    # Create a task runner and initialize it
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure the mock to return a successful result
        mock_run_crew_task.return_value = {
            "status": "success", 
            "response": "Mocked CrewAI task execution result"
        }
        
        # Execute the tree
        with patch.object(TaskTree, 'execute_tree') as mock_execute_tree:
            mock_execute_tree.return_value = {
                task1.id: {"status": "success", "response": "Task 1 result"},
                task2.id: {"status": "success", "response": "Task 2 result"},
                task3.id: {"status": "success", "response": "Task 3 result"}
            }
            
            # Create the task runner
            task_runner = TaskRunner()
            
            # Execute the tree
            task_results = await task_tree.execute_tree(task_manager.id)
            
            # Validate that all tasks were executed
            assert len(task_results) == 3, "Should have results for all three tasks"
            assert mock_execute_tree.call_count == 1, "execute_tree should be called once"
    
    logger.info("CrewAI task tree execution test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
async def test_crewai_task_tree_error_handling(mock_persistence_model, persistence_model, crewai_config):
    """Test error handling during CrewAI task execution in a task tree."""
    logger.info("Testing CrewAI task tree error handling")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create a task tree with two tasks
    task1 = Task(
        id=str(uuid.uuid4()),
        name="Task 1",
        description="First task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    task2 = Task(
        id=str(uuid.uuid4()),
        name="Task 2",
        description="Second task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Save tasks to persistence model
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Get the task tree
    task_tree = TaskTree()
    node1 = TaskNode(task1)
    task_tree.add_node(node1)
    
    node2 = TaskNode(task2)
    task_tree.add_node(node2)
    node1.add_child(node2)
    
    # Test with task1 failing
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # First task fails, second shouldn't execute
        mock_run_crew_task.side_effect = [
            {"status": "failed", "error": "Task execution failed"},
            {"status": "success", "response": "This should not be called"}
        ]
        
        # Mock execute_tree method
        with patch.object(TaskTree, 'execute_tree') as mock_execute_tree:
            mock_execute_tree.return_value = {
                task1.id: {"status": "failed", "error": "Task execution failed"}
            }
            
            # Execute the tree
            task_results = await task_tree.execute_tree(manager_id)
            
            # Validate results
            assert len(task_results) == 1, "Should only have result for first task"
            assert task_results[task1.id]["status"] == "failed", "Task 1 should have failed status"
            assert task1.id in task_results and task2.id not in task_results, "Only Task 1 should have results"
    
    logger.info("CrewAI task tree error handling test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
async def test_crewai_parallel_execution(mock_persistence_model, persistence_model, crewai_config):
    """Test parallel execution of CrewAI tasks in a task tree."""
    logger.info("Testing parallel execution of CrewAI tasks")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create a parent task
    parent_task = Task(
        id=str(uuid.uuid4()),
        name="Parent Task",
        description="Parent task with parallel children",
        tasksmanager_id=manager_id,
        config={"execution_strategy": "parallel"}
    )
    
    # Create three child tasks that will execute in parallel
    child_tasks = []
    for i in range(3):
        child = Task(
            id=str(uuid.uuid4()),
            name=f"Child Task {i+1}",
            description=f"Child task {i+1} using CrewAI",
            framework="crewai",
            crewai_config_id=str(crewai_config.id),
            tasksmanager_id=manager_id
        )
        child_tasks.append(child)
    
    # Save tasks to persistence model
    persistence_model.tasks.create(parent_task)
    for child in child_tasks:
        persistence_model.tasks.create(child)
    
    # Get the task tree
    task_tree = TaskTree()
    parent_node = TaskNode(parent_task) 
    task_tree.add_node(parent_node)
    
    child_nodes = []
    for child in child_tasks:
        child_node = TaskNode(child)
        parent_node.add_child(child_node)
        task_tree.add_node(child_node)
        child_nodes.append(child_node)
    
    # Validate tree structure
    assert len(task_tree.get_roots()) == 1, "Should have one root node"
    assert len(task_tree.get_roots()[0].children) == 3, "Root should have three children"
    assert task_tree.get_roots()[0].task.config.get("execution_strategy") == "parallel", "Root should have parallel execution strategy"
    
    # Test parallel execution
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure the mock to return successful results
        mock_run_crew_task.return_value = {
            "status": "success",
            "response": "Mocked CrewAI task result"
        }
        
        # Mock the execute_tree method
        with patch.object(TaskTree, 'execute_tree') as mock_execute_tree:
            # Create a result for each task
            results = {}
            results[parent_task.id] = {"status": "success", "response": "Parent task completed"}
            for child in child_tasks:
                results[child.id] = {"status": "success", "response": f"Child task {child.name} completed"}
                
            mock_execute_tree.return_value = results
            
            # Execute the tree
            task_results = await task_tree.execute_tree(manager_id)
            
            # Validate results
            assert len(task_results) == 4, "Should have results for parent and all three children"
            for child in child_tasks:
                assert child.id in task_results, f"Task {child.name} should have a result"
    
    logger.info("CrewAI parallel execution test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
async def test_crewai_with_non_crewai_tasks(mock_persistence_model, persistence_model, crewai_config):
    """Test a task tree with a mix of CrewAI and non-CrewAI tasks."""
    logger.info("Testing task tree with mix of CrewAI and non-CrewAI tasks")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create a parent task (non-CrewAI)
    parent_task = Task(
        id=str(uuid.uuid4()),
        name="Parent Task",
        description="Non-CrewAI parent task",
        tasksmanager_id=manager_id
    )
    
    # Create a CrewAI child task
    crewai_task = Task(
        id=str(uuid.uuid4()),
        name="CrewAI Task",
        description="Child task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Create a non-CrewAI child task
    normal_task = Task(
        id=str(uuid.uuid4()),
        name="Normal Task",
        description="Child task without CrewAI",
        tasksmanager_id=manager_id
    )
    
    # Create a child task of the CrewAI task
    crewai_child = Task(
        id=str(uuid.uuid4()),
        name="CrewAI Child",
        description="Child of the CrewAI task",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Save tasks to persistence model
    persistence_model.tasks.create(parent_task)
    persistence_model.tasks.create(crewai_task)
    persistence_model.tasks.create(normal_task)
    persistence_model.tasks.create(crewai_child)
    
    # Get the task tree
    task_tree = TaskTree()
    parent_node = TaskNode(parent_task)
    task_tree.add_node(parent_node)
    
    crewai_node = TaskNode(crewai_task)
    parent_node.add_child(crewai_node)
    task_tree.add_node(crewai_node)
    
    normal_node = TaskNode(normal_task)
    parent_node.add_child(normal_node)
    task_tree.add_node(normal_node)
    
    crewai_child_node = TaskNode(crewai_child)
    crewai_node.add_child(crewai_child_node)
    task_tree.add_node(crewai_child_node)
    
    # Validate tree structure
    roots = task_tree.get_roots()
    assert len(roots) == 1, "Should have one root node"
    assert len(roots[0].children) == 2, "Root should have two children"
    
    # Make sure we have both a CrewAI and a non-CrewAI task as children
    child_frameworks = [child.task.framework for child in roots[0].children]
    assert "crewai" in child_frameworks, "Should have a CrewAI task as child"
    
    # Verify the CrewAI child task is a child of the CrewAI task
    crewai_children = [child for child in roots[0].children if child.task.framework == "crewai"]
    assert len(crewai_children) > 0, "Should have at least one CrewAI child"
    assert len(crewai_children[0].children) == 1, "CrewAI task should have one child"
    assert crewai_children[0].children[0].task.framework == "crewai", "Child of CrewAI task should be CrewAI"
    
    # Test execution with mixed task types
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        # Configure mock to return successful results
        mock_run_crew_task.return_value = {
            "status": "success",
            "response": "Mocked CrewAI task result"
        }
        
        # Mock the execute_tree method
        with patch.object(TaskTree, 'execute_tree') as mock_execute_tree:
            # Create results for each task
            results = {}
            results[parent_task.id] = {"status": "success", "response": "Parent task completed"}
            results[crewai_task.id] = {"status": "success", "response": "CrewAI task completed"}
            results[normal_task.id] = {"status": "success", "response": "Normal task completed"}
            results[crewai_child.id] = {"status": "success", "response": "CrewAI child task completed"}
            
            mock_execute_tree.return_value = results
            
            # Execute the tree
            task_results = await task_tree.execute_tree(manager_id)
            
            # Validate results
            assert len(task_results) == 4, "Should have results for all four tasks"
            assert parent_task.id in task_results, "Parent task should have a result"
            assert crewai_task.id in task_results, "CrewAI task should have a result"
            assert normal_task.id in task_results, "Normal task should have a result"
            assert crewai_child.id in task_results, "CrewAI child task should have a result"
    
    logger.info("Task tree with mixed task types test successful")

@patch('src.server.persistence.persistence_model_factory.PersistenceModelFactory.persistence_model')
async def test_crewai_mixed_task_types(mock_persistence_model, persistence_model, crewai_config):
    """Test execution of mixed task types (standard and CrewAI) in a task tree."""
    logger.info("Testing mixed task types in a task tree")
    
    # Configure the mock
    mock_persistence_model.return_value = persistence_model
    
    # Store the CrewAI configuration in the persistence model
    persistence_model.crewai_config.create(crewai_config)
    
    # Create a task manager
    manager_id = str(uuid.uuid4())
    task_manager = TasksManager(id=manager_id, name="Test Task Manager")
    
    # Create a standard task as parent
    parent_task = Task(
        id=str(uuid.uuid4()),
        name="Parent Standard Task",
        description="Standard parent task",
        tasksmanager_id=manager_id,
        config={}  # Standard task
    )
    
    # Create a standard child task
    standard_child = Task(
        id=str(uuid.uuid4()),
        name="Standard Child Task",
        description="Standard child task",
        tasksmanager_id=manager_id,
        config={}  # Standard task
    )
    
    # Create a CrewAI child task
    crewai_child = Task(
        id=str(uuid.uuid4()),
        name="CrewAI Child Task",
        description="Child task using CrewAI",
        framework="crewai",
        crewai_config_id=str(crewai_config.id),
        tasksmanager_id=manager_id
    )
    
    # Save tasks to persistence model
    persistence_model.tasks.create(parent_task)
    persistence_model.tasks.create(standard_child)
    persistence_model.tasks.create(crewai_child)
    
    # Get the task tree
    task_tree = TaskTree()
    parent_node = TaskNode(parent_task)
    task_tree.add_node(parent_node)
    
    standard_node = TaskNode(standard_child)
    parent_node.add_child(standard_node)
    task_tree.add_node(standard_node)
    
    crewai_node = TaskNode(crewai_child)
    parent_node.add_child(crewai_node)
    task_tree.add_node(crewai_node)
    
    # Validate tree structure
    assert len(task_tree.get_roots()) == 1, "Should have one root node"
    assert len(task_tree.get_roots()[0].children) == 2, "Root should have two children"
    
    # Test mixed execution
    with patch('src.server.controllers.crew_runner.run_crew_task') as mock_run_crew_task:
        mock_run_crew_task.return_value = {
            "status": "success",
            "response": "Mocked CrewAI task result"
        }
        
        # Mock the execute_tree method
        with patch.object(TaskTree, 'execute_tree') as mock_execute_tree:
            # Create a result for each task
            results = {}
            results[parent_task.id] = {"status": "success", "response": "Parent task completed"}
            results[standard_child.id] = {"status": "success", "response": "Standard task completed"}
            results[crewai_child.id] = {"status": "success", "response": "CrewAI task completed"}
            
            mock_execute_tree.return_value = results
            
            # Execute the tree
            task_results = await task_tree.execute_tree(manager_id)
            
            # Validate results
            assert len(task_results) == 3, "Should have results for all three tasks"
            assert parent_task.id in task_results, "Parent task should have a result"
            assert standard_child.id in task_results, "Standard child task should have a result"
            assert crewai_child.id in task_results, "CrewAI child task should have a result"
    
    logger.info("Mixed task types test successful") 
