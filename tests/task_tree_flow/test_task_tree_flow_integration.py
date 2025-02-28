"""
Integration tests for the Task Tree Flow implementation.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional

from src.server.controllers.task_tree_flow import TaskNode, TaskTreeFlowManager
from src.server.models.task_tree_flow import TaskTreeFlow, TaskTreeFlowNode, TaskStatus
from src.server.controllers.task_tree_flow_aggregators import (
    AllAggregator,
    CombineAggregator,
    SummarizeAllAggregator
)


class MockTask:
    """Mock task for testing."""
    
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description
        self.tasksmanager_id = "tm1"
    
    async def run(self, context: Dict[str, Any]) -> str:
        """Run the mock task."""
        if self.id == "task1":
            return f"Task 1 result with input: {context.get('input', '')}"
        elif self.id == "task2":
            return f"Task 2 result with input: {context.get('input', '')}"
        elif self.id == "task3":
            return f"Task 3 result with input: {context.get('input', '')}"
        elif self.id == "task4":
            return f"Task 4 result with input: {context.get('input', '')}"
        elif self.id == "error_task":
            raise Exception("Task execution failed")
        return f"Unknown task result with input: {context.get('input', '')}"


class MockTaskManager:
    """Mock task manager for testing."""
    
    def __init__(self):
        self.tasks = {
            "task1": MockTask("task1", "Task 1", "Task 1 description"),
            "task2": MockTask("task2", "Task 2", "Task 2 description"),
            "task3": MockTask("task3", "Task 3", "Task 3 description"),
            "task4": MockTask("task4", "Task 4", "Task 4 description"),
            "error_task": MockTask("error_task", "Error Task", "Task that raises an error")
        }
    
    def get_task(self, task_id: str) -> Optional[MockTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)


class MockPersistenceModel:
    """Mock persistence model for testing."""
    
    def __init__(self):
        self.data = {}
    
    def create(self, collection: str, id: str, data: Any) -> None:
        """Create an item in the collection."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
    
    def read(self, collection: str, id: str) -> Any:
        """Read an item from the collection."""
        if collection not in self.data:
            return None
        return self.data[collection].get(id)
    
    def update(self, collection: str, id: str, data: Any) -> None:
        """Update an item in the collection."""
        if collection not in self.data:
            self.data[collection] = {}
        self.data[collection][id] = data
    
    def delete(self, collection: str, id: str) -> None:
        """Delete an item from the collection."""
        if collection in self.data and id in self.data[collection]:
            del self.data[collection][id]
    
    def list(self, collection: str) -> List[str]:
        """List all items in the collection."""
        if collection not in self.data:
            return []
        return list(self.data[collection].keys())
    
    def collection(self, collection_name: str) -> 'MockCollection':
        """Get a collection by name."""
        return MockCollection(self, collection_name)


class MockCollection:
    """Mock collection for testing."""
    
    def __init__(self, persistence_model: MockPersistenceModel, collection_name: str):
        self.persistence_model = persistence_model
        self.collection_name = collection_name
    
    def create(self, id: str, data: Any) -> None:
        """Create an item in the collection."""
        self.persistence_model.create(self.collection_name, id, data)
    
    def read(self, id: str) -> Any:
        """Read an item from the collection."""
        return self.persistence_model.read(self.collection_name, id)
    
    def update(self, id: str, data: Any) -> None:
        """Update an item in the collection."""
        self.persistence_model.update(self.collection_name, id, data)
    
    def delete(self, id: str) -> None:
        """Delete an item from the collection."""
        self.persistence_model.delete(self.collection_name, id)
    
    def list(self) -> List[str]:
        """List all items in the collection."""
        return self.persistence_model.list(self.collection_name)


class MockTransformer:
    """Mock transformer for testing."""
    
    def __init__(self, instructions: str, prefix: str = "", suffix: str = ""):
        self.type = "prompt"
        self.instructions = instructions
        self.prefix = prefix
        self.suffix = suffix
    
    async def transform(self, content: str, context: Dict[str, Any]) -> str:
        """Transform the content."""
        return f"{self.prefix}{content} - Transformed with: {self.instructions}{self.suffix}"


@pytest.fixture
def task_manager():
    """Create a mock task manager."""
    return MockTaskManager()


@pytest.fixture
def persistence_model():
    """Create a mock persistence model."""
    return MockPersistenceModel()


