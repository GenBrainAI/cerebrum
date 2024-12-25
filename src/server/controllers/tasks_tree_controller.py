from typing import List, Dict, Callable, Optional, Set, Any, Union, Tuple
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from ..models.task import Task
import asyncio
from collections import defaultdict

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class AggregationPolicy(Enum):
    ALL = "all"  # All responses required
    ANY = "any"  # Any response is sufficient
    MAJORITY = "majority"  # Majority of responses needed
    CONSENSUS = "consensus"  # All responses must agree
    CUSTOM = "custom"  # Custom aggregation logic

class TaskAggregator(ABC):
    def __init__(self, policy: AggregationPolicy = AggregationPolicy.ALL):
        self.policy = policy

    @abstractmethod
    def aggregate(self, responses: List[str]) -> str:
        pass

    def validate_responses(self, responses: List[str]) -> bool:
        """Validate responses according to the aggregation policy"""
        if not responses:
            return False
            
        if self.policy == AggregationPolicy.ALL:
            return len(responses) > 0
        elif self.policy == AggregationPolicy.ANY:
            return True
        elif self.policy == AggregationPolicy.MAJORITY:
            return len(responses) > 0  # Simplified for now
        elif self.policy == AggregationPolicy.CONSENSUS:
            return len(set(responses)) == 1
        return True

class AllAggregator(TaskAggregator):
    """Concatenates all responses with newlines"""
    def aggregate(self, responses: List[str]) -> str:
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return "\n".join(responses)

class CombineAggregator(TaskAggregator):
    """Combines responses into a single flow"""
    def aggregate(self, responses: List[str]) -> str:
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return " ".join(responses)

class SummarizeAllAggregator(TaskAggregator):
    """Creates a summary of all responses"""
    def aggregate(self, responses: List[str]) -> str:
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return f"Summary: {', '.join(responses)}"

class FilterAggregator(TaskAggregator):
    """Filters responses based on a condition"""
    def __init__(self, condition: Callable[[str], bool], policy: AggregationPolicy = AggregationPolicy.ALL):
        super().__init__(policy)
        self.condition = condition

    def aggregate(self, responses: List[str]) -> str:
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        filtered = [r for r in responses if self.condition(r)]
        return "\n".join(filtered)

class PrioritizeAggregator(TaskAggregator):
    """Prioritizes responses based on a scoring function"""
    def __init__(self, score_func: Callable[[str], float], policy: AggregationPolicy = AggregationPolicy.ALL):
        super().__init__(policy)
        self.score_func = score_func

    def aggregate(self, responses: List[str]) -> str:
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        scored = [(r, self.score_func(r)) for r in responses]
        sorted_responses = sorted(scored, key=lambda x: x[1], reverse=True)
        return "\n".join(f"[Score: {score:.2f}] {response}" 
                        for response, score in sorted_responses)

class ConsensusAggregator(TaskAggregator):
    """Requires consensus among responses"""
    def __init__(self, threshold: float = 1.0):
        super().__init__(AggregationPolicy.CONSENSUS)
        self.threshold = threshold

    def aggregate(self, responses: List[str]) -> str:
        if not responses:
            raise ValueError("No responses to aggregate")
            
        # Count occurrences of each response
        response_counts = {}
        for response in responses:
            response_counts[response] = response_counts.get(response, 0) + 1

        # Find responses that meet the threshold
        total = len(responses)
        consensus_responses = [
            resp for resp, count in response_counts.items()
            if count / total >= self.threshold
        ]

        if not consensus_responses:
            raise ValueError("No consensus reached")
            
        return "\n".join(consensus_responses)

class TaskExecutionError(Exception):
    """Exception raised for errors during task execution"""
    pass

class ExecutionStrategy(Enum):
    SEQUENTIAL = "sequential"  # Execute tasks one after another
    PARALLEL = "parallel"    # Execute independent tasks in parallel
    PARALLEL_WITH_LIMIT = "parallel_with_limit"  # Parallel with max concurrency

