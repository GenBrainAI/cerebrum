# src/server/views/components/sidebar/task_hierarchy_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType
import asyncio

class TaskHierarchySidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    def render(self):
        """Render task hierarchy sidebar."""
        st.sidebar.subheader("Task Hierarchy")
        
        # Add new task button
        if st.sidebar.button("New Task", use_container_width=True):
            self.view_state.show_dialog = True
            self.view_state.dialog_type = "new_task"
        
        # Add new group button
        if st.sidebar.button("New Group", use_container_width=True):
            self.view_state.show_dialog = True
            self.view_state.dialog_type = "new_group"
        
        # Show task tree if available
        if hasattr(st.session_state, 'task_tree') and hasattr(st.session_state, 'task_controller'):
            try:
                tree_data = asyncio.run(st.session_state.task_controller.get_task_tree())
                if tree_data:
                    with st.sidebar:
                        st.session_state.task_tree.render(tree_data)
            except Exception as e:
                st.sidebar.error(f"Error loading task tree: {str(e)}")
        
        # Import/Export section
        st.sidebar.markdown("---")
        st.sidebar.subheader("Import/Export")
        
        if st.sidebar.button("Import Tasks", use_container_width=True):
            st.sidebar.file_uploader("Upload Task File", type=["json"])
        
        if st.sidebar.button("Export Tasks", use_container_width=True):
            # TODO: Implement export functionality
            pass

def render_task_hierarchy_sidebar():
    """Render sidebar content for task hierarchy view."""
    # Initialize sidebar if needed
    if 'task_sidebar' not in st.session_state:
        st.session_state.task_sidebar = TaskHierarchySidebar(
            st.session_state.task_controller.view_state
        )
    
    # Ensure we're in the sidebar context
    with st.sidebar:
        # Update view type
        st.session_state.current_view = ViewType.TASK_HIERARCHY
        
        # Render the sidebar
        st.session_state.task_sidebar.render()