# src/server/views/components/sidebar/tools_catalog_sidebar.py
import streamlit as st
from ...models.view_state import ViewState
from ...models.view_types import ViewType
from .utils import truncate_tree_node_names
import json
import aiohttp

class ToolsCatalogSidebar:
    """Sidebar component for tools catalog view."""
    
    def __init__(self, controller=None):
        self.controller = controller
        
        # Initialize save status in session state if not exists
        if 'save_status' not in st.session_state:
            st.session_state.save_status = None
        if 'last_save_time' not in st.session_state:
            st.session_state.last_save_time = None
    
    async def render(self):
        """Render the tools catalog sidebar."""
        with st.sidebar:
            st.header("Tools Catalog")
            
            # Get state status from controller
            if self.controller and self.controller.local_persistence:
                status = self.controller.view_state.task_status
                if status["loaded"]:
                    # Show state status with save indicator
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"🟢 **Active Task:** {status['tasksmanager_name']}-{status['task_name']}")
                    with col2:
                        import time
                        if st.session_state.save_status == "pending":
                            st.markdown("💾 *Saving...*")
                        elif st.session_state.save_status == "saved" and st.session_state.last_save_time:
                            time_diff = time.time() - st.session_state.last_save_time
                            if time_diff < 5:  # Show saved status for 5 seconds
                                st.markdown("✅ *Saved*")
                            else:
                                st.session_state.save_status = None
                    
                    st.markdown("**State:** Tools Management loaded")
                else:
                    st.markdown("🔴 State loaded but no task context found")
            else:
                st.markdown("🔴 No tools state loaded")
            
            st.markdown("---")
            
            # Add OpenAPI Spec Upload Section (Collapsible)
            with st.expander("➕ Add OpenAPI Tools", expanded=False):
                # Tool Name and Description
                tool_name = st.text_input("Tool Name", key="tool_name")
                tool_description = st.text_area("Description", key="tool_description", height=100)
                
                # Security Selection (None as default)
                security_type = st.selectbox(
                    "Security Type",
                    options=["None", "Bearer Token", "API Key"],
                    index=0,  # Set None as default
                    key="security_type",
                    help="Select 'None' for internal APIs that don't require authentication"
                )
                
                # Security Key Input (disabled for None)
                security_key = st.text_input(
                    "Security Token/Key",
                    type="password",
                    key="security_key",
                    disabled=security_type == "None",
                    help="Disabled when security type is None"
                ) if security_type != "None" else None
                
                # File Upload
                uploaded_file = st.file_uploader(
                    "Upload OpenAPI Spec",
                    type=["yaml", "json"],
                    key="openapi_spec"
                )
                
                # Process Upload Button
                if st.button("Add Tools", key="process_upload"):
                    if not tool_name:
                        st.error("Tool name is required")
                    elif not tool_description:
                        st.error("Tool description is required")
                    elif security_type != "None" and not security_key:
                        st.error("Security token/key is required when security type is not None")
                    elif not uploaded_file:
                        st.error("Please upload an OpenAPI spec file")
                    else:
                        try:
                            # Prepare credentials based on security type
                            credentials = (
                                {"auth_type": "None"} if security_type == "None"
                                else {
                                    "auth_type": "Bearer" if security_type == "Bearer Token" else "ApiKey",
                                    "auth_key": security_key
                                }
                            )
                            
                            # Read file content
                            spec_content = uploaded_file.read().decode()
                            
                            # Prepare form data
                            form_data = {
                                "name": tool_name,
                                "description": tool_description,
                                "credentials": json.dumps(credentials),
                                "swagger_str": spec_content
                            }
                            
                            # Make API call to create toolset
                            async with aiohttp.ClientSession() as session:
                                async with session.post(
                                    "http://localhost:8000/toolsets",
                                    data=form_data
                                ) as response:
                                    if response.status == 201:
                                        st.success("Tools added successfully!")
                                        # Force refresh of the tree
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to add tools: {await response.text()}")
                        except Exception as e:
                            st.error(f"Error processing upload: {str(e)}")
            
            st.markdown("---")
            
            # Render tools catalog tree as main sidebar content
            st.subheader("Available Tools")
            if self.controller:
                tree_data = await self.controller.get_tools_tree()
                if tree_data:
                    # Apply smart name truncation
                    truncate_tree_node_names(tree_data)
                    
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