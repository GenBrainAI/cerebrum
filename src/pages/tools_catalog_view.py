import streamlit as st
import asyncio
from server.views.controllers.tools_view_controller import ToolsCatalogController
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.views.components.header import render_header
from server.views.components.sidebar.tools_catalog_sidebar import render_tools_catalog_sidebar
from server.views.base_view import BaseView
from server.views.models.view_types import ViewType
from typing import Dict, Any
from server.models.message import Message
from server.controllers.task_runner import TaskRunner
from server.views.components.task_tool_relationship import render_task_tool_relationship

class ToolsCatalogView(BaseView):
    def __init__(self):
        super().__init__(ViewType.TOOLS_CATALOG)
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get tools catalog specific session data."""
        data = super().get_session_data()
        
        if 'tools_controller' in st.session_state:
            chat_history = st.session_state.tools_controller.view_state.chat_history
            print(f"\n📝 Saving chat history:")
            print(f"  Length: {len(chat_history)}")
            print(f"  Content: {chat_history}")
        
        data.update({
            'chat_history': st.session_state.tools_controller.view_state.chat_history
            if 'tools_controller' in st.session_state else [],
            'view_mode': st.session_state.get('view_mode', 'chat')
        })
        return data
        
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore tools catalog specific session state."""
        super().restore_session_state(session_data)
        
        chat_history = session_data.get('chat_history', [])
        print(f"\n📖 Restoring chat history:")
        print(f"  Length: {len(chat_history)}")
        
        st.session_state.view_mode = session_data.get('view_mode', 'chat')
        
        if 'tools_controller' in st.session_state:
            st.session_state.tools_controller.view_state.chat_history = chat_history
            
    def clear_session(self):
        """Clear the tools catalog session data."""
        if 'tools_controller' in st.session_state:
            # Clear chat history
            st.session_state.tools_controller.view_state.chat_history = []
            
            # Save empty session
            self.save_session()
            
            print("\n🗑️ Cleared tools catalog session")

def render_chat_view():
    """Render the chat interface."""
    # Display messages
    for msg in st.session_state.tools_controller.view_state.chat_history:
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
        
        asyncio.run(st.session_state.tools_controller.handle_chat(prompt))
        st.rerun()

def render_observability_view():
    """Render the observability interface."""
    if 'tools_controller' not in st.session_state:
        st.warning("No active tools controller")
        return
        
    # Get active task from controller's view state
    task_status = st.session_state.tools_controller.view_state.task_status
    if not task_status or not task_status.get("loaded"):
        st.info("No active task loaded")
        return
        
    task_id = task_status.get("task_id")
    if not task_id:
        st.info("No task ID available")
        return
        
    # Initialize task runner if needed
    if not hasattr(st.session_state.tools_controller, 'task_runner'):
        st.session_state.tools_controller.task_runner = TaskRunner(st.session_state.tools_controller.global_persistence)
        
    # Get observability manager
    observability = st.session_state.tools_controller.task_runner.get_task_observability(task_id)
    
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

