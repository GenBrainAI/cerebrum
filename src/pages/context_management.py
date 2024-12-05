import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.server.context.context_ui import ContextManagerUI

def initialize_context_session():
    """Initialize session state variables."""
    if 'context_view' not in st.session_state:
        st.session_state.context_view = "knowledge"
    if 'context_manager' not in st.session_state:
        st.session_state.context_manager = ContextManagerUI()

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

    initialize_context_session()
    
    try:
        # Get context manager instance
        context_manager = st.session_state.context_manager
        
        # Render the UI
        context_manager.render()
        
    except Exception as e:
        st.error(f"Error rendering context manager: {str(e)}")
        if st.button("Retry"):
            st.rerun()

def main():
    """Main entry point."""
    try:
        render_context_page()
    except Exception as e:
        st.error("Error initializing context management page")
        st.error(str(e))
        if st.button("Retry"):
            st.rerun()

if __name__ == "__main__":
    main()