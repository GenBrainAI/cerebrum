# Implementation of Unit 3: Plugin Explorer Component

## 1. Code Implementation

### Create the Plugin Explorer Component 

First, I'll create the component to explore available plugins:

```python
# src/server/views/components/plugin_explorer_component.py
import streamlit as st
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class PluginExplorerComponent:
    """Component for exploring available plugins."""
    
    def __init__(self, plugin_manager):
        """Initialize the component with a plugin manager.
        
        Args:
            plugin_manager: The plugin manager instance
        """
        self.plugin_manager = plugin_manager
    
    def render(self):
        """Render the plugin explorer UI."""
        st.write("## Agent Framework Plugin Explorer")
        
        try:
            # Get all loaded plugins
            plugins = self.plugin_manager.list_plugins()
            
            if not plugins:
                st.warning("No plugins are currently loaded.")
                
                # Add a button to load demo plugins
                if st.button("Load Demo Plugins"):
                    asyncio.run(self._load_demo_plugins())
                    st.rerun()
                return
            
            # Create tabs for each plugin
            plugin_names = [plugin["name"] for plugin in plugins]
            tabs = st.tabs(plugin_names)
            
            for i, plugin in enumerate(plugins):
                with tabs[i]:
                    self._render_plugin_details(plugin)
                    
        except Exception as e:
            logger.error(f"Error rendering plugin explorer: {str(e)}")
            st.error(f"Error loading plugins: {str(e)}")
    
    def _render_plugin_details(self, plugin: Dict[str, Any]):
        """Render details for a single plugin.
        
        Args:
            plugin: Plugin information dictionary
        """
        # Header with version
        st.subheader(f"{plugin['name']} v{plugin['version']}")
        
        # Description
        st.write(plugin["description"])
        
        # Status indicator
        status = "Active" if plugin["is_initialized"] else "Inactive"
        status_color = "green" if plugin["is_initialized"] else "red"
        st.markdown(f"**Status:** <span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)
        
        # Capabilities
        if "capabilities" in plugin and plugin["capabilities"]:
            st.write("### Capabilities")
            for capability in plugin["capabilities"]:
                st.write(f"- {capability}")
        
        # Example usage
        st.write("### Example Usage")
        st.code(f"""
# Create an agent with {plugin['name']}
agent = await plugin_manager.create_agent("{plugin['name']}", {{
    "role": "Researcher",
    "goal": "Find information about AI agents",
    "backstory": "Expert researcher with broad knowledge"
}})

# Execute a task with the agent
result = await plugin_manager.execute_task("{plugin['name']}", agent, {{
    "description": "Research the latest developments in AI agents",
    "expected_output": "A comprehensive research report"
}})
        """, language="python")
        
        # Plugin configuration
        if "settings" in plugin:
            st.write("### Configuration")
            st.json(plugin.get("settings", {}))
    
    async def _load_demo_plugins(self):
        """Load demo plugins for demonstration purposes."""
        from src.server.plugins.agent_framework_config import AgentFrameworkConfig
        
        try:
            # Load CrewAI plugin
            crewai_config = AgentFrameworkConfig(
                name="crewai",
                version="1.0.0",
                description="CrewAI Plugin for orchestrating multi-agent workflows",
                settings={"model": "gpt-4o-mini"}
            )
            await self.plugin_manager.load_plugin("src/server/plugins/crewai_plugin.py", crewai_config)
            
            # Load AutoGen plugin if available
            autogen_config = AgentFrameworkConfig(
                name="autogen",
                version="1.0.0",
                description="Microsoft AutoGen Plugin for conversational agents",
                settings={"model": "gpt-4o-mini"}
            )
            await self.plugin_manager.load_plugin("src/server/plugins/autogen_plugin.py", autogen_config)
            
            # Load SmolAgents plugin if available
            smolagents_config = AgentFrameworkConfig(
                name="smolagents",
                version="1.0.0",
                description="HuggingFace SmolAgents Plugin for lightweight agents",
                settings={"model": "gpt-4o-mini"}
            )
            await self.plugin_manager.load_plugin("src/server/plugins/smolagents_plugin.py", smolagents_config)
            
            return True
        except Exception as e:
            logger.error(f"Error loading demo plugins: {str(e)}")
            return False
```

