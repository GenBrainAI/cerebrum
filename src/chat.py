import streamlit as st
import time
import os
import asyncio
import json
from typing import Optional
from typing import List, Dict
from datetime import datetime
from pathlib import Path

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
    """Save the current state."""
    try:
        state_dir = get_state_dir()
        location = StorageLocation(
            type=StorageType.file,
            location=str(state_dir),
            state_name=f"{state_name}"
        )
        
        # Create context state with only session info (no messages)
        context_state = {
            'current_tasksmanager_id': st.session_state.current_tasksmanager_id,
            'current_task_id': st.session_state.current_task_id,
            'current_session_id': st.session_state.current_session_id
        }
        
        print(f"\n🔍 Context state to save:")
        print(f"  Content: {context_state}")
        
        # Save state with context
        result = save_to_storage(location, context_state=context_state)
        print(f"  Save result: {result}")
        
        # Save metadata about last used state
        save_last_used_state(f"{state_name}")
        
        return result
    except Exception as e:
        print(f"❌ Error saving state: {str(e)}")
        st.error(f"Error saving state: {str(e)}")
        return str(e)

def load_state(state_path: Optional[str] = None):
    """Load Cerebrum state from file."""
    try:
        if not state_path and not st.session_state.default_state_loaded:
            metadata = get_last_used_state()
            if metadata.get("last_used_state"):
                state_path = str(get_state_dir() / metadata["last_used_state"])
            else:
                state_path = "state/default_state.json"
            st.session_state.default_state_loaded = True
        
        if state_path:
            print(f"\n📥 Loading state from: {state_path}")
            
            location = StorageLocation(
                type=StorageType.file,
                location=os.path.dirname(state_path),
                state_name=os.path.basename(state_path)
            )
            
            # Store location in session state
            st.session_state.state_location = location
            
            # Load the state
            json_str = load_from_storage(location)
            state_data = json.loads(json_str)
            
            print(f"\n🔍 Loaded state data:")
            print(f"  Has context_state: {'context_state' in state_data}")
            if 'context_state' in state_data:
                context_state = state_data['context_state']
                print(f"  Context state content: {context_state}")
                
                # Restore session state from context
                if 'messages' in context_state:
                    st.session_state.messages = [Message(**msg) if isinstance(msg, dict) else msg 
                                               for msg in context_state['messages']]
                st.session_state.current_tasksmanager_id = context_state.get('current_tasksmanager_id')
                st.session_state.current_task_id = context_state.get('current_task_id')
                st.session_state.current_session_id = context_state.get('current_session_id')
            
            # Save this as the last used state
            save_last_used_state(os.path.basename(state_path))
            
            return f"Successfully loaded state from {state_path}"
        return "No state file specified"
    except Exception as e:
        if state_path == "state/default_state.json":
            return "No default state loaded"
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
    persistence_model = st.session_state.persistence_model
    
    with st.sidebar:
        st.subheader("State Management")
        
        # Initialize session state variables if not already present
        if 'selected_state_file' not in st.session_state:
            # Try to get the last used state from metadata
            metadata = get_last_used_state()
            st.session_state.selected_state_file = metadata.get("last_used_state", "")
        if 'state_loaded' not in st.session_state:
            st.session_state.state_loaded = False
        if 'state_location' not in st.session_state:
            st.session_state.state_location = None
        
        # State loading section
        st.write("Load State")
        state_files = list((get_state_dir()).glob("*.json"))
        
        # Dropdown selection
        if state_files:
            file_names = [""] + [f.name for f in state_files]
            
            # Handle selection change
            def on_state_select():
                selected = st.session_state.state_selector
                if selected != st.session_state.selected_state_file:
                    st.session_state.selected_state_file = selected
                    st.session_state.state_loaded = False
            
            # Use the last used state as the default index if available
            default_index = 0
            if st.session_state.selected_state_file in file_names:
                default_index = file_names.index(st.session_state.selected_state_file)
            
            selected_state = st.selectbox(
                "Select saved state",
                file_names,
                index=default_index,
                key="state_selector",
                on_change=on_state_select
            )
            
            # Auto-load the last used state if not already loaded
            if (not st.session_state.state_loaded and 
                st.session_state.selected_state_file and 
                st.session_state.selected_state_file in file_names):
                try:
                    state_to_load = str(get_state_dir() / st.session_state.selected_state_file)
                    result = load_state(state_to_load)
                    st.session_state.state_loaded = True
                except Exception as e:
                    st.error(f"Error loading state: {str(e)}")
        
        # Manual path input
        manual_state_path = st.text_input("Or enter state file path")
        
        # Action buttons
        if selected_state or manual_state_path:
            state_to_load = str(get_state_dir() / selected_state) if selected_state else manual_state_path
            if st.button("Load State", use_container_width=True):
                try:
                    result = load_state(state_to_load)
                    st.session_state.state_loaded = True
                    st.success(result)
                except Exception as e:
                    st.error(f"Error loading state: {str(e)}")
            
            if selected_state and st.session_state.state_loaded:
                if st.button("Save State", use_container_width=True):
                    try:
                        # Save current state including chat messages
                        if st.session_state.get('messages') and st.session_state.get('current_task_id'):
                            save_chat_messages(
                                st.session_state.current_task_id, 
                                st.session_state.messages
                            )
                        result = save_current_state(selected_state)
                        st.success("State saved successfully")
                    except Exception as e:
                        st.error(f"Error saving state: {str(e)}")
        
        st.write("---")
        
        # New state creation
        if persistence_model.tasksmanagers.list():
            st.write("Create New State")
            new_state_name = st.text_input("New State Name")
            if st.button("Create State"):
                if new_state_name:
                    try:
                        result = save_current_state(new_state_name)
                        new_state_filename = f"{new_state_name}.json"
                        # Use rerun to update the UI with new state
                        st.success(f"New state created as {new_state_filename}")
                        st.session_state.state_selector = new_state_filename
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating state: {str(e)}")
                else:
                    st.error("Please enter a name for the new state")


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
    # Persistence and task runner
    if 'persistence_model' not in st.session_state:
        st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
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
    if st.session_state.tm_selector == "+ New Chat":
        st.session_state.creating_new_chat = True
        st.session_state.messages = []
        st.session_state.current_session_id = None
    else:
        st.session_state.creating_new_chat = False
        # Create new session for selected task
        if st.session_state.current_task_id:
            session_id = create_new_session(st.session_state.current_task_id)
            st.session_state.current_session_id = session_id
            st.session_state.messages = []

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
                    
                    st.rerun()
            
            with col2:
                if st.button("Cancel", key="cancel_create"):
                    st.session_state.creating_new_chat = False
                    st.rerun()
    
    # Existing Chats Section
    if tasksmanagers:
        st.markdown("---")
        st.subheader("Existing Chats")
        
        # TaskManager selection
        tm_options = {tm.name: tm.id for tm in tasksmanagers}
        selected_tm = st.selectbox(
            "Select Task Manager",
            options=list(tm_options.keys()),
            key="tm_selector",
            on_change=on_tm_select
        )
        
        if selected_tm:
            selected_tm_id = tm_options[selected_tm]
            tasks = get_tasks_for_tasksmanager(selected_tm_id)
            
            if tasks:
                # Task selection
                task_options = {task.name: task.id for task in tasks}
                selected_task = st.selectbox(
                    "Select Task",
                    options=list(task_options.keys()),
                    key="task_selector"
                )
                
                if selected_task:
                    selected_task_id = task_options[selected_task]
                    
                    if (selected_tm_id != st.session_state.current_tasksmanager_id or 
                        selected_task_id != st.session_state.current_task_id):
                        
                        # Update session state
                        st.session_state.current_tasksmanager_id = selected_tm_id
                        st.session_state.current_task_id = selected_task_id
                        st.session_state.messages = []
                        
                        # Create new session
                        session_id = create_new_session(selected_task_id)
                        st.session_state.current_session_id = session_id
                        
                        st.rerun()

