# src/server/views/controllers/task_management_controller.py
from __future__ import annotations
import os
import sys
import inspect
import streamlit as st
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
import logging
import json
from pathlib import Path

from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ...models.task import Task
from ...models.tasks_manager import TasksManager
from ...models.message import Message
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...controllers.task_runner import TaskRunner


class TaskManagementController:
    """Controller for task and task manager management view."""
    
    def __init__(self, persistence_model):
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_name="task_management")
        self.logger = logging.getLogger(__name__)
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.task_runner = None  # Will be initialized after persistence is loaded
        
        # Initialize view state attributes
        self.view_state.selected_task_manager = None
        self.view_state.selected_task = None
        self.view_state.available_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "ollama/llama3"
        ]
        
    async def initialize(self):
        """Initialize controller."""
        self.task_runner = TaskRunner(self.persistence_model)
        await self.task_runner.initialize()
        print("✅ Task runner initialized with persistence")
        
    def handle_node_click(self, node_id: UUID):
        """Handle tree node selection."""
        self.view_state.selected_node = node_id
        
    def get_task_managers(self) -> List[TasksManager]:
        """Get all task managers from persistence."""
        try:
            return self.persistence_model.tasksmanagers.list()
        except Exception as e:
            self.logger.error(f"Error getting task managers: {str(e)}")
            return []
            
    def get_tasks(self, tasksmanager_id: Optional[str] = None) -> List[Task]:
        """Get tasks for a specific task manager or all tasks."""
        try:
            all_tasks = self.persistence_model.tasks.list()
            if tasksmanager_id:
                return [task for task in all_tasks if task.tasksmanager_id == tasksmanager_id]
            return all_tasks
        except Exception as e:
            self.logger.error(f"Error getting tasks: {str(e)}")
            return []
            
    def create_task_manager(self, name: str, model: Optional[str] = None, 
                          description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Create a new task manager."""
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
            
            # Save to persistence
            created_manager = self.persistence_model.tasksmanagers.create(task_manager)
            return created_manager
        except Exception as e:
            self.logger.error(f"Error creating task manager: {str(e)}")
            return None
            
    def update_task_manager(self, task_manager_id: str, name: Optional[str] = None, 
                          model: Optional[str] = None, description: Optional[str] = None, 
                          system_message: Optional[str] = None) -> Optional[TasksManager]:
        """Update an existing task manager."""
        try:
            # Get existing task manager
            task_manager = self.persistence_model.tasksmanagers.read(task_manager_id)
            if not task_manager:
                self.logger.error(f"Task manager not found: {task_manager_id}")
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
                    
            # Update in persistence
            updated_manager = self.persistence_model.tasksmanagers.update(task_manager_id, task_manager)
            return updated_manager
        except Exception as e:
            self.logger.error(f"Error updating task manager: {str(e)}")
            return None
            
    def delete_task_manager(self, task_manager_id: str) -> bool:
        """Delete a task manager and its associated tasks."""
        try:
            # Get all tasks for this manager
            tasks = self.get_tasks(task_manager_id)
            
            # Delete all tasks first
            for task in tasks:
                self.persistence_model.tasks.delete(task.id)
                
            # Delete the task manager
            return self.persistence_model.tasksmanagers.delete(task_manager_id)
        except Exception as e:
            self.logger.error(f"Error deleting task manager: {str(e)}")
            return False
            
    def create_task(self, name: str, tasksmanager_id: str, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: bool = False) -> Optional[Task]:
        """Create a new task associated with a task manager."""
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
            
            # Save to persistence
            created_task = self.persistence_model.tasks.create(task)
            return created_task
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            return None
            
    def update_task(self, task_id: str, name: Optional[str] = None, 
                  tasksmanager_id: Optional[str] = None, model: Optional[str] = None,
                  description: Optional[str] = None, system_message: Optional[str] = None,
                  inherit_manager_context: Optional[bool] = None) -> Optional[Task]:
        """Update an existing task."""
        try:
            # Get existing task
            task = self.persistence_model.tasks.read(task_id)
            if not task:
                self.logger.error(f"Task not found: {task_id}")
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
                system_messages = [msg for msg in task.messages if msg.role == "system"]
                if system_messages:
                    system_messages[0].content = system_message
                else:
                    task.messages.append(Message(role="system", content=system_message))
                    
            # Update in persistence
            updated_task = self.persistence_model.tasks.update(task_id, task)
            return updated_task
        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            return None
            
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            return self.persistence_model.tasks.delete(task_id)
        except Exception as e:
            self.logger.error(f"Error deleting task: {str(e)}")
            return False
            
    def get_system_message(self, obj: Any) -> Optional[str]:
        """Extract system message from a task or task manager."""
        if not obj or not hasattr(obj, 'messages'):
            return None
            
        system_messages = [msg.content for msg in obj.messages if msg.role == "system"]
        return system_messages[0] if system_messages else None 