### Update the Agentic View Controller to Handle Plugins

Next, I'll update the agentic view controller to initialize and manage plugins:

```python
# src/server/views/controllers/agentic_view_controller.py
# Add the following methods/code

import asyncio
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

# Add to the __init__ method
def __init__(self, persistence_model):
    # Existing initialization code...
    
    # Initialize plugin manager
    self.plugin_manager = PluginManager()
    
# Update the initialize method to load plugins
async def initialize(self):
    """Initialize controller with specialized state and plugins."""
    try:
        print("\n🚀 Starting agentic controller initialization...")
        
        # Existing initialization code...
        
        # Initialize plugin manager and load available plugins
        print("📥 Loading available plugins...")
        await self._initialize_plugins()
        
        print("✅ Agentic controller initialization complete")
        
    except Exception as e:
        print(f"Error initializing agentic controller: {str(e)}")
        raise

async def _initialize_plugins(self):
    """Initialize and load available plugins."""
    try:
        from pathlib import Path
        
        # Check for each plugin and load if available
        plugin_path = Path("src/server/plugins")
        
        # Load CrewAI plugin
        crewai_path = plugin_path / "crewai_plugin.py"
        if crewai_path.exists():
            crewai_config = AgentFrameworkConfig(
                name="crewai",
                version="1.0.0",
                description="CrewAI Plugin for orchestrating multi-agent workflows",
                settings={"model": "gpt-4o-mini"}
            )
            success = await self.plugin_manager.load_plugin(str(crewai_path), crewai_config)
            print(f"CrewAI plugin loaded: {success}")
        
        # Load AutoGen plugin if available
        autogen_path = plugin_path / "autogen_plugin.py"
        if autogen_path.exists():
            autogen_config = AgentFrameworkConfig(
                name="autogen",
                version="1.0.0",
                description="Microsoft AutoGen Plugin for conversational agents",
                settings={"model": "gpt-4o-mini"}
            )
            success = await self.plugin_manager.load_plugin(str(autogen_path), autogen_config)
            print(f"AutoGen plugin loaded: {success}")
        
        # Load SmolAgents plugin if available
        smolagents_path = plugin_path / "smolagents_plugin.py"
        if smolagents_path.exists():
            smolagents_config = AgentFrameworkConfig(
                name="smolagents",
                version="1.0.0",
                description="HuggingFace SmolAgents Plugin for lightweight agents",
                settings={"model": "gpt-4o-mini"}
            )
            success = await self.plugin_manager.load_plugin(str(smolagents_path), smolagents_config)
            print(f"SmolAgents plugin loaded: {success}")
            
        print(f"✅ Loaded plugins: {len(self.plugin_manager.list_plugins())}")
        
    except Exception as e:
        print(f"Error initializing plugins: {str(e)}")
        # Don't raise - allow initialization to continue even if plugins fail
```

### Update Agentic Config View to Include Plugin Explorer Tab

Finally, update the agentic_config_view.py file to include the plugin explorer tab:

