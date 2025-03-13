import streamlit as st
import time
import os
import asyncio
import json
from typing import Optional
from typing import List, Dict
from datetime import datetime
from pathlib import Path

# Fix import paths - remove 'src.' prefix since we're running from the project root
from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.controllers.task_runner import TaskRunner
from server.models.message import Message
from server.models.tasks_manager import TasksManager
from server.models.task import Task
from server.controllers.persistence_controller import load_from_storage, save_to_storage
from server.models.persistence_models import StorageLocation, StorageType
from server.persistence.persistence_model import PersistenceModelBase 
from server.views.models.view_types import ViewType


def get_project_root() -> Path:
    """Get the absolute path to the project root."""
    # Assumes this file is in src/chat.py
    return Path(__file__).parent.parent

def get_state_dir() -> Path:
    """Get the state directory path, creating it if necessary."""
    state_dir = get_project_root() / "state"
    state_dir.mkdir(exist_ok=True)
    return state_dir

def save_current_state(state_name: str) -> str:
    """Save the current state.
    
    Args:
        state_name: Name of the state to save (without .json extension)
        
    Returns:
        str: Result of save operation
    """
    try:
        state_dir = get_state_dir()
        # Ensure state name has .json extension
        if not state_name.endswith('.json'):
            state_filename = f"{state_name}.json"
        else:
            state_filename = state_name
            state_name = state_name.replace('.json', '')
            
        location = StorageLocation(
            type=StorageType.file,
            location=str(state_dir),
            state_name=f"{state_name}"
        )
        
        # Create context state with session info
        context_state = {
            'current_tasksmanager_id': st.session_state.get('current_tasksmanager_id'),
            'current_task_id': st.session_state.get('current_task_id'),
            'current_session_id': st.session_state.get('current_session_id')
        }
        
        print(f"\n🔍 Context state to save:")
        print(f"  Content: {context_state}")
        
        # Get persistence model from session state
        persistence_model = st.session_state.persistence_model
        
        # Save state with context
        result = save_to_storage(persistence_model, location)
        print(f"  Save result: {result}")
        
        # Verify file was created
        state_file_path = state_dir / state_filename
        if not state_file_path.exists():
            print(f"⚠️ Warning: Expected state file not found at {state_file_path}")
            st.session_state.state_error_message = f"Failed to create state file: {state_filename}"
        else:
            print(f"✅ Confirmed state file saved at {state_file_path}")
            st.session_state.state_success_message = f"State saved successfully as {state_filename}"
        
        # Save metadata about last used state - use state_name without .json extension
        save_last_used_state(state_name)
        
        return result
    except Exception as e:
        print(f"❌ Error saving state: {str(e)}")
        st.session_state.state_error_message = f"Error saving state: {str(e)}"
        return str(e)

def load_state(state_path: Optional[str] = None):
    """Load Cerebrum state from file."""
    try:
        print(f"\n📂 Load state called with path: {state_path}")
        print(f"  Default state loaded flag: {st.session_state.get('default_state_loaded', False)}")
        
        # Attempt to load default state if no specific path provided
        if not state_path and not st.session_state.get('default_state_loaded'):
            metadata = get_last_used_state()
            if metadata.get("last_used_state"):
                # Ensure the state name has .json extension
                state_name = metadata["last_used_state"]
                if not state_name.endswith('.json'):
                    state_file_name = f"{state_name}.json"
                else:
                    state_file_name = state_name
                
                state_path = str(get_state_dir() / state_file_name)
                print(f"  Loading last used state from metadata: {state_path}")
                
                # Check if the file exists
                if not Path(state_path).exists():
                    print(f"⚠️ Last used state file not found: {state_path}")
                    st.session_state.state_error_message = f"Last used state file not found: {metadata['last_used_state']}"
                    # Reset the metadata to avoid trying to load this file again
                    save_last_used_state("")
                    return "Last used state file not found"
            else:
                default_state = "state/default_state.json"
                if Path(default_state).exists():
                    state_path = default_state
                    print(f"  Using default state: {default_state}")
                else:
                    print("  No default state available")
                    st.session_state.state_error_message = "No default state available"
                    return "No default state available"
            st.session_state.default_state_loaded = True
        
        if state_path:
            print(f"\n📥 Loading state from: {state_path}")
            
            # Check if the state file exists
            if not Path(state_path).exists():
                print(f"⚠️ State file not found: {state_path}")
                st.session_state.state_error_message = f"State file not found: {Path(state_path).name}"
                return f"State file not found: {Path(state_path).name}"
            
            location = StorageLocation(
                type=StorageType.file,
                location=os.path.dirname(state_path),
                state_name=os.path.basename(state_path)
            )
            
            # Store location in session state
            st.session_state.state_location = location
            
            try:
                # Reset the persistence model to start clean
                persistence_model = PersistenceModelFactory.persistence_model("inmemory")
                
                # Set as the current persistence model
                st.session_state.persistence_model = persistence_model
                
                # Load the state
                json_str = load_from_storage(location)
                state_data = json.loads(json_str)
                
                print(f"\n🔍 Loaded state data keys: {list(state_data.keys())}")
                
                # Process each collection in the loaded data
                for collection_name in ['toolsets', 'tools', 'tasksmanagers', 'tasks', 
                                        'messages', 'crewai_config', 'curried_proxies', 'task_flows']:
                    if collection_name in state_data:
                        if state_data[collection_name]:  # Only if there's data
                            try:
                                raw_data = json.loads(state_data[collection_name])
                                if collection_name == 'tasksmanagers':
                                    for tm_id, tm_data in raw_data.items():
                                        persistence_model.tasksmanagers.create(TasksManager(**tm_data))
                                elif collection_name == 'tasks':
                                    for task_id, task_data in raw_data.items():
                                        persistence_model.tasks.create(Task(**task_data))
                                else:
                                    # For other collections, use update
                                    persistence_model.update(collection_name, raw_data)
                                print(f"  Loaded {collection_name}: {len(raw_data) if isinstance(raw_data, dict) else 'non-dict data'}")
                            except Exception as e:
                                print(f"❌ Error loading {collection_name}: {str(e)}")
                        else:
                            print(f"  Empty {collection_name} in state data")
                
                # Process context state if available
                if 'context_state' in state_data:
                    context_state = state_data['context_state']
                    print(f"  Context state content: {context_state}")
                    
                    # Restore session state from context
                    if 'messages' in context_state:
                        st.session_state.messages = [Message(**msg) if isinstance(msg, dict) else msg 
                                                   for msg in context_state['messages']]
                    # Use get() to handle missing or None values safely
                    st.session_state.current_tasksmanager_id = context_state.get('current_tasksmanager_id')
                    st.session_state.current_task_id = context_state.get('current_task_id')
                    st.session_state.current_session_id = context_state.get('current_session_id')
                else:
                    # If no context state, try to find a default session
                    print("  No context state found, looking for default session")
                    
                    # Find the first task manager
                    tasksmanagers = persistence_model.tasksmanagers.list()
                    if tasksmanagers:
                        default_tm = tasksmanagers[0]
                        st.session_state.current_tasksmanager_id = default_tm.id
                        print(f"  Using first task manager: {default_tm.name} (ID: {default_tm.id})")
                        
                        # Find the first task for this task manager
                        tasks = get_tasks_for_tasksmanager(default_tm.id)
                        if tasks:
                            default_task = tasks[0]
                            st.session_state.current_task_id = default_task.id
                            print(f"  Using first task: {default_task.name} (ID: {default_task.id})")
                            
                            # Find or create a session for this task
                            if hasattr(default_task, 'chat_sessions') and default_task.chat_sessions:
                                # Use the first session
                                session_id = list(default_task.chat_sessions.keys())[0]
                                st.session_state.current_session_id = session_id
                                print(f"  Using existing session: {session_id}")
                            else:
                                # Create a new session
                                session_id = create_new_session(default_task.id)
                                st.session_state.current_session_id = session_id
                                print(f"  Created new session: {session_id}")
                            
                            # Initialize empty messages
                            st.session_state.messages = []
                
                # Save this as the last used state
                state_name = os.path.basename(state_path)
                # Remove .json extension for consistency in metadata
                if state_name.endswith('.json'):
                    state_name_for_metadata = state_name[:-5]
                else:
                    state_name_for_metadata = state_name
                    
                save_last_used_state(state_name_for_metadata)
                st.session_state.selected_state_file = state_name
                
                # Also reset selection tracking to sync with newly loaded state
                st.session_state.previous_tm_selection = None
                st.session_state.previous_task_selection = None
                
                # Force refresh of state files list on next render
                if 'current_state_files' in st.session_state:
                    del st.session_state.current_state_files
                
                success_message = f"Successfully loaded state from {os.path.basename(state_path)}"
                st.session_state.state_success_message = success_message
                return success_message
            except Exception as e:
                print(f"❌ Error loading state data: {e}")
                st.session_state.state_error_message = f"Error loading state data: {str(e)}"
                return f"Error loading state data: {str(e)}"
        return "No state file specified"
    except Exception as e:
        if state_path == "state/default_state.json":
            return "No default state loaded"
        print(f"❌ Error loading state: {str(e)}")
        st.session_state.state_error_message = f"Error loading state: {str(e)}"
        return f"Error loading state: {str(e)}"

