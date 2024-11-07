import streamlit as st
import time
import os
import asyncio
from typing import Optional

from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.controllers.task_runner import TaskRunner
from server.models.message import Message
from server.models.tasks_manager import TasksManager
from server.models.task import Task
from server.models.run_task import RunTask

# Initialize persistence model and task runner
persistence_model = PersistenceModelFactory.persistence_model("inmemory")
task_runner = TaskRunner(persistence_model)


def create_new_chat(chat_name: str):
    """Create a new TasksManager and Task for a new chat"""
    # Create TasksManager
    tasksmanager = TasksManager(
        name=chat_name,
        model="gpt-4o-mini",
        description="Chat session TasksManager"
    )
    tasksmanager = persistence_model.tasksmanagers.create(tasksmanager)
    
    # Create Task
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
    if 'chat_title' not in st.session_state:
        st.session_state.chat_title = "New Chat"
    if 'default_state_loaded' not in st.session_state:
        st.session_state.default_state_loaded = False

def on_tm_select():
    """Callback when TaskManager selection changes"""
    if st.session_state.tm_selector == "+ New Chat":
        st.session_state.creating_new_chat = True
    else:
        st.session_state.creating_new_chat = False

def load_state(state_path: Optional[str] = None):
    """
    Load Cerebrum state from file. If no state_path is provided,
    attempt to load from config/default.cm
    """
    from server.controllers.persistence_controller import load_from_storage
    from server.models.persistence_models import StorageLocation, StorageType

    try:
        if not state_path and not st.session_state.default_state_loaded:
            # Try to load default state
            state_path = "config/default.cm"
            st.session_state.default_state_loaded = True
        
        if state_path:
            location = StorageLocation(
                type=StorageType.file,
                location=os.path.dirname(state_path),
                state_name=os.path.basename(state_path)
            )
            
            json_str = load_from_storage(location)
            return f"Successfully loaded state from {state_path} with length {len(json_str)}"
        return "No state file specified"
    
    except Exception as e:
        if state_path == "config/default.cm":
            # Don't show error for default state file if it doesn't exist
            return "No default state loaded"
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

def render_sidebar():
    """Render the sidebar UI"""
    with st.sidebar:
        st.title("Cerebrum Chat")
        
        # State file loader
        state_file = st.text_input("State File Path (optional)", "")
        if st.button("Load State"):
            result = load_state(state_file if state_file else None)
            st.success(result)

        # Chat selection section
        st.subheader("Session Selection")

        # Get all available TaskManagers and format them for selection
        tasksmanagers = get_available_tasksmanagers()

        # Always show Create New Chat section at the top
        with st.expander("Create New Chat", expanded=not tasksmanagers):
            new_chat_name = st.text_input(
                "Chat Name",
                value=f"Chat {len(tasksmanagers) + 1}",
                key="new_chat_name"
            )
            if st.button("Create Chat", key="create_chat_button"):
                tasksmanager_id, task_id = create_new_chat(new_chat_name)
                
                # Update session state
                st.session_state.current_tasksmanager_id = tasksmanager_id
                st.session_state.current_task_id = task_id
                st.session_state.messages = []
                st.session_state.chat_title = new_chat_name
                st.rerun()

        # Show existing chats in dropdown if any exist
        if tasksmanagers:
            tm_options = {tm.name: tm.id for tm in tasksmanagers}
            
            # Find current session for default selection
            default_index = 0
            if st.session_state.current_tasksmanager_id:
                current_tm = next((tm for tm in tasksmanagers 
                                if tm.id == st.session_state.current_tasksmanager_id), None)
                if current_tm and current_tm.name in tm_options:
                    default_index = list(tm_options.keys()).index(current_tm.name)

            # TaskManager selection dropdown
            selected_tm = st.selectbox(
                "Select Existing Chat",
                options=list(tm_options.keys()),
                index=default_index,
                key="tm_selector"
            )

            # Handle chat selection
            if selected_tm in tm_options:
                selected_tm_id = tm_options[selected_tm]
                
                # Get tasks for selected TaskManager
                tasks = get_tasks_for_tasksmanager(selected_tm_id)
                if tasks:
                    if len(tasks) > 1:
                        task_options = {task.name: task.id for task in tasks}
                        selected_task = st.selectbox(
                            "Select Task",
                            options=list(task_options.keys()),
                            key="task_selector"
                        )
                        selected_task_id = task_options[selected_task]
                    else:
                        selected_task_id = tasks[0].id

                    if (selected_tm_id != st.session_state.current_tasksmanager_id or 
                        selected_task_id != st.session_state.current_task_id):
                        st.session_state.current_tasksmanager_id = selected_tm_id
                        st.session_state.current_task_id = selected_task_id
                        selected_task_obj = next((t for t in tasks if t.id == selected_task_id), None)
                        if selected_task_obj:
                            st.session_state.messages = selected_task_obj.messages
                        st.rerun()

        # Display current session info
        if st.session_state.current_tasksmanager_id:
            st.markdown("### Current Session Info")
            current_tm = next((tm for tm in tasksmanagers 
                             if tm.id == st.session_state.current_tasksmanager_id), None)
            if current_tm:
                new_name = st.text_input(
                    "Chat Name",
                    value=current_tm.name,
                    key="edit_chat_name"
                )
                if new_name != current_tm.name:
                    current_tm.name = new_name
                    persistence_model.tasksmanagers.update(current_tm.id, current_tm)
                    st.rerun()
                
                st.text(f"TasksManager ID: {current_tm.id[:8]}...")
                st.text(f"Task ID: {st.session_state.current_task_id[:8]}...")

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
    
    # Display chat messages
    for msg in st.session_state.messages:
        # Ensure msg is a Message object
        if isinstance(msg, dict):
            msg = Message(**msg)
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
        
        # Ensure all messages in session state are Message objects
        messages = []
        for msg in st.session_state.messages:
            if isinstance(msg, dict):
                messages.append(Message(**msg))
            else:
                messages.append(msg)
        messages.append(user_message)
        st.session_state.messages = messages

        # Get AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                # Run async task in sync context
                full_response = asyncio.run(
                    process_message(
                        prompt=prompt,
                        tasksmanager_id=st.session_state.current_tasksmanager_id,
                        task_id=st.session_state.current_task_id,
                        messages=st.session_state.messages
                    )
                )

                # Simulate streaming for smoother experience
                current_response = ""
                for chunk in full_response.split():
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

                # Update task in persistence model
                task = persistence_model.tasks.read(st.session_state.current_task_id)
                task.messages = st.session_state.messages
                persistence_model.tasks.update(st.session_state.current_task_id, task)

            except Exception as e:
                st.error(f"Error processing request: {str(e)}")
def main():
    """Main application entry point"""
    st.set_page_config(page_title="Cerebrum Chat", layout="wide")
    initialize_session_state()
    
    # Render both sidebar and main chat interface
    render_sidebar()
    render_main_chat()

if __name__ == "__main__":
    main()
