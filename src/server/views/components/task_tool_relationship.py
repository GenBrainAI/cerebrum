import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from uuid import UUID
from ...persistence.persistence_model import PersistenceModelBase
from ...models.task import Task
from ...models.toolset import Toolset, Tool
from ...controllers.curried_proxy import CurriedProxy
from ...tools.tools_catalog import tools_catalog
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64

class TaskToolRelationshipComponent:
    """Component to visualize the relationship between tasks, curried proxies, and tools."""
    
    def __init__(self, persistence_model: PersistenceModelBase, tools_controller=None):
        self.persistence_model = persistence_model
        self.tools_controller = tools_controller
        
    def render(self):
        """Render the task-tool relationship visualization component."""
        st.subheader("Task-Tool Relationship Visualization")
        
        # Get all tasks
        tasks = self.persistence_model.tasks.list()
        if not tasks:
            st.warning("No tasks found in the current state.")
            return
        
        # Display persistence model type info
        is_global = True
        if self.tools_controller:
            is_global = self.tools_controller.using_global_persistence
            
        # Display info about which persistence model is being used
        st.info(f"Visualizing tasks from the {'global' if is_global else 'local'} persistence model.")
        
        # Get all available tools from the catalog
        available_tools = tools_catalog.list_tools()
        
        # Create tabs for different sections
        main_tab1, main_tab2, main_tab3 = st.tabs(["Table View", "Graph View", "Manage Relationships"])
        
        with main_tab1:
            self._render_table_view(tasks)
            
        with main_tab2:
            self._render_graph_view(tasks)
            
        with main_tab3:
            self._render_management_view(tasks, available_tools)
    
    def _render_management_view(self, tasks: List[Task], available_tools: List[str]):
        """Render the management interface for task-tool relationships."""
        st.subheader("Manage Task-Tool Relationships")
        
        # Select a task
        task_options = {task.id: f"{task.name} ({task.id})" for task in tasks}
        selected_task_id = st.selectbox(
            "Select a task to configure tools for:",
            options=list(task_options.keys()),
            format_func=lambda x: task_options[x] if x in task_options else x
        )
        
        # Get the selected task
        selected_task = next((task for task in tasks if task.id == selected_task_id), None)
        if not selected_task:
            st.warning("Please select a valid task.")
            return
            
        # Display current relationships
        st.subheader(f"Current Configuration for: {selected_task.name}")
        
        # Display CurriedProxy information
        current_proxy = None
        if selected_task.curried_proxy_id:
            current_proxy = self.persistence_model.curried_proxies.read(selected_task.curried_proxy_id)
            
        if current_proxy:
            # Get proxy name
            proxy_name = "Unnamed Proxy"
            if hasattr(current_proxy, 'name') and current_proxy.name:
                proxy_name = current_proxy.name
                
            # Create a nice info box with the proxy information
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.success(f"✅ This task is linked to a CurriedProxy with ID: `{selected_task.curried_proxy_id}`")
                with col2:
                    # Add a Remove button with better styling
                    st.button("🗑️ Remove", 
                              type="secondary", 
                              use_container_width=True,
                              help="Remove this CurriedProxy from the task",
                              key="remove_proxy_button",
                              on_click=lambda: st.session_state.update({
                                  'pending_operations': st.session_state.get('pending_operations', []) + [
                                      {'type': 'remove_proxy', 'task_id': selected_task_id}
                                  ]
                              }))
                
                # Display tools in proxy
                if hasattr(current_proxy, 'tools'):
                    st.markdown("**Tools in Proxy:**")
                    for tool in current_proxy.tools:
                        st.markdown(f"- {tool.name}")
                    
                    # Add Edit button for the proxy
                    if st.button("✏️ Edit CurriedProxy", key="edit_proxy_button"):
                        # Initialize the session state variables if they don't exist
                        if 'editing_proxy' not in st.session_state:
                            st.session_state.editing_proxy = False
                        if 'editing_proxy_id' not in st.session_state:
                            st.session_state.editing_proxy_id = None
                            
                        # Set the editing state
                        st.session_state.editing_proxy = True
                        st.session_state.editing_proxy_id = str(selected_task.curried_proxy_id)
                        st.rerun()
                else:
                    st.info("No tools information available in this CurriedProxy.")
        else:
            st.warning("⚠️ This task has no associated CurriedProxy.")
        
        # Display Toolsets information
        toolsets = []
        if selected_task.toolsets:
            for toolset_id in selected_task.toolsets:
                toolset = self.persistence_model.toolsets.read(toolset_id)
                if toolset:
                    toolsets.append(toolset)
        
        if toolsets:
            st.markdown("**Associated Toolsets:**")
            for i, toolset in enumerate(toolsets):
                with st.expander(f"Toolset: {toolset.name}"):
                    st.markdown(f"**ID:** `{toolset.id}`")
                    st.markdown(f"**Description:** {toolset.description or 'No description'}")
                    
                    if toolset.tool_ids:
                        st.markdown("**Tools:**")
                        for tool_id in toolset.tool_ids:
                            tool = self.persistence_model.tools.read(tool_id)
                            if tool:
                                tool_name = tool.function.name if hasattr(tool, 'function') and hasattr(tool.function, 'name') else "Unknown"
                                st.markdown(f"- {tool_name}")
                    else:
                        st.info("No tools in this toolset.")
        else:
            st.info("This task has no associated toolsets.")
            
        # Add separator
        st.markdown("---")
        
        # CurriedProxy Management (exactly like Vector Store Management)
        st.subheader("CurriedProxy Management")
        
        # Get available CurriedProxies
        available_proxies = []
        if self.tools_controller:
            available_proxies = self.tools_controller.get_available_curried_proxies()
        
        # Add text "Add tools to task via"
        st.markdown("Add tools to task via")
        
        # Create dropdown for proxy selection
        proxy_options = {"": "Select a CurriedProxy..."}
        for proxy in available_proxies:
            proxy_id = proxy["id"]
            proxy_name = proxy.get("name", "Unnamed Proxy")
            tool_count = proxy["tool_count"]
            proxy_options[proxy_id] = f"{proxy_name} ({tool_count} tools)"
        
        selected_proxy_id = st.selectbox(
            "",  # No label as we already have the text above
            options=list(proxy_options.keys()),
            format_func=lambda x: proxy_options[x],
            key="proxy_selector",
            label_visibility="collapsed"
        )
        
        # Create New CurriedProxy section (collapsible)
        with st.expander("Create New CurriedProxy", expanded=False):
            # New CurriedProxy Name
            new_proxy_name = st.text_input("New CurriedProxy Name", value="New CurriedProxy")
            
            # Multi-select tools from catalog
            selected_tools = st.multiselect(
                "Select tools from catalog to add to the new CurriedProxy:",
                options=available_tools
            )
            
            # Create button
            if st.button("Create CurriedProxy", type="primary"):
                if self.tools_controller is not None and selected_tools:
                    # Store the operation in session state for execution
                    if 'pending_operations' not in st.session_state:
                        st.session_state.pending_operations = []
                    
                    st.session_state.pending_operations.append({
                        'type': 'create_proxy',
                        'task_id': selected_task_id,
                        'tool_names': selected_tools,
                        'proxy_name': new_proxy_name
                    })
                    
                    st.success(f"Will create CurriedProxy '{new_proxy_name}' with {len(selected_tools)} tools.")
                    st.rerun()
                elif not selected_tools:
                    st.warning("Please select at least one tool to add to the CurriedProxy.")
                else:
                    st.error("Tools controller not available.")
        
        # Handle proxy selection
        if selected_proxy_id:
            # User selected an existing proxy
            selected_proxy = next((p for p in available_proxies if p["id"] == selected_proxy_id), None)
            
            if selected_proxy:
                # Show proxy details
                proxy_name = selected_proxy.get("name", "Unnamed Proxy")
                st.markdown(f"**Selected CurriedProxy:** {proxy_name}")
                
                # Show tools in the selected proxy
                if selected_proxy["tools"]:
                    st.markdown("**Tools in selected proxy:**")
                    for tool_name in selected_proxy["tools"]:
                        st.markdown(f"- {tool_name}")
                
                # Show Link button only if task doesn't already have this proxy
                if not current_proxy or str(current_proxy.id) != selected_proxy_id:
                    if st.button("Link Selected CurriedProxy to Task", type="primary"):
                        if self.tools_controller:
                            # Store the operation in session state
                            if 'pending_operations' not in st.session_state:
                                st.session_state.pending_operations = []
                            
                            st.session_state.pending_operations.append({
                                'type': 'link_proxy',
                                'task_id': selected_task_id,
                                'proxy_id': selected_proxy_id
                            })
                            
                            st.success(f"Will link the selected CurriedProxy to this task.")
                            st.rerun()
                else:
                    st.success("This proxy is already linked to the task.")
        else:
            # No proxy selected
            st.info("Please select a CurriedProxy to view its contents")
        
        # Toolset Management
        st.markdown("---")
        st.subheader("Toolset Management")
        
        # Enter toolset name
        toolset_name = st.text_input("Toolset Name:", value=f"Toolset for {selected_task.name}")
        
        # Multi-select tools to add to toolset
        selected_toolset_tools = st.multiselect(
            "Select tools to add to the toolset:",
            options=available_tools,
            key="toolset_tools"
        )
        
        if selected_toolset_tools and toolset_name:
            # Button to create toolset
            if st.button("Create and Link Toolset", type="primary"):
                if self.tools_controller is not None:
                    # Store the operation in session state for execution
                    if 'pending_operations' not in st.session_state:
                        st.session_state.pending_operations = []
                    
                    st.session_state.pending_operations.append({
                        'type': 'create_toolset',
                        'task_id': selected_task_id,
                        'toolset_name': toolset_name,
                        'tool_names': selected_toolset_tools
                    })
                    
                    st.success(f"Will create toolset with {len(selected_toolset_tools)} tools.")
                    st.rerun()
                else:
                    st.error("Tools controller not available.")
        
        # Show editing interface if in editing mode
        editing_proxy = st.session_state.get('editing_proxy', False)
        editing_proxy_id = st.session_state.get('editing_proxy_id')
        current_proxy_id = str(selected_task.curried_proxy_id) if selected_task.curried_proxy_id else None
        
        if editing_proxy and editing_proxy_id == current_proxy_id:
            with st.container(border=True):
                st.subheader("Edit CurriedProxy")
                
                # Get proxy details
                proxy_info = self.persistence_model.curried_proxies.read(selected_task.curried_proxy_id)
                if not proxy_info:
                    st.error(f"Could not find CurriedProxy with ID: {selected_task.curried_proxy_id}")
                    return
                    
                # Get proxy name
                proxy_name = "Unnamed Proxy"
                if hasattr(proxy_info, 'name') and proxy_info.name:
                    proxy_name = proxy_info.name
                
                # Rename proxy
                new_name = st.text_input("Proxy Name", value=proxy_name, key="edit_proxy_name")
                if new_name != proxy_name and st.button("Update Name", key="update_proxy_name"):
                    if self.tools_controller:
                        if 'pending_operations' not in st.session_state:
                            st.session_state.pending_operations = []
                        
                        st.session_state.pending_operations.append({
                            'type': 'rename_proxy',
                            'proxy_id': selected_task.curried_proxy_id,
                            'new_name': new_name
                        })
                        
                        st.success(f"Will rename proxy to '{new_name}'.")
                        st.rerun()
                
                # Add tools to proxy
                st.markdown("### Add Tools")
                
                # Get current tools in proxy
                current_tools = []
                if hasattr(proxy_info, 'tools'):
                    current_tools = [tool.name for tool in proxy_info.tools]
                
                # Filter available tools to show only those not already in the proxy
                available_new_tools = [tool for tool in available_tools if tool not in current_tools]
                
                # Multi-select tools to add
                tools_to_add = st.multiselect(
                    "Select tools to add:",
                    options=available_new_tools,
                    key="tools_to_add"
                )
                
                if tools_to_add and st.button("Add Selected Tools", key="add_tools_button"):
                    if self.tools_controller:
                        if 'pending_operations' not in st.session_state:
                            st.session_state.pending_operations = []
                        
                        st.session_state.pending_operations.append({
                            'type': 'add_tools_to_proxy',
                            'proxy_id': selected_task.curried_proxy_id,
                            'tool_names': tools_to_add
                        })
                        
                        st.success(f"Will add {len(tools_to_add)} tools to proxy.")
                        st.rerun()
                
                # Remove tools from proxy
                if current_tools:
                    st.markdown("### Remove Tools")
                    
                    # Multi-select tools to remove
                    tools_to_remove = st.multiselect(
                        "Select tools to remove:",
                        options=current_tools,
                        key="tools_to_remove"
                    )
                    
                    if tools_to_remove and st.button("Remove Selected Tools", key="remove_tools_button", type="secondary"):
                        if self.tools_controller:
                            if 'pending_operations' not in st.session_state:
                                st.session_state.pending_operations = []
                            
                            st.session_state.pending_operations.append({
                                'type': 'remove_tools_from_proxy',
                                'proxy_id': selected_task.curried_proxy_id,
                                'tool_names': tools_to_remove
                            })
                            
                            st.success(f"Will remove {len(tools_to_remove)} tools from proxy.")
                            st.rerun()
                
                # Done editing button
                if st.button("Done Editing", key="done_editing_button"):
                    # Ensure we're clearing the editing state properly
                    st.session_state.editing_proxy = False
                    st.session_state.editing_proxy_id = None
                    # Force a rerun to update the UI
                    st.rerun()
    
    def _render_table_view(self, tasks: List[Task]):
        """Render a table view of task-tool relationships."""
        # Create a list to hold all the relationship data
        relationships = []
        
        for task in tasks:
            task_name = task.name or "Unnamed Task"
            
            # Get CurriedProxy if available
            proxy = None
            if task.curried_proxy_id:
                try:
                    proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
                except:
                    pass
            
            # Get toolsets associated with the task
            toolsets = []
            if task.toolsets:
                for toolset_id in task.toolsets:
                    try:
                        toolset = self.persistence_model.toolsets.read(toolset_id)
                        if toolset:
                            toolsets.append(toolset)
                    except:
                        pass
            
            # If no proxy or toolsets, add one row showing no tools
            if not proxy and not toolsets:
                relationships.append({
                    "Task": task_name,
                    "Task ID": str(task.id),
                    "CurriedProxy ID": "None",
                    "Toolset": "None",
                    "Tool": "None"
                })
                continue
                
            # If there's a proxy, add tools from the proxy
            if proxy:
                # Handle CurriedProxyInfo object - look for tools attribute
                if hasattr(proxy, 'tools') and proxy.tools:
                    for tool in proxy.tools:
                        relationships.append({
                            "Task": task_name,
                            "Task ID": str(task.id),
                            "CurriedProxy ID": str(task.curried_proxy_id),
                            "Toolset": "From CurriedProxy",
                            "Tool": tool.name
                        })
                else:
                    relationships.append({
                        "Task": task_name,
                        "Task ID": str(task.id),
                        "CurriedProxy ID": str(task.curried_proxy_id),
                        "Toolset": "From CurriedProxy",
                        "Tool": "No tools information available"
                    })
            
            # Add tools from toolsets
            for toolset in toolsets:
                if toolset.tool_ids:
                    for tool_id in toolset.tool_ids:
                        try:
                            tool = self.persistence_model.tools.read(tool_id)
                            if tool:
                                tool_name = tool.function.name if hasattr(tool, 'function') and hasattr(tool.function, 'name') else "Unknown"
                                relationships.append({
                                    "Task": task_name,
                                    "Task ID": str(task.id),
                                    "CurriedProxy ID": str(task.curried_proxy_id) if task.curried_proxy_id else "None",
                                    "Toolset": toolset.name,
                                    "Tool": tool_name
                                })
                        except:
                            pass
                else:
                    relationships.append({
                        "Task": task_name,
                        "Task ID": str(task.id),
                        "CurriedProxy ID": str(task.curried_proxy_id) if task.curried_proxy_id else "None",
                        "Toolset": toolset.name,
                        "Tool": "No tools in toolset"
                    })
        
        # Create DataFrame and display it
        if relationships:
            df = pd.DataFrame(relationships)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No task-tool relationships found.")
    
    def _render_graph_view(self, tasks: List[Task]):
        """Render a graph visualization of task-tool relationships."""
        # Create a graph
        G = nx.DiGraph()
        
        # Add nodes and edges
        for task in tasks:
            task_name = task.name or f"Task {str(task.id)[:8]}"
            task_id = f"task_{task.id}"
            G.add_node(task_id, label=task_name, type="task")
            
            # Add CurriedProxy if available
            if task.curried_proxy_id:
                proxy_id = f"proxy_{task.curried_proxy_id}"
                proxy_label = f"Proxy {str(task.curried_proxy_id)[:8]}"
                G.add_node(proxy_id, label=proxy_label, type="proxy")
                G.add_edge(task_id, proxy_id)
                
                # Try to get tools from the proxy
                try:
                    proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
                    if proxy and hasattr(proxy, 'tools'):
                        for tool in proxy.tools:
                            tool_id = f"tool_{tool.name}"
                            G.add_node(tool_id, label=tool.name, type="tool")
                            G.add_edge(proxy_id, tool_id)
                except:
                    pass
            
            # Add toolsets and their tools
            if task.toolsets:
                for toolset_id in task.toolsets:
                    try:
                        toolset = self.persistence_model.toolsets.read(toolset_id)
                        if toolset:
                            toolset_node_id = f"toolset_{toolset_id}"
                            G.add_node(toolset_node_id, label=toolset.name, type="toolset")
                            G.add_edge(task_id, toolset_node_id)
                            
                            if toolset.tool_ids:
                                for tool_id in toolset.tool_ids:
                                    try:
                                        tool = self.persistence_model.tools.read(tool_id)
                                        if tool and hasattr(tool, 'function') and hasattr(tool.function, 'name'):
                                            tool_node_id = f"tool_{tool.function.name}_{tool_id}"
                                            G.add_node(tool_node_id, label=tool.function.name, type="tool")
                                            G.add_edge(toolset_node_id, tool_node_id)
                                    except:
                                        pass
                    except:
                        pass
        
        # Check if graph has nodes
        if not G.nodes():
            st.info("No data available for graph visualization.")
            return
            
        # Set node colors based on type
        node_colors = []
        for node in G.nodes():
            if G.nodes[node]['type'] == 'task':
                node_colors.append('lightblue')
            elif G.nodes[node]['type'] == 'proxy':
                node_colors.append('lightgreen')
            elif G.nodes[node]['type'] == 'toolset':
                node_colors.append('orange')
            else:  # tool
                node_colors.append('pink')
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=False, node_color=node_colors, node_size=700, arrows=True)
        
        # Add labels with better positioning
        labels = {node: G.nodes[node]['label'] for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
        
        # Add a legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue', markersize=10, label='Task'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen', markersize=10, label='CurriedProxy'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Toolset'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='pink', markersize=10, label='Tool')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # Save figure to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        
        # Display the image in Streamlit
        st.image(buf, use_column_width=True)
        plt.close()

def render_task_tool_relationship(persistence_model: PersistenceModelBase, tools_controller=None):
    """Render the task-tool relationship component."""
    # Initialize editing state if not exists
    if 'editing_proxy' not in st.session_state:
        st.session_state.editing_proxy = False
    if 'editing_proxy_id' not in st.session_state:
        st.session_state.editing_proxy_id = None
    
    # Process any pending operations
    if 'pending_operations' in st.session_state and st.session_state.pending_operations:
        for operation in st.session_state.pending_operations:
            if operation['type'] == 'create_proxy':
                # Execute the operation
                proxy_id = tools_controller.create_proxy_for_task(
                    operation['task_id'], 
                    operation['tool_names'],
                    operation.get('proxy_name', 'New CurriedProxy')  # Get proxy name if provided
                )
                # Show confirmation
                if proxy_id:
                    proxy_name = operation.get('proxy_name', 'New CurriedProxy')
                    st.success(f"CurriedProxy '{proxy_name}' created with ID: {proxy_id}")
                else:
                    st.error("Failed to create CurriedProxy.")
            
            elif operation['type'] == 'link_proxy':
                # Link an existing proxy to a task
                success = tools_controller.link_existing_proxy_to_task(
                    operation['task_id'],
                    operation['proxy_id']
                )
                # Show confirmation
                if success:
                    st.success(f"Task linked to existing CurriedProxy successfully.")
                else:
                    st.error("Failed to link task to CurriedProxy.")
            
            elif operation['type'] == 'remove_proxy':
                # Remove a proxy from a task
                success = tools_controller.remove_proxy_from_task(
                    operation['task_id']
                )
                # Show confirmation
                if success:
                    st.success(f"CurriedProxy removed from task successfully.")
                else:
                    st.error("Failed to remove CurriedProxy from task.")
            
            elif operation['type'] == 'add_tools_to_proxy':
                # Add tools to a proxy
                success = tools_controller.add_tools_to_proxy(
                    operation['proxy_id'],
                    operation['tool_names']
                )
                # Show confirmation
                if success:
                    st.success(f"Tools added to CurriedProxy successfully.")
                else:
                    st.error("Failed to add tools to CurriedProxy.")
            
            elif operation['type'] == 'remove_tools_from_proxy':
                # Remove tools from a proxy
                success = tools_controller.remove_tools_from_proxy(
                    operation['proxy_id'],
                    operation['tool_names']
                )
                # Show confirmation
                if success:
                    st.success(f"Tools removed from CurriedProxy successfully.")
                else:
                    st.error("Failed to remove tools from CurriedProxy.")
            
            elif operation['type'] == 'rename_proxy':
                # Rename a proxy
                success = tools_controller.rename_proxy(
                    operation['proxy_id'],
                    operation['new_name']
                )
                # Show confirmation
                if success:
                    st.success(f"CurriedProxy renamed successfully.")
                else:
                    st.error("Failed to rename CurriedProxy.")
            
            elif operation['type'] == 'create_toolset':
                # Execute the operation
                toolset_id = tools_controller.add_tools_to_task_toolset(
                    operation['task_id'],
                    operation['toolset_name'],
                    operation['tool_names']
                )
                # Show confirmation
                if toolset_id:
                    st.success(f"Toolset created with ID: {toolset_id}")
                else:
                    st.error("Failed to create toolset.")
        
        # Clear the operations list
        st.session_state.pending_operations = []
    
    # Render the component
    component = TaskToolRelationshipComponent(persistence_model, tools_controller)
    component.render() 