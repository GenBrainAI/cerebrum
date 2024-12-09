from typing import Dict, Any, Optional
from datetime import datetime

class ContextAnalytics:
    """Handles analytics for context usage and effectiveness."""
    
    def __init__(self):
        self.analytics_store = {}

    async def get_task_analytics(self, task_id: str) -> Dict[str, Any]:
        """Get analytics data for a specific task."""
        if task_id not in self.analytics_store:
            # Return default structure if no analytics exist
            return {
                'total_usage': {
                    'views': 0,
                    'successful_enhancements': 0,
                    'last_used': None
                },
                'usage_by_type': {}
            }
        
        return self.analytics_store[task_id]

    async def record_context_usage(
        self,
        task_id: str,
        context_type: str,
        success: bool = True,
        relevance: Optional[float] = None
    ):
        """Record usage of context for a task."""
        if task_id not in self.analytics_store:
            self.analytics_store[task_id] = {
                'total_usage': {
                    'views': 0,
                    'successful_enhancements': 0,
                    'last_used': None
                },
                'usage_by_type': {}
            }
        
        analytics = self.analytics_store[task_id]
        
        # Update total usage
        analytics['total_usage']['views'] += 1
        if success:
            analytics['total_usage']['successful_enhancements'] += 1
        analytics['total_usage']['last_used'] = datetime.now()
        
        # Update type-specific usage
        if context_type not in analytics['usage_by_type']:
            analytics['usage_by_type'][context_type] = {
                'views': 0,
                'successful_enhancements': 0,
                'average_relevance': 0.0,
                'relevance_count': 0
            }
        
        type_stats = analytics['usage_by_type'][context_type]
        type_stats['views'] += 1
        if success:
            type_stats['successful_enhancements'] += 1
        
        if relevance is not None:
            current_avg = type_stats['average_relevance']
            current_count = type_stats['relevance_count']
            new_count = current_count + 1
            type_stats['average_relevance'] = (
                (current_avg * current_count + relevance) / new_count
            )
            type_stats['relevance_count'] = new_count

    async def clear_analytics(self, task_id: Optional[str] = None):
        """Clear analytics data for a task or all tasks."""
        if task_id:
            if task_id in self.analytics_store:
                del self.analytics_store[task_id]
        else:
            self.analytics_store.clear()