def render_view_specific_chat():
    """Render chat interface with view-specific components."""
    st.sidebar.title("Navigation")
    view = st.sidebar.selectbox(
        "Select View",
        ["Task Hierarchy", "Tools Catalog", "Agentic Config"]
    )

def render_state_management():
    """Render the state management section in the sidebar."""
    print("\n🔄 Starting render_state_management")
    persistence_model = st.session_state.persistence_model
    
    with st.sidebar:
        st.subheader("State Management")
        
        # Initialize session state variables if not already present
        if 'selected_state_file' not in st.session_state:
            print("\n🔄 Initializing selected_state_file")
            # Try to get the last used state from metadata
            metadata = get_last_used_state()
            st.session_state.selected_state_file = metadata.get("last_used_state", "")
            print(f"  Set selected_state_file to: {st.session_state.selected_state_file}")
            
        if 'state_loaded' not in st.session_state:
            st.session_state.state_loaded = False
            
        if 'state_location' not in st.session_state:
            st.session_state.state_location = None
            
        # Display current state information
        if st.session_state.selected_state_file:
            # Check if the file actually exists
            state_path = get_state_dir() / st.session_state.selected_state_file
            if state_path.exists():
                st.info(f"Current state: {st.session_state.selected_state_file}")
            else:
                st.warning(f"Selected state file not found: {st.session_state.selected_state_file}")
                # Reset the selected state file since it doesn't exist
                st.session_state.selected_state_file = ""
        
        # State loading section
        st.write("Load State")
        
        # Get state files - use cached version if available
        try:
            if 'current_state_files' not in st.session_state or st.session_state.current_state_files is None:
                state_files = list((get_state_dir()).glob("*.json"))
                st.session_state.current_state_files = state_files
                print(f"  Loaded {len(state_files)} state files")
            else:
                state_files = st.session_state.current_state_files
                print(f"  Using cached state files: {len(state_files) if state_files else 0}")
        except Exception as e:
            print(f"❌ Error loading state files: {str(e)}")
            state_files = []
            st.session_state.current_state_files = []
        
        # Dropdown selection
        if state_files:
            file_names = [""] + [f.name for f in state_files]
            
            # Handle selection change
            def on_state_select():
                print("\n🔄 State selection changed")
                selected = st.session_state.state_selector
                if selected != st.session_state.selected_state_file:
                    print(f"  Selection changed from {st.session_state.selected_state_file} to {selected}")
                    st.session_state.selected_state_file = selected
                    st.session_state.state_loaded = False
                    
                    if selected:  # Auto-load when a state is selected
                        try:
                            state_to_load = str(get_state_dir() / selected)
                            # Check if the file exists before trying to load it
                            if not Path(state_to_load).exists():
                                print(f"⚠️ Selected state file not found: {state_to_load}")
                                st.session_state.state_error_message = f"Selected state file not found: {selected}"
                                return
                                
                            print(f"  Auto-loading state: {state_to_load}")
                            result = load_state(state_to_load)
                            st.session_state.state_loaded = True
                            print(f"  Auto-load result: {result}")
                            st.rerun()
                        except Exception as e:
                            print(f"❌ Error auto-loading state: {str(e)}")
                            st.session_state.state_error_message = f"Error loading state: {str(e)}"
            
            # Use the last used state as the default index if available
            default_index = 0
            if st.session_state.selected_state_file in file_names:
                default_index = file_names.index(st.session_state.selected_state_file)
                print(f"  Using default index {default_index} for {st.session_state.selected_state_file}")
            
            selected_state = st.selectbox(
                "Select saved state",
                file_names,
                index=default_index,
                key="state_selector",
                on_change=on_state_select
            )
        else:
            st.warning("No state files found. Create a new state to get started.")
            selected_state = None
        
        # Manual path input
        manual_state_path = st.text_input("Or enter state file path", key="manual_state_path")
        
        # Action buttons
        if selected_state or manual_state_path:
            state_to_load = str(get_state_dir() / selected_state) if selected_state else manual_state_path
            
            # Check if the file exists before showing the load button
            file_exists = Path(state_to_load).exists()
            
            if st.button("Load State", key="load_state_btn", use_container_width=True, disabled=not file_exists):
                try:
                    with st.spinner("Loading state..."):
                        result = load_state(state_to_load)
                        st.session_state.state_loaded = True
                        st.session_state.state_success_message = result
                        st.rerun()
                except Exception as e:
                    st.session_state.state_error_message = f"Error loading state: {str(e)}"
            
            if not file_exists and (selected_state or manual_state_path):
                st.warning(f"State file not found: {Path(state_to_load).name}")
            
            if selected_state and st.session_state.state_loaded:
                if st.button("Save State", key="save_state_btn", use_container_width=True):
                    try:
                        with st.spinner("Saving state..."):
                            # Save current state including chat messages
                            if st.session_state.get('messages') and st.session_state.get('current_task_id'):
                                save_chat_messages(
                                    st.session_state.current_task_id, 
                                    st.session_state.messages
                                )
                            result = save_current_state(selected_state)
                            st.session_state.state_success_message = "State saved successfully"
                            
                            # Force refresh of state files list
                            st.session_state.current_state_files = list((get_state_dir()).glob("*.json"))
                            
                            st.rerun()
                    except Exception as e:
                        st.session_state.state_error_message = f"Error saving state: {str(e)}"
        
        st.write("---")
        
        # New state creation
        st.write("Create New State")
        new_state_name = st.text_input("New State Name", key="new_state_name_input")
        save_current = st.checkbox("Save current state first", value=True, key="save_current_checkbox")
        
        if st.button("Create State", key="create_state_btn"):
            if new_state_name:
                try:
                    with st.spinner("Creating new state..."):
                        # Create new state with default session
                        success = create_new_state(new_state_name, save_current)
                        if success:
                            st.session_state.state_success_message = f"New state '{new_state_name}' created successfully!"
                            
                            # Force refresh of state files list
                            st.session_state.current_state_files = list((get_state_dir()).glob("*.json"))
                            
                            # Force rerun to update the UI with new state
                            time.sleep(1)  # Give a moment for the user to see the success message
                            st.rerun()
                except Exception as e:
                    st.session_state.state_error_message = f"Error creating state: {str(e)}"
            else:
                st.session_state.state_error_message = "Please enter a name for the new state"


