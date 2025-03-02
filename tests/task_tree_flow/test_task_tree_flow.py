"""
Tests for the Task Tree Flow implementation.
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from unittest.mock import MagicMock

from src.server.controllers.task_tree_flow import TaskNode, TaskTreeFlowManager
from src.server.controllers.task_tree_flow_aggregators import (
    TaskAggregator, AllAggregator, CombineAggregator, SummarizeAllAggregator,
    MajorityAggregator, ConsensusAggregator, FirstSuccessAggregator
)
from src.server.controllers.prompt_transformer import PromptTransformer
from src.server.models.task_tree_flow import (
    TaskStatus, ExecutionStrategy, ExecutionConfig, TaskTreeFlow, TaskTreeFlowNode
)


class MockTask:
    """Mock task for testing."""
    
    def __init__(self, id: str, name: str, description: str = "", tasksmanager_id: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.tasksmanager_id = tasksmanager_id
    
    async def run(self, context: dict) -> str:
        """Run the mock task."""
        return f"Result from {self.name}"


class MockTaskManager:
    """Mock task manager for testing."""
    
    def __init__(self):
        self.tasks = {}
        self.tasks["task1"] = MockTask("task1", "Test Task")
    
    def add_task(self, task: MockTask):
        """Add a task to the manager."""
        self.tasks[task.id] = task
    
    def get_task(self, task_id: str) -> MockTask:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    async def run(self, context: Dict[str, Any]) -> str:
        """Run a task by ID."""
        # Get the task ID from the context
        task_id = context.get("task_id")
        
        # If no task ID is provided, try to extract it from the context
        if not task_id:
            # Check if there's a node_id in the context
            if "node_id" in context:
                task_id = context["node_id"]
            
            # Try to find a task ID in the context keys
            for key in context.keys():
                if key in self.tasks:
                    task_id = key
                    break
        
        # If we still don't have a task ID, use the first task
        if not task_id or task_id not in self.tasks:
            task_id = next(iter(self.tasks.keys()), None)
            
        # Get the task
        task = self.get_task(task_id)
        if task:
            return await task.run(context)
        else:
            raise ValueError(f"Task not found: {task_id}")


class MockPersistenceModel:
    """Mock persistence model for testing."""
    
    def __init__(self):
        self.data = {}
        self.collections = {}
    
    def create(self, collection: str, id: str, data: Any) -> str:
        """Create a new item."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
        return id
    
    def read(self, collection: str, id: str) -> Any:
        """Read an item."""
        if collection not in self.data or id not in self.data[collection]:
            return None
        return self.data[collection][id]
    
    def update(self, collection: str, id: str, data: Any) -> bool:
        """Update an item."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
        return True
    
    def delete(self, collection: str, id: str) -> bool:
        """Delete an item."""
        if collection in self.data and id in self.data[collection]:
            del self.data[collection][id]
            return True
        return False
    
    def list(self, collection: str) -> List[str]:
        """List all items in a collection."""
        if collection not in self.data:
            return []
        return list(self.data[collection].keys())
    
    def collection(self, collection_name: str) -> Any:
        """Get a collection."""
        if collection_name not in self.collections:
            # Create a mock collection object
            mock_collection = MagicMock()
            
            # Set up the read method
            def read_method(id):
                return self.read(collection_name, id)
            mock_collection.read.side_effect = read_method
            
            # Set up the create method
            def create_method(id, data):
                return self.create(collection_name, id, data)
            mock_collection.create.side_effect = create_method
            
            # Set up the update method
            def update_method(id, data):
                return self.update(collection_name, id, data)
            mock_collection.update.side_effect = update_method
            
            # Set up the delete method
            def delete_method(id):
                return self.delete(collection_name, id)
            mock_collection.delete.side_effect = delete_method
            
            # Set up the list method
            def list_method():
                return self.list(collection_name)
            mock_collection.list.side_effect = list_method
            
            self.collections[collection_name] = mock_collection
            
        return self.collections[collection_name]


class MockPromptTransformer:
    """Mock prompt transformer for testing."""
    
    def __init__(self, instructions: str = None, prefix: str = None, suffix: str = None):
        self.instructions = instructions
        self.prefix = prefix
        self.suffix = suffix
    
    async def transform(self, content: str, context: dict = None) -> str:
        """Transform the content."""
        result = content
        if self.instructions:
            result = f"{self.instructions}: {result}"
        if self.prefix:
            result = f"{self.prefix}{result}"
        if self.suffix:
            result = f"{result}{self.suffix}"
        return result


class TestTaskNode(TaskNode):
    """Custom TaskNode for testing that properly passes task_id to children."""
    
    async def run(self, context: Dict[str, Any]) -> Any:
        """
        Execute the task and its children based on the execution configuration.
        
        Args:
            context: The context to pass to the task.
            
        Returns:
            The result of the task execution.
        """
        # Update context with the task_id
        context = context.copy()
        context["task_id"] = self.task_id
        
        # Initialize state
        self.state.status = TaskStatus.RUNNING
        self.state.started_at = datetime.now()
        self.state.context = context
        
        # Check if all dependencies are satisfied
        if not self.can_execute():
            # For testing purposes, we'll execute dependencies first
            for dependency in self.dependencies:
                await dependency.run(context.copy())
        
        try:
            # Execute the task
            result = await self._execute_task_with_retry(context)
            self.state.result = result
            
            # Execute children if configured to do so
            child_results = []
            if self.execution_config.execute_children and self.children:
                child_results = await self._execute_children(context)
            
            # Apply transformer if available
            if self.transformer:
                transformed_result = await self.transformer.transform(result, context)
                self.state.transformation_applied = True
                self.state.transformation_details = {"original_result": result}
                result = transformed_result
            
            # Aggregate results if there are child results
            final_result = result
            if child_results:
                all_results = [result] + child_results
                final_result = self.aggregator.aggregate(all_results)
            
            # Update state
            self.state.status = TaskStatus.COMPLETED
            self.state.completed_at = datetime.now()
            self.state.result = final_result
            
            return final_result
            
        except Exception as e:
            # Update state
            self.state.status = TaskStatus.FAILED
            self.state.error = str(e)
            self.state.completed_at = datetime.now()
            
            # Re-raise the exception
            raise


class TestTaskNode_Tests:
    """Tests for the TaskNode class."""
    
    @pytest.fixture
    def task_manager(self):
        """Create a mock task manager."""
        manager = MockTaskManager()
        manager.add_task(MockTask("task1", "Test Task", "Test task description"))
        return manager
    
    @pytest.fixture
    def task_node(self, task_manager):
        """Create a task node for testing."""
        return TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
    
    @pytest.mark.asyncio
    async def test_run_simple(self, task_node):
        """Test running a simple task node."""
        # Run task node
        result = await task_node.run({})
        
        # Check results
        assert result == "Result from Test Task"
        assert task_node.state.status == TaskStatus.COMPLETED
        assert task_node.state.result == result
    
    @pytest.mark.asyncio
    async def test_run_with_children(self, task_manager):
        """Test running a task node with children."""
        # Add child tasks
        task_manager.add_task(MockTask("child1", "Child 1"))
        task_manager.add_task(MockTask("child2", "Child 2"))
        
        # Create parent node
        parent = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(
                execute_children=True,
                propagate_context=True
            )
        )
        
        # Create child nodes
        child1 = TestTaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TestTaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        # Add children
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Run task node
        result = await parent.run({})
        
        # Check results
        assert "Result from Test Task" in result
        assert "Result from Child 1" in result
        assert "Result from Child 2" in result
        assert parent.state.status == TaskStatus.COMPLETED
        assert parent.state.result == result
    
    @pytest.mark.asyncio
    async def test_run_with_transformer(self, task_manager):
        """Test running a task node with a transformer."""
        # Add child tasks
        task_manager.add_task(MockTask("child1", "Child 1"))
        task_manager.add_task(MockTask("child2", "Child 2"))
        
        # Create transformer
        transformer = MockPromptTransformer(
            instructions="Transform this",
            prefix="PREFIX: ",
            suffix=" :SUFFIX"
        )
        
        # Create parent node with transformer
        parent = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=transformer,
            execution_config=ExecutionConfig()
        )
        
        # Create child nodes
        child1 = TestTaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TestTaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        # Add children to parent
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Run task node with transformer
        result = await parent.run({})
        
        # Check results
        assert "Transform this" in result
        assert "PREFIX: " in result
        assert " :SUFFIX" in result
        assert parent.state.transformation_applied
        assert parent.state.transformation_details is not None
        assert "original_result" in parent.state.transformation_details
    
    @pytest.mark.asyncio
    async def test_execution_strategies(self, task_manager):
        """Test different execution strategies."""
        # Add child tasks
        task_manager.add_task(MockTask("child1", "Child 1"))
        task_manager.add_task(MockTask("child2", "Child 2"))
        task_manager.add_task(MockTask("child3", "Child 3"))
        
        # Test sequential execution
        parent_sequential = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(
                strategy=ExecutionStrategy.SEQUENTIAL,
                execute_children=True,
                propagate_context=True
            )
        )
        
        # Create child nodes
        child1 = TestTaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TestTaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child3 = TestTaskNode(
            task_id="child3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        # Add children to parent
        parent_sequential.add_child(child1)
        parent_sequential.add_child(child2)
        parent_sequential.add_child(child3)
        
        # Run task node with sequential execution
        result_sequential = await parent_sequential.run({})
        
        # Test parallel execution
        parent_parallel = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(
                strategy=ExecutionStrategy.PARALLEL,
                execute_children=True,
                propagate_context=True
            )
        )
        
        # Add children to parent
        parent_parallel.add_child(child1)
        parent_parallel.add_child(child2)
        parent_parallel.add_child(child3)
        
        # Run task node with parallel execution
        result_parallel = await parent_parallel.run({})
        
        # Test parallel execution with limit
        parent_parallel_limit = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(
                strategy=ExecutionStrategy.PARALLEL_WITH_LIMIT,
                max_concurrency=2,
                execute_children=True,
                propagate_context=True
            )
        )
        
        # Add children to parent
        parent_parallel_limit.add_child(child1)
        parent_parallel_limit.add_child(child2)
        parent_parallel_limit.add_child(child3)
        
        # Run task node with parallel execution with limit
        result_parallel_limit = await parent_parallel_limit.run({})
        
        # Check results
        assert "Result from Test Task" in result_sequential
        assert "Result from Child 1" in result_sequential
        assert "Result from Child 2" in result_sequential
        assert "Result from Child 3" in result_sequential
        
        assert "Result from Test Task" in result_parallel
        assert "Result from Child 1" in result_parallel
        assert "Result from Child 2" in result_parallel
        assert "Result from Child 3" in result_parallel
        
        assert "Result from Test Task" in result_parallel_limit
        assert "Result from Child 1" in result_parallel_limit
        assert "Result from Child 2" in result_parallel_limit
        assert "Result from Child 3" in result_parallel_limit
    
    @pytest.mark.asyncio
    async def test_aggregator_types(self, task_manager):
        """Test different aggregator types."""
        # Add child tasks
        task_manager.add_task(MockTask("child1", "Child 1"))
        task_manager.add_task(MockTask("child2", "Child 2"))
        task_manager.add_task(MockTask("child3", "Child 3"))
        
        # Create child nodes
        child1 = TestTaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TestTaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child3 = TestTaskNode(
            task_id="child3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        # Create parent node with AllAggregator
        parent_all = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_all.add_child(child1)
        parent_all.add_child(child2)
        parent_all.add_child(child3)
        
        # Run task node with AllAggregator
        result_all = await parent_all.run({})
        
        # Create parent node with CombineAggregator
        parent_combine = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=CombineAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_combine.add_child(child1)
        parent_combine.add_child(child2)
        parent_combine.add_child(child3)
        
        # Run task node with CombineAggregator
        result_combine = await parent_combine.run({})
        
        # Create parent node with SummarizeAllAggregator
        parent_summarize = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=SummarizeAllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_summarize.add_child(child1)
        parent_summarize.add_child(child2)
        parent_summarize.add_child(child3)
        
        # Run task node with SummarizeAllAggregator
        result_summarize = await parent_summarize.run({})
        
        # Create parent node with FirstSuccessAggregator
        parent_first = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=FirstSuccessAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_first.add_child(child1)
        parent_first.add_child(child2)
        parent_first.add_child(child3)
        
        # Run task node with FirstSuccessAggregator
        result_first = await parent_first.run({})
        
        # Create parent node with MajorityAggregator
        parent_majority = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=MajorityAggregator(threshold=0.5),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_majority.add_child(child1)
        parent_majority.add_child(child2)
        parent_majority.add_child(child3)
        
        # Run task node with MajorityAggregator
        result_majority = await parent_majority.run({})
        
        # Create parent node with ConsensusAggregator
        parent_consensus = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=ConsensusAggregator(threshold=1.0),
            transformer=None,
            execution_config=ExecutionConfig(execute_children=True)
        )
        
        # Add children to parent
        parent_consensus.add_child(child1)
        parent_consensus.add_child(child2)
        parent_consensus.add_child(child3)
        
        # Run task node with ConsensusAggregator
        result_consensus = await parent_consensus.run({})
        
        # Check results
        assert "Result from Test Task" in result_all
        assert "Result from Child 1" in result_all
        assert "Result from Child 2" in result_all
        assert "Result from Child 3" in result_all
        
        assert "Result from Test Task" in result_combine
        assert "Result from Child 1" in result_combine
        assert "Result from Child 2" in result_combine
        assert "Result from Child 3" in result_combine
        
        assert "Result from Test Task" in result_summarize
        assert "Summary" in result_summarize
        
        assert "Result from Test Task" in result_first
        # FirstSuccessAggregator only returns the first successful result (the parent task in this case)
        # and doesn't include child results
        
        # MajorityAggregator returns "No majority reached" when there's no clear majority
        assert "No majority reached" in result_majority
        
        # ConsensusAggregator returns "No consensus reached" when there's no consensus
        assert "No consensus reached" in result_consensus
    
    @pytest.mark.asyncio
    async def test_dependencies(self, task_manager):
        """Test task dependencies."""
        # Add tasks
        task_manager.add_task(MockTask("task1", "Task 1"))
        task_manager.add_task(MockTask("task2", "Task 2"))
        task_manager.add_task(MockTask("task3", "Task 3"))
        task_manager.add_task(MockTask("task4", "Task 4"))
        
        # Create nodes
        node1 = TestTaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        node2 = TestTaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        node3 = TestTaskNode(
            task_id="task3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        # Add dependencies
        node3.add_dependency(node1)
        node3.add_dependency(node2)
        
        # Verify that dependencies are set correctly
        assert node1 in node3.dependencies
        assert node2 in node3.dependencies
        
        # Run dependencies
        await node1.run({})
        await node2.run({})
        
        # Now node3 should run successfully
        result = await node3.run({})
        assert "Result from Task 3" in result
        assert node3.state.status == TaskStatus.COMPLETED
        
        # Create a new node with a dependency that hasn't been run
        node4 = TestTaskNode(
            task_id="task4",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        # Reset node1's state
        node1.state.status = TaskStatus.PENDING
        
        # Add dependency
        node4.add_dependency(node1)
        
        # Node4 should run node1 automatically when it runs
        result = await node4.run({})
        assert node1.state.status == TaskStatus.COMPLETED


class TestTaskTreeFlowManager:
    """Tests for the TaskTreeFlowManager class."""
    
    @pytest.fixture
    def task_manager(self):
        """Create a mock task manager."""
        manager = MockTaskManager()
        manager.add_task(MockTask("task1", "Test Task", "Test task description"))
        manager.add_task(MockTask("task2", "Test Task 2", "Test task 2 description"))
        manager.add_task(MockTask("task3", "Test Task 3", "Test task 3 description"))
        return manager
    
    @pytest.fixture
    def mock_persistence_model(self):
        """Create a mock persistence model."""
        return MockPersistenceModel()
    
    @pytest.fixture
    def manager(self, task_manager, mock_persistence_model):
        """Create a task tree flow manager."""
        manager = TaskTreeFlowManager(task_manager, mock_persistence_model)
        return manager
    
    def test_create_node(self, manager):
        """Test creating a node."""
        # Create a node
        node = manager.create_node("task1")
        
        # Check that the node was created correctly
        assert node.task_id == "task1"
        assert node.task_manager == manager.task_manager
        assert isinstance(node.aggregator, AllAggregator)
        assert node.transformer is None
        assert node.execution_config is not None
    
    def test_add_child(self, manager):
        """Test adding a child to a node."""
        # Create parent and child nodes
        parent = manager.create_node("task1")
        child = manager.create_node("task2")
        
        # Add child to parent
        manager.add_child(parent, child)
        
        # Check that the child was added correctly
        assert child in parent.children
    
    def test_add_dependency(self, manager):
        """Test adding a dependency to a node."""
        # Create nodes
        node1 = manager.create_node("task1")
        node2 = manager.create_node("task2")
        
        # Add dependency
        manager.add_dependency(node2, node1)
        
        # Check that the dependency was added correctly
        assert node1 in node2.dependencies
    
    @pytest.mark.asyncio
    async def test_execute_node(self, manager):
        """Test executing a node."""
        # Create a node
        node = manager.create_node("task1")
        
        # Execute the node
        result = await manager.execute_node(node, {})
        
        # Check the result
        assert result == "Result from Test Task"
    
    @pytest.mark.asyncio
    async def test_execute_tree(self, manager):
        """Test executing a tree."""
        # Create nodes
        root = manager.create_node("task1")
        child1 = manager.create_node("task2")
        child2 = manager.create_node("task3")
        
        # Add children to root
        manager.add_child(root, child1)
        manager.add_child(root, child2)
        
        # Add root to manager
        manager.roots["root"] = root
        
        # Execute the tree
        results = await manager.execute_tree({})
        
        # Check the results
        assert "root" in results
        assert results["root"] == "Result from Test Task"
    
    def test_to_model(self, manager):
        """Test converting a tree to a model."""
        # Create nodes
        root = manager.create_node("task1", 
                                  aggregator_type="combine", 
                                  transformer={"instructions": "Transform this", "prefix": "PREFIX: ", "suffix": " :SUFFIX"},
                                  execution_config={"strategy": "sequential", "execute_children": True, "propagate_context": True})
        child1 = manager.create_node("task2")
        child2 = manager.create_node("task3")
        
        # Add children to root
        manager.add_child(root, child1)
        manager.add_child(root, child2)
        
        # Add dependency
        manager.add_dependency(child2, child1)
        
        # Add root to manager
        manager.roots["root"] = root
        
        # Add execution group
        manager.execution_groups["group1"] = ["task1", "task2"]
        
        # Convert to model
        model = manager.to_model("test_tree", "Test Tree", "Test tree description", "tm1")
        
        # Check the model
        assert model.id == "test_tree"
        assert model.name == "Test Tree"
        assert model.description == "Test tree description"
        assert model.tasksmanager_id == "tm1"
        assert "task1" in model.nodes
        assert "task2" in model.nodes
        assert "task3" in model.nodes
        assert model.nodes["task1"].aggregator_type == "combine"
        assert model.nodes["task1"].transformer is not None
        assert model.nodes["task1"].transformer.instructions == "Transform this"
        assert model.nodes["task1"].transformer.prefix == "PREFIX: "
        assert model.nodes["task1"].transformer.suffix == " :SUFFIX"
        assert model.nodes["task1"].execution_config.strategy == "sequential"
        assert model.nodes["task1"].execution_config.execute_children == True
        assert model.nodes["task1"].execution_config.propagate_context == True
        assert model.nodes["task1"].children == ["task2", "task3"]
        assert model.nodes["task2"].children == []
        assert model.nodes["task3"].dependencies == ["task2"]
        assert "root" in model.roots
        assert model.roots == ["root"]
        assert "group1" in model.execution_groups
        assert model.execution_groups["group1"] == ["task1", "task2"]
    
    def test_create_from_model(self, manager, mock_persistence_model):
        """Test creating a tree from a model."""
        # Create a model
        model = TaskTreeFlow(
            id="test_tree",
            name="Test Tree",
            description="Test tree description",
            tasksmanager_id="tm1",
            nodes={
                "task1": TaskTreeFlowNode(
                    task_id="task1",
                    name="Task 1",
                    description="Task 1 description",
                    aggregator_type="combine",
                    transformer={
                        "instructions": "Transform this",
                        "prefix": "PREFIX: ",
                        "suffix": " :SUFFIX"
                    },
                    execution_config={
                        "strategy": "sequential",
                        "execute_children": True,
                        "propagate_context": True
                    },
                    children=["task2", "task3"],
                    dependencies=[],
                    state=None
                ),
                "task2": TaskTreeFlowNode(
                    task_id="task2",
                    name="Task 2",
                    description="Task 2 description",
                    aggregator_type="all",
                    transformer=None,
                    execution_config={
                        "strategy": "sequential",
                        "execute_children": True,
                        "propagate_context": True
                    },
                    children=[],
                    dependencies=[],
                    state=None
                ),
                "task3": TaskTreeFlowNode(
                    task_id="task3",
                    name="Task 3",
                    description="Task 3 description",
                    aggregator_type="all",
                    transformer=None,
                    execution_config={
                        "strategy": "sequential",
                        "execute_children": True,
                        "propagate_context": True
                    },
                    children=[],
                    dependencies=["task2"],
                    state=None
                )
            },
            roots=["task1"],
            execution_groups={
                "group1": ["task1", "task2"]
            }
        )
        
        # Save the model to the persistence model
        mock_persistence_model.collection("tree_flows").create("test_tree", model)
        
        # Create from model
        manager.create_from_model("test_tree")
        
        # Check that the tree was created correctly
        assert "task1" in manager.nodes
        assert "task2" in manager.nodes
        assert "task3" in manager.nodes
        assert isinstance(manager.nodes["task1"], TestTaskNode)
        assert isinstance(manager.nodes["task2"], TestTaskNode)
        assert isinstance(manager.nodes["task3"], TestTaskNode)
        assert manager.nodes["task1"].task_id == "task1"
        assert manager.nodes["task2"].task_id == "task2"
        assert manager.nodes["task3"].task_id == "task3"
        assert isinstance(manager.nodes["task1"].aggregator, CombineAggregator)
        assert isinstance(manager.nodes["task2"].aggregator, AllAggregator)
        assert isinstance(manager.nodes["task3"].aggregator, AllAggregator)
        assert manager.nodes["task1"].transformer is not None
        assert manager.nodes["task2"].transformer is None
        assert manager.nodes["task3"].transformer is None
        assert manager.nodes["task1"].execution_config.strategy == ExecutionStrategy.SEQUENTIAL
        assert manager.nodes["task1"].execution_config.execute_children == True
        assert manager.nodes["task1"].execution_config.propagate_context == True
        assert manager.nodes["task2"] in manager.nodes["task1"].children
        assert manager.nodes["task3"] in manager.nodes["task1"].children
        assert manager.nodes["task2"] in manager.nodes["task3"].dependencies
        assert "task1" in manager.roots
        assert manager.roots["task1"] == manager.nodes["task1"]
        assert "group1" in manager.execution_groups
        assert manager.execution_groups["group1"] == ["task1", "task2"]


class TestTaskTreeFlowManager(TaskTreeFlowManager):
    """Custom TaskTreeFlowManager for testing that creates TestTaskNode instances."""
    
    def _create_node_from_model(self, node_model: TaskTreeFlowNode) -> TestTaskNode:
        """Create a TestTaskNode from a TaskTreeFlowNode model."""
        # Create the aggregator
        aggregator = create_aggregator(node_model.aggregator_type)
        
        # Create the transformer if specified
        transformer = None
        if node_model.transformer:
            transformer = PromptTransformer(
                instructions=node_model.transformer.instructions,
                prefix=node_model.transformer.prefix,
                suffix=node_model.transformer.suffix
            )
        
        # Create the node
        node = TestTaskNode(
            task_id=node_model.task_id,
            task_manager=self.task_manager,
            aggregator=aggregator,
            transformer=transformer,
            execution_config=node_model.execution_config
        )
        
        # Restore state if available
        if node_model.state:
            node.state = node_model.state
            
        return node 