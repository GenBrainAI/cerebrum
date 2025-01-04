import streamlit as st
from typing import Optional, Dict, Any, List
from ...models.view_state import ViewState

class ConfigDialog:
    """Dialog for managing agentic configurations."""
    
    def __init__(self, view_state: ViewState, persistence_model):
        self.view_state = view_state
        self.persistence_model = persistence_model
        
    def render(self) -> Optional[Dict[str, Any]]:
        """Render configuration dialog."""
        st.subheader("Agent Configuration")
        
        # Basic info
        name = st.text_input("Configuration Name", key="config_name")
        description = st.text_area("Description", key="config_description")
        
        # Framework selection
        framework = st.selectbox(
            "Framework",
            ["CrewAI", "AutoGen", "LangGraph"],
            key="framework"
        )
        
        # Agent roles
        st.subheader("Agent Roles")
        roles = self._render_roles_section()
        
        # Workflow configuration
        st.subheader("Workflow")
        workflow = self._render_workflow_section(roles)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save", use_container_width=True):
                if name and roles:
                    config_data = {
                        "name": name,
                        "description": description,
                        "framework": framework,
                        "roles": roles,
                        "workflow": workflow
                    }
                    return config_data
                else:
                    st.error("Name and at least one role are required")
                    
        with col2:
            if st.button("Cancel", use_container_width=True):
                return None
                
    def _render_roles_section(self) -> List[Dict[str, Any]]:
        """Render the agent roles configuration section."""
        roles = []
        
        # Add role button
        if st.button("Add Role"):
            st.session_state.role_count = st.session_state.get('role_count', 0) + 1
            
        # Role entries
        for i in range(st.session_state.get('role_count', 0)):
            with st.expander(f"Role {i+1}", expanded=True):
                role_name = st.text_input("Role Name", key=f"role_name_{i}")
                role_description = st.text_area("Description", key=f"role_desc_{i}")
                role_model = st.selectbox(
                    "Model",
                    ["gpt-4o-mini", "gpt-3.5-turbo", "claude-3"],
                    key=f"role_model_{i}"
                )
                
                if role_name:
                    roles.append({
                        "name": role_name,
                        "description": role_description,
                        "model": role_model
                    })
                    
        return roles
        
    def _render_workflow_section(self, roles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Render the workflow configuration section."""
        workflow = {}
        
        # Workflow type
        workflow_type = st.selectbox(
            "Workflow Type",
            ["Sequential", "Parallel", "Dynamic"],
            key="workflow_type"
        )
        
        # Role ordering
        if roles:
            role_names = [role["name"] for role in roles]
            workflow["sequence"] = st.multiselect(
                "Role Sequence",
                role_names,
                key="role_sequence"
            )
            
        workflow["type"] = workflow_type
        return workflow
