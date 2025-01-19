import streamlit as st
from typing import Optional, Dict, Any
from ...models.tools_descriptors import ToolType
from ...models.toolset import Tool

class ToolDialog:
    """Dialog for adding/configuring tools."""
    
    def __init__(self, view_state, persistence_model):
        self.view_state = view_state
        self.persistence_model = persistence_model
    
    def render(self) -> Optional[Tool]:
        """Render the tool dialog.
        
        Returns:
            Tool object if created, None otherwise
        """
        with st.form("tool_dialog"):
            st.subheader("Add New Tool")
            
            # Basic tool info
            name = st.text_input("Tool Name", help="Name of the tool")
            description = st.text_area("Description", help="Description of what the tool does")
            
            # Tool type selection
            tool_type = st.selectbox(
                "Tool Type",
                options=[t.value for t in ToolType],
                help="Type of tool to create"
            )
            
            # Additional fields based on tool type
            extra_fields = {}
            if tool_type == ToolType.API_TOOL.value:
                extra_fields["base_url"] = st.text_input(
                    "Base URL",
                    help="Base URL for API endpoints"
                )
                extra_fields["auth_type"] = st.selectbox(
                    "Authentication Type",
                    options=["None", "Bearer", "Basic", "API Key"],
                    help="Type of authentication required"
                )
                if extra_fields["auth_type"] != "None":
                    extra_fields["auth_key"] = st.text_input(
                        "Authentication Key",
                        type="password",
                        help="Authentication key or token"
                    )
            
            elif tool_type == ToolType.FUNCTION_TOOL.value:
                extra_fields["code"] = st.text_area(
                    "Function Code",
                    help="Python code for the function"
                )
                extra_fields["parameters"] = st.text_area(
                    "Parameters (one per line)",
                    help="Function parameters, one per line"
                )
            
            elif tool_type == ToolType.UTILITY_TOOL.value:
                extra_fields["command"] = st.text_input(
                    "Command",
                    help="Command to execute"
                )
                extra_fields["working_dir"] = st.text_input(
                    "Working Directory",
                    help="Working directory for the command"
                )
            
            # Submit button
            submitted = st.form_submit_button("Add Tool")
            
            if submitted:
                if not name:
                    st.error("Tool name is required")
                    return None
                
                try:
                    # Create tool object
                    tool = Tool(
                        name=name,
                        description=description,
                        tool_type=tool_type,
                        metadata=extra_fields
                    )
                    
                    # Save to persistence
                    created_tool = self.persistence_model.tools.create(tool)
                    return created_tool
                    
                except Exception as e:
                    st.error(f"Error creating tool: {str(e)}")
                    return None
        
        return None 