# src/server/views/components/sidebar/task_hierarchy_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType

class TaskHierarchySidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    async def render(self):
        """Render task hierarchy sidebar."""
        st.sidebar.subheader("Task Hierarchy")
        
        # Get state status from controller
        controller = st.session_state.task_controller
        if controller.local_persistence:
            status = controller.view_state.task_status
            if status["loaded"]:
                st.sidebar.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                st.sidebar.markdown("**State:** Task Management loaded")
            else:
                st.sidebar.markdown("🔴 State loaded but no task context found")
        else:
            st.sidebar.markdown("🔴 No task state loaded")
        
        st.sidebar.markdown("---")
        
        # Show task tree
        if hasattr(st.session_state, 'task_tree'):
            try:
                tree_data = await st.session_state.task_controller.get_task_tree()
                if tree_data:
                    with st.sidebar:
                        st.session_state.task_tree.render(tree_data)
                else:
                    st.sidebar.info("No tasks configured in current state")
            except Exception as e:
                st.sidebar.error(f"Error loading tasks: {str(e)}")

async def render_task_hierarchy_sidebar():
    """Render sidebar content for task hierarchy view."""
    if 'task_sidebar' not in st.session_state:
        st.session_state.task_sidebar = TaskHierarchySidebar(
            st.session_state.task_controller.view_state
        )
    
    with st.sidebar:
        st.session_state.current_view = ViewType.TASK_HIERARCHY
        await st.session_state.task_sidebar.render()