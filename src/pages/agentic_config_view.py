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
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "🧩 Plugin Explorer", "📓 Notebooks", "📊 Observability"])
        
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
        
        # Notebook View - new
        with tab3:
            st.subheader("Jupyter Notebooks")
            
            from src.server.views.components.notebook_viewer_component import NotebookViewerComponent
            from pathlib import Path
            import json
            import os
            
            notebook_viewer = NotebookViewerComponent()
            
            # Ensure notebooks directory exists
            notebook_dir = Path("notebooks")
            if not notebook_dir.exists():
                notebook_dir.mkdir(parents=True)
            
            # Define predefined demonstration notebooks
            predefined_notebooks = {
                "Plugin Handover Demo": "notebooks/plugin_handover_demo.ipynb",
                "Task Tree Example": "notebooks/task_tree_example.ipynb",
                "Multi-Agent Collaboration": "notebooks/multi_agent_collaboration.ipynb"
            }
            
            # Create a tab section with edit and create options
            browse_tab, create_tab = st.tabs(["Edit Notebook", "Create Notebook"])
            
            # Tab 1: Edit Notebooks (combined predefined and custom)
            with browse_tab:
                # Find all available notebooks
                available_notebooks = list(notebook_dir.glob("*.ipynb"))
                weather_example = Path("notebooks/weather-example.ipynb")
                
                if weather_example.exists() and weather_example not in available_notebooks:
                    available_notebooks.append(weather_example)
                
                if not available_notebooks:
                    st.info("No notebooks found in the notebooks directory. Please create or upload a notebook.")
                else:
                    # Create a dictionary mapping display names to file paths
                    notebook_options = {}
                    
                    # Add predefined notebooks first with special markers
                    for name, path in predefined_notebooks.items():
                        if Path(path).exists():
                            notebook_options[f"📘 {name}"] = str(Path(path).resolve())
                    
                    # Add all other notebooks
                    for notebook_path in available_notebooks:
                        path_str = str(notebook_path.resolve())  # Use resolved absolute path
                        # Skip if already added as predefined
                        if path_str not in notebook_options.values():
                            display_name = notebook_path.stem.replace("_", " ").title()
                            notebook_options[f"📔 {display_name}"] = path_str
                    
                    # Let the user select a notebook
                    selected_notebook = st.selectbox(
                        "Select a notebook to view:", 
                        list(notebook_options.keys()),
                        key="notebook_selector"
                    )
                    
                    selected_path = notebook_options[selected_notebook]
                    # Verify the file exists before proceeding
                    if not Path(selected_path).exists():
                        st.error(f"Cannot find notebook at path: {selected_path}")
                        st.info("The notebook file may have been moved or deleted. Please refresh the page and try again.")
                    else:
                        # Show edit options
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.write("Actions:")
                            # Add button to launch in Jupyter if possible
                            if st.button("🚀 Open in Jupyter", help="Open this notebook in Jupyter if available"):
                                jupyter_url = f"http://localhost:8888/notebooks/{os.path.basename(selected_path)}"
                                st.markdown(f"[Click here to open in Jupyter]({jupyter_url})", unsafe_allow_html=True)
                                st.info(f"If Jupyter is running, you can open the notebook at: {jupyter_url}")
                                st.info("Note: Run `jupyter notebook` in the project directory to enable this link")
                            
                            # Add button to execute the notebook
                            if st.button("▶️ Execute Notebook", help="Execute the notebook and update outputs"):
                                with st.spinner("Executing notebook..."):
                                    try:
                                        result = subprocess.run(
                                            [
                                                "jupyter", "nbconvert", 
                                                "--to", "notebook", 
                                                "--execute",
                                                "--inplace",
                                                selected_path
                                            ], 
                                            capture_output=True, 
                                            text=True
                                        )
                                        if result.returncode == 0:
                                            st.success("Notebook executed successfully!")
                                        else:
                                            st.error(f"Error executing notebook: {result.stderr}")
                                    except Exception as e:
                                        st.error(f"Failed to execute notebook: {str(e)}")
                            
                            # Add download button
                            try:
                                with open(selected_path, "rb") as file:
                                    st.download_button(
                                        label="⬇️ Download Notebook",
                                        data=file,
                                        file_name=os.path.basename(selected_path),
                                        mime="application/x-ipynb+json"
                                    )
                            except Exception as e:
                                st.error(f"Failed to prepare download: {str(e)}")
                        
                        with col2:
                            # Render the selected notebook
                            st.write(f"### {selected_notebook}")
                            st.info(f"Loading notebook from: {selected_path}")
                            notebook_viewer.render(selected_path)
                    
                    # Add a file uploader for notebook files
                    st.divider()
                    st.subheader("Upload Notebook")
                    uploaded_file = st.file_uploader("Upload a notebook file", type=["ipynb"])
                    if uploaded_file is not None:
                        # Save the uploaded file
                        save_path = notebook_dir / uploaded_file.name
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        st.success(f"Notebook uploaded successfully: {uploaded_file.name}")
                        
                        # Option to view the uploaded notebook
                        if st.button("View Uploaded Notebook"):
                            st.write(f"### {uploaded_file.name}")
                            notebook_viewer.render(str(save_path.resolve()))
            
            # Tab 2: Create Notebook
            with create_tab:
                st.subheader("Create a New Notebook")
                
                # Basic notebook creation form
                new_notebook_name = st.text_input("Notebook Name", key="new_notebook_name")
                notebook_type = st.selectbox(
                    "Notebook Type", 
                    ["Empty Notebook", "Plugin Handover Template", "Task Tree Template", "Multi-Agent Collaboration Template"],
                    key="notebook_type"
                )
                
                if st.button("Create Notebook"):
                    if not new_notebook_name:
                        st.error("Please enter a notebook name")
                    else:
                        # Create filename from the provided name
                        filename = new_notebook_name.lower().replace(" ", "_")
                        if not filename.endswith(".ipynb"):
                            filename += ".ipynb"
                        
                        new_notebook_path = notebook_dir / filename
                        
                        # Check if the file already exists
                        if new_notebook_path.exists():
                            st.error(f"A notebook with the name '{filename}' already exists.")
                        else:
                            # Create basic notebook structure based on selected type
                            if notebook_type == "Empty Notebook":
                                notebook_content = {
                                    "cells": [
                                        {
                                            "cell_type": "markdown",
                                            "metadata": {},
                                            "source": [f"# {new_notebook_name}\n\nThis is a sample notebook created with Cerebrum. Use this notebook to explore data, create visualizations, or run experiments."]
                                        },
                                        {
                                            "cell_type": "markdown",
                                            "metadata": {},
                                            "source": ["## Hello World Example\n\nBelow is a simple Python code cell that prints 'Hello World!'."]
                                        },
                                        {
                                            "cell_type": "code",
                                            "execution_count": null,
                                            "metadata": {},
                                            "source": ["# A simple Hello World example\nprint('Hello World!')\n\n# You can add more code here\n# For example:\nimport numpy as np\nimport matplotlib.pyplot as plt"],
                                            "outputs": []
                                        },
                                        {
                                            "cell_type": "markdown",
                                            "metadata": {},
                                            "source": ["## Next Steps\n\nYou can add more cells using the '+' button in the Jupyter interface.\nExperiment with different code examples and markdown documentation."]
                                        }
                                    ],
                                    "metadata": {
                                        "kernelspec": {
                                            "display_name": "Python 3",
                                            "language": "python",
                                            "name": "python3"
                                        },
                                        "language_info": {
                                            "codemirror_mode": {
                                                "name": "ipython",
                                                "version": 3
                                            },
                                            "file_extension": ".py",
                                            "mimetype": "text/x-python",
                                            "name": "python",
                                            "nbconvert_exporter": "python",
                                            "pygments_lexer": "ipython3",
                                            "version": "3.8.10"
                                        }
                                    },
                                    "nbformat": 4,
                                    "nbformat_minor": 5
                                }
                            else:
                                # Determine which template to use based on selection
                                if notebook_type == "Plugin Handover Template":
                                    template_key = "Plugin Handover Demo"
                                elif notebook_type == "Task Tree Template":
                                    template_key = "Task Tree Example"
                                else:  # Multi-Agent Collaboration Template
                                    template_key = "Multi-Agent Collaboration"
                                
                                # Get the content from the predefined demo if it exists
                                template_path = predefined_notebooks[template_key]
                                if Path(template_path).exists():
                                    with open(template_path, 'r') as f:
                                        notebook_content = json.load(f)
                                        
                                    # Update the title to reflect the new notebook name
                                    if notebook_content["cells"][0]["cell_type"] == "markdown":
                                        notebook_content["cells"][0]["source"] = [f"# {new_notebook_name}\n\nBased on the {notebook_type}."]
                                else:
                                    st.error(f"Template '{template_key}' not available. Please ensure demo notebooks exist.")
                                    notebook_content = None
                            
                            # Save the new notebook
                            if notebook_content:
                                with open(new_notebook_path, 'w') as f:
                                    json.dump(notebook_content, f, indent=2)
                                
                                st.success(f"Notebook '{filename}' created successfully!")
                                
                                # Button to view the new notebook
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    if st.button("View New Notebook"):
                                        st.write(f"### {new_notebook_name}")
                                        notebook_viewer.render(str(new_notebook_path))
                                with col2:
                                    jupyter_url = f"http://localhost:8888/notebooks/{os.path.basename(new_notebook_path)}"
                                    st.markdown(f"[Open in Jupyter]({jupyter_url})", unsafe_allow_html=True)
                                    st.info("Run `jupyter notebook` in the project directory to use this link")

            # Add refresh button at the bottom
            if st.button("Refresh Notebooks"):
                st.rerun()
        
        # Observability View
        with tab4:
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
