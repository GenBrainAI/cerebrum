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

async def setup_tools_state():
    """Setup initial state for tools management."""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create TasksManager for tools management
    tools_manager = TasksManager(
        name="Tools Management System",
        model="gpt-4o-mini",
        description="Manages and catalogs system tools and their capabilities",
        messages=[
            Message(
                role="system",
                content="""You are a tools management assistant. Your responsibilities include:
                1. Maintain tool catalog and documentation
                2. Track tool dependencies and compatibility
                3. Manage tool versions and updates
                4. Assist with tool configuration
                
                For each tool, track:
                - Tool capabilities and requirements
                - Version information
                - Dependencies
                - Usage examples and documentation"""
            ).dict()
        ]
    )
    tools_manager = persistence_model.tasksmanagers.create(tools_manager)
    
    # Create main task
    task = Task(
        name="Tool Catalog Management",
        description="Manage and organize system tools catalog",
        tasksmanager_id=tools_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Manage the tools catalog by:
                1. Maintaining tool documentation
                2. Tracking tool versions and updates
                3. Managing tool dependencies
                4. Providing tool usage examples
                5. Ensuring tool compatibility"""
            ).dict()
        ]
    )
    task = persistence_model.tasks.create(task)
    
    # Save state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state/specialized",
        state_name="tools_management_state.json"
    )
    
    result = save_to_storage(state_location)
    print(f"Tools management state saved: {result}")
    
    return {
        "tools_manager_id": tools_manager.id,
        "task_id": task.id
    }

if __name__ == "__main__":
    asyncio.run(setup_tools_state())