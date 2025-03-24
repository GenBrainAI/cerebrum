from typing import Dict, List, Any, Optional
import logging

from .context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)

class TaskConfigurator:
    """
    Responsible for configuring tasks with appropriate context and parameters.
    Serves as a bridge between tasks and their execution environment.
    """
    
    def __init__(self, context_manager: ContextManager):
        """
        Initialize the task configurator with a context manager.
        
        Args:
            context_manager: The context manager to use for task configuration.
        """
        self.context_manager = context_manager
        logger.debug("TaskConfigurator initialized")
    
    def configure_task_context(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure a task with the appropriate context from the context manager.
        
        Args:
            task_id: The ID of the task to configure.
            context: The initial context to configure.
            
        Returns:
            The configured context with any additional values from the context manager.
        """
        # Get the current context from the context manager
        context_values = self.context_manager.get_context()
        
        # Merge with the provided context, giving priority to the provided context
        merged_context = {**context_values, **context}
        
        logger.debug(f"Configured context for task {task_id}")
        return merged_context
    
    def apply_task_configuration(self, task_id: str, configuration: Dict[str, Any]) -> None:
        """
        Apply a configuration to a task.
        
        Args:
            task_id: The ID of the task to configure.
            configuration: The configuration to apply.
        """
        # Update the context manager with configuration values
        for key, value in configuration.items():
            self.context_manager.set_context_value(key, value, ContextType.TASK_CONFIGURATION)
        
        logger.debug(f"Applied configuration for task {task_id}")
    
    def get_task_configuration(self, task_id: str) -> Dict[str, Any]:
        """
        Get the configuration for a task.
        
        Args:
            task_id: The ID of the task to get the configuration for.
            
        Returns:
            The configuration for the task.
        """
        # Get configuration values from the context manager
        context_values = self.context_manager.get_context()
        
        # Filter for configuration values
        config_values = {
            key: value
            for key, value in context_values.items()
            if self.context_manager.get_context_type(key) == ContextType.TASK_CONFIGURATION
        }
        
        logger.debug(f"Retrieved configuration for task {task_id}")
        return config_values 