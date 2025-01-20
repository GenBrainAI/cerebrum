"""
Plugin discovery and management system.
"""

import logging
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Set
import shutil

from .base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

logger = logging.getLogger(__name__)

class PluginManifest:
    """Plugin manifest schema."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data["name"]
        self.version = data["version"]
        self.description = data["description"]
        self.entry_point = data["entry_point"]
        self.framework = data["framework"]
        self.capabilities = data["capabilities"]
        self.supported_roles = data["supported_roles"]
        self.config_schema = data["config_schema"]
        self.dependencies = data["dependencies"]

class PluginRegistry:
    """Registry for managing agent framework plugins."""
    
    def __init__(self, installed_plugins_dir: str, example_plugins_dir: str):
        """Initialize the plugin registry.
        
        Args:
            installed_plugins_dir: Directory containing installed plugins
            example_plugins_dir: Directory containing example plugins
        """
        self._installed_dir = Path(installed_plugins_dir)
        self._examples_dir = Path(example_plugins_dir)
        self._plugins: Dict[str, AgentFrameworkPlugin] = {}
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._plugin_classes: Dict[str, Type[AgentFrameworkPlugin]] = {}
        self._src_examples: Set[str] = set()

    async def discover_plugins(self) -> List[str]:
        """Discover plugins from both installed and example directories."""
        # Clear existing plugins
        self._plugins.clear()
        self._manifests.clear()
        self._plugin_classes.clear()
        self._src_examples.clear()

        # Load installed plugins
        if self._installed_dir.exists():
            for plugin_dir in self._installed_dir.iterdir():
                if plugin_dir.is_dir():
                    manifest_path = plugin_dir / "manifest.json"
                    if manifest_path.exists():
                        await self._load_plugin(plugin_dir.name, manifest_path)

        # Load example plugins
        if self._examples_dir.exists():
            for plugin_dir in self._examples_dir.iterdir():
                if plugin_dir.is_dir():
                    manifest_path = plugin_dir / "manifest.json"
                    if manifest_path.exists():
                        await self._load_plugin(plugin_dir.name, manifest_path)
                        self._src_examples.add(plugin_dir.name)

        return list(self._plugins.keys())

    async def _load_plugin(self, plugin_name: str, manifest_path: Path):
        """Load a plugin from a given manifest path."""
        try:
            # Load manifest
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            plugin_dir = manifest_path.parent
            plugin_path = plugin_dir / "plugin.py"

            if not plugin_path.exists():
                logger.error(f"Plugin module not found: {plugin_path}")
                return

            # Load plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}", str(plugin_path)
            )
            if not spec or not spec.loader:
                logger.error(f"Failed to load plugin spec: {plugin_path}")
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get plugin class from entry point
            class_name = manifest["entry_point"].split(".")[-1]
            plugin_class = getattr(module, class_name)

            # Create plugin instance
            plugin = plugin_class()

            # Store plugin info
            self._manifests[plugin_name] = manifest
            self._plugin_classes[plugin_name] = plugin_class
            self._plugins[plugin_name] = plugin

            logger.info(f"Loaded plugin: {plugin_name}")

        except Exception as e:
            logger.error(f"Failed to load plugin from {manifest_path}: {str(e)}")

    def is_example_plugin(self, plugin_name: str) -> bool:
        """Check if a plugin is an example plugin."""
        return plugin_name in self._src_examples

    async def remove_plugin(self, plugin_name: str) -> bool:
        """Remove a plugin from the registry and delete its directory."""
        if plugin_name not in self._plugins:
            return False

        # Shutdown the plugin if it's initialized
        plugin = self._plugins[plugin_name]
        if plugin.is_initialized:
            await plugin.shutdown()

        # Remove from registry
        del self._plugins[plugin_name]
        del self._manifests[plugin_name]
        del self._plugin_classes[plugin_name]
        if plugin_name in self._src_examples:
            self._src_examples.remove(plugin_name)

        # Delete the plugin directory
        plugin_dir = self._installed_dir / plugin_name
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        return True

    async def setup_examples(self):
        """Create symlinks for example plugins in installed directory."""
        for example in self._examples_dir.iterdir():
            if example.is_dir():
                target = self._installed_dir / example.name
                if not target.exists():
                    target.symlink_to(example, target_is_directory=True)
                    logger.info(f"Created symlink for example plugin: {example.name}")

    async def cleanup_examples(self):
        """Remove symlinks for example plugins from installed directory."""
        for symlink in self._installed_dir.iterdir():
            if symlink.is_symlink():
                symlink.unlink()
                logger.info(f"Removed symlink for example plugin: {symlink.name}")

    def get_plugins_by_capability(self, capability: str) -> List[str]:
        """Get a list of plugin names that have the specified capability."""
        return [
            name for name, manifest in self._manifests.items()
            if capability in manifest.get("capabilities", [])
        ]

    def get_plugins_by_framework(self, framework: str) -> List[str]:
        """Get a list of plugin names that use the specified framework."""
        return [
            name for name, manifest in self._manifests.items()
            if manifest.get("framework") == framework
        ]

    def list_example_plugins(self) -> List[str]:
        """List all example plugins."""
        return list(self._src_examples)

    def list_installed_plugins(self) -> List[str]:
        """List all installed plugins that are not examples."""
        return [name for name in self._plugins.keys() if name not in self._src_examples]

    def list_plugins(self) -> List[str]:
        """List all plugins."""
        return list(self._plugins.keys())

    def get_plugin(self, plugin_name: str) -> Optional[AgentFrameworkPlugin]:
        """Get a plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance if found, None otherwise
        """
        return self._plugins.get(plugin_name) 