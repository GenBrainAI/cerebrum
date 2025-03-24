from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import logging

from .task_selector import Task, TaskStatus

logger = logging.getLogger(__name__)

class DependencyResolver:
    """Resolves task dependencies and manages the dependency graph."""
    
    def __init__(self, task_selector):
        self.task_selector = task_selector
        logger.info("Dependency resolver initialized")
    
    def analyze_dependency_graph(self) -> Dict[str, Any]:
        """Analyze the dependency graph and provide metrics."""
        if not self.task_selector.dependency_graph:
            logger.info("Dependency graph is empty")
            return {"empty": True}
        
        # Calculate metrics
        metrics = {
            "total_tasks": len(self.task_selector.tasks),
            "independent_tasks": self._count_independent_tasks(),
            "terminal_tasks": self._count_terminal_tasks(),
            "max_chain_length": self._find_max_chain_length(),
            "critical_path": self._find_critical_path(),
            "bottleneck_tasks": self._find_bottleneck_tasks(),
            "circular_dependencies": self._detect_circular_dependencies()
        }
        
        logger.debug(f"Dependency graph analysis: {metrics}")
        return metrics
    
    def _count_independent_tasks(self) -> int:
        """Count tasks with no dependencies."""
        count = 0
        for task in self.task_selector.tasks.values():
            if not task.dependencies:
                count += 1
        return count
    
    def _count_terminal_tasks(self) -> int:
        """Count tasks that no other task depends on."""
        terminal_tasks = set()
        for task_id in self.task_selector.tasks:
            if task_id not in self.task_selector.dependency_graph or not self.task_selector.dependency_graph[task_id]:
                terminal_tasks.add(task_id)
        return len(terminal_tasks)
    
    def _find_max_chain_length(self) -> int:
        """Find the length of the longest dependency chain."""
        max_length = 0
        for task_id in self.task_selector.tasks:
            length = self._calculate_max_chain_from(task_id, set())
            max_length = max(max_length, length)
        return max_length
    
    def _calculate_max_chain_from(self, task_id: str, visited: Set[str]) -> int:
        """Calculate the maximum chain length starting from a task."""
        if task_id in visited:  # Prevent infinite recursion with circular dependencies
            return 0
        
        visited.add(task_id)
        
        if task_id not in self.task_selector.reverse_dependency_graph or not self.task_selector.reverse_dependency_graph[task_id]:
            return 1
        
        max_length = 0
        for dep_id in self.task_selector.reverse_dependency_graph[task_id]:
            length = 1 + self._calculate_max_chain_from(dep_id, visited.copy())
            max_length = max(max_length, length)
        
        return max_length
    
    def _find_critical_path(self) -> List[str]:
        """Find the critical path in the dependency graph."""
        # This is a simplified implementation; a real one would use more sophisticated algorithms
        paths = []
        start_tasks = [task_id for task_id, task in self.task_selector.tasks.items() if not task.dependencies]
        
        for start_id in start_tasks:
            self._find_paths_from(start_id, [], paths, set())
        
        if not paths:
            return []
        
        # Find the longest path
        critical_path = max(paths, key=len)
        logger.debug(f"Critical path identified: {critical_path}")
        return critical_path
    
    def _find_paths_from(self, task_id: str, current_path: List[str], all_paths: List[List[str]], visited: Set[str]) -> None:
        """Find all paths from a starting task."""
        if task_id in visited:  # Prevent infinite recursion
            return
        
        visited.add(task_id)
        current_path.append(task_id)
        
        if task_id not in self.task_selector.dependency_graph or not self.task_selector.dependency_graph[task_id]:
            # This is a terminal task
            all_paths.append(current_path.copy())
        else:
            for dependent_id in self.task_selector.dependency_graph[task_id]:
                self._find_paths_from(dependent_id, current_path.copy(), all_paths, visited.copy())
    
    def _find_bottleneck_tasks(self) -> List[str]:
        """Find tasks that many other tasks depend on."""
        bottlenecks = []
        threshold = max(3, len(self.task_selector.tasks) // 5)  # Adjust threshold based on total tasks
        
        for task_id, dependents in self.task_selector.dependency_graph.items():
            if len(dependents) >= threshold:
                bottlenecks.append(task_id)
        
        if bottlenecks:
            logger.info(f"Identified bottleneck tasks: {bottlenecks}")
        return bottlenecks
    
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the graph."""
        circular_deps = []
        visited = set()
        path = []
        
        # Check for circular dependencies starting from each task
        for task_id in self.task_selector.tasks:
            if task_id not in visited:
                self._dfs_circular_detect(task_id, path, visited, set(), circular_deps)
        
        if circular_deps:
            logger.warning(f"Detected circular dependencies: {circular_deps}")
        return circular_deps
    
    def _dfs_circular_detect(self, task_id: str, path: List[str], visited: Set[str], 
                           current_path: Set[str], circular_deps: List[List[str]]) -> None:
        """
        Depth-first search to detect circular dependencies.
        
        Args:
            task_id: Current task ID
            path: Current path through the graph 
            visited: Set of all visited tasks
            current_path: Set of tasks in current path (for cycle detection)
            circular_deps: List to store found cycles
        """
        visited.add(task_id)
        current_path.add(task_id)
        path.append(task_id)
        
        # Check dependencies of current task
        task = self.task_selector.tasks[task_id]
        for dep in task.dependencies:
            dep_id = dep.task_id
            
            if dep_id in current_path:
                # Found a cycle
                cycle_start = path.index(dep_id)
                cycle = path[cycle_start:] + [dep_id]
                if cycle not in circular_deps:
                    circular_deps.append(cycle)
            elif dep_id in self.task_selector.tasks and dep_id not in visited:
                self._dfs_circular_detect(dep_id, path.copy(), visited, current_path.copy(), circular_deps)
        
        # Remove from current path when backtracking
        current_path.remove(task_id)
    
    def resolve_dependencies(self, task_id: str) -> bool:
        """Attempt to resolve dependencies for a task."""
        if task_id not in self.task_selector.tasks:
            logger.error(f"Cannot resolve dependencies for unknown task: {task_id}")
            return False
        
        task = self.task_selector.tasks[task_id]
        
        # Check if all dependencies are satisfied
        all_satisfied = True
        for dep in task.dependencies:
            if dep.task_id in self.task_selector.tasks:
                dep_task = self.task_selector.tasks[dep.task_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    all_satisfied = False
                    logger.debug(f"Dependency {dep.task_id} is not completed (status: {dep_task.status.value})")
                    break
            else:
                all_satisfied = False
                logger.warning(f"Dependency {dep.task_id} not found in task list")
                break
        
        if all_satisfied and task.status == TaskStatus.BLOCKED:
            task.status = TaskStatus.READY
            task.updated_at = datetime.now()
            logger.info(f"Task {task_id} dependencies resolved, status updated to READY")
            return True
        
        return all_satisfied 