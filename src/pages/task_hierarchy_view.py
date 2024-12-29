# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
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

class TaskHierarchyView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TASK_HIERARCHY)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get task hierarchy specific session data."""
        data = super().get_session_data()
        
        # Debug chat history
        if 'task_controller' in st.session_state:
            chat_history = st.session_state.task_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        else:
            print("\n⚠️ No task controller in session state")
        
        # Add view-specific data
        data.update({
            'selected_task': st.session_state.get('selected_task'),
            'expanded_nodes': st.session_state.get('expanded_nodes', []),
            'chat_history': st.session_state.task_controller.view_state.chat_history,
            'view_mode': st.session_state.get('view_mode', 'chat')
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore task hierarchy specific session state."""
        super().restore_session_state(session_data)
        st.session_state.selected_task = session_data.get('selected_task')
        st.session_state.expanded_nodes = session_data.get('expanded_nodes', [])
        st.session_state.view_mode = session_data.get('view_mode', 'chat')
        
        # Debug restored chat history
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        print(f"  Content: {chat_history}")
        
        if 'task_controller' in st.session_state:
            st.session_state.task_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the task hierarchy session data."""
        if 'task_controller' in st.session_state:
            # Clear chat history
            st.session_state.task_controller.view_state.chat_history = []
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared task hierarchy session")

def render_chat_view():
    """Render the chat interface."""
    # Display messages - handle both Message objects and dicts
    for msg in st.session_state.task_controller.view_state.chat_history:
        if isinstance(msg, Message):
            role = msg.role
            content = msg.content
        elif isinstance(msg, dict):
            role = msg["role"]
            content = msg["content"]
        else:
            role = getattr(msg, 'role', 'user')
            content = str(msg)
        
        with st.chat_message(role):
            st.write(content)
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        asyncio.run(st.session_state.task_controller.handle_chat(prompt))
        st.rerun()

def render_observability_view():
    """Render the observability interface."""
    if 'task_controller' not in st.session_state:
        st.warning("No active task controller")
        return
        
    # Get active task from controller's view state
    task_status = st.session_state.task_controller.view_state.task_status
    if not task_status or not task_status.get("loaded"):
        st.info("No active task loaded")
        return
        
    task_id = task_status.get("task_id")
    if not task_id:
        st.info("No task ID available")
        return
        
    # Initialize task runner if needed
    if not hasattr(st.session_state.task_controller, 'task_runner'):
        st.session_state.task_controller.task_runner = TaskRunner(st.session_state.task_controller.global_persistence)
        
    # Get observability manager
    observability = st.session_state.task_controller.task_runner.get_task_observability(task_id)
    
    if not observability:
        st.info("No observability data available for this task")
        return
        
    entries = observability.get_all_entries()
    if not entries:
        st.info("No execution entries available")
        return
        
    # Create columns for stats and output
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Execution Stats")
        stats_entries = [e for e in entries if e.get('metadata', {}).get('execution_stats')]
        
        if stats_entries:
            latest_stats = stats_entries[-1]['metadata']['execution_stats']
            st.json(latest_stats)
        else:
            st.info("No execution stats available")
            
    with col2:
        st.subheader("Execution Output")
        
        # Format entries for display
        formatted_lines = []
        for entry in entries:
            timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
            level = entry['level']
            message = entry['message']
            
            # Color-code based on level
            if level == "ERROR":
                message = f"🔴 {message}"
            elif level == "WARNING":
                message = f"🟡 {message}"
            elif level == "INFO":
                message = f"🟢 {message}"
                
            formatted_lines.append(f"[{timestamp}] {message}")
            
        # Create a scrollable container with auto-scroll
        output_container = st.container()
        with output_container:
            # Calculate max height based on viewport
            st.markdown("""
                <style>
                    .stMarkdown {
                        max-height: 500px;
                        overflow-y: auto;
                    }
                    .stMarkdown::-webkit-scrollbar {
                        width: 10px;
                        background: #f1f1f1;
                    }
                    .stMarkdown::-webkit-scrollbar-thumb {
                        background: #888;
                        border-radius: 5px;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Join lines and add newlines for proper markdown rendering
            formatted_output = "\n".join(formatted_lines)
            
            # Use markdown with code block for monospace font
            st.markdown(f"```\n{formatted_output}\n```")
            
            # Auto-scroll to bottom using JavaScript
            if formatted_lines:
                st.markdown("""
                    <script>
                        const elements = parent.document.querySelectorAll('.stMarkdown');
                        const lastElement = elements[elements.length - 1];
                        lastElement.scrollTop = lastElement.scrollHeight;
                    </script>
                    """, 
                    unsafe_allow_html=True
                )

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
            
            # Load saved session state
            view.load_session()
        
        # Render header
        render_header("Task Hierarchy")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset chat history"):
                    view.clear_session()
                    st.rerun()
        
        # Render sidebar
        await render_task_hierarchy_sidebar()
        
        # Get task tree data
        print("\n🌳 Getting task tree for sidebar...")
        tree_data = await st.session_state.task_controller.get_task_tree()
        if tree_data:
            print(f"Tree data received: {len(tree_data.children)} root children")
            print("✅ Tree rendered successfully")
        
        # Create columns for view controls
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("💬", help="Switch to chat view"):
                st.session_state.active_tab = 0
                st.rerun()
        
        with col2:
            if st.button("📈", help="Switch to observability view"):
                st.session_state.active_tab = 1
                st.rerun()
        
        # Initialize active tab if not set
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
            
        # Chat View
        if st.session_state.active_tab == 0:
            st.subheader("Task Management Chat")
            
            # Display messages
            for msg in st.session_state.task_controller.view_state.chat_history:
                if isinstance(msg, Message):
                    role = msg.role
                    content = msg.content
                elif isinstance(msg, dict):
                    role = msg["role"]
                    content = msg["content"]
                else:
                    role = getattr(msg, 'role', 'user')
                    content = str(msg)
                
                with st.chat_message(role):
                    st.write(content)
            
            # Chat input
            if prompt := st.chat_input("Type your message..."):
                with st.chat_message("user"):
                    st.write(prompt)
                
                await st.session_state.task_controller.handle_chat(prompt)
                
                # Save session after each message
                view.save_session()
                
                st.rerun()
        
        # Observability View
        else:
            st.subheader("Task Execution Observability")
            render_observability_view()
            
    except Exception as e:
        st.error(f"Error rendering task hierarchy view: {str(e)}")
        print(f"Error in render_task_hierarchy_view: {str(e)}")
        raise

def main():
    """Main entry point for task hierarchy view."""
    st.set_page_config(page_title="Task Hierarchy", layout="wide")
    asyncio.run(render_task_hierarchy_view())

if __name__ == "__main__":
    main()