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
                
                # Add a button to load demo plugins
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔌 Load Demo Plugins", use_container_width=True):
                        with st.spinner("Loading demo plugins..."):
                            asyncio.run(self._load_demo_plugins())
                            st.rerun()
                with col2:
                    st.markdown("""
                    Click to load demonstration plugins for CrewAI, AutoGen, and SmolAgents.
                    These plugins will demonstrate the handover capabilities between different agent frameworks.
                    """)
                return
            
            # Add stats overview
            self._render_plugin_stats(plugins)
            
            # Show capabilities comparison
            self.render_capabilities_comparison()
            
            # Plugin detailed cards
            st.subheader("Available Plugins")
            
            # Create a row of columns for plugin cards
            plugin_cols = st.columns(min(3, len(plugins)))
            
            for i, plugin in enumerate(plugins):
                with plugin_cols[i % len(plugin_cols)]:
                    self._render_plugin_card(plugin)
                    
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
                    if len(plugin_names) >= 2:
                        second_plugin = st.selectbox("Second Plugin (Analysis)", plugin_names, index=min(1, len(plugin_names)-1))
                        second_role = st.text_input("Second Agent Role", "Analyst")
                    else:
                        second_plugin = None
                with col3:
                    if len(plugin_names) >= 3:
                        third_plugin = st.selectbox("Third Plugin (Report)", plugin_names, index=min(2, len(plugin_names)-1))
                        third_role = st.text_input("Third Agent Role", "Writer")
                    else:
                        third_plugin = None
            
            submit = st.form_submit_button("Create Workflow", disabled=submit_disabled)
            
            if submit:
                st.success(f"Workflow '{workflow_name}' created successfully!")
                st.info("Note: This is a demonstration only. The workflow is not actually created.")
                
                # Show the workflow visualization
                self._render_workflow_preview(
                    workflow_name,
                    workflow_topic,
                    [
                        {"plugin": first_plugin, "role": first_role},
                        {"plugin": second_plugin, "role": second_role} if second_plugin else None,
                        {"plugin": third_plugin, "role": third_role} if third_plugin else None
                    ]
                )
    
    def _render_workflow_preview(self, workflow_name, topic, steps):
        """Render a preview of the workflow."""
        st.write(f"### {workflow_name} Preview")
        st.write(f"**Topic:** {topic}")
        
        # Filter out None steps
        steps = [step for step in steps if step]
        
        # Create a simple workflow diagram
        import networkx as nx
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.figure import Figure
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Define colors for each plugin
        plugin_colors = {
            step["plugin"]: color for step, color in zip(
                steps, ['lightblue', 'lightgreen', 'lightsalmon'][:len(steps)]
            )
        }
        
        # Add nodes for each step
        for i, step in enumerate(steps):
            G.add_node(
                f"{step['plugin']}\n{step['role']}", 
                color=plugin_colors[step["plugin"]],
                position=(i, 0)
            )
        
        # Add edges between steps
        for i in range(len(steps) - 1):
            from_node = f"{steps[i]['plugin']}\n{steps[i]['role']}"
            to_node = f"{steps[i+1]['plugin']}\n{steps[i+1]['role']}"
            if i == 0:
                G.add_edge(from_node, to_node, label="Research Results")
            else:
                G.add_edge(from_node, to_node, label="Analysis Results")
        
        # Create a figure
        fig = Figure(figsize=(10, 4))
        ax = fig.subplots()
        
        # Get positions
        pos = {n: (i, 0) for i, n in enumerate(G.nodes())}
        
        # Draw nodes
        node_colors = [G.nodes[n].get("color", "lightgray") for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, alpha=0.8, ax=ax)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=2, arrowsize=20, connectionstyle="arc3,rad=0.1", ax=ax)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold", ax=ax)
        
        # Draw edge labels
        edge_labels = {(u, v): d.get("label", "") for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10, ax=ax)
        
        # Create legend
        legend_patches = [
            mpatches.Patch(color=color, label=plugin) 
            for plugin, color in plugin_colors.items()
        ]
        ax.legend(handles=legend_patches, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=len(steps))
        
        # Remove axis
        ax.axis("off")
        ax.set_title(workflow_name, fontsize=14, pad=20)
        
        # Display the figure
        st.pyplot(fig)
    
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
            await self.plugin_manager.load_plugin("src/server/plugins/examples/crewai_plugin.py", crewai_config)
            
            # Load AutoGen plugin
            autogen_config = AgentFrameworkConfig(
                name="autogen",
                version="1.0.0",
                description="Microsoft AutoGen Plugin for conversational agents",
                settings={"model": "gpt-4o-mini"},
                capabilities=["function_calling", "agent_handoff", "context_variables"]
            )
            await self.plugin_manager.load_plugin("src/server/plugins/examples/autogen_plugin.py", autogen_config)
            
            # Load SmolAgents plugin
            smolagents_config = AgentFrameworkConfig(
                name="smolagents",
                version="1.0.0",
                description="HuggingFace SmolAgents Plugin for lightweight agents",
                settings={"model": "gpt-4o-mini"},
                capabilities=["lightweight_agents", "resource_efficient", "quantized_models"]
            )
            await self.plugin_manager.load_plugin("src/server/plugins/examples/smolagents_plugin.py", smolagents_config)
            
            return True
        except Exception as e:
            logger.error(f"Error loading demo plugins: {str(e)}")
            return False 