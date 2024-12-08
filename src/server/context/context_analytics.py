from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from collections import defaultdict

class ContextUsageMetrics(BaseModel):
    """Metrics for context usage analysis."""
    views: int = 0
    successful_enhancements: int = 0
    failed_enhancements: int = 0
    average_relevance: float = 0.0
    last_used: Optional[datetime] = None

class ContextAnalytics:
    """Tracks and analyzes context usage."""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'total': ContextUsageMetrics(),
            'by_type': defaultdict(ContextUsageMetrics),
            'by_task': defaultdict(ContextUsageMetrics)
        })

    async def record_context_usage(
        self, 
        task_id: str,
        contexts: List[Dict[str, Any]],
        success: bool = True
    ):
        """Record usage of contexts for a task."""
        timestamp = datetime.now()
        
        # Update total metrics
        total_metrics = self.metrics[task_id]['total']
        total_metrics.views += 1
        if success:
            total_metrics.successful_enhancements += 1
        else:
            total_metrics.failed_enhancements += 1
        total_metrics.last_used = timestamp

        # Update per-type metrics
        for context in contexts:
            type_metrics = self.metrics[task_id]['by_type'][context['type']]
            type_metrics.views += 1
            if success:
                type_metrics.successful_enhancements += 1
            else:
                type_metrics.failed_enhancements += 1
            type_metrics.last_used = timestamp
            
            # Update relevance scores
            if 'relevance' in context:
                type_metrics.average_relevance = (
                    (type_metrics.average_relevance * (type_metrics.views - 1) + 
                     context['relevance']) / type_metrics.views
                )

    async def get_task_analytics(self, task_id: str) -> Dict[str, Any]:
        """Get analytics for a specific task."""
        if task_id not in self.metrics:
            return {}
            
        task_metrics = self.metrics[task_id]
        return {
            'total_usage': task_metrics['total'].dict(),
            'usage_by_type': {
                context_type: metrics.dict()
                for context_type, metrics in task_metrics['by_type'].items()
            }
        }

    async def get_summary_analytics(self) -> Dict[str, Any]:
        """Get summary analytics across all tasks."""
        summary = {
            'total_tasks': len(self.metrics),
            'total_views': 0,
            'success_rate': 0.0,
            'type_distribution': defaultdict(int),
            'most_active_tasks': []
        }
        
        for task_id, metrics in self.metrics.items():
            total = metrics['total']
            summary['total_views'] += total.views
            
            # Calculate success rate
            if total.views > 0:
                success_rate = total.successful_enhancements / total.views
                summary['most_active_tasks'].append({
                    'task_id': task_id,
                    'views': total.views,
                    'success_rate': success_rate
                })
            
            # Track type distribution
            for context_type in metrics['by_type'].keys():
                summary['type_distribution'][context_type] += 1
        
        # Sort most active tasks
        summary['most_active_tasks'].sort(key=lambda x: x['views'], reverse=True)
        summary['most_active_tasks'] = summary['most_active_tasks'][:10]
        
        return summary
