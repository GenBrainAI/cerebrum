from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio
import uuid

from ..models.task import Task, Message
from ..models.tasks_manager import TasksManager
from ..persistence.persistence_model import PersistenceModelBase
from ..controllers.prompt_transformer import PromptTransformer, MessageTransformer
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

class TaskRunner:
    """Runner for executing tasks."""

    def __init__(self, persistence_model: PersistenceModelBase):
        """Initialize TaskRunner with persistence model."""
        self.persistence_model = persistence_model
        self.tools_operator = ToolsOperator()
        self.operator = APIOperator()
        self.observability_managers: Dict[str, TaskObservabilityManager] = {}
        self.context_provider = ContextProvider()
        self.context_provider.persistence_model = persistence_model
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

    def set_persistence_model(self, persistence_model: PersistenceModelBase):
        """Set a new persistence model for the task runner.
        
        This method allows switching the persistence model used by the task runner
        and ensures all dependent components are updated accordingly.
        
        Args:
            persistence_model: The new persistence model to use
        """
        try:
            logger.info(f"Switching task runner to use a different persistence model: {type(persistence_model).__name__}")
            
            # Store the old persistence model in case we need to rollback
            old_persistence = self.persistence_model
            
            # Update the main persistence model
            self.persistence_model = persistence_model
            
            # Update the context provider with the new persistence model
            if hasattr(self, 'context_provider') and self.context_provider:
                logger.info("Updating context provider with new persistence model")
                self.context_provider.persistence_model = persistence_model
            
            # Update tools operator if it exists
            if hasattr(self, 'tools_operator') and self.tools_operator:
                logger.info("Updating tools operator with new persistence model")
                self.tools_operator.persistence_model = persistence_model
            
            # Update any other components that might depend on the persistence model
            # For plugins
            if hasattr(self, 'plugin_manager') and self.plugin_manager:
                logger.info("Notifying plugin manager of persistence model change")
                # If there's a way to update plugins, do it here
                if hasattr(self.plugin_manager, 'set_persistence_model'):
                    self.plugin_manager.set_persistence_model(persistence_model)
            
            # For CrewAI executor if present
            if hasattr(self, 'crewai_executor') and self.crewai_executor:
                logger.info("Updating CrewAI executor with new persistence model")
                if hasattr(self.crewai_executor, 'set_persistence_model'):
                    self.crewai_executor.set_persistence_model(persistence_model)
            
            # For Tree Flow executor if present
            if hasattr(self, 'tree_flow_executor') and self.tree_flow_executor:
                logger.info("Updating Tree Flow executor with new persistence model")
                if hasattr(self.tree_flow_executor, 'set_persistence_model'):
                    self.tree_flow_executor.set_persistence_model(persistence_model)
            
            logger.info("Successfully switched task runner to new persistence model")
            return True
            
        except Exception as e:
            logger.error(f"Error switching persistence model: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Try to rollback if possible
            if 'old_persistence' in locals():
                try:
                    logger.warning("Attempting to rollback to previous persistence model")
                    self.persistence_model = old_persistence
                    if hasattr(self, 'context_provider') and self.context_provider:
                        self.context_provider.persistence_model = old_persistence
                    logger.info("Rollback successful")
                except:
                    logger.error("Rollback failed - task runner may be in an inconsistent state")
            
            return False

    async def _update_task_status(self, task: Task, status: str, error: Optional[str] = None):
        """Update task status and error message."""
        try:
            task.status = status
            task.error = error
            task.updated_at = datetime.now()
            self.persistence_model.tasks.update(task.id, task)
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
                
                if task.crewai_config_id:
                    logger.info(f"  ✅ Found task.crewai_config_id: {task.crewai_config_id}")
                else:
                    logger.error(f"  ❌ CrewAI config not found task.crewai_config_id is None")

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
        """Run a standard task."""
        try:
            # Get the task manager if not provided
            if not tasksmanager and task.tasksmanager_id:
                tasksmanager = self.persistence_model.tasksmanagers.read(task.tasksmanager_id)
            
            # Initialize context
            contexts = []
            
            # Extract messages from running_extra_params
            messages = running_extra_params.get('messages', [])
            
            # Extract query from the last user message if available
            query = None
            
            # First check if context_query is directly provided in running_extra_params
            if running_extra_params and "context_query" in running_extra_params:
                query = running_extra_params["context_query"]
                logger.info(f"📝 Context query from running_extra_params: {query}")
            # Otherwise try to extract from the last user message
            elif messages:
                # Find the last user message
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        query = msg.get('content')
                        break
                    elif hasattr(msg, 'role') and msg.role == 'user':
                        query = msg.content
                        break
                logger.info(f"📝 Context query from last user message: {query}")
            else:
                logger.info("📝 No context query found")
            
            # Get model to use for context retrieval
            model = None
            if tasksmanager and hasattr(tasksmanager, 'model') and tasksmanager.model:
                model = tasksmanager.model
            elif hasattr(task, 'model') and task.model:
                model = task.model
            else:
                model = "gpt-4o-mini"  # Default model
                
            logger.info(f"🤖 Using model {model} for context retrieval")
            
            # Get message history for token calculation
            message_history = []
            if messages:
                for msg in messages:
                    if isinstance(msg, dict):
                        message_history.append(msg)
                    elif hasattr(msg, 'to_dict'):
                        message_history.append(msg.to_dict())
                    elif hasattr(msg, '__dict__'):
                        message_history.append(msg.__dict__)
            
            # Get contexts if we have a query
            if query:
                try:
                    # Use the context provider that's already set on the TaskRunner
                    self.context_provider.persistence_model = self.persistence_model
                    contexts = await self.context_provider.get_contexts(
                        query=query,
                        task_id=task.id,
                        model=model,
                        message_history=message_history
                    )
                    logger.info(f"📚 Found {len(contexts)} contexts for query")
                    
                    # Log context details for debugging
                    for i, ctx in enumerate(contexts):
                        logger.debug(f"Context {i+1}: Type={ctx.get('type')}, "
                                    f"Source={ctx.get('source_id')}, "
                                    f"Content preview: {ctx.get('content', '')[:50]}...")
                except Exception as e:
                    logger.error(f"❌ Error getting contexts: {str(e)}")
                    logger.exception(e)
            
            # Get the messages from running_extra_params
            messages = running_extra_params.get('messages', [])
            
            # If no messages provided, use the task messages
            if not messages and hasattr(task, 'messages') and task.messages:
                messages = task.messages
            
            # Prepare the messages with context
            if contexts:
                # Use the context provider that's already set on the TaskRunner
                self.context_provider.persistence_model = self.persistence_model
                
                # Add contexts to task
                for context in contexts:
                    await self.context_provider.add_context_to_task(
                        task_id=task.id,
                        type=context.get('type', 'unknown'),
                        source_id=context.get('source_id', 'unknown'),
                        metadata={
                            'content': context.get('content', ''),
                            **context.get('metadata', {})
                        },
                        priority=context.get('priority', 50)
                    )
                
                # Prepare messages with context
                messages = await self.context_provider.prepare_task_messages(task.id, messages)
            
            # Get the model to use
            model = None
            if tasksmanager and hasattr(tasksmanager, 'model') and tasksmanager.model:
                model = tasksmanager.model
            elif hasattr(task, 'model') and task.model:
                model = task.model
            
            # Get the system prompt
            system_prompt = None
            if hasattr(task, 'system_prompt') and task.system_prompt:
                system_prompt = task.system_prompt
            elif tasksmanager and hasattr(tasksmanager, 'system_prompt') and tasksmanager.system_prompt:
                system_prompt = tasksmanager.system_prompt
            
            # Add system prompt if available and not already in messages
            if system_prompt:
                has_system_message = False
                for msg in messages:
                    if (isinstance(msg, dict) and msg.get('role') == 'system') or \
                       (hasattr(msg, 'role') and msg.role == 'system'):
                        has_system_message = True
                        break
                
                if not has_system_message:
                    system_message = Message(role="system", content=system_prompt)
                    messages = [system_message] + messages
            
            # Get the curried proxy
            curried_proxy = None
            if tasksmanager:
                curried_proxy = self._get_or_create_curried_proxy(task, tasksmanager)
            
            # Run the completion
            response = await self.completion(
                tasksmanager_id=task.tasksmanager_id,
                task_id=task.id,
                messages=messages,
                model=model,
                curried_proxy=curried_proxy
            )
            
            # Update the task with the response
            task.last_response = response
            task.updated_at = datetime.now()
            self.persistence_model.tasks.update(task.id, task)
            
            return {
                "response": response,
                "task": task.to_dict() if hasattr(task, 'to_dict') else task
            }
        except Exception as e:
            logger.error(f"❌ Error running standard task: {str(e)}")
            logger.exception(e)
            raise TaskExecutionError(f"Failed to run standard task: {str(e)}")

    def _sanitize_for_crewai(self, data):
        """
        Recursively sanitize data for CrewAI by converting datetime objects to strings
        and ensuring all data is of supported types (str, int, float, bool, dict, list).
        
        Args:
            data: The data to sanitize
            
        Returns:
            Sanitized data safe for CrewAI
        """
        import datetime
        
        if isinstance(data, dict):
            return {k: self._sanitize_for_crewai(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_crewai(item) for item in data]
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return str(data)
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            # Convert any other types to strings
            return str(data)

    async def _run_crewai_task(
        self,
        task: Task,
        tasksmanager: TasksManager,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task."""
        try:
            logger.info(f"\n🤖 Running CrewAI task: {task.id}")
            
            # Debug prints for task attributes
            logger.info(f"\n🔍 DEBUG - CrewAI Task Details:")
            logger.info(f"  Task ID: {task.id}")
            logger.info(f"  Task Name: {task.name}")
            logger.info(f"  Task crewai_config_id: {task.crewai_config_id}")
            logger.info(f"  Task dict: {task.dict() if hasattr(task, 'dict') else task.__dict__}")
            
            # Initialize context
            contexts = []
            
            # Extract messages from running_extra_params
            messages = running_extra_params.get('messages', []) if running_extra_params else []
            
            # Extract query from the last user message if available
            query = None
            
            # First check if there's a crewai_task with a context field
            if running_extra_params and "crewai_task" in running_extra_params:
                crewai_task = running_extra_params["crewai_task"]
                if isinstance(crewai_task, dict) and "context" in crewai_task:
                    query = crewai_task["context"]
                    logger.info(f"📝 Context query from crewai_task: {query}")
            
            # If no query from crewai_task, try to extract from messages
            if not query and messages:
                # Find the last user message
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        query = msg.get('content')
                        break
                    elif hasattr(msg, 'role') and msg.role == 'user':
                        query = msg.content
                        break
                logger.info(f"📝 Context query from last user message: {query}")
            
            # Get message history for token calculation
            message_history = []
            if messages:
                for msg in messages:
                    if isinstance(msg, dict):
                        message_history.append(msg)
                    elif hasattr(msg, 'to_dict'):
                        message_history.append(msg.to_dict())
                    elif hasattr(msg, '__dict__'):
                        message_history.append(msg.__dict__)
            
            # Get contexts if we have a query
            if query:
                try:
                    # Get model from tasksmanager
                    model = tasksmanager.model if hasattr(tasksmanager, 'model') and tasksmanager.model else "gpt-4"
                    
                    logger.info(f"🤖 Using model {model} for context retrieval")
                    
                    # Get contexts with intelligent token management
                    self.context_provider.persistence_model = self.persistence_model
                    contexts = await self.context_provider.get_contexts(
                        query=query,
                        model=model,
                        task_id=task.id,
                        message_history=message_history
                    )
                    
                    logger.info(f"📚 Found {len(contexts)} contexts for query")
                    # Log context details for debugging
                    for i, ctx in enumerate(contexts):
                        content_preview = ctx.get("content", "")[:100] + "..." if len(ctx.get("content", "")) > 100 else ctx.get("content", "")
                        logger.debug(f"Context {i+1}: Type={ctx.get('type', 'unknown')}, Source={ctx.get('source_id', 'unknown')}")
                        logger.debug(f"Content preview: {content_preview}")
                except Exception as e:
                    logger.error(f"❌ Error getting contexts: {str(e)}")
                    logger.exception(e)
                    contexts = []
            
            # Prepare task input parameters
            task_input = {"contexts": contexts}
            if running_extra_params:
                task_input.update(running_extra_params)
            
            # Sanitize task input to ensure all data is compatible with CrewAI
            sanitized_task_input = self._sanitize_for_crewai(task_input)
            
            logger.info(f"🔧 Task input parameters sanitized for CrewAI")
            
            # DIRECT CALL TO run_crew_task instead of using plugin system
            from ..controllers.crew_runner import run_crew_task
            
            logger.info(f"\n🚀 Executing crew task via direct call to run_crew_task")
            result = await run_crew_task(
                task_id=task.id,
                task_input=sanitized_task_input,
                persistence_model=self.persistence_model
            )
            logger.info(f"✅ Crew task executed successfully: {result}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in CrewAI task execution: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
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

    async def run_task_sequence(
        self,
        tasksmanager_id: str,
        task_ids: List[str],
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a sequence of tasks with handover between them.
        
        Args:
            tasksmanager_id: ID of the task manager
            task_ids: List of task IDs to execute in sequence
            initial_context: Optional initial context to provide to the first task
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        logger.info(f"\n🔄 Running task sequence with {len(task_ids)} tasks")
        
        # Initialize results and task outputs storage
        results = {}
        task_outputs = {}
        
        # Initialize context from input
        context = initial_context.copy() if initial_context else {}
        
        # Execute tasks in sequence
        for task_id in task_ids:
            try:
                # Get task
                task = self.persistence_model.tasks.read(task_id)
                if not task:
                    raise ValueError(f"Task {task_id} not found")
                    
                logger.info(f"📋 Processing task: {task.name} (ID: {task_id})")
                
                # Check if this task takes input from previous tasks
                if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
                    # Gather inputs from dependency tasks
                    task_inputs = {}
                    for input_task_id in task.input_from_tasks:
                        if input_task_id in task_outputs:
                            logger.info(f"  ↳ Using output from task {input_task_id}")
                            task_inputs[input_task_id] = task_outputs[input_task_id]
                        else:
                            logger.warning(f"  ⚠️ Input task {input_task_id} not in outputs, skipping")
                    
                    # Add inputs to task's input_data
                    if not hasattr(task, 'input_data') or task.input_data is None:
                        task.input_data = {}
                    
                    # Add previous task outputs to input_data
                    if task_inputs:
                        task.input_data["previous_task_outputs"] = task_inputs
                        logger.info(f"  ↳ Added {len(task_inputs)} inputs to task input_data")
                        
                        # Update task in persistence model
                        self.persistence_model.tasks.update(task_id, task)
                
                # Prepare context for this specific task execution
                task_context = context.copy()
                if hasattr(task, 'input_data') and task.input_data:
                    # Add task's input_data to context
                    task_context.update(task.input_data)
                
                # Run the task
                logger.info(f"🚀 Executing task: {task.name}")
                result = await self.run_task(
                    tasksmanager_id=tasksmanager_id,
                    task_id=task_id,
                    running_extra_params=task_context
                )
                
                # Store result
                results[task_id] = result
                
                # Extract the actual result content
                result_content = result
                if isinstance(result, dict) and "response" in result:
                    result_content = result["response"]
                
                # Update task's output_data
                if not hasattr(task, 'output_data') or task.output_data is None:
                    task.output_data = {}
                    
                task.output_data["result"] = result_content
                task.output_data["timestamp"] = datetime.now().isoformat()
                
                # Store output for potential dependent tasks
                task_outputs[task_id] = result_content
                
                # Update task in persistence model
                task.status = "completed"
                self.persistence_model.tasks.update(task_id, task)
                
                logger.info(f"✅ Task {task.name} completed successfully")
                
            except Exception as e:
                error_msg = f"Error executing task {task_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                
                # Update task status to failed
                try:
                    task = self.persistence_model.tasks.read(task_id)
                    if task:
                        task.status = "failed"
                        task.error = error_msg
                        self.persistence_model.tasks.update(task_id, task)
                except Exception as update_err:
                    logger.error(f"Failed to update task status: {str(update_err)}")
                
                # Store error in results
                results[task_id] = {"error": error_msg, "status": "failed"}
                
                # Continue with next task or break depending on requirements
                # Here we continue with the next task, but this could be configurable
        
        return results

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