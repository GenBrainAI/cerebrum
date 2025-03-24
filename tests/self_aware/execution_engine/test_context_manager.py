import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.server.execution_engine.context_manager import (
    ContextManager, ContextType, ContextEntry
)


@pytest.fixture
def context_manager():
    """Create a ContextManager instance with mocked task_selector."""
    task_selector = MagicMock()
    return ContextManager(task_selector)


class TestContextManager:
    """Tests for the ContextManager class."""

    def test_set_get_context(self, context_manager):
        """Test setting and getting context values."""
        # Set a context value
        context_manager.set_context("test_key", "test_value", ContextType.GLOBAL)
        
        # Get the context value
        value = context_manager.get_context("test_key")
        assert value == "test_value"
        
        # Set a different context type
        context_manager.set_context("test_key", "task_value", ContextType.TASK)
        
        # Task context overrides global
        value = context_manager.get_context("test_key")
        assert value == "task_value"
        
        # Get from specific context type
        global_value = context_manager.get_typed_context("test_key", ContextType.GLOBAL)
        assert global_value == "test_value"

    def test_context_precedence(self, context_manager):
        """Test context type precedence."""
        # Set values in different context types
        context_manager.set_context("precedence_key", "global_value", ContextType.GLOBAL)
        context_manager.set_context("precedence_key", "session_value", ContextType.SESSION)
        context_manager.set_context("precedence_key", "task_value", ContextType.TASK)
        context_manager.set_context("precedence_key", "temp_value", ContextType.TEMPORARY)
        
        # Check precedence (TASK > SESSION > GLOBAL > TEMPORARY)
        value = context_manager.get_context("precedence_key")
        assert value == "task_value"
        
        # Delete task context
        context_manager.delete_context("precedence_key", ContextType.TASK)
        value = context_manager.get_context("precedence_key")
        assert value == "session_value"
        
        # Delete session context
        context_manager.delete_context("precedence_key", ContextType.SESSION)
        value = context_manager.get_context("precedence_key")
        assert value == "global_value"
        
        # Delete global context
        context_manager.delete_context("precedence_key", ContextType.GLOBAL)
        value = context_manager.get_context("precedence_key")
        assert value == "temp_value"

    def test_delete_context(self, context_manager):
        """Test deleting context values."""
        # Set a context value
        context_manager.set_context("delete_key", "value", ContextType.GLOBAL)
        assert context_manager.get_context("delete_key") == "value"
        
        # Delete the context
        result = context_manager.delete_context("delete_key", ContextType.GLOBAL)
        assert result is True
        assert context_manager.get_context("delete_key") is None
        
        # Deleting non-existent context
        result = context_manager.delete_context("non_existent_key")
        assert result is False

    def test_clear_context(self, context_manager):
        """Test clearing all contexts of a specific type."""
        # Set multiple values in a context type
        context_manager.set_context("key1", "value1", ContextType.SESSION)
        context_manager.set_context("key2", "value2", ContextType.SESSION)
        
        # Clear the context type
        context_manager.clear_context(ContextType.SESSION)
        
        # All keys should be gone
        assert context_manager.get_typed_context("key1", ContextType.SESSION) is None
        assert context_manager.get_typed_context("key2", ContextType.SESSION) is None

    def test_expired_context(self, context_manager):
        """Test handling of expired context entries."""
        # Set context with expiration
        expires_at = datetime.now() + timedelta(seconds=1)
        context_manager.set_context("expiring_key", "expiring_value", 
                                    ContextType.TEMPORARY, expires_at)
        
        # Should be available before expiration
        assert context_manager.get_context("expiring_key") == "expiring_value"
        
        # Manually simulate expiration by creating a past expiration time
        context_manager.contexts[ContextType.TEMPORARY]["expiring_key"].expires_at = datetime.now() - timedelta(seconds=1)
        
        # Should not be available after expiration
        assert context_manager.get_context("expiring_key") is None

    def test_get_current_context(self, context_manager):
        """Test getting all current context values."""
        # Set values in different context types
        context_manager.set_context("global_key", "global_value", ContextType.GLOBAL)
        context_manager.set_context("session_key", "session_value", ContextType.SESSION)
        context_manager.set_context("task_key", "task_value", ContextType.TASK)
        context_manager.set_context("temp_key", "temp_value", ContextType.TEMPORARY)
        context_manager.set_context("override_key", "global_override", ContextType.GLOBAL)
        context_manager.set_context("override_key", "session_override", ContextType.SESSION)
        
        # Get current context
        current = context_manager.get_current_context()
        
        # Should contain all non-expired keys
        assert "global_key" in current
        assert "session_key" in current
        assert "task_key" in current
        assert "temp_key" in current
        assert "override_key" in current
        
        # Override key should have session value
        assert current["override_key"] == "session_override"

    def test_context_validation(self, context_manager):
        """Test context validation rules."""
        # Add a validation rule
        validation_func = lambda x: isinstance(x, int) and x > 0
        context_manager.add_validation_rule("validated_key", validation_func)
        
        # Valid value should be accepted
        context_manager.set_context("validated_key", 42, ContextType.GLOBAL)
        assert context_manager.get_context("validated_key") == 42
        
        # Invalid value should raise exception
        with pytest.raises(ValueError):
            context_manager.set_context("validated_key", "not_an_int", ContextType.GLOBAL)
        
        with pytest.raises(ValueError):
            context_manager.set_context("validated_key", -5, ContextType.GLOBAL)

    def test_propagation_rules(self, context_manager):
        """Test context propagation rules."""
        # Add a propagation rule
        transform_func = lambda x: x.upper()
        context_manager.add_propagation_rule("source_key", "target_key", transform_func)
        
        # Set source context, should trigger propagation
        context_manager.set_context("source_key", "propagate_me", ContextType.GLOBAL)
        
        # Target key should have transformed value
        assert context_manager.get_context("target_key") == "PROPAGATE_ME"
        
        # Target should be in TASK context by default
        assert "target_key" in context_manager.contexts[ContextType.TASK]

    def test_prepare_task_context(self, context_manager):
        """Test preparing context for a task."""
        # Mock task selector and task
        task = MagicMock()
        task.context_requirements = ["req1", "req2"]
        task.id = "task123"
        
        context_manager.task_selector.tasks = {"task123": task}
        
        # Set required context
        context_manager.set_context("req1", "value1", ContextType.GLOBAL)
        context_manager.set_context("req2", "value2", ContextType.SESSION)
        context_manager.set_context("extra", "extra_value", ContextType.TASK)
        
        # Prepare task context
        task_context = context_manager.prepare_task_context("task123")
        
        # Should only contain required keys
        assert "req1" in task_context
        assert "req2" in task_context
        assert "extra" not in task_context
        
        # Values should be correct
        assert task_context["req1"] == "value1"
        assert task_context["req2"] == "value2"

    def test_serialize_deserialize_context(self, context_manager):
        """Test context serialization and deserialization."""
        # Set some context values
        context_manager.set_context("serialize_key1", "value1", ContextType.GLOBAL)
        context_manager.set_context("serialize_key2", {"nested": "value2"}, ContextType.SESSION)
        
        # Serialize
        serialized = context_manager.serialize_context()
        
        # Create a new context manager
        new_context_manager = ContextManager()
        
        # Deserialize into the new manager
        new_context_manager.deserialize_context(serialized)
        
        # Check values were restored
        assert new_context_manager.get_context("serialize_key1") == "value1"
        assert new_context_manager.get_context("serialize_key2") == {"nested": "value2"}

    def test_context_diff(self, context_manager):
        """Test getting context differences."""
        # Set up first context manager
        context_manager.set_context("common_key", "common_value", ContextType.GLOBAL)
        context_manager.set_context("diff_key1", "value1", ContextType.SESSION)
        
        # Set up second context manager
        other_context = ContextManager()
        other_context.set_context("common_key", "common_value", ContextType.GLOBAL)
        other_context.set_context("diff_key2", "value2", ContextType.SESSION)
        other_context.set_context("modified_key", "old_value", ContextType.GLOBAL)
        
        # Modify a value in the first context
        context_manager.set_context("modified_key", "new_value", ContextType.GLOBAL)
        
        # Get diff
        diff = context_manager.get_context_diff(other_context)
        
        # Check diff structure
        assert "added" in diff
        assert "modified" in diff
        assert "removed" in diff
        
        # Check specific differences
        assert "diff_key1" in diff["added"]
        assert "diff_key2" in diff["removed"]
        assert "modified_key" in diff["modified"]
        assert diff["modified"]["modified_key"]["old"] == "old_value"
        assert diff["modified"]["modified_key"]["new"] == "new_value" 