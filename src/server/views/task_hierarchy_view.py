import streamlit as st
import logging
import asyncio
from ..controllers.task_runner import TaskRunner
from .controllers.task_view_controller import TaskHierarchyController
from .components.task_management_component import TaskManagementComponent
from .components.task_tree_visualization_component import TaskTreeVisualizationComponent
from .components.task_tree_handover_component import TaskTreeHandoverComponent
from .utils.async_utils import run_async_sync

# Add task sequence components import
from .components.task_sequence_component import TaskSequenceComponent

def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    st.title("Task Hierarchy")
    
    # Initialize controller
    controller = TaskHierarchyController()
    
    # Create tabs
    tree_tab, management_tab, sequences_tab = st.tabs(["Task Tree", "Task Management", "Task Sequences"])
    
    with tree_tab:
        # Tree component
        tree_component = TaskTreeVisualizationComponent(controller.global_persistence)
        tree_component.render()
    
    with management_tab:
        # Management component
        management_component = TaskManagementComponent(controller)
        management_component.render()
    
    with sequences_tab:
        # Get task managers
        task_managers = controller.get_task_managers()
        
        if not task_managers:
            st.info("No task managers available. Create a task manager first.")
            return
        
        # Select task manager
        selected_manager = st.selectbox(
            "Select Task Manager",
            options=[tm.id for tm in task_managers],
            format_func=lambda x: next((tm.name for tm in task_managers if tm.id == x), x),
            key="sequence_view_manager_selector"
        )
        
        # Render sequences for selected manager
        if selected_manager:
            st.subheader("Task Sequences")
            
            # Get sequences for this manager
            try:
                sequences = run_async_sync(
                    controller.get_task_sequences(selected_manager)
                )
                
                if not sequences:
                    st.info("No sequences defined for this task manager. Create one in the Task Management tab.")
                else:
                    # Select sequence to view
                    selected_sequence = st.selectbox(
                        "Select Sequence",
                        options=[seq["id"] for seq in sequences],
                        format_func=lambda x: next((seq["name"] for seq in sequences if seq["id"] == x), x),
                        key="sequence_viewer_selector"
                    )
                    
                    if selected_sequence:
                        # Render sequence visualization
                        tree_component = TaskTreeVisualizationComponent(controller.global_persistence)
                        tree_component.render_sequence(selected_manager, selected_sequence)
                
            except Exception as e:
                st.error(f"Error loading sequences: {str(e)}") 