# In the render_navigation function, add:
def render_navigation():
    """Render the horizontal navigation menu."""
    st.markdown("---")
    nav_cols = st.columns(5)  # Updated to 5 columns
    
    with nav_cols[0]:
        if st.button("💬 Chat", use_container_width=True):
            st.session_state.context_view = "chat"
            
    with nav_cols[1]:
        if st.button("🧠 Context", use_container_width=True):
            st.session_state.context_view = "context"
            
    with nav_cols[2]:
        if st.button("📚 Knowledge", use_container_width=True):
            st.session_state.context_view = "knowledge"
            
    with nav_cols[3]:
        if st.button("🔄 Vector Store", use_container_width=True):
            st.session_state.context_view = "vector"
            
    with nav_cols[4]:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.context_view = "settings"
        
    st.markdown("---")

def select_or_create_chat(chat_name: str, existing_tm_name: Optional[str] = None, existing_task_name: Optional[str] = None):
    """Select existing task/tasksmanager or create new ones"""
    tasksmanagers = get_available_tasksmanagers()
    
    if existing_tm_name and existing_task_name:
        # Find existing tasksmanager and task
        selected_tm = next((tm for tm in tasksmanagers if tm.name == existing_tm_name), None)
        if selected_tm:
            tasks = get_tasks_for_tasksmanager(selected_tm.id)
            selected_task = next((t for t in tasks if t.name == existing_task_name), None)
            if selected_task:
                return selected_tm.id, selected_task.id

    # If we get here, either we didn't find the existing task/tm or none was specified
    # Create new ones
    tasksmanager = TasksManager(
        name=chat_name,
        model="gpt-4o-mini",  # You might want to make this configurable
        description="Chat session TasksManager"
    )
    persistence_model = st.session_state.persistence_model
    tasksmanager = persistence_model.tasksmanagers.create(tasksmanager)
    
    task = Task(
        name=chat_name,
        description="Chat conversation task",
        tasksmanager_id=tasksmanager.id,
        messages=[Message(
            role="system",
            content="You are a helpful AI assistant engaged in a conversation."
        )]
    )
    task = persistence_model.tasks.create(task)
    
    return tasksmanager.id, task.id


def initialize_session_state():
    """Initialize session state variables."""
    print("\n🔄 Initializing session state")
    
    # Track initialization to prevent multiple calls
    if 'session_initialized' in st.session_state:
        print("✅ Session already initialized, skipping")
        
        # Still increment rerun counter to detect potential loops
        if 'rerun_count' in st.session_state:
            st.session_state.rerun_count += 1
            if st.session_state.rerun_count > 5:  # Threshold of 5 reruns
                print(f"⚠️ Warning: High rerun count detected ({st.session_state.rerun_count})")
                # Reset counter after warning
                st.session_state.rerun_count = 0
                
                # Force break potential loops by ensuring selection tracking is synchronized
                if 'tm_selector' in st.session_state and 'previous_tm_selection' in st.session_state:
                    if st.session_state.tm_selector != st.session_state.previous_tm_selection:
                        print(f"🔄 Synchronizing previous_tm_selection to break potential loop")
                        st.session_state.previous_tm_selection = st.session_state.tm_selector
                
                if 'task_selector' in st.session_state and 'previous_task_selection' in st.session_state:
                    if st.session_state.task_selector != st.session_state.previous_task_selection:
                        print(f"🔄 Synchronizing previous_task_selection to break potential loop")
                        st.session_state.previous_task_selection = st.session_state.task_selector
                
                # Force synchronization of current IDs with selected values
                if 'tm_selector' in st.session_state and st.session_state.tm_selector:
                    # Find the task manager ID for the selected name
                    persistence_model = st.session_state.persistence_model
                    tasksmanagers = persistence_model.tasksmanagers.list()
                    for tm in tasksmanagers:
                        if tm.name == st.session_state.tm_selector:
                            print(f"🔄 Forcing current_tasksmanager_id to match selected: {tm.id}")
                            st.session_state.current_tasksmanager_id = tm.id
                            break
                
                # Also synchronize task selection
                if 'task_selector' in st.session_state and st.session_state.task_selector:
                    # Get current TM ID
                    tm_id = st.session_state.get('current_tasksmanager_id')
                    if tm_id:
                        tasks = get_tasks_for_tasksmanager(tm_id)
                        for task in tasks:
                            if task.name == st.session_state.task_selector:
                                print(f"🔄 Forcing current_task_id to match selected: {task.id}")
                                st.session_state.current_task_id = task.id
                                break
        return
    
    # Initialize rerun counter
    st.session_state.rerun_count = 0
    
    # Persistence and task runner
    if 'persistence_model' not in st.session_state:
        print("\n🆕 Creating new persistence model")
        st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        print("✅ Stored new persistence model in session state")
    
    if 'task_runner' not in st.session_state:
        st.session_state.task_runner = TaskRunner(st.session_state.persistence_model)
    
    # Initialize basic session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_tasksmanager_id' not in st.session_state:
        st.session_state.current_tasksmanager_id = None
    if 'current_task_id' not in st.session_state:
        st.session_state.current_task_id = None
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'chat_title' not in st.session_state:
        st.session_state.chat_title = "New Chat"
    if 'creating_new_chat' not in st.session_state:
        st.session_state.creating_new_chat = False
    if 'current_view' not in st.session_state:
        st.session_state.current_view = None
    if 'default_state_loaded' not in st.session_state:
        st.session_state.default_state_loaded = False
    if 'state_location' not in st.session_state:
        st.session_state.state_location = None
    if 'previous_tm_selection' not in st.session_state:
        st.session_state.previous_tm_selection = None
    if 'previous_task_selection' not in st.session_state:
        st.session_state.previous_task_selection = None
    
    # State management variables
    if 'selected_state_file' not in st.session_state:
        st.session_state.selected_state_file = ""
    if 'state_loaded' not in st.session_state:
        st.session_state.state_loaded = False
    if 'state_initialized' not in st.session_state:
        st.session_state.state_initialized = False
    if 'state_error_message' not in st.session_state:
        st.session_state.state_error_message = None
    if 'state_success_message' not in st.session_state:
        st.session_state.state_success_message = None
    if 'pending_state_load' not in st.session_state:
        st.session_state.pending_state_load = None
    if 'current_state_files' not in st.session_state:
        st.session_state.current_state_files = None
    
    # Mark as initialized
    st.session_state.session_initialized = True

def get_task_system_messages(task_id: str) -> List[Dict]:
    """Get system messages for a specific task"""
    if not task_id:
        return []
    
    # Use session state persistence model
    persistence_model = st.session_state.persistence_model
    task = persistence_model.tasks.read(task_id)
    if task and task.messages:
        return [msg.dict() for msg in task.messages if isinstance(msg, dict) and msg.get('role') == 'system' 
                or getattr(msg, 'role', None) == 'system']
    return []

def create_new_session(task_id: str) -> str:
    """Create a new chat session for a task"""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    # Use session state persistence model
    persistence_model: PersistenceModelBase = st.session_state.persistence_model
    task: Task = persistence_model.tasks.read(task_id)
    if task:
        # Create new session in the task
        if not hasattr(task, 'chat_sessions') or task.chat_sessions is None:
            task.chat_sessions = {}
        task.chat_sessions[session_id] = []
        persistence_model.tasks.update(task_id, task)
    return session_id

def save_session_messages(task_id: str, session_id: str, messages: List[Dict]):
    """Save messages for a specific chat session"""
    if not task_id or not session_id:
        return
    
    # Use session state persistence model    
    persistence_model = st.session_state.persistence_model
    task: Task = persistence_model.tasks.read(task_id)
    if task:
        if not hasattr(task, 'chat_sessions') or task.chat_sessions is None:
            task.chat_sessions = {}
        task.chat_sessions[session_id] = [
            msg.dict() if hasattr(msg, 'dict') else msg for msg in messages
        ]
        persistence_model.tasks.update(task_id, task)

def get_session_messages(task_id: str, session_id: str) -> List[Dict]:
    """Get messages for a specific chat session"""
    # Use session state persistence model
    persistence_model = st.session_state.persistence_model
    task = persistence_model.tasks.read(task_id)
    if task:
        task_dict = task.dict() if hasattr(task, 'dict') else task
        if 'chat_sessions' in task_dict:
            return task_dict['chat_sessions'].get(session_id, [])
    return []

