from typing import Dict, Any, Optional
import streamlit as st
import logging
from datetime import datetime
from pathlib import Path
import json
from uuid import UUID, uuid4
from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, TaskGenerationState, StateMetadata
from ..state.state_manager import ViewStateManager
from ..models.tree_node import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...models.message import Message
from ...controllers.task_runner import TaskRunner

class TaskHierarchyController:
    """Controller for task hierarchy view."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.logger = logging.getLogger(__name__)
        self.view_state = ViewState(view_name="task_hierarchy")
        self.state_manager = ViewStateManager(persistence_model)
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.local_persistence = None
        self.task_runner = None  # Will be initialized after local persistence is loaded
        self.view_state.task_status = {
            "loaded": False,
            "tasksmanager_name": "",
            "task_name": ""
        }
        self.view_state.chat_history = []

    def handle_node_click(self, node_id: UUID):
        """Handle tree node selection."""
        self.view_state.selected_node = node_id
        # TODO: Implement task selection logic

    async def get_task_tree(self):
        """Get the task hierarchy as a tree structure."""
        try:
            print("\n🌳 Building task hierarchy tree...")
            
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                metadata={},
                data={}
            )
            print("✅ Created root node")
            
            # Get all task managers
            task_managers = self.global_persistence.tasksmanagers.list()
            print(f"📊 Found {len(task_managers)} task managers")
            
            for tm in task_managers:
                print(f"\n👥 Processing task manager: {tm.name} ({tm.id})")
                # Create task manager node
                tm_node = TreeNode(
                    id=UUID(tm.id) if isinstance(tm.id, str) else tm.id,
                    name=tm.name,
                    type="manager",
                    metadata={},
                    data={}
                )
                
                # Get tasks for this manager
                tasks = [t for t in self.global_persistence.tasks.list() 
                        if hasattr(t, 'tasksmanager_id') and t.tasksmanager_id == tm.id]
                print(f"📋 Found {len(tasks)} tasks for manager {tm.name}")
                
                # Add tasks as children
                for task in tasks:
                    print(f"  - Adding task: {task.name} ({task.id})")
                    task_node = TreeNode(
                        id=UUID(task.id) if isinstance(task.id, str) else task.id,
                        name=task.name,
                        type="task",
                        metadata={
                            "description": task.description,
                            "tasksmanager_id": task.tasksmanager_id
                        },
                        data={}
                    )
                    tm_node.children.append(task_node)
                
                # Only add manager node if it has tasks
                if tm_node.children:
                    print(f"✅ Adding manager node with {len(tm_node.children)} tasks")
                    root.children.append(tm_node)
                else:
                    print(f"⚠️ Skipping manager node - no tasks found")
            
            print(f"\n🎯 Final tree structure:")
            print(f"  Root children: {len(root.children)}")
            for child in root.children:
                print(f"  - {child.name}: {len(child.children)} tasks")
            
            return root
            
        except Exception as e:
            self.logger.error(f"Error building task tree: {str(e)}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return None

    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("\n🚀 Starting task controller initialization...")
            
            state_file = StateLoader.get_state_file("task_management_state.json")
            print(f"📁 Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                return

            print(f"📖 Loading state from: {state_file}")
            
            # Read state file content as string
            with open(state_file, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            # Create local persistence model and load state from string
            self.local_persistence = InMemoryPersistenceModel()
            self.local_persistence.from_json(json_str=json_str)
            
            if self.local_persistence:
                print("✅ Local persistence model created")
                
                # Initialize task runner with local persistence
                self.task_runner = TaskRunner(self.local_persistence)
                await self.task_runner.initialize()
                print("✅ Task runner initialized with local persistence")
                
                # Get task context from local persistence
                task_managers = self.local_persistence.tasksmanagers.list()
                tasks = self.local_persistence.tasks.list()
                
                print(f"Found {len(task_managers)} task managers and {len(tasks)} tasks")
                
                if task_managers and tasks:
                    # Find the task management manager and task
                    task_manager = next(
                        (m for m in task_managers if "Task Management" in m.name),
                        task_managers[0]
                    )
                    main_task = next(
                        (t for t in tasks if t.tasksmanager_id == task_manager.id),
                        None
                    )
                    
                    if main_task:
                        # Update view state with task context
                        self.view_state.set_active_task(
                            task_id=main_task.id,
                            task_name=main_task.name,
                            manager_id=task_manager.id,
                            manager_name=task_manager.name
                        )
                        
                        print(f"🟢 Loaded state for {task_manager.name}-{main_task.name}")
                    else:
                        print("🔴 No task management task found")
                else:
                    print("🔴 No task context found in state file")
            else:
                print("🔴 Failed to create local persistence model")
                
        except Exception as e:
            print(f"Error initializing task controller: {str(e)}")
            raise

    async def handle_chat(self, prompt: str):
        """Handle chat messages."""
        try:
            # Add user message to chat history
            user_message = {
                "role": "user",
                "content": prompt,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(user_message)
            
            # Save chat history to session state immediately after adding user message
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
            
            # Process the message if we have an active task
            if self.view_state.task_status and self.view_state.task_status.get("loaded"):
                task_id = self.view_state.task_status.get("task_id")
                manager_id = self.view_state.task_status.get("tasksmanager_id")
                
                if task_id and manager_id:
                    # Prepare messages context
                    current_messages = []
                    
                    # Add existing chat history
                    for msg in self.view_state.chat_history:
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
                    
                    # Run task with message context
                    print("\n🔄 Using existing persistence model from session state")
                    print("Context provider initialized and synced with persistence model")
                    
                    # Use the task runner with local persistence
                    if not self.task_runner:
                        print("🔄 Initializing task runner with local persistence")
                        self.task_runner = TaskRunner(self.local_persistence)
                        await self.task_runner.initialize()
                    
                    response = await self.task_runner.run_task(
                        tasksmanager_id=manager_id,
                        task_id=task_id,
                        running_extra_params={'messages': current_messages}
                    )
                    
                    # Process response
                    if isinstance(response, dict) and 'response' in response:
                        response_text = response['response']
                    else:
                        response_text = str(response)
                    
                    # Add assistant response to chat history
                    assistant_message = {
                        "role": "assistant",
                        "content": response_text,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    self.view_state.chat_history.append(assistant_message)
                    
                    # Save updated chat history to session state
                    if 'task_controller' in st.session_state:
                        st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
                    
                    # Save chat history to persistence
                    if self.local_persistence and task_id:
                        task = self.local_persistence.tasks.read(task_id)
                        if task:
                            if not hasattr(task, 'chat_sessions'):
                                task.chat_sessions = {}
                            session_id = str(uuid4())
                            task.chat_sessions[session_id] = self.view_state.chat_history
                            self.local_persistence.tasks.update(task_id, task)
                else:
                    # Add simple response if no active task
                    response_message = {
                        "role": "assistant",
                        "content": "No active task to process message.",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    self.view_state.chat_history.append(response_message)
            else:
                # Add simple response if no task loaded
                response_message = {
                    "role": "assistant",
                    "content": "Task management not loaded. Please initialize first.",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                self.view_state.chat_history.append(response_message)
            
            # Final save of chat history to session state
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
                
        except Exception as e:
            self.logger.error(f"Error handling chat: {str(e)}")
            st.error(f"Error handling chat: {str(e)}")
            # Add error message to chat history
            error_message = {
                "role": "assistant",
                "content": f"Error processing message: {str(e)}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(error_message)
            
            # Save error message to session state
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
