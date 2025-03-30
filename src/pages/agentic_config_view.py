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
import subprocess
import os
from pathlib import Path

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
        
        # Ensure active_tab is valid
        active_tab = st.session_state.get('active_tab', 0)
        if not isinstance(active_tab, int) or active_tab < 0 or active_tab > 3:
            active_tab = 0  # Default to chat if invalid
            st.session_state.active_tab = active_tab
        
        print(f"📝 Saving active_tab: {active_tab}")
        
        data.update({
            'chat_history': st.session_state.agentic_controller.view_state.chat_history
            if 'agentic_controller' in st.session_state else [],
            'view_mode': st.session_state.get('view_mode', 'chat'),
            'active_tab': active_tab
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore agentic config specific session state."""
        super().restore_session_state(session_data)
        
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        
        active_tab = session_data.get('active_tab', 0)
        view_mode = session_data.get('view_mode', 'chat')
        
        print(f"📖 Restoring active tab: {active_tab}")
        
        # Ensure active_tab is valid
        if not isinstance(active_tab, int) or active_tab < 0 or active_tab > 3:
            active_tab = 0  # Default to chat if invalid
        
        # Set session state values
        st.session_state.view_mode = view_mode
        st.session_state.active_tab = active_tab
        
        if 'agentic_controller' in st.session_state:
            st.session_state.agentic_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the agentic config session data."""
        if 'agentic_controller' in st.session_state:
            # Clear chat history
            st.session_state.agentic_controller.view_state.chat_history = []
            
            # Reset active tab to Chat
            st.session_state.active_tab = 0
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared agentic config session")
            print("🔄 Reset to Chat tab")

def render_chat_view():
    """Render the chat interface."""
    st.subheader("💬 Agentic Framework Chat")
    
    # Check if controller is initialized
    if 'agentic_controller' not in st.session_state:
        st.warning("Agentic controller not initialized.")
        return
        
    # Display messages using standard chat components
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
        
        st.chat_message(role).write(content)
    
    # Chat input with unique key
    if prompt := st.chat_input("Type your message...", key="agentic_config_chat_input"):
        # Add user message to chat history
        st.chat_message("user").write(prompt)
        
        # Process the message
        try:
            # Use asyncio.run to handle the async function
            asyncio.run(st.session_state.agentic_controller.handle_chat(prompt))
            st.rerun()
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

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

        .button-tab {
            width: 100%;
            text-align: center;
            padding: 0.5rem 0;
            border-radius: 0.5rem;
        }

        .button-tab:hover {
            background-color: rgba(128, 128, 128, 0.1);
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
        
        # Initialize active tab if not in session state or ensure it's valid
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0  # Default to chat
        elif not isinstance(st.session_state.active_tab, int) or st.session_state.active_tab < 0 or st.session_state.active_tab > 3:
            # Reset to chat if active_tab is invalid
            st.session_state.active_tab = 0
        
        # Render header
        render_header("Agentic Configuration")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.3, 0.7])
            with col1:
                if st.button("🔄", help="Reset session and clear chat history"):
                    view.clear_session()
                    st.session_state.active_tab = 0  # Reset to chat tab
                    st.rerun()
        
        # Render sidebar - use async function
        await render_agentic_config_sidebar()
        
        # Add navigation tabs with icons, similar to task hierarchy view
        col1, col2, col3, col4 = st.columns([0.25, 0.25, 0.25, 0.25])
        with col1:
            if st.button("💬 Chat", help="Switch to chat view", key="main_tab_chat", use_container_width=True):
                st.session_state.active_tab = 0
                st.rerun()
        with col2:
            if st.button("🧩 Plugins", help="Switch to plugin explorer", key="main_tab_plugins", use_container_width=True):
                st.session_state.active_tab = 1
                st.rerun()
        with col3:
            if st.button("📓 Notebooks", help="Switch to notebooks view", key="main_tab_notebooks", use_container_width=True):
                st.session_state.active_tab = 2
                st.rerun()
        with col4:
            if st.button("📊 Observability", help="Switch to observability view", key="main_tab_obs", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
                
        # Highlight active tab with a custom style
        active_tab_style = """
        <style>
        div[data-testid="column"]:nth-child({}) button {{
            background-color: rgba(0, 104, 201, 0.1);
            border-color: #0068c9;
            border-style: solid;
            border-width: 1px;
        }}
        </style>
        """.format(st.session_state.active_tab + 1)
        st.markdown(active_tab_style, unsafe_allow_html=True)
        
        st.write("---")  # Add separator

        # Chat View (default)
        if st.session_state.active_tab == 0:
            render_chat_view()
            
        # Plugin Explorer View
        elif st.session_state.active_tab == 1:
            from src.server.views.components.plugin_explorer_component import PluginExplorerComponent
            
            # Render plugin explorer
            plugin_explorer = PluginExplorerComponent(st.session_state.agentic_controller.plugin_manager)
            plugin_explorer.render()
            
        # Notebooks View
        elif st.session_state.active_tab == 2:
            st.subheader("Notebooks")
            
            # Add notebook tabs
            demo_tab, browse_tab, create_tab = st.tabs(["Demo Notebooks", "Browse Notebooks", "Create Notebook"])
            
            with demo_tab:
                st.write("## Demo Notebooks")
                st.markdown("""
                Select a demo notebook to explore Cerebrum's capabilities:
                """)
                
                notebook_options = {
                    "Plugin Handover Demo": "notebooks/plugin_handover_demo.ipynb",
                    "Task Tree Example": "notebooks/task_tree_example.ipynb",
                    "Weather Example": "notebooks/weather-example.ipynb"
                }
                
                selected_notebook = st.selectbox(
                    "Select a demo notebook:", 
                    list(notebook_options.keys())
                )
                
                if selected_notebook:
                    notebook_path = notebook_options[selected_notebook]
                    from src.server.views.components.notebook_viewer_component import NotebookViewerComponent
                    notebook_viewer = NotebookViewerComponent()
                    notebook_viewer.render(notebook_path)
                
            with browse_tab:
                st.write("## Browse Notebooks")
                # Implementation for browsing notebooks
                
            with create_tab:
                st.write("## Create Notebook")
                # Implementation for creating notebooks
            
        # Observability View
        elif st.session_state.active_tab == 3:
            render_observability_view()
            
        # Add keyboard shortcuts for tabs
        st.markdown("""
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            // Numbered shortcuts for tabs
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                let tabIndex;
                switch(e.key) {
                    case '1': tabIndex = 0; break; // Chat
                    case '2': tabIndex = 1; break; // Plugins
                    case '3': tabIndex = 2; break; // Notebooks
                    case '4': tabIndex = 3; break; // Observability
                }
                
                const tabButtons = [
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_chat"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_plugins"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_notebooks"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_obs"]')
                ];
                
                if (tabButtons[tabIndex]) {
                    tabButtons[tabIndex].click();
                }
            }
        });
        </script>
        """, unsafe_allow_html=True)
        
        # Save session state after rendering
        view.save_session()
    except Exception as e:
        st.error(f"Error in agentic config view: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

def main():
    """Main function to run the view."""
    st.set_page_config(
        page_title="Agentic Framework",
        page_icon="🧠",
        layout="wide"
    )
    
    # Initialize active_tab if not in session state
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0  # Default to chat
        print("📝 Setting default active_tab to 0 (Chat)")
    else:
        print(f"📝 Current active_tab: {st.session_state.active_tab}")
    
    asyncio.run(render_agentic_config_view())

if __name__ == "__main__":
    main()