def get_chat_sessions(task_id: str) -> Dict[str, List[Dict]]:
    """Get all chat sessions for a task"""
    persistence_model = st.session_state.persistence_model
    task = persistence_model.tasks.read(task_id)
    if task:
        # Use model_dump instead of dict
        task_dict = task.model_dump() if hasattr(task, 'model_dump') else task
        if 'chat_sessions' in task_dict:
            return task_dict['chat_sessions']
    return {}

def on_tm_select():
    """Callback when TaskManager selection changes"""
    # Store previous selection
    previous_tm = st.session_state.get('previous_tm_selection')
    current_tm = st.session_state.tm_selector
    
    print(f"\n🔍 DEBUG - on_tm_select callback:")
    print(f"  Previous TM selection: {previous_tm}")
    print(f"  Current TM selection: {current_tm}")
    
    # Only process if the selection has actually changed
    if previous_tm != current_tm:
        print(f"  TaskManager selection changed from {previous_tm} to {current_tm}")
        # Update previous selection before processing to prevent loops
        st.session_state.previous_tm_selection = current_tm
        
        if current_tm == "+ New Chat":
            print(f"  Creating new chat")
            st.session_state.creating_new_chat = True
            st.session_state.messages = []
            st.session_state.current_session_id = None
        else:
            print(f"  Selecting existing chat")
            st.session_state.creating_new_chat = False
            
            # Get the task manager ID from the name
            persistence_model = st.session_state.persistence_model
            tasksmanagers = persistence_model.tasksmanagers.list()
            selected_tm_id = None
            
            for tm in tasksmanagers:
                if tm.name == current_tm:
                    selected_tm_id = tm.id
                    break
            
            if selected_tm_id:
                print(f"  Found TM ID: {selected_tm_id}")
                
                # Only update if the ID has changed to prevent unnecessary reruns
                if st.session_state.get('current_tasksmanager_id') != selected_tm_id:
                    print(f"  Updating current_tasksmanager_id from {st.session_state.get('current_tasksmanager_id')} to {selected_tm_id}")
                    st.session_state.current_tasksmanager_id = selected_tm_id
                    
                    # Reset previous task selection to prevent rerun loops
                    st.session_state.previous_task_selection = None
                    
                    # Get the first task for this TM
                    tasks = get_tasks_for_tasksmanager(selected_tm_id)
                    if tasks:
                        first_task = tasks[0]
                        print(f"  Setting first task: {first_task.name} (ID: {first_task.id})")
                        st.session_state.current_task_id = first_task.id
                        
                        # Create new session for selected task
                        print(f"  Creating new session for task: {first_task.id}")
                        session_id = create_new_session(first_task.id)
                        st.session_state.current_session_id = session_id
                        st.session_state.messages = []
                else:
                    print(f"  TM ID already set to {selected_tm_id}, skipping update")
    else:
        print(f"  No change in TaskManager selection, skipping processing")

def get_available_tasksmanagers():
    """Get list of available TasksManagers sorted by creation date"""
    try:
        # Use session state persistence model
        persistence_model = st.session_state.persistence_model
        tasksmanagers = persistence_model.tasksmanagers.list()
        return sorted(
            tasksmanagers,
            key=lambda x: (x.created_at or '', x.name),
            reverse=True  # Most recent first
        )
    except Exception as e:
        st.error(f"Error fetching TasksManagers: {str(e)}")
        return []

def get_tasks_for_tasksmanager(tasksmanager_id: str):
    """Get list of tasks for a specific TasksManager sorted by creation date"""
    try:
        # Use session state persistence model
        persistence_model = st.session_state.persistence_model
        all_tasks = persistence_model.tasks.list()
        tasks = [task for task in all_tasks if task.tasksmanager_id == tasksmanager_id]
        return sorted(
            tasks,
            key=lambda x: (x.created_at or '', x.name),
            reverse=True  # Most recent first
        )
    except Exception as e:
        st.error(f"Error fetching tasks: {str(e)}")
        return []

async def process_message(prompt: str, 
                        tasksmanager_id: str, 
                        task_id: str, 
                        messages: list):
    """Process a user message and get AI response"""
    # Use session state persistence model and task runner
    persistence_model = st.session_state.persistence_model
    task_runner = st.session_state.task_runner
    
    # Create new message for the prompt
    new_message = Message(
        role="user",
        content=prompt,
        file_ids=None,
        created_at=None,
        updated_at=None
    )
    task = persistence_model.tasks.read(task_id)
    task.messages.append(new_message)
    persistence_model.tasks.update(task_id, task)    
    try:
        response = await task_runner.run_task(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            running_extra_params={}
        )
        
        if isinstance(response, dict) and 'response' in response:
            return response['response']
        return str(response)
    except Exception as e:
        raise Exception(f"Error processing request: {str(e)}")

def get_logo_path() -> str:
    """Get the path to the logo file."""
    # Try different potential locations for the logo
    potential_paths = [
        Path(__file__).parent.parent / "logo.png",  # From src/chat.py, up one level
        Path(__file__).parent.parent.parent / "logo.png",  # Up two levels
        Path.cwd() / "logo.png"  # Current working directory
    ]
    
    for path in potential_paths:
        if path.exists():
            return str(path)
    
    return None  # Return None if logo not found

def render_logo(width=150):
    """Render the logo with specified width"""
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, width=width)
    else:
        st.warning("Logo not found", icon="⚠️")

