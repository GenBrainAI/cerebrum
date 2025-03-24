from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import logging

from .task_selector import Task, TaskPriority

logger = logging.getLogger(__name__)

class PriorityCalculator:
    """Calculates dynamic task priorities based on multiple factors."""
    
    def __init__(self, base_weights=None):
        self.weights = base_weights or {
            "base_priority": 1.0,
            "urgency": 0.8,
            "dependency_impact": 0.7,
            "resource_availability": 0.6,
            "context_relevance": 0.5
        }
        self.tag_priorities = {}  # Tag-based priority boosts
        self.custom_priority_functions = []  # Custom priority calculation functions
        logger.info(f"Priority calculator initialized with weights: {self.weights}")
    
    def calculate_effective_priority(self, task: Task, context_manager=None, resource_manager=None) -> float:
        """Calculate effective priority based on multiple factors."""
        factors = {
            "base_priority": self._normalize_base_priority(task.priority),
            "urgency": self._calculate_urgency(task),
            "dependency_impact": self._calculate_dependency_impact(task, context_manager.task_selector if context_manager else None),
            "resource_availability": self._calculate_resource_availability(task, resource_manager),
            "context_relevance": self._calculate_context_relevance(task, context_manager)
        }
        
        # Apply tag-based priority boosts
        tag_boost = self._calculate_tag_priority_factor(task)
        if tag_boost > 0:
            factors["tag_priority"] = tag_boost
            
        # Apply custom priority functions
        for idx, func in enumerate(self.custom_priority_functions):
            result = func(task)
            if result is not None:
                factors[f"custom_{idx}"] = result
        
        # Calculate weighted sum
        effective_priority = 0
        for factor, value in factors.items():
            if factor in self.weights:
                effective_priority += value * self.weights.get(factor, 1.0)
            else:
                effective_priority += value  # Default weight of 1.0 for custom factors
        
        logger.debug(f"Calculated effective priority for task {task.id}: {effective_priority}")
        logger.debug(f"Priority factors: {factors}")
        
        return effective_priority
    
    def _normalize_base_priority(self, priority: TaskPriority) -> float:
        """Normalize base priority to 0-1 range."""
        return priority.value / 100.0
    
    def _calculate_urgency(self, task: Task) -> float:
        """Calculate urgency factor based on creation time and deadlines."""
        # Implementation depends on how urgency is defined in your system
        # This is a simplified example
        if 'deadline' in task.metadata:
            deadline = task.metadata['deadline']
            now = datetime.now()
            if isinstance(deadline, datetime):
                time_left = (deadline - now).total_seconds()
                if time_left <= 0:
                    return 1.0  # Maximum urgency for past deadline
                
                # Normalize: closer to deadline = higher urgency
                time_factor = min(1.0, max(0.0, 1.0 - (time_left / (24 * 3600))))  # Use 24h as reference
                return time_factor
        
        # Consider waiting time as a factor of urgency
        return self._calculate_waiting_time_factor(task)
    
    def _calculate_waiting_time_factor(self, task: Task) -> float:
        """Calculate a factor based on how long the task has been waiting."""
        now = datetime.now()
        wait_time = (now - task.created_at).total_seconds()
        
        # Normalize waiting time: longer wait = higher priority
        # Using 4 hours as reference maximum wait time
        return min(1.0, wait_time / (4 * 3600))
    
    def _calculate_dependency_impact(self, task: Task, task_selector) -> float:
        """Calculate impact of this task on dependent tasks."""
        if not task_selector:
            return 0.0
            
        # Count how many tasks depend on this one
        dependent_count = len(task_selector.dependency_graph.get(task.id, set()))
        
        # Normalize: more dependents = higher priority
        return min(1.0, dependent_count / 5.0)  # Using 5 as reference maximum
    
    def _calculate_resource_availability(self, task: Task, resource_manager) -> float:
        """Calculate how well the task matches available resources."""
        if not resource_manager or not task.estimated_resources:
            return 0.5  # Neutral score if no resource info
            
        available = resource_manager.get_available_resources()
        
        # Check if required resources are available
        can_run = True
        resource_match = 0.0
        
        for resource_type, amount in task.estimated_resources.items():
            if resource_type in available:
                if available[resource_type] < amount:
                    can_run = False
                    # Calculate partial availability
                    resource_match += (available[resource_type] / amount) / len(task.estimated_resources)
                else:
                    resource_match += 1.0 / len(task.estimated_resources)
            else:
                can_run = False
        
        # Prioritize tasks that can run right now
        return 1.0 if can_run else resource_match
    
    def _calculate_context_relevance(self, task: Task, context_manager) -> float:
        """Calculate how relevant this task is to current context."""
        if not context_manager or not task.context_requirements:
            return 0.5  # Neutral score if no context info
            
        # Count how many context requirements are already available
        satisfied = 0
        for req in task.context_requirements:
            if context_manager.get_context(req) is not None:
                satisfied += 1
                
        # Normalize: more satisfied requirements = higher priority
        return satisfied / len(task.context_requirements) if task.context_requirements else 0.5
    
    def _calculate_tag_priority_factor(self, task: Task) -> float:
        """Calculate priority boost based on tags."""
        if not task.tags or not self.tag_priorities:
            return 0.0
            
        # For tasks with the "background" tag, use it to lower priority
        if "background" in task.tags and "background" in self.tag_priorities:
            return self.tag_priorities["background"]
            
        # For other tags, find highest priority boost from tags
        max_boost = 0.0
        for tag in task.tags:
            max_boost = max(max_boost, self.tag_priorities.get(tag, 0.0))
            
        return max_boost
    
    def calculate_all_priorities(self, tasks: List[Task], context_manager=None, resource_manager=None) -> Dict[str, float]:
        """Calculate priorities for all tasks."""
        result = {}
        for task in tasks:
            result[task.id] = self.calculate_effective_priority(task, context_manager, resource_manager)
        return result
    
    def set_priority_factors(self, weights: Dict[str, float]) -> None:
        """Update the weights for different priority factors."""
        self.weights.update(weights)
        logger.info(f"Updated priority factors: {self.weights}")
    
    def set_tag_priorities(self, tag_priorities: Dict[str, float]) -> None:
        """Set priority boosts for specific tags."""
        self.tag_priorities = tag_priorities
        logger.info(f"Set tag priorities: {self.tag_priorities}")
    
    def add_custom_priority_function(self, func: Callable[[Task], float]) -> None:
        """Add a custom function that calculates a priority factor."""
        self.custom_priority_functions.append(func)
        logger.info(f"Added custom priority function: {func.__name__}")
    
    def clear_priorities(self) -> None:
        """Reset all priority settings to defaults."""
        self.weights = {
            "base_priority": 1.0,
            "urgency": 0.8,
            "dependency_impact": 0.7,
            "resource_availability": 0.6,
            "context_relevance": 0.5
        }
        self.tag_priorities = {}
        self.custom_priority_functions = []
        logger.info("Reset all priority settings to defaults")
    
    def get_task_priority_score(self, task: Task) -> float:
        """Get the base priority score normalized to 0-1 range."""
        return self._normalize_base_priority(task.priority) 