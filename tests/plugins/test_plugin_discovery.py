"""
Tests for plugin discovery mechanism.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.server.plugins.discovery import PluginRegistry, PluginManifest

@pytest.fixture
def temp_plugin_dirs(tmp_path):
    """Create temporary directories for plugins."""
    installed_dir = tmp_path / "installed"
    examples_dir = tmp_path / "examples"
    installed_dir.mkdir()
    examples_dir.mkdir()
    return installed_dir, examples_dir

@pytest.fixture
def example_manifest():
    """Return a sample manifest for an example plugin."""
    return {
        "name": "example_plugin",
        "version": "1.0.0",
        "description": "An example plugin",
        "entry_point": "plugin.ExamplePlugin",
        "framework": "test",
        "capabilities": ["test_capability"],
        "supported_roles": ["test_role"],
        "config_schema": {},
        "dependencies": {}
    }

@pytest.fixture
def installed_manifest():
    """Return a sample manifest for an installed plugin."""
    return {
        "name": "installed_plugin",
        "version": "1.0.0",
        "description": "An installed plugin",
        "entry_point": "plugin.InstalledPlugin",
        "framework": "test",
        "capabilities": ["installed_capability"],
        "supported_roles": ["installed_role"],
        "config_schema": {},
        "dependencies": {}
    }

def create_plugin_module(plugin_dir: Path, class_name: str):
    """Create a plugin module file."""
    plugin_code = f'''
from src.server.plugins.base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

class {class_name}(AgentFrameworkPlugin):
    def __init__(self):
        super().__init__(AgentFrameworkConfig(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            settings={{}},
            enabled=True,
            priority=0
        ))

    async def initialize(self):
        self._is_initialized = True
        return True

    async def shutdown(self):
        self._is_initialized = False
        return True

    async def create_agent(self, agent_config):
        return {{"role": "test"}}

    async def execute_task(self, agent, task):
        return {{"status": "completed"}}

    def get_capabilities(self):
        return ["test_capability"]

    @property
    def version(self):
        return "1.0.0"
'''
    with open(plugin_dir / "plugin.py", "w") as f:
        f.write(plugin_code)

@pytest.mark.asyncio
async def test_plugin_discovery(temp_plugin_dirs, example_manifest, installed_manifest):
    """Test discovering plugins from both directories."""
    installed_dir, examples_dir = temp_plugin_dirs
    
    # Create example plugin structure
    example_plugin_dir = examples_dir / "example_plugin"
    example_plugin_dir.mkdir(parents=True)
    with open(example_plugin_dir / "manifest.json", "w") as f:
        json.dump(example_manifest, f)
    create_plugin_module(example_plugin_dir, "ExamplePlugin")
    
    # Create installed plugin structure
    installed_plugin_dir = installed_dir / "installed_plugin"
    installed_plugin_dir.mkdir(parents=True)
    with open(installed_plugin_dir / "manifest.json", "w") as f:
        json.dump(installed_manifest, f)
    create_plugin_module(installed_plugin_dir, "InstalledPlugin")
    
    # Initialize registry with test directories
    registry = PluginRegistry(
        installed_plugins_dir=str(installed_dir),
        example_plugins_dir=str(examples_dir)
    )
    
    # Discover plugins
    discovered = await registry.discover_plugins()
    
    # Verify discoveries
    assert "example_plugin" in discovered
    assert "installed_plugin" in discovered
    assert len(discovered) == 2
    
    # Verify plugin sources
    assert registry.is_example_plugin("example_plugin")
    assert not registry.is_example_plugin("installed_plugin")
    
    # Verify listings
    assert "example_plugin" in registry.list_example_plugins()
    assert "installed_plugin" in registry.list_installed_plugins()

@pytest.mark.asyncio
async def test_plugin_removal(temp_plugin_dirs, example_manifest, installed_manifest):
    """Test removing plugins."""
    installed_dir, examples_dir = temp_plugin_dirs
    
    # Create plugin structures
    example_plugin_dir = examples_dir / "example_plugin"
    example_plugin_dir.mkdir(parents=True)
    with open(example_plugin_dir / "manifest.json", "w") as f:
        json.dump(example_manifest, f)
    create_plugin_module(example_plugin_dir, "ExamplePlugin")
    
    installed_plugin_dir = installed_dir / "installed_plugin"
    installed_plugin_dir.mkdir(parents=True)
    with open(installed_plugin_dir / "manifest.json", "w") as f:
        json.dump(installed_manifest, f)
    create_plugin_module(installed_plugin_dir, "InstalledPlugin")
    
    # Initialize registry
    registry = PluginRegistry(
        installed_plugins_dir=str(installed_dir),
        example_plugins_dir=str(examples_dir)
    )
    
    # Discover plugins
    await registry.discover_plugins()
    
    # Remove example plugin
    assert await registry.remove_plugin("example_plugin")
    assert "example_plugin" not in registry.list_plugins()
    
    # Remove installed plugin
    assert await registry.remove_plugin("installed_plugin")
    assert "installed_plugin" not in registry.list_plugins()
    assert not installed_plugin_dir.exists()

@pytest.mark.asyncio
async def test_example_plugin_symlinks(temp_plugin_dirs):
    """Test example plugin symlink creation and removal."""
    installed_dir, examples_dir = temp_plugin_dirs
    
    # Create example plugin
    plugin_dir = examples_dir / "test_plugin"
    plugin_dir.mkdir(parents=True)
    create_plugin_module(plugin_dir, "TestPlugin")
    
    # Initialize registry
    registry = PluginRegistry(
        installed_plugins_dir=str(installed_dir),
        example_plugins_dir=str(examples_dir)
    )
    
    # Create symlinks
    await registry.setup_examples()
    assert (installed_dir / "test_plugin").exists()
    assert (installed_dir / "test_plugin").is_symlink()
    
    # Remove symlinks
    await registry.cleanup_examples()
    assert not (installed_dir / "test_plugin").exists()

@pytest.mark.asyncio
async def test_plugin_capabilities(temp_plugin_dirs, example_manifest):
    """Test plugin capability querying."""
    installed_dir, examples_dir = temp_plugin_dirs

    # Create plugin with capabilities
    plugin_dir = examples_dir / "example_plugin"
    plugin_dir.mkdir(parents=True)
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(example_manifest, f)
    create_plugin_module(plugin_dir, "ExamplePlugin")

    # Initialize registry
    registry = PluginRegistry(
        installed_plugins_dir=str(installed_dir),
        example_plugins_dir=str(examples_dir)
    )

    # Discover plugins
    await registry.discover_plugins()

    # Test capability queries
    plugins = registry.get_plugins_by_capability("test_capability")
    assert "example_plugin" in plugins
    assert len(plugins) == 1

    # Test framework queries
    plugins = registry.get_plugins_by_framework("test")
    assert "example_plugin" in plugins
    assert len(plugins) == 1 