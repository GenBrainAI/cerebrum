import streamlit as st
import asyncio
from src.server.views.controllers.agentic_view_controller import AgenticViewController
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.views.components.header import render_header
from src.server.views.components.sidebar.agentic_config_sidebar import render_agentic_config_sidebar
from src.server.views.base_view import BaseView
from src.server.views.models.view_types import ViewType
from typing import Dict, Any
from src.server.models.message import Message
from src.server.controllers.task_runner import TaskRunner

class AgenticConfigView(BaseView):
    def __init__(self):
        super().__init__(ViewType.AGENTIC_CONFIG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get agentic config specific session data."""
        data = super().get_session_data()
        
        if 'agentic_controller' in st.session_state:
            chat_history = st.session_state.agentic_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        
        data.update({
            'chat_history': st.session_state.agentic_controller.view_state.chat_history
            if 'agentic_controller' in st.session_state else [],
            'view_mode': st.session_state.get('view_mode', 'chat'),
            'active_tab': st.session_state.get('active_tab', 0)
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore agentic config specific session state."""
        super().restore_session_state(session_data)
        
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        
        st.session_state.view_mode = session_data.get('view_mode', 'chat')
        st.session_state.active_tab = session_data.get('active_tab', 0)
        
        if 'agentic_controller' in st.session_state:
            st.session_state.agentic_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the agentic config session data."""
        if 'agentic_controller' in st.session_state:
            # Clear chat history
            st.session_state.agentic_controller.view_state.chat_history = []
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared agentic config session")

def render_chat_view():
    """Render the chat interface."""
    # Display messages
    for msg in st.session_state.agentic_controller.view_state.chat_history:
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
        
        asyncio.run(st.session_state.agentic_controller.handle_chat(prompt))
        st.rerun()

def render_observability_view():
    """Render the observability interface."""
    if 'agentic_controller' not in st.session_state:
        st.warning("No active agentic controller")
        return
        
    # Get active task from controller's view state
    task_status = st.session_state.agentic_controller.view_state.task_status
    if not task_status or not task_status.get("loaded"):
        st.info("No active task loaded")
        return
        
    task_id = task_status.get("task_id")
    if not task_id:
        st.info("No task ID available")
        return
        
    # Initialize task runner if needed
    if not hasattr(st.session_state.agentic_controller, 'task_runner'):
        st.session_state.agentic_controller.task_runner = TaskRunner(st.session_state.agentic_controller.global_persistence)
        
    # Get observability manager
    observability = st.session_state.agentic_controller.task_runner.get_task_observability(task_id)
    
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
        entries = observability.get_all_entries()
        stats_entries = [e for e in entries if e.get('metadata', {}).get('execution_stats')]
        
        if stats_entries:
            latest_stats = stats_entries[-1]['metadata']['execution_stats']
            st.json(latest_stats)
        else:
            st.info("No execution stats available")
            
    with col2:
        st.subheader("Execution Output")
        
        # Get all entries
        entries = observability.get_all_entries()
        
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

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    try:
        # Add custom CSS for plugin explorer
        st.markdown("""
        <style>
        .plugin-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
        }

        .plugin-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .status-badge {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }

        .active-badge {
            background-color: #d4edda;
            color: #155724;
        }

        .inactive-badge {
            background-color: #f8d7da;
            color: #721c24;
        }

        .capabilities-list li {
            margin-bottom: 5px;
        }

        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Initialize view and session state
        view = AgenticConfigView()
        
        # Initialize persistence model if not in session state
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Initialize agentic controller if not in session state
        if 'agentic_controller' not in st.session_state:
            st.session_state.agentic_controller = AgenticViewController(st.session_state.persistence_model)
            await st.session_state.agentic_controller.initialize()
            
            # Load saved session state
            view.load_session()
        
        # Render header
        render_header("Agentic Framework")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset chat history"):
                    view.clear_session()
                    st.rerun()
        
        # Render sidebar
        await render_agentic_config_sidebar()
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["💬 Chat", "🧩 Plugin Explorer", "📊 Observability"])
        
        # Chat View
        with tab1:
            st.subheader("Agentic Framework Chat")
            render_chat_view()
        
        # Plugin Explorer View
        with tab2:
            from src.server.views.components.plugin_explorer_component import PluginExplorerComponent
            
            if 'agentic_controller' in st.session_state and hasattr(st.session_state.agentic_controller, 'plugin_manager'):
                plugin_explorer = PluginExplorerComponent(st.session_state.agentic_controller.plugin_manager)
                plugin_explorer.render()
            else:
                st.warning("Plugin manager not initialized")
        
        # Observability View
        with tab3:
            st.subheader("Agentic Framework Observability")
            render_observability_view()
            
        # Save session after view is rendered
        view.save_session()
        
    except Exception as e:
        st.error(f"Error rendering agentic config view: {str(e)}")
        print(f"Error in render_agentic_config_view: {str(e)}")
        raise

def main():
    """Main function to run the view."""
    st.set_page_config(
        page_title="Agentic Framework",
        page_icon="🧠",
        layout="wide"
    )
    
    asyncio.run(render_agentic_config_view())

if __name__ == "__main__":
    main()