def render_chat_management_sidebar():
    """Render the chat management section in the sidebar."""
    print("\n🔄 Starting render_chat_management_sidebar")
    # Get persistence model from session state
    persistence_model = st.session_state.persistence_model
    
    # Chat Management section
    tasksmanagers = get_available_tasksmanagers()
    
    st.subheader("Chat Management")
    
    # Create New Chat button
    create_new = st.button("Create New Chat")
    
    if create_new:
        st.session_state.creating_new_chat = True
    
    # New Chat Creation Form
    if st.session_state.get('creating_new_chat', False):
        with st.expander("New Chat Details", expanded=True):
            new_chat_name = st.text_input(
                "Chat Name",
                value=f"Chat {len(tasksmanagers) + 1}",
                key="new_chat_name"
            )
            
            # Show existing task selection if state is loaded
            if tasksmanagers:
                use_existing = st.checkbox("Use existing task", key="use_existing")
                
                if use_existing:
                    # TaskManager selection
                    tm_names = [tm.name for tm in tasksmanagers]
                    selected_tm_name = st.selectbox(
                        "Select Task Manager",
                        options=tm_names,
                        key="select_existing_tm"
                    )
                    
                    # Task selection for chosen TaskManager
                    if selected_tm_name:
                        selected_tm = next(tm for tm in tasksmanagers if tm.name == selected_tm_name)
                        tasks = get_tasks_for_tasksmanager(selected_tm.id)
                        task_names = [t.name for t in tasks]
                        selected_task_name = st.selectbox(
                            "Select Task",
                            options=task_names,
                            key="select_existing_task"
                        )
                else:
                    selected_tm_name = None
                    selected_task_name = None
            else:
                selected_tm_name = None
                selected_task_name = None
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Create", key="confirm_create"):
                    # Select or create new chat
                    tasksmanager_id, task_id = select_or_create_chat(
                        new_chat_name,
                        selected_tm_name,
                        selected_task_name
                    )
                    
                    # Update session state
                    st.session_state.current_tasksmanager_id = tasksmanager_id
                    st.session_state.current_task_id = task_id
                    st.session_state.messages = []
                    st.session_state.chat_title = new_chat_name
                    st.session_state.creating_new_chat = False
                    
                    # Create new session
                    session_id = create_new_session(task_id)
                    st.session_state.current_session_id = session_id
                    
                    # Store the selection to prevent future reruns
                    for tm in tasksmanagers:
                        if tm.id == tasksmanager_id:
                            st.session_state.previous_tm_selection = tm.name
                            break
                    
                    st.rerun()
            
            with col2:
                if st.button("Cancel", key="cancel_create"):
                    st.session_state.creating_new_chat = False
                    st.rerun()
    
    # Existing Chats Section
    if tasksmanagers:
        st.markdown("---")
        st.subheader("Existing Chats")
        
        # Create a mapping of TM names to IDs and IDs to names for easier lookup
        tm_name_to_id = {tm.name: tm.id for tm in tasksmanagers}
        tm_id_to_name = {tm.id: tm.name for tm in tasksmanagers}
        
        # Get current TM ID and name
        current_tm_id = st.session_state.get('current_tasksmanager_id')
        current_tm_name = tm_id_to_name.get(current_tm_id) if current_tm_id else None
        
        # Get previous TM selection
        previous_tm_selection = st.session_state.get('previous_tm_selection')
        
        print(f"\n🔍 DEBUG - TaskManager Selection:")
        print(f"  Previous TM selection: {previous_tm_selection}")
        print(f"  Current TM ID: {current_tm_id}")
        print(f"  Current TM name: {current_tm_name}")
        
        # Determine default selection
        default_index = 0
        tm_options = list(tm_name_to_id.keys())
        
        # If we have a current TM name, use it as default
        if current_tm_name and current_tm_name in tm_options:
            default_index = tm_options.index(current_tm_name)
        # If not, but we have a previous selection, use that
        elif previous_tm_selection and previous_tm_selection in tm_options:
            default_index = tm_options.index(previous_tm_selection)
        
        print(f"  Default TM index: {default_index}")
        
        # TaskManager selection
        selected_tm = st.selectbox(
            "Select Task Manager",
            options=tm_options,
            index=default_index,
            key="tm_selector",
            on_change=on_tm_select
        )
        
        # Update previous_tm_selection to match current UI selection
        # This prevents unnecessary reruns when the UI is first rendered
        if selected_tm != st.session_state.get('previous_tm_selection'):
            print(f"  Updating previous_tm_selection from {st.session_state.get('previous_tm_selection')} to {selected_tm}")
            st.session_state.previous_tm_selection = selected_tm
        
        if selected_tm:
            selected_tm_id = tm_name_to_id[selected_tm]
            print(f"  Selected TM: {selected_tm} (ID: {selected_tm_id})")
            
            # Ensure current_tasksmanager_id matches the selected TM
            # This is crucial to prevent rerun loops
            if st.session_state.get('current_tasksmanager_id') != selected_tm_id:
                print(f"  Updating current_tasksmanager_id to match selected TM: {selected_tm_id}")
                st.session_state.current_tasksmanager_id = selected_tm_id
            
            # Get tasks for the selected TM
            tasks = get_tasks_for_tasksmanager(selected_tm_id)
            
            if tasks:
                # Create task name to ID mapping
                task_name_to_id = {task.name: task.id for task in tasks}
                task_id_to_name = {task.id: task.name for task in tasks}
                
                # Get current task ID and name
                current_task_id = st.session_state.get('current_task_id')
                current_task_name = task_id_to_name.get(current_task_id) if current_task_id else None
                
                print(f"  Current task ID: {current_task_id}")
                print(f"  Current task name: {current_task_name}")
                
                # Track previous task selection to prevent rerun loops
                if 'previous_task_selection' not in st.session_state:
                    st.session_state.previous_task_selection = None
                
                # Determine default task selection
                default_task_index = 0
                task_options = list(task_name_to_id.keys())
                
                if current_task_name and current_task_name in task_options:
                    default_task_index = task_options.index(current_task_name)
                
                print(f"  Default task index: {default_task_index}")
                
                # Task selection
                selected_task = st.selectbox(
                    "Select Task",
                    options=task_options,
                    index=default_task_index,
                    key="task_selector"
                )
                
                # Update previous_task_selection to match current UI selection
                # This prevents unnecessary reruns when the UI is first rendered
                if selected_task != st.session_state.get('previous_task_selection'):
                    print(f"  Updating previous_task_selection from {st.session_state.get('previous_task_selection')} to {selected_task}")
                    st.session_state.previous_task_selection = selected_task
                
                if selected_task:
                    selected_task_id = task_name_to_id[selected_task]
                    print(f"  Selected task: {selected_task} (ID: {selected_task_id})")
                    
                    # Read the task to verify it exists
                    try:
                        task = persistence_model.tasks.read(selected_task_id)
                        print(f"\n📖 Reading Task {selected_task_id}:")
                        print(f"  Type: {type(task)}")
                        print(f"  Is instance of Task: {isinstance(task, Task)}")
                        
                        # Check if the selection has actually changed
                        selection_changed = (selected_task_id != current_task_id)
                        
                        if selection_changed:
                            print(f"  Task selection changed from {current_task_id} to {selected_task_id}")
                            # Update session state
                            st.session_state.current_task_id = selected_task_id
                            st.session_state.messages = []
                            
                            # Create new session
                            session_id = create_new_session(selected_task_id)
                            st.session_state.current_session_id = session_id
                        else:
                            print(f"  No change in task selection, skipping update")
                    except Exception as e:
                        print(f"❌ Error reading task {selected_task_id}: {e}")

