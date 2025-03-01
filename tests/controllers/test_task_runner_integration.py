import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.task_tree_flow import TaskTreeFlow, TaskTreeFlowNode, ExecutionStrategy, ExecutionConfig
from src.server.controllers.task_tree_flow import TaskTreeFlowManager
from src.server.models.tasks_manager import TasksManager


class MockCollection:
    """Mock collection for testing."""
    
    def __init__(self, persistence_model, collection_name: str):
        self.persistence_model = persistence_model
        self.collection_name = collection_name
    
    def create(self, data: any) -> None:
        """Create an item in the collection."""
        self.persistence_model.create(self.collection_name, data.id, data)
    
    def read(self, id: str) -> any:
        """Read an item from the collection."""
        return self.persistence_model.read(self.collection_name, id)
    
    def update(self, id: str, data: any) -> None:
        """Update an item in the collection."""
        self.persistence_model.update(self.collection_name, id, data)
    
    def delete(self, id: str) -> None:
        """Delete an item from the collection."""
        self.persistence_model.delete(self.collection_name, id)
    
    def list(self) -> list:
        """List all items in the collection."""
        return self.persistence_model.list(self.collection_name)


class MockPersistenceModel:
    """Mock persistence model for testing."""
    
    def __init__(self):
        self.data = {}
        self.tasksmanagers = MagicMock()
        self.tasks = MagicMock()
    
    def create(self, collection: str, id: str, data: any) -> None:
        """Create an item in the collection."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
    
    def read(self, collection: str, id: str) -> any:
        """Read an item from the collection."""
        if collection not in self.data:
            return None
        return self.data[collection].get(id)
    
    def update(self, collection: str, id: str, data: any) -> None:
        """Update an item in the collection."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
    
    def delete(self, collection: str, id: str) -> None:
        """Delete an item from the collection."""
        if collection in self.data and id in self.data[collection]:
            del self.data[collection][id]
    
    def list(self, collection: str) -> list:
        """List all items in the collection."""
        if collection not in self.data:
            return []
        return list(self.data[collection].keys())
    
    def collection(self, collection_name: str) -> MockCollection:
        """Get a collection by name."""
        return MockCollection(self, collection_name)


