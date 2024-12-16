# src/server/views/components/sidebar/tools_catalog_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType

class ToolsCatalogSidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    async def render(self):
        """Render tools catalog sidebar."""
        st.sidebar.subheader("Tools Catalog")
        
        # Get state status from controller
        controller = st.session_state.tools_controller
        if controller.local_persistence:
            status = controller.view_state.task_status
            if status["loaded"]:
                st.sidebar.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                st.sidebar.markdown("**State:** Tools Management loaded")
            else:
                st.sidebar.markdown("🔴 State loaded but no task context found")
        else:
            st.sidebar.markdown("🔴 No tools state loaded")
        
        st.sidebar.markdown("---")
        
        # Show tools tree
        if hasattr(st.session_state, 'tools_tree'):
            try:
                tree_data = await st.session_state.tools_controller.get_tools_tree()
                if tree_data:
                    with st.sidebar:
                        st.session_state.tools_tree.render(tree_data)
                else:
                    st.sidebar.info("No tools configured in current state")
            except Exception as e:
                st.sidebar.error(f"Error loading tools: {str(e)}")

async def render_tools_catalog_sidebar():
    """Render sidebar content for tools catalog view."""
    if 'tools_sidebar' not in st.session_state:
        st.session_state.tools_sidebar = ToolsCatalogSidebar(
            st.session_state.tools_controller.view_state
        )
    
    with st.sidebar:
        st.session_state.current_view = ViewType.TOOLS_CATALOG
        await st.session_state.tools_sidebar.render()