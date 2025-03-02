from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio
import uuid

from src.server.models.task import Task, Message
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.persistence_model import PersistenceModelBase
from src.server.controllers.prompt_transformer import PromptTransformer, MessageTransformer
from ..controllers.tools_operator import ToolsOperator
from ..controllers.operator import ToolsOperator as APIOperator
from ..controllers.curried_proxy import CurriedProxy
from ..controllers.crew_runner import run_crew_task
from ..context.context_provider import ContextProvider
from ..context.context_analytics import ContextAnalytics
from ..controllers.task_tree_flow import TaskNode
from .task_observability import TaskObservabilityManager, ObservabilityLevel
from ..plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)

class TaskExecutionError(Exception):
    """Exception raised when task execution fails."""
    pass

class TaskExecutor:
    """Wrapper class for Task that provides execution functionality."""
    
    def __init__(self, task: Task, task_runner: 'TaskRunner'):
        self.task = task
        self.task_runner = task_runner
        self.observability = TaskObservabilityManager(task.id)

    async def run(self, context: Dict[str, Any]) -> str:
        """Execute the task with the given context."""
        try:
            with self.observability:
                tasksmanager = self.task_runner.persistence_model.tasksmanagers.read(self.task.tasksmanager_id)
                result = await self.task_runner._run_standard_task(
                    task=self.task,
                    running_extra_params=context,
                    tasksmanager=tasksmanager
                )
                return result.get("response", "")
        except Exception as e:
            raise TaskExecutionError(f"Task execution failed: {str(e)}")

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the wrapped task."""
        return getattr(self.task, name)

    @property
    def id(self) -> str:
        """Explicitly forward id property to task."""
        return self.task.id

    @property
    def name(self) -> str:
        """Explicitly forward name property to task."""
        return self.task.name

    @property
    def tasksmanager_id(self) -> str:
        """Explicitly forward tasksmanager_id property to task."""
        return self.task.tasksmanager_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get the task with the given ID if it matches the wrapped task's ID."""
        if task_id == self.task.id:
            return self.task
        return None

