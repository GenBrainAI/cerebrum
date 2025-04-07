"""
Plugin manager for agent frameworks.
Handles plugin registration, initialization, and lifecycle management.
"""

import logging
import importlib.util
from typing import Dict, Any, Optional, List, Type
from pathlib import Path
import sys

from .base_plugin import AgentFrameworkPlugin
from .agent_framework_config import AgentFrameworkConfig

logger = logging.getLogger(__name__)

class PluginManager:
    """Manager for agent framework plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, AgentFrameworkPlugin] = {}
        self._plugin_configs: Dict[str, AgentFrameworkConfig] = {}
    
    async def load_plugin(self, plugin_path: str, config: AgentFrameworkConfig) -> bool:
        """Load a plugin from the given path."""
        try:
            # Import plugin module
            spec = importlib.util.spec_from_file_location(config.name, plugin_path)
            if not spec or not spec.loader:
                logger.error(f"Could not load spec for plugin {config.name}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, AgentFrameworkPlugin) and 
                    attr != AgentFrameworkPlugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                raise ValueError(f"No plugin class found in {plugin_path}")
            
            # Create and initialize plugin
            plugin = plugin_class(config)
            success = await plugin.initialize()
            if not success:
                raise RuntimeError(f"Failed to initialize plugin {config.name}")
            
            # Store plugin
            self._plugins[config.name] = plugin
            self._plugin_configs[config.name] = config
            
            logger.info(f"Successfully loaded plugin {config.name} v{plugin.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {config.name}: {str(e)}")
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload and cleanup a plugin."""
        try:
            if plugin_name not in self._plugins:
                logger.warning(f"Plugin {plugin_name} not found")
                return False
            
            plugin = self._plugins[plugin_name]
            success = await plugin.shutdown()
            if success:
                del self._plugins[plugin_name]
                del self._plugin_configs[plugin_name]
                logger.info(f"Successfully unloaded plugin {plugin_name}")
                return True
            else:
                logger.error(f"Failed to shutdown plugin {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {str(e)}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[AgentFrameworkPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(plugin_name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins and their capabilities."""
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.config.description,
                "capabilities": plugin.get_capabilities(),
                "is_initialized": plugin.is_initialized
            }
            for plugin in self._plugins.values()
        ]
    
    async def execute_task(
        self, 
        plugin_name: str, 
        task: Any, 
        curried_proxy: Any = None, 
        allowed_tools: List[str] = None, 
        inputs: Dict[str, Any] = None,
        persistence_model: Any = None
    ) -> Any:
        """Execute a task using the specified plugin.
        
        Args:
            plugin_name: The name of the plugin to execute the task with
            task: The task to execute
            curried_proxy: The curried proxy for tool access
            allowed_tools: The list of allowed tools
            inputs: The inputs for the task
            persistence_model: The persistence model to use
            
        Returns:
            The result of the task execution
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        if not plugin.is_initialized:
            raise RuntimeError(f"Plugin {plugin_name} is not initialized")
        
        # Pass all the parameters to the plugin's run_task method
        if plugin_name == "crewai":
            return await plugin.run_task(
                task=task,
                curried_proxy=curried_proxy,
                allowed_tools=allowed_tools,
                inputs=inputs,
                persistence_model=persistence_model
            )
        else:
            # Default case for other plugins
            return await plugin.execute_task(task)
    
    async def create_agent(self, plugin_name: str, config: Dict[str, Any]) -> Any:
        """Create an agent using the specified plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        if not plugin.is_initialized:
            raise RuntimeError(f"Plugin {plugin_name} is not initialized")
        
        return await plugin.create_agent(config)
    
    async def shutdown_all(self) -> bool:
        """Shutdown all plugins."""
        success = True
        for plugin_name in list(self._plugins.keys()):
            if not await self.unload_plugin(plugin_name):
                success = False
        return success 