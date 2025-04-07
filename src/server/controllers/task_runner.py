from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio
import uuid
import traceback
import copy
import time
from collections import defaultdict
import json
import re
import os
import inspect
import sys
import importlib
import aiohttp

from ..models.task import Task
from ..models.tasks_manager import TasksManager
from ..models.message import Message
from ..persistence.persistence_model import PersistenceModelBase
from ..controllers.prompt_transformer import PromptTransformer, MessageTransformer
from ..controllers.tools_operator import ToolsOperator
from ..controllers.operator import ToolsOperator as APIOperator
from ..controllers.curried_proxy import CurriedProxy
from ..controllers.crew_runner import run_crew_task
from ..controllers.task_sequence_controller import TaskSequenceController
from ..controllers.task_context import TaskContext
from ..persistence.persistence_model_factory import PersistenceModelFactory


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
                tasksmanager = self.task_runner.persistence_model.tasksmanagers.read(
                    self.task.tasksmanager_id)
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

    def __init__(self, persistence_model=None):
        """Initialize the Task Runner with optional persistence model."""

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize the PluginManager
        self.plugin_manager = None

        # Initialize the TaskContext
        self.task_context = None

        # Get or create persistence model
        if persistence_model:
            self.persistence_model = persistence_model
        else:
            self.persistence_model = PersistenceModelFactory().persistence_model()
        self.tools_operator = ToolsOperator()
        self.operator = APIOperator()
        self.observability_managers: Dict[str, TaskObservabilityManager] = {}
        self.context_provider = ContextProvider()
        self.context_provider.persistence_model = self.persistence_model
        self.context_analytics = ContextAnalytics()

        # Create task sequence controller
        self.sequence_controller = TaskSequenceController(self.persistence_model)
        self.sequence_controller.set_task_runner(self)

        self._active_observability_managers = {}
        self._active_tasks = set()  # Track currently running tasks
        self._task_locks = {}  # Locks for each task
        self._task_results = {}  # Store task results
        self._task_errors = {}  # Store task errors
        self._task_status = {}  # Store task status
        self._initialized = False

    async def initialize(self):
        """Initialize the task runner."""
        try:
            if not self._initialized:
                # Initialize the plugin manager
                if not self.plugin_manager:
                    self.plugin_manager = PluginManager()
                    self.logger.info("🔌 Initializing PluginManager")
                    self.logger.info("✅ PluginManager initialized")

                    # Load default plugins
                    self.logger.info("🔌 Loading default plugins...")

                    # Manual implementation of loading default plugins
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
                        success = await self.plugin_manager.load_plugin(
                            str(crewai_path),
                            crewai_config
                        )
                        if success:
                            self.logger.info("✅ CrewAI plugin loaded successfully")
                        else:
                            self.logger.error("❌ Failed to load CrewAI plugin")
                    else:
                        self.logger.warning("⚠️ CrewAI plugin file not found")

                    self._initialized = True
                    self.logger.info("✅ TaskRunner initialization complete")
            return True
        except Exception as e:
            error_msg = f"Failed to initialize TaskRunner: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def set_persistence_model(self, persistence_model: PersistenceModelBase):
        """Set a new persistence model for the task runner.

        This method allows switching the persistence model used by the task runner
        and ensures all dependent components are updated accordingly.

        Args:
            persistence_model: The new persistence model to use
        """
        try:
            logger.info(
                f"Switching task runner to use a different persistence model: {type(persistence_model).__name__}")

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
                    logger.warning(
                        "Attempting to rollback to previous persistence model")
                    self.persistence_model = old_persistence
                    if hasattr(self, 'context_provider') and self.context_provider:
                        self.context_provider.persistence_model = old_persistence
                    logger.info("Rollback successful")
                except BaseException:
                    logger.error(
                        "Rollback failed - task runner may be in an inconsistent state")

            return False

    async def _update_task_status(
            self,
            task: Task,
            status: str,
            error: Optional[str] = None):
        """Update task status and error message."""
        try:
            task.status = status
            task.error = error
            task.updated_at = datetime.now()
            self.persistence_model.tasks.update(task.id, task)

            # Update task status in memory
            self._task_status[task.id] = status

            # Store error if present
            if error:
                self._task_errors[task.id] = error

            # Log status change
            logger.info(f"Task {task.id} status updated to: {status}")
            if error:
                logger.error(f"Task error: {error}")

        except Exception as e:
            logger.error(f"❌ Failed to update task status: {str(e)}")

    def get_task_observability(
            self,
            task_id: str) -> Optional[TaskObservabilityManager]:
        """Get the observability manager for a task."""
        return self._active_observability_managers.get(task_id)

    def get_sequence_observability(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get observability data for a sequence execution."""
        try:
            # Get sequence data from persistence model
            sequence_data = self.persistence_model.sequence_executions.read(
                execution_id)
            if not sequence_data:
                return None

            # Get observability data for each task in the sequence
            task_observability = {}
            for task_id in sequence_data.task_ids:
                if task_id in self._active_observability_managers:
                    task_observability[task_id] = self._active_observability_managers[task_id].get_data(
                    )

            return {
                "execution_id": execution_id,
                "status": sequence_data.status,
                "task_observability": task_observability,
                "start_time": sequence_data.start_time,
                "end_time": sequence_data.end_time
            }
        except Exception as e:
            logger.error(f"Error getting sequence observability: {str(e)}")
            return None

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
        running_extra_params: Optional[Dict[str, Any]] = None,
        inside_sequence: bool = False
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

            # Extract user query from messages for context
            if running_extra_params and 'messages' in running_extra_params:
                messages = running_extra_params['messages']
                user_query = None
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        user_query = msg.get('content')
                        break
                    elif hasattr(msg, 'role') and msg.role == 'user':
                        user_query = msg.content
                        break

                if user_query:
                    logger.info(f"📝 Extracted user query: {user_query}")
                    if not running_extra_params:
                        running_extra_params = {}
                    running_extra_params['user_query'] = user_query

                    # Enhanced location detection
                    city = None
                    country = None

                    # First check for specific cities by name
                    if "Paris" in user_query:
                        logger.info(f"🌍 Direct match for city: Paris")
                        city = "Paris"
                        country = "France"
                    # Then try pattern matching for more general cases
                    else:
                        try:
                            import re
                            # Try multiple patterns to capture various ways of
                            # specifying location
                            location_patterns = [
                                # in Paris, France
                                r"(?:in|at|for)\s+([A-Za-z\s]+)(?:,\s*([A-Za-z\s]+))?",
                                # to Paris, France
                                r"(?:to|in)\s+([A-Za-z\s]+)(?:,\s*([A-Za-z\s]+))?",
                                # traveling to Paris
                                r"traveling to\s+([A-Za-z\s]+)(?:,\s*([A-Za-z\s]+))?",
                                # visiting Paris
                                r"visiting\s+([A-Za-z\s]+)(?:,\s*([A-Za-z\s]+))?",
                                # going to Paris
                                r"going to\s+([A-Za-z\s]+)(?:,\s*([A-Za-z\s]+))?"
                            ]

                            for pattern in location_patterns:
                                match = re.search(pattern, user_query, re.IGNORECASE)
                                if match:
                                    city = match.group(1).strip()
                                    country = match.group(
                                        2).strip() if match.group(2) else None
                                    logger.info(
                                        f"🌍 Pattern match for city: {city}, country: {country or 'None'}")

                                    # Add default country for known cities
                                    if not country:
                                        if city.lower() == "paris":
                                            country = "France"
                                        elif city.lower() == "london":
                                            country = "UK"
                                        elif city.lower() == "new york":
                                            country = "US"
                                    break
                        except Exception as e:
                            logger.error(
                                f"Error processing location from query: {str(e)}")

                    # Set location info in context if found
                    if city:
                        running_extra_params['city'] = city
                        if country:
                            running_extra_params['country'] = country
                        running_extra_params['location'] = {
                            'city': city,
                            'country': country
                        }
                        logger.info(
                            f"🌍 Added location to context: {city}, {country or 'Unknown'}")

                        # Also check for specific use case in data
                        if not hasattr(task, 'data'):
                            task.data = {}
                        task.data['location'] = {'city': city, 'country': country}
                        # Make sure this gets saved
                        self.persistence_model.tasks.update(task.id, task)

            # Only check for sequences if we're not already executing one
            if not inside_sequence:
                sequence_to_run = self._check_if_task_starts_sequence(manager, task_id)
                if sequence_to_run:
                    logger.info(
                        f"Task {task_id} is first in a sequence - delegating to sequence controller")
                    return await self.sequence_controller.execute_sequence(
                        tasksmanager_id=tasksmanager_id,
                        task_ids=sequence_to_run,
                        initial_context=running_extra_params
                    )

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
                    logger.info(
                        f"  ✅ Found task.crewai_config_id: {task.crewai_config_id}")
                else:
                    logger.error(
                        f"  ❌ CrewAI config not found task.crewai_config_id is None")

                # Check if this is a CrewAI task
                if (hasattr(task, 'crewai_config_id') and task.crewai_config_id) or (
                        hasattr(task, 'framework') and task.framework == "crewai"):
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

    def _check_if_task_starts_sequence(self,
                                       manager: TasksManager,
                                       task_id: str) -> Optional[List[str]]:
        """Check if a task is the start of a sequence."""
        try:
            # Check if manager has sequences defined
            if not hasattr(manager, 'sequences') or not manager.sequences:
                return None

            # Look for sequences that start with this task
            for sequence in manager.sequences:
                if sequence.task_ids and sequence.task_ids[0] == task_id:
                    return sequence.task_ids

            return None
        except Exception as e:
            logger.error(f"Error checking for task sequence: {str(e)}")
            return None

    async def _run_standard_task(
        self,
        task: Task,
        running_extra_params: Dict[str, Any],
        tasksmanager: Optional[TasksManager] = None
    ) -> Dict[str, Any]:
        """Run a standard task."""
        try:
            # Debug log task information
            logger.info(f"==== RUNNING STANDARD TASK: {task.name} ====")

            # Get the task manager if not provided
            if not tasksmanager and task.tasksmanager_id:
                tasksmanager = self.persistence_model.tasksmanagers.read(
                    task.tasksmanager_id)

            # Initialize context
            contexts = []

            # Extract messages from running_extra_params
            messages = running_extra_params.get('messages', [])
            logger.info(
                f"Initial message count from running_extra_params: {len(messages)}")

            # Debug - Examine initial messages
            for i, msg in enumerate(messages[:3]):  # Show first 3 messages only
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    logger.info(
                        f"Initial message [{i}] - {msg.role}: {msg.content[:100]}...")
                elif isinstance(msg, dict):
                    logger.info(
                        f"Initial message [{i}] - {msg.get('role')}: {msg.get('content', '')[:100]}...")

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
                        logger.debug(
                            f"Context {i+1}: Type={ctx.get('type')}, "
                            f"Source={ctx.get('source_id')}, "
                            f"Content preview: {ctx.get('content', '')[:50]}...")
                except Exception as e:
                    logger.error(f"❌ Error getting contexts: {str(e)}")
                    logger.exception(e)

            # Get the messages from running_extra_params
            messages = running_extra_params.get('messages', [])

            # If no messages provided, use the task messages
            if not messages and hasattr(task, 'messages') and task.messages:
                messages = task.messages.copy() if hasattr(
                    task.messages, 'copy') else task.messages[:]
                logger.info(f"Using task messages: {len(messages)} messages found")

            # DEBUG: Log messages before prepare_task_messages
            logger.info(f"Messages BEFORE prepare_task_messages: {len(messages)}")
            has_system_message = False
            for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                role = msg.role if hasattr(msg, 'role') else msg.get('role', 'unknown')
                content = msg.content if hasattr(
                    msg, 'content') else msg.get(
                    'content', '')
                logger.info(
                    f"Message before prepare [{i}]: {role} - {content[:100]}...")
                if role == "system":
                    has_system_message = True

            # Check for task messages and add them to the list
            if hasattr(task, 'messages') and task.messages and len(task.messages) > 0:
                logger.info(
                    f"Found {len(task.messages)} messages in task {task.name}, adding to messages list")

                # Create new list for combined messages
                combined_messages = []
                system_messages = []
                non_system_messages = []

                # First separate existing messages into system and non-system
                for msg in messages:
                    role = msg.role if hasattr(
                        msg, 'role') else msg.get(
                        'role', 'unknown')
                    if role == "system":
                        system_messages.append(msg)
                    else:
                        non_system_messages.append(msg)

                # Now process task messages
                task_system_messages = []
                task_non_system_messages = []

                for msg in task.messages:
                    role = msg.role if hasattr(
                        msg, 'role') else msg.get(
                        'role', 'unknown')
                    content = msg.content if hasattr(
                        msg, 'content') else msg.get(
                        'content', '')
                    logger.info(f"Task message: {role} - {content[:100]}...")

                    if role == "system":
                        task_system_messages.append(msg)
                    else:
                        task_non_system_messages.append(msg)

                # Combine all messages in the right order (system messages first)
                combined_messages = system_messages + task_system_messages + \
                    non_system_messages + task_non_system_messages

                if combined_messages:
                    messages = combined_messages
                    logger.info(
                        f"Combined messages list now has {len(messages)} messages")
                    has_system_message = has_system_message or len(
                        task_system_messages) > 0

            # Check for task or manager system prompt if no system message present
            system_prompt = None
            if not has_system_message:
                if hasattr(task, 'system_prompt') and task.system_prompt:
                    system_prompt = task.system_prompt
                    logger.info(f"Using task system prompt: {system_prompt[:100]}...")
                elif tasksmanager and hasattr(tasksmanager, 'system_prompt') and tasksmanager.system_prompt:
                    system_prompt = tasksmanager.system_prompt
                    logger.info(
                        f"Using tasksmanager system prompt: {system_prompt[:100]}...")

                # If system prompt found, add it to messages
                if system_prompt:
                    from ..models.message import Message
                    system_message = Message(role="system", content=system_prompt)
                    messages = [system_message] + messages
                    logger.info(
                        f"Added system prompt to messages. New count: {len(messages)}")

            # Prepare task messages with context
            messages = await self.context_provider.prepare_task_messages(task.id, messages)

            # DEBUG: Log messages after prepare_task_messages
            logger.info(f"Messages AFTER prepare_task_messages: {len(messages)}")
            for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                role = msg.role if hasattr(msg, 'role') else msg.get('role', 'unknown')
                content = msg.content if hasattr(
                    msg, 'content') else msg.get(
                    'content', '')
                logger.info(f"Message after prepare [{i}]: {role} - {content[:100]}...")

            # If still no system message, check if we have a system prompt in the task
            if not any((hasattr(msg, 'role') and msg.role == 'system') or
                       (isinstance(msg, dict) and msg.get('role') == 'system')
                       for msg in messages):
                logger.warning("No system message found after prepare_task_messages")

                # Add default system message if nothing else is available
                if not system_prompt:
                    logger.info("Using default system message")
                    from ..models.message import Message
                    default_system = Message(
                        role="system", content="You are a helpful assistant. Respond concisely and accurately.")
                    messages = [default_system] + messages

            # Get the curried proxy for tool access
            curried_proxy = self._get_or_create_curried_proxy(task, tasksmanager)

            # Call the completion method
            logger.info(
                f"🤖 Calling completion with model {model} and {len(messages)} messages")
            output = await self.completion(
                tasksmanager_id=task.tasksmanager_id,
                task_id=task.id,
                messages=messages,
                model=model,
                curried_proxy=curried_proxy
            )

            return {
                "task_id": task.id,
                "response": output,
                "task_name": task.name,
                "messages": messages,
                "model": model
            }
        except Exception as e:
            logger.error(f"Error in _run_standard_task: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

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
        manager: TasksManager,
        running_extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a CrewAI task."""
        try:
            logger.info(f"\n🤖 Running CrewAI task: {task.id}")

            # Check if crewai_config_id exists
            if not task.crewai_config_id:
                raise TaskExecutionError("CrewAI config ID not found in task")

            # Get CrewAI config
            crewai_config = self.persistence_model.crewai_config.read(
                task.crewai_config_id)
            if not crewai_config:
                raise TaskExecutionError(
                    f"CrewAI config not found with ID: {task.crewai_config_id}")

            # Get curried proxy
            curried_proxy = None
            if task.curried_proxy_id:
                curried_proxy = self.persistence_model.curried_proxies.read(
                    task.curried_proxy_id)
                if not curried_proxy:
                    raise TaskExecutionError(
                        f"Curried proxy not found with ID: {task.curried_proxy_id}")

            # Get the CrewAI plugin
            if not self.plugin_manager:
                await self.initialize()
            plugin = self.plugin_manager.get_plugin("crewai")
            if not plugin:
                raise TaskExecutionError("CrewAI plugin not found")

            # Prepare task input
            task_input = running_extra_params or {}

            # Run the task
            try:
                result = await plugin.run_task(
                    task=task,
                    curried_proxy=curried_proxy,
                    inputs=task_input,
                    persistence_model=self.persistence_model
                )
                return {
                    "status": "completed",
                    "response": result,
                    "error": None
                }
            except Exception as e:
                error_msg = f"CrewAI task execution failed: {str(e)}"
                logger.error(error_msg)
                logger.exception(e)
                return {
                    "status": "failed",
                    "error": error_msg,
                    "response": error_msg
                }

        except Exception as e:
            error_msg = f"Error in CrewAI task execution: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            return {
                "status": "failed",
                "error": error_msg,
                "response": error_msg
            }

    def _sanitize_crewai_input(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize input parameters for CrewAI tasks.

        Args:
            input_params: Dictionary of input parameters

        Returns:
            Sanitized parameters dictionary
        """
        sanitized = {}

        for key, value in input_params.items():
            # Handle messages specially
            if key == 'messages':
                sanitized[key] = self._validate_messages(value, "crewai input")
            else:
                # Sanitize other values
                sanitized[key] = self._sanitize_for_crewai(value)

        return sanitized

    def _get_contexts_for_task(self, task):
        """Get relevant contexts for a task."""
        try:
            # Get task description or query
            query = None
            if hasattr(task, 'description'):
                query = task.description
            elif hasattr(task, 'query'):
                query = task.query

            if not query:
                return []

            # Get contexts using context provider
            contexts = self.context_provider.get_contexts(query)

            # Add contexts to task
            for context in contexts:
                self.context_provider.add_context_to_task(
                    task_id=task.id,
                    type=context.get('type', 'unknown'),
                    source_id=context.get('source_id', 'unknown'),
                    metadata=context.get('metadata', {}),
                    priority=context.get('priority', 50)
                )

            return contexts

        except Exception as e:
            logger.error(f"Error getting contexts for task: {str(e)}")
            return []

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

            # Get the tree flow from persistence model
            tree_flow = self.persistence_model.task_tree_flows.read(task.tree_flow_id)
            if not tree_flow:
                raise ValueError(f"Tree flow {task.tree_flow_id} not found")

            # Get contexts if needed
            query = running_extra_params.get(
                "context_query") if running_extra_params else None
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
                response = "\n".join(
                    [f"{node_id}: {node_result}" for node_id, node_result in result.items()])
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
            curried_proxy = self.persistence_model.curried_proxies.read(
                task.curried_proxy_id)
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

        logger.info(
            f"📦 Found {len(tasksmanager_toolsets)} manager toolsets and {len(task_toolsets)} task toolsets")

        # Add tools to proxy
        self._add_tools_to_proxy(curried_proxy, tasksmanager_toolsets + task_toolsets)

        # Log registered tools
        tools = curried_proxy.list_tools()
        logger.info(
            f"🛠️ Registered tools in proxy: {', '.join(tools) if tools else 'None'}")

        return curried_proxy

    def _add_tools_to_proxy(
            self,
            curried_proxy: CurriedProxy,
            toolset_ids: list) -> None:
        """Add tools from toolsets to curried proxy."""
        import re

        def sanitize_name(name: str) -> str:
            """Sanitize name to match pattern ^[a-zA-Z0-9_-]+$"""
            # Replace any character that isn't alphanumeric, hyphen, or underscore
            # with underscore
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
        # Ensure all messages are proper Message objects
        validated_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                # Convert dict to Message object
                try:
                    validated_msg = Message(**msg)
                    validated_messages.append(validated_msg)
                except Exception as e:
                    logger.error(
                        f"❌ Error converting dict to Message: {str(e)}, dict: {msg}")
                    raise TaskExecutionError(f"Invalid message format: {str(e)}")
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                # It's already a Message-like object
                validated_messages.append(msg)
            else:
                logger.error(f"❌ Invalid message format: {type(msg)}, message: {msg}")
                raise TaskExecutionError(f"Invalid message format: {type(msg)}")

        # Log the conversion success
        logger.debug(f"✅ Validated {len(validated_messages)} messages for completion")

        return await self.operator.completion(
            tasksmanager_id=tasksmanager_id,
            task_id=task_id,
            messages=validated_messages,
            model=model,
            curried_proxy=curried_proxy
        )

    async def run_sequential_tasks(
        self,
        task_ids: List[str],
        initial_context: Dict
    ) -> List[Dict]:
        """Run tasks in sequence, passing context forward."""
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

    def trigger_state_save(self):
        """Trigger saving of the current state."""
        try:
            # Save task status
            for task_id, status in self._task_status.items():
                task = self.persistence_model.tasks.read(task_id)
                if task:
                    task.status = status
                    if task_id in self._task_errors:
                        task.error = self._task_errors[task_id]
                    self.persistence_model.tasks.update(task_id, task)

            # Save observability data
            for task_id, observability in self._active_observability_managers.items():
                data = observability.get_data()
                if data:
                    self.persistence_model.task_observability.create_or_update(
                        task_id, data)

            # Save sequence data if available
            if hasattr(self, 'sequence_controller'):
                self.sequence_controller.save_state()

            logger.info("✅ State saved successfully")

        except Exception as e:
            logger.error(f"❌ Error saving state: {str(e)}")

    def _validate_messages(
            self,
            messages: List[Any],
            source: str = "unknown") -> List[Message]:
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
        logger.debug(f"\n🔍 DEBUG - _validate_messages called from source: {source}")
        logger.debug(f"  messages count: {len(messages) if messages else 0}")
        logger.debug(f"  messages type: {type(messages)}")

        validated_messages = []
        for i, msg in enumerate(messages):
            logger.debug(f"  message {i} type: {type(msg)}")
            logger.debug(
                f"  message {i} dir: {dir(msg) if hasattr(msg, '__dict__') else 'N/A'}")

            if isinstance(msg, Message):
                logger.debug(f"  ✅ message {i} is a valid Message object")
                validated_messages.append(msg)
            else:
                logger.debug(f"  ❌ message {i} is NOT a valid Message object")
                logger.debug(f"  message {i} content: {msg}")
                raise TypeError(
                    f"Invalid message type from {source}: {type(msg)}. Only Pydantic Message objects are allowed.")

        logger.debug(f"  ✅ Validated {len(validated_messages)} messages successfully")
        return validated_messages

    async def run_task_sequence(
        self,
        tasksmanager_id: str,
        task_ids: List[str],
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a sequence of tasks in order.

        Args:
            tasksmanager_id: ID of the task manager
            task_ids: List of task IDs to execute in sequence
            initial_context: Optional initial context for the sequence

        Returns:
            Dictionary containing sequence results
        """
        try:
            logger.info(f"\n🔄 Running task sequence with {len(task_ids)} tasks")

            # Generate a unique sequence execution ID
            sequence_execution_id = str(uuid.uuid4())
            logger.info(f"  Sequence execution ID: {sequence_execution_id}")

            # Initialize sequence context
            sequence_context = initial_context.copy() if initial_context else {}
            sequence_context["sequence_execution_id"] = sequence_execution_id

            # Initialize sequence results
            results = []
            all_successful = True

            # Execute tasks in sequence
            for i, task_id in enumerate(task_ids):
                try:
                    logger.info(f"\n  Running task {i+1}/{len(task_ids)}: {task_id}")

                    # Add sequence position to context
                    task_context = sequence_context.copy()
                    task_context.update({
                        "sequence_position": i,
                        "is_first_task": i == 0,
                        "is_last_task": i == len(task_ids) - 1,
                        "previous_results": results
                    })

                    # Run the task
                    result = await self.run_task(
                        tasksmanager_id=tasksmanager_id,
                        task_id=task_id,
                        running_extra_params=task_context,
                        inside_sequence=True
                    )

                    # Add result to sequence results
                    task_result = {
                        "task_id": task_id,
                        "position": i,
                        "status": result.get("status", "unknown"),
                        "response": result.get("response", ""),
                        "error": result.get("error")
                    }
                    results.append(task_result)

                    # Update sequence context with this task's result
                    sequence_context[f"task_{i}_result"] = result
                    sequence_context["last_task_result"] = result

                    # Check if task failed
                    if result.get("status") == "failed":
                        all_successful = False
                        logger.error(
                            f"  ❌ Task {task_id} failed: {result.get('error')}")
                        break

                    logger.info(f"  ✅ Task {task_id} completed successfully")

                except Exception as e:
                    error_msg = f"Error executing task {task_id}: {str(e)}"
                    logger.error(f"  ❌ {error_msg}")
                    all_successful = False
                    results.append({
                        "task_id": task_id,
                        "position": i,
                        "status": "failed",
                        "error": error_msg,
                        "response": error_msg
                    })
                    break

            return {
                "sequence_execution_id": sequence_execution_id,
                "status": "completed" if all_successful else "failed",
                "results": results,
                "context": sequence_context
            }

        except Exception as e:
            error_msg = f"Sequence execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "failed",
                "error": error_msg,
                "results": []
            }

    async def run_task_sequence_by_id(
        self,
        tasksmanager_id: str,
        sequence_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        sequence_execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a task sequence by its ID.

        Args:
            tasksmanager_id: ID of the task manager
            sequence_id: ID of the sequence to run
            initial_context: Optional initial context
            sequence_execution_id: Optional execution ID for the sequence

        Returns:
            Dictionary containing sequence results
        """
        try:
            # Get the sequence from the persistence model
            sequence = self.persistence_model.task_sequences.read(sequence_id)
            if not sequence:
                raise ValueError(f"Sequence {sequence_id} not found")

            # Get the task IDs from the sequence
            task_ids = sequence.task_ids
            if not task_ids:
                raise ValueError(f"Sequence {sequence_id} has no tasks")

            # Run the sequence
            return await self.run_task_sequence(
                tasksmanager_id=tasksmanager_id,
                task_ids=task_ids,
                initial_context=initial_context
            )

        except Exception as e:
            error_msg = f"Failed to run sequence {sequence_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "failed",
                "error": error_msg,
                "results": []
            }

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
                context['messages'] = self._validate_messages(
                    context['messages'], "context")

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
                        print(
                            f"\n🔄 DEBUG - Applying transformer for step {i}: {step.name}")
                        print(f"  transformer type: {type(step.transformer)}")
                        print(f"  previous_result: {previous_result}")

                        if isinstance(step.transformer, PromptTransformer):
                            print(f"  Applying PromptTransformer")
                            # Transform the prompt and create messages
                            messages = step.transformer.create_messages(
                                previous_result, task)
                            print(f"  created messages count: {len(messages)}")
                            print(
                                f"  created messages types: {[type(m) for m in messages]}")
                            # Validate transformer messages using helper method
                            step_context["messages"] = self._validate_messages(
                                messages, "prompt transformer")
                        elif isinstance(step.transformer, MessageTransformer):
                            print(f"  Applying MessageTransformer")
                            # Get the previous task
                            previous_task = self.persistence_model.tasks.read(
                                flow.steps[i - 1].task_id)

                            # Transform messages between tasks
                            messages = step.transformer.transform(
                                previous_task,
                                task,
                                session_id=flow.session_id,
                                additional_content=step_context.get("additional_content")
                            )
                            print(f"  transformed messages count: {len(messages)}")
                            print(
                                f"  transformed messages types: {[type(m) for m in messages]}")
                            # Validate transformer messages using helper method
                            step_context["messages"] = self._validate_messages(
                                messages, "message transformer")

                    # Call pre-execute hook if available
                    if step.pre_execute_hook:
                        hook_result = step.pre_execute_hook(
                            step_context, previous_result, task)
                        if hook_result:
                            step_context.update(hook_result)

                            # Validate hook messages using helper method
                            if 'messages' in hook_result and isinstance(
                                    hook_result['messages'], list):
                                step_context["messages"] = self._validate_messages(
                                    hook_result['messages'], "pre-execute hook")

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