@pytest.mark.asyncio
class TestTaskTreeFlowIntegration:
    """Integration tests for the Task Tree Flow implementation."""
    
    async def test_simple_task_execution(self, task_manager):
        """Test executing a simple task."""
        # Create a task node
        node = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Execute the task
        result = await node.run({"input": "test"})
        
        # Check the result
        assert result == "Task 1 result with input: test"
    
    async def test_task_with_transformer(self, task_manager):
        """Test executing a task with a transformer."""
        # Create a task node with a transformer
        node = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=MockTransformer(
                instructions="Add some context",
                prefix="PREFIX: ",
                suffix=" :SUFFIX"
            ),
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Execute the task
        result = await node.run({"input": "test"})
        
        # Check the result
        assert result == "PREFIX: Task 1 result with input: test - Transformed with: Add some context :SUFFIX"
    
    async def test_task_with_children_sequential(self, task_manager):
        """Test executing a task with children in sequential mode."""
        # Create child nodes
        child1 = TaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        child2 = TaskNode(
            task_id="task3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Create parent node
        parent = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=CombineAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Add children to parent
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Execute the parent task
        result = await parent.run({"input": "test"})
        
        # Check the result
        assert "Task 1 result with input: test" in result
        assert "Task 2 result with input: test" in result
        assert "Task 3 result with input: test" in result
    
    async def test_task_with_children_parallel(self, task_manager):
        """Test executing a task with children in parallel mode."""
        # Create child nodes
        child1 = TaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        child2 = TaskNode(
            task_id="task3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Create parent node with parallel execution
        parent = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=CombineAggregator(),
            transformer=None,
            execution_config={
                "strategy": "parallel",
                "max_concurrency": 5,
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Add children to parent
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Execute the parent task
        result = await parent.run({"input": "test"})
        
        # Check the result
        assert "Task 1 result with input: test" in result
        assert "Task 2 result with input: test" in result
        assert "Task 3 result with input: test" in result
    
    async def test_task_with_dependencies(self, task_manager):
        """Test executing a task with dependencies."""
        # Create dependency node
        dependency = TaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Create dependent node
        dependent = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Add dependency
        dependent.add_dependency(dependency)
        
        # Execute the dependent task
        result = await dependent.run({"input": "test"})
        
        # Check the result
        assert result == "Task 1 result with input: test"
        assert dependency.state is not None
        assert dependency.state["result"] == "Task 2 result with input: test"
    
    async def test_task_with_error_handling(self, task_manager):
        """Test error handling during task execution."""
        # Create a task node that will raise an error
        node = TaskNode(
            task_id="error_task",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "max_retries": 2,
                "retry_delay": 0.1,
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Execute the task and expect an error
        with pytest.raises(Exception) as excinfo:
            await node.run({"input": "test"})
        
        # Check the error message
        assert "Task execution failed" in str(excinfo.value)
        
        # Check that retries were attempted
        assert node.state is not None
        assert node.state.retry_count == 2
    
    async def test_task_with_summarize_aggregator(self, task_manager):
        """Test executing a task with a summarize aggregator."""
        # Create child nodes
        child1 = TaskNode(
            task_id="task2",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        child2 = TaskNode(
            task_id="task3",
            task_manager=task_manager,
            aggregator=AllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Create parent node with summarize aggregator
        parent = TaskNode(
            task_id="task1",
            task_manager=task_manager,
            aggregator=SummarizeAllAggregator(),
            transformer=None,
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Add children to parent
        parent.add_child(child1)
        parent.add_child(child2)
        
        # Execute the parent task
        result = await parent.run({"input": "test"})
        
        # Check the result
        assert "Task 1 result with input: test" in result
        assert "Task 2 result with input: test" in result
        assert "Task 3 result with input: test" in result
    
    async def test_task_tree_flow_manager(self, task_manager, persistence_model):
        """Test the TaskTreeFlowManager."""
        # Create a task tree flow
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
                    aggregator_type="combine",
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
                    dependencies=[],
                    state=None
                )
            },
            roots=["task1"],
            execution_groups={}
        )
        
        # Save the tree flow to the persistence model
        persistence_model.collection("tree_flows").create("tree1", tree_flow)
        
        # Create a manager
        manager = TaskTreeFlowManager(task_manager, persistence_model)
        await manager.initialize()
        
        # Create from model
        manager.create_from_model("tree1")
        
        # Execute the tree
        result = await manager.execute_tree({"input": "test"})
        
        # Check the result
        assert "task1" in result
        assert "Task 1 result with input: test" in result["task1"]
        assert "Task 2 result with input: test" in result["task1"]
        assert "Task 3 result with input: test" in result["task1"]
        
        # Check that the tree flow was updated in the persistence model
        updated_tree = persistence_model.collection("tree_flows").read("tree1")
        assert updated_tree is not None
        assert updated_tree.nodes["task1"].state is not None
        assert updated_tree.nodes["task2"].state is not None
        assert updated_tree.nodes["task3"].state is not None
    
    async def test_execute_specific_node(self, task_manager, persistence_model):
        """Test executing a specific node in the tree."""
        # Create a task tree flow
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
                    aggregator_type="combine",
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
                    dependencies=[],
                    state=None
                )
            },
            roots=["task1"],
            execution_groups={}
        )
        
        # Save the tree flow to the persistence model
        persistence_model.collection("tree_flows").create("tree1", tree_flow)
        
        # Create a manager
        manager = TaskTreeFlowManager(task_manager, persistence_model)
        await manager.initialize()
        
        # Create from model
        manager.create_from_model("tree1")
        
        # Execute a specific node
        result = await manager.execute_node("task2", {"input": "test"})
        
        # Check the result
        assert result == "Task 2 result with input: test"
        
        # Check that only the executed node was updated in the persistence model
        updated_tree = persistence_model.collection("tree_flows").read("tree1")
        assert updated_tree is not None
        assert updated_tree.nodes["task1"].state is None
        assert updated_tree.nodes["task2"].state is not None
        assert updated_tree.nodes["task3"].state is None

    async def test_task_with_transformer(self, persistence_model):
        """Test a task with a transformer."""
        # Create a task with a transformer
        task = TaskNode(
            task_id="task1",
            task_manager=MockTaskManager(),
            aggregator=AllAggregator(),
            transformer=MockTransformer(instructions="Add some context", prefix="PREFIX: "),
            execution_config={
                "strategy": "sequential",
                "execute_children": True,
                "propagate_context": True
            }
        )
        
        # Execute the task
        result = await task.run({"input": "test"})
        
        # Check the result
        assert result == "PREFIX: Task 1 result with input: test - Transformed with: Add some context"
        
        # Check the task state
        assert task.state is not None
        assert task.state.status == TaskStatus.COMPLETED
        assert task.state.result == "PREFIX: Task 1 result with input: test - Transformed with: Add some context" 