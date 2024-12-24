import sys
from pathlib import Path
import asyncio
from datetime import datetime

project_root = str(Path(__file__).parents[1])
sys.path.append(project_root)

from server.persistence.persistence_model_factory import PersistenceModelFactory
from server.models.tasks_manager import TasksManager
from server.models.task import Task
from server.models.message import Message
from server.models.persistence_models import StorageLocation, StorageType
from server.controllers.persistence_controller import save_to_storage

async def setup_agentic_state():
    """Setup initial state for agentic framework management."""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create TasksManager for agentic framework
    agentic_manager = TasksManager(
        name="Agentic Framework Management",
        model="gpt-4o",
        description="Manages agentic framework configuration and behavior",
        messages=[
            Message(
                role="system",
                content="""You are an agentic framework manager. Your responsibilities include:
                1. Manage agent configurations and roles
                2. Coordinate agent interactions and workflows
                3. Monitor agent performance and behavior
                4. Optimize agent decision-making processes
                
                Track for each agent:
                - Role and responsibilities
                - Capabilities and limitations
                - Interaction patterns
                - Performance metrics"""
            ).dict()
        ]
    )
    agentic_manager = persistence_model.tasksmanagers.create(agentic_manager)
    
    # Create main task
    task = Task(
        name="Agent Framework Management",
        description="Manage and coordinate agentic framework",
        tasksmanager_id=agentic_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Manage the agentic framework by:
                1. Configuring agent roles and responsibilities
                2. Coordinating agent interactions
                3. Monitoring agent performance
                4. Optimizing agent workflows
                5. Maintaining agent documentation"""
            ).dict()
        ]
    )
    task = persistence_model.tasks.create(task)
    
    # Save state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state/specialized",
        state_name="agentic_framework_state.json"
    )
    
    result = save_to_storage(state_location)
    print(f"Agentic framework state saved: {result}")
    
    return {
        "agentic_manager_id": agentic_manager.id,
        "task_id": task.id
    }

if __name__ == "__main__":
    asyncio.run(setup_agentic_state())