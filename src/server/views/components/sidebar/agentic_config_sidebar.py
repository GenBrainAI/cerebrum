# src/server/views/components/sidebar/agentic_config_sidebar.py
import streamlit as st
from ...models.view_state import ViewState

class AgenticConfigSidebar:
    def __init__(self, view_state: ViewState):
        self.view_state = view_state

    def render(self):
        """Render agentic configuration sidebar."""
        st.subheader("Agent Configuration")
        
        # Add new agent role
        if st.button("New Agent Role", use_container_width=True):
            self.view_state.show_dialog = True
            self.view_state.dialog_type = "new_role"
        
        # Add new workflow
        if st.button("New Workflow", use_container_width=True):
            self.view_state.show_dialog = True
            self.view_state.dialog_type = "new_workflow"
        
        # Configuration templates
        st.markdown("---")
        st.subheader("Templates")
        
        template_type = st.selectbox(
            "Template Type",
            ["Role Templates", "Workflow Templates"]
        )
        
        if template_type == "Role Templates":
            templates = ["Researcher", "Writer", "Analyst", "Custom"]
            selected = st.selectbox("Select Template", templates)
            if selected and st.button("Use Template"):
                self.view_state.show_dialog = True
                self.view_state.dialog_type = "new_role"
                self.view_state.template = selected
        else:
            templates = ["Sequential", "Parallel", "Conditional", "Custom"]
            selected = st.selectbox("Select Template", templates)
            if selected and st.button("Use Template"):
                self.view_state.show_dialog = True
                self.view_state.dialog_type = "new_workflow"
                self.view_state.template = selected
        
        # Import/Export section
        st.markdown("---")
        st.subheader("Import/Export")
        
        if st.button("Import Configuration", use_container_width=True):
            st.file_uploader("Upload Config File", type=["json", "yaml"])
        
        if st.button("Export Configuration", use_container_width=True):
            # TODO: Implement export functionality
            pass

def render_agentic_config_sidebar():
    """Render sidebar content for agentic configuration view."""
    if 'agentic_sidebar' not in st.session_state:
        st.session_state.agentic_sidebar = AgenticConfigSidebar(
            st.session_state.agentic_controller.view_state
        )
    st.session_state.agentic_sidebar.render()