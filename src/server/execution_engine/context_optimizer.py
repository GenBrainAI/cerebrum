from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)

class ContextOptimizer:
    """Optimizes context storage and management for efficient execution."""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.usage_stats = {}  # key -> {access_count, last_access}
        self.dependency_graph = {}  # key -> [dependent_keys]
        self.optimization_thresholds = {
            "cleanup_threshold": 0.7,  # Percentage of unused context to trigger cleanup
            "access_threshold": 5,  # Minimum accesses to keep during optimization
            "time_threshold": 3600  # Time in seconds since last access to consider stale
        }
        logger.info("Context optimizer initialized")
    
    def track_context_access(self, key: str) -> None:
        """Track access to context keys for optimization."""
        now = datetime.now()
        
        if key not in self.usage_stats:
            self.usage_stats[key] = {"access_count": 0, "last_access": now}
        
        self.usage_stats[key]["access_count"] += 1
        self.usage_stats[key]["last_access"] = now
        logger.debug(f"Tracked access to context key: {key}")
    
    def track_context_dependency(self, dependent_key: str, dependency_key: str) -> None:
        """Track dependencies between context keys."""
        if dependency_key not in self.dependency_graph:
            self.dependency_graph[dependency_key] = []
        
        if dependent_key not in self.dependency_graph[dependency_key]:
            self.dependency_graph[dependency_key].append(dependent_key)
            logger.debug(f"Tracked dependency: {dependency_key} -> {dependent_key}")
    
    def optimize(self) -> int:
        """Optimize the context by removing stale or unused entries."""
        if not self.context_manager.optimization_enabled:
            logger.debug("Context optimization is disabled")
            return 0
        
        removed_count = 0
        now = datetime.now()
        
        # Update the tracked keys from current context
        current_context = self.context_manager.get_current_context()
        for key in current_context:
            if key not in self.usage_stats:
                self.usage_stats[key] = {"access_count": 0, "last_access": now}
        
        # Find candidates for removal
        candidates = []
        for key, stats in self.usage_stats.items():
            # Skip keys not in context (already removed)
            if key not in current_context:
                continue
                
            # Skip keys with dependencies
            if key in self.dependency_graph and self.dependency_graph[key]:
                continue
                
            # Calculate staleness score (higher means more stale)
            time_since_access = (now - stats["last_access"]).total_seconds()
            staleness = time_since_access / self.optimization_thresholds["time_threshold"]
            
            # Calculate usage score (higher means less used)
            usage = 1.0 - min(1.0, stats["access_count"] / self.optimization_thresholds["access_threshold"])
            
            # Combine scores
            score = (staleness + usage) / 2.0
            
            if score > self.optimization_thresholds["cleanup_threshold"]:
                candidates.append((key, score))
        
        # Sort candidates by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Remove high-scoring candidates
        for key, score in candidates:
            # Check which context type this key belongs to
            for context_type in [ContextType.TEMPORARY, ContextType.TASK]:
                if key in self.context_manager.contexts[context_type]:
                    self.context_manager.delete_context(key, context_type)
                    removed_count += 1
                    logger.debug(f"Optimized out context key: {key} (score: {score:.2f})")
                    break
        
        # Also clean up expired entries
        for context_type in self.context_manager.contexts:
            expired_keys = []
            for key, entry in self.context_manager.contexts[context_type].items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.context_manager.delete_context(key, context_type)
                removed_count += 1
                logger.debug(f"Removed expired context key: {key}")
        
        # Clean up usage stats for keys that no longer exist
        keys_to_remove = []
        for key in self.usage_stats:
            exists = False
            for context_type in self.context_manager.contexts:
                if key in self.context_manager.contexts[context_type]:
                    exists = True
                    break
            
            if not exists:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.usage_stats[key]
        
        if removed_count > 0:
            logger.info(f"Optimization completed: removed {removed_count} context entries")
        return removed_count
    
    def set_optimization_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update optimization thresholds."""
        logger.info(f"Updating optimization thresholds: {thresholds}")
        for key, value in thresholds.items():
            if key in self.optimization_thresholds:
                self.optimization_thresholds[key] = value
                logger.debug(f"Updated threshold {key}: {value}")
            else:
                logger.warning(f"Unknown optimization threshold: {key}")
    
    def analyze_context_usage(self) -> Dict[str, Any]:
        """Analyze context usage patterns."""
        analysis = {
            "total_keys": len(self.usage_stats),
            "avg_access_count": 0,
            "most_accessed": [],
            "least_accessed": [],
            "stalest": []
        }
        
        if not self.usage_stats:
            logger.info("No context usage stats available for analysis")
            return analysis
        
        # Calculate average access count
        total_accesses = sum(stats["access_count"] for stats in self.usage_stats.values())
        analysis["avg_access_count"] = total_accesses / len(self.usage_stats)
        
        # Sort by access count
        by_access = sorted(self.usage_stats.items(), key=lambda x: x[1]["access_count"], reverse=True)
        
        # Most accessed keys
        analysis["most_accessed"] = [
            {"key": key, "count": stats["access_count"]} 
            for key, stats in by_access[:5]
        ]
        
        # Least accessed keys
        analysis["least_accessed"] = [
            {"key": key, "count": stats["access_count"]} 
            for key, stats in by_access[-5:]
        ]
        
        # Stalest keys
        now = datetime.now()
        by_staleness = sorted(
            self.usage_stats.items(),
            key=lambda x: (now - x[1]["last_access"]).total_seconds(),
            reverse=True
        )
        
        analysis["stalest"] = [
            {
                "key": key, 
                "seconds_since_access": (now - stats["last_access"]).total_seconds()
            } 
            for key, stats in by_staleness[:5]
        ]
        
        logger.info(f"Context usage analysis completed: {len(self.usage_stats)} keys analyzed")
        return analysis 