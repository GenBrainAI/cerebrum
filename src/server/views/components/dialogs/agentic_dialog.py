import streamlit as st
from typing import Optional, Dict, Any, List, Callable
from uuid import UUID

from ....models.agent import Agentic
from ...models.view_state import ViewState
from ..tree_component import TreeComponent

class AgenticDialog:
    """Dialog component for agentic configuration."""
    
    def __init__(self, on_save: Callable[[Agentic], None], on_cancel: Callable[[], None]):
        self.on_save = on_save
        self.on_cancel = on_cancel
        
    def render(self, state: ViewState, agentic: Optional[Agentic] = None):
        """Render the agentic configuration dialog."""
        # Render form in main area
        with st.container():
            with st.form("agentic_config_form"):
                # Basic agentic info
                name = st.text_input("Agentic Name", value=agentic.name if agentic else "")
                description = st.text_area("Description", value=agentic.description if agentic else "")
                
                # Role configuration
                st.subheader("Role Configuration")
                role_name = st.text_input(
                    "Role Name",
                    value=agentic.role.name if agentic and agentic.role else ""
                )
                role_description = st.text_area(
                    "Role Description",
                    value=agentic.role.description if agentic and agentic.role else ""
                )
                
                # Capabilities and permissions
                capabilities = st.text_area(
                    "Capabilities (one per line)",
                    value="\n".join(agentic.role.capabilities) if agentic and agentic.role else ""
                )
                permissions = st.text_area(
                    "Permissions (one per line)",
                    value="\n".join(agentic.role.permissions) if agentic and agentic.role else ""
                )
                
                # Advanced configuration
                with st.expander("Advanced Configuration"):
                    config_json = st.text_area(
                        "Configuration (JSON)",
                        value=str(agentic.config) if agentic else "{}"
                    )
                
                # Form actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Save"):
                        try:
                            # Create or update agentic
                            if not agentic:
                                agentic = Agentic(name=name, description=description)
                            else:
                                agentic.name = name
                                agentic.description = description
                            
                            # Update role
                            agentic.set_role(
                                name=role_name,
                                description=role_description,
                                capabilities=capabilities.split("\n") if capabilities else [],
                                permissions=permissions.split("\n") if permissions else []
                            )
                            
                            # Update config if provided
                            if config_json and config_json != "{}":
                                try:
                                    import json
                                    config = json.loads(config_json)
                                    agentic.update_config(config)
                                except json.JSONDecodeError:
                                    st.error("Invalid JSON configuration")
                                    return
                            
                            self.on_save(agentic)
                            
                        except Exception as e:
                            st.error(f"Error saving agentic: {str(e)}")
                
                with col2:
                    if st.form_submit_button("Cancel"):
                        self.on_cancel() 