class TestTaskRunnerIntegration:
    """Integration tests for TaskRunner with TaskTreeFlow."""

    @pytest.fixture
    def persistence_model(self):
        """Create a mock persistence model for testing."""
        model = MockPersistenceModel()
        
        # Create a tasks manager
        tasksmanager = TasksManager(
            id="manager-123",
            name="Test Manager",
            description="Test tasks manager for integration testing",
            model="gpt-4o-mini"
        )
        model.tasksmanagers.read.return_value = tasksmanager
        
        # Create a task with a tree flow ID
        task_with_flow = Task(
            id="task-with-flow",
            name="Task with Tree Flow",
            description="A task that uses a tree flow",
            tasksmanager_id="manager-123",
            tree_flow_id="tree-flow-123"
        )
        
        # Create a regular task without a tree flow ID
        regular_task = Task(
            id="regular-task",
            name="Regular Task",
            description="A regular task without a tree flow",
            tasksmanager_id="manager-123"
        )
        
        # Set up the tasks mock to return the appropriate task based on the ID
        def mock_read_task(task_id):
            if task_id == "task-with-flow":
                return task_with_flow
            elif task_id == "regular-task":
                return regular_task
            return None
        
        model.tasks.read.side_effect = mock_read_task
        
        # Create a tree flow
        tree_flow = TaskTreeFlow(
            id="tree-flow-123",
            name="Test Tree Flow",
            description="A test tree flow for integration testing",
            tasksmanager_id="manager-123",
            nodes={},
            roots=["root-node"]
        )
        
        # Create nodes for the tree flow
        root_node = TaskTreeFlowNode(
            task_id="root-task",
            name="Root Task",
            description="The root task of the tree flow",
            aggregator_type="all",
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            },
            children=["child-task-1", "child-task-2"],
            dependencies=[]
        )
        
        child_node1 = TaskTreeFlowNode(
            task_id="child-task-1",
            name="Child Task 1",
            description="First child task",
            aggregator_type="all",
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            },
            children=[],
            dependencies=[]
        )
        
        child_node2 = TaskTreeFlowNode(
            task_id="child-task-2",
            name="Child Task 2",
            description="Second child task",
            aggregator_type="all",
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            },
            children=[],
            dependencies=[]
        )
        
        # Store the tree flow and nodes in the mock persistence model
        model.create("tree_flows", "tree-flow-123", tree_flow)
        model.create("tree_flow_nodes", "root-node", root_node)
        model.create("tree_flow_nodes", "child-task-1", child_node1)
        model.create("tree_flow_nodes", "child-task-2", child_node2)
        
        # Update the tree flow with the nodes
        tree_flow.nodes = {
            "root-node": root_node,
            "child-task-1": child_node1,
            "child-task-2": child_node2
        }
        model.update("tree_flows", "tree-flow-123", tree_flow)
        
        return model

    @pytest.fixture
    def task_runner(self, persistence_model):
        """Create a TaskRunner instance with a mock persistence model."""
        runner = TaskRunner(persistence_model)
        # Mock the initialize method to avoid actual initialization
        runner.initialize = AsyncMock()
        return runner

    @pytest.mark.asyncio
    async def test_run_task_with_tree_flow(self, task_runner, persistence_model):
        """Test that TaskRunner correctly handles a task with a tree flow."""
        # Mock the TaskTreeFlowManager.execute_tree method to return a predictable result
        # This avoids having to set up real tasks that can be executed
        with patch.object(TaskTreeFlowManager, 'execute_tree', new_callable=AsyncMock) as mock_execute_tree, \
             patch.object(TaskTreeFlowManager, 'initialize', new_callable=AsyncMock) as mock_initialize, \
             patch.object(TaskTreeFlowManager, 'create_from_model', return_value=None) as mock_create_from_model:
            
            # Set up the mock to return a specific result
            mock_execute_tree.return_value = {
                "result": "Tree flow executed successfully",
                "node_results": {
                    "root-node": "Root node result",
                    "child-task-1": "Child node 1 result",
                    "child-task-2": "Child node 2 result"
                }
            }
            
            # Initialize the task runner
            await task_runner.initialize()
            
            # Run the task with a tree flow
            result = await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="task-with-flow",
                running_extra_params={"test_param": "test_value"}
            )
            
            # Verify that TaskTreeFlowManager.execute_tree was called
            mock_execute_tree.assert_called_once()
            
            # Verify that the result contains the expected tree flow execution results
            assert "result" in result
            assert "Tree flow executed successfully" in str(result)

    @pytest.mark.asyncio
    async def test_run_regular_task(self, task_runner, persistence_model):
        """Test that TaskRunner correctly handles a regular task without a tree flow."""
        # Mock the standard task execution to return a predictable result
        with patch.object(task_runner, '_run_standard_task', new_callable=AsyncMock) as mock_run_standard_task:
            # Set up the mock to return a specific result
            mock_run_standard_task.return_value = {
                "status": "completed",
                "response": "Regular task executed",
                "error": None
            }
            
            # Initialize the task runner
            await task_runner.initialize()
            
            # Run a regular task without a tree flow
            result = await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="regular-task",
                running_extra_params={"test_param": "test_value"}
            )
            
            # Verify that _run_standard_task was called
            mock_run_standard_task.assert_called_once()
            
            # Verify that the result contains the expected standard task execution results
            assert result["status"] == "completed"
            assert result["response"] == "Regular task executed"

    @pytest.mark.asyncio
    async def test_task_execution_branching_logic(self, task_runner, persistence_model):
        """Test that TaskRunner correctly branches between tree flow and standard execution."""
        # Create mocks for both execution paths
        with patch.object(task_runner, '_run_tree_flow_task', new_callable=AsyncMock) as mock_tree_flow_task, \
             patch.object(task_runner, '_run_standard_task', new_callable=AsyncMock) as mock_standard_task:
            
            # Set up the mocks to return specific results
            mock_tree_flow_task.return_value = {
                "result": "Tree flow executed",
                "node_results": {}
            }
            mock_standard_task.return_value = {
                "status": "completed",
                "response": "Standard task executed",
                "error": None
            }
            
            # Initialize the task runner
            await task_runner.initialize()
            
            # Run a task with a tree flow
            await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="task-with-flow",
                running_extra_params={}
            )
            
            # Run a regular task
            await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="regular-task",
                running_extra_params={}
            )
            
            # Verify that _run_tree_flow_task was called for the task with a tree flow
            mock_tree_flow_task.assert_called_once()
            
            # Verify that _run_standard_task was called for the regular task
            mock_standard_task.assert_called_once()
            
            # Verify that the correct methods were called with the correct tasks
            tree_flow_task_arg = mock_tree_flow_task.call_args[0][0]
            standard_task_arg = mock_standard_task.call_args[0][0]
            
            assert tree_flow_task_arg.id == "task-with-flow"
            assert tree_flow_task_arg.tree_flow_id == "tree-flow-123"
            
            assert standard_task_arg.id == "regular-task"
            assert standard_task_arg.tree_flow_id is None 