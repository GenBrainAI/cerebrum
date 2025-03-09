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
from ...models.toolset import Tool
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from ...models.specialized_state import StateType, ToolManagementState, StateMetadata
from ..state.state_manager import ViewStateManager
from ..models.tree_node import TreeNode
from ..components.tree_component import TreeComponent
from ...utils.state_loader import StateLoader
from ...persistence.in_memory_persistence import InMemoryPersistenceModel
from ..components.tree_select_component import TreeSelectComponent
from ...extensions.dynamic_tools_loader import tools_loader
from ...models.message import Message
from ..components.tool_dialog import ToolDialog
from ...controllers.task_runner import TaskRunner
import logging
import json
from pathlib import Path
import streamlit as st
from .remove_proxy_method import remove_proxy_from_task

class ToolsCatalogController:
    """Controller for tools catalog view with specialized state support."""
    
    def __init__(self, persistence_model):
        self.global_persistence = persistence_model
        self.persistence_model = persistence_model
        self.view_state = ViewState(view_name="tools_catalog")
        self.state_manager = ViewStateManager(persistence_model)
        self.local_persistence = None
        self.tool_state = None
        self.tree_component = TreeSelectComponent(self.handle_node_click)
        self.logger = logging.getLogger(__name__)
        self.task_runner = None  # Will be initialized after local persistence is loaded
        self.using_global_persistence = True  # Flag to track which persistence is active
        
        # Initialize dynamic tools loader
        tools_loader.initialize()
        tools_loader.start_file_watching()
        print("✅ Dynamic tools loader initialized and watching for changes")
        
    async def initialize(self):
        """Initialize controller with specialized state."""
        try:
            print("\n🚀 Starting tools controller initialization...")
            
            # Initialize task runner with global persistence
            self.task_runner = TaskRunner(self.global_persistence)
            await self.task_runner.initialize()
            print("✅ Task runner initialized with global persistence")
            
            # Look in state/specialized directory for dynamic tools state
            state_file = Path("state/specialized/dynamic_tools_state.json")
            if not state_file.exists():
                # Fallback to StateLoader
                state_file = StateLoader.get_state_file("dynamic_tools_state.json")
            
            print(f"📁 Checking state file path: {state_file}")
            
            if not state_file or not state_file.exists():
                print(f"🔴 Specialized state file not found at {state_file}")
                self.using_global_persistence = True
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
                # Keep track that we're using local persistence
                self.using_global_persistence = False
                
                # Initialize task runner with local persistence
                self.task_runner = TaskRunner(self.local_persistence)
                await self.task_runner.initialize()
                print("✅ Task runner initialized with local persistence")
                
                # Switch to local persistence
                self.persistence_model = self.local_persistence
                
                # Get task context from local persistence
                task_managers = self.local_persistence.tasksmanagers.list()
                tasks = self.local_persistence.tasks.list()
                
                print(f"📊 Found {len(task_managers)} task managers and {len(tasks)} tasks")
                
                # Debug tools catalog state
                print("\n🔍 Checking tools catalog state...")
                try:
                    catalog_tools = tools_loader.load_tools_from_directory(tools_loader.default_tools_dir)
                    print(f"📦 Found {len(catalog_tools)} tools in catalog:")
                    for tool_name in catalog_tools:
                        print(f"  - {tool_name}")
                except Exception as e:
                    print(f"❌ Error listing catalog tools: {str(e)}")
                
                # Set status in view state
                self.view_state.task_status = {
                    "loaded": True,
                    "tasksmanager_name": task_managers[0].name if task_managers else "Unknown",
                    "task_name": tasks[0].name if tasks else "Unknown"
                }
            else:
                print("❌ Failed to create local persistence model")
                self.using_global_persistence = True
                
        except Exception as e:
            print(f"❌ Error initializing tools controller: {str(e)}")
            self.using_global_persistence = True
        
    def get_active_persistence(self):
        """Get the currently active persistence model."""
        return self.global_persistence if self.using_global_persistence else self.local_persistence

    def use_global_persistence(self):
        """Switch to using the global persistence model."""
        self.persistence_model = self.global_persistence
        self.using_global_persistence = True
        
    def use_local_persistence(self):
        """Switch to using the local persistence model if available."""
        if self.local_persistence:
            self.persistence_model = self.local_persistence
            self.using_global_persistence = False
            return True
        return False

    async def get_tools_tree(self) -> Optional[TreeNode]:
        """Get tools catalog as tree structure."""
        try:
            print("\n🌳 Building tools catalog tree...")
            
            # Create root node
            root = TreeNode(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                name="Tools Catalog",
                type="root",
                metadata={},
                data={}
            )
            print("✅ Created root node")
            
            # Create category nodes with fixed UUIDs for consistency
            categories = {
                "api": TreeNode(
                    id=UUID('11111111-1111-1111-1111-111111111111'),
                    name="API Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "function": TreeNode(
                    id=UUID('22222222-2222-2222-2222-222222222222'),
                    name="Functions",
                    type="category",
                    metadata={},
                    data={}
                ),
                "langchain": TreeNode(
                    id=UUID('33333333-3333-3333-3333-333333333333'),
                    name="LangChain Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "utility": TreeNode(
                    id=UUID('44444444-4444-4444-4444-444444444444'),
                    name="Utility Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "github": TreeNode(
                    id=UUID('55555555-5555-5555-5555-555555555555'),
                    name="GitHub Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "file": TreeNode(
                    id=UUID('66666666-6666-6666-6666-666666666666'),
                    name="File Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "web": TreeNode(
                    id=UUID('77777777-7777-7777-7777-777777777777'),
                    name="Web Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "internal": TreeNode(
                    id=UUID('88888888-8888-8888-8888-888888888888'),
                    name="Internal Tools",
                    type="category",
                    metadata={},
                    data={}
                ),
                "other": TreeNode(
                    id=UUID('99999999-9999-9999-9999-999999999999'),
                    name="Other",
                    type="category",
                    metadata={},
                    data={}
                )
            }
            print("✅ Created category nodes")
            
            # Add all categories to root (even if empty)
            for category in categories.values():
                root.children.append(category)
            
            # Get tools from catalog
            try:
                print("\n📦 Getting catalog tools...")
                # First load tools from directory to ensure they're registered
                tools_loader.load_tools_from_directory(tools_loader.default_tools_dir)
                # Then get the list of tools from the catalog
                catalog_tools = tools_loader.tools_catalog.list_tools()
                print(f"✅ Found {len(catalog_tools)} catalog tools")
                
                # Add catalog tools to categories
                for tool_name in catalog_tools:
                    print(f"  Processing tool: {tool_name}")
                    
                    # Determine category based on tool name
                    category_name = 'other'
                    if 'github' in tool_name.lower():
                        category_name = 'github'
                    elif 'file' in tool_name.lower():
                        category_name = 'file'
                    elif 'web' in tool_name.lower() or 'url' in tool_name.lower():
                        category_name = 'web'
                    elif 'internal' in tool_name.lower():
                        category_name = 'internal'
                    elif 'api' in tool_name.lower():
                        category_name = 'api'
                    elif 'langchain' in tool_name.lower():
                        category_name = 'langchain'
                    elif 'util' in tool_name.lower():
                        category_name = 'utility'
                    
                    # Get tool metadata
                    tool_metadata = tools_loader.tools_catalog.get_tool_metadata(tool_name)
                    description = tool_metadata.description if tool_metadata else ''
                    
                    tool_node = TreeNode(
                        id=uuid4(),
                        name=tool_name,
                        type="tool",
                        metadata={
                            "description": description,
                            "source": "catalog"
                        },
                        data={}
                    )
                    categories[category_name].children.append(tool_node)
                    print(f"  ✅ Added to {category_name} category")
                
            except Exception as e:
                print(f"❌ Error getting catalog tools: {str(e)}")
                import traceback
                print(f"Stack trace: {traceback.format_exc()}")
            
            # Get tools from persistence
            try:
                print("\n📦 Getting persisted tools...")
                persisted_tools = self.global_persistence.tools.list()
                print(f"✅ Found {len(persisted_tools)} persisted tools")
                
                # Add persisted tools to categories
                for tool in persisted_tools:
                    print(f"  Processing tool: {tool.name}")
                    
                    # Determine category based on tool name
                    category_name = 'other'
                    if 'github' in tool.name.lower():
                        category_name = 'github'
                    elif 'file' in tool.name.lower():
                        category_name = 'file'
                    elif 'web' in tool.name.lower() or 'url' in tool.name.lower():
                        category_name = 'web'
                    elif 'internal' in tool.name.lower():
                        category_name = 'internal'
                    elif 'api' in tool.name.lower():
                        category_name = 'api'
                    elif 'langchain' in tool.name.lower():
                        category_name = 'langchain'
                    elif 'util' in tool.name.lower():
                        category_name = 'utility'
                    
                    tool_node = TreeNode(
                        id=UUID(tool.id) if isinstance(tool.id, str) else tool.id,
                        name=tool.name,
                        type="tool",
                        metadata={
                            "description": getattr(tool, 'description', ''),
                            "source": "persistence"
                        },
                        data={}
                    )
                    categories[category_name].children.append(tool_node)
                    print(f"  ✅ Added to {category_name} category")
                
            except Exception as e:
                print(f"❌ Error getting persisted tools: {str(e)}")
                import traceback
                print(f"Stack trace: {traceback.format_exc()}")
            
            # Remove empty categories
            root.children = [cat for cat in root.children if cat.children]
            
            print("\n🎯 Final tree structure:")
            print(f"  Categories: {len(root.children)}")
            for category in root.children:
                print(f"  - {category.name}: {len(category.children)} tools")
            
            return root
            
        except Exception as e:
            print(f"❌ Error building tools tree: {str(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            return None
            
    async def handle_chat(self, message: str) -> str:
        """Process chat messages."""
        try:
            # Debug logging for persistence models
            print("\n🔍 Debug - Tools Controller State:")
            print(f"  Global Persistence Type: {type(self.global_persistence)}")
            print(f"  Local Persistence Type: {type(self.local_persistence) if hasattr(self, 'local_persistence') else 'None'}")
            
            # Add user message to chat history
            user_message = {
                "role": "user",
                "content": message,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(user_message)
            
            # Save chat history to session state immediately after adding user message
            if 'tools_controller' in st.session_state:
                st.session_state.tools_controller.view_state.chat_history = self.view_state.chat_history
            
            # Debug task status
            if self.view_state.task_status:
                print("\n📋 Task Status:")
                print(f"  Loaded: {self.view_state.task_status.get('loaded')}")
                print(f"  Task ID: {self.view_state.task_status.get('task_id')}")
                print(f"  Manager ID: {self.view_state.task_status.get('tasksmanager_id')}")
                
                # List available tasks in both persistence models
                if hasattr(self, 'local_persistence') and self.local_persistence:
                    local_tasks = self.local_persistence.tasks.list()
                    print("\n📚 Local Persistence Tasks:")
                    for task in local_tasks:
                        print(f"  - {task.id}: {task.name}")
                
                global_tasks = self.global_persistence.tasks.list()
                print("\n🌍 Global Persistence Tasks:")
                for task in global_tasks:
                    print(f"  - {task.id}: {task.name}")
            
            # Process message and get response
            if self.view_state.task_status and self.view_state.task_status.get("loaded"):
                task_id = self.view_state.task_status.get("task_id")
                manager_id = self.view_state.task_status.get("tasksmanager_id")
                
                if task_id and manager_id:
                    print(f"\n🎯 Attempting to run task:")
                    print(f"  Task ID: {task_id}")
                    print(f"  Manager ID: {manager_id}")
                    
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
                    if 'tools_controller' in st.session_state:
                        st.session_state.tools_controller.view_state.chat_history = self.view_state.chat_history
                    
                    # Save chat history to persistence
                    if self.local_persistence and task_id:
                        task = self.local_persistence.tasks.read(task_id)
                        if task:
                            if not hasattr(task, 'chat_sessions'):
                                task.chat_sessions = {}
                            session_id = str(uuid4())
                            task.chat_sessions[session_id] = self.view_state.chat_history
                            self.local_persistence.tasks.update(task_id, task)
                    
                    return response_text
                else:
                    print("\n⚠️ Missing task or manager ID")
                    response_text = "No active task or manager ID available"
            else:
                print("\n⚠️ No active task loaded")
                response_text = "No active task loaded. Please initialize first."
            
            # Add system response to chat history
            system_message = {
                "role": "assistant",
                "content": response_text,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(system_message)
            
            # Final save of chat history to session state
            if 'tools_controller' in st.session_state:
                st.session_state.tools_controller.view_state.chat_history = self.view_state.chat_history
            
            return response_text
                
        except Exception as e:
            self.logger.error(f"Chat handling error: {str(e)}")
            print(f"\n❌ Error in handle_chat: {str(e)}")
            
            # Add error message to chat history
            error_message = {
                "role": "assistant",
                "content": f"An error occurred: {str(e)}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.view_state.chat_history.append(error_message)
            
            # Save error message to session state
            if 'tools_controller' in st.session_state:
                st.session_state.tools_controller.view_state.chat_history = self.view_state.chat_history
            
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
        
    def handle_node_click(self, node: TreeNode):
        """Handle tree node click events."""
        self.view_state.selected_node = node.id
        # No action needed for node clicks in this version
        pass

    def create_proxy_for_task(self, task_id: str, tool_names: List[str], proxy_name: str = "New CurriedProxy") -> Optional[str]:
        """Create a new CurriedProxy for a task and add specified tools to it."""
        try:
            # Get the task from the active persistence model
            active_persistence = self.get_active_persistence()
            task = active_persistence.tasks.read(task_id)
            if not task:
                self.logger.error(f"Task not found: {task_id}")
                return None
                
            # Create a new CurriedProxy
            from ...controllers.curried_proxy import CurriedProxy
            curried_proxy = CurriedProxy()
            self.logger.info(f"Created new CurriedProxy '{proxy_name}' with ID: {curried_proxy.id}")
            
            # Add tools from the tools catalog
            from ...tools.tools_catalog import tools_catalog, ToolMetadata
            for tool_name in tool_names:
                try:
                    if tool_name in tools_catalog.list_tools():
                        tool_metadata = tools_catalog.get_tool_metadata(tool_name)
                        if tool_metadata:
                            self.logger.info(f"Found tool metadata for {tool_name}, adding to proxy")
                            # Add the tool to the proxy's tool_names list directly
                            if tool_name not in curried_proxy.tool_names:
                                curried_proxy.tool_names.append(tool_name)
                        else:
                            self.logger.warning(f"No metadata found for tool {tool_name}")
                    else:
                        self.logger.warning(f"Tool {tool_name} not found in tools catalog")
                except Exception as tool_error:
                    self.logger.error(f"Error adding tool {tool_name}: {str(tool_error)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            # Log the tools added
            self.logger.info(f"Added {len(curried_proxy.tool_names)} tools to proxy: {', '.join(curried_proxy.tool_names)}")
            
            # Convert CurriedProxy to CurriedProxyInfo for persistence
            curried_proxy_info = curried_proxy.to_info()
            
            # Add name to the proxy info if possible
            if hasattr(curried_proxy_info, 'name'):
                curried_proxy_info.name = proxy_name
            
            # Save the CurriedProxyInfo object
            created_proxy = active_persistence.curried_proxies.create(curried_proxy_info)
            
            if not created_proxy:
                self.logger.error("Failed to create CurriedProxyInfo in persistence model")
                return None
                
            # Link the proxy to the task
            task.curried_proxy_id = str(curried_proxy.id)
            
            # Use update instead of save for TaskCrud
            try:
                active_persistence.tasks.update(task_id, task)
                self.logger.info(f"Updated task {task_id} with CurriedProxy {curried_proxy.id}")
            except AttributeError:
                # If update doesn't exist, try other methods
                try:
                    active_persistence.tasks.create(task)
                    self.logger.info(f"Created task {task_id} with CurriedProxy {curried_proxy.id}")
                except Exception as e:
                    self.logger.error(f"Failed to update task with proxy: {str(e)}")
                    return None
            
            return str(curried_proxy.id)
        except Exception as e:
            self.logger.error(f"Error creating proxy for task: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def get_available_curried_proxies(self) -> List[dict]:
        """Get all available CurriedProxies in the active persistence model."""
        try:
            active_persistence = self.get_active_persistence()
            proxies = active_persistence.curried_proxies.list()
            
            # Format for UI display
            result = []
            for proxy in proxies:
                # Skip proxies without an ID
                if not hasattr(proxy, 'id'):
                    continue

                # Extract ID as string
                proxy_id = str(proxy.id)
                
                # Extract name
                proxy_name = "Unnamed Proxy"
                if hasattr(proxy, 'name') and proxy.name:
                    proxy_name = proxy.name
                
                # Extract tools safely
                tools = []
                tool_count = 0
                try:
                    if hasattr(proxy, 'tools') and proxy.tools:
                        tools = [getattr(tool, 'name', f"Tool-{i}") for i, tool in enumerate(proxy.tools)]
                        tool_count = len(tools)
                except Exception as tools_error:
                    self.logger.warning(f"Error extracting tools from proxy {proxy_id}: {str(tools_error)}")
                
                # Add to result
                result.append({
                    "id": proxy_id,
                    "name": proxy_name,
                    "tool_count": tool_count,
                    "tools": tools
                })
                
            self.logger.info(f"Found {len(result)} available CurriedProxies")
            return result
        except Exception as e:
            self.logger.error(f"Error getting curried proxies: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []

    def link_existing_proxy_to_task(self, task_id: str, proxy_id: str) -> bool:
        """Link an existing CurriedProxy to a task."""
        try:
            active_persistence = self.get_active_persistence()
            task = active_persistence.tasks.read(task_id)
            if not task:
                self.logger.error(f"Task not found: {task_id}")
                return False
                
            # Check if the proxy exists
            proxy = active_persistence.curried_proxies.read(proxy_id)
            if not proxy:
                self.logger.error(f"CurriedProxy not found: {proxy_id}")
                return False
                
            # Link the proxy to the task
            task.curried_proxy_id = proxy_id
            
            # Use update instead of save for TaskCrud
            try:
                active_persistence.tasks.update(task_id, task)
                self.logger.info(f"Updated task {task_id} with CurriedProxy {proxy_id}")
                return True
            except AttributeError:
                # If update doesn't exist, try other methods
                try:
                    active_persistence.tasks.create(task)
                    self.logger.info(f"Created task {task_id} with CurriedProxy {proxy_id}")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to update task with proxy: {str(e)}")
                    return False
        except Exception as e:
            self.logger.error(f"Error linking proxy to task: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def add_tools_to_task_toolset(self, task_id: str, toolset_name: str, tool_names: List[str]) -> Optional[str]:
        """Create a new toolset for a task and add specified tools to it."""
        try:
            # Get the task from the active persistence model
            active_persistence = self.get_active_persistence()
            task = active_persistence.tasks.read(task_id)
            if not task:
                return None
                
            # Create a new toolset
            from ...models.toolset import Toolset, Tool
            from uuid import uuid4
            
            toolset = Toolset(
                id=str(uuid4()),
                name=toolset_name,
                description=f"Toolset created for task {task.name}"
            )
            
            # Create tools and add to toolset
            tool_ids = []
            for name in tool_names:
                tool = Tool(
                    id=str(uuid4()),
                    function=type("FunctionModel", (), {"name": name})(),
                    name=name,
                    description=f"Tool {name}"
                )
                active_persistence.tools.save(tool)
                tool_ids.append(tool.id)
            
            # Link tools to toolset
            toolset.tool_ids = tool_ids
            active_persistence.toolsets.save(toolset)
            
            # Link toolset to task
            if not task.toolsets:
                task.toolsets = []
            task.toolsets.append(toolset.id)
            active_persistence.tasks.save(task)
            
            return toolset.id
        except Exception as e:
            self.logger.error(f"Error creating toolset for task: {str(e)}")
            return None

    def export_demo_state(self) -> bool:
        """Export the current state as a demonstration state."""
        try:
            # Use the active persistence model
            active_persistence = self.get_active_persistence()
            if not active_persistence:
                self.logger.error("No persistence model available to export")
                return False
                
            # Export the state to JSON
            state_json = active_persistence.to_json()
            
            # Create the state directory if it doesn't exist
            from pathlib import Path
            state_dir = Path("state")
            state_dir.mkdir(exist_ok=True)
            
            # Save the state to a file in the main state directory
            demo_state_path = state_dir / "task_tool_relationship_demo_state.json"
            with open(demo_state_path, 'w', encoding='utf-8') as f:
                f.write(state_json)
                
            self.logger.info(f"Exported demonstration state to {demo_state_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting demonstration state: {str(e)}")
            return False

    def remove_proxy_from_task(self, task_id: str) -> bool:
        """Remove the CurriedProxy association from a task."""
        from ...controllers.curried_proxy import CurriedProxy
        active_persistence = self.get_active_persistence()
        return CurriedProxy.remove_from_task(active_persistence, task_id, self.logger)

    def add_tools_to_proxy(self, proxy_id: str, tool_names: List[str]) -> bool:
        """Add tools to an existing CurriedProxy.
        
        Args:
            proxy_id: The ID of the CurriedProxy to add tools to
            tool_names: List of tool names to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            active_persistence = self.get_active_persistence()
            proxy_info = active_persistence.curried_proxies.read(proxy_id)
            if not proxy_info:
                self.logger.error(f"CurriedProxy not found: {proxy_id}")
                return False
                
            # Convert to CurriedProxy
            from ...controllers.curried_proxy import CurriedProxy
            proxy = CurriedProxy.from_info(proxy_info)
            
            # Add tools from the tools catalog
            from ...tools.tools_catalog import tools_catalog
            tools_added = 0
            for tool_name in tool_names:
                if tool_name in tools_catalog.list_tools():
                    if tool_name not in proxy.tool_names:
                        proxy.tool_names.append(tool_name)
                        tools_added += 1
                        self.logger.info(f"Added tool {tool_name} to proxy {proxy_id}")
                    else:
                        self.logger.info(f"Tool {tool_name} already in proxy {proxy_id}")
                else:
                    self.logger.warning(f"Tool {tool_name} not found in tools catalog")
            
            if tools_added == 0:
                self.logger.info(f"No new tools added to proxy {proxy_id}")
                return True  # Still return success as this isn't an error
                
            # Convert back to CurriedProxyInfo and save
            new_proxy_info = proxy.to_info()
            active_persistence.curried_proxies.update(proxy_id, new_proxy_info)
            
            self.logger.info(f"Added {tools_added} tools to proxy {proxy_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding tools to proxy: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    def remove_tools_from_proxy(self, proxy_id: str, tool_names: List[str]) -> bool:
        """Remove tools from an existing CurriedProxy.
        
        Args:
            proxy_id: The ID of the CurriedProxy to remove tools from
            tool_names: List of tool names to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            active_persistence = self.get_active_persistence()
            proxy_info = active_persistence.curried_proxies.read(proxy_id)
            if not proxy_info:
                self.logger.error(f"CurriedProxy not found: {proxy_id}")
                return False
                
            # Convert to CurriedProxy
            from ...controllers.curried_proxy import CurriedProxy
            proxy = CurriedProxy.from_info(proxy_info)
            
            # Remove tools
            tools_removed = 0
            for tool_name in tool_names:
                if tool_name in proxy.tool_names:
                    proxy.tool_names.remove(tool_name)
                    tools_removed += 1
                    self.logger.info(f"Removed tool {tool_name} from proxy {proxy_id}")
                else:
                    self.logger.info(f"Tool {tool_name} not in proxy {proxy_id}")
            
            if tools_removed == 0:
                self.logger.info(f"No tools removed from proxy {proxy_id}")
                return True  # Still return success as this isn't an error
                
            # Convert back to CurriedProxyInfo and save
            new_proxy_info = proxy.to_info()
            active_persistence.curried_proxies.update(proxy_id, new_proxy_info)
            
            self.logger.info(f"Removed {tools_removed} tools from proxy {proxy_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing tools from proxy: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    def rename_proxy(self, proxy_id: str, new_name: str) -> bool:
        """Rename an existing CurriedProxy.
        
        Args:
            proxy_id: The ID of the CurriedProxy to rename
            new_name: The new name for the proxy
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            active_persistence = self.get_active_persistence()
            proxy_info = active_persistence.curried_proxies.read(proxy_id)
            if not proxy_info:
                self.logger.error(f"CurriedProxy not found: {proxy_id}")
                return False
                
            # Check if proxy_info has a name attribute
            if not hasattr(proxy_info, 'name'):
                self.logger.error(f"CurriedProxyInfo object does not have a name attribute")
                return False
                
            # Update the name directly on the CurriedProxyInfo object
            proxy_info.name = new_name
            
            # Save the updated proxy
            active_persistence.curried_proxies.update(proxy_id, proxy_info)
            
            self.logger.info(f"Renamed proxy {proxy_id} to '{new_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Error renaming proxy: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False