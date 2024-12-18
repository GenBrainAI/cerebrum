# src/server/views/components/sidebar/tools_catalog_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType

class ToolsCatalogSidebar:
    """Sidebar component for tools catalog view."""
    
    def __init__(self, controller=None):
        self.controller = controller
    
    async def render(self):
        """Render the tools catalog sidebar."""
        with st.sidebar:
            st.header("Tools Catalog")
            
            # Get state status from controller
            if self.controller and self.controller.local_persistence:
                status = self.controller.view_state.task_status
                if status["loaded"]:
                    st.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                    st.markdown("**State:** Tools Management loaded")
                else:
                    st.markdown("🔴 State loaded but no task context found")
            else:
                st.markdown("🔴 No tools state loaded")
            
            st.markdown("---")
            
            # Add quick actions at the top
            if st.button("➕ Add New Tool"):
                # TODO: Implement tool creation dialog
                st.info("Tool creation coming soon")
                
            if st.button("🔄 Refresh Catalog"):
                st.rerun()
                
            st.markdown("---")
            
            # Render tools catalog tree as main sidebar content
            st.subheader("Tools Catalog")
            if self.controller:
                tree_data = await self.controller.get_tools_tree()
                if tree_data:
                    result = self.controller.tree_component.render(
                        tree_data,
                        key="tools_tree_sidebar"
                    )
                    if result is None:
                        st.warning("Failed to load tools catalog")
                else:
                    st.info("No tools available")

# Legacy function for backward compatibility
async def render_tools_catalog_sidebar():
    """Legacy function to render the tools catalog sidebar."""
    if 'tools_controller' in st.session_state:
        sidebar = ToolsCatalogSidebar(st.session_state.tools_controller)
        await sidebar.render()
    else:
        with st.sidebar:
            st.warning("Tools controller not initialized")