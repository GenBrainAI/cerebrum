"""
Task Tree Flow Controller

This module provides a unified implementation of task trees with transformation capabilities,
combining the hierarchical execution of task trees with the transformation capabilities of task flows.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Union, Callable, Tuple, TYPE_CHECKING

from src.server.models.task import Task
from src.server.models.task_tree_flow import (
    TaskStatus, ExecutionStrategy, TaskNodeState, ExecutionConfig, 
    TaskTreeFlowNode, TaskTreeFlow
)
from src.server.controllers.task_tree_flow_aggregators import (
    TaskAggregator, AllAggregator, create_aggregator
)
from src.server.controllers.prompt_transformer import PromptTransformer

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.server.persistence.persistence_model_base import PersistenceModelBase
    from src.server.controllers.task_runner import TaskRunner

logger = logging.getLogger(__name__)


class TaskExecutionError(Exception):
    """Exception raised when task execution fails."""
    pass


class TaskNode:
    """
    Enhanced task node with aggregation and transformation capabilities.
    """
    
    def __init__(
        self, 
        task_id: str,
        task_manager: Any = None,
        aggregator: TaskAggregator = None,
        transformer: Optional[PromptTransformer] = None,
        execution_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task node.
        
        Args:
            task_id: The ID of the task to execute
            task_manager: The task manager to use for retrieving tasks
            aggregator: Aggregator for child responses
            transformer: Transformer for aggregated responses
            execution_config: Configuration for task execution
        """
        self.task_id = task_id
        self.task_manager = task_manager
        self.aggregator = aggregator or AllAggregator()
        self.transformer = transformer
        self.children: List[TaskNode] = []
        self.dependencies: Set[TaskNode] = set()
        
        # Get task name from task manager if available
        task_name = task_id
        if task_manager and hasattr(task_manager, "get_task"):
            task = task_manager.get_task(task_id)
            if task and hasattr(task, "name"):
                task_name = task.name
        
        self.state = TaskNodeState(task_id=task_id, name=task_name)
        
        if execution_config is None:
            self.execution_config = ExecutionConfig()
        elif isinstance(execution_config, dict):
            self.execution_config = ExecutionConfig(**execution_config)
        else:
            self.execution_config = execution_config
    
    def add_child(self, child: 'TaskNode') -> None:
        """Add a child node."""
        self.children.append(child)
    
    def add_dependency(self, dependency: 'TaskNode') -> None:
        """Add a dependency node."""
        self.dependencies.add(dependency)
    
    def can_execute(self) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep.state.status == TaskStatus.COMPLETED for dep in self.dependencies)
    
    async def _execute_task_with_timeout(self, context: Dict[str, Any]) -> str:
        """Execute the task with timeout handling."""
        timeout = self.execution_config.timeout
        
        # Get the task from the task manager
        if not self.task_manager or not hasattr(self.task_manager, "get_task"):
            raise TaskExecutionError(f"No task manager available for task {self.task_id}")
        
        task = self.task_manager.get_task(self.task_id)
        if not task:
            raise TaskExecutionError(f"Task {self.task_id} not found")
        
        if not hasattr(task, "run") or not callable(task.run):
            raise TaskExecutionError(f"Task {self.task_id} does not have a run method")
        
        if timeout:
            try:
                return await asyncio.wait_for(task.run(context), timeout)
            except asyncio.TimeoutError:
                raise TaskExecutionError(f"Task execution timed out after {timeout} seconds")
        else:
            return await task.run(context)
    
    async def _execute_task_with_retry(self, context: Dict[str, Any]) -> str:
        """Execute the task with retry logic."""
        max_retries = self.execution_config.max_retries
        retry_delay = self.execution_config.retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                return await self._execute_task_with_timeout(context)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Task {self.task_id} failed, retrying ({attempt+1}/{max_retries}): {str(e)}")
                    self.state.retry_count += 1
                    self.state.last_retry_at = datetime.now()
                    await asyncio.sleep(retry_delay)
                else:
                    raise TaskExecutionError(f"Task failed after {max_retries} retries: {str(e)}")
    
    async def _execute_children(self, context: Dict[str, Any]) -> List[Any]:
        """
        Execute child tasks based on the execution strategy.
        
        Args:
            context: The context to pass to child tasks.
            
        Returns:
            List of child task results.
        """
        strategy = self.execution_config.strategy
        
        if strategy == ExecutionStrategy.SEQUENTIAL:
            return await self._execute_children_sequential(context)
        elif strategy == ExecutionStrategy.PARALLEL:
            return await self._execute_children_parallel(context)
        elif strategy == ExecutionStrategy.PARALLEL_WITH_LIMIT:
            return await self._execute_children_parallel_with_limit(context)
        else:
            raise ValueError(f"Unknown execution strategy: {strategy}")
            
    async def _execute_children_sequential(self, context: Dict[str, Any]) -> List[Any]:
        """
        Execute child tasks sequentially.
        
        Args:
            context: The context to pass to child tasks.
            
        Returns:
            List of child task results.
        """
        results = []
        
        for child in self.children:
            try:
                # Propagate context if configured to do so
                child_context = context.copy() if self.execution_config.propagate_context else {}
                
                # Execute child task
                result = await child.run(child_context)
                results.append(result)
            except Exception as e:
                if self.execution_config.fail_fast:
                    raise
                # Log error but continue with other children
                results.append(f"Error executing child {child.task_id}: {str(e)}")
                
        return results
        
    async def _execute_children_parallel(self, context: Dict[str, Any]) -> List[Any]:
        """
        Execute child tasks in parallel.
        
        Args:
            context: The context to pass to child tasks.
            
        Returns:
            List of child task results.
        """
        tasks = []
        
        for child in self.children:
            # Propagate context if configured to do so
            child_context = context.copy() if self.execution_config.propagate_context else {}
            
            # Create task
            task = asyncio.create_task(child.run(child_context))
            tasks.append(task)
            
        # Wait for all tasks to complete
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                if self.execution_config.fail_fast:
                    # Cancel all remaining tasks
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    raise
                # Log error but continue with other tasks
                results.append(f"Error executing child task: {str(e)}")
                
        return results
        
    async def _execute_children_parallel_with_limit(self, context: Dict[str, Any]) -> List[Any]:
        """
        Execute child tasks in parallel with a concurrency limit.
        
        Args:
            context: The context to pass to child tasks.
            
        Returns:
            List of child task results.
        """
        semaphore = asyncio.Semaphore(self.execution_config.max_concurrency)
        
        async def run_with_semaphore(child):
            async with semaphore:
                # Propagate context if configured to do so
                child_context = context.copy() if self.execution_config.propagate_context else {}
                
                # Execute child task
                return await child.run(child_context)
        
        # Create tasks
        tasks = [asyncio.create_task(run_with_semaphore(child)) for child in self.children]
        
        # Wait for all tasks to complete
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                if self.execution_config.fail_fast:
                    # Cancel all remaining tasks
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    raise
                # Log error but continue with other tasks
                results.append(f"Error executing child task: {str(e)}")
                
        return results
    
    async def run(self, context: Dict[str, Any]) -> Any:
        """
        Run the task node and its children based on the execution configuration.
        
        Args:
            context: The context to pass to the task.
            
        Returns:
            The result of the task execution, potentially aggregated with child results.
        """
        # Update the existing state instead of creating a new one
        self.state.status = TaskStatus.RUNNING
        self.state.started_at = datetime.now()
        self.state.context = context
        
        try:
            # Check if dependencies are satisfied
            await self._check_dependencies()
            
            # Execute the task with retry logic
            task_result = await self._execute_task_with_retry(context)
            
            # Execute children if configured to do so
            child_results = []
            if self.execution_config.execute_children and self.children:
                child_results = await self._execute_children(context)
            
            # Apply transformer if available
            if self.transformer:
                transformed_result = await self.transformer.transform(task_result, context)
                self.state.transformation_applied = True
                self.state.transformation_details = {"original_result": task_result}
                task_result = transformed_result
            
            # Aggregate results if there are child results
            final_result = task_result
            if child_results:
                all_results = [task_result] + child_results
                final_result = self.aggregator.aggregate(all_results)
            
            self.state.status = TaskStatus.COMPLETED
            self.state.completed_at = datetime.now()
            self.state.result = final_result
            return final_result
            
        except Exception as e:
            self.state.status = TaskStatus.FAILED
            self.state.error = str(e)
            self.state.completed_at = datetime.now()
            logger.error(f"Task {self.task_id} execution failed: {str(e)}")
            raise

    async def _check_dependencies(self) -> None:
        """Check if all dependencies are satisfied."""
        if not self.dependencies:
            return
            
        # Execute all dependencies that haven't been executed yet
        for dependency in self.dependencies:
            if dependency.state.status != TaskStatus.COMPLETED:
                # Propagate context to dependencies if configured to do so
                dependency_context = self.state.context if self.execution_config.propagate_context else {}
                await dependency.run(dependency_context or {})
                
        # Check if all dependencies are now satisfied
        unsatisfied = [dep.task_id for dep in self.dependencies if dep.state.status != TaskStatus.COMPLETED]
        if unsatisfied:
            raise ValueError(f"Dependencies not satisfied: {', '.join(unsatisfied)}")


