# src/pages/task_hierarchy_view.py
import streamlit as st
import asyncio
import pandas as pd
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.views.components.tree_component import TreeComponent
from src.server.views.components.header import render_header
from src.server.views.components.sidebar.task_hierarchy_sidebar import render_task_hierarchy_sidebar
from src.server.views.components.task_handover_component import TaskHandoverComponent
from src.server.views.components.task_tree_handover_component import TaskTreeHandoverComponent
from src.server.views.components.handover_info_component import HandoverInfoComponent
from src.server.views.base_view import BaseView
from src.server.views.models.view_types import ViewType
from typing import Dict, Any
from src.server.models.message import Message
from datetime import datetime, timedelta
from src.server.controllers.task_runner import TaskRunner
from src.server.views.components.task_management_component import render_task_management
from src.chat import get_last_used_state, get_state_dir, load_state
from pathlib import Path

class TaskHierarchyView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TASK_HIERARCHY)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get session data for persistence"""
        data = super().get_session_data()
        
        # Save chat history
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            task_status = st.session_state.task_controller.view_state.task_status
            print(f"📝 Saving task status to session: {task_status}")
            
            data["chat_history"] = st.session_state.task_controller.view_state.chat_history
            data["selected_node"] = st.session_state.task_controller.view_state.selected_node
            data["expanded_nodes"] = st.session_state.task_controller.view_state.expanded_nodes
            data["task_status"] = task_status
            
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
            # Ensure all required fields are present in task_status
            task_status = session_data["task_status"]
            print(f"📝 Restoring task status from session: {task_status}")
            
            if task_status and isinstance(task_status, dict):
                # Make sure all required fields are present
                if "loaded" in task_status:
                    # If loaded is True, ensure all required fields are present
                    if task_status.get("loaded", False):
                        print(f"📝 Task status has loaded=True, checking required fields")
                        required_fields = ["task_id", "task_name", "tasksmanager_id", "tasksmanager_name"]
                        missing_fields = [field for field in required_fields if field not in task_status]
                        
                        if missing_fields:
                            print(f"📝 Missing required fields in task_status: {missing_fields}")
                            # If any required field is missing, set loaded to False
                            task_status["loaded"] = False
                            task_status["tasksmanager_name"] = task_status.get("tasksmanager_name", "")
                            task_status["task_name"] = task_status.get("task_name", "")
                        else:
                            print(f"📝 All required fields present in task_status")
                    
                    # Update the view state with the validated task_status
                    st.session_state.task_controller.view_state.task_status = task_status
                    print(f"📝 Updated view_state.task_status: {st.session_state.task_controller.view_state.task_status}")
            
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

    def save_session(self):
        """Save the current view session."""
        # First, ensure task_status is properly set
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            task_status = st.session_state.task_controller.view_state.task_status
            if not task_status.get("loaded", False):
                # Try to find a task manager and task to set as active
                task_managers = st.session_state.task_controller.get_task_managers()
                if task_managers:
                    tasks = st.session_state.task_controller.get_tasks(task_managers[0].id)
                    if tasks:
                        print(f"📝 Setting active task before saving session")
                        st.session_state.task_controller.view_state.set_active_task(
                            task_id=tasks[0].id,
                            task_name=tasks[0].name,
                            manager_id=task_managers[0].id,
                            manager_name=task_managers[0].name
                        )
                        print(f"📝 Updated task status before saving: {st.session_state.task_controller.view_state.task_status}")
        
        # Call parent save_session method
        super().save_session()

def render_task_details(controller, task_id):
    """Render details for the selected task."""
    # Get the task
    task = controller.persistence_model.tasks.read(task_id)
    if not task:
        st.warning(f"Task with ID {task_id} not found.")
        return
        
    # Display task details
    st.subheader(f"Task: {task.name}")
    
    # Basic task information
    st.write(f"**Task ID:** {task.id}")
    st.write(f"**Description:** {task.description or 'No description'}")
    
    # Task properties
    with st.expander("Task Properties", expanded=False):
        props = {
            "Model": getattr(task, "model", "Not specified"),
            "Status": getattr(task, "status", "Not specified"),
            "Created": getattr(task, "created_at", "Not specified"),
            "Updated": getattr(task, "updated_at", "Not specified")
        }
        
        for key, value in props.items():
            st.write(f"**{key}:** {value}")
    
    # Task system message
    if hasattr(task, "messages") and task.messages:
        with st.expander("System Message", expanded=False):
            system_messages = [m for m in task.messages if m.role == "system"]
            if system_messages:
                st.code(system_messages[0].content)
            else:
                st.write("No system message defined.")
    
    # Display handover information
    handover_info = HandoverInfoComponent(controller.persistence_model)
    handover_info.render(task_id)

async def render_chat_view():
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
    
    # Display task info with state indicator
    task_status = controller.view_state.task_status
    task_id = task_status.get("task_id")
    
    # Check if this is a specialized state task
    is_specialized = False
    if hasattr(controller, 'local_persistence') and controller.local_persistence:
        try:
            # Try to find this task in specialized state
            specialized_task = controller.local_persistence.tasks.read(task_id)
            if specialized_task:
                is_specialized = True
        except:
            pass
    
    # Display task info with state indicator
    if is_specialized:
        st.markdown(f"**Current Task:** {task_status['tasksmanager_name']} - {task_status['task_name']} (Specialized State)")
    else:
        st.markdown(f"**Current Task:** {task_status['tasksmanager_name']} - {task_status['task_name']} (Global State)")
    
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
        
        # Process user message with the task runner
        # Properly await the chat handling
        try:
            # Directly await the coroutine since we're in an async function
            await controller.handle_chat(prompt)
            
            # Save session state
            view = TaskHierarchyView()
            view.save_session()
            
            # Force re-render
            st.rerun()
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

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

async def render_tree_view(controller):
    """Render the task tree with handover relationships"""
    st.subheader("Task Hierarchy Tree")
    
    # Display info about task hierarchy
    st.info("This view shows the hierarchy of task managers and tasks. "
           "The tree now visualizes handover relationships between tasks.")

    # Get task tree with handover relationships
    task_tree = await controller.get_task_tree_with_handover()
    
    # Initialize tree component with handover visualization
    if "tree_component" not in dir(controller) or not isinstance(controller.tree_component, TaskTreeHandoverComponent):
        controller.tree_component = TaskTreeHandoverComponent(controller.handle_node_click)
    
    # Render tree with relationships
    col1, col2 = st.columns([2, 3])
    with col1:
        # Render tree with handover relationships
        selected_node = controller.tree_component.render(task_tree, "task_tree")
        
        # Handle selection
        if selected_node:
            node_id = selected_node.get("id")
            node_type = selected_node.get("type")
            node_data = selected_node.get("data", {})
            
            # Store selection in controller
            controller.view_state.selected_node = node_id
            
            # Update selected task or task manager based on node type
            if node_type == "task":
                controller.view_state.selected_task = node_data.get("id")
            elif node_type == "tasksmanager":
                controller.view_state.selected_task_manager = node_data.get("id")
            
            # Save session state after node selection
            view = TaskHierarchyView()
            view.save_session()
    
    # Render details for selected node
    with col2:
        if controller.view_state.selected_node:
            selected_id = str(controller.view_state.selected_node)
            
            # Find the selected node in the tree
            found_node = task_tree.find_child(controller.view_state.selected_node)
            
            if found_node:
                if found_node.type == "task":
                    # Render task details including handover information
                    render_task_details(controller, found_node.data.get("id"))
                elif found_node.type == "tasksmanager":
                    # Render task manager details
                    tm_id = found_node.data.get("id")
                    tm = controller.persistence_model.tasksmanagers.read(tm_id)
                    
                    if tm:
                        st.subheader(f"Task Manager: {tm.name}")
                        st.write(f"**ID:** {tm.id}")
                        st.write(f"**Model:** {tm.model or 'Not specified'}")
                        st.write(f"**Description:** {tm.description or 'No description'}")
            else:
                st.info("Select a task or task manager to view details.")
        else:
            st.info("Select a task or task manager to view details.")

async def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    try:
        # Initialize active tab if not set (do this first to prevent the error)
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
            
        # Initialize view and session state
        view = TaskHierarchyView()
        
        # Initialize persistence model if not in session state
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            
            # Only load state if not loaded before
            if 'default_state_loaded' not in st.session_state or not st.session_state.default_state_loaded:
                # Load the last used state if available (reuse logic from chat.py)
                from src.chat import get_last_used_state, get_state_dir, load_state
                from pathlib import Path
                
                # Try to load the last used state
                metadata = get_last_used_state()
                if metadata.get("last_used_state"):
                    state_name = metadata["last_used_state"]
                    if not state_name.endswith('.json'):
                        state_file_name = f"{state_name}.json"
                    else:
                        state_file_name = state_name
                    
                    state_path = str(get_state_dir() / state_file_name)
                    print(f"\n📥 Loading last used state from metadata: {state_path}")
                    
                    if Path(state_path).exists():
                        # Load the state into the persistence model
                        try:
                            load_state(state_path)
                            print(f"✅ Successfully loaded state from {state_path}")
                            
                            # Mark state as loaded to prevent redundant loading
                            st.session_state.default_state_loaded = True
                            
                            # Debug: Check if tasks were loaded properly
                            try:
                                task_count = len(st.session_state.persistence_model.tasks.list())
                                print(f"📊 After loading state, found {task_count} tasks in persistence model")
                                
                                if task_count > 0:
                                    print("📋 Task details:")
                                    for task in st.session_state.persistence_model.tasks.list():
                                        print(f"  - {task.id}: {task.name} - Manager ID: {task.tasksmanager_id}")
                            except Exception as e:
                                print(f"❌ Error checking tasks after state load: {str(e)}")
                        except Exception as e:
                            print(f"❌ Error loading state: {str(e)}")
                    else:
                        print(f"⚠️ Last used state file not found: {state_path}")
            else:
                print(f"✅ State already loaded, skipping load operation")
        
        # Initialize task controller if not in session state
        if 'task_controller' not in st.session_state:
            print("🔄 Creating new task controller")
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
            print("🔄 Loading saved session state")
            view.load_session()
        else:
            print("🔄 Using existing task controller")
            # Ensure controller is using global persistence for UI operations
            if hasattr(st.session_state.task_controller, 'global_persistence'):
                # Always use global persistence for task tree and management
                # This ensures we don't mix specialized state with global state
                if st.session_state.get('active_tab', 0) != 0:  # Not in chat view
                    print("🔄 Ensuring controller uses global persistence for non-chat operations")
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
            
        # Debug task status
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            print(f"🔄 Current task status: {st.session_state.task_controller.view_state.task_status}")
            
            # Fix: Ensure task_status is properly set if it's not already
            task_status = st.session_state.task_controller.view_state.task_status
            if not task_status.get("loaded", False):
                # Try to find a task manager and task to set as active
                # For chat view (tab 0), prefer specialized state task if available
                if st.session_state.get('active_tab', 0) == 0 and hasattr(st.session_state.task_controller, 'local_persistence') and st.session_state.task_controller.local_persistence:
                    print(f"🔄 Setting active task from specialized state for chat view")
                    # Get tasks from specialized state
                    local_task_managers = st.session_state.task_controller.local_persistence.tasksmanagers.list()
                    if local_task_managers:
                        local_task_manager = next(
                            (m for m in local_task_managers if "Task Management" in m.name),
                            local_task_managers[0]
                        )
                        local_tasks = st.session_state.task_controller.local_persistence.tasks.list()
                        local_task = next(
                            (t for t in local_tasks if t.tasksmanager_id == local_task_manager.id),
                            None
                        )
                        if local_task:
                            print(f"🔄 Found specialized task: {local_task.name} for chat functionality")
                            st.session_state.task_controller.view_state.set_active_task(
                                task_id=local_task.id,
                                task_name=local_task.name,
                                manager_id=local_task_manager.id,
                                manager_name=local_task_manager.name
                            )
                            print(f"🔄 Updated task status with specialized task: {st.session_state.task_controller.view_state.task_status}")
                else:
                    # For non-chat views, always use global state tasks
                    task_managers = st.session_state.task_controller.get_task_managers()
                    if task_managers:
                        tasks = st.session_state.task_controller.get_tasks(task_managers[0].id)
                        if tasks:
                            print(f"🔄 Setting active task from global state")
                            st.session_state.task_controller.view_state.set_active_task(
                                task_id=tasks[0].id,
                                task_name=tasks[0].name,
                                manager_id=task_managers[0].id,
                                manager_name=task_managers[0].name
                            )
                            print(f"🔄 Updated task status with global task: {st.session_state.task_controller.view_state.task_status}")
        
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
        print("🔄 Rendering sidebar")
        await render_task_hierarchy_sidebar()
        
        # Add navigation tabs with icons, aligned like in tools catalog view
        col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
        with col1:
            if st.button("💬", help="Switch to chat view", key="main_tab_chat"):
                # When switching to chat view, ensure we're using the specialized state task if available
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "local_persistence") and st.session_state.task_controller.local_persistence:
                    local_task_managers = st.session_state.task_controller.local_persistence.tasksmanagers.list()
                    local_tasks = st.session_state.task_controller.local_persistence.tasks.list()
                    if local_task_managers and local_tasks:
                        local_task_manager = next(
                            (m for m in local_task_managers if "Task Management" in m.name),
                            local_task_managers[0]
                        )
                        local_task = next(
                            (t for t in local_tasks if t.tasksmanager_id == local_task_manager.id),
                            None
                        )
                        if local_task:
                            print(f"🔄 Setting specialized task as active for chat view")
                            st.session_state.task_controller.view_state.set_active_task(
                                task_id=local_task.id,
                                task_name=local_task.name,
                                manager_id=local_task_manager.id,
                                manager_name=local_task_manager.name
                            )
                
                st.session_state.active_tab = 0
                st.rerun()
        with col2:
            if st.button("🌳", help="Switch to tree view", key="main_tab_tree"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 3
                st.rerun()
        with col3:
            if st.button("📊", help="Switch to observability view", key="main_tab_obs"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 1
                st.rerun()
        with col4:
            if st.button("⚙️", help="Switch to task management view", key="main_tab_manage"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 2
                st.rerun()
        
        # Chat View (primary view)
        if st.session_state.active_tab == 0:
            await render_chat_view()
        
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
            
        # Tree View
        elif st.session_state.active_tab == 3:
            await render_tree_view(st.session_state.task_controller)
        
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
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                let tabIndex;
                switch(e.key) {
                    case '1': tabIndex = 0; break; // Chat
                    case '2': tabIndex = 3; break; // Tree View
                    case '3': tabIndex = 1; break; // Observability
                    case '4': tabIndex = 2; break; // Task Management
                }
                
                const tabButtons = [
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_chat"]'),
                    doc.querySelector('button[data-testid="stButton"][key="main_tab_tree"]'),
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