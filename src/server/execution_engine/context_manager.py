from typing import Dict, List, Set, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

class ContextType(Enum):
    GLOBAL = "global"
    SESSION = "session"
    TASK = "task"
    TEMPORARY = "temporary"

@dataclass
class ContextEntry:
    key: str
    value: Any
    type: ContextType
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if the context entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

class ContextManager:
    """
    Manages execution context across tasks, ensuring relevant information
    is propagated, validated, and optimized for efficient task execution.
    """
    
    def __init__(self, task_selector=None):
        self.contexts = {
            ContextType.GLOBAL: {},  # Persistent across all sessions
            ContextType.SESSION: {},  # Persistent for current session
            ContextType.TASK: {},  # Current task context
            ContextType.TEMPORARY: {}  # Short-lived context
        }
        self.context_history = []  # History of context changes
        self.validation_rules = {}  # Key -> validation function
        self.propagation_rules = {}  # Source key -> list of target keys
        self.optimization_enabled = True
        self.task_selector = task_selector
        logger.info("Context manager initialized")
        
    @property
    def global_context(self) -> Dict[str, Any]:
        """Get the global context dictionary."""
        return self.contexts[ContextType.GLOBAL]

    @property
    def session_context(self) -> Dict[str, Any]:
        """Get the session context dictionary."""
        return self.contexts[ContextType.SESSION]

    @property
    def task_context(self) -> Dict[str, Any]:
        """Get the task context dictionary."""
        return self.contexts[ContextType.TASK]

    @property
    def temporary_context(self) -> Dict[str, Any]:
        """Get the temporary context dictionary."""
        return self.contexts[ContextType.TEMPORARY]
        
    def set_context(self, key: str, value: Any, context_type: ContextType = ContextType.TASK, 
                   expires_at: datetime = None, metadata: Dict[str, Any] = None, skip_validation: bool = False) -> None:
        """Set a context value."""
        now = datetime.now()
        old_value = None
        
        # Validate the context value if rules exist
        if key in self.validation_rules and not skip_validation:
            if not self.validation_rules[key](value):
                error_msg = f"Invalid value for context key: {key}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # Create or update context entry
        if key in self.contexts[context_type]:
            entry = self.contexts[context_type][key]
            old_value = entry.value
            entry.value = value
            entry.updated_at = now
            entry.expires_at = expires_at
            if metadata:
                entry.metadata = {**(entry.metadata or {}), **metadata}
            logger.debug(f"Updated context: {key} in {context_type.value} context")
        else:
            entry = ContextEntry(
                key=key,
                value=value,
                type=context_type,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                metadata=metadata
            )
            self.contexts[context_type][key] = entry
            logger.debug(f"Created new context: {key} in {context_type.value} context")
        
        # Record history
        self.context_history.append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "type": context_type.value,
            "timestamp": now.isoformat()
        })
        
        # Apply propagation rules
        if key in self.propagation_rules:
            for target_key, transform_func in self.propagation_rules[key]:
                transformed_value = transform_func(value)
                target_type = ContextType.TASK  # Default to task context for propagated values
                logger.debug(f"Propagating {key} to {target_key} in {target_type.value} context")
                self.set_context(target_key, transformed_value, target_type)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value, checking all context types in order of specificity."""
        # Order of precedence: Task, Session, Global, Temporary
        for context_type in [ContextType.TASK, ContextType.SESSION, ContextType.GLOBAL, ContextType.TEMPORARY]:
            if key in self.contexts[context_type]:
                entry = self.contexts[context_type][key]
                if not entry.is_expired():
                    return entry.value
        
        return default
    
    def has_context(self, key: str) -> bool:
        """
        Check if a context key exists in any context type.
        
        Args:
            key: The key to check.
            
        Returns:
            bool: True if the key exists in any non-expired context, False otherwise.
        """
        # Check all context types in order of precedence
        for context_type in [ContextType.TASK, ContextType.SESSION, ContextType.GLOBAL, ContextType.TEMPORARY]:
            if key in self.contexts[context_type]:
                entry = self.contexts[context_type][key]
                if not entry.is_expired():
                    return True
        
        return False
    
    def get_typed_context(self, key: str, context_type: ContextType, default: Any = None) -> Any:
        """Get a context value from a specific context type."""
        if key in self.contexts[context_type]:
            entry = self.contexts[context_type][key]
            if not entry.is_expired():
                return entry.value
        
        return default
    
    def delete_context(self, key: str, context_type: Optional[ContextType] = None) -> bool:
        """Delete a context entry."""
        if context_type is not None:
            if key in self.contexts[context_type]:
                del self.contexts[context_type][key]
                logger.debug(f"Deleted context: {key} from {context_type.value} context")
                return True
            return False
        
        # Delete from all context types if type not specified
        deleted = False
        for ctx_type in self.contexts:
            if key in self.contexts[ctx_type]:
                del self.contexts[ctx_type][key]
                deleted = True
                logger.debug(f"Deleted context: {key} from {ctx_type.value} context")
        
        return deleted
    
    def clear_context(self, context_type: ContextType) -> None:
        """Clear all entries for a specific context type."""
        self.contexts[context_type] = {}
        logger.info(f"Cleared all entries in {context_type.value} context")
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get all current context values across all types."""
        result = {}
        
        # Start with global context
        for key, entry in self.contexts[ContextType.GLOBAL].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Override with session context
        for key, entry in self.contexts[ContextType.SESSION].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Override with task context
        for key, entry in self.contexts[ContextType.TASK].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        # Add temporary context
        for key, entry in self.contexts[ContextType.TEMPORARY].items():
            if not entry.is_expired():
                result[key] = entry.value
        
        return result
    
    def get_all_contexts(self) -> Dict[str, Any]:
        """Get all context values across all types for validation purposes.
        This is similar to get_current_context but used specifically by the context validator."""
        return self.get_current_context()
    
    def add_validation_rule(self, key: str, validation_func) -> None:
        """Add a validation rule for a context key."""
        self.validation_rules[key] = validation_func
        logger.debug(f"Added validation rule for context key: {key}")
    
    def add_propagation_rule(self, source_key: str, target_key: str, transform_func=None) -> None:
        """Add a propagation rule to automatically update related context values."""
        if transform_func is None:
            transform_func = lambda x: x  # Identity function by default
        
        if source_key not in self.propagation_rules:
            self.propagation_rules[source_key] = []
        
        self.propagation_rules[source_key].append((target_key, transform_func))
        logger.debug(f"Added propagation rule: {source_key} -> {target_key}")
    
    def optimize_context(self) -> None:
        """Optimize the context by removing expired entries and consolidating frequently used values."""
        if not self.optimization_enabled:
            return
        
        # Remove expired entries
        for context_type in self.contexts:
            expired_keys = []
            for key, entry in self.contexts[context_type].items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.contexts[context_type][key]
                logger.debug(f"Removed expired context: {key} from {context_type.value} context")
        
        # Compact history
        if len(self.context_history) > 1000:  # Arbitrary threshold
            self.context_history = self.context_history[-500:]  # Keep only recent history
            logger.info(f"Compacted context history to last 500 entries (from {len(self.context_history)})")
    
    def prepare_task_context(self, task_id: str) -> Dict[str, Any]:
        """Prepare context for a specific task."""
        if not self.task_selector or task_id not in self.task_selector.tasks:
            logger.warning(f"Task {task_id} not found or no task selector available")
            return {}
        
        task = self.task_selector.tasks[task_id]
        
        # Get the current context
        current_context = self.get_current_context()
        
        # Filter context based on task requirements
        task_context = {}
        if task.context_requirements:
            for req in task.context_requirements:
                if req in current_context:
                    task_context[req] = current_context[req]
        
        logger.info(f"Prepared context for task {task_id}: {len(task_context)} context keys")
        return task_context
    
    def propagate_context_from_task(self, task_id: str, task_output: Dict[str, Any]) -> None:
        """Propagate context from task output to the context store."""
        if not task_output:
            return
        
        logger.info(f"Propagating context from task {task_id}: {len(task_output)} context keys")
        
        # Update task context with task output
        for key, value in task_output.items():
            self.set_context(key, value, ContextType.TASK)
    
    def serialize_context(self, include_types: List[ContextType] = None) -> str:
        """Serialize the context to a JSON string."""
        if include_types is None:
            include_types = [ContextType.GLOBAL, ContextType.SESSION, ContextType.TASK]
        
        serializable = {}
        for context_type in include_types:
            type_dict = {}
            for key, entry in self.contexts[context_type].items():
                if not entry.is_expired():
                    type_dict[key] = {
                        "value": entry.value,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                        "metadata": entry.metadata
                    }
            serializable[context_type.value] = type_dict
        
        return json.dumps(serializable)
    
    def deserialize_context(self, serialized: str) -> None:
        """Deserialize context from a JSON string."""
        data = json.loads(serialized)
        
        for type_str, entries in data.items():
            context_type = ContextType(type_str)
            for key, entry_data in entries.items():
                expires_at = None
                if entry_data["expires_at"]:
                    expires_at = datetime.fromisoformat(entry_data["expires_at"])
                
                entry = ContextEntry(
                    key=key,
                    value=entry_data["value"],
                    type=context_type,
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                    expires_at=expires_at,
                    metadata=entry_data["metadata"]
                )
                
                self.contexts[context_type][key] = entry
        
        logger.info(f"Deserialized context: {sum(len(entries) for entries in self.contexts.values())} total entries")
    
    def get_context_hash(self) -> str:
        """Get a hash of the current context state."""
        context_str = self.serialize_context()
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def get_context_diff(self, other_context_manager) -> Dict[str, Any]:
        """Get the difference between this context and another context manager."""
        diff = {
            "added": {},
            "modified": {},
            "removed": {}
        }
        
        current = self.get_current_context()
        other = other_context_manager.get_current_context()
        
        # Find added and modified
        for key, value in current.items():
            if key not in other:
                diff["added"][key] = value
            elif value != other[key]:
                diff["modified"][key] = {
                    "old": other[key],
                    "new": value
                }
        
        # Find removed
        for key in other:
            if key not in current:
                diff["removed"][key] = other[key]
        
        return diff 