```python
# src/pages/agentic_config_view.py
# Update render_agentic_config_view() function

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    try:
        # Existing initialization code...
        
        # Add tabs for different views
        tab1, tab2, tab3 = st.tabs(["Chat", "Plugin Explorer", "Observability"])
        
        # Chat View
        with tab1:
            st.subheader("Agentic Framework Chat")
            
            # Display messages
            for msg in st.session_state.agentic_controller.view_state.chat_history:
                if isinstance(msg, Message):
                    role = msg.role
                    content = msg.content
                elif isinstance(msg, dict):
                    role = msg["role"]
                    content = msg["content"]
                else:
                    role = getattr(msg, 'role', 'user')
                    content = str(msg)
                
                with st.chat_message(role):
                    st.write(content)
            
            # Chat input
            if prompt := st.chat_input("Type your message..."):
                with st.chat_message("user"):
                    st.write(prompt)
                
                await st.session_state.agentic_controller.handle_chat(prompt)
                
                # Save session after each message
                view.save_session()
                
                st.rerun()
        
        # Plugin Explorer View
        with tab2:
            st.subheader("Agentic Plugin System")
            
            # Import and create the plugin explorer component
            from server.views.components.plugin_explorer_component import PluginExplorerComponent
            
            if 'agentic_controller' in st.session_state and hasattr(st.session_state.agentic_controller, 'plugin_manager'):
                plugin_explorer = PluginExplorerComponent(st.session_state.agentic_controller.plugin_manager)
                plugin_explorer.render()
            else:
                st.warning("Plugin manager not initialized")
        
        # Observability View
        with tab3:
            st.subheader("Agentic Framework Observability")
            render_observability_view()
            
    except Exception as e:
        st.error(f"Error rendering agentic config view: {str(e)}")
        print(f"Error in render_agentic_config_view: {str(e)}")
        raise
```

## 2. Unit Testing

Create a test file for the plugin explorer component:

```python
# tests/views/components/test_plugin_explorer_component.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import streamlit as st
from src.server.views.components.plugin_explorer_component import PluginExplorerComponent

class TestPluginExplorerComponent:
    """Tests for the PluginExplorerComponent."""
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock plugin manager."""
        mock_manager = MagicMock()
        mock_manager.list_plugins = MagicMock(return_value=[
            {
                "name": "crewai",
                "version": "1.0.0",
                "description": "CrewAI Plugin for orchestrating multi-agent workflows",
                "capabilities": ["agent_creation", "task_execution", "multi-agent_collaboration"],
                "is_initialized": True,
                "settings": {"model": "gpt-4o-mini"}
            },
            {
                "name": "autogen",
                "version": "1.0.0",
                "description": "Microsoft AutoGen Plugin for conversational agents",
                "capabilities": ["function_calling", "agent_handoff", "context_variables"],
                "is_initialized": True,
                "settings": {"model": "gpt-4o-mini"}
            }
        ])
        mock_manager.load_plugin = AsyncMock(return_value=True)
        return mock_manager
    
    @pytest.mark.asyncio
    async def test_render_with_plugins(self, mock_plugin_manager):
        """Test rendering the component with available plugins."""
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Mock streamlit functions
        with patch("streamlit.write") as mock_write, \
             patch("streamlit.warning") as mock_warning, \
             patch("streamlit.tabs") as mock_tabs, \
             patch("streamlit.subheader") as mock_subheader, \
             patch("streamlit.code") as mock_code, \
             patch("streamlit.markdown") as mock_markdown, \
             patch("streamlit.json") as mock_json:
            
            # Mock tabs to return a list of context managers
            mock_tab1 = MagicMock()
            mock_tab2 = MagicMock()
            mock_tabs.return_value = [mock_tab1, mock_tab2]
            
            # Call render
            component.render()
            
            # Assertions
            mock_plugin_manager.list_plugins.assert_called_once()
            mock_tabs.assert_called_once_with(["crewai", "autogen"])
            mock_warning.assert_not_called()  # Should not show warning when plugins exist
            
            # Check that plugin details were rendered
            assert mock_write.call_count >= 1
            assert mock_subheader.call_count >= 1
            assert mock_code.call_count >= 1
            assert mock_markdown.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_render_no_plugins(self, mock_plugin_manager):
        """Test rendering when no plugins are available."""
        # Override mock to return empty list
        mock_plugin_manager.list_plugins.return_value = []
        
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Mock streamlit functions
        with patch("streamlit.write") as mock_write, \
             patch("streamlit.warning") as mock_warning, \
             patch("streamlit.button") as mock_button, \
             patch("streamlit.tabs") as mock_tabs:
            
            mock_button.return_value = False
            
            # Call render
            component.render()
            
            # Assertions
            mock_plugin_manager.list_plugins.assert_called_once()
            mock_warning.assert_called_once()  # Should show warning when no plugins
            mock_tabs.assert_not_called()  # Should not create tabs
            mock_button.assert_called_once()  # Should show load demo button
    
    @pytest.mark.asyncio
    async def test_load_demo_plugins(self, mock_plugin_manager):
        """Test loading demo plugins."""
        # Create component
        component = PluginExplorerComponent(mock_plugin_manager)
        
        # Call _load_demo_plugins
        with patch("src.server.plugins.agent_framework_config.AgentFrameworkConfig") as mock_config:
            result = await component._load_demo_plugins()
            
            # Assertions
            assert result is True
            assert mock_plugin_manager.load_plugin.call_count == 3  # Should load 3 plugins
```

