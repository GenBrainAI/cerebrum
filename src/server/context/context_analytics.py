from typing import Dict, List, Optional

class ContextAnalytics:
    def __init__(self):
        self.context_usage = {}

    async def record_context_usage(self, task_id: str, success: bool = True):
        """
        Record usage of a context
        Args:
            task_id: The ID of the task using the context
            success: Whether the context usage was successful
        """
        if task_id not in self.context_usage:
            self.context_usage[task_id] = {
                'total_uses': 0,
                'successful_uses': 0
            }
        
        usage = self.context_usage[task_id]
        usage['total_uses'] += 1
        if success:
            usage['successful_uses'] += 1

    def get_context_stats(self, task_id: str) -> Optional[Dict]:
        """
        Get usage statistics for a specific task
        Args:
            task_id: The ID of the task
        Returns:
            Dictionary containing usage statistics or None if task not found
        """
        if task_id not in self.context_usage:
            return None
            
        usage = self.context_usage[task_id]
        return {
            'total_uses': usage['total_uses'],
            'successful_uses': usage['successful_uses'],
            'success_rate': usage['successful_uses'] / usage['total_uses'] if usage['total_uses'] > 0 else 0.0
        }
