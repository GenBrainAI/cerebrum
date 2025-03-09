import streamlit as st
import asyncio
import os
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime.uploaded_file_manager import UploadedFile

from server.views.models.view_types import ViewType
from server.views.base_view import BaseView
from server.views.components.header import render_header
from server.views.components.sidebar.task_management_sidebar import render_task_management_sidebar
from server.views.components.task_management_component import render_task_management
from server.views.controllers.task_management_controller import TaskManagementController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.models.message import Message
from server.controllers.task_runner import TaskRunner

class TaskManagementView(BaseView):
    """View for task management."""
    
    def __init__(self):
        super().__init__(ViewType.TASK_MANAGEMENT)
        
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data for persistence."""
        data = super().get_session_data()
        
        # Save task controller state
        if 'task_controller' in st.session_state:
            # Store any relevant view state
            controller = st.session_state.task_controller
            if hasattr(controller, 'view_state'):
                data['selected_task_manager'] = controller.view_state.selected_task_manager
                data['selected_task'] = controller.view_state.selected_task
                
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore session state from data."""
        super().restore_session_state(session_data)
        
        if not session_data:
            return
            
        # Only restore if controller exists
        if 'task_controller' in st.session_state:
            controller = st.session_state.task_controller
            
            # Restore view state
            if hasattr(controller, 'view_state'):
                if 'selected_task_manager' in session_data:
                    controller.view_state.selected_task_manager = session_data['selected_task_manager']
                    
                if 'selected_task' in session_data:
                    controller.view_state.selected_task = session_data['selected_task']
                    
    def clear_session(self):
        """Clear the session state."""
        if 'task_controller' in st.session_state:
            # Reset view state
            controller = st.session_state.task_controller
            if hasattr(controller, 'view_state'):
                controller.view_state.selected_task_manager = None
                controller.view_state.selected_task = None

def render_chat_view():
    """Render chat functionality."""
    st.markdown("### Chat")
    st.info("Chat functionality will be integrated here.")
    
def render_observability_view():
    """Render observability links."""
    st.sidebar.markdown("## Observability")
    
    with st.sidebar.expander("System Logs", expanded=False):
        st.markdown("""
        Logs are stored in the `logs` directory:
        - `cerebrum.log`: Main application log
        - `streamlit.log`: Streamlit-specific log
        """)
        
        # Add button to show logs
        if st.button("Show Recent Logs"):
            try:
                log_path = Path("logs/cerebrum.log")
                if log_path.exists():
                    with open(log_path, "r") as f:
                        log_content = f.readlines()
                        # Show last 20 lines
                        st.code("".join(log_content[-20:]), language="text")
                else:
                    st.warning("Log file not found.")
            except Exception as e:
                st.error(f"Error reading logs: {str(e)}")
                
    # Add link to API documentation
    st.sidebar.markdown("## API Documentation")
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    st.sidebar.markdown(f"[API Docs]({api_url}/docs)")
    
    # Add version info
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("cerebrum").version
        st.sidebar.markdown(f"Version: {version}")
    except:
        st.sidebar.markdown("Version: development")

async def render_task_management_view():
    """Render the task management view."""
    try:
        # Initialize view and session state
        view = TaskManagementView()
        
        # Initialize persistence model if not in session state
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Initialize task controller if not in session state
        if 'task_controller' not in st.session_state:
            st.session_state.task_controller = TaskManagementController(st.session_state.persistence_model)
            await st.session_state.task_controller.initialize()
            
            # Load saved session state
            view.load_session()
        
        # Render header
        render_header("Task Management")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset view"):
                    view.clear_session()
                    st.rerun()
        
        # Render sidebar
        await render_task_management_sidebar()
        
        # Render observability view in sidebar
        render_observability_view()
        
        # Render main content
        render_task_management(st.session_state.task_controller)
        
        # Handle keyboard shortcuts
        st.markdown("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            // Ctrl+Shift+R or Cmd+Shift+R to reset
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'r') {
                e.preventDefault();
                const resetButton = doc.querySelector('button[data-testid="stButton"]:has-text("🔄")');
                if (resetButton) resetButton.click();
            }
        });
        </script>
        """, unsafe_allow_html=True)
        
        # Auto-scroll to bottom
        st.markdown("""
        <script>
        const elements = parent.document.querySelectorAll('.stMarkdown');
        const lastElement = elements[elements.length - 1];
        lastElement.scrollTop = lastElement.scrollHeight;
        </script>
        """, 
        unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Error in task management view: {str(e)}")
        logging.exception("Error in task management view")

def main():
    """Main function to run the task management view."""
    st.set_page_config(
        page_title="Task Management - Cerebrum",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Run the async app
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    
    # Add Streamlit context to the event loop
    add_script_run_ctx(async_loop)
    
    try:
        # Run the main rendering function
        async_loop.run_until_complete(render_task_management_view())
    finally:
        async_loop.close()

if __name__ == "__main__":
    main() 