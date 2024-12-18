# src/server/views/components/sidebar/agentic_config_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType

class AgenticConfigSidebar:
    """Sidebar component for agentic configuration view."""
    
    def __init__(self, controller=None):
        self.controller = controller
    
    async def render(self):
        """Render the agentic configuration sidebar."""
        with st.sidebar:
            st.header("Agentic Frameworks")
            
            # Get state status from controller
            if self.controller and self.controller.local_persistence:
                status = self.controller.view_state.task_status
                print(f"📊 Task status: {status}")
                if status["loaded"]:
                    st.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                    st.markdown("**State:** Agentic Framework loaded")
                else:
                    st.markdown("🔴 State loaded but no task context found")
            else:
                st.markdown("🔴 No framework state loaded")
            
            st.markdown("---")
            
            # Add quick actions at the top
            if st.button("➕ Add New Framework"):
                # TODO: Implement framework creation dialog
                st.info("Framework creation coming soon")
                
            if st.button("🔄 Refresh Frameworks"):
                st.rerun()
                
            st.markdown("---")
            
            # Render frameworks tree as main sidebar content
            st.subheader("Framework Structure")
            if self.controller:
                tree_data = await self.controller.get_agent_tree()
                if tree_data:
                    result = self.controller.tree_component.render(
                        tree_data,
                        key="agentic_tree_sidebar"
                    )
                    if result is None:
                        st.warning("Failed to load framework tree")
                else:
                    st.info("No frameworks available")

# Legacy function for backward compatibility
async def render_agentic_config_sidebar():
    """Legacy function to render the agentic configuration sidebar."""
    if 'agentic_controller' in st.session_state:
        sidebar = AgenticConfigSidebar(st.session_state.agentic_controller)
        await sidebar.render()
    else:
        with st.sidebar:
            st.warning("Agentic controller not initialized")