async def render_tools_catalog_view():
    """Render the tools catalog view."""
    # Import streamlit at the beginning of the function to avoid UnboundLocalError
    import streamlit as st
    
    try:
        # Initialize view and session state
        view = ToolsCatalogView()
        
        # Initialize persistence model if not in session state
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Ensure state_location is properly initialized
        if 'state_location' not in st.session_state or not st.session_state.state_location:
            from src.chat import get_last_used_state, get_state_dir
            from server.models.persistence_models import StorageLocation, StorageType
            import os
            
            # Get the last used state from metadata
            metadata = get_last_used_state()
            if metadata.get("last_used_state"):
                state_path = str(get_state_dir() / metadata["last_used_state"])
                
                # Create and store the location in session state
                st.session_state.state_location = StorageLocation(
                    type=StorageType.file,
                    location=os.path.dirname(state_path),
                    state_name=os.path.basename(state_path)
                )
                print(f"📍 Initialized state_location from last used state: {st.session_state.state_location.state_name}")
        
        # Initialize tools controller if not in session state
        if 'tools_controller' not in st.session_state:
            st.session_state.tools_controller = ToolsCatalogController(st.session_state.persistence_model)
            await st.session_state.tools_controller.initialize()
            
            # Load saved session state
            view.load_session()
        
        # Render header
        render_header("Tools Catalog")
        
        # Add reset button in sidebar
        with st.sidebar:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("🔄", help="Reset chat history"):
                    view.clear_session()
                    st.rerun()
        
        # Render sidebar
        await render_tools_catalog_sidebar()
        
        # Add view mode toggle
        col1, col2, col3, col4 = st.columns([0.1, 0.7, 0.1, 0.1])
        with col1:
            if st.button("💬", help="Switch to chat view"):
                st.session_state.active_tab = 0
                st.rerun()
        with col3:
            if st.button("📊", help="Switch to observability view"):
                st.session_state.active_tab = 1
                st.rerun()
        with col4:
            if st.button("🔄", help="Switch to relationship view"):
                st.session_state.active_tab = 2
                st.rerun()
        
        # Initialize active tab if not set
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
            
        # Chat View
        if st.session_state.active_tab == 0:
            st.subheader("Tools Management Chat")
            
            # Display messages
            for msg in st.session_state.tools_controller.view_state.chat_history:
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
                
                await st.session_state.tools_controller.handle_chat(prompt)
                
                # Save session after each message
                view.save_session()
                
                st.rerun()
        
        # Observability View
        elif st.session_state.active_tab == 1:
            render_observability_view()
            
        # Task-Tool Relationship View
        elif st.session_state.active_tab == 2:
            st.subheader("Task-Tool Relationship View")
            st.markdown("""
            This view helps you visualize the relationships between Tasks, CurriedProxy instances, and Tools.
            You can see how tools are connected to tasks either directly through toolsets or via CurriedProxy instances.
            """)
            
            # Ensure tools controller exists
            if not hasattr(st.session_state, 'tools_controller'):
                st.error("Tools controller not initialized properly. Please refresh the page.")
                st.stop()
            
            # Initialize a loading indicator
            with st.status("Loading global persistence data...", expanded=True) as status:
                # Force using global persistence
                if not st.session_state.tools_controller.using_global_persistence:
                    st.session_state.tools_controller.use_global_persistence()
                    status.update(label="Switched to global persistence", state="running", expanded=True)
                
                # Get the global persistence explicitly
                active_persistence = st.session_state.tools_controller.global_persistence
                print(f"\n🔍 DEBUG: Active persistence type: {type(active_persistence).__name__}")
                print(f"🔍 DEBUG: Active persistence ID: {id(active_persistence)}")
                print(f"🔍 DEBUG: Task collections type: {type(active_persistence.tasks).__name__}")
                
                # Ensure persistence model in session state matches the global one
                if id(st.session_state.persistence_model) != id(active_persistence):
                    print(f"⚠️ WARNING: Session state persistence model ID ({id(st.session_state.persistence_model)}) doesn't match active persistence ID ({id(active_persistence)})")
                    print(f"🔄 Updating session state persistence model to match global persistence model")
                    st.session_state.persistence_model = active_persistence
                else:
                    print(f"✅ Session state persistence model matches active persistence: ID={id(active_persistence)}")
                
                # Force reset of task runner to use the global persistence
                if hasattr(st.session_state.tools_controller, 'task_runner'):
                    try:
                        st.session_state.tools_controller.task_runner.set_persistence_model(active_persistence)
                        status.update(label="Refreshed task runner with global persistence", state="running", expanded=True)
                        print(f"🔍 DEBUG: Updated task runner to use global persistence")
                    except Exception as e:
                        st.warning(f"Error updating task runner: {str(e)}")
                        print(f"🔍 DEBUG: Error updating task runner: {str(e)}")
                    
                # Try to get task managers first
                task_managers = []
                try:
                    task_managers = active_persistence.tasksmanagers.list()
                    print(f"🔍 DEBUG: Found {len(task_managers)} task managers")
                    for tm in task_managers:
                        print(f"🔍 DEBUG: Task Manager: {tm.id} - {tm.name}")
                    status.update(label=f"Found {len(task_managers)} task managers", state="running", expanded=True)
                except Exception as e:
                    st.warning(f"Error listing task managers: {str(e)}")
                    print(f"🔍 DEBUG: Error listing task managers: {str(e)}")
                    print(f"🔍 DEBUG: Exception type: {type(e).__name__}")
                    import traceback
                    print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
                
                # Get tasks from the persistence model
                tasks = []
                try:
                    # Directly try to list tasks
                    status.update(label="Retrieving tasks from global persistence...", state="running", expanded=True)
                    print(f"🔍 DEBUG: Attempting to list tasks from global persistence")
                    tasks = active_persistence.tasks.list()
                    print(f"🔍 DEBUG: Found {len(tasks)} tasks directly from global persistence")
                    for task in tasks:
                        print(f"🔍 DEBUG: Task: {task.id} - {task.name} - Manager ID: {task.tasksmanager_id}")
                    status.update(label=f"Found {len(tasks)} tasks in global persistence", state="complete", expanded=False)
                except Exception as e:
                    st.error(f"Error retrieving tasks: {str(e)}")
                    print(f"🔍 DEBUG: Error retrieving tasks: {str(e)}")
                    print(f"🔍 DEBUG: Exception type: {type(e).__name__}")
                    import traceback
                    print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
                    tasks = []
                
                # If no tasks found, try an alternative approach
                if not tasks:
                    status.update(label="No tasks found, trying fallback approach...", state="running", expanded=True)
                    try:
                        # Try to collect tasks from task managers
                        all_task_ids = []
                        all_tasks = []
                        
                        for tm in task_managers:
                            # Try to get tasks from this manager
                            try:
                                tasks_for_manager = active_persistence.tasks.list_for_tasksmanager(tm.id)
                                if tasks_for_manager:
                                    all_task_ids.extend([t.id for t in tasks_for_manager])
                                    all_tasks.extend(tasks_for_manager)
                                    status.update(label=f"Found {len(tasks_for_manager)} tasks for manager {tm.name}", state="running", expanded=True)
                            except:
                                # Try direct lookup if list_for_tasksmanager fails
                                tasks_for_manager = [t for t in active_persistence.tasks.list() if t.tasksmanager_id == tm.id]
                                if tasks_for_manager:
                                    all_task_ids.extend([t.id for t in tasks_for_manager])
                                    all_tasks.extend(tasks_for_manager)
                                    status.update(label=f"Found {len(tasks_for_manager)} tasks for manager {tm.name} (fallback method)", state="running", expanded=True)
                        
                        if all_tasks:
                            tasks = all_tasks
                            status.update(label=f"Found {len(tasks)} tasks in total via fallback method", state="complete", expanded=False)
                    except Exception as e:
                        st.error(f"Fallback approach also failed: {str(e)}")
                        tasks = []
            
            # If absolutely no tasks found, create a test task automatically
            if not tasks:
                try:
                    print("\n🔍 DEBUG: No tasks found, creating a test task automatically")
                    from uuid import uuid4
                    from server.models.task import Task
                    from server.models.tasksmanager import TasksManager

                    # First check if we have any task managers
                    demo_tm = None
                    if task_managers:
                        demo_tm = task_managers[0]
                        print(f"🔍 DEBUG: Using existing task manager: {demo_tm.name}")
                    else:
                        # Create a new task manager
                        demo_tm = TasksManager(
                            id=str(uuid4()),
                            name="Auto Task Manager",
                            description="Task manager created automatically for testing"
                        )
                        active_persistence.tasksmanagers.save(demo_tm)
                        print(f"🔍 DEBUG: Created new task manager: {demo_tm.name} with ID: {demo_tm.id}")
                    
                    # Create a demo task
                    demo_task = Task(
                        id=str(uuid4()),
                        name="Auto Test Task",
                        description="Task created automatically for testing",
                        tasksmanager_id=demo_tm.id
                    )
                    active_persistence.tasks.save(demo_task)
                    print(f"🔍 DEBUG: Created new task: {demo_task.name} with ID: {demo_task.id}")
                    
                    # Now fetch the tasks again to see if it worked
                    try:
                        tasks = active_persistence.tasks.list()
                        print(f"🔍 DEBUG: After auto-creation, found {len(tasks)} tasks")
                    except Exception as e:
                        print(f"🔍 DEBUG: Error listing tasks after auto-creation: {str(e)}")
                    
                except Exception as e:
                    print(f"🔍 DEBUG: Error auto-creating test task: {str(e)}")
                    import traceback
                    print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            
            # If still no tasks, try loading from test tasks setup function
            if not tasks:
                try:
                    print("\n🔍 DEBUG: No tasks found after auto-creation, trying to initialize using setup_test_tasks()")
                    from src.state_setup.tasks import setup_test_tasks
                    
                    # Setup test tasks directly in the active persistence model
                    setup_test_tasks(active_persistence)
                    print("🔍 DEBUG: Called setup_test_tasks to initialize test data")
                    
                    # Try to fetch tasks again
                    tasks = active_persistence.tasks.list()
                    print(f"🔍 DEBUG: After setup_test_tasks, found {len(tasks)} tasks")
                    for task in tasks:
                        print(f"🔍 DEBUG: Found task: {task.id} - {task.name}")
                except Exception as e:
                    print(f"🔍 DEBUG: Error using setup_test_tasks: {str(e)}")
                    import traceback
                    print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            
            # Display task count with styled info message
            tasks_count = len(tasks)
            if tasks_count > 0:
                st.success(f"Found {tasks_count} tasks in the global persistence model.")
            else:
                st.warning(f"Found {tasks_count} tasks in the global persistence model.")
            
            # Check if we have tasks to visualize
            if tasks:
                # Render the task-tool relationship component
                try:
                    render_task_tool_relationship(
                        active_persistence,
                        st.session_state.tools_controller
                    )
                except Exception as e:
                    st.error(f"Error rendering relationship view: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc(), language="python")
            else:
                st.warning("No tasks found in the global persistence model.")
                
                # Add a button to create a dummy relationship for demonstration
                if st.button("Create Demo Relationship"):
                    try:
                        # Create a demo task in the global persistence
                        from uuid import uuid4
                        from server.models.task import Task
                        from server.models.tasksmanager import TasksManager

                        # First check if we already have a demo task manager
                        demo_tm = None
                        task_managers = active_persistence.tasksmanagers.list()
                        for tm in task_managers:
                            if tm.name == "Demo Task Manager":
                                demo_tm = tm
                                break
                        
                        # Create a demo task manager if it doesn't exist
                        if not demo_tm:
                            demo_tm = TasksManager(
                                id=str(uuid4()),
                                name="Demo Task Manager",
                                description="Task manager for demonstration purposes"
                            )
                            active_persistence.tasksmanagers.save(demo_tm)
                            st.success("Created demo task manager")
                        
                        # Create a demo task
                        demo_task = Task(
                            id=str(uuid4()),
                            name="Demo Task",
                            description="Task created for demonstration purposes",
                            tasksmanager_id=demo_tm.id
                        )
                        active_persistence.tasks.save(demo_task)
                        
                        # Create a CurriedProxy with tools
                        from server.controllers.curried_proxy import CurriedProxy
                        from server.tools.tools_catalog import tools_catalog
                        
                        # Get some demo tools - choose a few common ones if available
                        available_tools = tools_catalog.list_tools()
                        demo_tools = []
                        preferred_tools = ["web.search", "file.read", "utils.answer", "internal.context_lookup"]
                        
                        # Add preferred tools if they exist
                        for tool in preferred_tools:
                            if any(t.startswith(tool) for t in available_tools):
                                for available_tool in available_tools:
                                    if available_tool.startswith(tool):
                                        demo_tools.append(available_tool)
                                        break
                        
                        # If we don't have at least 2 tools, add some from what's available
                        if len(demo_tools) < 2 and available_tools:
                            for tool in filter_container_tools(available_tools)[:3]:
                                if tool not in demo_tools:
                                    demo_tools.append(tool)
                        
                        # Create the CurriedProxy
                        if demo_tools:
                            demo_proxy = CurriedProxy(
                                id=str(uuid4()),
                                name="Demo Tools Proxy",
                                tool_names=demo_tools
                            )
                            active_persistence.curried_proxies.save(demo_proxy)
                            
                            # Link the proxy to the task
                            demo_task.curried_proxy_id = demo_proxy.id
                            active_persistence.tasks.update(demo_task.id, demo_task)
                            
                            st.success(f"Created demo relationship with {len(demo_tools)} tools")
                            st.info("Refresh the page to see the demo relationship")
                        else:
                            st.error("No tools available to create demo relationship")
                        
                        # Force a rerun to show the new relationship
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error creating demo relationship: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")
            
    except Exception as e:
        # Using the already imported st from the beginning of the function
        st.error(f"Error rendering tools catalog view: {str(e)}")
        print(f"Error in render_tools_catalog_view: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")
        raise

def main():
    """Main entry point for tools catalog view."""
    st.set_page_config(page_title="Tools Catalog", layout="wide")
    asyncio.run(render_tools_catalog_view())

if __name__ == "__main__":
    main()