class TaskRunner:
    """Runner for executing tasks."""

    def __init__(self, persistence_model: PersistenceModelBase):
        """Initialize TaskRunner with persistence model."""
        self.persistence_model = persistence_model
        self.tools_operator = ToolsOperator()
        self.operator = APIOperator()
        self.observability_managers: Dict[str, TaskObservabilityManager] = {}
        self.context_provider = ContextProvider(persistence_model)
        self.context_analytics = ContextAnalytics()
        self._active_observability_managers = {}
        self._active_tasks = set()  # Track currently running tasks
        self._task_locks = {}  # Locks for each task
        self._task_results = {}  # Store task results
        self._task_errors = {}  # Store task errors
        self._task_status = {}  # Store task status
        self._plugin_manager = None  # Plugin manager instance
        self._initialized = False

    async def initialize(self):
        """Initialize the task runner components."""
        if self._initialized:
            return

        logger.info("🚀 Initializing TaskRunner")
        try:
            # Initialize operator if not already initialized
            if not hasattr(self, 'operator') or not self.operator:
                logger.info("⚙️ Initializing ToolsOperator")
                self.operator = APIOperator(api_provider="openai")
                logger.info("✅ ToolsOperator initialized")
            
            # Initialize context provider if needed
            if not self.context_provider:
                logger.info("📚 Initializing ContextProvider")
                self.context_provider = ContextProvider()
                logger.info("✅ ContextProvider initialized")

            # Initialize plugin manager
            if not self._plugin_manager:
                logger.info("🔌 Initializing PluginManager")
                self._plugin_manager = PluginManager()
                logger.info("✅ PluginManager initialized")

            # Load default plugins
            logger.info("🔌 Loading default plugins...")
            from pathlib import Path
            from ..plugins.agent_framework_config import AgentFrameworkConfig

            # Get plugins directory
            plugins_dir = Path(__file__).parent.parent / "plugins"
            
            # Load CrewAI plugin
            crewai_config = AgentFrameworkConfig(
                name="crewai",
                version="1.0.0",
                description="CrewAI framework integration",
                settings={
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            
            crewai_path = plugins_dir / "crewai_plugin.py"
            if crewai_path.exists():
                success = await self._plugin_manager.load_plugin(
                    str(crewai_path),
                    crewai_config
                )
                if success:
                    logger.info("✅ CrewAI plugin loaded successfully")
                else:
                    logger.error("❌ Failed to load CrewAI plugin")
            else:
                logger.warning("⚠️ CrewAI plugin file not found")
            
            self._initialized = True
            logger.info("✅ TaskRunner initialization complete")
            
        except Exception as e:
            error_msg = f"Failed to initialize TaskRunner: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def _update_task_status(self, task: Task, status: str, error: Optional[str] = None):
        """Update task status and error message."""
        try:
            task.status = status
            task.error = error
            task.updated_at = datetime.now()
            self.persistence_model.tasks.update(task)
        except Exception as e:
            logger.error(f"❌ Failed to update task status: {str(e)}")

    def get_task_observability(self, task_id: str) -> Optional[TaskObservabilityManager]:
        """Get the observability manager for a task."""
        return self._active_observability_managers.get(task_id)

    def _initialize_observability(self, task_id: str) -> TaskObservabilityManager:
        """Initialize observability for a task."""
        if task_id not in self._active_observability_managers:
            logger.info(f"📊 Creating new observability manager for task {task_id}")
            observability = TaskObservabilityManager(task_id)
            self._active_observability_managers[task_id] = observability
            observability.start_capture()
            logger.info("✅ Observability manager created and started")
        return self._active_observability_managers[task_id]

    async def run_task(
        self,
        tasksmanager_id: str,
        task_id: str,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a task with the given ID."""
        observability = None
        try:
            logger.info(f"\n🚀 Running task {task_id} from manager {tasksmanager_id}")
            
            # Get task and manager
            task = self.persistence_model.tasks.read(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            manager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
            if not manager:
                raise ValueError(f"Task manager {tasksmanager_id} not found")
            
            # Initialize observability for this task
            observability = self._initialize_observability(task_id)
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(observability.monitor_execution())
            
            try:
                # Log task execution start
                observability.add_entry(
                    f"Starting execution of task: {task.name}",
                    ObservabilityLevel.INFO
                )
                
                # Update task status
                task.status = "running"
                self.persistence_model.tasks.update(task.id, task)
                
                # Check if this is a CrewAI task
                if hasattr(task, 'crewai_config_id') and task.crewai_config_id:
                    result = await self._run_crewai_task(task, manager, running_extra_params)
                # Check if this is a Tree Flow task
                elif hasattr(task, 'tree_flow_id') and task.tree_flow_id:
                    result = await self._run_tree_flow_task(task, manager, running_extra_params)
                else:
                    # Execute standard task
                    result = await self._run_standard_task(task, running_extra_params or {}, manager)
                
                # Normalize result format
                if isinstance(result, dict):
                    status = result.get("status", "completed")
                    response = result.get("response", result.get("result", ""))
                    error = result.get("error")
                else:
                    status = "completed"
                    response = str(result)
                    error = None
                
                # Update task with result
                task.status = status
                task.result = response
                task.error = error
                self.persistence_model.tasks.update(task.id, task)
                
                # Log successful execution
                observability.add_entry(
                    f"Task completed with status {status}: {task.name}",
                    ObservabilityLevel.INFO
                )
                
                return result
                
            except Exception as e:
                error_msg = f"Task execution failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                
                # Update task status
                task.status = "failed"
                task.error = error_msg
                self.persistence_model.tasks.update(task.id, task)
                
                # Log error in observability
                observability.add_entry(
                    error_msg,
                    ObservabilityLevel.ERROR
                )
                
                return {
                    "status": "failed",
                    "error": error_msg,
                    "response": error_msg
                }
            
            finally:
                # Cancel monitoring task
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                
                # Stop observability capture
                if observability:
                    observability.stop_capture()
                
        except Exception as e:
            error_msg = f"Task runner error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            if observability:
                observability.add_entry(error_msg, ObservabilityLevel.ERROR)
                observability.stop_capture()
            return {
                "status": "failed",
                "error": error_msg,
                "response": error_msg
            }

    async def _run_standard_task(
        self,
        task: Task,
        running_extra_params: Dict[str, Any],
        tasksmanager: Optional[TasksManager] = None
    ) -> Dict[str, Any]:
        """Execute a standard task."""
        try:
            logger.info(f"🔄 Running standard task: {task.name}")
            task_data = task.dict() if hasattr(task, 'dict') else task.model_dump()
            
            # Add running_extra_params to task_data
            if running_extra_params:
                task_data.update(running_extra_params)

            # If a plugin is configured, try to use it
            if hasattr(task, 'framework') and task.framework and self._plugin_manager:
                try:
                    plugin = self._plugin_manager.get_plugin(task.framework)
                    if plugin:
                        agent = await plugin.create_agent(task_data)
                        return await plugin.execute_task(agent, task_data)
                except Exception as plugin_error:
                    logger.warning(f"Plugin execution failed: {str(plugin_error)}, falling back to standard execution")

            # Get or create curried proxy for standard execution
            curried_proxy = self._get_or_create_curried_proxy(task, tasksmanager) if tasksmanager else None

            # Standard task execution using operator for completions
            messages_input = running_extra_params.get('messages', [])
            
            # Validate messages using helper method
            formatted_messages = self._validate_messages(messages_input, "input parameters")
            
            # If no messages provided, use task's default messages
            if not formatted_messages and task.messages:
                formatted_messages = self._validate_messages(task.messages, "task messages")

            if not formatted_messages:
                return {
                    "status": "failed",
                    "response": "No messages found for task execution",
                    "error": "Missing messages"
                }

            # Get model from tasksmanager or use default
            model = None
            if tasksmanager and hasattr(tasksmanager, 'model'):
                model = tasksmanager.model
            if not model and hasattr(task, 'model'):
                model = task.model
            if not model:
                model = "gpt-4o-mini"  # Default model if none specified

            # Execute completion with curried proxy
            response = await self.completion(
                tasksmanager_id=task.tasksmanager_id,
                task_id=task.id,
                messages=formatted_messages,
                model=model,
                curried_proxy=curried_proxy
            )

            return {
                "status": "completed",
                "response": response,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "failed",
                "response": error_msg,
                "error": str(e)
            }

    async def _run_crewai_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task."""
        try:
            logger.info(f"\n🤖 Running CrewAI task: {task.id}")
            
            # Get contexts if needed
            query = running_extra_params.get("context_query") if running_extra_params else None
            logger.info(f"🔍 Getting contexts with query: {query}")
            contexts = await self.context_provider.get_contexts(query) if query else []
            logger.info(f"✅ Found {len(contexts)} contexts")
            
            # Prepare running parameters
            params = {"contexts": contexts}
            if running_extra_params:
                params.update(running_extra_params)
            logger.info(f"🔧 Running params: {params}")
            
            logger.info("\n🚀 Executing crew task")
            result = await run_crew_task(
                task_id=task.id,
                task_input=params,
                persistence_model=self.persistence_model
            )
            logger.info("✅ Crew task executed successfully")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in CrewAI task execution: {str(e)}"
            logger.error(error_msg)
            logger.info(f"❌ {error_msg}")
            return {
                "status": "failed",
                "error": error_msg,
                "response": error_msg
            }

    async def _run_tree_flow_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a Task Tree Flow task."""
        try:
            logger.info(f"\n🌳 Running Task Tree Flow task: {task.id}")
            
            # Check if tree flow exists
            if not task.tree_flow_id:
                raise ValueError(f"Task {task.id} has no associated tree flow")
                
            # Get contexts if needed
            query = running_extra_params.get("context_query") if running_extra_params else None
            logger.info(f"🔍 Getting contexts with query: {query}")
            contexts = await self.context_provider.get_contexts(query) if query else []
            logger.info(f"✅ Found {len(contexts)} contexts")
            
            # Prepare running parameters
            params = {"contexts": contexts}
            if running_extra_params:
                params.update(running_extra_params)
            logger.info(f"🔧 Running params: {params}")
            
            # Initialize tree flow manager
            from src.server.controllers.task_tree_flow import TaskTreeFlowManager
            tree_flow_manager = TaskTreeFlowManager(self, self.persistence_model)
            await tree_flow_manager.initialize()
            
            # Create from model and execute
            logger.info(f"\n🚀 Executing tree flow: {task.tree_flow_id}")
            tree_flow_manager.create_from_model(task.tree_flow_id)
            result = await tree_flow_manager.execute_tree(params)
            logger.info("✅ Tree flow executed successfully")
            
            # Format the result
            if isinstance(result, dict):
                response = "\n".join([f"{node_id}: {node_result}" for node_id, node_result in result.items()])
            else:
                response = str(result)
                
            return {
                "status": "completed",
                "response": response,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Error in Task Tree Flow execution: {str(e)}"
            logger.error(error_msg)
            logger.info(f"❌ {error_msg}")
            return {
                "status": "failed",
                "error": error_msg,
                "response": error_msg
            }

    def _get_or_create_curried_proxy(
        self,
        task: Task,
        tasksmanager: TasksManager
    ) -> CurriedProxy:
        """Get existing curried proxy or create new one with tools."""
        logger.info(f"\n🔍 Getting curried proxy for task: {task.id}")
        
        curried_proxy = None
        if task.curried_proxy_id:
            logger.info(f"🔄 Loading existing proxy with ID: {task.curried_proxy_id}")
            curried_proxy = self.persistence_model.curried_proxies.read(task.curried_proxy_id)
            if curried_proxy:
                logger.info("✅ Successfully loaded existing proxy")
            else:
                logger.info("⚠️ Failed to load existing proxy")
        
        if not curried_proxy:
            logger.info("🆕 Creating new curried proxy")
            curried_proxy = CurriedProxy()
            
        # Add tools from both tasksmanager and task
        tasksmanager_toolsets = getattr(tasksmanager, 'toolsets', []) or []
        task_toolsets = getattr(task, 'toolsets', []) or []
        
        logger.info(f"📦 Found {len(tasksmanager_toolsets)} manager toolsets and {len(task_toolsets)} task toolsets")
        
        # Add tools to proxy
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)
        
        # Log registered tools
        tools = curried_proxy.list_tools()
        logger.info(f"🛠️ Registered tools in proxy: {', '.join(tools) if tools else 'None'}")
                
        return curried_proxy

    def _add_tools_to_proxy(self, curried_proxy: CurriedProxy, toolset_ids: list) -> None:
        """Add tools from toolsets to curried proxy."""
        import re

        def sanitize_name(name: str) -> str:
            """Sanitize name to match pattern ^[a-zA-Z0-9_-]+$"""
            # Replace any character that isn't alphanumeric, hyphen, or underscore with underscore
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            # Ensure name starts with a letter or underscore
            if sanitized and sanitized[0].isdigit():
                sanitized = f"_{sanitized}"
            return sanitized

        for toolset_id in toolset_ids:
            toolset = self.persistence_model.toolsets.read(toolset_id)
            if toolset and toolset.tool_ids:
                for tool_id in toolset.tool_ids:
                    tool = self.persistence_model.tools.read(tool_id)
                    if tool:
                        # Sanitize the toolset name before concatenation
                        sanitized_toolset_name = sanitize_name(toolset.name)
                        tool_name = f"{sanitized_toolset_name}_{tool.function.name}"
                        curried_proxy.add_tool(tool_name, tool)

    async def completion(
        self, 
        tasksmanager_id: str, 
        task_id: str, 
        messages: List[Message], 
        model: Optional[str] = None,
        curried_proxy: Optional[CurriedProxy] = None
    ) -> str:
        """Execute a completion task."""
        return await self.operator.completion(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            messages=messages,
            model=model,
            curried_proxy=curried_proxy
        )

    async def run_sequential_tasks(
        self, 
        task_ids: List[str], 
        initial_context: Dict
    ) -> List[Dict]:
        """Run tasks in sequence, passing context forward"""
        responses = []
        current_context = initial_context.copy()
        
        for task_id in task_ids:
            task = self.persistence_model.tasks.read(task_id)
            node = TaskNode(task)
            
            response = await node.run(current_context)
            result = {
                "task_id": task_id,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            responses.append(result)
            current_context["previous_response"] = response
            
        return responses

    def wrap_task(self, task: Task) -> TaskExecutor:
        """Wrap a Task model in a TaskExecutor."""
        return TaskExecutor(task, self)

    async def run_flow(
        self,
        flow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a task flow with the given ID.
        
        Args:
            flow_id: The ID of the flow to execute
            initial_context: Optional initial context for the flow
            session_id: Optional session ID to use for the flow
            
        Returns:
            A dictionary with the flow results
        """
        try:
            logger.info(f"\n🚀 Running flow {flow_id}")
            
            # Get the flow from the persistence model
            from ..controllers.task_flow_manager import TaskFlowManager
            flow_manager = TaskFlowManager(self.persistence_model)
            await flow_manager.initialize()
            
            flow = flow_manager.get_flow(flow_id)
            if not flow:
                raise ValueError(f"Flow with ID {flow_id} not found")
                
            if session_id:
                flow.session_id = session_id
                
            context = initial_context.copy() if initial_context else {}
            context["flow_id"] = flow_id
            context["session_id"] = flow.session_id
            
            # Validate messages in context using helper method
            if 'messages' in context and isinstance(context['messages'], list):
                context['messages'] = self._validate_messages(context['messages'], "context")
            
            results = []
            
            for i, step in enumerate(flow.steps):
                try:
                    # Mark step as started
                    step.mark_started()
                    
                    # Get the task for this step
                    task = self.persistence_model.tasks.read(step.task_id)
                    
                    # Get the previous step result if available
                    previous_result = None
                    if i > 0:
                        previous_step = flow.steps[i - 1]
                        previous_result = previous_step.result
                    
                    # Prepare the context for this step
                    step_context = context.copy()
                    
                    # Apply transformer if available
                    if step.transformer and previous_result:
                        print(f"\n🔄 DEBUG - Applying transformer for step {i}: {step.name}")
                        print(f"  transformer type: {type(step.transformer)}")
                        print(f"  previous_result: {previous_result}")
                        
                        if isinstance(step.transformer, PromptTransformer):
                            print(f"  Applying PromptTransformer")
                            # Transform the prompt and create messages
                            messages = step.transformer.create_messages(previous_result, task)
                            print(f"  created messages count: {len(messages)}")
                            print(f"  created messages types: {[type(m) for m in messages]}")
                            # Validate transformer messages using helper method
                            step_context["messages"] = self._validate_messages(messages, "prompt transformer")
                        elif isinstance(step.transformer, MessageTransformer):
                            print(f"  Applying MessageTransformer")
                            # Get the previous task
                            previous_task = self.persistence_model.tasks.read(flow.steps[i - 1].task_id)
                            
                            # Transform messages between tasks
                            messages = step.transformer.transform(
                                previous_task,
                                task,
                                session_id=flow.session_id,
                                additional_content=step_context.get("additional_content")
                            )
                            print(f"  transformed messages count: {len(messages)}")
                            print(f"  transformed messages types: {[type(m) for m in messages]}")
                            # Validate transformer messages using helper method
                            step_context["messages"] = self._validate_messages(messages, "message transformer")
                    
                    # Call pre-execute hook if available
                    if step.pre_execute_hook:
                        hook_result = step.pre_execute_hook(step_context, previous_result, task)
                        if hook_result:
                            step_context.update(hook_result)
                            
                            # Validate hook messages using helper method
                            if 'messages' in hook_result and isinstance(hook_result['messages'], list):
                                step_context["messages"] = self._validate_messages(hook_result['messages'], "pre-execute hook")
                    
                    # Execute the task
                    result = await self.run_task(
                        tasksmanager_id=flow.tasksmanager_id,
                        task_id=step.task_id,
                        running_extra_params=step_context
                    )
                    
                    # Call post-execute hook if available
                    if step.post_execute_hook:
                        hook_result = step.post_execute_hook(result, step_context, task)
                        if hook_result:
                            result = hook_result
                    
                    # Mark step as completed
                    step.mark_completed(result)
                    
                    # Add result to results list
                    results.append({
                        "step_index": i,
                        "task_id": step.task_id,
                        "name": step.name or task.name,
                        "result": result,
                        "status": "completed"
                    })
                    
                    # Update context with this step's result
                    context[f"step_{i}_result"] = result
                    context["previous_result"] = result
                    
                except Exception as e:
                    error_msg = f"Flow step execution failed: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    
                    # Mark step as failed
                    step.mark_failed(str(e))
                    
                    # Add error to results list
                    results.append({
                        "step_index": i,
                        "task_id": step.task_id,
                        "name": step.name or "Unknown",
                        "error": str(e),
                        "status": "failed"
                    })
                    
                    # Stop execution if a step fails
                    break
            
            # Update the flow in the persistence model
            flow_manager.update_flow(flow)
            
            return {
                "flow_id": flow_id,
                "session_id": flow.session_id,
                "results": results,
                "completed": all(step.status == "completed" for step in flow.steps),
                "context": context
            }
            
        except Exception as e:
            error_msg = f"Flow execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "flow_id": flow_id,
                "error": error_msg,
                "completed": False,
                "results": []
            }

    def _validate_messages(self, messages: List[Any], source: str = "unknown") -> List[Message]:
        """
        Validate that all messages are Pydantic Message objects.
        
        Args:
            messages: List of messages to validate
            source: Source of the messages for error reporting
            
        Returns:
            List of validated Message objects
            
        Raises:
            TypeError: If any message is not a Pydantic Message object
        """
        print(f"\n🔍 DEBUG - _validate_messages called from source: {source}")
        print(f"  messages count: {len(messages) if messages else 0}")
        print(f"  messages type: {type(messages)}")
        
        validated_messages = []
        for i, msg in enumerate(messages):
            print(f"  message {i} type: {type(msg)}")
            print(f"  message {i} dir: {dir(msg) if hasattr(msg, '__dict__') else 'N/A'}")
            
            if isinstance(msg, Message):
                print(f"  ✅ message {i} is a valid Message object")
                validated_messages.append(msg)
            else:
                print(f"  ❌ message {i} is NOT a valid Message object")
                print(f"  message {i} content: {msg}")
                raise TypeError(f"Invalid message type from {source}: {type(msg)}. Only Pydantic Message objects are allowed.")
        
        print(f"  ✅ Validated {len(validated_messages)} messages successfully")
        return validated_messages