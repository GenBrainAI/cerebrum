# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
import pandas as pd
from server.views.controllers.task_view_controller import TaskHierarchyController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.tree_component import TreeComponent
from server.views.components.header import render_header
from server.views.components.sidebar.task_hierarchy_sidebar import render_task_hierarchy_sidebar
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from typing import Dict, Any
from server.models.message import Message
from datetime import datetime, timedelta
from server.controllers.task_runner import TaskRunner
from server.views.components.task_management_component import render_task_management

class TaskHierarchyView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TASK_HIERARCHY)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data for persistence"""
        data = super().get_session_data()
        
        # Save chat history
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            data["chat_history"] = st.session_state.task_controller.view_state.chat_history
            data["selected_node"] = st.session_state.task_controller.view_state.selected_node
            data["expanded_nodes"] = st.session_state.task_controller.view_state.expanded_nodes
            data["task_status"] = st.session_state.task_controller.view_state.task_status
            
            # Store task management specific state
            data["selected_task_manager"] = st.session_state.task_controller.view_state.selected_task_manager
            data["selected_task"] = st.session_state.task_controller.view_state.selected_task
            
            # Save active tab
            data["active_tab"] = st.session_state.get("active_tab", 0)
            
        return data
    
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore session state from saved data"""
        super().restore_session_state(session_data)
        
        if "chat_history" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.chat_history = session_data["chat_history"]
            
        if "selected_node" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.selected_node = session_data["selected_node"]
            
        if "expanded_nodes" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.expanded_nodes = session_data["expanded_nodes"]
            
        if "task_status" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.task_status = session_data["task_status"]
            
        # Restore task management specific state
        if "selected_task_manager" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.selected_task_manager = session_data["selected_task_manager"]
            
        if "selected_task" in session_data and hasattr(st.session_state, "task_controller"):
            st.session_state.task_controller.view_state.selected_task = session_data["selected_task"]
            
        # Restore active tab
        if "active_tab" in session_data:
            st.session_state.active_tab = session_data["active_tab"]
    
    def clear_session(self):
        """Clear chat history and other session state"""
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            st.session_state.task_controller.view_state.chat_history = []
            st.session_state.task_controller.view_state.selected_node = None
            st.session_state.task_controller.view_state.expanded_nodes = []
            st.session_state.task_controller.view_state.task_status = {
                "loaded": False,
                "tasksmanager_name": "",
                "task_name": ""
            }
            
            # Clear task management specific state
            st.session_state.task_controller.view_state.selected_task_manager = None
            st.session_state.task_controller.view_state.selected_task = None
            
            # Reset active tab
            st.session_state.active_tab = 0

def render_chat_view():
    """Render the chat interface"""
    st.subheader("Task Interaction")
    
    # Get controller from session state
    if not hasattr(st.session_state, "task_controller"):
        st.warning("Task controller not initialized.")
        return
    
    controller = st.session_state.task_controller
    
    # Check if a task is loaded
    if not controller.view_state.task_status["loaded"]:
        st.info("👈 Please select a task from the sidebar to start chatting.")
        return
    
    # Display task info
    st.markdown(f"**Current Task:** {controller.view_state.task_status['tasksmanager_name']} - {controller.view_state.task_status['task_name']}")
    
    # Display chat history
    for message in controller.view_state.chat_history:
        role = message.get("role", "")
        content = message.get("content", "")
        
        if role == "user":
            st.chat_message("user").write(content)
        elif role == "assistant":
            st.chat_message("assistant").write(content)
    
    # Chat input
    if prompt := st.chat_input("Enter your message"):
        # Add user message to chat history
        st.chat_message("user").write(prompt)
        controller.view_state.add_message("user", prompt)
        
        # TODO: Process user message with the task runner
        
        # Temporary mock response
        response = f"This is a mock response to '{prompt}'. Task processing will be implemented soon."
        
        # Add assistant response to chat history
        st.chat_message("assistant").write(response)
        controller.view_state.add_message("assistant", response)
        
        # Save session state
        view = TaskHierarchyView()
        view.save_session()
        
        # Force re-render
        st.rerun()

