from typing import Dict, Any, Optional
import streamlit as st
import logging
from datetime import datetime
from pathlib import Path
import json
from uuid import UUID, uuid4
from ..models.view_state import ViewState
from ..state.state_manager import ViewStateManager
from ...models.message import Message
from ..components.tree_select_component import TreeSelectComponent
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel

class TaskHierarchyController:
    """Controller for task hierarchy view."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.logger = logging.getLogger(__name__)
        self.view_state = ViewState(view_name="task_hierarchy")
        self.state_manager = ViewStateManager(persistence_model)
        self.tree_component = TreeSelectComponent(self.handle_node_click)
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
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                node_type="root"
            )
            
            # Get all task managers
            task_managers = self.global_persistence.tasksmanagers.list()
            
            for tm in task_managers:
                # Create task manager node
                tm_node = TreeNode(
                    id=UUID(tm.id) if isinstance(tm.id, str) else tm.id,
                    name=tm.name,
                    node_type="manager"
                )
                
                # Get tasks for this manager
                tasks = [t for t in self.global_persistence.tasks.list() 
                        if t.tasksmanager_id == tm.id]
                
                # Add tasks as children
                for task in tasks:
                    task_node = TreeNode(
                        id=UUID(task.id) if isinstance(task.id, str) else task.id,
                        name=task.name,
                        node_type="task",
                        metadata={
                            "description": task.description,
                            "tasksmanager_id": task.tasksmanager_id
                        }
                    )
                    tm_node.children.append(task_node)
                
                # Add task manager node to root
                root.children.append(tm_node)
            
            return root
            
        except Exception as e:
            self.logger.error(f"Error building task tree: {str(e)}")
            return None

    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("Starting task controller initialization...")
            state_file = StateLoader.get_state_file("task_management_state.json")
            print(f"Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                return

            print(f"Loading state from: {state_file}")
            
            # Read state file content as string
            with open(state_file, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            # Create local persistence model and load state from string
            self.local_persistence = InMemoryPersistenceModel()
            self.local_persistence.from_json(json_str=json_str)
            
            if self.local_persistence:
                print("Local persistence model created")
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
            self.view_state.chat_history.append({
                "role": "user",
                "content": prompt
            })
            
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
                    response = await self.state_manager.task_runner.run_task(
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
                    self.view_state.chat_history.append({
                        "role": "assistant",
                        "content": response_text
                    })
                else:
                    # Add simple response if no active task
                    self.view_state.chat_history.append({
                        "role": "assistant",
                        "content": "No active task to process message."
                    })
            else:
                # Add simple response if no task loaded
                self.view_state.chat_history.append({
                    "role": "assistant",
                    "content": "Task management not loaded. Please initialize first."
                })
                
        except Exception as e:
            self.logger.error(f"Error handling chat: {str(e)}")
            st.error(f"Error handling chat: {str(e)}")
            # Add error message to chat history
            self.view_state.chat_history.append({
                "role": "assistant",
                "content": f"Error processing message: {str(e)}"
            })