class TaskNodeState(BaseModel):
    """Enhanced state management for task nodes"""
    task_id: str
    name: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_count: int = 0
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    execution_duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    child_states: Dict[str, 'TaskNodeState'] = Field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)

    def update_status(self, new_status: TaskStatus, error: Optional[str] = None):
        """Update task status with history tracking"""
        old_status = self.status
        self.status = new_status
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_status": old_status.value,
            "new_status": new_status.value,
            "error": error
        }
        self.execution_history.append(history_entry)

    def start_execution(self):
        """Mark task as started"""
        self.started_at = datetime.now()
        self.update_status(TaskStatus.RUNNING)

    def complete_execution(self, result: str):
        """Mark task as completed"""
        self.completed_at = datetime.now()
        self.result = result
        self.execution_duration = (self.completed_at - self.started_at).total_seconds()
        self.update_status(TaskStatus.COMPLETED)

    def fail_execution(self, error: str):
        """Mark task as failed"""
        self.completed_at = datetime.now()
        self.error = error
        self.execution_duration = (self.completed_at - self.started_at).total_seconds()
        self.update_status(TaskStatus.FAILED, error)

    def can_retry(self, max_retries: int) -> bool:
        """Check if task can be retried"""
        return (
            self.status == TaskStatus.FAILED and 
            self.retry_count < max_retries
        )

    class Config:
        arbitrary_types_allowed = True

class ExecutionConfig(BaseModel):
    """Configuration for task execution"""
    strategy: ExecutionStrategy = Field(default=ExecutionStrategy.SEQUENTIAL)
    max_concurrency: Optional[int] = Field(default=None)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)  # seconds
    timeout: Optional[float] = Field(default=None)  # seconds
    fail_fast: bool = Field(default=False)  # Stop on first error
    execute_children: bool = Field(default=True)  # Whether to execute child tasks
    propagate_context: bool = Field(default=True)  # Whether to propagate context to children

class TaskNode:
    def __init__(
        self, 
        task: Task, 
        aggregator: TaskAggregator = AllAggregator(),
        execution_config: Optional[ExecutionConfig] = None
    ):
        self.task = task
        self.aggregator = aggregator
        self.children: List[TaskNode] = []
        self.dependencies: Set[TaskNode] = set()
        self.state = TaskNodeState(task_id=task.id, name=task.name)
        self.execution_config = execution_config or ExecutionConfig()

    def add_child(self, child: 'TaskNode'):
        """Add a child task node"""
        self.children.append(child)
        self.state.child_states[child.task.id] = child.state

    def add_dependency(self, dependency: 'TaskNode'):
        """Add a dependency task node"""
        self.dependencies.add(dependency)

    def can_execute(self) -> bool:
        """Check if all dependencies are completed successfully"""
        return all(dep.state.status == TaskStatus.COMPLETED for dep in self.dependencies)

    async def _execute_with_retry(self, context: Dict) -> str:
        """Execute task with retry logic"""
        while True:
            try:
                return await self.task.run(context)
            except Exception as e:
                if not self.state.can_retry(self.execution_config.max_retries):
                    raise
                
                self.state.retry_count += 1
                self.state.last_retry_at = datetime.now()
                await asyncio.sleep(self.execution_config.retry_delay)

    async def run(self, additional_info: Optional[Dict] = None) -> str:
        """Enhanced run method with parallel execution support"""
        try:
            if not self.can_execute():
                raise TaskExecutionError("Dependencies not satisfied")

            self.state.start_execution()
            context = additional_info or {}

            # Only execute children if configured to do so
            responses = []
            if self.execution_config.execute_children and self.children:
                # Execute children based on strategy
                if self.execution_config.strategy == ExecutionStrategy.PARALLEL:
                    responses = await self._run_parallel(
                        context.copy() if self.execution_config.propagate_context else {}
                    )
                elif self.execution_config.strategy == ExecutionStrategy.PARALLEL_WITH_LIMIT:
                    responses = await self._run_parallel_limited(
                        context.copy() if self.execution_config.propagate_context else {}
                    )
                else:
                    responses = await self._run_sequential(
                        context.copy() if self.execution_config.propagate_context else {}
                    )

            # Aggregate child responses
            if responses:
                try:
                    aggregated_response = self.aggregator.aggregate(responses)
                    context["child_responses"] = responses
                    context["aggregated_response"] = aggregated_response
                except Exception as e:
                    raise TaskExecutionError(f"Aggregation failed: {str(e)}")

            # Add dependency results to context
            dependency_results = {
                f"dep_{dep.task.id}": dep.state.result
                for dep in self.dependencies
                if dep.state.status == TaskStatus.COMPLETED
            }
            context.update(dependency_results)

            # Execute this task with retry logic and timeout
            if self.execution_config.timeout:
                try:
                    async with asyncio.timeout(self.execution_config.timeout):
                        result = await self._execute_with_retry(context)
                except asyncio.TimeoutError:
                    raise TaskExecutionError("Task execution timed out")
            else:
                result = await self._execute_with_retry(context)

            self.state.complete_execution(result)
            return result

        except Exception as e:
            self.state.fail_execution(str(e))
            raise TaskExecutionError(f"Task execution failed: {str(e)}")

    async def _run_sequential(self, context: Dict) -> List[str]:
        """Run child tasks sequentially"""
        responses = []
        for child in self.children:
            try:
                response = await child.run(context)
                responses.append(response)
                context[f"child_{child.task.id}"] = response
            except Exception as e:
                if self.execution_config.fail_fast:
                    raise
                child.state.fail_execution(str(e))
        return responses

    async def _run_parallel(self, context: Dict) -> List[str]:
        """Run child tasks in parallel"""
        tasks = [
            self._execute_child(child, context.copy()) 
            for child in self.children
        ]
        results = await asyncio.gather(*tasks, return_exceptions=not self.execution_config.fail_fast)
        
        responses = []
        for result, child in zip(results, self.children):
            if isinstance(result, Exception):
                child.state.fail_execution(str(result))
                if self.execution_config.fail_fast:
                    raise result
            else:
                responses.append(result)
                context[f"child_{child.task.id}"] = result
        return responses

    async def _run_parallel_limited(self, context: Dict) -> List[str]:
        """Run child tasks in parallel with concurrency limit"""
        semaphore = asyncio.Semaphore(self.execution_config.max_concurrency or len(self.children))
        tasks = [
            self._execute_child_limited(child, context.copy(), semaphore) 
            for child in self.children
        ]
        results = await asyncio.gather(*tasks, return_exceptions=not self.execution_config.fail_fast)
        
        responses = []
        for result, child in zip(results, self.children):
            if isinstance(result, Exception):
                child.state.fail_execution(str(result))
                if self.execution_config.fail_fast:
                    raise result
            else:
                responses.append(result)
                context[f"child_{child.task.id}"] = result
        return responses

    async def _execute_child(self, child: 'TaskNode', context: Dict) -> str:
        """Execute a single child task"""
        return await child.run(context)

    async def _execute_child_limited(
        self, 
        child: 'TaskNode', 
        context: Dict, 
        semaphore: asyncio.Semaphore
    ) -> str:
        """Execute a single child task with semaphore"""
        async with semaphore:
            return await child.run(context)

    def get_execution_stats(self) -> Dict:
        """Get execution statistics for this task node"""
        return {
            "task_id": self.task.id,
            "name": self.task.name,
            "status": self.state.status.value,
            "started_at": self.state.started_at.isoformat() if self.state.started_at else None,
            "completed_at": self.state.completed_at.isoformat() if self.state.completed_at else None,
            "execution_count": self.state.execution_count,
            "execution_duration": self.state.execution_duration,
            "error": self.state.error,
            "has_result": self.state.result is not None,
            "child_count": len(self.children),
            "dependency_count": len(self.dependencies),
            "metadata": self.state.metadata
        }

