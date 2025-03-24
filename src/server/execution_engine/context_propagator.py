from typing import Dict, List, Any, Optional, Tuple, Callable
import logging
import re

from .context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)

class ContextPropagator:
    """
    Class to manage context propagation rules between tasks.
    Rules define how output from one task is transformed and stored in the context for use by other tasks.
    """

    def __init__(self, context_manager: ContextManager):
        """Initialize the propagator with a context manager."""
        self._context_manager = context_manager
        self._rules = []  # List of (source_pattern, target_pattern, transform_func)
        self._logger = logging.getLogger(__name__)

    def add_rule(self, source_pattern: str, target_pattern: str, transform_func: Callable = None):
        """
        Add a new propagation rule.
        
        Args:
            source_pattern: Pattern to match source keys in the context
            target_pattern: Pattern to generate target keys
            transform_func: Function to transform the source value to target value
        """
        if transform_func is None:
            transform_func = lambda x: x  # Identity function
            
        self._rules.append((source_pattern, target_pattern, transform_func))
        self._logger.info(f"Added propagation rule from {source_pattern} to {target_pattern}")
        
        # Apply the new rule to any existing matching context items
        # This is crucial for tests like test_context_integration
        self._apply_rule_to_existing_context(source_pattern, target_pattern, transform_func)

    def _apply_rule_to_existing_context(self, source_pattern: str, target_pattern: str, transform_func: Callable):
        """Apply a rule to existing context values that match the source pattern."""
        # Get the current context
        current_context = self._context_manager.get_current_context()
        
        # Find matching keys
        for key, value in current_context.items():
            if self._key_matches_pattern(key, source_pattern):
                # Extract the wildcard part if applicable
                wildcard_part = self._extract_wildcard(key, source_pattern)
                
                # Generate the target key
                target_key = target_pattern
                if '*' in source_pattern and '*' in target_pattern:
                    target_key = target_pattern.replace('*', wildcard_part)
                
                try:
                    # Transform and store the value
                    transformed_value = transform_func(value)
                    self._context_manager.set_context(target_key, transformed_value, ContextType.GLOBAL)
                    self._logger.debug(f"Applied rule to existing context: {key} -> {target_key}")
                    
                    # Trigger subsequent propagations for this new context
                    self._propagate_subsequent_rules({target_key: transformed_value})
                except Exception as e:
                    self._logger.error(f"Error applying transform function for {key}: {e}")

    def _propagate_subsequent_rules(self, context_updates: Dict[str, Any]):
        """Propagate changes further through any matching rules."""
        if not context_updates:
            return
            
        changes_made = False
        new_updates = {}
        
        # Check each rule against each updated context key
        for rule_source, rule_target, rule_transform in self._rules:
            for context_key, context_value in context_updates.items():
                if self._key_matches_pattern(context_key, rule_source):
                    # Extract wildcard part if applicable
                    wildcard_part = self._extract_wildcard(context_key, rule_source)
                    
                    # Generate target key
                    target_key = rule_target
                    if '*' in rule_source and '*' in rule_target:
                        target_key = rule_target.replace('*', wildcard_part)
                    
                    try:
                        # Transform and store
                        transformed_value = rule_transform(context_value)
                        self._context_manager.set_context(target_key, transformed_value, ContextType.GLOBAL)
                        new_updates[target_key] = transformed_value
                        changes_made = True
                        self._logger.debug(f"Propagated: {context_key} -> {target_key}")
                    except Exception as e:
                        self._logger.error(f"Error in propagation chain for {context_key}: {e}")
        
        # Continue propagation if we made changes
        if changes_made:
            self._propagate_subsequent_rules(new_updates)

    def propagate_from_task_output(self, task_id: str, output: Dict[str, Any]) -> None:
        """Propagate values from task output to context according to rules."""
        logger.debug(f"Propagating task output for task {task_id}")
        
        # First, store the raw output in the context
        self._context_manager.set_context("task_output", output, ContextType.TASK)
        
        # Apply propagation rules to each output key
        for key, value in output.items():
            # Skip None values
            if value is None:
                continue
                
            # Check all rules for matches
            for source_pattern, target_pattern, transform_func in self._rules:
                if self._key_matches_pattern(key, source_pattern):
                    try:
                        # For wildcard patterns, generate the specific target key
                        if '*' in source_pattern and '*' in target_pattern:
                            wildcard_part = self._extract_wildcard(key, source_pattern)
                            actual_target_key = target_pattern.replace('*', wildcard_part)
                        else:
                            actual_target_key = target_pattern
                            
                        # Transform and store the value
                        transformed_value = transform_func(value)
                        logger.debug(f"Applying rule: {source_pattern} -> {actual_target_key}")
                        self._context_manager.set_context(actual_target_key, transformed_value, ContextType.TASK)
                    except Exception as e:
                        logger.error(f"Error applying transformation from {key} to {target_pattern}: {str(e)}")
        
        # Process any nested dictionaries (for backward compatibility)
        for key, value in output.items():
            if isinstance(value, dict) and key != "task_output":  # Avoid double-processing task_output
                for nested_key, nested_value in value.items():
                    if nested_value is not None:
                        full_key = f"{key}.{nested_key}"
                        # Apply rules to nested keys
                        for source_pattern, target_pattern, transform_func in self._rules:
                            if self._key_matches_pattern(full_key, source_pattern):
                                try:
                                    if '*' in source_pattern and '*' in target_pattern:
                                        wildcard_part = self._extract_wildcard(full_key, source_pattern)
                                        actual_target_key = target_pattern.replace('*', wildcard_part)
                                    else:
                                        actual_target_key = target_pattern
                                        
                                    transformed_value = transform_func(nested_value)
                                    logger.debug(f"Applying rule to nested key: {full_key} -> {actual_target_key}")
                                    self._context_manager.set_context(actual_target_key, transformed_value, ContextType.TASK)
                                except Exception as e:
                                    logger.error(f"Error with nested key {full_key}: {str(e)}")
                                    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Check if a key matches a pattern, handling wildcards."""
        return self._key_matches_pattern(key, pattern)

    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """
        Check if a key matches a pattern, supporting wildcards.
        
        Args:
            key: The key to check
            pattern: The pattern to match against, supports * wildcards
            
        Returns:
            bool: True if the key matches the pattern
        """
        # Direct string match
        if pattern == key:
            return True
        
        # Convert glob-style pattern to regex
        # Escape any special regex chars except *
        regex_pattern = re.escape(pattern).replace('\\*', '.*')
        # Anchor to beginning and end
        regex_pattern = f'^{regex_pattern}$'
        
        # Compile the regex
        regex = re.compile(regex_pattern)
        
        # Check for match
        return bool(regex.match(key))
        
    def _extract_wildcard(self, key: str, pattern: str) -> str:
        """Extract the part of the key that matches the wildcard in the pattern."""
        if '*' not in pattern:
            return ""
            
        # Split pattern at the wildcard
        prefix, suffix = pattern.split('*', 1)
        
        # Extract the matching part
        if not suffix:  # Pattern ends with wildcard
            return key[len(prefix):]
        elif not prefix:  # Pattern starts with wildcard
            return key[:-len(suffix)]
        else:  # Wildcard in the middle
            return key[len(prefix):-len(suffix) if suffix else None]

    def _apply_pattern(self, key: str, source_pattern: str, target_pattern: str) -> str:
        """Apply a pattern transformation to generate a target key."""
        if '*' in source_pattern and '*' in target_pattern:
            wildcard_part = self._extract_wildcard(key, source_pattern)
            return target_pattern.replace('*', wildcard_part)
        return target_pattern
    
    def prepare_context_for_task(self, task_id: str) -> Dict[str, Any]:
        """Prepare the context for a task based on its requirements."""
        if not self._context_manager.task_selector or task_id not in self._context_manager.task_selector.tasks:
            self._logger.warning(f"Task {task_id} not found in task selector")
            return {}
        
        task = self._context_manager.task_selector.tasks[task_id]
        if not task.context_requirements:
            self._logger.debug(f"Task {task_id} has no context requirements")
            return {}
        
        current_context = self._context_manager.get_current_context()
        task_context = {}
        
        for req in task.context_requirements:
            if req in current_context:
                # Direct match
                task_context[req] = current_context[req]
                continue
            
            # Handle pattern matches
            for key, value in current_context.items():
                for source_pattern, target_pattern, transform_func in self._rules:
                    if self._key_matches_pattern(key, source_pattern):
                        target_key = self._apply_pattern(key, source_pattern, target_pattern)
                        if target_key == req:
                            transformed_value = transform_func(current_context[key])
                            task_context[req] = transformed_value
                            break
        
        self._logger.debug(f"Prepared context for task {task_id}: {len(task_context)} keys")
        return task_context
    
    def validate_context_for_task(self, task_id: str) -> Tuple[bool, List[str]]:
        """Validate that all required context for a task is available."""
        if not self._context_manager.task_selector or task_id not in self._context_manager.task_selector.tasks:
            self._logger.error(f"Task {task_id} not found in task selector")
            return False, ["Task not found"]
        
        task = self._context_manager.task_selector.tasks[task_id]
        if not task.context_requirements:
            self._logger.debug(f"Task {task_id} has no context requirements")
            return True, []  # No requirements means validation passes
        
        current_context = self._context_manager.get_current_context()
        missing_requirements = []
        
        for req in task.context_requirements:
            if req not in current_context:
                # Check if it could be satisfied by a propagation rule
                satisfied_by_rule = False
                for key in current_context:
                    for source_pattern, target_pattern, _ in self._rules:
                        if self._key_matches_pattern(key, source_pattern):
                            target_key = self._apply_pattern(key, source_pattern, target_pattern)
                            if target_key == req:
                                satisfied_by_rule = True
                                break
                    if satisfied_by_rule:
                        break
                
                if not satisfied_by_rule:
                    missing_requirements.append(req)
        
        if missing_requirements:
            self._logger.warning(f"Task {task_id} is missing required context: {missing_requirements}")
            return False, missing_requirements
        
        self._logger.debug(f"All required context available for task {task_id}")
        return True, [] 

    @property
    def propagation_rules(self):
        """Return a dictionary representation of the rules for backward compatibility."""
        rules_dict = {}
        for source_pattern, target_pattern, transform_func in self._rules:
            rules_dict[source_pattern] = (target_pattern, transform_func)
        return rules_dict 