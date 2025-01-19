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

async def setup_tasks_state():
    """Setup initial state for task management."""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create TasksManager for task management
    task_manager = TasksManager(
        name="Task Management System",
        model="gpt-4o-mini",
        description="Manages and organizes tasks within the system",
        messages=[
            Message(
                role="system",
                content="""You are a task management assistant. Your responsibilities include:
                1. Help organize and prioritize tasks
                2. Track task dependencies and relationships
                3. Provide status updates and progress tracking
                4. Assist with task scheduling and deadlines
                
                Format your responses clearly and include:
                - Task details and requirements
                - Priority level and deadlines
                - Dependencies and related tasks
                - Current status and progress"""
            ).dict()
        ]
    )
    task_manager = persistence_model.tasksmanagers.create(task_manager)
    
    # Create main task
    task = Task(
        name="Task Organization",
        description="Organize and manage system tasks",
        tasksmanager_id=task_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Help organize tasks by:
                1. Categorizing tasks by type and priority
                2. Identifying dependencies between tasks
                3. Tracking task progress and status
                4. Managing task deadlines and schedules
                5. Providing task summaries and reports"""
            ).dict()
        ]
    )
    task = persistence_model.tasks.create(task)
    
    # Save state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state/specialized",
        state_name="task_management_state.json"
    )
    
    result = save_to_storage(state_location)
    print(f"Task management state saved: {result}")
    
    return {
        "task_manager_id": task_manager.id,
        "task_id": task.id
    }

if __name__ == "__main__":
    asyncio.run(setup_tasks_state())