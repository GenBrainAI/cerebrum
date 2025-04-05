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
        st.subheader("🧩 Agent Framework Plugin Explorer")
        
        try:
            # Get all loaded plugins
            plugins = self.plugin_manager.list_plugins()
            
            if not plugins:
                st.info("No plugins are currently loaded.")
                st.warning("To use agent frameworks, you need to load plugins.")
                
                # Add a button to load demo plugins
                if st.button("🔌 Load Demo Plugins", use_container_width=True):
                    with st.spinner("Loading demo plugins..."):
                        asyncio.run(self._load_demo_plugins())
                        st.rerun()
                return
            
            # Add stats overview
            self._render_plugin_stats(plugins)
            
            # Create tabs for different plugins
            plugin_names = [p["name"] for p in plugins]
            tabs = st.tabs(plugin_names)
            
            # Fill each tab with plugin details
            for i, (tab, plugin) in enumerate(zip(tabs, plugins)):
                with tab:
                    self._render_plugin_details(plugin)
            
            # Show capabilities comparison
            self.render_capabilities_comparison()
            
        except Exception as e:
            logger.error(f"Error rendering plugin explorer: {str(e)}")
            st.error(f"Error loading plugins: {str(e)}")
    
    def _render_plugin_stats(self, plugins: List[Dict[str, Any]]):
        """Render a summary of plugin stats."""
        active_plugins = sum(1 for p in plugins if p.get("is_initialized", False))
        total_capabilities = sum(len(p.get("capabilities", [])) for p in plugins)
        unique_capabilities = len({cap for p in plugins for cap in p.get("capabilities", [])})
        
        st.write("### Plugin System Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Plugins", len(plugins))
        with col2:
            st.metric("Active Plugins", f"{active_plugins}/{len(plugins)}")
        with col3:
            st.metric("Total Capabilities", total_capabilities)
        with col4:
            st.metric("Unique Capabilities", unique_capabilities)
    
    def _render_plugin_card(self, plugin: Dict[str, Any]):
        """Render a single plugin card with improved styling."""
        # Create a card with border
        st.markdown(f"""
        <div style="
            border: 1px solid {'#7fbf7b' if plugin['is_initialized'] else '#d3d3d3'};
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: {'#f8fdf8' if plugin['is_initialized'] else '#f9f9f9'};
            height: 100%;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0;">{plugin['name']}</h3>
                <span style="
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 0.8em;
                    font-weight: bold;
                    background-color: {'#d4edda' if plugin['is_initialized'] else '#f8d7da'};
                    color: {'#155724' if plugin['is_initialized'] else '#721c24'};
                ">
                    {'Active' if plugin['is_initialized'] else 'Inactive'}
                </span>
            </div>
            <p><strong>Version:</strong> {plugin.get('version', 'N/A')}</p>
            <p>{plugin.get('description', 'No description available')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add plugin actions as buttons with fixed height
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"⚙️ Configuration", key=f"config_{plugin['name']}", use_container_width=True):
                st.session_state[f"show_config_{plugin['name']}"] = True
        with col2:
            if st.button(f"ℹ️ Details", key=f"details_{plugin['name']}", use_container_width=True):
                st.session_state[f"show_details_{plugin['name']}"] = True
        
        # Show configuration if button was clicked
        if st.session_state.get(f"show_config_{plugin['name']}", False):
            with st.expander("Plugin Configuration", expanded=True):
                st.json(plugin.get("settings", {}))
                if st.button("Close", key=f"close_config_{plugin['name']}"):
                    st.session_state[f"show_config_{plugin['name']}"] = False
        
        # Show details if button was clicked
        if st.session_state.get(f"show_details_{plugin['name']}", False):
            with st.expander("Plugin Details", expanded=True):
                # Capabilities
                if "capabilities" in plugin and plugin["capabilities"]:
                    st.write("#### ✨ Capabilities")
                    for capability in plugin["capabilities"]:
                        st.markdown(f"- {capability}")
                
                # Example usage
                st.write("#### 📝 Example Usage")
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
                
                if st.button("Close", key=f"close_details_{plugin['name']}"):
                    st.session_state[f"show_details_{plugin['name']}"] = False
    
    def _render_plugin_details(self, plugin: Dict[str, Any]):
        """Render detailed information about a plugin."""
        # Basic info
        st.write(f"#### {plugin['name']} {plugin.get('version', '')}")
        st.markdown(plugin.get('description', 'No description available'))
        
        # Status indicator
        status = "✅ Active" if plugin.get("is_initialized", False) else "❌ Inactive"
        st.info(f"**Status:** {status}")
        
        # Capabilities
        if "capabilities" in plugin and plugin["capabilities"]:
            st.write("#### Capabilities")
            for capability in plugin["capabilities"]:
                st.markdown(f"- {capability}")
                
        # Configuration
        if "settings" in plugin and plugin["settings"]:
            with st.expander("Plugin Configuration"):
                st.json(plugin["settings"])
                
        # Example code
        with st.expander("Example Usage"):
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
    
    def render_capabilities_comparison(self):
        """Render a comparison of capabilities across all plugins."""
        plugins = self.plugin_manager.list_plugins()
        if not plugins:
            return
        
        st.write("### 📊 Plugin Capabilities Comparison")
        
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
        
        # Create visualization with improved colors
        chart = alt.Chart(df).mark_rect().encode(
            x=alt.X('Plugin:N', title="Plugin", sort=alt.EncodingSortField(field="Plugin")),
            y=alt.Y('Capability:N', title="Capability", sort=alt.EncodingSortField(field="Capability")),
            color=alt.Color('Has Capability:N', 
                           scale=alt.Scale(domain=[True, False],
                                          range=['#7fbf7b', '#f7f7f7'])),
            tooltip=['Plugin', 'Capability', 'Has Capability']
        ).properties(
            width=500,
            height=30 * len(all_capabilities),
            title="Plugin Capabilities Comparison"
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # Add a button to create a handover workflow
        st.write("### 🔄 Create Handover Workflow")
        st.markdown("""
        Create a workflow that hands over between different plugins, allowing agents
        from different frameworks to collaborate on a task.
        """)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("✨ Create Workflow", key="create_handover_workflow", use_container_width=True):
                st.session_state["show_handover_form"] = True
                
        # Show handover workflow form if button was clicked
        if st.session_state.get("show_handover_form", False):
            self._render_handover_workflow_form(plugins)
    
    def _render_handover_workflow_form(self, plugins: List[Dict[str, Any]]):
        """Render a form to create a handover workflow."""
        with st.form("handover_workflow_form"):
            st.write("#### Configure Handover Workflow")
            
            workflow_name = st.text_input("Workflow Name", "My Handover Workflow")
            workflow_topic = st.text_input("Research Topic", "AI agent frameworks")
            
            st.write("#### Select Plugins for Each Step")
            
            plugin_names = [p["name"] for p in plugins if p.get("is_initialized", False)]
            
            if len(plugin_names) < 2:
                st.warning("You need at least 2 active plugins to create a handover workflow")
                submit_disabled = True
            else:
                submit_disabled = False
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    first_plugin = st.selectbox("First Plugin (Research)", plugin_names, index=0)
                    first_role = st.text_input("First Agent Role", "Researcher")
                with col2:
                    second_plugin = st.selectbox("Second Plugin (Analysis)", plugin_names, index=min(1, len(plugin_names)-1))
                    second_role = st.text_input("Second Agent Role", "Analyst")
                with col3:
                    third_plugin = st.selectbox("Third Plugin (Summary)", plugin_names, index=min(2, len(plugin_names)-1))
                    third_role = st.text_input("Third Agent Role", "Writer")
            
            st.write("#### Workflow Preview")
            steps = [
                {"plugin": first_plugin, "role": first_role, "task": f"Research information about {workflow_topic}"},
                {"plugin": second_plugin, "role": second_role, "task": f"Analyze research findings about {workflow_topic}"},
                {"plugin": third_plugin, "role": third_role, "task": f"Write a summary report about {workflow_topic}"}
            ] if not submit_disabled else []
            
            self._render_workflow_preview(workflow_name, workflow_topic, steps)
            
            submit_button = st.form_submit_button("Create Workflow", disabled=submit_disabled)
            
            if submit_button:
                st.success(f"Workflow '{workflow_name}' created successfully!")
                # Here you would actually create the workflow
                st.session_state["show_handover_form"] = False
                
    def _render_workflow_preview(self, workflow_name, topic, steps):
        """Render a preview of the workflow."""
        if not steps:
            return
            
        st.markdown(f"""
        <div style="border: 1px solid #d3d3d3; border-radius: 10px; padding: 15px; margin-bottom: 15px;">
            <h4 style="margin-top: 0;">{workflow_name}</h4>
            <p>This workflow will research, analyze, and summarize information about <strong>{topic}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
        
        for i, step in enumerate(steps):
            st.markdown(f"""
            <div style="
                display: flex;
                margin-bottom: 10px;
                align-items: center;
            ">
                <div style="
                    background-color: #4b7bec;
                    color: white;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 15px;
                    flex-shrink: 0;
                ">
                    {i+1}
                </div>
                <div style="
                    border: 1px solid #d3d3d3;
                    border-radius: 10px;
                    padding: 10px;
                    flex-grow: 1;
                ">
                    <div style="font-weight: bold;">{step['plugin']} - {step['role']}</div>
                    <div>{step['task']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add arrow between steps
            if i < len(steps) - 1:
                st.markdown("""
                <div style="
                    display: flex;
                    justify-content: center;
                    margin: 5px 0;
                ">
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 10px solid transparent;
                        border-right: 10px solid transparent;
                        border-top: 10px solid #4b7bec;
                    "></div>
                </div>
                """, unsafe_allow_html=True)
    
    async def _load_demo_plugins(self):
        """Load demo plugins for testing."""
        try:
            # This is just a mock implementation for testing
            # In a real implementation, you would load actual plugins
            
            # Load CrewAI plugin
            await self.plugin_manager.load_plugin({
                "name": "crewai",
                "version": "1.0.0",
                "description": "CrewAI Plugin for orchestrating multi-agent workflows",
                "capabilities": ["agent_creation", "task_execution", "multi-agent_collaboration"]
            })
            
            # Load AutoGen plugin
            await self.plugin_manager.load_plugin({
                "name": "autogen",
                "version": "1.0.0",
                "description": "Microsoft AutoGen Plugin for conversational agents",
                "capabilities": ["function_calling", "agent_handoff", "context_variables"]
            })
            
            # Load SmolAgents plugin
            await self.plugin_manager.load_plugin({
                "name": "smol",
                "version": "0.1.0",
                "description": "SmolAgents Plugin for lightweight agent frameworks",
                "capabilities": ["memory_management", "efficient_execution", "quantized_models"]
            })
            
            return True
        except Exception as e:
            logger.error(f"Error loading demo plugins: {str(e)}")
            return False 