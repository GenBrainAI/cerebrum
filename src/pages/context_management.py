import streamlit as st
import sys
from pathlib import Path
import asyncio
from src.server.context.context_ui import ContextManagerUI
from src.server.views.components.sidebar.context_mng_sidebar import render_context_mng_sidebar

# Add project root to Python path
project_root = str(Path(__file__).parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)


def initialize_context_session():
    """Initialize session state variables."""
    if 'context_view' not in st.session_state:
        st.session_state.context_view = "knowledge"
    if 'context_manager' not in st.session_state:
        st.session_state.context_manager = ContextManagerUI()

def render_context_page():
    """Render the context management page."""
    initialize_context_session()
    
    try:
        # Get context manager instance
        context_manager = st.session_state.context_manager
        
        # Create new event loop for this thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Define async function to wrap the render calls
        async def render_async():
            try:
                # Render sidebar first
                await render_context_mng_sidebar()
                # Then render main content
                await context_manager.render()
            except Exception as e:
                st.error(f"Error in render: {str(e)}")
        
        # Run the async function
        loop.run_until_complete(render_async())
            
    except Exception as e:
        st.error(f"Error rendering context manager: {str(e)}")
        if st.button("Retry"):
            st.rerun()

def render_repository_list(st, code_catalog):
    """Render the list of repositories with collapse/delete controls."""
    # Get unique repository names from file index
    repos = {
        path.split('/')[0] 
        for path in code_catalog.file_index.keys() 
        if '/' in path
    }
    
    if not repos:
        st.info("No repositories indexed yet")
        return

    # Style for the container
    st.markdown("""
        <style>
        .repo-container {
            display: flex;
            align-items: center;
            padding: 5px;
        }
        .delete-button {
            float: right;
        }
        </style>
    """, unsafe_allow_html=True)
    
    for repo in sorted(repos):
        # Create horizontal container for repo name and delete button
        col1, col2 = st.columns([20, 1])
        
        with col1:
            # Repository expander
            with st.expander(f"📁 {repo}", expanded=False):
                # Get files for this repository
                repo_files = {}
                for path in code_catalog.file_index.keys():
                    if path.startswith(f"{repo}/"):
                        parts = path[len(repo)+1:].split('/')  # Remove repo prefix
                        current = repo_files
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = "file"

                # Recursive function to display the file tree
                def display_tree(tree, prefix=""):
                    for name, content in sorted(tree.items()):
                        if content == "file":
                            st.text(f"{prefix}└── {name}")
                        else:
                            st.text(f"{prefix}├── 📁 {name}")
                            display_tree(content, prefix + "│   ")

                display_tree(repo_files)

        with col2:
            # Delete button
            if st.button("🗑️", key=f"delete_{repo}", help=f"Delete {repo}"):
                if st.warning(f"Delete {repo}?"):
                    if code_catalog.delete_repository(repo):
                        st.success(f"Deleted {repo}")
                        st.rerun()

if __name__ == "__main__":
    render_context_page()
