import streamlit as st
import time
import os
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import traceback
import sys
import uuid
import re
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# Fix import paths
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.controllers.task_observability import TaskObservabilityManager, ObservabilityLevel
from src.server.models.message import Message
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.controllers.persistence_controller import load_from_storage, save_to_storage
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.persistence.persistence_model import PersistenceModelBase 
from src.server.views.models.view_types import ViewType
from src.server.views.utils.async_utils import run_async_sync

def get_project_root() -> Path:
    """Get the absolute path to the project root."""
    # Assumes this file is in src/chat.py
    return Path(__file__).parent.parent

def get_state_dir() -> Path:
    """Get the state directory path, creating it if necessary."""
    state_dir = get_project_root() / "state"
    state_dir.mkdir(exist_ok=True)
    return state_dir

def ensure_notebook_directory() -> Path:
    """Ensure the notebooks directory exists and return its path."""
    notebook_dir = get_project_root() / "notebooks"
    notebook_dir.mkdir(exist_ok=True)
    return notebook_dir

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
                                        # Debug print for task data
                                        print(f"\n🔍 Task data for {task_id}:")
                                        print(f"  crewai_config_id: {task_data.get('crewai_config_id')}")
                                        persistence_model.tasks.create(Task(**task_data))
                                elif collection_name == 'crewai_config':
                                    # Debug print for crewai_config data
                                    print(f"\n🔍 CrewAI config data:")
                                    for config_id, config_data in raw_data.items():
                                        print(f"  Config ID: {config_id}")
                                        # Create CrewAIConfig objects properly
                                        from src.server.models.agent import CrewAIConfig
                                        persistence_model.crewai_config.create(CrewAIConfig(**config_data))
                                else:
                                    # For other collections, use collection method
                                    collection = persistence_model.collection(collection_name)
                                    for item_id, item_data in raw_data.items():
                                        try:
                                            collection.create(item_id, item_data)
                                        except Exception as e:
                                            print(f"❌ Error creating {collection_name} item {item_id}: {str(e)}")
                                print(f"  Loaded {collection_name}: {len(raw_data) if isinstance(raw_data, dict) else 'non-dict data'}")
                            except Exception as e:
                                print(f"❌ Error loading {collection_name}: {str(e)}")
                        else:
                            print(f"  Empty {collection_name} in state data")
                
                # Add verification of loaded tasks with crewai_config_id
                print("\n🔍 Verifying loaded tasks with crewai_config_id:")
                tasks = persistence_model.tasks.list()
                for task in tasks:
                    if hasattr(task, 'crewai_config_id') and task.crewai_config_id:
                        print(f"  Task {task.id} ({task.name}) has crewai_config_id: {task.crewai_config_id}")
                        # Verify the config exists
                        config = persistence_model.crewai_config.read(task.crewai_config_id)
                        if config:
                            print(f"    ✅ CrewAI config found: {config.id}")
                        else:
                            print(f"    ❌ CrewAI config NOT found for ID: {task.crewai_config_id}")
                
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
        
        st.write("Demo States")
        
        if st.button("Load Concert Trip Planner", key="load_concert_trip_btn", use_container_width=True):
            try:
                with st.spinner("Loading Concert Trip Planner demo..."):
                    concert_state_path = str(get_state_dir() / "concert_travel_planner.json")
                    if Path(concert_state_path).exists():
                        result = load_state(concert_state_path)
                        st.session_state.state_loaded = True
                        st.session_state.state_success_message = "Concert Trip Planner demo loaded successfully!"
                        st.rerun()
                    else:
                        st.session_state.state_error_message = "Concert Trip Planner demo state not found"
            except Exception as e:
                st.session_state.state_error_message = f"Error loading Concert Trip Planner demo: {str(e)}"
        
        if st.button("Load Task Tree Demo", key="load_task_tree_btn", use_container_width=True):
            try:
                with st.spinner("Loading Task Tree demo..."):
                    task_tree_state_path = str(get_state_dir() / "task_tree_demo.json")
                    if Path(task_tree_state_path).exists():
                        result = load_state(task_tree_state_path)
                        st.session_state.state_loaded = True
                        st.session_state.state_success_message = "Task Tree demo loaded successfully!"
                        st.rerun()
                    else:
                        st.session_state.state_error_message = "Task Tree demo state not found"
            except Exception as e:
                st.session_state.state_error_message = f"Error loading Task Tree demo: {str(e)}"
        
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
    nav_cols = st.columns(6)  # Updated to 6 columns to include human-in-the-loop
    
    with nav_cols[0]:
        if st.button("💬", help="Switch to chat view", key="switch_to_chat"):
            # Save current messages if they exist before switching views
            if st.session_state.messages and st.session_state.current_task_id and st.session_state.current_session_id:
                save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
            
            st.session_state.chat_view_mode = 'chat'
            st.session_state.show_observability = False
            st.rerun()
    with nav_cols[1]:
        if st.button("📊", help="Switch to observability view", key="switch_to_observability"):
            # Save current messages if they exist before switching views
            if st.session_state.messages and st.session_state.current_task_id and st.session_state.current_session_id:
                save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
                
            st.session_state.chat_view_mode = 'observability'
            st.session_state.show_observability = True
            st.rerun()
    with nav_cols[2]:
        if st.button("📁", help="View session info", key="switch_to_session_info"):
            # Save current messages if they exist before switching views
            if st.session_state.messages and st.session_state.current_task_id and st.session_state.current_session_id:
                save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
                
            st.session_state.chat_view_mode = 'session_info'
            st.rerun()
    with nav_cols[3]:
        if st.button("🧠", help="Human-in-the-Loop", key="switch_to_hitl"):
            # Save current messages if they exist before switching views
            if st.session_state.messages and st.session_state.current_task_id and st.session_state.current_session_id:
                save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
                
            # Import and call the human input view function
            from src.pages.human_input_view import render_human_input_view
            st.session_state.chat_view_mode = 'human_input'
            
            # We'll set a flag to render the human input view instead
            st.session_state.render_human_input = True
            st.rerun()
    
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
    """Initialize session state variables if they don't exist."""
    # Main required state variables
    if "persistence_model" not in st.session_state:
        st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    if "task_runner" not in st.session_state:
        st.session_state.task_runner = TaskRunner(st.session_state.persistence_model)
        # Schedule async initialization using our helper
        run_async_sync(st.session_state.task_runner.initialize())
    
    # Task and conversation management
    if "current_tasksmanager_id" not in st.session_state:
        st.session_state.current_tasksmanager_id = None
    
    if "current_task_id" not in st.session_state:
        st.session_state.current_task_id = None
    
    # Add support for sequences
    if "current_sequence_id" not in st.session_state:
        st.session_state.current_sequence_id = None
    
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    
    # Add current_view initialization
    if "current_view" not in st.session_state:
        st.session_state.current_view = None
        
    # Messages management
    if "messages" not in st.session_state:
        st.session_state.messages = []

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
            msg.model_dump() if hasattr(msg, 'model_dump') else (msg.dict() if hasattr(msg, 'dict') else msg) for msg in messages
        ]
        persistence_model.tasks.update(task_id, task)

