from typing import List, Optional, Dict
from src.server.models.task import Task

class TaskAggregator:
    def aggregate(self, responses: List[str]) -> str:
        return "\n".join(responses)

class AllAggregator(TaskAggregator):
    """Aggregates all responses by concatenating them."""
    pass

class TaskNode:
    def __init__(self, task: Task, aggregator: TaskAggregator = AllAggregator()):
        self.task = task
        self.aggregator = aggregator
        self.children: List[TaskNode] = []
        self._context: Optional[Dict] = None
        self._response: Optional[str] = None

    async def run(self, context: Optional[Dict] = None) -> str:
        """Enhanced run method with context management"""
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