def render_observability_view():
    """Render observability tools"""
    st.subheader("Task Execution Observability")
    
    with st.expander("System Logs", expanded=True):
        st.markdown("""
        #### System Logs
        Monitor the execution of tasks and view any errors or warnings.
        """)
        
        # Mock log data
        log_data = [
            {"timestamp": "2025-03-09 20:30:45", "level": "INFO", "message": "Task initialized"},
            {"timestamp": "2025-03-09 20:30:46", "level": "INFO", "message": "Loading models"},
            {"timestamp": "2025-03-09 20:30:48", "level": "WARNING", "message": "Model loading took longer than expected"},
            {"timestamp": "2025-03-09 20:30:50", "level": "INFO", "message": "Task execution completed"}
        ]
        
        # Display logs in a dataframe
        logs_df = pd.DataFrame(log_data)
        st.dataframe(logs_df, use_container_width=True)
    
    with st.expander("Metrics", expanded=True):
        st.markdown("""
        #### Performance Metrics
        View execution time, token usage, and other metrics.
        """)
        
        # Mock metrics data
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Execution Time", value="1.2s")
        with col2:
            st.metric(label="Token Usage", value="450")
        with col3:
            st.metric(label="Memory Usage", value="128MB")

async def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    try:
        # Initialize view and session state
        view = TaskHierarchyView()
        
        # Initialize persistence model if not in session state
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Initialize task controller if not in session state
        if 'task_controller' not in st.session_state:
            st.session_state.task_controller = TaskHierarchyController(st.session_state.persistence_model)
            await st.session_state.task_controller.initialize()
            
            # Check if we need to create test tasks
            task_managers = st.session_state.task_controller.get_task_managers()
            if not task_managers:
                try:
                    from src.state_setup.tasks import setup_test_tasks
                    setup_test_tasks(st.session_state.persistence_model)
                    st.info("Created demo task managers and tasks for testing")
                except Exception as e:
                    st.warning(f"Failed to create test tasks: {str(e)}")
            
            # Load saved session state
            view.load_session()
        
        # Render header
        render_header("Task Hierarchy")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset view"):
                    view.clear_session()
                    st.rerun()
        
        # Render sidebar
        await render_task_hierarchy_sidebar()
        
        # Add navigation tabs with icons, aligned like in tools catalog view
        col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
        with col1:
            if st.button("💬", help="Switch to chat view", key="main_tab_chat"):
                st.session_state.active_tab = 0
                st.rerun()
        with col3:
            if st.button("📊", help="Switch to observability view", key="main_tab_obs"):
                st.session_state.active_tab = 1
                st.rerun()
        with col4:
            if st.button("⚙️", help="Switch to task management view", key="main_tab_manage"):
                st.session_state.active_tab = 2
                st.rerun()
        
        # Initialize active tab if not set
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
        
        # Chat View (primary view)
        if st.session_state.active_tab == 0:
            render_chat_view()
        
        # Observability View
        elif st.session_state.active_tab == 1:
            render_observability_view()
            
        # Task Management View
        elif st.session_state.active_tab == 2:
            st.subheader("Task Management")
            st.markdown("""
            This view allows you to create, edit, and manage task managers and tasks.
            You can configure task properties like model, description, and system messages.
            """)
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
            
            // Numbered shortcuts for tabs
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key >= '1' && e.key <= '3') {
                e.preventDefault();
                let tabIndex;
                switch(e.key) {
                    case '1': tabIndex = 0; break; // Chat
                    case '2': tabIndex = 1; break; // Observability
                    case '3': tabIndex = 2; break; // Task Management
                }
                
                const tabButtons = [
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_chat"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_obs"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_manage"]')
                ];
                
                if (tabButtons && tabButtons[tabIndex]) {
                    tabButtons[tabIndex].click();
                }
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
        
        # Save session state after rendering
        view.save_session()
    except Exception as e:
        st.error(f"Error in task hierarchy view: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

def main():
    """Main entry point"""
    st.set_page_config(
        page_title="Task Hierarchy - Cerebrum",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Create and run async loop
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    
    try:
        async_loop.run_until_complete(render_task_hierarchy_view())
    finally:
        async_loop.close()

if __name__ == "__main__":
    main()