import streamlit as st
import time
import os
import asyncio
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

# Initialize persistence model and task runner
persistence_model = PersistenceModelFactory.persistence_model("inmemory")
task_runner = TaskRunner(persistence_model)

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
        result = save_to_storage(location)
        return result
    except Exception as e:
        st.error(f"Error saving state: {str(e)}")
        return str(e)

def load_state(state_path: Optional[str] = None):
    """Load Cerebrum state from file."""
    try:
        if not state_path and not st.session_state.default_state_loaded:
            # Try to load default state
            state_path = "state/default_state.json"
            st.session_state.default_state_loaded = True
        
        if state_path:
            location = StorageLocation(
                type=StorageType.file,
                location=os.path.dirname(state_path),
                state_name=os.path.basename(state_path)
            )
            
            # Store location in session state for future saves
            st.session_state.state_location = location
            
            json_str = load_from_storage(location)
            return f"Successfully loaded state from {state_path} with length {len(json_str)}"
        return "No state file specified"
    
    except Exception as e:
        if state_path == "state/default_state.json":
            return "No default state loaded"
        return f"Error loading state: {str(e)}"

def render_state_management():
    """Render the state management section in the sidebar."""
    with st.sidebar:
        st.subheader("State Management")
        
        # State loading section
        st.write("Load State")
        state_files = list((get_state_dir()).glob("*.json"))
        if state_files:
            selected_state = st.selectbox(
                "Select saved state",
                [""] + [f.name for f in state_files]
            )
            if selected_state:
                if st.button("Load Selected State"):
                    result = load_state(str(get_state_dir() / selected_state))
                    st.success(result)
        
        # Manual state file path input
        manual_state_path = st.text_input("Or enter state file path")
        if st.button("Load State File"):
            result = load_state(manual_state_path if manual_state_path else None)
            st.success(result)
        
        # State saving section
        if persistence_model.tasksmanagers.list():  # Only show if there's state to save
            st.write("---")
            st.write("Save Current State")
            new_state_name = st.text_input("State Name")
            if st.button("Save State") and new_state_name:
                try:
                    result = save_current_state(new_state_name)
                    st.success(f"State saved successfully as {new_state_name}.json")
                except Exception as e:
                    st.error(f"Error saving state: {str(e)}")


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
        model="gpt-4",  # You might want to make this configurable
        description="Chat session TasksManager"
    )
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
    """Initialize session state variables if they don't exist"""
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
    if 'default_state_loaded' not in st.session_state:
        st.session_state.default_state_loaded = False

def get_task_system_messages(task_id: str) -> List[Dict]:
    """Get system messages for a specific task"""
    if not task_id:
        return []
    
    task = persistence_model.tasks.read(task_id)
    if task and task.messages:
        # Return only system messages from the task
        return [msg.dict() for msg in task.messages if isinstance(msg, dict) and msg.get('role') == 'system' 
                or getattr(msg, 'role', None) == 'system']
    return []

def create_new_session(task_id: str) -> str:
    """Create a new chat session for a task"""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task = persistence_model.tasks.read(task_id)
    if task:
        if not hasattr(task, 'chat_sessions'):
            task.chat_sessions = {}
        task.chat_sessions[session_id] = []
        persistence_model.tasks.update(task_id, task)
    return session_id

def save_session_messages(task_id: str, session_id: str, messages: List[Dict]):
    """Save messages for a specific chat session"""
    if not task_id or not session_id:
        return
        
    task = persistence_model.tasks.read(task_id)
    if task:
        if not hasattr(task, 'chat_sessions'):
            task.chat_sessions = {}
        task.chat_sessions[session_id] = [msg.dict() if hasattr(msg, 'dict') else msg for msg in messages]
        persistence_model.tasks.update(task_id, task)

def get_session_messages(task_id: str, session_id: str) -> List[Dict]:
    """Get messages for a specific chat session"""
    task = persistence_model.tasks.read(task_id)
    if task and hasattr(task, 'chat_sessions'):
        return task.chat_sessions.get(session_id, [])
    return []