def get_session_messages(task_id: str, session_id: str) -> List[Dict]:
    """Get messages for a specific chat session"""
    # Use session state persistence model
    persistence_model = st.session_state.persistence_model
    task = persistence_model.tasks.read(task_id)
    if task:
        task_dict = task.model_dump() if hasattr(task, 'model_dump') else (task.dict() if hasattr(task, 'dict') else task)
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
    """Handle change in TaskManager selection."""
    # ... existing code ...
    # If tasksmanager changed, reset task selection and messages
    if st.session_state.tm_selector != st.session_state.get('previous_tm_selection', None):
        print(f"🔄 TaskManager changed from '{st.session_state.get('previous_tm_selection')}' to '{st.session_state.tm_selector}'")
        st.session_state.previous_tm_selection = st.session_state.tm_selector
        
        # Get the selected TM id
        try:
            tasksmanagers = get_available_tasksmanagers()
            for tm in tasksmanagers:
                if tm.name == st.session_state.tm_selector:
                    st.session_state.current_tasksmanager_id = tm.id
                    
                    # Reset task selection
                    st.session_state.current_task_id = None
                    # Reset sequence ID when changing task manager
                    st.session_state.current_sequence_id = None
                    st.session_state.messages = []
                    
                    # Try to select first task if available
                    tasks = get_tasks_for_tasksmanager(tm.id)
                    if tasks:
                        first_task = tasks[0]
                        st.session_state.current_task_id = first_task.id
                        
                        # Check if this is part of a sequence
                        if hasattr(tm, 'task_sequences') and tm.task_sequences:
                            for seq_id, seq in tm.task_sequences.items():
                                if first_task.id in seq.task_ids:
                                    st.session_state.current_sequence_id = seq_id
                                    st.session_state.is_in_sequence = True
                                    print(f"✅ Task {first_task.id} is part of sequence {seq_id}")
                                    break
                        
                        # Create new session for this task
                        session_id = create_new_session(first_task.id)
                        st.session_state.current_session_id = session_id
                    break
        except Exception as e:
            st.error(f"Error selecting TaskManager: {str(e)}")
            print(f"❌ Error in on_tm_select: {e}")
    # ... existing code ...

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