class TaskTreeFlowManager:
    """
    Manager for task tree flows with transformation capabilities.
    """
    
    def __init__(self, task_manager: Any, persistence_model: 'PersistenceModelBase' = None):
        """
        Initialize the task tree flow manager.
        
        Args:
            task_manager: The task manager for retrieving tasks
            persistence_model: The persistence model for storing and retrieving tasks
        """
        self.task_manager = task_manager
        self.persistence_model = persistence_model
        self.nodes: Dict[str, TaskNode] = {}
        self.roots: Dict[str, TaskNode] = {}
        self.execution_groups: Dict[str, List[str]] = {}
        self.task_runner = None
        
    async def initialize(self):
        """Initialize the task tree flow manager."""
        from src.server.controllers.task_runner import TaskRunner
        
        if self.task_runner is None and self.persistence_model:
            self.task_runner = TaskRunner(self.persistence_model)
            await self.task_runner.initialize()
    
    def create_node(
        self, 
        task_id: str, 
        aggregator_type: str = "all",
        transformer: Optional[Dict[str, Any]] = None,
        execution_config: Optional[Dict[str, Any]] = None
    ) -> TaskNode:
        """
        Create a new task node with optional transformer.
        
        Args:
            task_id: The ID of the task to execute
            aggregator_type: Type of aggregator to use
            transformer: Transformer configuration
            execution_config: Configuration for task execution
            
        Returns:
            The created task node
        """
        # Create aggregator
        aggregator_kwargs = {}
        if isinstance(aggregator_type, dict):
            aggregator_kwargs = {k: v for k, v in aggregator_type.items() if k != "type"}
            aggregator_type = aggregator_type.get("type", "all")
        
        aggregator = create_aggregator(aggregator_type, **aggregator_kwargs)
        
        # Create transformer
        transformer_obj = None
        if transformer:
            transformer_type = transformer.get("type", "prompt")
            if transformer_type == "prompt":
                transformer_obj = PromptTransformer(
                    instructions=transformer.get("instructions"),
                    prefix=transformer.get("prefix"),
                    suffix=transformer.get("suffix")
                )
        
        # Create node
        node = TaskNode(
            task_id=task_id,
            task_manager=self.task_manager,
            aggregator=aggregator,
            transformer=transformer_obj,
            execution_config=execution_config
        )
        
        self.nodes[task_id] = node
        self.roots[task_id] = node  # Initially, all nodes are roots
        return node
    
    def add_child(self, parent_id: str, child_id: str) -> None:
        """
        Add a child relationship between nodes.
        
        Args:
            parent_id: ID of the parent task
            child_id: ID of the child task
        """
        if parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} not found")
        if child_id not in self.nodes:
            raise ValueError(f"Child node {child_id} not found")
        
        parent = self.nodes[parent_id]
        child = self.nodes[child_id]
        
        parent.add_child(child)
        
        # If this was a root node, it's no longer a root
        if child_id in self.roots:
            del self.roots[child_id]
    
    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        """
        Add a dependency relationship between nodes.
        
        Args:
            task_id: ID of the dependent task
            dependency_id: ID of the dependency task
        """
        if task_id not in self.nodes:
            raise ValueError(f"Task node {task_id} not found")
        if dependency_id not in self.nodes:
            raise ValueError(f"Dependency node {dependency_id} not found")
        
        task = self.nodes[task_id]
        dependency = self.nodes[dependency_id]
        
        task.add_dependency(dependency)
    
    def set_execution_config(self, task_id: str, config: ExecutionConfig) -> None:
        """
        Set execution configuration for a node.
        
        Args:
            task_id: ID of the task
            config: Execution configuration
        """
        if task_id not in self.nodes:
            raise ValueError(f"Task node {task_id} not found")
        
        self.nodes[task_id].execution_config = config
    
    def set_transformer(self, task_id: str, transformer: PromptTransformer) -> None:
        """
        Set transformer for a node.
        
        Args:
            task_id: ID of the task
            transformer: Prompt transformer
        """
        if task_id not in self.nodes:
            raise ValueError(f"Task node {task_id} not found")
        
        self.nodes[task_id].transformer = transformer
    
    def set_aggregator(self, task_id: str, aggregator: TaskAggregator) -> None:
        """
        Set aggregator for a node.
        
        Args:
            task_id: ID of the task
            aggregator: Task aggregator
        """
        if task_id not in self.nodes:
            raise ValueError(f"Task node {task_id} not found")
        
        self.nodes[task_id].aggregator = aggregator
    
    def get_roots(self) -> List[TaskNode]:
        """Get all root nodes."""
        return list(self.roots.values())
    
    def get_execution_order(self) -> List[TaskNode]:
        """Get nodes in execution order (topological sort)."""
        visited: Set[str] = set()
        execution_order: List[TaskNode] = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            
            visited.add(node_id)
            node = self.nodes[node_id]
            
            # Visit dependencies first
            for dep in node.dependencies:
                visit(dep.task_id)
            
            # Visit children
            for child in node.children:
                visit(child.task_id)
            
            execution_order.append(node)
        
        # Visit all roots
        for root_id in self.roots:
            visit(root_id)
        
        return execution_order
    
    async def execute_node(self, task_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a specific node in the tree.
        
        Args:
            task_id: ID of the task to execute
            context: Additional context information
            
        Returns:
            The execution result
        """
        if task_id not in self.nodes:
            raise ValueError(f"Task node {task_id} not found")
        
        node = self.nodes[task_id]
        result = await node.run(context or {})
        
        # Update the tree flow in the persistence model if available
        if self.persistence_model:
            # Find the original tree flow ID
            tree_flow_id = None
            original_tree_flow = None
            for tree_id in self.persistence_model.collection("tree_flows").list():
                tree_flow = self.persistence_model.collection("tree_flows").read(tree_id)
                if tree_flow and set(tree_flow.nodes.keys()) == set(self.nodes.keys()):
                    tree_flow_id = tree_id
                    original_tree_flow = tree_flow
                    break
            
            # Update only the executed node's state in the tree flow
            if tree_flow_id and original_tree_flow:
                # Create a new tree model with the same structure
                updated_tree = TaskTreeFlow(
                    id=tree_flow_id,
                    name=original_tree_flow.name,
                    description=original_tree_flow.description,
                    tasksmanager_id=original_tree_flow.tasksmanager_id,
                    nodes={},
                    roots=original_tree_flow.roots,
                    execution_groups=original_tree_flow.execution_groups
                )
                
                # Copy all nodes from the original tree
                for node_id, node_model in original_tree_flow.nodes.items():
                    if node_id == task_id:
                        # For the executed node, use the updated state
                        executed_node = self.nodes[task_id]
                        # Convert TaskNodeState to a dictionary
                        state_dict = None
                        if executed_node.state:
                            state_dict = {
                                "task_id": executed_node.state.task_id,
                                "name": executed_node.state.name,
                                "status": executed_node.state.status,
                                "result": executed_node.state.result,
                                "error": executed_node.state.error,
                                "started_at": executed_node.state.started_at,
                                "completed_at": executed_node.state.completed_at,
                                "retry_count": executed_node.state.retry_count,
                                "last_retry_at": executed_node.state.last_retry_at,
                                "transformation_applied": executed_node.state.transformation_applied,
                                "transformation_details": executed_node.state.transformation_details,
                                "context": executed_node.state.context
                            }
                        updated_tree.nodes[node_id] = TaskTreeFlowNode(
                            task_id=node_model.task_id,
                            name=node_model.name,
                            description=node_model.description,
                            aggregator_type=node_model.aggregator_type,
                            transformer=node_model.transformer,
                            execution_config=node_model.execution_config,
                            children=node_model.children,
                            dependencies=node_model.dependencies,
                            state=state_dict
                        )
                    else:
                        # For other nodes, keep the original state
                        updated_tree.nodes[node_id] = node_model
                
                # Update the tree flow in the persistence model
                self.persistence_model.collection("tree_flows").update(tree_flow_id, updated_tree)
        
        return result
    
    async def execute_tree(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Execute the entire tree starting from root nodes.
        
        Args:
            context: Additional context information
            
        Returns:
            Dictionary mapping task IDs to execution results
        """
        results = {}
        
        for root_id, root_node in self.roots.items():
            try:
                result = await root_node.run(context or {})
                results[root_id] = result
            except Exception as e:
                logger.error(f"Root node {root_id} execution failed: {str(e)}")
                results[root_id] = f"ERROR: {str(e)}"
        
        # Update the tree flow in the persistence model if available
        if self.persistence_model:
            # Convert the current state to a model
            tree_model = self.to_model()
            
            # Find the original tree flow ID
            tree_flow_id = None
            for tree_id in self.persistence_model.collection("tree_flows").list():
                tree_flow = self.persistence_model.collection("tree_flows").read(tree_id)
                if tree_flow and set(tree_flow.nodes.keys()) == set(self.nodes.keys()):
                    tree_flow_id = tree_id
                    tree_model.id = tree_id  # Preserve the original ID
                    break
            
            # Update the tree flow in the persistence model
            if tree_flow_id:
                self.persistence_model.collection("tree_flows").update(tree_flow_id, tree_model)
        
        return results
    
    def create_from_model(self, tree_flow_id_or_model: Union[str, TaskTreeFlow]) -> None:
        """
        Create a task tree flow from a model.
        
        Args:
            tree_flow_id_or_model: The task tree flow model or ID
        """
        # Reset nodes and roots
        self.nodes = {}
        self.roots = {}
        
        # Get tree flow model
        tree_flow = None
        if isinstance(tree_flow_id_or_model, str):
            if not self.persistence_model:
                raise ValueError("Persistence model is required to load tree flow by ID")
            tree_flow = self.persistence_model.collection("tree_flows").read(tree_flow_id_or_model)
            if not tree_flow:
                raise ValueError(f"Tree flow {tree_flow_id_or_model} not found")
        else:
            tree_flow = tree_flow_id_or_model
        
        self.execution_groups = tree_flow.execution_groups
        
        # First pass: create all nodes
        for node_id, node_data in tree_flow.nodes.items():
            # Create node
            self.create_node(
                task_id=node_id,
                aggregator_type=node_data.aggregator_type,
                transformer=node_data.transformer,
                execution_config=node_data.execution_config
            )
        
        # Second pass: add relationships
        for node_id, node_data in tree_flow.nodes.items():
            # Add child relationships
            for child_id in node_data.children:
                self.add_child(node_id, child_id)
            
            # Add dependency relationships
            for dep_id in node_data.dependencies:
                self.add_dependency(node_id, dep_id)
        
        # Set roots from model
        self.roots = {root_id: self.nodes[root_id] for root_id in tree_flow.roots if root_id in self.nodes}
    
    def to_model(self) -> TaskTreeFlow:
        """
        Convert the task tree flow to a model.
        
        Returns:
            The task tree flow model
        """
        nodes = {}
        
        for node_id, node in self.nodes.items():
            # Convert aggregator
            aggregator_type = "all"
            if isinstance(node.aggregator, AllAggregator):
                aggregator_type = "all"
            elif hasattr(node.aggregator, "__class__"):
                class_name = node.aggregator.__class__.__name__.lower()
                # Preserve underscores in aggregator type names
                if class_name == "summarizeallaggregator":
                    aggregator_type = "summarize_all"
                elif class_name == "firstsuccessaggregator":
                    aggregator_type = "first_success"
                else:
                    aggregator_type = class_name.replace("aggregator", "")
            
            # Convert transformer
            transformer = None
            if node.transformer:
                transformer = {
                    "type": "prompt",
                    "instructions": node.transformer.instructions,
                    "prefix": node.transformer.prefix,
                    "suffix": node.transformer.suffix
                }
            
            # Convert execution config
            execution_config = {
                "strategy": node.execution_config.strategy.value,
                "max_concurrency": node.execution_config.max_concurrency,
                "max_retries": node.execution_config.max_retries,
                "retry_delay": node.execution_config.retry_delay,
                "timeout": node.execution_config.timeout,
                "fail_fast": node.execution_config.fail_fast,
                "execute_children": node.execution_config.execute_children,
                "propagate_context": node.execution_config.propagate_context
            }
            
            # Convert state
            state = node.state.model_dump() if node.state else None
            
            # Create node data
            nodes[node_id] = TaskTreeFlowNode(
                task_id=node_id,
                name=node.state.name,
                description="",  # We don't have description in the node
                aggregator_type=aggregator_type,
                transformer=transformer,
                execution_config=execution_config,
                children=[child.task_id for child in node.children],
                dependencies=[dep.task_id for dep in node.dependencies],
                state=state
            )
        
        # Get tasksmanager_id from first node if available
        tasksmanager_id = ""
        if self.task_manager and hasattr(self.task_manager, "get_task"):
            for node_id in self.nodes:
                task = self.task_manager.get_task(node_id)
                if task and hasattr(task, "tasksmanager_id"):
                    tasksmanager_id = task.tasksmanager_id
                    break
        
        # Create tree flow model
        return TaskTreeFlow(
            id=f"tree_flow_{int(time.time())}",
            name="Task Tree Flow",
            description="Generated from TaskTreeFlowManager",
            tasksmanager_id=tasksmanager_id,
            nodes=nodes,
            roots=list(self.roots.keys()),
            execution_groups=self.execution_groups
        )

# Compatibility layer for old interfaces

class TaskTreeManagerCompat:
    """
    Compatibility layer for the old TaskTreeManager interface.
    This class provides backward compatibility with the old TaskTreeManager interface
    from tasks_tree_controller.py.
    """
    
    def __init__(self, manager: TaskTreeFlowManager):
        """Initialize with a TaskTreeFlowManager instance."""
        self._manager = manager
        
    def add_task(self, task_id: str, name: str, description: str = "", **kwargs) -> str:
        """Add a task to the tree."""
        return self._manager.create_node(
            task_id=task_id,
            name=name,
            description=description,
            **kwargs
        ).task_id
        
    def add_child(self, parent_id: str, child_id: str) -> bool:
        """Add a child task to a parent task."""
        return self._manager.add_child(parent_id, child_id)
        
    def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Add a dependency between tasks."""
        return self._manager.add_dependency(task_id, depends_on_id)
        
    def execute_node(self, node_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a single node."""
        return asyncio.run(self._manager.execute_node(node_id, context or {}))
        
    def execute_tree(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the entire tree."""
        return asyncio.run(self._manager.execute_tree(context or {}))
        
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current state."""
        return self._manager.to_model().dict()
        
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = {}
        for node_id, node in self._manager.nodes.items():
            if node.state and node.state.status != TaskStatus.PENDING:
                stats[node_id] = {
                    "status": node.state.status.value,
                    "execution_time": node.state.execution_duration or 0,
                    "started_at": node.state.started_at.isoformat() if node.state.started_at else None,
                    "completed_at": node.state.completed_at.isoformat() if node.state.completed_at else None
                }
        return stats 