class TaskTreeManager:
    """Enhanced task tree manager with parallel execution support"""
    
    def __init__(self, execution_config: Optional[ExecutionConfig] = None):
        self.nodes: Dict[str, TaskNode] = {}
        self.root_nodes: List[TaskNode] = []
        self.execution_config = execution_config or ExecutionConfig()
        self._execution_groups: Dict[str, Set[str]] = defaultdict(set)

    def create_node(self, task: Task, aggregator: Optional[TaskAggregator] = None) -> TaskNode:
        """Create a new task node and register it"""
        node = TaskNode(task, aggregator or AllAggregator())
        self.nodes[task.id] = node
        return node

    def add_dependency(self, dependent_id: str, dependency_id: str):
        """Add a dependency relationship between tasks"""
        if dependent_id not in self.nodes or dependency_id not in self.nodes:
            raise ValueError("Both tasks must be registered before adding dependencies")
        
        dependent = self.nodes[dependent_id]
        dependency = self.nodes[dependency_id]
        dependent.add_dependency(dependency)

    def add_child(self, parent_id: str, child_id: str):
        """Add a parent-child relationship between tasks"""
        if parent_id not in self.nodes or child_id not in self.nodes:
            raise ValueError("Both tasks must be registered before adding relationships")
        
        parent = self.nodes[parent_id]
        child = self.nodes[child_id]
        parent.add_child(child)

    def set_as_root(self, task_id: str):
        """Mark a task as a root task"""
        if task_id not in self.nodes:
            raise ValueError("Task must be registered before setting as root")
        
        node = self.nodes[task_id]
        if node not in self.root_nodes:
            self.root_nodes.append(node)

    def create_execution_group(self, group_name: str, task_ids: List[str]):
        """Create a group of tasks that can be executed together"""
        for task_id in task_ids:
            if task_id not in self.nodes:
                raise ValueError(f"Task {task_id} not registered")
            self._execution_groups[group_name].add(task_id)

    async def execute_group(
        self, 
        group_name: str, 
        context: Optional[Dict] = None,
        strategy: Optional[ExecutionStrategy] = None
    ) -> Dict[str, Any]:
        """Execute a group of tasks"""
        if group_name not in self._execution_groups:
            raise ValueError(f"Group {group_name} not found")

        task_ids = self._execution_groups[group_name]
        nodes = [self.nodes[tid] for tid in task_ids]
        
        # Override execution strategy if specified
        if strategy:
            for node in nodes:
                node.execution_config.strategy = strategy

        results = {}
        errors = []

        if strategy == ExecutionStrategy.PARALLEL:
            tasks = [node.run(context) for node in nodes]
            execution_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for node, result in zip(nodes, execution_results):
                if isinstance(result, Exception):
                    errors.append({"task_id": node.task.id, "error": str(result)})
                else:
                    results[node.task.id] = result
        else:
            for node in nodes:
                try:
                    result = await node.run(context)
                    results[node.task.id] = result
                except TaskExecutionError as e:
                    errors.append({"task_id": node.task.id, "error": str(e)})

        return {
            "group_name": group_name,
            "results": results,
            "errors": errors,
            "execution_stats": {
                task_id: self.nodes[task_id].get_execution_stats()
                for task_id in task_ids
            }
        }

    def get_group_state(self, group_name: str) -> Dict[str, Any]:
        """Get execution state for a group of tasks"""
        if group_name not in self._execution_groups:
            raise ValueError(f"Group {group_name} not found")

        return {
            "group_name": group_name,
            "task_states": {
                task_id: self.nodes[task_id].state.dict()
                for task_id in self._execution_groups[group_name]
            }
        }

    def get_execution_stats(self) -> Dict[str, Dict]:
        """Get execution statistics for all nodes"""
        return {
            task_id: node.get_execution_stats()
            for task_id, node in self.nodes.items()
        }

    def validate_tree(self) -> List[str]:
        """Validate the task tree for cycles and other issues"""
        issues = []
        visited = set()
        
        def check_cycles(node: TaskNode, path: Set[str]):
            if node.task.id in path:
                cycle = " -> ".join(list(path) + [node.task.id])
                issues.append(f"Dependency cycle detected: {cycle}")
                return
                
            path.add(node.task.id)
            visited.add(node.task.id)
            
            for dep in node.dependencies:
                check_cycles(dep, path.copy())
            for child in node.children:
                check_cycles(child, path.copy())

        # Check for cycles starting from root nodes
        for root in self.root_nodes:
            check_cycles(root, set())

        # Check for orphaned nodes
        orphaned = set(self.nodes.keys()) - visited
        if orphaned:
            issues.append(f"Orphaned tasks detected: {', '.join(orphaned)}")

        return issues

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get a complete snapshot of the current tree state"""
        def serialize_node(node: TaskNode) -> Dict[str, Any]:
            return {
                "task_id": node.task.id,
                "name": node.task.name,
                "status": node.state.status.value,
                "result": node.state.result,
                "error": node.state.error,
                "started_at": node.state.started_at.isoformat() if node.state.started_at else None,
                "completed_at": node.state.completed_at.isoformat() if node.state.completed_at else None,
                "execution_count": node.state.execution_count,
                "metadata": node.state.metadata,
                "children": [serialize_node(child) for child in node.children],
                "dependencies": [dep.task.id for dep in node.dependencies]
            }

        return {
            "root_nodes": [serialize_node(root) for root in self.root_nodes],
            "timestamp": datetime.now().isoformat()
        }

    def restore_state(self, state_snapshot: Dict[str, Any]) -> None:
        """Restore the tree state from a snapshot"""
        def deserialize_node(node_data: Dict[str, Any]) -> None:
            node = self.nodes.get(node_data["task_id"])
            if not node:
                return

            node.state.status = TaskStatus(node_data["status"])
            node.state.result = node_data["result"]
            node.state.error = node_data["error"]
            node.state.started_at = datetime.fromisoformat(node_data["started_at"]) if node_data["started_at"] else None
            node.state.completed_at = datetime.fromisoformat(node_data["completed_at"]) if node_data["completed_at"] else None
            node.state.execution_count = node_data["execution_count"]
            node.state.metadata = node_data["metadata"]

            for child_data in node_data["children"]:
                deserialize_node(child_data)

        for root_data in state_snapshot["root_nodes"]:
            deserialize_node(root_data)


