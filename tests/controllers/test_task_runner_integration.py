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
        """Create a mock persistence model with test data."""
        model = MockPersistenceModel()
        
        # Create mock task manager
        manager = MagicMock(spec=TasksManager)
        manager.id = "manager-123"
        manager.name = "Test Manager"
        model.create("tasksmanagers", "manager-123", manager)
        
        # Create mock tasks
        task_with_flow = MagicMock(spec=Task)
        task_with_flow.id = "task-with-flow"
        task_with_flow.name = "Task with Tree Flow"
        task_with_flow.tasksmanager_id = "manager-123"
        task_with_flow.framework = "standard"  # Standard framework
        task_with_flow.tree_flow_id = "tree-flow-123"  # Has tree flow ID
        task_with_flow.curried_proxy_id = None
        task_with_flow.crewai_config_id = None
        task_with_flow.data = {}
        task_with_flow.status = "pending"
        
        regular_task = MagicMock(spec=Task)
        regular_task.id = "regular-task"
        regular_task.name = "Regular Task"
        regular_task.tasksmanager_id = "manager-123"
        regular_task.framework = "standard"  # Standard framework
        regular_task.tree_flow_id = None  # No tree flow ID
        regular_task.curried_proxy_id = None
        regular_task.crewai_config_id = None
        regular_task.data = {}
        regular_task.status = "pending"
        
        model.create("tasks", "task-with-flow", task_with_flow)
        model.create("tasks", "regular-task", regular_task)
        
        # Override the read method to handle task-specific attributes
        def mock_read_task(task_id):
            if task_id == "task-with-flow":
                return task_with_flow
            elif task_id == "regular-task":
                return regular_task
            else:
                return None
                
        model.tasks.read = mock_read_task
        
        # Create mock tree flow
        tree_flow = MagicMock()
        tree_flow.id = "tree-flow-123"
        tree_flow.name = "Test Tree Flow"
        
        # Create mock tree flow nodes
        root_node = MagicMock()
        root_node.id = "root-node"
        root_node.name = "Root Node"
        root_node.children = ["child-task-1", "child-task-2"]
        
        child_node1 = MagicMock()
        child_node1.id = "child-task-1"
        child_node1.name = "Child Task 1"
        child_node1.children = []
        
        child_node2 = MagicMock()
        child_node2.id = "child-task-2"
        child_node2.name = "Child Task 2"
        child_node2.children = []
        
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
        # Mock both _run_tree_flow_task and _run_standard_task to ensure we can check which one is called
        with patch.object(task_runner, '_run_tree_flow_task', new_callable=AsyncMock) as mock_tree_flow_task, \
             patch.object(task_runner, '_run_standard_task', new_callable=AsyncMock) as mock_standard_task:
            
            # Set up the mocks to return specific results
            mock_tree_flow_task.return_value = {
                "result": "Tree flow executed successfully",
                "node_results": {
                    "root-node": "Root node result",
                    "child-task-1": "Child node 1 result",
                    "child-task-2": "Child node 2 result"
                }
            }
            
            # Make sure initialize is mocked and returns True
            task_runner.initialize = AsyncMock(return_value=True)
            task_runner._initialized = True
            
            # Run the task with a tree flow
            result = await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="task-with-flow",
                running_extra_params={"test_param": "test_value"}
            )
            
            # Verify that _run_tree_flow_task was called
            mock_tree_flow_task.assert_called_once()
            
            # Verify _run_standard_task was NOT called
            mock_standard_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_regular_task(self, task_runner, persistence_model):
        """Test that TaskRunner correctly handles a regular task without a tree flow."""
        # Mock both _run_tree_flow_task and _run_standard_task to ensure we can check which one is called
        with patch.object(task_runner, '_run_tree_flow_task', new_callable=AsyncMock) as mock_tree_flow_task, \
             patch.object(task_runner, '_run_standard_task', new_callable=AsyncMock) as mock_standard_task:
            
            # Set up the mocks to return specific results
            mock_standard_task.return_value = {
                "status": "completed",
                "response": "Regular task executed",
                "error": None
            }
            
            # Make sure initialize is mocked and returns True
            task_runner.initialize = AsyncMock(return_value=True)
            task_runner._initialized = True
            
            # Run a regular task without a tree flow
            result = await task_runner.run_task(
                tasksmanager_id="manager-123",
                task_id="regular-task",
                running_extra_params={"test_param": "test_value"}
            )
            
            # Verify that _run_standard_task was called
            mock_standard_task.assert_called_once()
            
            # Verify _run_tree_flow_task was NOT called
            mock_tree_flow_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_task_execution_branching_logic(self, task_runner, persistence_model):
        """Test that TaskRunner correctly branches between tree flow and standard execution."""
        # Mock both _run_tree_flow_task and _run_standard_task to ensure we can check which one is called
        with patch.object(task_runner, '_run_tree_flow_task', new_callable=AsyncMock) as mock_tree_flow_task, \
             patch.object(task_runner, '_run_standard_task', new_callable=AsyncMock) as mock_standard_task, \
             patch.object(task_runner, '_run_crewai_task', new_callable=AsyncMock) as mock_crewai_task:
            
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
            
            # Make sure initialize is mocked and returns True
            task_runner.initialize = AsyncMock(return_value=True)
            task_runner._initialized = True
            
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
            
            # Verify the correct methods were called
            assert mock_tree_flow_task.call_count == 1
            assert mock_standard_task.call_count == 1 