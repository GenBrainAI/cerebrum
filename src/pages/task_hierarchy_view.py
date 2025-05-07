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
from src.server.views.components.task_management_component import render_task_management
from src.server.views.base_view import BaseView
from src.server.views.models.view_types import ViewType
from typing import Dict, Any
from src.server.models.message import Message
from datetime import datetime, timedelta
from src.server.controllers.task_runner import TaskRunner
from src.chat import get_last_used_state, get_state_dir, load_state
from pathlib import Path
from src.server.views.components.task_tree_visualization_component import TaskTreeVisualizationComponent
from src.server.views.components.task_tree_demo_component import TaskTreeDemoComponent
from src.server.views.components.task_tree_demo_launcher import TaskTreeDemoLauncher
import time

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
    
    # Add an alias method to handle code that expects restore_session
    def restore_session(self):
        """Alias for load_session to maintain backward compatibility.
        Some code may expect this method to exist, so we provide it as an alias to load_session.
        """
        print("📝 Calling restore_session (alias for load_session)")
        return self.load_session()
    
    def clear_session(self):
        """Clear chat history and other session state"""
        print("\n🗑️ TaskHierarchyView: Clearing session")
        
        if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "view_state"):
            # Get the current task information before clearing
            task_status = st.session_state.task_controller.view_state.task_status
            current_task_id = task_status.get("task_id")
            
            # Clear view state and UI state
            st.session_state.task_controller.view_state.chat_history = []
            st.session_state.task_controller.view_state.selected_node = None
            st.session_state.task_controller.view_state.expanded_nodes = []
            
            # If a task is loaded, clear its chat sessions
            if current_task_id and task_status.get("loaded", False):
                try:
                    print(f"🔍 Clearing ALL sessions for task {current_task_id}")
                    
                    # Get the task from the persistence model
                    persistence_model = st.session_state.task_controller.persistence_model
                    task = persistence_model.tasks.read(current_task_id)
                    
                    if task and hasattr(task, 'chat_sessions'):
                        # Create a new empty session 
                        new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # COMPLETELY CLEAR all chat sessions
                        existing_session_count = len(task.chat_sessions) if task.chat_sessions else 0
                        print(f"🧹 Removing {existing_session_count} existing chat sessions")
                        
                        # Replace with a single empty session
                        task.chat_sessions = {new_session_id: []}
                        
                        # Find and clear any tasks with the same name to ensure full cleanup
                        task_name = task.name if hasattr(task, 'name') else ""
                        if task_name:
                            # Look for similar tasks by name
                            all_tasks = persistence_model.tasks.list()
                            for other_task in all_tasks:
                                if other_task.id != current_task_id and hasattr(other_task, 'name') and other_task.name == task_name:
                                    print(f"🧹 Also clearing chat sessions for similar task: {other_task.id}")
                                    if hasattr(other_task, 'chat_sessions'):
                                        other_task.chat_sessions = {}
                                        persistence_model.tasks.update(other_task.id, other_task)
                        
                        # Update the task in the persistence model
                        persistence_model.tasks.update(current_task_id, task)
                        print(f"✅ Cleared ALL sessions and created single new empty session {new_session_id}")
                        
                        # Update task_status to indicate we've made changes
                        task_status["session_id"] = new_session_id
                        st.session_state.task_controller.view_state.task_status = task_status
                    else:
                        print(f"⚠️ Task {current_task_id} not found or doesn't have chat_sessions")
                except Exception as e:
                    print(f"❌ Error clearing task sessions: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
            
            # Maintain the task status but clear session-related data
            st.session_state.task_controller.view_state.task_status = {
                "loaded": task_status.get("loaded", False),
                "task_id": task_status.get("task_id"),
                "task_name": task_status.get("task_name", ""),
                "tasksmanager_id": task_status.get("tasksmanager_id"),
                "tasksmanager_name": task_status.get("tasksmanager_name", ""),
                "session_id": task_status.get("session_id", "")
            }
            
            # Clear task management specific state
            st.session_state.task_controller.view_state.selected_task_manager = None
            st.session_state.task_controller.view_state.selected_task = None
            
            # Reset active tab
            st.session_state.active_tab = 0
            
            # Trigger state save to ensure changes are persisted
            if hasattr(st.session_state.task_controller, 'trigger_state_save'):
                st.session_state.task_controller.trigger_state_save()
            
            print("✅ Successfully cleared task hierarchy session")
        else:
            print("⚠️ Task controller or view state not available")

    def save_session(self):
        """Save the current view session."""
        print("\n💾 TaskHierarchyView: Saving session")
        
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
        
        # Call parent save_session method to save session data
        super().save_session()
        
        # Also save the state file to persist changes
        if hasattr(st.session_state, "task_controller"):
            try:
                # Trigger state save to persist changes
                if hasattr(st.session_state.task_controller, 'trigger_state_save'):
                    st.session_state.task_controller.trigger_state_save()
                    print("✅ Triggered state save to persist changes")
                
                # Update the save status in session state
                st.session_state.save_status = "saved"
                st.session_state.last_save_time = time.time()
                print(f"✅ Updated save status: {st.session_state.save_status}, time: {st.session_state.last_save_time}")
            except Exception as e:
                print(f"❌ Error triggering state save: {str(e)}")
                import traceback
                print(traceback.format_exc())

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
    
    # Chat input with unique key
    if prompt := st.chat_input("Enter your message", key="task_hierarchy_chat_input"):
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
    # Simply call the task_hierarchy_view_handle method
    # We've modified the controller to handle async internally
    controller.task_hierarchy_view_handle()

async def render_task_hierarchy_view():
    """Render the task hierarchy view"""
    try:
        # Initialize view
        view = TaskHierarchyView()
        
        # Initialize session state if needed
        if "task_controller" not in st.session_state:
            # Initialize controller and view state
            try:
                persistence_model = PersistenceModelFactory.persistence_model("inmemory")
                st.session_state.task_controller = TaskHierarchyController(persistence_model)
                
                # Make sure chat view (tab 0) is selected by default
                if "active_tab" not in st.session_state:
                    st.session_state.active_tab = 0
                    
                # Initialize controller
                await st.session_state.task_controller.initialize()
                print(f"🚀 Task controller initialized")
                
                # Restore session state if available
                view.restore_session()
                print(f"🔄 Session state restored")
                
                # Properly setup task status after restore
                if not st.session_state.task_controller.view_state.task_status.get("loaded", False):
                    # Try to find a task manager and task to set as active
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
            except Exception as e:
                print(f"Error initializing controller: {str(e)}")
                st.error(f"Error initializing task controller: {str(e)}")
                
        # Initialize active tab if not set - ALWAYS default to chat view (tab 0)
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
                    from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
                    if isinstance(st.session_state.persistence_model, InMemoryPersistenceModel):
                        setup_test_tasks(st.session_state.persistence_model)
                    else:
                        # Create a new InMemoryPersistenceModel if the type doesn't match
                        setup_test_tasks()
                    st.info("Created demo task managers and tasks for testing")
                except Exception as e:
                    st.warning(f"Failed to create test tasks: {str(e)}")
            
            # Load saved session state
            print("🔄 Loading saved session state")
            view.load_session()
            
            # After loading session, ensure active_tab defaults to 0 (chat) if still not set
            if 'active_tab' not in st.session_state:
                st.session_state.active_tab = 0
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
        
        # Add CSS for active tab highlighting
        st.markdown("""
        <style>
        .active-tab {
            background-color: rgba(70, 130, 180, 0.3);
            border-radius: 5px;
            padding: 2px 0px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Ensure active_tab is set to a valid value
        current_tab = st.session_state.get('active_tab', 0)
        
        # Add navigation tabs with icons, aligned like in tools catalog view
        col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
        with col1:
            # Add active-tab class if this is the current tab
            tab_class = "active-tab" if current_tab == 0 else ""
            st.markdown(f'<div class="{tab_class}">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            tab_class = "active-tab" if current_tab == 3 else ""
            st.markdown(f'<div class="{tab_class}">', unsafe_allow_html=True)
            if st.button("🌳", help="Switch to tree view", key="main_tab_tree"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 3
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            tab_class = "active-tab" if current_tab == 1 else ""
            st.markdown(f'<div class="{tab_class}">', unsafe_allow_html=True)
            if st.button("📊", help="Switch to observability view", key="main_tab_obs"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col4:
            tab_class = "active-tab" if current_tab == 2 else ""
            st.markdown(f'<div class="{tab_class}">', unsafe_allow_html=True)
            if st.button("⚙️", help="Switch to task management view", key="main_tab_manage"):
                # When switching to non-chat view, ensure we're using global persistence
                if hasattr(st.session_state, "task_controller") and hasattr(st.session_state.task_controller, "global_persistence"):
                    st.session_state.task_controller.persistence_model = st.session_state.task_controller.global_persistence
                
                st.session_state.active_tab = 2
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
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
            with st.expander("Task Tree Demonstration", expanded=False):
                demo_launcher = TaskTreeDemoLauncher(st.session_state.task_controller)
                demo_launcher.render()
            
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