Test for the agentic view controller plugin initialization:

```python
# tests/views/controllers/test_agentic_view_controller.py
# Add these test methods

@pytest.mark.asyncio
async def test_initialize_plugins(self):
    """Test initializing plugins in the agentic controller."""
    # Mock persistence model
    mock_persistence = MagicMock()
    
    # Create controller
    controller = AgenticViewController(mock_persistence)
    controller.plugin_manager = MagicMock()
    controller.plugin_manager.load_plugin = AsyncMock(return_value=True)
    controller.plugin_manager.list_plugins = MagicMock(return_value=[
        {"name": "crewai", "version": "1.0.0"}
    ])
    
    # Mock Path.exists to return True
    with patch("pathlib.Path.exists", return_value=True):
        # Call _initialize_plugins
        await controller._initialize_plugins()
        
        # Assertions
        assert controller.plugin_manager.load_plugin.call_count >= 1
```

## 3. UI/UX Implementation

### CSS Styling

Add the following CSS to enhance the plugin explorer appearance:

```python
# Add to agentic_config_view.py at the beginning of render_agentic_config_view()

# Add custom CSS for plugin explorer
st.markdown("""
<style>
.plugin-card {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 15px;
    background-color: #f9f9f9;
}

.plugin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.status-badge {
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 0.8em;
    font-weight: bold;
}

.active-badge {
    background-color: #d4edda;
    color: #155724;
}

.inactive-badge {
    background-color: #f8d7da;
    color: #721c24;
}

.capabilities-list li {
    margin-bottom: 5px;
}

.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)
```

### Update Plugin Explorer Component to Use Enhanced Styling

Update the `_render_plugin_details` method in `PluginExplorerComponent` to use the enhanced styling:

```python
def _render_plugin_details(self, plugin: Dict[str, Any]):
    """Render details for a single plugin with enhanced styling."""
    # Start plugin card
    st.markdown('<div class="plugin-card">', unsafe_allow_html=True)
    
    # Plugin header with status badge
    status = "Active" if plugin["is_initialized"] else "Inactive"
    badge_class = "active-badge" if plugin["is_initialized"] else "inactive-badge"
    
    st.markdown(f"""
    <div class="plugin-header">
        <h3>{plugin['name']} v{plugin['version']}</h3>
        <span class="status-badge {badge_class}">{status}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Description
    st.write(plugin["description"])
    
    # Capabilities
    if "capabilities" in plugin and plugin["capabilities"]:
        st.write("### Capabilities")
        st.markdown('<ul class="capabilities-list">', unsafe_allow_html=True)
        for capability in plugin["capabilities"]:
            st.markdown(f'<li>{capability}</li>', unsafe_allow_html=True)
        st.markdown('</ul>', unsafe_allow_html=True)
    
    # Create two columns for example and configuration
    col1, col2 = st.columns(2)
    
    with col1:
        # Example usage
        st.write("### Example Usage")
        st.code(f"""
# Create an agent with {plugin['name']}
agent = await plugin_manager.create_agent(
    "{plugin['name']}", 
    {{
        "role": "Researcher",
        "goal": "Find information about AI",
        "backstory": "Expert researcher"
    }}
)

# Execute a task with the agent
result = await plugin_manager.execute_task(
    "{plugin['name']}", 
    agent, 
    {{
        "description": "Research AI frameworks",
        "expected_output": "Comprehensive report"
    }}
)
        """, language="python")
    
    with col2:
        # Plugin configuration
        st.write("### Configuration")
        st.json(plugin.get("settings", {}))
    
    # End plugin card
    st.markdown('</div>', unsafe_allow_html=True)
```

