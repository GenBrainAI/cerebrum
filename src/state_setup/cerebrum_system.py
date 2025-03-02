import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parents[2])  # Go up two levels to reach project root
sys.path.append(project_root)

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
import json

from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.tools_catalog import ToolsCatalog
from src.server.tools.internal_file_tools import InternalFileTools
from src.server.tools.internal_credentials_tools import InternalCredentialsTools
from src.server.tools.internal_testing_tools import InternalTestingTools
from src.server.tools.internal_proxy_tools import InternalProxyTools
from src.server.tools.url_tools import URLTools
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, ToolModel, TaskModel
from src.server.models.process import Process
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.controllers.agents_controller import CreateCrewRequest, AgentModel
from src.server.models.agent import ToolModel
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage, load_from_storage
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.context.context_provider import ContextProvider
from src.server.context.crew_context_enhancer import CrewContextEnhancer, CrewContextConfig
from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.context.adaptive_context_manager import ContextConfig
from src.server.system.terminal_command_executor import SecurityConfig
from src.server.system.codebase_vector_store import VectorStoreConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Disable Streamlit warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)

# Get the global instance
tools_catalog = ToolsCatalog()

def register_internal_tools():
    """Register internal tools with the tools catalog."""
    tools_catalog = ToolsCatalog()
    
    # Register internal tools
    internal_file_tools = InternalFileTools()
    tools_catalog.register_instance(internal_file_tools, "internal_file_tools")
    
    internal_credentials_tools = InternalCredentialsTools()
    tools_catalog.register_instance(internal_credentials_tools, "internal_credentials_tools")
    
    internal_testing_tools = InternalTestingTools()
    tools_catalog.register_instance(internal_testing_tools, "internal_testing_tools")
    
    internal_proxy_tools = InternalProxyTools()
    tools_catalog.register_instance(internal_proxy_tools, "internal_proxy_tools")
    
    # Register URL tools
    url_tools = URLTools()
    tools_catalog.register_instance(url_tools, "URLTools")
    
    logger.info("Registered internal tools with the tools catalog")

def save_persistence_state(persistence_model: InMemoryPersistenceModel, file_path: str) -> None:
    """Save the persistence state to a file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Serialize the persistence model
    serialized_state = persistence_model.serialize()
    
    # Save to file
    with open(file_path, 'w') as f:
        json.dump(serialized_state, f, indent=2)
    
    logger.info(f"Saved persistence state to {file_path}")

def load_persistence_state(persistence_model: InMemoryPersistenceModel, file_path: str) -> None:
    """Load the persistence state from a file."""
    if not os.path.exists(file_path):
        logger.warning(f"State file {file_path} does not exist")
        return
    
    # Load from file
    with open(file_path, 'r') as f:
        serialized_state = f.read()
    
    # Deserialize into the persistence model
    persistence_model.from_json(serialized_state)
    
    logger.info(f"Loaded persistence state from {file_path}")

async def add_system_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add system context to the task."""
    context_provider = ContextProvider()
    context_provider.persistence_model = persistence_model
    
    # Add system context
    await context_provider.add_system_context(
        task_id=task_id,
        name="System Overview",
        content="""
# Cerebrum System Core

The Cerebrum System Core provides a unified interface for interacting with the Cerebrum framework's core capabilities, including:

- Codebase understanding and navigation
- System access and command execution
- Context management and adaptation
- Integrated system operations

## Key Components

- **CerebrumSystemCore**: The central integration point that brings together all the components and provides a unified interface.
- **AdaptiveContextManager**: Manages context with dynamic compression and prioritization.
- **TerminalCommandExecutor**: Provides secure command validation and execution.
- **CodebaseVectorStore**: Enables semantic search of the codebase.
- **UnifiedContextManager**: Integrates the various context providers into a cohesive system.

## Usage Examples

### Searching the Codebase

```python
# Search for code related to context management
results = await core.search_code("context management")
for result in results:
    print(f"{result.file_path} (lines {result.start_line}-{result.end_line})")
    print(result.content)
```

### Executing Commands

```python
# Execute a command
result = await core.execute_command("ls -la")
if isinstance(result, str):
    print(f"Command submitted for approval. Approval ID: {result}")
else:
    print(f"Command output: {result.stdout}")
```

### Managing Context

```python
# Add information to the context
await core.add_to_context("Important information to remember", source="user", priority=80)

# Get the current context
context = await core.get_context(max_tokens=1000)
print(context)
```
""",
        description="Overview of the Cerebrum System Core capabilities",
        tags=["system", "overview"],
        priority=90
    )
    
    logger.info(f"Added system context to task {task_id}")

async def add_codebase_navigation_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add codebase navigation context to the task."""
    context_provider = ContextProvider()
    context_provider.persistence_model = persistence_model
    
    # Add codebase navigation context
    await context_provider.add_system_context(
        task_id=task_id,
        name="Codebase Navigation",
        content="""
# Codebase Navigation

