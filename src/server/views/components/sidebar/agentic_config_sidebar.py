# src/server/views/components/sidebar/agentic_config_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType

class AgenticConfigSidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    async def render(self):
        """Render agentic configuration sidebar."""
        st.sidebar.subheader("Agentic Framework")
        
        # Get state status from controller
        controller = st.session_state.agentic_controller
        if controller.local_persistence:
            status = controller.view_state.task_status
            if status["loaded"]:
                st.sidebar.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                st.sidebar.markdown("**State:** Agentic Framework loaded")
            else:
                st.sidebar.markdown("🔴 State loaded but no task context found")
        else:
            st.sidebar.markdown("🔴 No framework state loaded")
        
        st.sidebar.markdown("---")
        
        # Show frameworks tree
        if hasattr(st.session_state, 'agent_tree'):
            try:
                tree_data = await st.session_state.agentic_controller.get_agent_tree()
                if tree_data:
                    with st.sidebar:
                        st.session_state.agent_tree.render(tree_data)
                else:
                    st.sidebar.info("No frameworks configured in current state")
            except Exception as e:
                st.sidebar.error(f"Error loading frameworks: {str(e)}")

async def render_agentic_config_sidebar():
    """Render sidebar content for agentic configuration view."""
    if 'agentic_sidebar' not in st.session_state:
        st.session_state.agentic_sidebar = AgenticConfigSidebar(
            st.session_state.agentic_controller.view_state
        )
    
    with st.sidebar:
        st.session_state.current_view = ViewType.AGENTIC_CONFIG
        await st.session_state.agentic_sidebar.render()