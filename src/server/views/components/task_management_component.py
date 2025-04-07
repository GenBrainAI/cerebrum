import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from ...models.task import Task
from ...models.tasks_manager import TasksManager
from ...models.message import Message
from ...persistence.persistence_model import PersistenceModelBase
from ..controllers.task_view_controller import TaskHierarchyController

class TaskManagementComponent:
    """Component for task and task manager management."""
    
    def __init__(self, controller: TaskHierarchyController):
        self.controller = controller
        
        # Ensure we're using global persistence for task management
        if hasattr(self.controller, 'global_persistence') and hasattr(self.controller, 'persistence_model'):
            if self.controller.persistence_model is not self.controller.global_persistence:
                print("🔧 Switching controller to global persistence in task management component")
                self.controller.persistence_model = self.controller.global_persistence
        
    def render(self):
        """Render the task management component."""
        st.subheader("Task Management")
        
        # Ensure we're using global persistence for task management
        if hasattr(self.controller, 'global_persistence') and hasattr(self.controller, 'persistence_model'):
            if self.controller.persistence_model is not self.controller.global_persistence:
                print("🔧 Switching controller to global persistence in task management render")
                self.controller.persistence_model = self.controller.global_persistence
        
        # Get all task managers and tasks
        task_managers = self.controller.get_task_managers()
        all_tasks = self.controller.get_tasks()
        
        if not task_managers:
            st.warning("No task managers found.")
            st.info("Create a new task manager to get started.")
            self._render_create_task_manager_form()
            return
            
        # Create tabs for different sections
        main_tab1, main_tab2, main_tab3 = st.tabs(["Table View", "Graph View", "Manage Tasks"])
        
        with main_tab1:
            self._render_table_view(task_managers, all_tasks)
            
        with main_tab2:
            self._render_graph_view(task_managers, all_tasks)
            
        with main_tab3:
            self._render_management_view(task_managers, all_tasks)
            
    def _render_table_view(self, task_managers: List[TasksManager], tasks: List[Task]):
        """Render table view of task managers and tasks."""
        st.subheader("Task Managers")
        
        # Create task managers table
        tm_data = []
        for tm in task_managers:
            system_message = self.controller.get_system_message(tm)
            task_count = len([t for t in tasks if t.tasksmanager_id == tm.id])
            
            tm_data.append({
                "ID": tm.id,
                "Name": tm.name,
                "Model": tm.model if tm.model else "Not specified",
                "Description": tm.description if tm.description else "No description",
                "System Message": system_message if system_message else "No system message",
                "Tasks": task_count
            })
            
        if tm_data:
            tm_df = pd.DataFrame(tm_data)
            st.dataframe(tm_df, use_container_width=True)
        else:
            st.info("No task managers data available.")
            
        st.markdown("---")
        st.subheader("Tasks")
        
        # Create tasks table
        task_data = []
        for task in tasks:
            # Find associated task manager
            tm_name = next((tm.name for tm in task_managers if tm.id == task.tasksmanager_id), "Unknown")
            system_message = self.controller.get_system_message(task)
            
            task_data.append({
                "ID": task.id,
                "Name": task.name,
                "Task Manager": tm_name,
                "Model": task.model if task.model else "Not specified",
                "Description": task.description if task.description else "No description",
                "System Message": system_message if system_message else "No system message",
                "Inherit Context": "Yes" if task.inherit_manager_context else "No"
            })
            
        if task_data:
            task_df = pd.DataFrame(task_data)
            st.dataframe(task_df, use_container_width=True)
        else:
            st.info("No tasks data available.")
            
    def _render_graph_view(self, task_managers: List[TasksManager], tasks: List[Task]):
        """Render a graph visualization of task managers and tasks."""
        st.subheader("Task Hierarchy Visualization")
        
        if not task_managers or not tasks:
            st.info("Not enough data to create a visualization.")
            return
            
        # Create graph
        G = nx.DiGraph()
        
        # Add task manager nodes
        for tm in task_managers:
            G.add_node(tm.id, name=tm.name, type="task_manager")
            
        # Add task nodes and edges
        for task in tasks:
            if task.tasksmanager_id:
                G.add_node(task.id, name=task.name, type="task")
                G.add_edge(task.tasksmanager_id, task.id)
                
        # Check if we have a connected graph
        if not G.nodes():
            st.info("No relationships to visualize.")
            return
            
        # Create positions using layout
        pos = nx.spring_layout(G, seed=42)
        
        # Create edge traces
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines')
            
        # Create node traces for task managers and tasks
        tm_node_x = []
        tm_node_y = []
        tm_node_text = []
        
        task_node_x = []
        task_node_y = []
        task_node_text = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_type = G.nodes[node]['type']
            node_name = G.nodes[node]['name']
            
            if node_type == 'task_manager':
                tm_node_x.append(x)
                tm_node_y.append(y)
                tm_node_text.append(f"Task Manager: {node_name}<br>ID: {node}")
            else:
                task_node_x.append(x)
                task_node_y.append(y)
                task_node_text.append(f"Task: {node_name}<br>ID: {node}")
                
        tm_node_trace = go.Scatter(
            x=tm_node_x, y=tm_node_y,
            mode='markers',
            hoverinfo='text',
            text=tm_node_text,
            marker=dict(
                size=20,
                color='#f76707',
                symbol='diamond',
                line_width=2))
                
        task_node_trace = go.Scatter(
            x=task_node_x, y=task_node_y,
            mode='markers',
            hoverinfo='text',
            text=task_node_text,
            marker=dict(
                size=10,
                color='#1f77b4',
                line_width=2))
                
        # Create the figure
        fig = go.Figure(data=[edge_trace, tm_node_trace, task_node_trace],
                      layout=go.Layout(
                          title=dict(
                              text='Task Managers and Tasks Relationship',
                              font=dict(size=16)
                          ),
                          showlegend=False,
                          hovermode='closest',
                          margin=dict(b=20, l=5, r=5, t=40),
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                      )
                      
        st.plotly_chart(fig, use_container_width=True)
        
    def _render_management_view(self, task_managers: List[TasksManager], tasks: List[Task]):
        """Render the management view with task managers and tasks."""
        # Select task manager
        selected_tm = st.selectbox(
            "Select Task Manager",
            options=[tm.id for tm in task_managers],
            format_func=lambda x: next((tm.name for tm in task_managers if tm.id == x), "Unknown")
        )
        
        if selected_tm:
            # Get selected task manager
            selected_tm_obj = next((tm for tm in task_managers if tm.id == selected_tm), None)
            
            # Create tabs for task managers, tasks, and sequences
            mgr_tab, task_tab, seq_tab = st.tabs(["Task Managers", "Tasks", "Sequences"])
            
            with mgr_tab:
                # Render task managers management
                self._render_task_managers_management(task_managers)
                
            with task_tab:
                # Render tasks management
                self._render_tasks_management(task_managers, tasks)
                
            with seq_tab:
                # Render sequences management
                self._render_sequences_management(selected_tm_obj)
                
    def _render_task_managers_management(self, task_managers: List[TasksManager]):
        """Render task managers management section."""
        # Task manager selection
        task_manager_options = {tm.id: f"{tm.name}" for tm in task_managers}
        task_manager_options["new"] = "➕ Create New Task Manager"
        
        selected_tm_id = st.selectbox(
            "Select Task Manager:",
            options=list(task_manager_options.keys()),
            format_func=lambda x: task_manager_options[x],
            key="task_manager_select"
        )
        
        if selected_tm_id == "new":
            # New task manager form
            self._render_create_task_manager_form()
        elif selected_tm_id:
            # Edit existing task manager
            selected_tm = next((tm for tm in task_managers if tm.id == selected_tm_id), None)
            if selected_tm:
                self._render_edit_task_manager_form(selected_tm)
            
    def _render_tasks_management(self, task_managers: List[TasksManager], tasks: List[Task]):
        """Render tasks management section."""
        # Task selection
        if not task_managers:
            st.info("Create a Task Manager first before adding tasks.")
            return
            
        task_options = {task.id: f"{task.name}" for task in tasks}
        task_options["new"] = "➕ Create New Task"
        
        selected_task_id = st.selectbox(
            "Select Task:",
            options=list(task_options.keys()),
            format_func=lambda x: task_options[x],
            key="task_select"
        )
        
        if selected_task_id == "new":
            # New task form
            self._render_create_task_form(task_managers)
        elif selected_task_id:
            # Edit existing task
            selected_task = next((task for task in tasks if task.id == selected_task_id), None)
            if selected_task:
                self._render_edit_task_form(selected_task, task_managers)
            
    def _render_create_task_manager_form(self):
        """Render form to create a new task manager."""
        with st.form("create_task_manager_form"):
            st.subheader("Create New Task Manager")
            
            name = st.text_input("Name", value="New Task Manager")
            description = st.text_area("Description", value="", height=150)
            model = st.selectbox(
                "Model",
                options=[""] + self.controller.view_state.available_models,
                index=0
            )
            system_message = st.text_area("System Message", value="You are a helpful assistant.", height=250)
            
            submitted = st.form_submit_button("Create Task Manager")
            
            if submitted:
                # Clean model value
                model_value = model if model else None
                
                # Create task manager
                result = self.controller.create_task_manager(
                    name=name,
                    description=description,
                    model=model_value,
                    system_message=system_message
                )
                
                if result:
                    st.success(f"Task Manager '{name}' created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create task manager.")
                    
    def _render_edit_task_manager_form(self, task_manager: TasksManager):
        """Render form to edit an existing task manager."""
        with st.form(f"edit_task_manager_form_{task_manager.id}"):
            st.subheader(f"Edit Task Manager: {task_manager.name}")
            
            # Extract system message
            system_message = self.controller.get_system_message(task_manager) or ""
            
            # Form fields
            name = st.text_input("Name", value=task_manager.name)
            description = st.text_area("Description", value=task_manager.description or "", height=150)
            
            # Find the index of the current model in the available models
            model_index = 0
            if task_manager.model:
                try:
                    model_index = self.controller.view_state.available_models.index(task_manager.model) + 1
                except ValueError:
                    model_index = 0
                    
            model = st.selectbox(
                "Model",
                options=[""] + self.controller.view_state.available_models,
                index=model_index
            )
            
            system_msg = st.text_area("System Message", value=system_message, height=250)
            
            # After the description field, add handover options
            st.write("### Task Handover Settings")
            enable_handover = st.checkbox(
                "Enable Task Handover", 
                value=task_manager.enable_handover if task_manager else False,
                help="When enabled, tasks will run in the specified order with outputs from one task feeding into the next."
            )
            
            # Only show task order selection if we're editing an existing task manager
            task_order = []
            if task_manager:
                # Get all tasks for this manager
                tasks = self.controller.get_tasks_for_tasksmanager(task_manager.id)
                if tasks:
                    # Create options for the multiselect
                    task_options = {task.id: task.name for task in tasks}
                    
                    # Get current task order
                    default_selection = task_manager.task_order if hasattr(task_manager, 'task_order') else []
                    
                    # Show a multiselect for ordering tasks
                    st.write("Select tasks and arrange them in execution order:")
                    task_order = st.multiselect(
                        "Task Execution Order",
                        options=list(task_options.keys()),
                        default=default_selection,
                        format_func=lambda x: task_options.get(x, x),
                        help="Tasks will be executed in this order with outputs passed as inputs to the next task."
                    )
                else:
                    st.info("Create tasks first, then set their execution order.")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Update Task Manager")
            with col2:
                delete_button = st.form_submit_button("🗑️ Delete", type="secondary")
                
            if submitted:
                # Clean model value
                model_value = model if model else None
                
                # Update existing task manager
                tasksmanager_id = self.controller.update_tasksmanager(
                    tasksmanager_id=task_manager.id,
                    name=name,
                    description=description,
                    model=model_value,
                    system_message=system_msg,
                    enable_handover=enable_handover,
                    task_order=task_order
                )
                
                if tasksmanager_id:
                    st.success(f"Task Manager '{name}' updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update task manager.")
                    
            if delete_button:
                # Confirm deletion
                confirm = st.checkbox("Confirm deletion of task manager and all associated tasks", key=f"confirm_delete_tm_{task_manager.id}")
                if confirm:
                    result = self.controller.delete_task_manager(task_manager.id)
                    if result:
                        st.success(f"Task Manager '{task_manager.name}' and all associated tasks deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete task manager.")
                else:
                    st.warning("Please confirm deletion by checking the box above.")
                    
    def _render_create_task_form(self, task_managers: List[TasksManager]):
        """Render form to create a new task."""
        with st.form("create_task_form"):
            st.subheader("Create New Task")
            
            name = st.text_input("Name", value="New Task")
            
            # Task manager selection
            tm_options = {tm.id: f"{tm.name}" for tm in task_managers}
            tasksmanager_id = st.selectbox(
                "Task Manager",
                options=list(tm_options.keys()),
                format_func=lambda x: tm_options[x]
            )
            
            description = st.text_area("Description", value="", height=150)
            
            model = st.selectbox(
                "Model",
                options=[""] + self.controller.view_state.available_models,
                index=0
            )
            
            inherit_context = st.checkbox("Inherit Manager Context", value=False)
            
            system_message = st.text_area("System Message", value="You are a helpful assistant.", height=250)
            
            # Add human input toggle
            human_input = st.checkbox("Enable Human Input", 
                                     value=False,
                                     help="Enable human-in-the-loop functionality for this task")
            
            submitted = st.form_submit_button("Create Task")
            
            if submitted and tasksmanager_id:
                # Clean model value
                model_value = model if model else None
                
                # Create task
                result = self.controller.create_task(
                    name=name,
                    tasksmanager_id=tasksmanager_id,
                    description=description,
                    model=model_value,
                    system_message=system_message,
                    inherit_manager_context=inherit_context,
                    human_input=human_input
                )
                
                if result:
                    st.success(f"Task '{name}' created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create task.")
                    
    def _render_edit_task_form(self, task: Task, task_managers: List[TasksManager]):
        """Render form to edit an existing task."""
        with st.form(f"edit_task_form_{task.id}"):
            st.subheader(f"Edit Task: {task.name}")
            
            # Extract system message
            system_message = self.controller.get_system_message(task) or ""
            
            # Form fields
            name = st.text_input("Name", value=task.name)
            
            # Task manager selection
            tm_options = {tm.id: f"{tm.name}" for tm in task_managers}
            
            # Find current task manager index
            tm_index = 0
            if task.tasksmanager_id:
                try:
                    tm_index = list(tm_options.keys()).index(task.tasksmanager_id)
                except ValueError:
                    tm_index = 0
                    
            tasksmanager_id = st.selectbox(
                "Task Manager",
                options=list(tm_options.keys()),
                format_func=lambda x: tm_options[x],
                index=tm_index
            )
            
            description = st.text_area("Description", value=task.description or "", height=150)
            
            # Find the index of the current model in the available models
            model_index = 0
            if task.model:
                try:
                    model_index = self.controller.view_state.available_models.index(task.model) + 1
                except ValueError:
                    model_index = 0
                    
            model = st.selectbox(
                "Model",
                options=[""] + self.controller.view_state.available_models,
                index=model_index
            )
            
            inherit_context = st.checkbox("Inherit Manager Context", value=task.inherit_manager_context)
            
            system_msg = st.text_area("System Message", value=system_message, height=250)
            
            # Add human input toggle
            human_input = st.checkbox("Enable Human Input", 
                                     value=task.human_input if task and hasattr(task, 'human_input') else False,
                                     help="Enable human-in-the-loop functionality for this task")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Update Task")
            with col2:
                delete_button = st.form_submit_button("🗑️ Delete", type="secondary")
                
            if submitted:
                # Clean model value
                model_value = model if model else None
                
                # Update task
                result = self.controller.update_task(
                    task_id=task.id,
                    name=name,
                    tasksmanager_id=tasksmanager_id,
                    description=description,
                    model=model_value,
                    system_message=system_msg,
                    inherit_manager_context=inherit_context
                )
                
                if result:
                    st.success(f"Task '{name}' updated successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to update task '{name}'. Please check the application logs for more details.")
                    # Try to get error details from session state if available
                    if hasattr(st, 'session_state') and hasattr(st.session_state, 'last_error'):
                        st.error(f"Error details: {st.session_state.last_error}")
                    
            if delete_button:
                # Confirm deletion
                confirm = st.checkbox("Confirm deletion of this task", key=f"confirm_delete_task_{task.id}")
                if confirm:
                    result = self.controller.delete_task(task.id)
                    if result:
                        st.success(f"Task '{task.name}' deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete task.")
                else:
                    st.warning("Please confirm deletion by checking the box above.")

    def _render_sequences_management(self, tasksmanager: TasksManager):
        """Render the sequences management view for a task manager."""
        if not tasksmanager:
            st.warning("Please select a task manager to manage sequences.")
            return
        
        st.write(f"### Sequences for: {tasksmanager.name}")
        
        # Import task sequence component
        from .task_sequence_component import TaskSequenceComponent
        
        # Create and render the component
        sequence_component = TaskSequenceComponent(self.controller)
        sequence_component.render(tasksmanager.id)

def render_task_management(controller: TaskHierarchyController):
    """Render the task management component."""
    # Ensure we're using global persistence for task management
    if hasattr(controller, 'global_persistence') and hasattr(controller, 'persistence_model'):
        if controller.persistence_model is not controller.global_persistence:
            print("🔧 Switching controller to global persistence in render_task_management")
            controller.persistence_model = controller.global_persistence
    
    component = TaskManagementComponent(controller)
    component.render() 