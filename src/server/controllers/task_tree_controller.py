"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use task_tree_flow.py instead.
"""

import warnings
import logging
from typing import List, Optional, Dict
from src.server.models.task import Task
from src.server.controllers.task_tree_flow import TaskNode as NewTaskNode
from src.server.controllers.task_tree_flow_aggregators import AllAggregator as NewAllAggregator

# Show deprecation warning
warnings.warn(
    "task_tree_controller.py is deprecated and will be removed in a future version. "
    "Please use task_tree_flow.py instead.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)

class TaskAggregator:
    """
    DEPRECATED: Use task_tree_flow_aggregators.TaskAggregator instead.
    """
    def aggregate(self, responses: List[str]) -> str:
        warnings.warn(
            "TaskAggregator in task_tree_controller.py is deprecated. "
            "Use task_tree_flow_aggregators.TaskAggregator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return "\n".join(responses)

class AllAggregator(TaskAggregator):
    """
    DEPRECATED: Use task_tree_flow_aggregators.AllAggregator instead.
    """
    pass

class TaskNode:
    """
    DEPRECATED: Use task_tree_flow.TaskNode instead.
    
    This class provides backward compatibility with the old TaskNode interface.
    """
    def __init__(self, task: Task, aggregator: TaskAggregator = AllAggregator()):
        warnings.warn(
            "TaskNode in task_tree_controller.py is deprecated. "
            "Use task_tree_flow.TaskNode instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.task = task
        self.aggregator = aggregator
        self.children: List[TaskNode] = []
        self._context: Optional[Dict] = None
        self._response: Optional[str] = None
        
        # Create a new TaskNode instance for delegation
        self._new_node = NewTaskNode(
            task_id=task.id,
            task_manager=None,  # Will be set during run
            aggregator=NewAllAggregator(),
            transformer=None,
            execution_config=None
        )

    async def run(self, context: Optional[Dict] = None) -> str:
        """Enhanced run method with context management"""
        warnings.warn(
            "TaskNode.run in task_tree_controller.py is deprecated. "
            "Use task_tree_flow.TaskNode.run instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._context = context or {}
        
        # Get child responses first
        child_responses = []
        for child in self.children:
            response = await child.run(self._context)
            child_responses.append(response)

        # Aggregate child responses
        if child_responses:
            aggregated_response = self.aggregator.aggregate(child_responses)
            self._context["aggregated_response"] = aggregated_response

        # Run this node's task with updated context
        self._response = await self.task.run(self._context)
        return self._response 