def get_chat_sessions(task_id: str) -> Dict[str, List[Dict]]:
    """Get all chat sessions for a task"""
    task = persistence_model.tasks.read(task_id)
    if task and hasattr(task, 'chat_sessions'):
        return task.chat_sessions
    return {}

def on_tm_select():
    """Callback when TaskManager selection changes"""
    if st.session_state.tm_selector == "+ New Chat":
        st.session_state.creating_new_chat = True
    else:
        st.session_state.creating_new_chat = False

def load_state(state_path: Optional[str] = None):
    """Load Cerebrum state from file."""
    try:
        if not state_path and not st.session_state.default_state_loaded:
            # Try to load default state
            state_path = "state/default_state.json"
            st.session_state.default_state_loaded = True
        
        if state_path:
            location = StorageLocation(
                type=StorageType.file,
                location=os.path.dirname(state_path),
                state_name=os.path.basename(state_path)
            )
            
            # Store location in session state for future saves
            st.session_state.state_location = location
            
            json_str = load_from_storage(location)
            return f"Successfully loaded state from {state_path} with length {len(json_str)}"
        return "No state file specified"
    
    except Exception as e:
        if state_path == "state/default_state.json":
            return "No default state loaded"
        return f"Error loading state: {str(e)}"
    
    except Exception as e:
        return f"Error loading state: {str(e)}"

def get_available_tasksmanagers():
    """
    Get list of available TasksManagers sorted by creation date
    """
    try:
        tasksmanagers = persistence_model.tasksmanagers.list()
        # Sort by creation date if available, otherwise by name
        return sorted(
            tasksmanagers,
            key=lambda x: (x.created_at or '', x.name),
            reverse=True  # Most recent first
        )
    except Exception as e:
        st.error(f"Error fetching TasksManagers: {str(e)}")
        return []

def get_tasks_for_tasksmanager(tasksmanager_id: str):
    """
    Get list of tasks for a specific TasksManager sorted by creation date
    """
    try:
        all_tasks = persistence_model.tasks.list()
        tasks = [task for task in all_tasks if task.tasksmanager_id == tasksmanager_id]
        # Sort by creation date if available, otherwise by name
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