The Cerebrum System Core provides powerful capabilities for navigating and understanding the codebase:

## Searching the Codebase

You can search the codebase for relevant code snippets:

```python
# Search for code related to a specific topic
results = await core.search_code("context management")
```

## Getting File Content

You can retrieve the content of specific files:

```python
# Get the content of a file
content = await core.get_file_content("src/server/context/adaptive_context_manager.py")
```

## Codebase Statistics

You can get statistics about the indexed codebase:

```python
# Get codebase statistics
stats = await core.get_codebase_stats()
print(f"Total Files: {stats.get('total_files', 0)}")
print(f"Total Lines: {stats.get('total_lines', 0)}")
```

## Refreshing the Codebase Index

You can refresh the codebase index to include new or modified files:

```python
# Refresh the codebase index
result = await core.refresh_codebase()
print(f"Indexed {result.get('indexed_files', 0)} files")
```
""",
        description="Guide for navigating and understanding the codebase",
        tags=["codebase", "navigation"],
        priority=85
    )
    
    logger.info(f"Added codebase navigation context to task {task_id}")

async def add_command_execution_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add command execution context to the task."""
    context_provider = ContextProvider()
    context_provider.persistence_model = persistence_model
    
    # Add command execution context
    await context_provider.add_system_context(
        task_id=task_id,
        name="Command Execution",
        content="""
# Command Execution

The Cerebrum System Core provides secure command execution capabilities:

## Executing Commands

You can execute terminal commands:

```python
# Execute a command
result = await core.execute_command("ls -la")
```

## Command Approval

Some commands may require approval before execution:

```python
# Execute a command that requires approval
result = await core.execute_command("rm -rf temp_dir", requires_approval=True)
if isinstance(result, str):
    print(f"Command submitted for approval. Approval ID: {result}")
```

## Approving Commands

You can approve pending commands:

```python
# Get pending approvals
approvals = await core.get_pending_approvals()

# Approve a command
result = await core.execute_approved_command(approval_id=approvals[0]["id"])
```

## Rejecting Commands

You can reject pending commands:

```python
# Reject a command
result = await core.reject_command(approval_id=approvals[0]["id"])
```
""",
        description="Guide for executing commands using the Cerebrum System Core",
        tags=["command", "execution"],
        priority=80
    )
    
    logger.info(f"Added command execution context to task {task_id}")

async def add_context_management_context(task_id: str, persistence_model: InMemoryPersistenceModel) -> None:
    """Add context management context to the task."""
    context_provider = ContextProvider()
    context_provider.persistence_model = persistence_model
    
    # Add context management context
    await context_provider.add_system_context(
        task_id=task_id,
        name="Context Management",
        content="""
# Context Management

The Cerebrum System Core provides powerful context management capabilities:

## Adding to Context

You can add information to the system context:

```python
# Add information to the context
await core.add_to_context(
    content="Important information to remember",
    source="user",
    priority=80,
    metadata={"key": "value"}
)
```

## Getting Context

You can retrieve the current system context:

```python
# Get the current context
context = await core.get_context(max_tokens=1000)
```

## Context with Metadata

You can include metadata in the context:

```python
# Get context with metadata
context = await core.get_context(include_metadata=True)
```
""",
        description="Guide for managing context using the Cerebrum System Core",
        tags=["context", "management"],
        priority=75
    )
    
    logger.info(f"Added context management context to task {task_id}")

def create_system_analyst_agent() -> AgentModel:
    """Create a system analyst agent."""
    agent = AgentModel(
        id=str(uuid.uuid4()),
        name="System Analyst",
        description="Expert in system analysis and codebase understanding",
        role="Analyzes the codebase and provides insights into system structure and behavior",
        goal="Provide comprehensive understanding of the codebase and system capabilities",
        backstory="""You are an expert system analyst with deep knowledge of software architecture and system design. 
        You have extensive experience in analyzing complex codebases and understanding how different components interact.
        Your expertise allows you to quickly navigate and understand the Cerebrum framework's codebase and provide
        valuable insights into its structure and behavior.""",
        allow_delegation=True,
        verbose=True,
        tools=[]
    )
    
    return agent

def create_system_operator_agent() -> AgentModel:
    """Create a system operator agent."""
    agent = AgentModel(
        id=str(uuid.uuid4()),
        name="System Operator",
        description="Expert in system operations and command execution",
        role="Executes commands and manages system operations",
        goal="Efficiently execute commands and manage system resources",
        backstory="""You are an experienced system operator with deep knowledge of command-line operations and system management.
        You have extensive experience in executing commands, managing system resources, and ensuring secure operations.
        Your expertise allows you to efficiently execute commands and manage system operations while maintaining security and stability.""",
        allow_delegation=True,
        verbose=True,
        tools=[]
    )
    
    return agent

