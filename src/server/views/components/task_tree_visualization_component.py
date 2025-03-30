"""
Component for visualizing task trees in Streamlit.

This component provides an interactive visualization of task trees, 
showing hierarchical relationships, data flow, and plugin integrations.
"""

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, Any, List, Optional
import uuid
import io
import base64
import logging
import time
import json
import asyncio
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ...controllers.task_runner import TaskRunner
from ..utils.async_utils import run_async_sync

logger = logging.getLogger(__name__)

class TaskTreeVisualizationComponent:
    """Component for visualizing task trees in Streamlit."""
    
    def __init__(self, persistence_model=None):
        """Initialize the component."""
        self.persistence_model = persistence_model
        self.plugin_colors = {
            "crewai": "#4CAF50",     # Green
            "autogen": "#2196F3",    # Blue
            "smolagents": "#FF9800", # Orange
            "default": "#9E9E9E"     # Gray
        }
    
    def render(self, tree_id: str = None, tasksmanager_id: str = None):
        """Render the task tree visualization."""
        if not self.persistence_model:
            st.error("Persistence model not available")
            return
            
        # Safely check if the collection_exists method is available
        has_collection_method = hasattr(self.persistence_model, 'collection_exists')
            
        # Get task tree metadata
        tree_metadata = None
        try:
            # Only check collection if the method exists
            if tree_id and has_collection_method and self.persistence_model.collection_exists("task_trees"):
                tree_metadata = self.persistence_model.collection("task_trees").read(tree_id)
            
            # If no tree_id provided or metadata not found, try to find by tasksmanager_id
            if not tree_metadata and tasksmanager_id:
                if has_collection_method and self.persistence_model.collection_exists("task_trees"):
                    # Try to find a tree with matching tasksmanager_id in any task
                    for tree_item_id in self.persistence_model.collection("task_trees").list():
                        tree_data = self.persistence_model.collection("task_trees").read(tree_item_id)
                        if tree_data and 'root_task_id' in tree_data:
                            root_task = self.persistence_model.tasks.read(tree_data['root_task_id'])
                            if root_task and root_task.tasksmanager_id == tasksmanager_id:
                                tree_metadata = tree_data
                                tree_id = tree_item_id
                                break
        except Exception as e:
            st.error(f"Error accessing task tree collection: {str(e)}")
            # Continue with dynamic tree generation
        
        # If still no metadata, build from tasks
        if not tree_metadata and tasksmanager_id:
            # Get all tasks for the tasksmanager
            tasks = self._get_tasks_by_manager_id(tasksmanager_id)
            
            # Find root tasks (no parent_id)
            root_tasks = [t for t in tasks if not hasattr(t, 'parent_id') or not t.parent_id]
            
            if root_tasks:
                # Use the first root task
                root_task = root_tasks[0]
                tree_id = f"dynamic_tree_{tasksmanager_id}"
                tree_metadata = {
                    "name": f"Task Tree for {root_task.name}",
                    "description": "Dynamically generated task tree",
                    "root_task_id": root_task.id,
                    "execution_strategy": "sequential",
                    "plugins": list(set([getattr(t, 'plugin', 'default') for t in tasks if hasattr(t, 'plugin')]))
                }
        
        if not tree_metadata:
            st.warning("No task tree found")
            return
            
        # Display tree information
        st.subheader(tree_metadata["name"])
        st.write(tree_metadata["description"])
        
        # Get execution metadata if available
        execution_metadata = None
        try:
            if tree_id and has_collection_method and self.persistence_model.collection_exists("task_tree_executions"):
                # Find execution metadata for this tree
                for exec_id in self.persistence_model.collection("task_tree_executions").list():
                    exec_data = self.persistence_model.collection("task_tree_executions").read(exec_id)
                    if exec_data and exec_data.get('task_tree_id') == tree_id:
                        execution_metadata = exec_data
                        break
        except Exception as e:
            st.warning(f"Error accessing execution metadata: {str(e)}")
            # Continue without execution metadata
        
        # Create graph
        G = nx.DiGraph()
        
        # Get all tasks
        root_task_id = tree_metadata.get('root_task_id')
        if not root_task_id:
            st.error("No root task ID specified in tree metadata")
            return
            
        root_task = self.persistence_model.tasks.read(root_task_id)
        if not root_task:
            st.error(f"Root task {root_task_id} not found")
            return
            
        # Get all tasks for the tasksmanager
        all_tasks = self._get_tasks_by_manager_id(root_task.tasksmanager_id)
        
        # Build tree structure
        task_nodes = {}
        for task in all_tasks:
            # Determine node color based on plugin
            plugin = getattr(task, 'plugin', 'default')
            node_color = self.plugin_colors.get(plugin, self.plugin_colors['default'])
            
            # Add node to graph
            G.add_node(
                task.id, 
                name=task.name, 
                description=task.description,
                plugin=plugin,
                color=node_color
            )
            task_nodes[task.id] = task
            
            # Add parent-child edges
            parent_id = getattr(task, 'parent_id', None)
            if parent_id and parent_id in task_nodes:
                G.add_edge(parent_id, task.id, type='hierarchy', style='solid')
            
            # Add dependency edges
            input_from = getattr(task, 'input_from_tasks', [])
            if input_from:
                for input_task_id in input_from:
                    if input_task_id in task_nodes:
                        # Check if edge already exists to avoid duplicates
                        if not G.has_edge(input_task_id, task.id):
                            G.add_edge(input_task_id, task.id, type='data', style='dashed')
        
        # Create visualization
        st.write("### Task Tree Structure")
        
        # Create plot
        plt.figure(figsize=(12, 8))
        
        # Use graphviz_layout if available for better hierarchical layout
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except:
            # Fall back to spring layout if graphviz is not available
            pos = nx.spring_layout(G, seed=42)
        
        # Draw nodes with plugin colors
        node_colors = [G.nodes[n]['color'] for n in G.nodes()]
        nx.draw_networkx_nodes(
            G, pos, 
            node_color=node_colors, 
            node_size=1500, 
            alpha=0.8
        )
        
        # Draw edges with different styles for hierarchy vs data flow
        hierarchy_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'hierarchy']
        data_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'data']
        
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=hierarchy_edges,
            edge_color='black', 
            arrows=True, 
            arrowsize=20,
            width=2,
            style='solid'
        )
        
        nx.draw_networkx_edges(
            G, pos,
            edgelist=data_edges,
            edge_color='blue',
            arrows=True,
            arrowsize=15,
            width=1.5,
            style='dashed'
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            G, pos, 
            labels={n: G.nodes[n]['name'] for n in G.nodes()},
            font_size=10,
            font_weight='bold'
        )
        
        # Add legend
        legend_patches = []
        for plugin, color in self.plugin_colors.items():
            if plugin in tree_metadata.get('plugins', []) or plugin == 'default':
                legend_patches.append(mpatches.Patch(color=color, label=plugin))
        
        # Add edge type legend
        legend_patches.append(plt.Line2D([0], [0], color='black', lw=2, label='Hierarchy'))
        legend_patches.append(plt.Line2D([0], [0], color='blue', lw=2, linestyle='--', label='Data Flow'))
        
        plt.legend(handles=legend_patches, loc='upper right')
        plt.axis('off')
        plt.title("Task Tree Visualization")
        
        # Save the plot to a buffer and display with st.image
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        st.image(buf, use_column_width=True)
        
        # Display execution information if available
        if execution_metadata:
            st.write("### Execution Flow")
            st.write("Execution order:")
            
            for idx, item in enumerate(execution_metadata.get('execution_order', [])):
                if isinstance(item, list):
                    # Parallel tasks
                    parallel_names = []
                    for task_id in item:
                        task = self.persistence_model.tasks.read(task_id)
                        if task:
                            parallel_names.append(task.name)
                    st.write(f"{idx+1}. Parallel: {', '.join(parallel_names)}")
                else:
                    # Sequential task
                    task = self.persistence_model.tasks.read(item)
                    if task:
                        st.write(f"{idx+1}. {task.name}")
            
            # Display data flow
            if 'data_flow' in execution_metadata:
                st.write("### Data Flow")
                for flow in execution_metadata['data_flow']:
                    from_task = self.persistence_model.tasks.read(flow['from'])
                    to_task = self.persistence_model.tasks.read(flow['to'])
                    if from_task and to_task:
                        st.write(f"- **{from_task.name}** → **{to_task.name}**: {flow.get('data_type', 'Data')}")

        # Add plugin integration details
        st.write("### Plugin Integration")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Plugins in Use")
            for plugin in tree_metadata.get('plugins', []):
                color = self.plugin_colors.get(plugin, self.plugin_colors['default'])
                st.markdown(f"<div style='background-color:{color}30; padding:5px; border-left:5px solid {color};'>{plugin}</div>", unsafe_allow_html=True)
            
        with col2:
            st.write("#### Plugin Tasks")
            for plugin in tree_metadata.get('plugins', []):
                plugin_tasks = [t for t in all_tasks if getattr(t, 'plugin', None) == plugin]
                if plugin_tasks:
                    st.write(f"**{plugin}**:")
                    for task in plugin_tasks:
                        st.write(f"- {task.name}")
    
    def _get_tasks_by_manager_id(self, tasksmanager_id: str) -> List[Any]:
        """Get all tasks for a task manager."""
        try:
            if not self.persistence_model:
                return []
            
            return [t for t in self.persistence_model.tasks.list() 
                   if t.tasksmanager_id == tasksmanager_id]
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
            
    def render_sequence(self, tasksmanager_id: str, sequence_id: str):
        """Render a visual representation of a task sequence.
        
        Args:
            tasksmanager_id: ID of the task manager
            sequence_id: ID of the sequence to visualize
        """
        try:
            # Get TasksManager
            tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                st.error(f"TasksManager not found: {tasksmanager_id}")
                return
            
            # Get sequence - ensure proper attribute name access
            if hasattr(tasksmanager, 'task_sequences') and sequence_id in tasksmanager.task_sequences:
                sequence = tasksmanager.task_sequences[sequence_id]
            else:
                st.error(f"Sequence not found: {sequence_id}")
                return
            
            # Get tasks
            tasks = []
            for task_id in sequence.task_ids:
                task = self.persistence_model.tasks.read(task_id)
                if task:
                    tasks.append(task)
            
            # Render sequence diagram
            st.subheader(f"Sequence: {sequence.name}")
            st.write(f"**Description:** {sequence.description}")
            
            # Render sequence flow
            if tasks:
                # Draw boxes for each task with arrows between them
                html = """
                <style>
                .sequence-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 20px;
                }
                .sequence-flow {
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    overflow-x: auto;
                    padding: 10px;
                    width: 100%;
                }
                .task-box {
                    min-width: 150px;
                    max-width: 200px;
                    padding: 10px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    margin: 0 5px;
                    text-align: center;
                    background-color: #f9f9f9;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                }
                .task-box:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .arrow {
                    font-size: 24px;
                    margin: 0 5px;
                    color: #666;
                    display: flex;
                    align-items: center;
                }
                .arrow::after {
                    content: "";
                    height: 2px;
                    width: 20px;
                    background-color: #666;
                    margin-left: 5px;
                }
                .plugin-crewai { border-left: 4px solid #4CAF50; }
                .plugin-autogen { border-left: 4px solid #2196F3; }
                .plugin-smolagents { border-left: 4px solid #FF9800; }
                .plugin-default { border-left: 4px solid #9E9E9E; }
                </style>
                
                <div class="sequence-container">
                    <div class="sequence-flow">
                """
                
                # Add task boxes with arrows
                for i, task in enumerate(tasks):
                    # Determine plugin class
                    plugin_class = "plugin-default"
                    if hasattr(task, 'plugin'):
                        plugin_class = f"plugin-{task.plugin}"
                    
                    # Add task box
                    html += f"""
                    <div class="task-box {plugin_class}">
                        <div><b>{task.name}</b></div>
                        <div style="font-size: 0.8em; color: #666;">{task.id[:8]}...</div>
                    </div>
                    """
                    
                    # Add arrow if not the last task
                    if i < len(tasks) - 1:
                        html += '<div class="arrow">→</div>'
                
                html += """
                    </div>
                </div>
                """
                
                # Render HTML
                st.markdown(html, unsafe_allow_html=True)
                
                # Add run button
                if st.button("Run Sequence", key=f"run_vis_seq_{sequence_id}"):
                    with st.spinner("Running sequence..."):
                        try:
                            # Initialize task runner
                            task_runner = TaskRunner(self.persistence_model)
                            
                            # Set the controller if available
                            if hasattr(self, 'controller') and self.controller:
                                task_runner._controller = self.controller
                            
                            # Initialize runner in a synchronous wrapper
                            run_async_sync(task_runner.initialize())
                            
                            # Check if we have messages in session_state to pass as context
                            initial_context = None
                            if hasattr(st, "session_state") and hasattr(st.session_state, "messages"):
                                initial_context = {
                                    'messages': st.session_state.messages
                                }
                                st.info(f"Passing {len(st.session_state.messages)} messages to sequence execution")
                            
                            # Run sequence
                            result = run_async_sync(task_runner.run_task_sequence_by_id(
                                tasksmanager_id, sequence_id, initial_context=initial_context))
                            
                            # Show results
                            st.success("Sequence executed successfully!")
                            
                            # Show execution status
                            status = result.get("execution_status", {})
                            if status:
                                st.json(status)
                        except Exception as e:
                            st.error(f"Error running sequence: {str(e)}")
            else:
                st.warning("No tasks found in this sequence.")
        except Exception as e:
            st.error(f"Error rendering sequence: {str(e)}") 