async def render_main_chat():
    """Render the main chat interface with context information."""
    from server.models.task import Task  # Add this import at the top
    
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
    current_task: Optional[Task] = None
    if st.session_state.current_task_id:
        task_data = persistence_model.tasks.read(st.session_state.current_task_id)
        if isinstance(task_data, dict):
            current_task = Task(**task_data)
        else:
            current_task = task_data

    # Load chat messages for current session
    if st.session_state.current_task_id and st.session_state.current_session_id:
        if not st.session_state.messages:  # Only load if messages are empty
            st.session_state.messages = load_chat_messages(st.session_state.current_task_id)
    
    # Display chat messages
    if st.session_state.messages is not None:
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
                    
                # Simulate streaming
                current_response = ""
                for chunk in response_text.split():
                    current_response += chunk + " "
                    time.sleep(0.02)
                    message_placeholder.write(current_response + "▌")
                message_placeholder.write(current_response)

                # Add assistant response and save state
                assistant_message = Message(
                    role="assistant",
                    content=current_response,
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
            from src.pages.task_hierarchy_view import render_task_hierarchy_view
            await render_task_hierarchy_view()
        elif st.session_state.current_view == ViewType.TOOLS_CATALOG:
            from src.pages.tools_catalog_view import render_tools_catalog_view
            await render_tools_catalog_view()
        elif st.session_state.current_view == ViewType.AGENTIC_CONFIG:
            from src.pages.agentic_config_view import render_agentic_config_view
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
        metadata = {
            "last_used_state": state_name,
            "last_tm_id": st.session_state.get("current_tasksmanager_id"),
            "last_task_id": st.session_state.get("current_task_id")
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
    except Exception as e:
        st.error(f"Error saving metadata: {str(e)}")

def get_last_used_state() -> dict:
    """Get the name of the last used state from metadata file."""
    try:
        state_dir = get_state_dir()
        metadata_path = state_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading metadata: {str(e)}")
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

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Cerebrum Chat",
        layout="wide",
        menu_items={
            'Get Help': 'https://github.com/GenBrainAI/cerebrum',
            'About': 'Cerebrum AI Chat Interface'
        }
    )
    
    # Initialize basic session state
    initialize_session_state()
    
    # Generate session ID
    session_id = generate_session_id()
    
    # Load anonymous session if it exists
    load_local_session()
    
    # Load last used state if available
    if not st.session_state.default_state_loaded:
        metadata = get_last_used_state()
        if metadata.get("last_used_state"):
            state_path = str(get_state_dir() / metadata["last_used_state"])
            load_state(state_path)
            st.session_state.default_state_loaded = True
            
            # Restore last used TM and Task
            st.session_state.current_tasksmanager_id = metadata.get("last_tm_id")
            st.session_state.current_task_id = metadata.get("last_task_id")
    
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

if __name__ == "__main__":
    main()

