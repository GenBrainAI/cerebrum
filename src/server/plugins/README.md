# Agent Framework Plugin System

## Overview
The Agent Framework Plugin System provides a flexible and extensible architecture for integrating various AI agent frameworks (like CrewAI, AutoGen, SmolAgents, etc.) through a common interface. The system supports dynamic discovery, loading, and management of plugins.

## Architecture

### Core Components

1. **Base Plugin Interface** (`AgentFrameworkPlugin`)
```python
class AgentFrameworkPlugin:
    async def initialize(self) -> bool
    async def shutdown(self) -> bool
    async def create_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]
    async def execute_task(self, agent: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]
    def get_capabilities(self) -> List[str]
    @property
    def version(self) -> str
```

2. **Plugin Registry** (`PluginRegistry`)
- Manages plugin discovery, loading, and lifecycle
- Supports both installed plugins and example plugins
- Provides capability-based plugin querying
- Handles plugin removal and cleanup

3. **Plugin Manifest**
```json
{
    "name": "plugin_name",
    "version": "1.0.0",
    "description": "Plugin description",
    "entry_point": "plugin.PluginClass",
    "framework": "framework_name",
    "capabilities": ["capability1", "capability2"],
    "supported_roles": ["role1", "role2"],
    "config_schema": {
        "required_field": {"type": "string", "description": "Field description"}
    },
    "dependencies": {
        "package_name": ">=1.0.0"
    }
}
```

## Plugin Directory Structure
```
plugins/
├── installed/           # User-installed plugins
│   └── plugin_name/
│       ├── manifest.json
│       └── plugin.py
└── examples/           # Example plugins (symlinked to installed)
    └── example_name/
        ├── manifest.json
        └── plugin.py
```

## Creating a New Plugin

1. Create a new directory in `plugins/installed/` or `plugins/examples/`
2. Create a `manifest.json` file with plugin metadata
3. Implement the plugin class in `plugin.py`:
```python
from src.server.plugins.base_plugin import AgentFrameworkPlugin
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

class MyPlugin(AgentFrameworkPlugin):
    def __init__(self):
        super().__init__(AgentFrameworkConfig(
            name="my_plugin",
            version="1.0.0",
            description="My plugin description",
            settings={},
            enabled=True,
            priority=0
        ))
    
    # Implement required methods...
```

## Using the Plugin System

```python
# Initialize the registry
registry = PluginRegistry(
    installed_plugins_dir="plugins/installed",
    example_plugins_dir="plugins/examples"
)

# Discover plugins
await registry.discover_plugins()

# Get plugins by capability
plugins = registry.get_plugins_by_capability("some_capability")

# Get plugin instance
plugin = registry.get_plugin("plugin_name")
if plugin:
    await plugin.initialize()
    result = await plugin.execute_task(agent_config, task_config)
```

## Example Plugins

1. **CrewAI Job Posting Plugin**
   - Framework: CrewAI
   - Capabilities: job_posting_generation, role_analysis
   - Purpose: Generates job postings using multi-agent collaboration

2. **RAG Assistant Plugin**
   - Framework: SmolAgents
   - Capabilities: document_retrieval, context_augmentation
   - Purpose: Provides RAG-enhanced document analysis

3. **Airline Assistant Plugin**
   - Framework: Open-Swarm
   - Capabilities: flight_booking, itinerary_planning
   - Purpose: Assists with airline-related tasks

## Testing
The plugin system includes comprehensive tests covering:
- Plugin discovery and loading
- Example plugin symlink management
- Plugin removal and cleanup
- Capability-based querying
- Framework-specific functionality

Run tests using:
```bash
pytest tests/plugins/test_plugin_discovery.py
```

## Best Practices
1. Always provide a detailed manifest.json
2. Implement proper error handling in plugin methods
3. Clean up resources in the shutdown method
4. Use type hints and docstrings
5. Include tests for your plugin
6. Keep plugin dependencies minimal and explicit 