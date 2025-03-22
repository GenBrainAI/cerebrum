import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import load_from_storage
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def run_crewai_task():
    """Run a CrewAI task from the concert_travel_planner_state.json file."""
    
    # Define the state file path
    state_file_path = os.path.join(project_root, "state", "concert_travel_planner_state.json")
    
    # Check if the state file exists
    if not os.path.exists(state_file_path):
        logger.error(f"State file not found: {state_file_path}")
        return
    
    logger.info(f"Loading state from: {state_file_path}")
    
    # Create a storage location
    location = StorageLocation(
        type=StorageType.file,
        location=os.path.dirname(state_file_path),
        state_name=os.path.basename(state_file_path)
    )
    
    # Reset the persistence model to start clean
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Load the state
    json_str = load_from_storage(location)
    state_data = json.loads(json_str)
    
    logger.info(f"Loaded state data keys: {list(state_data.keys())}")
    
    # Process each collection in the loaded data
    for collection_name in ['toolsets', 'tools', 'tasksmanagers', 'tasks', 
                            'messages', 'crewai_config', 'curried_proxies', 'task_flows']:
        if collection_name in state_data:
            if state_data[collection_name]:  # Only if there's data
                try:
                    raw_data = json.loads(state_data[collection_name])
                    if collection_name == 'tasksmanagers':
                        from src.server.models.tasks_manager import TasksManager
                        for tm_id, tm_data in raw_data.items():
                            persistence_model.tasksmanagers.create(TasksManager(**tm_data))
                    elif collection_name == 'tasks':
                        from src.server.models.task import Task
                        for task_id, task_data in raw_data.items():
                            # Debug print for task data
                            logger.info(f"Task data for {task_id}:")
                            logger.info(f"  crewai_config_id: {task_data.get('crewai_config_id')}")
                            persistence_model.tasks.create(Task(**task_data))
                    elif collection_name == 'crewai_config':
                        # Debug print for crewai_config data
                        logger.info(f"CrewAI config data:")
                        for config_id, config_data in raw_data.items():
                            logger.info(f"  Config ID: {config_id}")
                            # Create CrewAIConfig objects properly
                            from src.server.models.agent import CrewAIConfig
                            persistence_model.crewai_config.create(CrewAIConfig(**config_data))
                    else:
                        # For other collections, use collection method
                        collection = persistence_model.collection(collection_name)
                        for item_id, item_data in raw_data.items():
                            try:
                                collection.create(item_id, item_data)
                            except Exception as e:
                                logger.error(f"Error creating {collection_name} item {item_id}: {str(e)}")
                    logger.info(f"Loaded {collection_name}: {len(raw_data) if isinstance(raw_data, dict) else 'non-dict data'}")
                except Exception as e:
                    logger.error(f"Error loading {collection_name}: {str(e)}")
            else:
                logger.info(f"Empty {collection_name} in state data")
    
    # Verify loaded tasks with crewai_config_id
    logger.info("Verifying loaded tasks with crewai_config_id:")
    tasks = persistence_model.tasks.list()
    for task in tasks:
        if hasattr(task, 'crewai_config_id') and task.crewai_config_id:
            logger.info(f"Task {task.id} ({task.name}) has crewai_config_id: {task.crewai_config_id}")
            # Verify the config exists
            config = persistence_model.crewai_config.read(task.crewai_config_id)
            if config:
                logger.info(f"CrewAI config found: {config.id}")
            else:
                logger.error(f"CrewAI config NOT found for ID: {task.crewai_config_id}")
    
    # Get the task to run
    task_id = "2bc36c17-a529-4fcc-8f58-4c63d359dbc8"
    task = persistence_model.tasks.read(task_id)
    
    if not task:
        logger.error(f"Task not found with ID: {task_id}")
        return
    
    logger.info(f"Found task: {task.name} (ID: {task.id})")
    logger.info(f"Task crewai_config_id: {task.crewai_config_id}")
    
    # Get the task manager ID
    tasksmanager_id = task.tasksmanager_id
    logger.info(f"Task manager ID: {tasksmanager_id}")
    
    # Initialize TaskRunner
    task_runner = TaskRunner(persistence_model=persistence_model)
    await task_runner.initialize()
    
    # Run the task
    try:
        logger.info(f"Running task: {task.name} (ID: {task.id})")
        result = await task_runner.run_task(tasksmanager_id, task_id)
        logger.info(f"Task execution result: {result}")
    except Exception as e:
        logger.error(f"Error running task: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(run_crewai_task()) 