async def render_main_chat():
    """Render the main chat interface with context information."""
    from server.models.task import Task  # Add this import at the top
    
    print("\n🔄 Starting render_main_chat")
    persistence_model = st.session_state.persistence_model
    
    tasksmanagers = get_available_tasksmanagers()
    
    if st.session_state.current_tasksmanager_id is None:
        st.info("Please create a new chat or select an existing one to begin.")
        return

    current_tm = next((tm for tm in tasksmanagers 
                      if tm.id == st.session_state.current_tasksmanager_id), None)
    if current_tm:
        st.title(current_tm.name)
    
    # Get current task
    print(f"\n📋 Current task_id: {st.session_state.current_task_id}")
    current_task: Optional[Task] = None
    if st.session_state.current_task_id:
        task_data = persistence_model.tasks.read(st.session_state.current_task_id)
        if isinstance(task_data, dict):
            current_task = Task(**task_data)
        else:
            current_task = task_data

    # Load chat messages for current session
    if st.session_state.current_task_id and st.session_state.current_session_id:
        print(f"\n💬 Loading messages for session: {st.session_state.current_session_id}")
        if not st.session_state.messages:  # Only load if messages are empty
            st.session_state.messages = load_chat_messages(st.session_state.current_task_id)
    
    # Display chat messages
    if st.session_state.messages is not None:
        # Add CSS for proper markdown rendering
        st.markdown("""
        <style>
        .chat-message {
            margin-bottom: 10px;
        }
        .chat-message p {
            margin-bottom: 5px;
            white-space: pre-wrap;
        }
        .chat-message ul, .chat-message ol {
            margin-left: 20px;
            margin-bottom: 10px;
        }
        .chat-message h1, .chat-message h2, .chat-message h3, .chat-message h4 {
            margin-top: 10px;
            margin-bottom: 10px;
        }
        .chat-message code {
            white-space: pre-wrap;
        }
        .chat-message pre {
            white-space: pre-wrap;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .stMarkdown {
            overflow-wrap: break-word;
        }
        </style>
        """, unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            if msg is None:
                continue
                
            # Ensure msg is a Message object
            if isinstance(msg, dict):
                try:
                    msg = Message(**msg)
                except Exception as e:
                    st.error(f"Error parsing message: {str(e)}")
                    continue
                    
            with st.chat_message(msg.role):
                # Use write for better markdown rendering
                st.write(msg.content)

    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message to display
        with st.chat_message("user"):
            st.write(prompt)

        # Create and add Message object to state
        user_message = Message(
            role="user",
            content=prompt,
            file_ids=None,
            created_at=None,
            updated_at=None
        )
        
        # Ensure messages list exists
        if st.session_state.messages is None:
            st.session_state.messages = []
        
        # Add message to session state
        st.session_state.messages.append(user_message)

        # Get AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                # Prepare the messages for processing
                current_messages = []
                
                # Add system messages first
                if current_task:
                    current_messages.extend(current_task.get_system_messages())
                
                # Add session messages
                for msg in st.session_state.messages:
                    if isinstance(msg, Message):
                        current_messages.append(msg)
                    elif isinstance(msg, dict):
                        current_messages.append(Message(**msg))
                    else:
                        current_messages.append(Message(
                            role=getattr(msg, 'role', 'user'),
                            content=str(msg),
                            file_ids=getattr(msg, 'file_ids', None),
                            created_at=getattr(msg, 'created_at', None),
                            updated_at=getattr(msg, 'updated_at', None)
                        ))

                # Use session state task runner with await
                full_response = await st.session_state.task_runner.run_task(
                    tasksmanager_id=st.session_state.current_tasksmanager_id,
                    task_id=st.session_state.current_task_id,
                    running_extra_params={'messages': current_messages}
                )

                # Process response
                if isinstance(full_response, dict) and 'response' in full_response:
                    response_text = full_response['response']
                else:
                    response_text = str(full_response)
                
                # Display the full response with proper formatting
                message_placeholder.write(response_text)

                # Add assistant response and save state
                assistant_message = Message(
                    role="assistant",
                    content=response_text,
                    file_ids=None,
                    created_at=None,
                    updated_at=None
                )
                st.session_state.messages.append(assistant_message)

                # Save messages to both task and session
                save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
                
                # Save to local session file
                if 'browser_session_id' in st.session_state:
                    save_local_session(st.session_state.browser_session_id)

                # Save full state
                if st.session_state.state_location:
                    save_current_state(st.session_state.state_location.state_name)

            except Exception as e:
                st.error(f"Error processing request: {str(e)}")

async def render_main_content():
    """Render the main content area based on selected view."""
    try:
        # Save current state before switching views
        if st.session_state.messages and st.session_state.current_task_id:
            save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
            if st.session_state.state_location:
                save_current_state(st.session_state.state_location.state_name)
            
        if st.session_state.current_view == ViewType.TASK_HIERARCHY:
            from pages.task_hierarchy_view import render_task_hierarchy_view
            await render_task_hierarchy_view()
        elif st.session_state.current_view == ViewType.TOOLS_CATALOG:
            from pages.tools_catalog_view import render_tools_catalog_view
            await render_tools_catalog_view()
        elif st.session_state.current_view == ViewType.AGENTIC_CONFIG:
            from pages.agentic_config_view import render_agentic_config_view
            await render_agentic_config_view()
        else:
            await render_main_chat()
    except Exception as e:
        st.error(f"Error rendering content: {str(e)}")
        print(f"Error in render_main_content: {str(e)}")

def save_last_used_state(state_name: str):
    """Save the name of the last used state to a metadata file."""
    try:
        state_dir = get_state_dir()
        metadata_path = state_dir / "metadata.json"
        
        # Get current metadata if it exists
        current_metadata = {}
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    current_metadata = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading existing metadata: {str(e)}")
                # Continue with empty metadata
        
        # Update metadata
        metadata = {
            "last_used_state": state_name,
            "last_tm_id": st.session_state.get("current_tasksmanager_id"),
            "last_task_id": st.session_state.get("current_task_id"),
            "last_updated": datetime.now().isoformat()
        }
        
        # Merge with existing metadata to preserve other fields
        if isinstance(current_metadata, dict):
            for key, value in current_metadata.items():
                if key not in metadata:
                    metadata[key] = value
        
        # Save metadata
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"✅ Saved metadata: {metadata}")
        except Exception as e:
            print(f"❌ Error writing metadata file: {str(e)}")
            st.session_state.state_error_message = f"Error saving metadata: {str(e)}"
    except Exception as e:
        print(f"❌ Error in save_last_used_state: {str(e)}")
        st.session_state.state_error_message = f"Error saving metadata: {str(e)}"

def get_last_used_state() -> dict:
    """Get the name of the last used state from metadata file."""
    try:
        state_dir = get_state_dir()
        metadata_path = state_dir / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                
                # Validate the metadata
                if not isinstance(metadata, dict):
                    print(f"⚠️ Invalid metadata format: {metadata}")
                    return {}
                
                # Check if the last_used_state exists
                if "last_used_state" in metadata and metadata["last_used_state"]:
                    # Ensure the state name has .json extension for file checking
                    state_name = metadata["last_used_state"]
                    if not state_name.endswith('.json'):
                        state_file_name = f"{state_name}.json"
                    else:
                        state_file_name = state_name
                    
                    state_path = state_dir / state_file_name
                    if not state_path.exists():
                        print(f"⚠️ Last used state file not found: {state_path}")
                        # Reset the metadata to avoid trying to load this file again
                        save_last_used_state("")
                        return {}
                
                return metadata
            except json.JSONDecodeError:
                print(f"⚠️ Error decoding metadata file: {metadata_path}")
                # Backup the corrupted file and create a new one
                backup_path = metadata_path.with_suffix(".json.bak")
                try:
                    import shutil
                    shutil.copy(metadata_path, backup_path)
                    print(f"✅ Backed up corrupted metadata to: {backup_path}")
                except Exception as e:
                    print(f"❌ Error backing up metadata: {str(e)}")
                
                # Create a new empty metadata file
                save_last_used_state("")
                return {}
            except Exception as e:
                print(f"❌ Error loading metadata: {str(e)}")
                return {}
        else:
            print(f"ℹ️ No metadata file found at: {metadata_path}")
            # Create a new empty metadata file
            save_last_used_state("")
            return {}
    except Exception as e:
        print(f"❌ Error in get_last_used_state: {str(e)}")
        return {}

def save_session_state():
    """Save current session state to browser storage."""
    session_data = {
        'messages': st.session_state.messages,
        'current_view': st.session_state.current_view,
        'current_tasksmanager_id': st.session_state.current_tasksmanager_id,
        'current_task_id': st.session_state.current_task_id,
        'current_session_id': st.session_state.current_session_id,
        'chat_sessions': {}  # Store chat history by session ID
    }
    
    # Convert to JSON-serializable format
    serialized_data = json.dumps(session_data, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))

    # Save to browser storage using Streamlit's experimental_set_query_params
    st.experimental_set_query_params(
        session_data=serialized_data
    )

def load_session_state():
    """Load session state from browser storage."""
    params = st.experimental_get_query_params()
    if 'session_data' in params:
        try:
            session_data = json.loads(params['session_data'][0])
            
            # Restore session state
            st.session_state.messages = [Message(**msg) if isinstance(msg, dict) else msg 
                                       for msg in session_data.get('messages', [])]
            st.session_state.current_view = session_data.get('current_view')
            st.session_state.current_tasksmanager_id = session_data.get('current_tasksmanager_id')
            st.session_state.current_task_id = session_data.get('current_task_id')
            st.session_state.current_session_id = session_data.get('current_session_id')
            
            return True
        except Exception as e:
            st.error(f"Error loading session state: {str(e)}")
    return False

def generate_session_id():
    """Generate a unique session ID for the browser."""
    if 'browser_session_id' not in st.session_state:
        st.session_state.browser_session_id = "anonymous"
    return st.session_state.browser_session_id

def get_session_filename(view_type: ViewType = None) -> str:
    """Get the appropriate session filename based on view type."""
    if view_type == ViewType.TASK_HIERARCHY:
        return "task_hierarchy_view_default.json"
    elif view_type == ViewType.TOOLS_CATALOG:
        return "tools_catalog_view_default.json"
    elif view_type == ViewType.AGENTIC_CONFIG:
        return "agentic_config_view_default.json"
    else:
        return "chat_view_default.json"

