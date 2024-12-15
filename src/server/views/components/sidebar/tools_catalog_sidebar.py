# src/server/views/components/sidebar/tools_catalog_sidebar.py
import streamlit as st
from ...models.view_state import ViewState

class ToolsCatalogSidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    def render(self):
        """Render tools catalog sidebar."""
        st.subheader("Tools Catalog")
        
        # Add new tool button
        if st.button("New Tool", use_container_width=True):
            self.view_state.show_dialog = True
            self.view_state.dialog_type = "new_tool"
        
        # Tool categories
        st.markdown("---")
        st.subheader("Categories")
        
        categories = ["API Tools", "Local Tools", "Custom Tools"]
        selected = st.selectbox("Filter by Category", ["All"] + categories)
        
        # Import section
        st.markdown("---")
        st.subheader("Import Tools")
        
        if st.button("Import OpenAPI", use_container_width=True):
            st.text_input("OpenAPI URL")
            st.file_uploader("Or upload OpenAPI file", type=["json", "yaml"])

def render_tools_catalog_sidebar():
    """Render sidebar content for tools catalog view."""
    if 'tools_sidebar' not in st.session_state:
        st.session_state.tools_sidebar = ToolsCatalogSidebar(
            st.session_state.tools_controller.view_state
        )
    st.session_state.tools_sidebar.render()