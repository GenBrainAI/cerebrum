# src/server/views/controllers/tools_view_controller.py
from __future__ import annotations
import os
import sys
import inspect
import importlib.util
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
from ...models.exceptions import StateError, StateNotFoundError, StateValidationError
from ...models.function import Tool
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, ToolManagementState, StateMetadata
from ..state.state_manager import ViewStateManager
from ..components.tree_component import TreeNode
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...tools.tools_catalog import tools_catalog
from ...models.message import Message
from ..components.tool_dialog import ToolDialog
import logging
import json
from pathlib import Path

class ToolsCatalogController:
    """Controller for tools catalog view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.view_state = ViewState(view_name="tools_catalog")
        self.state_manager = ViewStateManager(persistence_model)
        self.local_persistence = None
        self.tool_state = None
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("Starting controller initialization...")
            # Note: We keep the old state file path in remarks for future reference
            # old_state_file = StateLoader.get_state_file("tools_management_state.json")
            
            state_file = StateLoader.get_state_file("dynamic_tools_state.json")
            print(f"Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                # Future enhancement: Add fallback to tools_management_state.json
                # if old_state_file and old_state_file.exists():
                #     print("Falling back to tools management state...")
                #     state_file = old_state_file
                # else:
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
                    # Find the dynamic tools manager and task
                    # Note: Old lookup was for "Tools Management"
                    tools_manager = next(
                        (m for m in task_managers if "Dynamic Langchain Tools Generator" in m.name),
                        task_managers[0]
                    )
                    tools_task = next(
                        (t for t in tasks if t.tasksmanager_id == tools_manager.id),
                        None
                    )
                    
                    if tools_task:
                        # Update view state with task context
                        self.view_state.set_active_task(
                            task_id=tools_task.id,
                            task_name=tools_task.name,
                            manager_id=tools_manager.id,
                            manager_name=tools_manager.name
                        )
                        
                        # Set tool state with CrewAI context
                        # Note: This is new for dynamic tools, old version only had:
                        # self.tool_state = {
                        #     "active_tools": [],
                        #     "total_tools": 0,
                        #     "manager_id": tools_manager.id,
                        #     "task_id": tools_task.id
                        # }
                        self.tool_state = {
                            "active_tools": [],
                            "total_tools": 0,
                            "manager_id": tools_manager.id,
                            "task_id": tools_task.id,
                            "crewai_config_id": tools_task.crewai_config_id,
                            "curried_proxy_id": tools_task.curried_proxy_id
                        }
                        
                        print(f"🟢 Loaded state for {tools_manager.name}-{tools_task.name}")
                        print(f"CrewAI Config ID: {tools_task.crewai_config_id}")
                        print(f"Curried Proxy ID: {tools_task.curried_proxy_id}")
                    else:
                        print("🔴 No dynamic tools task found")
                else:
                    print("🔴 No task context found in state file")
            else:
                print("🔴 Failed to create local persistence model")
                
        except Exception as e:
            print(f"Error initializing tools controller: {str(e)}")
            raise
        
    async def get_tools_tree(self) -> Optional[TreeNode]:
        """Get tools catalog as tree structure."""
        try:
            # Create root node
            root = TreeNode(UUID('00000000-0000-0000-0000-000000000000'), "Tools Catalog", "root")
            
            # Create category nodes with fixed UUIDs for consistency
            categories = {
                "api": TreeNode(
                    UUID('11111111-1111-1111-1111-111111111111'), 
                    "API Tools", 
                    "category"
                ),
                "function": TreeNode(
                    UUID('22222222-2222-2222-2222-222222222222'), 
                    "Functions", 
                    "category"
                ),
                "langchain": TreeNode(
                    UUID('33333333-3333-3333-3333-333333333333'), 
                    "LangChain Tools", 
                    "category"
                ),
                "utility": TreeNode(
                    UUID('44444444-4444-4444-4444-444444444444'), 
                    "Utility Tools", 
                    "category"
                ),
                "custom": TreeNode(
                    UUID('55555555-5555-5555-5555-555555555555'), 
                    "Custom Tools", 
                    "category"
                ),
                "other": TreeNode(
                    UUID('66666666-6666-6666-6666-666666666666'), 
                    "Other", 
                    "category"
                )
            }
            
            # Add all categories to root (even if empty)
            for category in categories.values():
                root.children.append(category)
            
            # Try to get tools from both sources
            try:
                persisted_tools = self.global_persistence.tools.list()
            except Exception as e:
                print(f"Error getting persisted tools: {str(e)}")
                persisted_tools = []
            
            try:
                catalog_tool_names = tools_catalog.list_tools()
            except Exception as e:
                print(f"Error getting catalog tools: {str(e)}")
                catalog_tool_names = []
            
            # Process persisted tools if any
            if persisted_tools:
                for tool in persisted_tools:
                    try:
                        tool_node = TreeNode(
                            UUID(tool.id),
                            tool.name,
                            "tool"
                        )
                        
                        # Add tool details if available
                        if hasattr(tool, 'description'):
                            tool_node.description = tool.description
                        if hasattr(tool, 'metadata'):
                            tool_node.metadata = tool.metadata
                        
                        # Determine tool category
                        category = 'other'
                        if hasattr(tool, 'tool_type'):
                            tool_type = tool.tool_type.lower()
                            if tool_type in categories:
                                category = tool_type
                        elif hasattr(tool, 'metadata') and tool.metadata.get('type'):
                            meta_type = tool.metadata['type'].lower()
                            if meta_type in categories:
                                category = meta_type
                        
                        # Add tool to appropriate category
                        categories[category].children.append(tool_node)
                        
                    except Exception as e:
                        print(f"Error processing persisted tool {tool.id}: {str(e)}")
            
            # Process catalog tools if any
            if catalog_tool_names:
                for tool_name in catalog_tool_names:
                    try:
                        # Get tool instance
                        tool = tools_catalog.get_tool_instance(tool_name)
                        if not tool:
                            continue
                        
                        # Create unique UUID based on tool name
                        tool_uuid = uuid4() # UUID(bytes=tool_name.encode()[:16], version=3)
                        # print(f"Creating tool node for {tool_name} with UUID {tool_uuid}")
                        tool_node = TreeNode(
                            tool_uuid,
                            tool_name,
                            "catalog_tool"
                        )
                        
                        # Add tool details
                        if hasattr(tool, 'description'):
                            tool_node.description = tool.description
                        if hasattr(tool, '__doc__') and tool.__doc__:
                            tool_node.description = tool.__doc__.strip()
                        
                        # Try to determine category from tool attributes or class name
                        category = 'other'
                        if hasattr(tool, 'tool_type'):
                            tool_type = tool.tool_type.lower()
                            if tool_type in categories:
                                category = tool_type
                        elif hasattr(tool, 'category'):
                            cat_type = tool.category.lower()
                            if cat_type in categories:
                                category = cat_type
                        elif 'langchain' in str(tool.__class__.__module__).lower():
                            category = 'langchain'
                        elif callable(tool):
                            category = 'function'
                        
                        # Add tool to appropriate category
                        categories[category].children.append(tool_node)
                        
                    except Exception as e:
                        print(f"Error processing catalog tool {tool_name}: {str(e)}")
            
            # Sort tools within each category
            for category in categories.values():
                category.children.sort(key=lambda x: x.name)
            
            # Add empty state indicators to categories
            for category in categories.values():
                if not category.children:
                    empty_node = TreeNode(
                        uuid4(),
                        "No tools available",
                        "empty"
                    )
                    category.children.append(empty_node)
            
            return root
            
        except Exception as e:
            print(f"Error building tools tree: {str(e)}")
            return None
            
    async def handle_chat(self, message: str) -> str:
        """Process chat messages."""
        try:
            # Add user message to chat history
            self.view_state.chat_history.append({
                "role": "user",
                "content": message
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
                    
                    # Add CrewAI context for dynamic tools
                    running_extra_params = {
                        'messages': current_messages,
                        'crewai_config_id': self.tool_state.get('crewai_config_id'),
                        'curried_proxy_id': self.tool_state.get('curried_proxy_id'),
                        'context': {
                            'tool_request': message,
                            'active_tools': self.tool_state.get('active_tools', []),
                            'total_tools': self.tool_state.get('total_tools', 0)
                        }
                    }
                    
                    # Run task with CrewAI context
                    response = await self.state_manager.task_runner.run_task(
                        tasksmanager_id=manager_id,
                        task_id=task_id,
                        running_extra_params=running_extra_params
                    )
                    
                    # Process response
                    if isinstance(response, dict) and 'response' in response:
                        response_text = response['response']
                        
                        # Update tool state if new tool was created
                        if 'tool_created' in response:
                            self.tool_state['active_tools'].append(response['tool_created'])
                            self.tool_state['total_tools'] += 1
                            
                            # Save updated state
                            try:
                                state_data = self.view_state.dict()
                                await self.state_manager.save_session_state("tools_catalog", state_data)
                            except Exception as e:
                                self.logger.error(f"Failed to save session state: {str(e)}")
                    else:
                        response_text = str(response)
                    
                    # Add assistant response to chat history
                    self.view_state.chat_history.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    
                    return response_text
                else:
                    return "No active task to process message."
            else:
                return "Tools management not loaded. Please initialize first."
                
        except Exception as e:
            self.logger.error(f"Chat handling error: {str(e)}")
            return f"An error occurred: {str(e)}"
            
    async def _process_tool_command(self, message: str) -> str:
        """Process tool management commands or run active task."""
        try:
            command = message.lower().strip()
            
            # Check for specific commands
            if "add tool" in command:
                name = command.split("add tool")[-1].strip()
                if not name:
                    raise StateValidationError("Tool name is required")
                    
                tool = await self._create_tool(name)
                if self.tool_state:
                    self.tool_state.active_tools.append(tool.id)
                return f"Added tool: {tool.name}"
                
            elif "list tools" in command:
                tools = await self._get_active_tools()
                if not tools:
                    return "No active tools found"
                return "Active tools:\n" + "\n".join(f"- {t.name}" for t in tools)
                
            elif "help" in command:
                return """Available commands:
- add tool <name>
- list tools
- help"""
            
            # If no command matched, run the active task
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
                    
                    # Add current message
                    user_message = Message(
                        role="user",
                        content=message,
                        file_ids=None,
                        created_at=None,
                        updated_at=None
                    )
                    current_messages.append(user_message)
                    
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
                    
                    return response_text
            
            return "No active task to process message."
                
        except StateError as e:
            raise
        except Exception as e:
            self.logger.error(f"Command processing error: {str(e)}")
            raise StateError(f"Failed to process command: {str(e)}")
            
    async def _create_tool(self, name: str) -> Tool:
        """Create a tool with state tracking."""
        try:
            tool = Tool(name=name)
            created = self.persistence_model.tools.create(tool)
            
            if self.tool_state:
                await self.state_manager.update_state(
                    self.tool_state.id,
                    {
                        "last_created_tool": created.id,
                        "total_tools": len(self.tool_state.active_tools) + 1
                    }
                )
            
            return created
            
        except Exception as e:
            raise StateError(f"Failed to create tool: {str(e)}")
            
    async def _get_active_tools(self) -> List[Tool]:
        """Get active tools from state."""
        if not self.tool_state:
            raise StateNotFoundError("Tool state not initialized")
            
        try:
            return [
                self.persistence_model.tools.get(tool_id)
                for tool_id in self.tool_state.active_tools
                if self.persistence_model.tools.get(tool_id)
            ]
        except Exception as e:
            raise StateError(f"Failed to get active tools: {str(e)}")
        
    def show_tool_dialog(self) -> Optional[Dict[str, Any]]:
        """Show dialog for adding/configuring tools."""
        dialog = ToolDialog(self.view_state, self.persistence_model)
        result = dialog.render()
        
        if result:
            # TODO: Implement tool creation/configuration
            if hasattr(self.persistence_model, 'tools'):
                return self.persistence_model.tools.create(result)
        return None
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        if node.type == "tool":
            # Show tool configuration dialog
            self.show_tool_dialog()