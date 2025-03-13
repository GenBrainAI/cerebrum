import sys
from pathlib import Path
import asyncio
from datetime import datetime
from uuid import uuid4
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from server.models.persistence_models import StorageLocation, StorageType
from server.controllers.persistence_controller import save_to_storage
from typing import Optional
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

project_root = str(Path(__file__).parents[1])
sys.path.append(project_root)

def setup_test_tasks(persistence_model: Optional[InMemoryPersistenceModel] = None) -> InMemoryPersistenceModel:
    """Set up test tasks and task managers"""
    # Create persistence model if not provided
    if persistence_model is None:
        persistence_model = InMemoryPersistenceModel()
    
    # Create a task manager for testing
    task_manager = TasksManager(
        name="Demo Task Manager",
        model="gpt-4",
        description="A task manager for demonstration purposes",
        messages=[
            Message(role="system", content="You are a helpful assistant that manages tasks for demonstration purposes.")
        ]
    )
    
    task_manager = persistence_model.tasksmanagers.create(task_manager)
    print(f"✅ Created task manager: {task_manager.name} ({task_manager.id})")
    
    # Create some tasks
    tasks = [
        Task(
            name="Demo Task 1",
            tasksmanager_id=task_manager.id,
            model="gpt-4",
            description="A sample task for testing",
            messages=[
                Message(role="system", content="You are a task that helps with testing the task hierarchy view.")
            ],
            inherit_manager_context=False
        ),
        Task(
            name="Demo Task 2",
            tasksmanager_id=task_manager.id,
            model="claude-3-opus",
            description="Another sample task",
            messages=[
                Message(role="system", content="You are a Claude assistant that answers questions about task management.")
            ],
            inherit_manager_context=True
        )
    ]
    
    # Save tasks
    for task in tasks:
        created_task = persistence_model.tasks.create(task)
        print(f"✅ Created task: {created_task.name} ({created_task.id})")
    
    return persistence_model

if __name__ == "__main__":
    # Create and set up persistence model
    persistence_model = setup_test_tasks()
    
    # Print task managers and tasks
    task_managers = persistence_model.tasksmanagers.list()
    print(f"\nCreated {len(task_managers)} task managers:")
    for tm in task_managers:
        print(f"- {tm.name} ({tm.id})")
        tasks = [t for t in persistence_model.tasks.list() if t.tasksmanager_id == tm.id]
        for task in tasks:
            print(f"  - {task.name} ({task.id})")