def render_sidebar():
    """Render the sidebar UI"""
    with st.sidebar:

        # Logo and title
        render_logo(width=150)

        st.title("Cerebrum")
        
        st.divider()
        
        # # Navigation Links
        # st.subheader("Navigation")
        # nav_col1, nav_col2 = st.columns(2)
        
        # with nav_col1:
        #     st.markdown('<a href="/" target="_self" style="text-decoration: none; color: inherit;">💬 Chat</a>', unsafe_allow_html=True)
            
        # with nav_col2:
        #     st.markdown('<a href="/pages/context_management" target="_self" style="text-decoration: none; color: inherit;">🧠 Context</a>', unsafe_allow_html=True)
        
        # st.divider()


        # State Management section
        render_state_management()
        
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
                        task = persistence_model.tasks.read(task_id)
                        if not task.chat_sessions:
                            session_id = task.create_session()
                            st.session_state.current_session_id = session_id
                        
                        # Save state if location exists
                        if st.session_state.get('state_location'):
                            save_current_state(st.session_state.state_location.state_name)
                        
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
            
            # Default to current selection if exists
            default_index = 0
            if st.session_state.current_tasksmanager_id:
                current_tm = next((tm for tm in tasksmanagers 
                                if tm.id == st.session_state.current_tasksmanager_id), None)
                if current_tm and current_tm.name in tm_options:
                    default_index = list(tm_options.keys()).index(current_tm.name)
            
            selected_tm = st.selectbox(
                "Select Chat",
                options=list(tm_options.keys()),
                index=default_index,
                key="tm_selector"
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
                            
                            # Load task and handle session
                            selected_task_obj = persistence_model.tasks.read(selected_task_id)
                            if selected_task_obj:
                                if not selected_task_obj.chat_sessions:
                                    session_id = selected_task_obj.create_session()
                                    st.session_state.messages = []
                                else:
                                    # Use most recent session
                                    session_id = max(selected_task_obj.chat_sessions.keys())
                                    st.session_state.messages = selected_task_obj.get_session_messages(session_id)
                                
                                st.session_state.current_session_id = session_id
                                persistence_model.tasks.update(selected_task_obj.id, selected_task_obj)
                                st.rerun()


def render_main_chat():
    """Render the main chat interface"""
    tasksmanagers = get_available_tasksmanagers()
    
    if st.session_state.current_tasksmanager_id is None:
        st.info("Please create a new chat or select an existing one to begin.")
        return

    current_tm = next((tm for tm in tasksmanagers 
                      if tm.id == st.session_state.current_tasksmanager_id), None)
    if current_tm:
        st.title(current_tm.name)
    
    # Session management
    if st.session_state.current_task_id:
        task = persistence_model.tasks.read(st.session_state.current_task_id)
        
        # TODO: Handle a case where task is none.

        # Session management UI
        col1, col2 = st.columns([3, 1])
        
        # Initialize chat_sessions if needed
        if not hasattr(task, 'chat_sessions') or task.chat_sessions is None:
            task.chat_sessions = {}
            persistence_model.tasks.update(task.id, task)
        
        # Get existing sessions or create first session
        if not task.chat_sessions:
            session_id = task.create_session()
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
            persistence_model.tasks.update(task.id, task)
        
        with col1:
            # Show session selection if there are multiple sessions
            if len(task.chat_sessions) > 1:
                session_options = list(task.chat_sessions.keys())
                selected_session = st.selectbox(
                    "Select Chat Session",
                    options=session_options,
                    index=session_options.index(st.session_state.current_session_id) 
                        if st.session_state.current_session_id in session_options else 0
                )
                if selected_session != st.session_state.current_session_id:
                    st.session_state.current_session_id = selected_session
                    st.session_state.messages = task.get_session_messages(selected_session)
                    st.rerun()
        
        with col2:
            # Button to create new session
            if st.button("New Session"):
                session_id = task.create_session()
                st.session_state.current_session_id = session_id
                st.session_state.messages = []
                persistence_model.tasks.update(task.id, task)
                st.rerun()
        
        # Ensure we have a current session
        if not st.session_state.current_session_id:
            session_id = task.create_session()
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
            persistence_model.tasks.update(task.id, task)
            st.rerun()
    
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
                # Prepare the messages for processing - all in Message format
                current_messages = []
                
                # Add system messages first
                current_messages.extend(task.get_system_messages())  # Already returns List[Message]
                
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

                # Run async task in sync context
                full_response = asyncio.run(
                    task_runner.run_task(
                        tasksmanager_id=st.session_state.current_tasksmanager_id,
                        task_id=st.session_state.current_task_id,
                        running_extra_params={'messages': current_messages}
                    )
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

                # Add assistant response to state
                assistant_message = Message(
                    role="assistant",
                    content=current_response,
                    file_ids=None,
                    created_at=None,
                    updated_at=None
                )
                st.session_state.messages.append(assistant_message)

                # Save session messages if task supports sessions
                if hasattr(task, 'add_message_to_session') and st.session_state.current_session_id:
                    task.add_message_to_session(
                        st.session_state.current_session_id,
                        assistant_message
                    )
                    persistence_model.tasks.update(task.id, task)

            except Exception as e:
                st.error(f"Error processing request: {str(e)}")
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

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Cerebrum Chat", 
        layout="wide",
        menu_items={
            'Get Help': 'https://github.com/GenBrainAI/cerebrum',
            'About': 'Cerebrum AI Chat Interface'
        }
    )
    initialize_session_state()
    
    # Render both sidebar and main chat interface
    render_sidebar()
    render_main_chat()

if __name__ == "__main__":
    main()

