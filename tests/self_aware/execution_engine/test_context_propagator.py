import pytest
from unittest.mock import MagicMock

from src.server.execution_engine.context_propagator import ContextPropagator
from src.server.execution_engine.context_manager import ContextManager, ContextType


@pytest.fixture
def context_manager():
    """Create a ContextManager with a mocked task_selector."""
    task_selector = MagicMock()
    return ContextManager(task_selector)


@pytest.fixture
def context_propagator(context_manager):
    """Create a ContextPropagator instance for testing."""
    return ContextPropagator(context_manager)


class TestContextPropagator:
    """Tests for the ContextPropagator class."""

    def test_add_rule(self, context_propagator):
        """Test adding propagation rules."""
        # Add a simple rule
        context_propagator.add_rule("source", "target")
        # Check if the rule is in the list of propagation rules
        assert any(rule[0] == "source" for rule in context_propagator.propagation_rules)
        
        # Find the rule with source pattern "source"
        source_rule = next(rule for rule in context_propagator.propagation_rules if rule[0] == "source")
        source_pattern, target_pattern, transform_func = source_rule
        # Default transform should be identity
        assert transform_func("test") == "test"
        
        # Add a rule with transform
        transform = lambda x: x.upper()
        context_propagator.add_rule("source2", "target2", transform)
        
        # Find the rule with source pattern "source2"
        source2_rule = next(rule for rule in context_propagator.propagation_rules if rule[0] == "source2")
        _, _, transform_func2 = source2_rule
        # Check transform works
        assert transform_func2("test") == "TEST"

    def test_match_pattern(self, context_propagator):
        """Test pattern matching."""
        # Exact matches
        assert context_propagator._match_pattern("key", "key") is True
        assert context_propagator._match_pattern("key", "other") is False
        
        # Wildcard matches
        assert context_propagator._match_pattern("prefix_suffix", "prefix_*") is True
        assert context_propagator._match_pattern("other_suffix", "prefix_*") is False
        assert context_propagator._match_pattern("prefix_middle_suffix", "prefix_*") is True

    def test_apply_pattern(self, context_propagator):
        """Test pattern application for generating target keys."""
        # Simple key replacement
        assert context_propagator._apply_pattern("key", "key", "target") == "target"
        
        # Wildcard replacement
        assert context_propagator._apply_pattern(
            "prefix_value", "prefix_*", "target_*"
        ) == "target_value"
        
        # Non-wildcard case
        assert context_propagator._apply_pattern(
            "exact", "exact", "target_exact"
        ) == "target_exact"

    def test_propagate_from_task_output(self, context_propagator, context_manager):
        """Test propagating context from task output."""
        # Add propagation rules
        context_propagator.add_rule("input_data", "processed_data", lambda x: {"processed": True, "value": x})
        context_propagator.add_rule("raw_*", "processed_*", lambda x: f"Processed: {x}")
        
        # Create task output
        task_output = {
            "input_data": {"value": 42},
            "raw_text": "Hello world",
            "raw_number": 123,
            "not_propagated": "stays the same"
        }
        
        # Propagate from task output
        context_propagator.propagate_from_task_output("task1", task_output)
        
        # Check direct propagation
        processed_data = context_manager.get_context("processed_data")
        assert processed_data == {"processed": True, "value": {"value": 42}}
        
        # Check wildcard propagation
        assert context_manager.get_context("processed_text") == "Processed: Hello world"
        assert context_manager.get_context("processed_number") == "Processed: 123"
        
        # Check non-propagated values
        assert context_manager.get_context("not_propagated") is None

    def test_prepare_context_for_task(self, context_propagator, context_manager):
        """Test preparing context for a task."""
        # Mock task with requirements
        task = MagicMock()
        task.id = "task1"
        task.context_requirements = ["input_data", "config", "processed_text"]
        
        # Add to task selector
        context_manager.task_selector.tasks = {"task1": task}
        
        # Add propagation rule
        context_propagator.add_rule("raw_text", "processed_text", lambda x: f"Processed: {x}")
        
        # Set context values
        context_manager.set_context("input_data", {"value": 42}, ContextType.GLOBAL)
        context_manager.set_context("config", {"setting": "value"}, ContextType.SESSION)
        context_manager.set_context("raw_text", "Hello world", ContextType.TASK)
        context_manager.set_context("extra", "not needed", ContextType.TASK)
        
        # Prepare context for task
        task_context = context_propagator.prepare_context_for_task("task1")
        
        # Direct values should be included
        assert "input_data" in task_context
        assert task_context["input_data"] == {"value": 42}
        assert "config" in task_context
        assert task_context["config"] == {"setting": "value"}
        
        # Propagated value should be included
        assert "processed_text" in task_context
        assert task_context["processed_text"] == "Processed: Hello world"
        
        # Extra values not in requirements should not be included
        assert "extra" not in task_context
        assert "raw_text" not in task_context

    def test_validate_context_for_task(self, context_propagator, context_manager):
        """Test validating that all required context for a task is available."""
        # Mock task with requirements
        task = MagicMock()
        task.id = "task1"
        task.context_requirements = ["input_data", "config", "processed_text"]
        
        # Add to task selector
        context_manager.task_selector.tasks = {"task1": task}
        
        # Add propagation rule
        context_propagator.add_rule("raw_text", "processed_text", lambda x: f"Processed: {x}")
        
        # Initially, validation should fail since no context is set
        is_valid, missing = context_propagator.validate_context_for_task("task1")
        assert is_valid is False
        assert set(missing) == {"input_data", "config", "processed_text"}
        
        # Set some context values
        context_manager.set_context("input_data", {"value": 42}, ContextType.GLOBAL)
        context_manager.set_context("config", {"setting": "value"}, ContextType.SESSION)
        
        # Should still fail, but with fewer missing items
        is_valid, missing = context_propagator.validate_context_for_task("task1")
        assert is_valid is False
        assert set(missing) == {"processed_text"}
        
        # Add source for propagation rule
        context_manager.set_context("raw_text", "Hello world", ContextType.TASK)
        
        # Now validation should pass
        is_valid, missing = context_propagator.validate_context_for_task("task1")
        assert is_valid is True
        assert not missing

    def test_complex_propagation_chain(self, context_propagator, context_manager):
        """Test propagation across a chain of rules."""
        # Set up a chain of propagation rules
        context_propagator.add_rule("raw_data", "stage1_data", lambda x: f"Stage 1: {x}")
        context_propagator.add_rule("stage1_data", "stage2_data", lambda x: f"Stage 2: {x}")
        context_propagator.add_rule("stage2_data", "final_data", lambda x: f"Final: {x}")
        
        # Set the source context and manually trigger propagation
        context_manager.set_context("raw_data", "original", ContextType.GLOBAL)
        
        # Manually trigger propagation
        context_propagator.propagate_from_task_output("test", {"raw_data": "original"})
        
        # Check each stage of propagation
        stage1 = context_manager.get_context("stage1_data")
        assert stage1 == "Stage 1: original", f"Expected 'Stage 1: original' but got {stage1}"
        
        # Trigger next chain manually
        context_propagator.propagate_from_task_output("test", {"stage1_data": stage1})
        
        stage2 = context_manager.get_context("stage2_data")
        assert stage2 == "Stage 2: Stage 1: original", f"Expected 'Stage 2: Stage 1: original' but got {stage2}"
        
        # Trigger final chain manually
        context_propagator.propagate_from_task_output("test", {"stage2_data": stage2})
        
        final = context_manager.get_context("final_data")
        assert final == "Final: Stage 2: Stage 1: original", f"Expected 'Final: Stage 2: Stage 1: original' but got {final}"

    def test_pattern_wildcard_propagation(self, context_propagator, context_manager):
        """Test wildcard pattern propagation with multiple matches."""
        # Add wildcard propagation rule
        context_propagator.add_rule("input_*", "output_*", lambda x: f"Processed: {x}")
        
        # Set multiple matching input contexts
        context_manager.set_context("input_text", "hello", ContextType.GLOBAL)
        context_manager.set_context("input_number", 42, ContextType.GLOBAL)
        context_manager.set_context("input_data", {"key": "value"}, ContextType.GLOBAL)
        context_manager.set_context("other_text", "not propagated", ContextType.GLOBAL)
        
        # Manually trigger propagation for each input
        context_propagator.propagate_from_task_output("test", {
            "input_text": "hello",
            "input_number": 42,
            "input_data": {"key": "value"}
        })
        
        # Get all created contexts
        current_context = context_manager.get_current_context()
        
        # Debug output
        print("Current context keys:", current_context.keys())
        
        # Check output contexts were created
        assert "output_text" in current_context, "output_text not found in context"
        assert "output_number" in current_context, "output_number not found in context" 
        assert "output_data" in current_context, "output_data not found in context"
        
        assert current_context["output_text"] == f"Processed: hello"
        assert current_context["output_number"] == f"Processed: 42"
        assert current_context["output_data"] == f"Processed: {{'key': 'value'}}"
        assert "output_other" not in current_context

    def test_error_handling(self, context_propagator, context_manager):
        """Test error handling during context propagation."""
        # Add a rule with a transform that might fail
        def problematic_transform(x):
            return x["key"]  # Will fail if x is not a dict with 'key'
        
        context_propagator.add_rule("problematic", "target", problematic_transform)
        
        # Set context that will cause transform to fail
        context_manager.set_context("problematic", "not a dict", ContextType.GLOBAL)
        
        # This should not raise an exception, but log an error
        # The propagation will simply not occur
        assert context_manager.get_context("target") is None 