def save_local_session(session_id: str = None):
    """Save session data to local storage."""
    session_dir = get_state_dir() / "sessions"
    session_dir.mkdir(exist_ok=True)
    
    session_data = {
        'messages': st.session_state.messages,
        'current_view': st.session_state.current_view,
        'current_tasksmanager_id': st.session_state.current_tasksmanager_id,
        'current_task_id': st.session_state.current_task_id,
        'current_session_id': st.session_state.current_session_id,
        'last_access': datetime.now().isoformat()
    }
    
    # Use view-specific session file
    session_file = session_dir / get_session_filename(st.session_state.current_view)
    with open(session_file, 'w') as f:
        json.dump(session_data, f, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))

def load_local_session(session_id: str = None):
    """Load session data from local storage."""
    session_file = get_state_dir() / "sessions" / get_session_filename(st.session_state.current_view)
    if session_file.exists():
        with open(session_file) as f:
            session_data = json.load(f)
            
        # Restore session state
        st.session_state.messages = [Message(**msg) if isinstance(msg, dict) else msg 
                                   for msg in session_data.get('messages', [])]
        st.session_state.current_view = session_data.get('current_view')
        st.session_state.current_tasksmanager_id = session_data.get('current_tasksmanager_id')
        st.session_state.current_task_id = session_data.get('current_task_id')
        st.session_state.current_session_id = session_data.get('current_session_id')

def cleanup_old_sessions(max_age_days: int = 7):
    """Clean up old session files."""
    session_dir = get_state_dir() / "sessions"
    if not session_dir.exists():
        return
        
    now = datetime.now()
    for session_file in session_dir.glob("*.json"):
        try:
            with open(session_file) as f:
                session_data = json.load(f)
            last_access = datetime.fromisoformat(session_data['last_access'])
            
            if (now - last_access).days > max_age_days:
                session_file.unlink()
        except Exception as e:
            print(f"Error cleaning up session {session_file}: {str(e)}")

def clear_session_state():
    """Clear the current session state."""
    if st.session_state.current_task_id and st.session_state.messages:
        # Save current messages before clearing
        save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
    
    # Clean up session files
    cleanup_session_files()
    
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.session_state.current_tasksmanager_id = None
    st.session_state.current_task_id = None
    
    # Save the empty session state to persist the changes
    save_local_session()
    print("\n🗑️ Cleared main chat session")

def save_chat_messages(task_id: str, messages: List[Message]):
    """Save chat messages to task's current session."""
    persistence_model = st.session_state.persistence_model
    task: Task = persistence_model.tasks.read(task_id)
    session_id = st.session_state.current_session_id
    
    if task and session_id:
        # Save to task
        if not hasattr(task, 'chat_sessions') or task.chat_sessions is None:
            task.chat_sessions = {}
        task.chat_sessions[session_id] = [
            msg.dict() if hasattr(msg, 'dict') else msg for msg in messages
        ]
        persistence_model.tasks.update(task_id, task)
        
        # Save to local session
        if 'browser_session_id' in st.session_state:
            session_data = {
                'messages': messages,
                'current_view': st.session_state.current_view,
                'current_tasksmanager_id': st.session_state.current_tasksmanager_id,
                'current_task_id': st.session_state.current_task_id,
                'current_session_id': st.session_state.current_session_id,
                'last_access': datetime.now().isoformat()
            }
            
            session_dir = get_state_dir() / "sessions"
            session_dir.mkdir(exist_ok=True)
            session_file = session_dir / f"{st.session_state.browser_session_id}.json"
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))

def load_chat_messages(task_id: str) -> List[Message]:
    """Load chat messages from task's current session."""
    persistence_model = st.session_state.persistence_model
    task: Task = persistence_model.tasks.read(task_id)
    session_id = st.session_state.current_session_id
    
    if task and session_id and task.chat_sessions and session_id in task.chat_sessions:
        return [Message(**msg) if isinstance(msg, dict) else msg 
                for msg in task.chat_sessions[session_id]]
    return []

def cleanup_session_files():
    """Remove all session files."""
    session_dir = get_state_dir() / "sessions"
    if session_dir.exists():
        for file in session_dir.glob("*.json"):
            try:
                file.unlink()
            except Exception as e:
                print(f"Error removing session file {file}: {e}")

def initialize_state():
    """Initialize application state from saved state if available."""
    print("\n🔄 Initializing application state")
    
    # Check if state is already initialized to prevent redundant operations
    if 'state_initialized' in st.session_state and st.session_state.state_initialized:
        print("✅ State already initialized")
        return
        
    try:
        # Get the last used state from metadata
        metadata = get_last_used_state()
        last_used_state = metadata.get("last_used_state")
        
        if last_used_state:
            # Ensure the state name has .json extension
            if not last_used_state.endswith('.json'):
                state_file_name = f"{last_used_state}.json"
            else:
                state_file_name = last_used_state
                
            state_path = get_state_dir() / state_file_name
            print(f"📥 Last used state from metadata: {last_used_state}")
            
            # Check if the file exists before trying to load it
            if not state_path.exists():
                print(f"⚠️ Last used state file not found: {state_path}")
                st.session_state.state_error_message = f"Last used state file not found: {last_used_state}"
                st.session_state.state_loaded = False
                st.session_state.default_state_loaded = False
                st.session_state.selected_state_file = ""
                
                # Reset the metadata to avoid trying to load this file again
                save_last_used_state("")
            else:
                try:
                    # Load the state
                    print(f"📥 Loading state from: {state_path}")
                    result = load_state(str(state_path))
                    print(f"📥 Load state result: {result}")
                    
                    # Set state flags
                    st.session_state.state_loaded = True
                    st.session_state.default_state_loaded = True
                    st.session_state.selected_state_file = state_file_name
                    
                    # Restore last used TM and Task
                    last_tm_id = metadata.get("last_tm_id")
                    last_task_id = metadata.get("last_task_id")
                    
                    print(f"📋 Last used TM ID: {last_tm_id}")
                    print(f"📋 Last used Task ID: {last_task_id}")
                    
                    # Only set these if they're not already set
                    if not st.session_state.get('current_tasksmanager_id'):
                        st.session_state.current_tasksmanager_id = last_tm_id
                        
                    if not st.session_state.get('current_task_id'):
                        st.session_state.current_task_id = last_task_id
                        
                    # Find the TM name for the current TM ID to set previous_tm_selection
                    if last_tm_id:
                        persistence_model = st.session_state.persistence_model
                        tasksmanagers = persistence_model.tasksmanagers.list()
                        for tm in tasksmanagers:
                            if tm.id == last_tm_id:
                                st.session_state.previous_tm_selection = tm.name
                                print(f"📋 Setting previous_tm_selection to: {tm.name}")
                                
                                # Also set previous_task_selection to prevent rerun loops
                                if last_task_id:
                                    tasks = get_tasks_for_tasksmanager(last_tm_id)
                                    for task in tasks:
                                        if task.id == last_task_id:
                                            st.session_state.previous_task_selection = task.name
                                            print(f"📋 Setting previous_task_selection to: {task.name}")
                                            break
                                break
                    
                    # Load messages for the current task and session
                    if last_task_id and st.session_state.get('current_session_id'):
                        st.session_state.messages = load_chat_messages(last_task_id)
                        print(f"📋 Loaded {len(st.session_state.messages) if st.session_state.messages else 0} messages")
                    
                    print("✅ State loaded successfully")
                except Exception as e:
                    print(f"❌ Error loading specific state: {str(e)}")
                    st.session_state.state_error_message = f"Error loading state: {str(e)}"
                    st.session_state.state_loaded = False
                    st.session_state.default_state_loaded = False
                    st.session_state.selected_state_file = ""
                    # Reset selection tracking to prevent rerun loops
                    st.session_state.previous_tm_selection = None
                    st.session_state.previous_task_selection = None
        else:
            print("ℹ️ No last used state found")
            st.session_state.state_loaded = False
            st.session_state.default_state_loaded = False
            st.session_state.selected_state_file = ""
            # Reset selection tracking to prevent rerun loops
            st.session_state.previous_tm_selection = None
            st.session_state.previous_task_selection = None
    except Exception as e:
        print(f"❌ Error loading state: {str(e)}")
        st.session_state.state_error_message = f"Error loading state: {str(e)}"
        # Reset state flags on error
        st.session_state.state_loaded = False
        st.session_state.default_state_loaded = False
        st.session_state.selected_state_file = ""
        # Reset selection tracking to prevent rerun loops
        st.session_state.previous_tm_selection = None
        st.session_state.previous_task_selection = None
    
    # Always mark as initialized to prevent loops
    st.session_state.state_initialized = True
    # Reset rerun counter
    st.session_state.rerun_count = 0

