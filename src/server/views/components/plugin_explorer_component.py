import streamlit as st
from typing import Dict, Any, List, Optional
import logging
import asyncio

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
        st.write("## 🧩 Agent Framework Plugin Explorer")
        
        try:
            # Get all loaded plugins
            plugins = self.plugin_manager.list_plugins()
            
            if not plugins:
                st.warning("No plugins are currently loaded.")
                
                # Add a button to load demo plugins
                if st.button("🔌 Load Demo Plugins"):
                    asyncio.run(self._load_demo_plugins())
                    st.rerun()
                return
            
            # Show capabilities comparison
            self.render_capabilities_comparison()
            
            # Create tabs for each plugin
            plugin_names = [f"🔌 {plugin['name']}" for plugin in plugins]
            tabs = st.tabs(plugin_names)
            
            for i, plugin in enumerate(plugins):
                with tabs[i]:
                    self._render_plugin_details(plugin)
                    
        except Exception as e:
            logger.error(f"Error rendering plugin explorer: {str(e)}")
            st.error(f"Error loading plugins: {str(e)}")
    
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
            st.write("### ✨ Capabilities")
            st.markdown('<ul class="capabilities-list">', unsafe_allow_html=True)
            for capability in plugin["capabilities"]:
                st.markdown(f'<li>{capability}</li>', unsafe_allow_html=True)
            st.markdown('</ul>', unsafe_allow_html=True)
        
        # Create two columns for example and configuration
        col1, col2 = st.columns(2)
        
        with col1:
            # Example usage
            st.write("### 📝 Example Usage")
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
            st.write("### ⚙️ Configuration")
            st.json(plugin.get("settings", {}))
        
        # End plugin card
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_capabilities_comparison(self):
        """Render a comparison of capabilities across all plugins."""
        plugins = self.plugin_manager.list_plugins()
        if not plugins:
            return
        
        st.write("## 📊 Plugin Capabilities Comparison")
        
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
    
    async def _load_demo_plugins(self):
        """Load demo plugins for demonstration purposes."""
        from src.server.plugins.agent_framework_config import AgentFrameworkConfig
        
        try:
            # Load CrewAI plugin
            crewai_config = AgentFrameworkConfig(
                name="crewai",
                version="1.0.0",
                description="CrewAI Plugin for orchestrating multi-agent workflows",
                settings={"model": "gpt-4o-mini"},
                capabilities=["agent_creation", "task_execution", "multi-agent_collaboration"]
            )
            await self.plugin_manager.load_plugin("src/server/plugins/crewai_plugin.py", crewai_config)
            
            # Load AutoGen plugin if available
            autogen_config = AgentFrameworkConfig(
                name="autogen",
                version="1.0.0",
                description="Microsoft AutoGen Plugin for conversational agents",
                settings={"model": "gpt-4o-mini"},
                capabilities=["function_calling", "agent_handoff", "context_variables"]
            )
            await self.plugin_manager.load_plugin("src/server/plugins/autogen_plugin.py", autogen_config)
            
            # Load SmolAgents plugin if available
            smolagents_config = AgentFrameworkConfig(
                name="smolagents",
                version="1.0.0",
                description="HuggingFace SmolAgents Plugin for lightweight agents",
                settings={"model": "gpt-4o-mini"},
                capabilities=["lightweight_agents", "resource_efficient", "quantized_models"]
            )
            await self.plugin_manager.load_plugin("src/server/plugins/smolagents_plugin.py", smolagents_config)
            
            return True
        except Exception as e:
            logger.error(f"Error loading demo plugins: {str(e)}")
            return False 