def generate_sequence_summary(sequence_result: Dict, sequence: Any, tasks: List[Task]) -> str:
    """Generate a summary of the task sequence execution with insights on data passing."""
    summary_lines = []
    
    # Add header
    summary_lines.append(f"## Task Sequence Execution Summary")
    summary_lines.append(f"**Sequence:** {sequence.name}")
    summary_lines.append(f"**Total tasks:** {len(sequence.task_ids)}")
    
    # Get task data flow
    summary_lines.append("\n### Data Flow Between Tasks")
    
    # Track successful and failed tasks
    successful_tasks = []
    failed_tasks = []
    
    # Create a map of tasks by ID for easy lookup
    task_map = {task.id: task for task in tasks}
    
    for i, task_id in enumerate(sequence.task_ids):
        task = task_map.get(task_id)
        if not task:
            continue
            
        # Check task result
        if "results" in sequence_result and task_id in sequence_result["results"]:
            result = sequence_result["results"][task_id]
            if "error" in result:
                status = "❌ Failed"
                failed_tasks.append((task, result.get("error", "Unknown error")))
            else:
                status = "✅ Success"
                successful_tasks.append(task)
        else:
            status = "⚠️ Unknown"
            
        # Get task dependencies
        dependencies = getattr(task, 'input_from_tasks', [])
        dependency_names = []
        for dep_id in dependencies:
            dep_task = task_map.get(dep_id)
            if dep_task:
                dependency_names.append(dep_task.name)
                
        # Format dependency info
        if dependency_names:
            dep_text = f"Inputs from: {', '.join(dependency_names)}"
        else:
            dep_text = "No input dependencies"
            
        # Add task info to summary
        summary_lines.append(f"**{i+1}. {task.name}** - {status}")
        summary_lines.append(f"   {dep_text}")
        
        # Add input/output data summary if available
        if hasattr(task, 'input_data') and task.input_data and isinstance(task.input_data, dict):
            input_keys = list(task.input_data.keys())
            summary_lines.append(f"   Input data keys: {', '.join(input_keys)}")
            
        if hasattr(task, 'output_data') and task.output_data and isinstance(task.output_data, dict):
            output_keys = list(task.output_data.keys())
            summary_lines.append(f"   Output data keys: {', '.join(output_keys)}")
            
        # Add separator between tasks
        summary_lines.append("")
            
    # Add execution summary
    summary_lines.append("\n### Execution Summary")
    summary_lines.append(f"✅ Successful tasks: {len(successful_tasks)}")
    summary_lines.append(f"❌ Failed tasks: {len(failed_tasks)}")
    
    # Add details about failures if any
    if failed_tasks:
        summary_lines.append("\n### Execution Errors")
        for task, error in failed_tasks:
            summary_lines.append(f"❌ **{task.name}**: {error}")
            
    return "\n".join(summary_lines)