def save_empty_state(state_name: str) -> str:
    """Save a completely empty state with no data.
    
    This function creates a state file with empty collections, 
    without copying any data from existing states.
    
    Args:
        state_name: Name of the state to save (without .json extension)
        
    Returns:
        str: Result of save operation
    """
    try:
        state_dir = get_state_dir()
        # Ensure state name has .json extension
        if not state_name.endswith('.json'):
            state_filename = f"{state_name}.json"
        else:
            state_filename = state_name
            state_name = state_name.replace('.json', '')
            
        location = StorageLocation(
            type=StorageType.file,
            location=str(state_dir),
            state_name=f"{state_name}"
        )
        
        # Create a new, completely empty persistence model
        print("  Creating new empty persistence model")
        empty_model = PersistenceModelFactory.persistence_model("inmemory")
        
        # Create a default session with a welcome task manager and task
        print("  Creating default task manager")
        default_tm = TasksManager(
            name="Welcome to Cerebrum",
            model="gpt-4o-mini",
            description="Default session for new state"
        )
        default_tm = empty_model.tasksmanagers.create(default_tm)
        
        # Create a default task with a welcome message
        print("  Creating default task")
        default_task = Task(
            name="Getting Started",
            description="Learn how to use Cerebrum",
            tasksmanager_id=default_tm.id,
            messages=[Message(
                role="system",
                content="You are a helpful assistant that guides users in using the Cerebrum framework. Provide clear, concise explanations and be responsive to user questions about functionality."
            )]
        )
        default_task = empty_model.tasks.create(default_task)
        
        # Create a default session for the task
        print("  Creating default session")
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        default_task.chat_sessions = {session_id: []}
        empty_model.tasks.update(default_task.id, default_task)
        
        # Set context state to point to the default session
        context_state = {
            'current_tasksmanager_id': default_tm.id,
            'current_task_id': default_task.id,
            'current_session_id': session_id
        }
        
        print(f"\n📝 Creating empty state with default session: {state_filename}")
        print(f"  Default TM: {default_tm.name} (ID: {default_tm.id})")
        print(f"  Default Task: {default_task.name} (ID: {default_task.id})")
        print(f"  Default Session: {session_id}")
        
        # Save empty state
        result = save_to_storage(empty_model, location)
        print(f"  Save result: {result}")
        
        # Verify file was created
        state_file_path = state_dir / state_filename
        if not state_file_path.exists():
            print(f"⚠️ Warning: Expected state file not found at {state_file_path}")
            st.session_state.state_error_message = f"Failed to create state file: {state_filename}"
            return f"Failed to create state file: {state_filename}"
        else:
            print(f"✅ Confirmed empty state file saved at {state_file_path}")
            st.session_state.state_success_message = f"Empty state created successfully as {state_filename}"
        
        return result
    except Exception as e:
        print(f"❌ Error creating empty state: {str(e)}")
        st.session_state.state_error_message = f"Error creating empty state: {str(e)}"
        return str(e)

def create_new_state(state_name: str, save_current_first: bool = False) -> bool:
    """Create a new state with a default session.
    
    Args:
        state_name: Name for the new state
        save_current_first: Whether to save the current state first
        
    Returns:
        bool: Success or failure
    """
    try:
        print(f"\n🆕 Creating new state with default session: {state_name}")
        
        # Save current state if requested
        if save_current_first and st.session_state.get('selected_state_file'):
            # Save any chat messages first
            if st.session_state.get('messages') and st.session_state.get('current_task_id'):
                save_chat_messages(
                    st.session_state.current_task_id, 
                    st.session_state.messages
                )
            # Save current state
            print(f"  Saving current state first: {st.session_state.selected_state_file}")
            save_current_state(st.session_state.selected_state_file)
        
        # Format state name
        if not state_name.endswith('.json'):
            state_filename = f"{state_name}.json"
        else:
            state_filename = state_name
            state_name = state_name.replace('.json', '')
            
        # Create state file with default session
        print(f"  Creating state with default session as: {state_filename}")
        result = save_empty_state(state_name)
        
        # Now load the newly created state to get the default session
        state_path = str(get_state_dir() / state_filename)
        print(f"  Loading newly created state: {state_path}")
        load_result = load_state(state_path)
        print(f"  Load result: {load_result}")
        
        # Update state selection 
        st.session_state.selected_state_file = state_filename
        
        # Clear state files cache to force reload
        if 'current_state_files' in st.session_state:
            del st.session_state.current_state_files
        
        # Update metadata to use new state
        save_last_used_state(state_name)
        
        # Set success message
        st.session_state.state_success_message = f"New state created as {state_filename}"
        
        print(f"✅ Successfully created new state: {state_filename}")
        return True
    except Exception as e:
        print(f"❌ Error creating new state: {str(e)}")
        st.session_state.state_error_message = f"Error creating state: {str(e)}"
        return False

def main():
    """Main application entry point."""
    print("\n🔄 Starting main application")
    
    # Configure Streamlit page
    st.set_page_config(
        page_title="Cerebrum Chat",
        layout="wide",
        menu_items={
            'Get Help': 'https://github.com/GenBrainAI/cerebrum',
            'About': 'Cerebrum AI Chat Interface'
        }
    )
    
    # Track if we've already run the main function in this session
    if 'main_executed' in st.session_state:
        print("⚠️ Main function called again - potential rerun loop")
    else:
        print("🆕 First execution of main function")
        st.session_state.main_executed = True
    
    # Initialize basic session state
    initialize_session_state()
    
    # Initialize state (single point of state loading)
    initialize_state()
    
    # Check if there's a pending state to load
    if 'pending_state_load' in st.session_state and st.session_state.pending_state_load:
        print(f"\n📥 Loading pending state: {st.session_state.pending_state_load}")
        try:
            load_state(st.session_state.pending_state_load)
            # Clear the pending load to prevent loops
            st.session_state.pending_state_load = None
        except Exception as e:
            print(f"❌ Error loading pending state: {str(e)}")
            st.session_state.state_error_message = f"Error loading pending state: {str(e)}"
            st.session_state.pending_state_load = None
    
    # Generate session ID
    session_id = generate_session_id()
    print(f"\n🔑 Generated session ID: {session_id}")
    
    # Load anonymous session if it exists
    load_local_session()
    
    # Display any state messages
    if 'state_error_message' in st.session_state and st.session_state.state_error_message:
        st.error(st.session_state.state_error_message)
        # Clear the message after displaying it
        st.session_state.state_error_message = None
    
    if 'state_success_message' in st.session_state and st.session_state.state_success_message:
        st.success(st.session_state.state_success_message)
        # Clear the message after displaying it
        st.session_state.state_success_message = None
    
    # Render UI
    with st.sidebar:
        render_logo(width=150)
        st.title("Cerebrum")
        st.divider()
        
        # Add session management
        if st.button("Clear Session"):
            clear_session_state()
            st.rerun()
        
        render_state_management()
        render_chat_management_sidebar()
    
    # Save current session state
    if st.session_state.get('messages') and st.session_state.get('current_task_id'):
        save_local_session(session_id)
    
    # Create placeholder for main content
    if 'main_content_placeholder' not in st.session_state:
        st.session_state.main_content_placeholder = st.empty()
    
    try:
        # Run async content
        asyncio.run(render_main_content())
    except Exception as e:
        st.error(f"Error in application: {str(e)}")
        print(f"❌ Error in application: {str(e)}")

if __name__ == "__main__":
    main()

