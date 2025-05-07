"""
Task Hierarchy Controller for managing task hierarchy view.

This controller manages the task hierarchy view with the following principles:
1. Global Persistence: All task tree and task management operations use the global persistence model.
   This ensures that the task tree and task management views show only the global state.

2. Specialized State: The specialized state (loaded from task_management_state.json) is used only
   for chat functionality. This allows the specialized state to help the user manipulate tasks
   via chat, with the effects applying to the global state.

3. No Synchronization: Unlike other controllers, we do NOT synchronize the specialized state to
   the global state. This prevents duplication of tasks in the task tree and task management views.

4. Persistence Model Usage:
   - self.global_persistence: Always used for task tree, task management, and saving state
   - self.local_persistence: Used only for chat functionality, if available
   - self.persistence_model: Should always be set to self.global_persistence for consistency
"""
from typing import Dict, Any, Optional, List
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
from ...models.task import Task
from ...models.tasks_manager import TasksManager
from ...models.persistence_models import StorageLocation, StorageType
from ...controllers.persistence_controller import save_to_storage
from src.chat import get_state_dir
import asyncio
import time
from ..components.task_tree_visualization_component import TaskTreeVisualizationComponent
from ..components.task_tree_demo_component import TaskTreeDemoComponent

class TaskHierarchyController:
    """Controller for task hierarchy view with task management capabilities."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.persistence_model = persistence_model  # For compatibility with task management
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
        
        # Initialize available models for task management
        self.view_state.available_models = [
            "gpt-4o-mini",
            "gpt-4.5-preview",
            "gpt-3.5-turbo",
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
        ]

    def handle_node_click(self, node_id: UUID):
        """Handle tree node selection."""
        self.view_state.selected_node = str(node_id) if node_id else None
        # TODO: Implement task selection logic

    async def get_task_tree(self):
        """Get the task hierarchy as a tree structure."""
        try:
            self.logger.info("Building task hierarchy tree...")
            
            # Always ensure we're using the global persistence model for task tree
            if self.persistence_model is not self.global_persistence:
                print("🔄 Switching to global persistence model for task tree")
                self.persistence_model = self.global_persistence
            
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                children=[]
            )
            
            # Get all task managers from global persistence
            task_managers = self.global_persistence.tasksmanagers.list()
            self.logger.info(f"Found {len(task_managers)} task managers in global persistence")
            
            # Create task manager nodes
            for tm in task_managers:
                tm_node = TreeNode(
                    id=UUID(tm.id),
                    name=f"{tm.name}",
                    type="tasksmanager",
                    data={"id": tm.id, "model": tm.model},
                    children=[]
                )
                
                # Get tasks for this task manager from global persistence
                tasks = [t for t in self.global_persistence.tasks.list() if t.tasksmanager_id == tm.id]
                self.logger.info(f"Found {len(tasks)} tasks for manager {tm.name} in global persistence")
                
                # Create task nodes
                for task in tasks:
                    task_node = TreeNode(
                        id=UUID(task.id),
                        name=f"{task.name}",
                        type="task",
                        data={"id": task.id, "model": task.model, "tasksmanager_id": tm.id},
                        children=[]
                    )
                    tm_node.children.append(task_node)
                
                # Always add the manager node even if it has no tasks
                # This allows users to see the manager in the tree and add tasks to it
                root.children.append(tm_node)
            
            # Log the tree structure for debugging
            self.logger.info(f"Task tree generated with {len(root.children)} task managers from global persistence")
            
            return root
        except Exception as e:
            self.logger.error(f"Error building task tree: {str(e)}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
            
    # Task Management methods
    
    def get_task_managers(self) -> List[TasksManager]:
        """Get all task managers from global persistence."""
        try:
            # Always use global persistence for task management
            return self.global_persistence.tasksmanagers.list()
        except Exception as e:
            self.logger.error(f"Error getting task managers: {str(e)}")
            return []
            
    def get_tasks(self, tasksmanager_id: Optional[str] = None) -> List[Task]:
        """Get tasks for a specific task manager or all tasks from global persistence."""
        try:
            # Always use global persistence for task management
            all_tasks = self.global_persistence.tasks.list()
            if tasksmanager_id:
                return [task for task in all_tasks if task.tasksmanager_id == tasksmanager_id]
            return all_tasks
        except Exception as e:
            self.logger.error(f"Error getting tasks: {str(e)}")
            return []
            
    def create_task_manager(self, name: str, model: Optional[str] = None, 
                          description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Create a new task manager in global persistence."""
        try:
            messages = []
            if system_message:
                messages.append(Message(role="system", content=system_message))
                
            task_manager = TasksManager(
                name=name,
                model=model,
                description=description,
                messages=messages
            )
            
            # Always save to global persistence
            created_tm = self.global_persistence.tasksmanagers.create(task_manager)
            print(f"🔄 Created task manager {created_tm.name} in global persistence")
            
            # Auto-save state after change
            self.trigger_save_state()
            
            return created_tm
        except Exception as e:
            self.logger.error(f"Error creating task manager: {str(e)}")
            return None
            
    def update_task_manager(self, task_manager_id: str, name: Optional[str] = None, 
                          model: Optional[str] = None, description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Update an existing task manager in global persistence."""
        try:
            # Get existing task manager from global persistence
            task_manager = self.global_persistence.tasksmanagers.read(task_manager_id)
            if not task_manager:
                self.logger.error(f"Task manager not found in global persistence: {task_manager_id}")
                return None
                
            # Update fields if provided
            if name:
                task_manager.name = name
            if model is not None:  # Allow setting to None
                task_manager.model = model
            if description is not None:  # Allow setting to None
                task_manager.description = description
                
            # Update system message if provided
            if system_message is not None:
                # Find existing system message or create new one
                system_messages = [msg for msg in task_manager.messages if msg.role == "system"]
                if system_messages:
                    system_messages[0].content = system_message
                else:
                    task_manager.messages.append(Message(role="system", content=system_message))
                    
            # Update in global persistence
            updated_tm = self.global_persistence.tasksmanagers.update(task_manager_id, task_manager)
            print(f"🔄 Updated task manager {updated_tm.name} in global persistence")
            
            # Auto-save state after change
            self.trigger_save_state()
            
            return updated_tm
        except Exception as e:
            self.logger.error(f"Error updating task manager: {str(e)}")
            return None
            
    def delete_task_manager(self, task_manager_id: str) -> bool:
        """Delete a task manager and all its associated tasks from global persistence."""
        try:
            # Get all tasks for this manager from global persistence
            tasks = [t for t in self.global_persistence.tasks.list() if t.tasksmanager_id == task_manager_id]
            
            # Delete all tasks from global persistence
            for task in tasks:
                self.global_persistence.tasks.delete(task.id)
                print(f"🔄 Deleted task {task.name} from global persistence")
                
            # Delete task manager from global persistence
            result = self.global_persistence.tasksmanagers.delete(task_manager_id)
            print(f"🔄 Deleted task manager from global persistence")
            
            # Auto-save state after change
            self.trigger_save_state()
            
            return result
        except Exception as e:
            self.logger.error(f"Error deleting task manager: {str(e)}")
            return False
            
    def create_task(self, name: str, tasksmanager_id: str, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: bool = False) -> Optional[Task]:
        """Create a new task associated with a task manager in global persistence."""
        try:
            messages = []
            if system_message:
                messages.append(Message(role="system", content=system_message))
                
            task = Task(
                name=name,
                tasksmanager_id=tasksmanager_id,
                model=model,
                description=description,
                messages=messages,
                inherit_manager_context=inherit_manager_context
            )
            
            # Save to global persistence
            created_task = self.global_persistence.tasks.create(task)
            print(f"🔄 Created task {created_task.name} in global persistence")
            
            # Auto-save state after change - try both strategies
            self.trigger_save_state()
            
            # Ensure it's saved with direct approach as well
            self._fallback_synchronous_save()
            
            # Directly update the metadata.json to point to this state
            try:
                from pathlib import Path
                import json
                from datetime import datetime
                
                state_dir = Path(__file__).parent.parent.parent.parent.parent / "state"
                metadata_path = state_dir / "metadata.json"
                
                metadata = {}
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                
                metadata["last_used_state"] = "task_hierarchy_state"
                metadata["last_updated"] = datetime.now().isoformat()
                metadata["last_task_id"] = created_task.id
                metadata["last_tm_id"] = tasksmanager_id
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.info(f"Updated metadata to track new task {created_task.id}")
            except Exception as e:
                self.logger.error(f"Error updating metadata after task creation: {str(e)}")
            
            return created_task
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            return None
            
    def update_task(self, task_id: str, name: Optional[str] = None, 
                  tasksmanager_id: Optional[str] = None, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: Optional[bool] = None) -> Optional[Task]:
        """Update an existing task in global persistence."""
        try:
            self.logger.info(f"Updating task {task_id} with name={name}, tasksmanager_id={tasksmanager_id}, model={model}")
            
            import streamlit as st
            if hasattr(st, 'session_state'):
                # Clear any previous errors
                st.session_state.last_error = None
            
            # Get existing task from global persistence
            task = self.global_persistence.tasks.read(task_id)
            if not task:
                error_msg = f"Task not found in global persistence: {task_id}"
                self.logger.error(error_msg)
                if hasattr(st, 'session_state'):
                    st.session_state.last_error = error_msg
                return None
                
            # Log the task before updates
            self.logger.info(f"Original task: {task.name}, manager_id: {task.tasksmanager_id}")
            
            # Validate that the task manager exists if changing it
            if tasksmanager_id and tasksmanager_id != task.tasksmanager_id:
                task_manager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
                if not task_manager:
                    error_msg = f"Task manager {tasksmanager_id} not found when updating task"
                    self.logger.error(error_msg)
                    if hasattr(st, 'session_state'):
                        st.session_state.last_error = error_msg
                    return None
                    
            # Update fields if provided
            if name:
                task.name = name
            if tasksmanager_id:
                task.tasksmanager_id = tasksmanager_id
            if model is not None:  # Allow setting to None
                task.model = model
            if description is not None:  # Allow setting to None
                task.description = description
            if inherit_manager_context is not None:
                task.inherit_manager_context = inherit_manager_context
                
            # Update system message if provided
            if system_message is not None:
                # Find existing system message or create new one
                from ...models.message import Message
                system_messages = [msg for msg in task.messages if msg.role == "system"]
                if system_messages:
                    self.logger.info(f"Updating existing system message for task {task_id}")
                    system_messages[0].content = system_message
                else:
                    self.logger.info(f"Creating new system message for task {task_id}")
                    task.messages.append(Message(role="system", content=system_message))
            
            # Ensure all messages are properly normalized
            self.logger.info(f"Normalizing messages for task {task_id}")
            try:
                # Call the normalization method to ensure all messages are proper Message objects
                task.normalize_messages()
                self.logger.info(f"Successfully normalized {len(task.messages)} messages")
            except Exception as norm_error:
                error_msg = f"Error normalizing messages: {str(norm_error)}"
                self.logger.error(error_msg)
                if hasattr(st, 'session_state'):
                    st.session_state.last_error = error_msg
                return None
                
            # Validate task before saving
            try:
                # Check if the task has the correct attribute types
                if not isinstance(task.name, str):
                    error_msg = f"Task name must be a string, got {type(task.name)}"
                    self.logger.error(error_msg)
                    if hasattr(st, 'session_state'):
                        st.session_state.last_error = error_msg
                    return None
                
                # More validation as needed
                self.logger.info("Task validated successfully")
            except Exception as validation_error:
                error_msg = f"Task validation error: {str(validation_error)}"
                self.logger.error(error_msg)
                if hasattr(st, 'session_state'):
                    st.session_state.last_error = error_msg
                return None
                    
            # Update in global persistence
            try:
                self.logger.info(f"Saving updated task to global persistence")
                updated_task = self.global_persistence.tasks.update(task_id, task)
                
                if not updated_task:
                    error_msg = "Task update returned None from persistence layer"
                    self.logger.error(error_msg)
                    if hasattr(st, 'session_state'):
                        st.session_state.last_error = error_msg
                    return None
                    
                print(f"🔄 Updated task {updated_task.name} in global persistence")
                
                # Log the updated task
                self.logger.info(f"Task updated: {updated_task.name}, manager_id: {updated_task.tasksmanager_id}")
                
                # Auto-save state after change
                self.logger.info("Triggering state save after task update")
                # Save synchronously first to ensure immediate persistence
                self._fallback_synchronous_save()
                # Then trigger the async save mechanism
                self.trigger_save_state()
                
                return updated_task
            except Exception as update_error:
                error_msg = f"Error updating task in persistence: {str(update_error)}"
                self.logger.error(error_msg)
                if hasattr(st, 'session_state'):
                    st.session_state.last_error = error_msg
                return None
                
        except Exception as e:
            error_msg = f"Error updating task: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            
            # Store error in session state if available
            import streamlit as st
            if hasattr(st, 'session_state'):
                st.session_state.last_error = error_msg
                
            return None
            
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from global persistence."""
        try:
            # Delete from global persistence
            result = self.global_persistence.tasks.delete(task_id)
            print(f"🔄 Deleted task from global persistence")
            
            # Auto-save state after change
            self.trigger_save_state()
            
            return result
        except Exception as e:
            self.logger.error(f"Error deleting task: {str(e)}")
            return False
            
    async def run_task_sequence(self, tasksmanager_id: str, task_ids: List[str], 
                              running_extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a sequence of tasks with handover of outputs between them."""
        try:
            # Initialize task runner if needed
            if not self.task_runner:
                self.task_runner = TaskRunner(self.global_persistence)
                # Initialize the task runner
                # self.task_runner._controller = self
                await self.task_runner.initialize()
                
            # Run the task sequence
            # IMPORTANT: For backward compatibility, we're passing 'running_extra_params'
            # as 'initial_context' which is what TaskRunner.run_task_sequence now expects
            result = await self.task_runner.run_task_sequence(
                tasksmanager_id=tasksmanager_id,
                task_ids=task_ids,
                initial_context=running_extra_params
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error running task sequence: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}
            
    async def run_task_sequence_by_id(self, tasksmanager_id: str, sequence_id: str, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a task sequence by its ID.
        
        Args:
            tasksmanager_id: ID of the task manager
            sequence_id: ID of the sequence to run
            initial_context: Optional initial context containing messages and user input
            
        Returns:
            Task sequence execution results
        """
        try:
            # Initialize task runner if needed
            if not self.task_runner:
                self.task_runner = TaskRunner(self.global_persistence)
                # Initialize the task runner
                # self.task_runner._controller = self
                await self.task_runner.initialize()
            
            # Log message context being passed
            if initial_context and 'messages' in initial_context:
                msg_count = len(initial_context['messages'])
                self.logger.info(f"Passing {msg_count} messages to task sequence execution")
                if 'user_query' in initial_context:
                    self.logger.info(f"User query: {initial_context['user_query'][:50]}...")
                
            # Run the task sequence with context
            result = await self.task_runner.run_task_sequence_by_id(
                tasksmanager_id=tasksmanager_id,
                sequence_id=sequence_id,
                initial_context=initial_context
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error running task sequence by ID: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    async def create_task_sequence(self, tasksmanager_id: str, name: str, description: str, task_ids: List[str]) -> str:
        """Create a new task sequence.
        
        Args:
            tasksmanager_id: ID of the task manager
            name: Name of the sequence
            description: Description of the sequence
            task_ids: List of task IDs in the sequence
            
        Returns:
            ID of the created sequence
        """
        try:
            # Get TasksManager
            tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                raise ValueError(f"TasksManager not found: {tasksmanager_id}")
            
            # Import TaskSequence
            from ...models.tasks_manager import TaskSequence
            
            # Create sequence
            sequence = TaskSequence(
                name=name,
                description=description,
                task_ids=task_ids
            )
            
            # Add to TasksManager
            sequence_id = tasksmanager.add_sequence(sequence)
            
            # Update TasksManager
            self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
            
            # Trigger state save
            self.trigger_save_state()
            
            # Also ensure it's saved with direct approach
            self._fallback_synchronous_save()
            
            # Directly update the metadata.json to track this sequence
            try:
                from pathlib import Path
                import json
                from datetime import datetime
                
                state_dir = Path(__file__).parent.parent.parent.parent.parent / "state"
                metadata_path = state_dir / "metadata.json"
                
                metadata = {}
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                
                metadata["last_used_state"] = "task_hierarchy_state"
                metadata["last_updated"] = datetime.now().isoformat()
                metadata["last_tm_id"] = tasksmanager_id
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.info(f"Updated metadata after creating sequence {sequence_id}")
            except Exception as e:
                self.logger.error(f"Error updating metadata after sequence creation: {str(e)}")
            
            self.logger.info(f"Created task sequence '{name}' with ID {sequence_id}")
            return sequence_id
        except Exception as e:
            self.logger.error(f"Error creating task sequence: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
    
    async def update_task_sequence(self, tasksmanager_id: str, sequence_id: str, 
                               name: Optional[str] = None, description: Optional[str] = None, 
                               task_ids: Optional[List[str]] = None) -> bool:
        """Update an existing task sequence.
        
        Args:
            tasksmanager_id: ID of the task manager
            sequence_id: ID of the sequence to update
            name: New name for the sequence
            description: New description for the sequence
            task_ids: New list of task IDs for the sequence
            
        Returns:
            True if the sequence was updated, False otherwise
        """
        try:
            # Get TasksManager
            tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                raise ValueError(f"TasksManager not found: {tasksmanager_id}")
            
            # Get existing sequence
            sequence = tasksmanager.get_sequence(sequence_id)
            if not sequence:
                raise ValueError(f"Task sequence not found: {sequence_id}")
            
            # Update fields
            if name is not None:
                sequence.name = name
            if description is not None:
                sequence.description = description
            if task_ids is not None:
                sequence.task_ids = task_ids
            
            sequence.updated_at = datetime.now()
            
            # Update in TasksManager
            success = tasksmanager.update_sequence(sequence_id, sequence)
            
            # Update TasksManager
            self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
            
            # Trigger state save
            self.trigger_save_state()
            
            self.logger.info(f"Updated task sequence {sequence_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error updating task sequence: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
    
    async def delete_task_sequence(self, tasksmanager_id: str, sequence_id: str) -> bool:
        """Delete a task sequence.
        
        Args:
            tasksmanager_id: ID of the task manager
            sequence_id: ID of the sequence to delete
            
        Returns:
            True if the sequence was deleted, False otherwise
        """
        try:
            # Get TasksManager
            tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                raise ValueError(f"TasksManager not found: {tasksmanager_id}")
            
            # Remove sequence
            success = tasksmanager.remove_sequence(sequence_id)
            
            # Update TasksManager
            if success:
                self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
                
                # Trigger state save
                self.trigger_save_state()
            
            self.logger.info(f"Deleted task sequence {sequence_id}: {success}")
            return success
        except Exception as e:
            self.logger.error(f"Error deleting task sequence: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
    
    async def get_task_sequences(self, tasksmanager_id: str) -> List[Dict[str, Any]]:
        """Get all task sequences for a TasksManager.
        
        Args:
            tasksmanager_id: ID of the task manager
            
        Returns:
            List of task sequences as dictionaries
        """
        try:
            # Get TasksManager
            tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                raise ValueError(f"TasksManager not found: {tasksmanager_id}")
            
            # Get sequences
            sequences = tasksmanager.get_sequences()
            
            # Convert to dicts for the view
            return [
                {
                    "id": seq.id,
                    "name": seq.name,
                    "description": seq.description,
                    "task_ids": seq.task_ids,
                    "created_at": seq.created_at,
                    "updated_at": seq.updated_at,
                    "enabled": seq.enabled,
                    "task_count": len(seq.task_ids)
                }
                for seq in sequences
            ]
        except Exception as e:
            self.logger.error(f"Error getting task sequences: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []

    def get_system_message(self, obj: Any) -> Optional[str]:
        """Extract system message from a task or task manager."""
        if not obj or not hasattr(obj, 'messages'):
            return None
            
        system_messages = []
        for msg in obj.messages:
            # Handle both Message objects and dictionaries
            if isinstance(msg, dict):
                if msg.get('role') == "system":
                    system_messages.append(msg.get('content', ''))
            else:
                # Assume it's a Message-like object with role and content attributes
                if hasattr(msg, 'role') and msg.role == "system" and hasattr(msg, 'content'):
                    system_messages.append(msg.content)
                    
        return system_messages[0] if system_messages else None

    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("\n🚀 Starting task controller initialization...")
            
            # First, ensure we're using the global persistence model for task tree and management
            self.persistence_model = self.global_persistence
            print("🔄 Using global persistence model for task tree and management")
            
            # Initialize task runner with global persistence
            self.task_runner = TaskRunner(self.global_persistence)
            await self.task_runner.initialize()
            print("🔄 Task runner initialized with global persistence")
            
            # Check for specialized state file (for chat functionality only)
            state_file = StateLoader.get_state_file("task_management_state.json")
            print(f"📁 Checking specialized state file path: {state_file}")
            
            if state_file and state_file.exists():
                print(f"📖 Loading specialized state from: {state_file}")
                
                # Read state file content as string
                with open(state_file, 'r', encoding='utf-8') as f:
                    json_str = f.read()
                
                # Create local persistence model and load state from string
                self.local_persistence = InMemoryPersistenceModel()
                self.local_persistence.from_json(json_str=json_str)
                
                # Get task context from local persistence (for chat functionality only)
                local_task_managers = self.local_persistence.tasksmanagers.list()
                local_tasks = self.local_persistence.tasks.list()
                
                print(f"📊 Found {len(local_task_managers)} task managers and {len(local_tasks)} tasks in specialized state")
                print(f"📊 These will be used for chat functionality only, not for task tree or management")
                
                # Find a task management task in the specialized state to set as active for chat
                if local_task_managers and local_tasks:
                    local_task_manager = next(
                        (m for m in local_task_managers if "Task Management" in m.name),
                        local_task_managers[0]
                    )
                    local_main_task = next(
                        (t for t in local_tasks if t.tasksmanager_id == local_task_manager.id),
                        None
                    )
                    
                    if local_main_task:
                        print(f"📊 Found specialized task: {local_main_task.name} for chat functionality")
                        # We'll use this for chat, but not set it as active yet
                    else:
                        print("🔴 No task management task found in specialized state")
                else:
                    print("🔴 No task context found in specialized state file")
            else:
                print(f"🔴 Specialized state file not found at {state_file}")
                self.local_persistence = None
            
            # Now, get task managers and tasks from global persistence for task tree and management
            global_task_managers = self.global_persistence.tasksmanagers.list()
            global_tasks = self.global_persistence.tasks.list()
            
            print(f"📊 Found {len(global_task_managers)} task managers and {len(global_tasks)} tasks in global persistence")
            print(f"📊 Task status before update: {self.view_state.task_status}")
            
            # Set active task from global persistence
            if global_task_managers and global_tasks:
                # Find the task management manager and task
                task_manager = next(
                    (m for m in global_task_managers if "Task Management" in m.name),
                    global_task_managers[0]
                )
                main_task = next(
                    (t for t in global_tasks if t.tasksmanager_id == task_manager.id),
                    None
                )
                
                print(f"📊 Found global task manager: {task_manager.name} (ID: {task_manager.id})")
                if main_task:
                    print(f"📊 Found global main task: {main_task.name} (ID: {main_task.id})")
                    
                    # Update view state with task context
                    self.view_state.set_active_task(
                        task_id=main_task.id,
                        task_name=main_task.name,
                        manager_id=task_manager.id,
                        manager_name=task_manager.name
                    )
                    
                    # Ensure all required fields are present in task_status
                    self.view_state.task_status = {
                        "loaded": True,
                        "task_id": main_task.id,
                        "task_name": main_task.name,
                        "tasksmanager_id": task_manager.id,
                        "tasksmanager_name": task_manager.name
                    }
                    
                    # Log task status for debugging
                    print(f"📊 Task status after update: {self.view_state.task_status}")
                    self.logger.info(f"Task status set to: {self.view_state.task_status}")
                    
                    print(f"🟢 Loaded state for {task_manager.name}-{main_task.name}")
                else:
                    print("🔴 No task management task found in global persistence")
                    self.view_state.task_status = {
                        "loaded": False,
                        "tasksmanager_name": "",
                        "task_name": ""
                    }
                    print(f"📊 Task status set to: {self.view_state.task_status}")
            else:
                print("🔴 No task context found in global persistence")
                self.view_state.task_status = {
                    "loaded": False,
                    "tasksmanager_name": "",
                    "task_name": ""
                }
                print(f"📊 Task status set to: {self.view_state.task_status}")
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
                    
                    # Determine which persistence model to use for chat
                    # If we have specialized state, use it for chat functionality
                    chat_persistence = self.local_persistence if self.local_persistence else self.global_persistence
                    print(f"\n🔄 Using {'specialized' if self.local_persistence else 'global'} persistence model for chat functionality")
                    
                    # Initialize task runner if needed
                    if not self.task_runner:
                        # Always initialize with global persistence for task execution
                        print("🔄 Initializing task runner with global persistence")
                        self.task_runner = TaskRunner(self.global_persistence)
                        await self.task_runner.initialize()
                    
                    # For chat, we'll use the specialized state if available
                    if self.local_persistence:
                        # Find the corresponding task in the specialized state
                        local_task_managers = self.local_persistence.tasksmanagers.list()
                        local_tasks = self.local_persistence.tasks.list()
                        
                        # Try to find the same task in the specialized state
                        local_task = next((t for t in local_tasks if t.id == task_id), None)
                        if not local_task:
                            # If not found, try to find a task with the same name
                            global_task = self.global_persistence.tasks.read(task_id)
                            if global_task:
                                local_task = next((t for t in local_tasks if t.name == global_task.name), None)
                        
                        if local_task:
                            print(f"🔄 Found corresponding task in specialized state: {local_task.name}")
                            # Use the specialized task for chat
                            task_id = local_task.id
                            manager_id = local_task.tasksmanager_id
                            
                            # Create a temporary task runner with the specialized state
                            temp_runner = TaskRunner(self.local_persistence)
                            await temp_runner.initialize()
                            
                            # Run the task with the specialized state
                            response = await temp_runner.run_task(
                                tasksmanager_id=manager_id,
                                task_id=task_id,
                                running_extra_params={'messages': current_messages}
                            )
                        else:
                            print(f"🔄 No corresponding task found in specialized state, using global state")
                            # Fall back to global state
                            response = await self.task_runner.run_task(
                                tasksmanager_id=manager_id,
                                task_id=task_id,
                                running_extra_params={'messages': current_messages}
                            )
                    else:
                        # Use global state
                        response = await self.task_runner.run_task(
                            tasksmanager_id=manager_id,
                            task_id=task_id,
                            running_extra_params={'messages': current_messages}
                        )
                    
                    # Process response
                    if isinstance(response, dict) and 'response' in response:
                        response_text = response['response']
                    elif isinstance(response, str):
                        response_text = response
                    else:
                        response_text = str(response)
                    
                    # Add assistant message to chat history
                    assistant_message = {
                        "role": "assistant",
                        "content": response_text,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    self.view_state.chat_history.append(assistant_message)
                    
                    # Update session state with new chat history
                    if 'task_controller' in st.session_state:
                        st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
                    
                    # Display the assistant message in the UI
                    if st.session_state.get('_current_page') == 'Task_Hierarchy':
                        st.chat_message("assistant").write(response_text)
                    
                    return response_text
                else:
                    print(f"❌ Missing task_id or manager_id in task_status: {self.view_state.task_status}")
                    return "Error: Task context not properly set."
            else:
                print(f"❌ No active task found in task_status: {self.view_state.task_status}")
                return "Error: No active task found."
        except Exception as e:
            error_msg = f"Error processing chat: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            print(traceback.format_exc())
            
            # Add error message to chat history
            error_response = {
                "role": "assistant",
                "content": f"I encountered an error: {str(e)}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(error_response)
            
            # Update session state with new chat history
            if 'task_controller' in st.session_state:
                st.session_state.task_controller.view_state.chat_history = self.view_state.chat_history
            
            return error_msg

    async def save_state(self):
        """Save the current state to disk."""
        try:
            # Set save status to pending
            st.session_state.save_status = "pending"
            self.logger.info("Setting save status to pending")
            
            # Always ensure we're using the global persistence model
            if self.persistence_model is not self.global_persistence:
                print("🔄 Switching to global persistence model for saving state")
                self.persistence_model = self.global_persistence
            
            state_dir = get_state_dir()
            location = StorageLocation(
                type=StorageType.file,
                location=str(state_dir),
                state_name="task_hierarchy_state"
            )
            
            # Save state with context - using the global persistence model
            result = save_to_storage(self.global_persistence, location)
            self.logger.info(f"State saved successfully: {result}")
            
            # Set save status to saved and update last save time
            st.session_state.save_status = "saved"
            st.session_state.last_save_time = time.time()
            self.logger.info(f"Updated save status: {st.session_state.save_status}, time: {st.session_state.last_save_time}")
            
            return result
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            # Reset save status on error
            st.session_state.save_status = None
            return None

    def trigger_save_state(self):
        """Helper method to trigger state saving with proper async handling."""
        try:
            self.logger.info("Triggering state save...")
            
            # Always ensure we're using the global persistence model
            if self.persistence_model is not self.global_persistence:
                print("🔄 Switching to global persistence model for saving state")
                self.persistence_model = self.global_persistence
            
            # Auto-save state after change - use a sync method to ensure immediate execution
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                self.logger.info("Event loop is running, creating async task to save state")
                try:
                    save_task = asyncio.create_task(self.save_state())
                    save_task.add_done_callback(
                        lambda t: self.logger.info(f"Save state task completed with result: {t.result() if not t.exception() else 'Error: ' + str(t.exception())}")
                    )
                except Exception as e:
                    self.logger.error(f"Error creating save task: {str(e)}", exc_info=True)
                    # Fall back to synchronous save
                    self._fallback_synchronous_save()
            else:
                # Otherwise run a new event loop
                self.logger.info("No event loop running, creating new event loop for state save")
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(self.save_state())
                    new_loop.close()
                    self.logger.info(f"Completed state save in new event loop with result: {result}")
                except Exception as e:
                    self.logger.error(f"Error in save loop: {str(e)}", exc_info=True)
                    # Fall back to synchronous save
                    self._fallback_synchronous_save()
        except Exception as e:
            self.logger.error(f"Error triggering save state: {str(e)}", exc_info=True)
            # Last resort: try direct file save
            self._fallback_synchronous_save()
            
    def _fallback_synchronous_save(self):
        """Fallback method for saving state synchronously when async fails."""
        try:
            self.logger.info("Attempting fallback synchronous state save...")
            import os
            from src.server.controllers.persistence_controller import save_to_storage
            from src.server.models.persistence_models import StorageLocation, StorageType
            from pathlib import Path
            
            # Get state directory
            state_dir = Path(__file__).parent.parent.parent.parent.parent / "state"
            state_dir.mkdir(exist_ok=True)
            
            # Create storage location
            location = StorageLocation(
                type=StorageType.file,
                location=str(state_dir),
                state_name="task_hierarchy_state"
            )
            
            # Direct synchronous save
            result = save_to_storage(self.global_persistence, location)
            self.logger.info(f"Fallback synchronous save completed: {result}")
            
            # Update metadata.json to point to this state file
            try:
                metadata_path = state_dir / "metadata.json"
                import json
                metadata = {}
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                
                metadata["last_used_state"] = "task_hierarchy_state"
                from datetime import datetime
                metadata["last_updated"] = datetime.now().isoformat()
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                    
                self.logger.info("Updated metadata.json to point to task_hierarchy_state")
            except Exception as e:
                self.logger.error(f"Error updating metadata: {str(e)}")
                
            # Update session state if in Streamlit context
            try:
                import streamlit as st
                if hasattr(st, "session_state"):
                    st.session_state.save_status = "saved"
                    import time
                    st.session_state.last_save_time = time.time()
                    self.logger.info("Updated Streamlit session state with save status")
            except Exception as e:
                self.logger.error(f"Error updating session state: {str(e)}")
                
            return result
        except Exception as e:
            self.logger.error(f"Error in fallback synchronous save: {str(e)}", exc_info=True)
            return None

    # Add this method after the get_task_tree method
    async def get_task_tree_with_handover(self):
        """Get the task hierarchy with handover relationships."""
        try:
            self.logger.info("Building task hierarchy tree with handover relationships...")
            
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                children=[]
            )
            
            # Get all task managers
            task_managers = self.global_persistence.tasksmanagers.list()
            
            # Create task manager nodes
            for tm in task_managers:
                try:
                    # Safely convert ID to UUID, generate a new one if invalid
                    try:
                        tm_uuid = UUID(tm.id)
                    except (ValueError, TypeError, AttributeError):
                        tm_uuid = uuid4()
                        self.logger.warning(f"Invalid UUID format for task manager ID: {tm.id}, generated new UUID: {tm_uuid}")
                        
                    tm_node = TreeNode(
                        id=tm_uuid,
                        name=f"{tm.name}",
                        type="tasksmanager",
                        data={"id": tm.id, "model": tm.model},
                        children=[]
                    )
                    
                    # Get tasks for this task manager
                    tasks = [t for t in self.global_persistence.tasks.list() if t.tasksmanager_id == tm.id]
                    
                    # Create task nodes
                    task_nodes = {}
                    for task in tasks:
                        try:
                            # Safely convert task ID to UUID
                            try:
                                task_uuid = UUID(task.id)
                            except (ValueError, TypeError, AttributeError):
                                task_uuid = uuid4()
                                self.logger.warning(f"Invalid UUID format for task ID: {task.id}, generated new UUID: {task_uuid}")
                                
                            task_node = TreeNode(
                                id=task_uuid,
                                name=f"{task.name}",
                                type="task",
                                data={
                                    "id": task.id, 
                                    "model": getattr(task, "model", None), 
                                    "tasksmanager_id": tm.id,
                                    "plugin": getattr(task, "plugin", "default")
                                },
                                children=[]
                            )
                            task_nodes[task.id] = task_node
                            tm_node.children.append(task_node)
                        except Exception as e:
                            self.logger.error(f"Error creating node for task {getattr(task, 'id', 'unknown')}: {str(e)}")
                            continue
                    
                    # Add handover relationships
                    for task in tasks:
                        if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
                            task_node = task_nodes.get(task.id)
                            if not task_node:
                                continue
                                
                            # Add visual indicator for inputs
                            task_node.data["has_inputs"] = True
                            
                            # Create connections for each input
                            for input_task_id in task.input_from_tasks:
                                if input_task_id in task_nodes:
                                    # Add connection indicator
                                    input_node = task_nodes[input_task_id]
                                    outputs_to = input_node.data.get("outputs_to", [])
                                    if task.id not in outputs_to:
                                        outputs_to.append(task.id)
                                    input_node.data["outputs_to"] = outputs_to
                    
                    # Add the manager node
                    root.children.append(tm_node)
                    
                except Exception as e:
                    self.logger.error(f"Error processing task manager {getattr(tm, 'id', 'unknown')}: {str(e)}")
                    continue
            
            return root
        except Exception as e:
            self.logger.error(f"Error building task hierarchy tree: {str(e)}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return None

    def task_hierarchy_view_handle(self):
        """Handle the task hierarchy view and add demo tab."""
        # Add tabs for hierarchy and demo
        tabs = st.tabs(["Task Hierarchy", "Task Tree Demo"])
        
        with tabs[0]:
            # Existing hierarchy view 
            self.render_task_hierarchy()
        
        with tabs[1]:
            # Add demo component
            demo_component = TaskTreeDemoComponent(self)
            demo_component.render()
            
    async def get_tree_data(self):
        """Async helper to get tree data without causing event loop conflicts."""
        try:
            return await self.get_task_tree_with_handover()
        except Exception as e:
            self.logger.error(f"Error getting task tree: {str(e)}")
            return None

    def render_task_hierarchy(self):
        """Render the task hierarchy with visualization support for task trees."""
        # Create columns for the view
        col1, col2 = st.columns([1, 3])

        # Column 1: Task Hierarchy Tree
        with col1:
            st.write("### Task Hierarchy")
            
            # Get the tree data using a safer approach
            try:
                # Try to use a non-blocking approach first
                if hasattr(self, '_tree_data_cache'):
                    tree = self._tree_data_cache
                else:
                    # Fall back to a synchronous approach for the first load
                    # This is less ideal but avoids the asyncio conflicts
                    tree = self._get_task_tree_synchronously()
                    # Cache the result to avoid repeated calls
                    self._tree_data_cache = tree
                    
                if tree:
                    self.tree_component.render(tree)
                else:
                    st.error("Could not load task hierarchy")
            except Exception as e:
                st.error(f"Error loading task hierarchy: {str(e)}")
                st.info("Please refresh the page if tree doesn't display correctly")

        # Column 2: Selected Task/Manager Details or Task Tree Visualization
        with col2:
            # Check if this is a task tree state
            tree_id = None
            try:
                # Safely check if collection_exists method is available
                if hasattr(self.global_persistence, 'collection_exists') and self.global_persistence.collection_exists("task_trees"):
                    for tree_item_id in self.global_persistence.collection("task_trees").list():
                        tree_metadata = self.global_persistence.collection("task_trees").read(tree_item_id)
                        tree_id = tree_item_id
                        break
            except Exception as e:
                self.logger.error(f"Error checking task tree collections: {str(e)}")
                # Continue gracefully without tree visualization
            
            # If tree_id is found, show visualization
            if tree_id:
                st.write("### Task Tree Visualization")
                viz_component = TaskTreeVisualizationComponent(self.global_persistence)
                viz_component.render(tree_id)
            elif self.view_state.selected_node:
                # Handle selected node display
                node_id = self.view_state.selected_node
                # Show task or manager details depending on selected node
                # This is existing functionality that should remain
                pass
            else:
                st.write("### Task Management")
                st.write("Select a task or manager from the tree to view details.")
                
    def _get_task_tree_synchronously(self):
        """Non-async version of get_task_tree_with_handover to avoid event loop issues."""
        # This is a simplified version that doesn't require async/await
        try:
            # Get all tasks
            tasks = list(self.persistence_model.tasks.list())
            
            # Create root node
            from ..models.tree_node import TreeNode
            from uuid import UUID
            
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                children=[]
            )
            
            # Build a dictionary of tasks by ID for quick lookup
            tasks_by_id = {str(task.id): task for task in tasks}
            
            # Group tasks by task manager ID
            tasks_by_manager = {}
            for task in tasks:
                manager_id = str(task.tasksmanager_id)
                if manager_id not in tasks_by_manager:
                    tasks_by_manager[manager_id] = []
                tasks_by_manager[manager_id].append(task)
            
            # Get all task managers
            task_managers = list(self.persistence_model.tasksmanagers.list())
            
            # Create manager nodes
            for manager in task_managers:
                try:
                    manager_id_str = str(manager.id)
                    manager_node = TreeNode(
                        id=UUID(manager_id_str),
                        name=manager.name,
                        type="tasksmanager",
                        data={"id": manager_id_str, "model": manager.model},
                        children=[]
                    )
                    
                    # Add tasks for this manager
                    manager_tasks = tasks_by_manager.get(manager_id_str, [])
                    for task in manager_tasks:
                        task_id_str = str(task.id)
                        task_node = TreeNode(
                            id=UUID(task_id_str),
                            name=task.name,
                            type="task",
                            data={
                                "id": task_id_str, 
                                "model": getattr(task, "model", None),
                                "tasksmanager_id": manager_id_str,
                                "plugin": getattr(task, "plugin", "default"),
                                "input_from": getattr(task, "input_from_tasks", [])
                            },
                            children=[]
                        )
                        manager_node.children.append(task_node)
                    
                    root.children.append(manager_node)
                except Exception as e:
                    self.logger.error(f"Error processing manager {getattr(manager, 'id', 'unknown')}: {str(e)}")
                    continue
            
            return root
            
        except Exception as e:
            self.logger.error(f"Error building task tree: {str(e)}")
            # Return an empty root node instead of an empty list
            from ..models.tree_node import TreeNode
            from uuid import UUID
            return TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Task Hierarchy",
                type="root",
                children=[]
            )

    def load_state(self, state_file: str) -> str:
        """Load the specified state file."""
        try:
            state_path = Path(state_file)
            if not state_path.exists():
                return f"State file not found: {state_file}"
            
            try:
                import json
                with open(state_path, 'r') as f:
                    loaded_state = json.load(f)
            except Exception as e:
                return f"Failed to load state from {state_file}: {str(e)}"
            
            if not loaded_state:
                return f"Failed to load state from {state_file}"
            
            # Reset the global persistence model
            self.global_persistence.reset()
            
            # Load the state into global persistence directly
            try:
                if "tasksmanagers" in loaded_state:
                    for tm_data in loaded_state["tasksmanagers"]:
                        from ...models.tasks_manager import TasksManager
                        tm = TasksManager.model_validate(tm_data)
                        self.global_persistence.tasksmanagers.create(tm)
                
                if "tasks" in loaded_state:
                    for task_data in loaded_state["tasks"]:
                        from ...models.task import Task
                        task = Task.model_validate(task_data)
                        self.global_persistence.tasks.create(task)
            except Exception as e:
                return f"Failed to restore state to model: {str(e)}"
            
            # Update view state with context from loaded state
            if "context_state" in loaded_state:
                context = loaded_state["context_state"]
                if "current_tasksmanager_id" in context:
                    self.view_state.current_tasksmanager_id = context["current_tasksmanager_id"]
                if "current_task_id" in context:
                    self.view_state.current_task_id = context["current_task_id"]
            
            return f"Successfully loaded state from {state_file}"
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return f"Error loading state: {str(e)}"

    def update_tasksmanager(self, tasksmanager_id: str, **kwargs) -> str:
        """Update a task manager."""
        # Get the existing task manager
        tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager with ID {tasksmanager_id} not found")
        
        # Extract handover settings
        enable_handover = kwargs.pop('enable_handover', None)
        task_order = kwargs.pop('task_order', None)
        
        # Update standard fields
        for key, value in kwargs.items():
            if hasattr(tasksmanager, key):
                setattr(tasksmanager, key, value)
        
        # Update handover settings if provided
        if enable_handover is not None:
            tasksmanager.set_handover_enabled(enable_handover)
        
        if task_order is not None:
            tasksmanager.set_task_order(task_order)
        
        # Update timestamp
        tasksmanager.updated_at = datetime.now()
        
        # Update in persistence
        self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
        
        # Trigger state save
        self.trigger_save_state()
        
        return tasksmanager_id

    def get_tasks_for_tasksmanager(self, tasksmanager_id: str) -> List[Task]:
        """Get all tasks for a specific task manager.
        
        Args:
            tasksmanager_id: ID of the task manager to get tasks for
            
        Returns:
            List of tasks associated with the specified task manager
        """
        tasks = self.get_tasks()
        return [task for task in tasks if task.tasksmanager_id == tasksmanager_id]
