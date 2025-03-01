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


class TestTaskNode:
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
        return TaskNode(
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
        parent = TaskNode(
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
        child1 = TaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TaskNode(
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
        parent = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=transformer,
            execution_config=ExecutionConfig()
        )
        
        # Create child nodes
        child1 = TaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TaskNode(
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
        parent_sequential = TaskNode(
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
        child1 = TaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child3 = TaskNode(
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
        parent_parallel = TaskNode(
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
        parent_parallel_limit = TaskNode(
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
        child1 = TaskNode(
            task_id="child1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child2 = TaskNode(
            task_id="child2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        child3 = TaskNode(
            task_id="child3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig()
        )
        
        # Create parent node with AllAggregator
        parent_all = TaskNode(
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
        parent_combine = TaskNode(
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
        parent_summarize = TaskNode(
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
        parent_first = TaskNode(
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
        parent_majority = TaskNode(
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
        parent_consensus = TaskNode(
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
        node1 = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        node2 = TaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config=ExecutionConfig(propagate_context=False)  # Disable context propagation
        )
        
        node3 = TaskNode(
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
        node4 = TaskNode(
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
        task_manager = MockTaskManager()
        task_manager.add_task(MockTask("task1", "Task 1"))
        task_manager.add_task(MockTask("task2", "Task 2"))
        task_manager.add_task(MockTask("task3", "Task 3"))
        return task_manager
    
    @pytest.fixture
    def mock_persistence_model(self):
        """Create a mock persistence model."""
        persistence_model = MockPersistenceModel()
        return persistence_model
    
    @pytest.fixture
    def manager(self, task_manager, mock_persistence_model):
        """Create a task tree flow manager."""
        manager = TaskTreeFlowManager(task_manager, mock_persistence_model)
        return manager
    
    def test_create_node(self, manager):
        """Test creating a task node."""
        node = manager.create_node(
            task_id="task1",
            aggregator_type="all",
            transformer=None,
            execution_config=None
        )
        
        assert node.task_id == "task1"
        assert isinstance(node.aggregator, AllAggregator)
        assert node.transformer is None
        assert node.execution_config is not None
        assert node.execution_config.strategy == ExecutionStrategy.SEQUENTIAL
    
    def test_add_child(self, manager):
        """Test adding a child relationship."""
        # Create nodes
        parent = manager.create_node(task_id="task1")
        child = manager.create_node(task_id="task2")
        
        # Add child relationship
        manager.add_child("task1", "task2")
        
        # Check relationship
        assert child in parent.children
    
    def test_add_dependency(self, manager):
        """Test adding a dependency relationship."""
        # Create nodes
        dependent = manager.create_node(task_id="task1")
        dependency = manager.create_node(task_id="task2")
        
        # Add dependency relationship
        manager.add_dependency("task1", "task2")
        
        # Check relationship
        assert dependency in dependent.dependencies
    
    @pytest.mark.asyncio
    async def test_execute_node(self, manager):
        """Test executing a node."""
        # Create node
        node = manager.create_node(task_id="task1")
        
        # Execute node
        result = await manager.execute_node("task1")
        
        # Check result
        assert result == "Result from Task 1"
        assert node.state.status == TaskStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_tree(self, manager):
        """Test executing a tree."""
        # Create nodes
        root = manager.create_node(task_id="task1")
        child1 = manager.create_node(task_id="task2")
        child2 = manager.create_node(task_id="task3")
        
        # Add relationships
        manager.add_child("task1", "task2")
        manager.add_child("task1", "task3")
        
        # Execute tree
        results = await manager.execute_tree()
        
        # Check results
        assert "task1" in results
        assert isinstance(results["task1"], str)
        assert "Result from Task 1" in results["task1"]
        # The root node result should include the results from child nodes
        assert "Result from Task 2" in results["task1"]
        assert "Result from Task 3" in results["task1"]
    
    def test_to_model(self, manager):
        """Test converting a manager to a model."""
        # Create nodes
        root = manager.create_node(
            task_id="task1",
            aggregator_type="all",
            transformer=None,
            execution_config={"strategy": "sequential"}
        )
        
        child1 = manager.create_node(
            task_id="task2",
            aggregator_type="combine",
            transformer={
                "type": "prompt",
                "instructions": "Transform this",
                "prefix": "PREFIX: ",
                "suffix": " :SUFFIX"
            },
            execution_config={
                "strategy": "parallel",
                "max_concurrency": 5
            }
        )
        
        child2 = manager.create_node(
            task_id="task3",
            aggregator_type="summarize_all",
            transformer=None,
            execution_config={"strategy": "sequential"}
        )
        
        # Add relationships
        manager.add_child("task1", "task2")
        manager.add_child("task1", "task3")
        
        # Convert to model
        tree_flow = manager.to_model()
        
        # Check model
        assert tree_flow.name is not None
        assert tree_flow.description is not None
        
        # Check nodes
        assert len(tree_flow.nodes) == 3
        assert "task1" in tree_flow.nodes
        assert "task2" in tree_flow.nodes
        assert "task3" in tree_flow.nodes
        
        # Check relationships
        assert "task2" in tree_flow.nodes["task1"].children
        assert "task3" in tree_flow.nodes["task1"].children
        
        # Check roots
        assert len(tree_flow.roots) == 1
        assert "task1" in tree_flow.roots
        
        # Check aggregators
        assert tree_flow.nodes["task1"].aggregator_type == "all"
        assert tree_flow.nodes["task2"].aggregator_type == "combine"
        assert tree_flow.nodes["task3"].aggregator_type == "summarize_all"
        
        # Check transformer
        assert tree_flow.nodes["task1"].transformer is None
        assert tree_flow.nodes["task2"].transformer is not None
        assert tree_flow.nodes["task2"].transformer["instructions"] == "Transform this"
        assert tree_flow.nodes["task2"].transformer["prefix"] == "PREFIX: "
        assert tree_flow.nodes["task2"].transformer["suffix"] == " :SUFFIX"
        assert tree_flow.nodes["task3"].transformer is None
        
        # Check execution config
        assert tree_flow.nodes["task1"].execution_config["strategy"] == "sequential"
        assert tree_flow.nodes["task2"].execution_config["strategy"] == "parallel"
        assert tree_flow.nodes["task2"].execution_config["max_concurrency"] == 5
        assert tree_flow.nodes["task3"].execution_config["strategy"] == "sequential"
    
    def test_create_from_model(self, manager, mock_persistence_model):
        """Test creating a manager from a model."""
        from src.server.models.task_tree_flow import TaskTreeFlow, TaskTreeFlowNode
        
        # Create a model
        tree_flow = TaskTreeFlow(
            id="tree1",
            name="Test Tree",
            description="Test tree description",
            tasksmanager_id="tm1",
            nodes={
                "task1": TaskTreeFlowNode(
                    task_id="task1",
                    name="Task 1",
                    description="Task 1 description",
                    aggregator_type="all",
                    transformer=None,
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
                    aggregator_type="combine",
                    transformer={
                        "type": "prompt",
                        "instructions": "Transform this",
                        "prefix": "PREFIX: ",
                        "suffix": " :SUFFIX"
                    },
                    execution_config={
                        "strategy": "parallel",
                        "max_concurrency": 5,
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
                    aggregator_type="summarize_all",
                    transformer=None,
                    execution_config={
                        "strategy": "sequential",
                        "execute_children": True,
                        "propagate_context": True
                    },
                    children=[],
                    dependencies=[],
                    state=None
                )
            },
            roots=["task1"],
            execution_groups={}
        )
        
        # Save the model to the persistence model
        mock_persistence_model.create("tree_flows", "tree1", tree_flow)
        
        # Create a manager from the model
        manager.create_from_model("tree1")
        
        # Check nodes
        assert len(manager.nodes) == 3
        assert "task1" in manager.nodes
        assert "task2" in manager.nodes
        assert "task3" in manager.nodes
        
        # Check relationships
        assert manager.nodes["task2"] in manager.nodes["task1"].children
        assert manager.nodes["task3"] in manager.nodes["task1"].children
        
        # Check roots
        assert len(manager.roots) == 1
        assert "task1" in manager.roots
        
        # Check aggregators
        assert isinstance(manager.nodes["task1"].aggregator, AllAggregator)
        assert isinstance(manager.nodes["task2"].aggregator, CombineAggregator)
        assert isinstance(manager.nodes["task3"].aggregator, SummarizeAllAggregator)
        
        # Check transformer
        assert manager.nodes["task1"].transformer is None
        assert manager.nodes["task2"].transformer is not None
        assert manager.nodes["task2"].transformer.instructions == "Transform this"
        assert manager.nodes["task2"].transformer.prefix == "PREFIX: "
        assert manager.nodes["task2"].transformer.suffix == " :SUFFIX"
        assert manager.nodes["task3"].transformer is None
        
        # Check execution config
        assert manager.nodes["task1"].execution_config.strategy == ExecutionStrategy.SEQUENTIAL
        assert manager.nodes["task2"].execution_config.strategy == ExecutionStrategy.PARALLEL
        assert manager.nodes["task2"].execution_config.max_concurrency == 5
        assert manager.nodes["task3"].execution_config.strategy == ExecutionStrategy.SEQUENTIAL 