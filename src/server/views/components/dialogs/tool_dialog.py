import streamlit as st
from typing import Optional, Dict, Any
from ...models.view_state import ViewState

class ToolDialog:
    """Dialog for adding and configuring tools."""
    
    def __init__(self, view_state: ViewState, persistence_model):
        self.view_state = view_state
        self.persistence_model = persistence_model
        
    def render(self) -> Optional[Dict[str, Any]]:
        """Render tool configuration dialog."""
        st.subheader("Tool Configuration")
        
        # Tool type selection
        tool_type = st.selectbox(
            "Tool Type",
            ["OpenAPI", "Python Function", "System Command"],
            key="tool_type"
        )
        
        # Basic info
        name = st.text_input("Tool Name", key="tool_name")
        description = st.text_area("Description", key="tool_description")
        
        # Type-specific configuration
        if tool_type == "OpenAPI":
            spec_url = st.text_input("OpenAPI Spec URL", key="spec_url")
            auth_type = st.selectbox(
                "Authentication Type",
                ["None", "API Key", "OAuth2"],
                key="auth_type"
            )
            
        elif tool_type == "Python Function":
            module_path = st.text_input("Module Path", key="module_path")
            function_name = st.text_input("Function Name", key="function_name")
            
        elif tool_type == "System Command":
            command = st.text_input("Command Template", key="command")
            working_dir = st.text_input("Working Directory", key="working_dir")
            
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save", use_container_width=True):
                if name:
                    tool_data = {
                        "name": name,
                        "type": tool_type,
                        "description": description
                    }
                    
                    # Add type-specific data
                    if tool_type == "OpenAPI":
                        tool_data.update({
                            "spec_url": spec_url,
                            "auth_type": auth_type
                        })
                    elif tool_type == "Python Function":
                        tool_data.update({
                            "module_path": module_path,
                            "function_name": function_name
                        })
                    elif tool_type == "System Command":
                        tool_data.update({
                            "command": command,
                            "working_dir": working_dir
                        })
                        
                    return tool_data
                else:
                    st.error("Tool name is required")
                    
        with col2:
            if st.button("Cancel", use_container_width=True):
                return None