### Visualization Enhancement for Plugin Capabilities

Add a visualization to show plugin capabilities comparison:

```python
# Add this method to PluginExplorerComponent
def render_capabilities_comparison(self):
    """Render a comparison of capabilities across all plugins."""
    plugins = self.plugin_manager.list_plugins()
    if not plugins:
        return
    
    st.write("## Plugin Capabilities Comparison")
    
    # Collect all unique capabilities
    all_capabilities = set()
    for plugin in plugins:
        capabilities = plugin.get("capabilities", [])
        all_capabilities.update(capabilities)
    
    # Create data for visualization
    import pandas as pd
    import altair as alt
    
    data = []
    for plugin in plugins:
        plugin_name = plugin["name"]
        capabilities = plugin.get("capabilities", [])
        
        for capability in all_capabilities:
            data.append({
                "Plugin": plugin_name,
                "Capability": capability,
                "Has Capability": capability in capabilities
            })
    
    # Create dataframe
    df = pd.DataFrame(data)
    
    # Create visualization
    chart = alt.Chart(df).mark_rect().encode(
        x=alt.X('Plugin:N', title="Plugin"),
        y=alt.Y('Capability:N', title="Capability"),
        color=alt.Color('Has Capability:N', 
                       scale=alt.Scale(domain=[True, False],
                                      range=['#7fbf7b', '#f7f7f7'])),
        tooltip=['Plugin', 'Capability', 'Has Capability']
    ).properties(
        width=500,
        height=30 * len(all_capabilities),
        title="Plugin Capabilities"
    )
    
    st.altair_chart(chart, use_container_width=True)
```

Update the render method to include the capabilities comparison:

```python
def render(self):
    """Render the plugin explorer UI."""
    st.write("## Agent Framework Plugin Explorer")
    
    try:
        # Get all loaded plugins
        plugins = self.plugin_manager.list_plugins()
        
        if not plugins:
            st.warning("No plugins are currently loaded.")
            
            # Add a button to load demo plugins
            if st.button("Load Demo Plugins"):
                asyncio.run(self._load_demo_plugins())
                st.rerun()
            return
        
        # Show capabilities comparison
        self.render_capabilities_comparison()
        
        # Create tabs for each plugin
        plugin_names = [plugin["name"] for plugin in plugins]
        tabs = st.tabs(plugin_names)
        
        for i, plugin in enumerate(plugins):
            with tabs[i]:
                self._render_plugin_details(plugin)
                
    except Exception as e:
        logger.error(f"Error rendering plugin explorer: {str(e)}")
        st.error(f"Error loading plugins: {str(e)}")
```

This implementation creates a comprehensive Plugin Explorer component that:

1. Displays available plugins in an organized tab interface
2. Shows detailed information about each plugin including capabilities and configuration
3. Provides code examples showing how to use each plugin
4. Includes a visual comparison of capabilities across plugins
5. Allows loading demo plugins if none are available
6. Features attractive styling for better user experience
7. Includes comprehensive unit tests to ensure functionality

The component integrates seamlessly with the existing Agentic Config View and enhances it with the ability to explore and understand the plugin system, which is a key feature to showcase in the demo.
