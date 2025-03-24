import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.server.execution_engine.context_optimizer import ContextOptimizer
from src.server.execution_engine.context_manager import ContextManager, ContextType


@pytest.fixture
def context_manager():
    """Create a ContextManager instance for testing."""
    return ContextManager()


@pytest.fixture
def context_optimizer(context_manager):
    """Create a ContextOptimizer instance for testing."""
    return ContextOptimizer(context_manager)


class TestContextOptimizer:
    """Tests for the ContextOptimizer class."""

    def test_track_context_access(self, context_optimizer):
        """Test tracking context access."""
        # Track some accesses
        context_optimizer.track_context_access("key1")
        context_optimizer.track_context_access("key1")  # Access twice
        context_optimizer.track_context_access("key2")
        
        # Check usage stats were updated
        assert "key1" in context_optimizer.usage_stats
        assert "key2" in context_optimizer.usage_stats
        assert context_optimizer.usage_stats["key1"]["access_count"] == 2
        assert context_optimizer.usage_stats["key2"]["access_count"] == 1

    def test_track_context_dependency(self, context_optimizer):
        """Test tracking dependencies between context keys."""
        # Track dependencies
        context_optimizer.track_context_dependency("dependent_key", "dependency_key")
        context_optimizer.track_context_dependency("another_dependent", "dependency_key")
        
        # Check dependency graph was updated
        assert "dependency_key" in context_optimizer.dependency_graph
        assert "dependent_key" in context_optimizer.dependency_graph["dependency_key"]
        assert "another_dependent" in context_optimizer.dependency_graph["dependency_key"]
        assert len(context_optimizer.dependency_graph["dependency_key"]) == 2

    def test_optimize_disabled(self, context_optimizer, context_manager):
        """Test that optimization does nothing when disabled."""
        # Disable optimization
        context_manager.optimization_enabled = False
        
        # Set some context
        context_manager.set_context("test_key", "test_value", ContextType.TEMPORARY)
        
        # Optimize (should do nothing)
        removed = context_optimizer.optimize()
        
        # No keys should be removed
        assert removed == 0
        assert context_manager.get_context("test_key") == "test_value"

    def test_optimize_removes_stale_entries(self, context_optimizer, context_manager):
        """Test that optimization removes stale entries."""
        # Set custom thresholds for testing
        context_optimizer.set_optimization_thresholds({
            "cleanup_threshold": 0.5,  # Lower threshold to make cleanup more aggressive
            "access_threshold": 2,     # Keys with fewer than 2 accesses are candidates
            "time_threshold": 3600     # 1 hour staleness
        })
        
        # Set some context values
        context_manager.set_context("stale_key", "stale_value", ContextType.TEMPORARY)
        context_manager.set_context("used_key", "used_value", ContextType.TEMPORARY)
        
        # Track access to the used key
        context_optimizer.track_context_access("used_key")
        context_optimizer.track_context_access("used_key")
        context_optimizer.track_context_access("used_key")
        
        # Make the stale key appear old by setting an old access time
        if "stale_key" not in context_optimizer.usage_stats:
            context_optimizer.track_context_access("stale_key")
        context_optimizer.usage_stats["stale_key"]["last_access"] = datetime.now() - timedelta(hours=2)
        
        # Optimize
        removed = context_optimizer.optimize()
        
        # The stale key should be removed
        assert removed == 1
        assert context_manager.get_context("stale_key") is None
        assert context_manager.get_context("used_key") == "used_value"

    def test_optimize_respects_dependencies(self, context_optimizer, context_manager):
        """Test that optimization respects dependencies."""
        # Set custom thresholds
        context_optimizer.set_optimization_thresholds({
            "cleanup_threshold": 0.5,
            "access_threshold": 2,
            "time_threshold": 3600
        })
        
        # Set up a dependency
        context_manager.set_context("dependency_key", "dependency_value", ContextType.TEMPORARY)
        context_manager.set_context("dependent_key", "dependent_value", ContextType.TEMPORARY)
        context_optimizer.track_context_dependency("dependent_key", "dependency_key")
        
        # Make both keys appear stale
        context_optimizer.track_context_access("dependency_key")
        context_optimizer.track_context_access("dependent_key")
        context_optimizer.usage_stats["dependency_key"]["last_access"] = datetime.now() - timedelta(hours=2)
        context_optimizer.usage_stats["dependent_key"]["last_access"] = datetime.now() - timedelta(hours=2)
        
        # Optimize
        removed = context_optimizer.optimize()
        
        # The dependency key should not be removed (because it has dependents)
        assert context_manager.get_context("dependency_key") == "dependency_value"
        
        # The dependent key might be removed
        assert removed <= 1
        if removed == 1:
            assert context_manager.get_context("dependent_key") is None

    def test_optimize_removes_expired_entries(self, context_optimizer, context_manager):
        """Test that optimization removes expired entries."""
        # Set context with expiration
        expiration = datetime.now() - timedelta(seconds=1)  # Already expired
        context_manager.set_context("expired_key", "expired_value", 
                                  ContextType.TEMPORARY, expiration)
        
        # Optimize
        removed = context_optimizer.optimize()
        
        # The expired key should be removed
        assert removed == 1
        assert context_manager.get_context("expired_key") is None

    def test_set_optimization_thresholds(self, context_optimizer):
        """Test setting optimization thresholds."""
        # Set custom thresholds
        new_thresholds = {
            "cleanup_threshold": 0.8,
            "access_threshold": 10,
            "time_threshold": 7200
        }
        context_optimizer.set_optimization_thresholds(new_thresholds)
        
        # Check thresholds were updated
        assert context_optimizer.optimization_thresholds["cleanup_threshold"] == 0.8
        assert context_optimizer.optimization_thresholds["access_threshold"] == 10
        assert context_optimizer.optimization_thresholds["time_threshold"] == 7200
        
        # Invalid threshold should be ignored
        context_optimizer.set_optimization_thresholds({"invalid_threshold": 1.0})
        assert "invalid_threshold" not in context_optimizer.optimization_thresholds

    def test_analyze_context_usage(self, context_optimizer):
        """Test analyzing context usage patterns."""
        # Track some context accesses
        for i in range(10):
            context_optimizer.track_context_access("frequent_key")
        
        context_optimizer.track_context_access("rare_key")
        
        # Set different access times
        now = datetime.now()
        context_optimizer.usage_stats["old_key"] = {
            "access_count": 5,
            "last_access": now - timedelta(days=10)
        }
        context_optimizer.usage_stats["recent_key"] = {
            "access_count": 5,
            "last_access": now - timedelta(minutes=5)
        }
        
        # Analyze usage
        analysis = context_optimizer.analyze_context_usage()
        
        # Check analysis structure
        assert "total_keys" in analysis
        assert "avg_access_count" in analysis
        assert "most_accessed" in analysis
        assert "least_accessed" in analysis
        assert "stalest" in analysis
        
        # Check specific values
        assert analysis["total_keys"] == 4
        
        # frequent_key should be in most_accessed
        most_accessed_keys = [item["key"] for item in analysis["most_accessed"]]
        assert "frequent_key" in most_accessed_keys
        
        # rare_key should be in least_accessed
        least_accessed_keys = [item["key"] for item in analysis["least_accessed"]]
        assert "rare_key" in least_accessed_keys
        
        # old_key should be in stalest
        stalest_keys = [item["key"] for item in analysis["stalest"]]
        assert "old_key" in stalest_keys

    @patch("src.server.execution_engine.context_optimizer.datetime")
    def test_optimize_with_mock_time(self, mock_datetime, context_optimizer, context_manager):
        """Test optimization with mocked time for deterministic testing."""
        # Mock datetime.now()
        fixed_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_now
        
        # Set up context and usage stats
        context_manager.set_context("recent_key", "recent_value", ContextType.TEMPORARY)
        context_manager.set_context("old_key", "old_value", ContextType.TEMPORARY)
        
        # Set usage stats with controlled times
        context_optimizer.usage_stats = {
            "recent_key": {
                "access_count": 5,
                "last_access": fixed_now - timedelta(minutes=30)
            },
            "old_key": {
                "access_count": 1,
                "last_access": fixed_now - timedelta(hours=2)
            }
        }
        
        # Set thresholds
        context_optimizer.set_optimization_thresholds({
            "cleanup_threshold": 0.6,
            "access_threshold": 3,
            "time_threshold": 3600  # 1 hour
        })
        
        # Optimize
        removed = context_optimizer.optimize()
        
        # old_key should be removed (low access count, old)
        assert removed == 1
        assert context_manager.get_context("old_key") is None
        assert context_manager.get_context("recent_key") == "recent_value"

    def test_cleanup_usage_stats(self, context_optimizer, context_manager):
        """Test cleanup of usage stats for keys that no longer exist."""
        # Track stats for keys that don't exist in context
        context_optimizer.track_context_access("nonexistent_key1")
        context_optimizer.track_context_access("nonexistent_key2")
        
        # Set a key that does exist
        context_manager.set_context("existing_key", "value", ContextType.TEMPORARY)
        context_optimizer.track_context_access("existing_key")
        
        # Before optimization
        assert "nonexistent_key1" in context_optimizer.usage_stats
        assert "nonexistent_key2" in context_optimizer.usage_stats
        assert "existing_key" in context_optimizer.usage_stats
        
        # Optimize
        context_optimizer.optimize()
        
        # After optimization, stats for nonexistent keys should be removed
        assert "nonexistent_key1" not in context_optimizer.usage_stats
        assert "nonexistent_key2" not in context_optimizer.usage_stats
        assert "existing_key" in context_optimizer.usage_stats 