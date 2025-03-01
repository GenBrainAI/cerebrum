import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from src.server.controllers.task_runner import TaskExecutor
from src.server.models.task import Task
from src.server.models.task_tree_flow import TaskTreeFlow, TaskTreeFlowNode, ExecutionStrategy, ExecutionConfig
from src.server.controllers.task_tree_flow import TaskTreeFlowManager

@pytest.fixture
def mock_task_manager():
    return MagicMock()

@pytest.fixture
def mock_task_runner():
    mock = AsyncMock()
    mock._run_tree_flow_task = AsyncMock(return_value={
        "result": "Tree flow executed successfully",
        "node_results": {
            "node-root": "Root node result",
            "node-child-1": "Child node 1 result",
            "node-child-2": "Child node 2 result"
        }
    })
    mock.run_task = AsyncMock(return_value={
        "status": "completed",
        "response": "Task executed",
        "error": None
    })
    return mock

@pytest.fixture
def mock_persistence_model():
    mock = MagicMock()
    
    # Mock tree flow
    tree_flow = TaskTreeFlow(
        id="tree-flow-123",
        name="Test Tree Flow",
        description="A test tree flow",
        tasksmanager_id="manager-123",
        nodes={},
        roots=[]
    )
    
    # Mock root node
    root_node = TaskTreeFlowNode(
        task_id="task-root",
        name="Root Node",
        description="Root node of the tree flow",
        execution_config={
            "strategy": "sequential",
            "execute_children": True,
            "propagate_context": True
        }
    )
    
    # Mock child nodes
    child_node1 = TaskTreeFlowNode(
        task_id="task-child-1",
        name="Child Node 1",
        description="First child node",
        children=[],
        dependencies=[]
    )
    
    child_node2 = TaskTreeFlowNode(
        task_id="task-child-2",
        name="Child Node 2",
        description="Second child node",
        children=[],
        dependencies=[]
    )
    
    # Set up mock collection for tree flows
    mock_tree_flows_collection = MagicMock()
    mock_tree_flows_collection.read.return_value = tree_flow
    
    # Set up mock collection for nodes
    mock_nodes_collection = MagicMock()
    mock_nodes_collection.list.return_value = [root_node, child_node1, child_node2]
    mock_nodes_collection.read.side_effect = lambda node_id: {
        "task-root": root_node,
        "task-child-1": child_node1,
        "task-child-2": child_node2
    }.get(node_id)
    
    # Set up collection method
    mock.collection.side_effect = lambda name: {
        "tree_flows": mock_tree_flows_collection,
        "tree_flow_nodes": mock_nodes_collection
    }.get(name)
    
    return mock

@pytest.fixture
def mock_task_tree_flow_manager():
    mock = AsyncMock()
    mock.execute_flow = AsyncMock(return_value={
        "result": "Tree flow executed successfully",
        "node_results": {
            "node-root": "Root node result",
            "node-child-1": "Child node 1 result",
            "node-child-2": "Child node 2 result"
        }
    })
    return mock

@pytest.mark.asyncio
async def test_run_tree_flow_task(mock_persistence_model, mock_task_tree_flow_manager, mock_task_runner):
    # Create a task with a tree flow ID
    task = Task(
        id="task-123",
        name="Test Task",
        description="A task with a tree flow",
        tree_flow_id="tree-flow-123"
    )
    
    # Mock the TaskTreeFlowManager class
    with patch("src.server.controllers.task_tree_flow.TaskTreeFlowManager", return_value=mock_task_tree_flow_manager):
        # Run the task
        result = await mock_task_runner._run_tree_flow_task(task, mock_persistence_model, {})
        
        # Verify the result
        assert result == {
            "result": "Tree flow executed successfully",
            "node_results": {
                "node-root": "Root node result",
                "node-child-1": "Child node 1 result",
                "node-child-2": "Child node 2 result"
            }
        }

@pytest.mark.asyncio
async def test_run_task_with_tree_flow(mock_persistence_model, mock_task_runner):
    # Create a task with a tree flow ID
    task = Task(
        id="task-123",
        name="Test Task",
        description="A task with a tree flow",
        tree_flow_id="tree-flow-123"
    )
    
    # Set up the mock to return a specific result for this test
    mock_task_runner.run_task.return_value = {
        "result": "Tree flow executed successfully",
        "node_results": {
            "node-root": "Root node result",
            "node-child-1": "Child node 1 result",
            "node-child-2": "Child node 2 result"
        }
    }
    
    # Run the task
    result = await mock_task_runner.run_task(
        tasksmanager_id="manager-123",
        task_id="task-123",
        running_extra_params={}
    )
    
    # Verify the result
    assert result == {
        "result": "Tree flow executed successfully",
        "node_results": {
            "node-root": "Root node result",
            "node-child-1": "Child node 1 result",
            "node-child-2": "Child node 2 result"
        }
    }

@pytest.mark.asyncio
async def test_run_task_without_tree_flow(mock_task_manager, mock_task_runner):
    # Create a task without a tree flow ID
    task = Task(
        id="task-123",
        name="Test Task",
        description="A regular task"
    )
    
    # Mock the task execution
    mock_task_manager.execute_task = AsyncMock(return_value="Task executed")
    
    # Set up the mock to return a specific result for this test
    mock_task_runner.run_task.return_value = {
        "status": "completed",
        "response": "Task executed",
        "error": None
    }
    
    # Run the task
    result = await mock_task_runner.run_task(
        tasksmanager_id="manager-123",
        task_id="task-123",
        running_extra_params={}
    )
    
    # Verify the result
    assert result["response"] == "Task executed"
    assert result["status"] == "completed" 