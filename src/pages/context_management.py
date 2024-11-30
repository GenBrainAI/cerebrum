import os
import sys
from pathlib import Path
import streamlit as st

# Add project root to Python path to enable imports
project_root = str(Path(__file__).parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.server.context.context_ui import render_context_manager, ContextManagerUI
from src.chat import initialize_session_state, render_logo

def render_context_page():
    """Render the context management page."""
    st.set_page_config(
        page_title="Context Management - Cerebrum", 
        layout="wide",
        menu_items={
            'Get Help': 'https://github.com/GenBrainAI/cerebrum',
            'About': 'Cerebrum Context Management System'
        }
    )
    initialize_session_state()

    # Initialize context manager if not already in session state
    if 'context_manager' not in st.session_state:
        st.session_state.context_manager = ContextManagerUI()
    
    # Header section
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        render_logo(width=150)
        st.title("Context Management System")
        
        with st.expander("About Context Management", expanded=False):
            st.markdown("""
            ### Context Management System
            
            This interface provides tools to:
            - Index and analyze code repositories
            - Manage and explore domain knowledge
            - Configure context system parameters
            - Monitor system performance
            
            Use the sidebar controls to manage your context and knowledge base.
            """)
    
    st.divider()
    
    # Main content
    try:
        render_context_manager()
    except Exception as e:
        st.error(f"Error rendering context manager: {str(e)}")
        st.error("Please check the logs for more details.")
        
    # System status in sidebar
    with st.sidebar:
        st.subheader("System Status")
        if st.session_state.get('context_manager'):
            stats = st.session_state.context_manager.get_statistics()
            st.success("✅ Context System Active")
            st.metric("Indexed Files", stats.get("total_files", 0))
            st.metric("Knowledge Entries", stats.get("total_entries", 0))
        else:
            st.warning("⚠️ Context System Initializing")
            
        st.divider()
        
        # Navigation
        if st.button("Return to Chat", use_container_width=True):
            try:
                st.switch_page("src/chat.py")
            except Exception as e:
                st.error(f"Error navigating to chat: {str(e)}")
                if st.button("Try Again"):
                    st.rerun()

def main():
    """Main entry point for the context management page."""
    try:
        render_context_page()
    except Exception as e:
        st.error("Error initializing context management page")
        st.error(str(e))
        if st.button("Retry"):
            st.rerun()

if __name__ == "__main__":
    main()