async def setup_cerebrum_system_state(persistence_model: InMemoryPersistenceModel, state_file: str = "state/specialized/cerebrum_system_state.json") -> Dict[str, Any]:
    """Set up the Cerebrum System state."""
    # Register internal tools
    register_internal_tools()
    
    # Create a tasks manager
    tasks_manager = TasksManager(
        id=str(uuid.uuid4()),
        name="Cerebrum System Tasks",
        description="Tasks for the Cerebrum System Core",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    # Save the tasks manager to the persistence model
    persistence_model.tasksmanagers.create(tasks_manager)
    
    # Create a task for system operations
    system_operations_task = Task(
        id=str(uuid.uuid4()),
        name="System Operations",
        description="Perform system operations using the Cerebrum System Core",
        task_manager_id=tasks_manager.id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        task_type="crewai",
        status="not_started",
        metadata={
            "type": "system_operations",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Save the task to the persistence model
    persistence_model.tasks.create(system_operations_task)
    
    # Add context to the task
    await add_system_context(system_operations_task.id, persistence_model)
    await add_codebase_navigation_context(system_operations_task.id, persistence_model)
    await add_command_execution_context(system_operations_task.id, persistence_model)
    await add_context_management_context(system_operations_task.id, persistence_model)
    
    # Create a task for codebase analysis
    codebase_analysis_task = Task(
        id=str(uuid.uuid4()),
        name="Codebase Analysis",
        description="Analyze the codebase using the Cerebrum System Core",
        task_manager_id=tasks_manager.id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        task_type="crewai",
        status="not_started",
        metadata={
            "type": "codebase_analysis",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Save the task to the persistence model
    persistence_model.tasks.create(codebase_analysis_task)
    
    # Add context to the task
    await add_system_context(codebase_analysis_task.id, persistence_model)
    await add_codebase_navigation_context(codebase_analysis_task.id, persistence_model)
    
    # Create agents
    system_analyst_agent = create_system_analyst_agent()
    system_operator_agent = create_system_operator_agent()
    
    # Create a CrewAI configuration for the system operations task
    system_operations_crew_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        task_id=system_operations_task.id,
        create_crew=CreateCrewRequest(
            description="System Operations Crew",
            process=Process.sequential,
            agents=[system_operator_agent, system_analyst_agent],
            tasks=[
                TaskModel(
                    description="Perform system operations",
                    expected_output="System operations report",
                    agent_role="System Operator"
                )
            ]
        ),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    # Save the CrewAI configuration to the persistence model
    persistence_model.crewai_config.create(system_operations_crew_config)
    
    # Create a CrewAI configuration for the codebase analysis task
    codebase_analysis_crew_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        task_id=codebase_analysis_task.id,
        create_crew=CreateCrewRequest(
            description="Codebase Analysis Crew",
            process=Process.sequential,
            agents=[system_analyst_agent],
            tasks=[
                TaskModel(
                    description="Analyze the codebase",
                    expected_output="Codebase analysis report",
                    agent_role="System Analyst"
                )
            ]
        ),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    # Save the CrewAI configuration to the persistence model
    persistence_model.crewai_config.create(codebase_analysis_crew_config)
    
    # Create configuration for the Cerebrum System Core
    cerebrum_system_config = {
        "base_path": "persistent_state/cerebrum_system",
        "context": {
            "max_tokens": 8192,
            "default_model": "gpt-4",
            "enable_history": True,
            "history_limit": 10
        },
        "security": {
            "max_execution_time": 60,
            "max_output_size": 1048576,
            "blocked_commands": [
                "rm -rf /",
                "sudo",
                "chmod 777"
            ]
        },
        "vector_store": {
            "embedding_model": "text-embedding-ada-002",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "exclude_files": [
                "*.pyc",
                "*.git",
                "*.DS_Store"
            ]
        }
    }
    
    # Save the configuration to a file
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "cerebrum_system_config.json")
    with open(config_file, "w") as f:
        json.dump(cerebrum_system_config, f, indent=4)
    
    logger.info(f"Saved Cerebrum System configuration to {config_file}")
    
    # Save the state to a file
    state_dir = os.path.dirname(state_file)
    os.makedirs(state_dir, exist_ok=True)
    
    # Serialize the persistence model to JSON
    state_json = persistence_model.to_json()
    
    # Save the state to a file
    with open(state_file, "w") as f:
        f.write(state_json)
    
    logger.info(f"Saved Cerebrum System state to {state_file}")
    
    # Return information about the state
    return {
        "tasks_manager_id": tasks_manager.id,
        "system_operations_task_id": system_operations_task.id,
        "codebase_analysis_task_id": codebase_analysis_task.id,
        "state_file": state_file,
        "config_file": config_file
    }

async def main():
    """Main entry point for setting up the Cerebrum System state."""
    # Create a new persistence model
    persistence_model = InMemoryPersistenceModel()
    
    # Set up the Cerebrum System state
    state_info = await setup_cerebrum_system_state(persistence_model)
    
    # Print information about the created state
    logger.info(f"Created Cerebrum System state with {len(state_info['tasks'])} tasks")
    logger.info(f"State saved to {state_info['state_file']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 