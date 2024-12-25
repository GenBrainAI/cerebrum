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
        """Initialize controller with state."""
        try:
            await self.state_manager.initialize()
            
            # Load existing state if available
            try:
                session_dir = Path("state/sessions")
                state_file = session_dir / "task_hierarchy_view_default.json"
                if state_file.exists():
                    with open(state_file) as f:
                        state_data = json.load(f)
                        self.view_state.chat_history = state_data.get('chat_history', [])
                        if 'task_status' in state_data:
                            self.view_state.task_status = state_data['task_status']
                        print(f"Loaded chat history: {len(self.view_state.chat_history)} messages")
            except Exception as e:
                self.logger.error(f"Failed to load existing state: {str(e)}")
            
            # Initialize task context
            task_managers = self.global_persistence.tasksmanagers.list()
            tasks = self.global_persistence.tasks.list()
            
            # Create default task manager and task if none exist
            if not task_managers:
                print("Creating default task manager and tasks...")
                task_manager = self.global_persistence.tasksmanagers.create({
                    "name": "Task Management",
                    "description": "Default task management system"
                })
                
                main_task = self.global_persistence.tasks.create({
                    "name": "Task Management",
                    "description": "Main task management task",
                    "tasksmanager_id": task_manager.id
                })
                
                task_managers = [task_manager]
                tasks = [main_task]
                print(f"Created default task manager: {task_manager.name}")
                print(f"Created default task: {main_task.name}")
            
            if task_managers and tasks:
                # Find task management task
                task_manager = next(
                    (m for m in task_managers if "Task Management" in m.name),
                    task_managers[0]
                )
                main_task = next(
                    (t for t in tasks if t.tasksmanager_id == task_manager.id),
                    None
                )
                
                if main_task:
                    # Set active task context
                    self.view_state.set_active_task(
                        task_id=main_task.id,
                        task_name=main_task.name,
                        manager_id=task_manager.id,
                        manager_name=task_manager.name
                    )
                    print(f"🟢 Set active task: {task_manager.name}-{main_task.name}")
                else:
                    print("🔴 No main task found for task manager")
            else:
                print("🔴 No task managers found")

        except Exception as e:
            self.logger.error(f"Error initializing task hierarchy: {str(e)}")
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
