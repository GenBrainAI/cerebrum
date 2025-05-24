import asyncio
import json
import logging
import os # For environment variables
import sys

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Model and Controller Imports ---
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.task import Task # For type hinting if needed
from src.server.models.tasks_manager import TasksManager # For type hinting if needed

# Ensure the project root is in PYTHONPATH if running script directly
# For this tool, it's assumed PYTHONPATH is set in the execution environment.

async def main():
    logger.info("Starting Console Human Input Test for Concert Planner")

    # 1. Setup
    logger.info("Initializing InMemoryPersistenceModel and TaskRunner...")
    
    # Set OPENAI_API_KEY to a dummy value to satisfy client initializations
    # This is crucial as TaskRunner and its components might try to initialize LLM clients
    os.environ["OPENAI_API_KEY"] = "dummy_key_for_testing"
    # Similarly, for any other required API keys if they cause init failures.
    # Example: os.environ["ANTHROPIC_API_KEY"] = "dummy_key_for_testing" 
    #          os.environ["GOOGLE_API_KEY"] = "dummy_key_for_testing"


    persistence_model_factory = PersistenceModelFactory()
    PersistenceModelFactory.reset() # Ensure a clean factory state
    persistence_model = persistence_model_factory.persistence_model(type="inmemory")
    
    logger.info("Loading state from concert_travel_planner_state.json...")
    try:
        with open("state/concert_travel_planner_state.json", "r") as f:
            file_content_str = f.read() # Read as string
        # InMemoryPersistenceModel has from_json method
        persistence_model.from_json(file_content_str) 
        logger.info("State loaded successfully using from_json.")
    except FileNotFoundError:
        logger.error("state/concert_travel_planner_state.json not found. Please run src/state_setup/concert_travel_planner.py first.")
        return
    except json.JSONDecodeError as e: # from_json might still raise this if content is invalid
        logger.error(f"Error decoding JSON from state file: {e}")
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred during state loading: {e}", exc_info=True)
        return

    task_runner = TaskRunner(persistence_model=persistence_model)
    
    # Critical: Ensure Streamlit is NOT detected for this console test
    # Patch `sys.modules` to remove 'streamlit' if it was somehow imported by other parts.
    # Also patch the 'st' object within human_tools if it directly imports `streamlit as st`.
    if 'streamlit' in sys.modules:
        logger.info("Temporarily removing 'streamlit' from sys.modules for console test.")
        original_streamlit_module = sys.modules.pop('streamlit', None)
    else:
        original_streamlit_module = None
    
    # Patch 'src.server.tools.human_tools.st' to ensure it doesn't use a mock Streamlit object
    # that might respond as if in a Streamlit environment.
    try:
        from src.server.tools import human_tools
        original_st_in_human_tools = getattr(human_tools, 'st', None)
        human_tools.st = None 
        logger.info("Patched 'st' in human_tools to None for console test.")
    except ImportError:
        logger.warning("Could not import human_tools to patch 'st'. This might be okay if not used.")
        original_st_in_human_tools = None # To satisfy finally block

    try:
        await task_runner.initialize()
        logger.info("TaskRunner initialized.")

        # 2. Identify Task Dynamically
        logger.info("Attempting to find 'Concert Travel Planner' TasksManager and 'Plan Concert Trip' Task dynamically...")
        
        all_managers = persistence_model.tasksmanagers.list()
        concert_manager = None
        for mgr in all_managers:
            if mgr.name == "Concert Travel Planner":
                concert_manager = mgr
                break
        
        if not concert_manager:
            logger.error("Could not find 'Concert Travel Planner' TasksManager in loaded state.")
            return
        
        tasks_manager_id = concert_manager.id
        logger.info(f"Found TasksManager 'Concert Travel Planner' with ID: {tasks_manager_id}")

        all_tasks = persistence_model.tasks.list()
        task_to_run = None
        for task_obj in all_tasks:
            if task_obj.tasksmanager_id == tasks_manager_id and task_obj.name == "Plan Concert Trip":
                task_to_run = task_obj
                break
        
        if not task_to_run:
            logger.error(f"Task 'Plan Concert Trip' not found for manager ID {tasks_manager_id}.")
            return
            
        plan_concert_task_id = task_to_run.id
        logger.info(f"Found Task 'Plan Concert Trip' with ID: {plan_concert_task_id}")

        if not (hasattr(task_to_run, 'human_input') and task_to_run.human_input):
             logger.warning(f"Task {plan_concert_task_id} ('{task_to_run.name}') might not be configured for human input. human_input attribute: {getattr(task_to_run, 'human_input', 'Not Set')}")
        
        logger.info(f"Task '{task_to_run.name}' found. Human input expected: {task_to_run.human_input if hasattr(task_to_run, 'human_input') else 'Attribute not found'}")


        # 3. Execute Task
        logger.info("Calling task_runner.run_task for the 'Plan Concert Trip' task...")
        logger.info("Please provide input when prompted by the AI.")
        
        running_extra_params = {
            "prompt": "I want to plan a concert trip.", # This might be used by the CrewAI setup
            "messages": [ # More direct way to provide initial message for non-CrewAI tasks if run_task uses it
                {"role": "user", "content": "I want to plan a concert trip."}
            ]
        }
        
        # The test will pause here if console_run is invoked, waiting for user input.
        # The actual task execution will likely fail afterwards due to dummy API keys for LLM calls.
        task_result = await task_runner.run_task(
            tasks_manager_id, # Corrected variable name
            plan_concert_task_id, 
            running_extra_params=running_extra_params
        )

        logger.info(f"Task execution finished. Result: {task_result}")
        if task_result and task_result.get("status") == "failed":
            logger.info("Task failed as expected after human input (due to dummy API keys for LLM).")
        elif task_result:
            logger.warning(f"Task status was '{task_result.get('status')}', not 'failed'. This might indicate an issue if LLM calls were expected to fail.")
        else:
            logger.error("Task execution returned no result.")

    except Exception as e:
        logger.error(f"An error occurred during task execution: {e}", exc_info=True)
    finally:
        # Restore patched modules/objects
        if original_streamlit_module:
            sys.modules['streamlit'] = original_streamlit_module
            logger.info("Restored 'streamlit' in sys.modules.")
        if original_st_in_human_tools is not None and 'human_tools' in locals() : # Check if human_tools was imported
            human_tools.st = original_st_in_human_tools
            logger.info("Restored 'st' in human_tools.")


if __name__ == "__main__":
    # Ensure PYTHONPATH includes the project root for src imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    asyncio.run(main())