def render_task_observability_panel(task_id: str, observability_data: List[Dict[str, Any]]):
    """Render the observability panel for a task."""
    if not observability_data:
        st.info("No observability data available for this task.")
        return
    
    # Get events by category
    state_events = [e for e in observability_data if e.get('metadata', {}).get('state_transition')]
    stats_events = [e for e in observability_data if e.get('metadata', {}).get('execution_stats')]
    tool_call_events = [e for e in observability_data if e.get('metadata', {}).get('tool_call') or e.get('metadata', {}).get('tool_result')]
    handover_events = [e for e in observability_data if e.get('metadata', {}).get('task_handover')]
    stdout_events = [e for e in observability_data if e.get('metadata', {}).get('output_type') == 'stdout']
    
    # Filter out debug events from stdout that aren't relevant for user
    important_stdout_events = []
    for event in stdout_events:
        message = event.get('message', '')
        # Skip most DEBUG log messages and internal state logging
        if ('DEBUG:' in message or message.startswith('🔍 DEBUG:') or 
            'Reading Task' in message or 'Type:' in message or 
            'Is instance of' in message or '✅ Updated Task item' in message or
            'Reading CurriedProxy' in message or 'ChromaDB' in message or
            'Reading TasksManager' in message or 'Added collection' in message):
            continue
        important_stdout_events.append(event)
    
    # Create tabs for different event types
    tabs = st.tabs(["🔧 Tool Calls", "🔄 Task Handovers", "📈 Stats", "📝 Standard Output", "🔄 State Transitions"])
    
    # Tool Calls tab
    with tabs[0]:
        st.subheader("Tool Calls and Results")
        if tool_call_events:
            try:
                import pandas as pd
                
                # Group into pairs of calls and results
                call_result_pairs = {}
                standalone_calls = []
                standalone_results = []
                
                # First pass - collect all calls
                for event in tool_call_events:
                    metadata = event.get('metadata', {})
                    if metadata.get('tool_call'):
                        call_id = metadata.get('call_id')
                        call_result_pairs[call_id] = {'call': event, 'result': None}
                    elif metadata.get('tool_result'):
                        call_id = metadata.get('call_id')
                        if call_id in call_result_pairs:
                            call_result_pairs[call_id]['result'] = event
                        else:
                            standalone_results.append(event)
                
                # Create a formatted display of tool calls with arguments and results
                if call_result_pairs:
                    for call_id, pair in call_result_pairs.items():
                        call = pair['call']
                        result = pair['result']
                        
                        tool_name = call['metadata'].get('tool_name', 'Unknown Tool')
                        timestamp = call['timestamp'].split('T')[1].split('.')[0]  # Extract time
                        
                        # Create expandable section for each tool call
                        with st.expander(f"[{timestamp}] {tool_name}", expanded=False):
                            # Display arguments
                            st.write("**Arguments:**")
                            args = call['metadata'].get('arguments', {})
                            st.json(args)
                            
                            # Display result if available
                            if result:
                                st.write("**Result:**")
                                res_data = result['metadata'].get('result')
                                # Format based on result type
                                if isinstance(res_data, dict):
                                    st.json(res_data)
                                elif isinstance(res_data, list):
                                    st.json(res_data)
                                else:
                                    st.write(res_data)
                                
                                # Show execution time if available
                                exec_time = result['metadata'].get('execution_time')
                                if exec_time:
                                    st.write(f"Execution time: {exec_time:.2f}s")
                            else:
                                st.write("**Result:** Not available")
                else:
                    st.info("No tool calls recorded")
                            
            except Exception as e:
                st.error(f"Error displaying tool calls: {str(e)}")
                
                # Fallback to basic display
                for entry in tool_call_events:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]
                    st.write(f"[{timestamp}] {entry['message']}")
        else:
            st.info("No tool calls recorded")
    
    # Task Handovers tab
    with tabs[1]:
        st.subheader("Task Handovers")
        if handover_events:
            try:
                import pandas as pd
                handovers_data = []
                
                for entry in handover_events:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
                    metadata = entry.get('metadata', {})
                    from_task = metadata.get('from_task_id', 'Unknown')
                    to_task = metadata.get('to_task_id', 'Unknown')
                    
                    # Create expandable section for each handover
                    with st.expander(f"[{timestamp}] Handover: {from_task[:8]}... → {to_task[:8]}...", expanded=False):
                        # Display input data if available
                        input_data = metadata.get('input_data')
                        if input_data:
                            st.write("**Input Data:**")
                            st.json(input_data)
                        
                        # Display any additional metadata
                        other_metadata = {k: v for k, v in metadata.items() 
                                         if k not in ['task_handover', 'from_task_id', 'to_task_id', 'input_data']}
                        if other_metadata:
                            st.write("**Additional Metadata:**")
                            st.json(other_metadata)
            except Exception as e:
                st.error(f"Error displaying handovers: {str(e)}")
                
                # Fallback to basic display
                for entry in handover_events:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]
                    st.write(f"[{timestamp}] {entry['message']}")
        else:
            st.info("No task handovers recorded")
    
    # Stats tab
    with tabs[2]:
        st.subheader("Execution Statistics")
        if stats_events:
            latest_stats = stats_events[-1]['metadata']['execution_stats']
            st.json(latest_stats)
            
            # If we have multiple statistics points, show them as a timeline
            if len(stats_events) > 1:
                try:
                    import pandas as pd
                    stats_data = []
                    
                    for entry in stats_events:
                        timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
                        stats = entry['metadata']['execution_stats']
                        stats_data.append({
                            "Time": timestamp,
                            **{k: v for k, v in stats.items() if isinstance(v, (int, float, str, bool))}
                        })
                    
                    if stats_data:
                        st.write("### Statistics Timeline")
                        stats_df = pd.DataFrame(stats_data)
                        st.dataframe(stats_df, use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying stats timeline: {str(e)}")
        else:
            st.info("No execution statistics available")
            
    # Standard output tab
    with tabs[3]:
        st.subheader("Standard Output")
        
        # Format entries for display
        formatted_lines = []
        for entry in important_stdout_events:
            timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
            message = entry['message']
            formatted_lines.append(f"[{timestamp}] {message}")
            
        if formatted_lines:
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
        else:
            st.info("No standard output captured")
    
    # State transitions tab
    with tabs[4]:
        st.subheader("State Transitions")
        
        if state_events:
            try:
                import pandas as pd
                transitions_data = []
                
                for entry in state_events:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
                    metadata = entry.get('metadata', {})
                    old_state = metadata.get('old_state', 'N/A')
                    new_state = metadata.get('new_state', 'N/A')
                    
                    transitions_data.append({
                        "Time": timestamp,
                        "From State": old_state,
                        "To State": new_state,
                        "Message": entry['message']
                    })
                
                if transitions_data:
                    transitions_df = pd.DataFrame(transitions_data)
                    st.dataframe(transitions_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying transitions data: {str(e)}")
                
                # Fallback to basic display
                for entry in state_events:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]
                    st.write(f"[{timestamp}] {entry['message']}")
        else:
            st.info("No state transitions recorded")

async def process_message(task_id: str, prompt: str) -> str:
    """Process user message and get AI response."""
    try:
        # Clear any previous assistant message that might be pending before adding the new user message
        if st.session_state.messages and len(st.session_state.messages) > 0:
            last_msg = st.session_state.messages[-1]
            if isinstance(last_msg, dict) and last_msg.get('role') == 'assistant' and not last_msg.get('content'):
                st.session_state.messages.pop()
            elif hasattr(last_msg, 'role') and last_msg.role == 'assistant' and not last_msg.content:
                st.session_state.messages.pop()
        
        # Get task runner from session state
        task_runner = st.session_state.task_runner
        
        # Prepare message context - do this ONCE at the top
        message_context = {'messages': st.session_state.messages, 'user_input': prompt, 'user_query': prompt}
        
        # Create messages to save (excluding system messages) - define once and reuse
        messages_to_save = []
        for msg in st.session_state.messages:
            if isinstance(msg, Message) and msg.role != 'system':
                messages_to_save.append(msg)
            elif isinstance(msg, dict) and msg.get('role') != 'system':
                messages_to_save.append(Message(**msg))
        
        # Check for sequences in the tasksmanager
        try:
            # Get task manager ID
            tm_id = st.session_state.current_tasksmanager_id
            tasksmanager = st.session_state.persistence_model.tasksmanagers.read(tm_id)
            
            # Look for sequences where this task is a member
            sequence_id = None
            sequence = None
            
            # Check task_sequences dictionary
            if hasattr(tasksmanager, 'task_sequences') and tasksmanager.task_sequences:
                for seq_id, seq in tasksmanager.task_sequences.items():
                    if task_id in seq.task_ids:
                        sequence_id = seq_id
                        sequence = seq
                        print(f"✅ Found sequence: {seq.name} for task ID {task_id}")
                        break
                
                if sequence and task_id in sequence.task_ids:
                    print(f"✅ Task {task_id} is in sequence {sequence.name}")
                    
                    # Add the prompt to the task's input data
                    for i, tid in enumerate(sequence.task_ids):
                        if tid == task_id:
                            # Set input for this task
                            task = st.session_state.persistence_model.tasks.read(tid)
                            # Ensure task has data attribute
                            if not hasattr(task, 'data'):
                                task.data = {}
                            task.data["user_input"] = prompt
                            st.session_state.persistence_model.tasks.update(tid, task)
                    
                    # Create an expandable section for task sequence observability
                    observability_expander = st.expander("Task Sequence Execution Details", expanded=False)
                    with observability_expander:
                        # Create progress bar and status indicators
                        st.write("### Executing Task Sequence")
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Create tabs for each task in sequence 
                        task_tabs = st.tabs([f"Task {i+1}: {task.name}" for i, task in 
                                            enumerate([st.session_state.persistence_model.tasks.read(tid) 
                                                     for tid in sequence.task_ids])])
                        
                        # Run the whole sequence with message context
                        print(f"🚀 Running task sequence: {sequence.name} with TaskManager ID {tm_id}")
                        print(f"📨 Passing {len(message_context['messages'])} messages to sequence")
                        
                        # Dictionary to collect observability data for each task in sequence
                        observability_data = {}
                        
                        # Store the execution ID for observability tracking
                        execution_id = f"seq_{uuid.uuid4().hex[:8]}"
                        st.session_state.current_execution_id = execution_id
                        
                        # Add execution ID to the context so it can be tracked
                        message_context['execution_id'] = execution_id
                        
                        # Run the sequence
                        sequence_result = await task_runner.run_task_sequence_by_id(
                            sequence_id=sequence_id,
                            tasksmanager_id=tm_id,
                            initial_context=message_context,
                            sequence_execution_id=execution_id
                        )
                        
                        # After the sequence runs, create and add the observability entries for each task
                        observability_data = {}
                        
                        # Get observability for the sequence
                        sequence_observability = task_runner.get_task_observability(f"sequence_{sequence.name}")
                        if sequence_observability:
                            observability_data['sequence'] = sequence_observability.get_all_entries()
                            
                            # Track handovers between tasks if we have results for multiple tasks
                            if "results" in sequence_result and len(sequence_result["results"]) > 1:
                                from src.server.controllers.task_observability import ObservabilityLevel
                                
                                # Get tasks from the sequence
                                task_ids = sequence.task_ids
                                tasks_info = {}
                                for tid in task_ids:
                                    task = st.session_state.persistence_model.tasks.read(tid)
                                    tasks_info[tid] = task.name if task else "Unknown Task"
                                
                                # Record handovers between consecutive tasks
                                prev_task_id = None
                                for i, task_id in enumerate(task_ids):
                                    # Skip the first task as it has no predecessor
                                    if i > 0 and prev_task_id:
                                        # Get input data from current task's result if available
                                        input_data = None
                                        if prev_task_id in sequence_result.get("results", {}):
                                            prev_result = sequence_result["results"][prev_task_id]
                                            if isinstance(prev_result, dict):
                                                input_data = prev_result.get("response", prev_result)
                                            else:
                                                input_data = str(prev_result)
                                        
                                        # Record the handover
                                        sequence_observability.add_task_handover(
                                            from_task_id=prev_task_id,
                                            to_task_id=task_id,
                                            input_data={"user_query": prompt, "previous_task_result": input_data},
                                            metadata={
                                                "from_task_name": tasks_info.get(prev_task_id, "Unknown"),
                                                "to_task_name": tasks_info.get(task_id, "Unknown"),
                                                "sequence_name": sequence.name
                                            }
                                        )
                                    
                                    prev_task_id = task_id
                        
                        # Get individual task observability data
                        for task_id in sequence.task_ids:
                            task_observability = task_runner.get_task_observability(task_id)
                            if task_observability:
                                task_entries = task_observability.get_all_entries()
                                observability_data[task_id] = task_entries
                                
                                # Get the task name for display
                                task = st.session_state.persistence_model.tasks.read(task_id)
                                task_name = task.name if task else f"Task {task_id[:8]}"
                                
                                # Display in the appropriate tab
                                task_idx = sequence.task_ids.index(task_id)
                                with task_tabs[task_idx]:
                                    render_task_observability_panel(task_id, task_entries)
                        
                        # Display sequence-level observability in its own section
                        if 'sequence' in observability_data:
                            # Update progress bar
                            progress_bar.progress(100)
                            status_text.write("✅ Task sequence execution completed")
                            
                            # Find all handover entries
                            handover_entries = [e for e in observability_data['sequence'] 
                                              if e.get('metadata', {}).get('task_handover')]
                        
                        # Complete the progress bar
                        progress_bar.progress(1.0)
                        status_text.write("✅ Task sequence execution completed")
                        
                        # Get sequence observability data if available
                        sequence_observability = None
                        if hasattr(st.session_state, 'current_execution_id'):
                            execution_id = st.session_state.current_execution_id
                            sequence_observability = task_runner.get_sequence_observability(execution_id)
                            
                            if sequence_observability:
                                # Add a tab for sequence observability
                                st.write("### Sequence Events Timeline")
                                
                                # Display sequence events in a pretty format
                                sequence_entries = sequence_observability.get('sequence_entries', [])
                                if sequence_entries:
                                    # Create a dataframe for better display
                                    import pandas as pd
                                    events_data = []
                                    
                                    for entry in sequence_entries:
                                        timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # Extract time
                                        event_type = entry.get('metadata', {}).get('event_type', 'unknown')
                                        message = entry['message']
                                        
                                        events_data.append({
                                            "Time": timestamp,
                                            "Event Type": event_type,
                                            "Message": message
                                        })
                                    
                                    if events_data:
                                        events_df = pd.DataFrame(events_data)
                                        st.dataframe(events_df, use_container_width=True)
                        
                        # Add a summary section
                        st.write("### Sequence Execution Summary")
                        
                        # Get all tasks for the sequence
                        all_sequence_tasks = []
                        for task_id in sequence.task_ids:
                            task = persistence_model.tasks.read(task_id)
                            if task:
                                all_sequence_tasks.append(task)
                        
                        # Generate and display summary
                        if all_sequence_tasks:
                            summary = generate_sequence_summary(sequence_result, sequence, all_sequence_tasks)
                            st.markdown(summary)
                        
                        # Option to include summary in chat
                        include_summary = st.checkbox("Include summary in chat response", value=False)
                        if include_summary:
                            st.session_state.include_sequence_summary = True
                            st.session_state.sequence_summary = summary
                        else:
                            st.session_state.include_sequence_summary = False
                    
                    print(f"✅ Sequence executed with result: {sequence_result}")
                    
                    # Extract the response from the result
                    if "response" in sequence_result and sequence_result["response"]:
                        content = sequence_result["response"]
                    elif "results" in sequence_result:
                        # Try to get the result of the last task in the sequence
                        last_task_id = sequence.task_ids[-1]
                        if last_task_id in sequence_result["results"]:
                            last_result = sequence_result["results"][last_task_id]
                            if isinstance(last_result, dict) and "response" in last_result:
                                content = last_result["response"]
                            else:
                                content = str(last_result)
                        else:
                            content = f"Sequence executed, but no result found for last task {last_task_id}"
                    else:
                        content = str(sequence_result)
                    
                    # Check if we should include sequence summary
                    if st.session_state.get('include_sequence_summary', False) and hasattr(st.session_state, 'sequence_summary'):
                        # Add the sequence summary to the content
                        full_content = f"{content}\n\n---\n\n{st.session_state.sequence_summary}"
                        
                        # Reset the flag and summary
                        st.session_state.include_sequence_summary = False
                        del st.session_state.sequence_summary
                    else:
                        full_content = content
                    
                    # Add sequence result as assistant message
                    assistant_message = Message(
                        role="assistant",
                        content=full_content,
                        file_ids=None,
                        created_at=None,
                        updated_at=None
                    )
                    messages_to_save.append(assistant_message)
                    
                    # Save to persistence model
                    save_chat_messages(task_id, messages_to_save)
                    
                    return full_content
            
        except Exception as e:
            print(f"❌ Error checking for sequences: {e}")
            print(traceback.format_exc())
            # Continue with normal task execution if error occurs
        
        # Standard task execution - using the same message context
        print(f"📨 Running standard task with {len(message_context['messages'])} messages")
        
        # Create an expandable section for task observability
        observability_expander = st.expander("Task Execution Details", expanded=False)
        with observability_expander:
            # Add a spinner and status text
            with st.spinner("Executing task..."):
                status_text = st.empty()
                status_text.write("Starting task execution...")
                
                # Run the task and collect observability data
                result = await task_runner.run_task(
                    tasksmanager_id=st.session_state.current_tasksmanager_id,
                    task_id=task_id,
                    running_extra_params=message_context
                )
                
                # Get observability data after the task is run
                observability = task_runner.get_task_observability(task_id)
                if observability:
                    observability_data = observability.get_all_entries()
                    status_text.write("✅ Task execution completed")
                    
                    # Display observability data
                    render_task_observability_panel(task_id, observability_data)
                else:
                    st.info("No observability data available for this task.")
        
        # Extract content from result if it's a dictionary
        content = result
        if isinstance(result, dict):
            if 'response' in result:
                content = result['response']
            else:
                # Try to convert dict to string for safety
                content = str(result)
        
        # Add assistant response
        assistant_message = Message(
            role="assistant",
            content=content or "No response generated.",
            file_ids=None,
            created_at=None,
            updated_at=None
        )
        messages_to_save.append(assistant_message)
        
        # Save to persistence model
        save_chat_messages(task_id, messages_to_save)
        
        # Return the content string, not the original result which might be a dict
        return content or "No response generated."
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        print(traceback.format_exc())
        return f"Error: {str(e)}"

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
            
            # Check if TaskManager has sequences defined
            try:
                # Get the TasksManager to check for sequences
                tasksmanager = persistence_model.tasksmanagers.read(selected_tm_id)
                has_sequences = hasattr(tasksmanager, 'task_sequences') and tasksmanager.task_sequences
                
                if has_sequences:
                    # Show sequence selector instead of task selector
                    sequences = list(tasksmanager.task_sequences.values())
                    if sequences:
                        sequence_options = {seq.name: seq.id for seq in sequences}
                        
                        st.write("**Task Sequence Detected**")
                        st.info("This Task Manager has sequences defined. When run, tasks will execute in sequence with handover between them.")
                        
                        # Sequence selection
                        selected_sequence = st.selectbox(
                            "Select Sequence",
                            options=list(sequence_options.keys()),
                            key="sequence_selector"
                        )
                        
                        if selected_sequence:
                            selected_sequence_id = sequence_options[selected_sequence]
                            sequence = tasksmanager.task_sequences.get(selected_sequence_id)
                            
                            if sequence and sequence.task_ids:
                                # Show tasks in sequence
                                st.write("**Tasks in sequence:**")
                                for i, task_id in enumerate(sequence.task_ids):
                                    task = persistence_model.tasks.read(task_id)
                                    if task:
                                        st.write(f"{i+1}. {task.name}")
                                
                                # Store sequence info in session state
                                st.session_state.current_sequence_id = selected_sequence_id
                                
                                # Use the first task in sequence for the chat interface
                                first_task_id = sequence.task_ids[0]
                                
                                # Only update if the task ID has changed
                                if st.session_state.get('current_task_id') != first_task_id:
                                    st.session_state.current_task_id = first_task_id
                                    # Create new session
                                    session_id = create_new_session(first_task_id)
                                    st.session_state.current_session_id = session_id
                                
                                # Add a run sequence button
                                if st.button("Run Sequence", key="run_sequence_btn"):
                                    st.info("Running sequence...")
                                    task_runner = st.session_state.task_runner
                                    
                                    # Run the sequence in an async-friendly way
                                    async def run_sequence():
                                        try:
                                            # Create context with messages
                                            initial_context = {
                                                'messages': st.session_state.messages,
                                                'user_query': "Run sequence" # Default user query for sequence runs
                                            }
                                            
                                            print(f"📨 Passing {len(st.session_state.messages)} messages to sequence execution")
                                            
                                            result = await task_runner.run_task_sequence_by_id(
                                                tasksmanager_id=selected_tm_id,
                                                sequence_id=selected_sequence_id,
                                                initial_context=initial_context
                                            )
                                            return result
                                        except Exception as e:
                                            return {"error": str(e)}
                                    
                                    # Run the sequence
                                    sequence_result = run_async_sync(run_sequence())
                                    
                                    # Show results
                                    if "error" in sequence_result:
                                        st.error(f"Error running sequence: {sequence_result['error']}")
                                    else:
                                        st.success("Sequence executed successfully!")
                                        # Add sequence result to chat
                                        result_message = Message(
                                            role="assistant",
                                            content=f"Sequence execution completed. Results:\n\n```json\n{json.dumps(sequence_result, indent=2)}\n```"
                                        )
                                        
                                        # Ensure messages list exists
                                        if st.session_state.messages is None:
                                            st.session_state.messages = []
                                        
                                        # Add message to session state
                                        st.session_state.messages.append(result_message)
                                        
                                        # Save chat messages
                                        save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
                    
                    # Skip the individual task selection
                    return
            except Exception as e:
                print(f"❌ Error checking for sequences: {e}")
                # Continue with normal task selection if error occurs
            
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
                            # Reset sequence ID when manually selecting a task
                            st.session_state.current_sequence_id = None
                            st.session_state.messages = []
                            
                            # Create new session
                            session_id = create_new_session(selected_task_id)
                            st.session_state.current_session_id = session_id
                        else:
                            print(f"  No change in task selection, skipping update")
                    except Exception as e:
                        print(f"❌ Error reading task {selected_task_id}: {e}")

async def render_main_chat():
    """Render the main chat interface."""
    # Get the current tasksmanager and task
    tasksmanager_id = st.session_state.current_tasksmanager_id
    task_id = st.session_state.current_task_id
    session_id = st.session_state.current_session_id
    
    if not tasksmanager_id or not task_id:
        st.info("Please select a task from the sidebar to start chatting.")
        return

    # If we have a framework-specific rendering, use that
    task = st.session_state.persistence_model.tasks.read(task_id)
    
    # Initialize message history if empty
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Chat title
    st.markdown(f"## {task.name}")
    st.markdown(f"*{task.description}*")
    
    # Display task system message if available
    system_messages = get_task_system_messages(task_id)
    if system_messages and not st.session_state.messages:
        with st.expander("Task System Prompt", expanded=False):
            for msg in system_messages:
                st.markdown(f"**{msg['role'].capitalize()}**")
                st.markdown(msg['content'])
    
    # Check for or create a session for this task
    if not session_id:
        session_id = create_new_session(task_id)
        st.session_state.current_session_id = session_id
        print(f"Created new session: {session_id}")
    
    # Load chat messages from session if available
    session_messages = get_session_messages(task_id, session_id)
    if session_messages and not st.session_state.messages:
        st.session_state.messages = session_messages
        print(f"Loaded {len(session_messages)} messages from session")
    
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        role = message.get("role", "")
        content = message.get("content", "")
        
        with st.chat_message(role):
            st.markdown(content)
    
    # Human input component for CrewAI tasks
    from src.server.views.components.human_input_component import render_human_input_component
    if task.framework == "crewai":
        # If CrewAI is waiting for human input, show the component
        from src.server.tools.human_tools import human_input_tool # Import the instance
        if human_input_tool.is_waiting_for_input: # Check the property on the instance
            with st.container():
                st.divider()
                st.subheader("Human Input Requested")
                render_human_input_component(session_id=session_id)
                st.divider()
    
    # Input prompt
    if prompt := st.chat_input("Send a message"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display the user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from the AI
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
        with st.spinner("Thinking..."):
            try:
                # Get response from task
                full_response = await process_message(task_id, prompt)
                
                # Update placeholder with full response
                message_placeholder.markdown(full_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # Save messages to session
                save_session_messages(task_id, session_id, st.session_state.messages)

            except Exception as e:
                print(f"❌ Error processing message: {str(e)}")
                message_placeholder.error(f"An error occurred: {str(e)}")
    
    # Add ability to clear chat history
    if st.session_state.messages:
        if st.button("Clear chat history"):
            st.session_state.messages = []
            # Remove all messages for this session
            save_session_messages(task_id, session_id, [])
            st.experimental_rerun()

async def render_main_content():
    """Render the main content area based on selected view."""
    try:
        # Save current state before switching views
        if st.session_state.messages and st.session_state.current_task_id:
            save_chat_messages(st.session_state.current_task_id, st.session_state.messages)
            if hasattr(st.session_state, 'state_location') and st.session_state.state_location is not None:
                save_current_state(st.session_state.state_location.state_name)
        
        # Check if we need to render the human input view
        if hasattr(st.session_state, 'render_human_input') and st.session_state.render_human_input:
            from src.pages.human_input_view import render_human_input_view
            await render_human_input_view()
            return
            
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
    serialized_data = json.dumps(session_data, default=lambda x: x.model_dump() if hasattr(x, 'model_dump') else (x.dict() if hasattr(x, 'dict') else str(x)))

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
        json.dump(session_data, f, default=lambda x: x.model_dump() if hasattr(x, 'model_dump') else (x.dict() if hasattr(x, 'dict') else str(x)))

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
    try:
        print("\n🗑️ Clearing main chat session")
        
        # Get current task and session information before clearing
        task_id = st.session_state.get('current_task_id')
        session_id = st.session_state.get('current_session_id')
        
        if task_id and session_id:
            print(f"🔍 Clearing ALL sessions for task {task_id}")
            
            # Get the task from the persistence model
            persistence_model = st.session_state.persistence_model
            task = persistence_model.tasks.read(task_id)
            
            if task and hasattr(task, 'chat_sessions'):
                # Count existing sessions
                existing_session_count = len(task.chat_sessions) if task.chat_sessions else 0
                print(f"🧹 Removing {existing_session_count} existing chat sessions")
                
                # Create a new empty session
                new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # COMPLETELY CLEAR all chat sessions and replace with a single empty session
                task.chat_sessions = {new_session_id: []}
                
                # Update the task in the persistence model
                persistence_model.tasks.update(task_id, task)
                
                # Find and clear any tasks with the same name to ensure full cleanup
                task_name = task.name if hasattr(task, 'name') else ""
                if task_name:
                    # Look for similar tasks by name
                    all_tasks = persistence_model.tasks.list()
                    for other_task in all_tasks:
                        if other_task.id != task_id and hasattr(other_task, 'name') and other_task.name == task_name:
                            print(f"🧹 Also clearing chat sessions for similar task: {other_task.id}")
                            if hasattr(other_task, 'chat_sessions'):
                                other_task.chat_sessions = {}
                                persistence_model.tasks.update(other_task.id, other_task)
                
                # Update session state to use the new session
                st.session_state.current_session_id = new_session_id
                st.session_state.messages = []
                
                print(f"✅ Cleared ALL sessions and created new empty session {new_session_id}")
            else:
                print(f"⚠️ Task {task_id} not found or doesn't have chat_sessions")
        
        # Clean up session files
        cleanup_session_files()
        
        # Clear messages list
        st.session_state.messages = []
        
        # Save the empty session state to persist the changes
        save_local_session()
        
        # Trigger a state save to persistently store the cleared session
        if hasattr(st.session_state, 'task_runner') and st.session_state.task_runner:
            if hasattr(st.session_state.task_runner, 'trigger_state_save'):
                st.session_state.task_runner.trigger_state_save()
            
        print("✅ Successfully cleared chat session")
    except Exception as e:
        print(f"❌ Error clearing session state: {str(e)}")
        import traceback
        print(traceback.format_exc())

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
            msg.model_dump() if hasattr(msg, 'model_dump') else (msg.dict() if hasattr(msg, 'dict') else msg) for msg in messages
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
                json.dump(session_data, f, default=lambda x: x.model_dump() if hasattr(x, 'model_dump') else (x.dict() if hasattr(x, 'dict') else str(x)))

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
    """Initialize Cerebrum state and session management."""
    print(f"\n🔄 Initializing Cerebrum state...")
    
    # Make sure required directories exist
    get_state_dir()
    ensure_notebook_directory()
    
    # Ensure session state is initialized
    if 'initialized' not in st.session_state:
        initialize_session_state()
        
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

