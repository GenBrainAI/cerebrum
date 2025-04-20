#!/usr/bin/env python3
"""
Test script for human input functionality with CrewAI.
This script demonstrates human-in-the-loop functionality with a console interface.
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Ensure src is in the path so imports work correctly
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import necessary components
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.tools.human_tools import HumanInputTool, human_input_tool
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.models.message import Message
from src.server.models.tasks_manager import TasksManager
from src.server.models.agent import CrewAIConfig, CreateCrewRequest
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.curried_proxy_info import CurriedProxyInfo

# Override the HumanInputTool's _run method for console input
def console_run(self, question: str, **kwargs) -> str:
    """Console-based implementation of the human input tool."""
    print(f"\n🧠 AI is asking: {question}")
    print("Please provide your response:")
    user_input = input(">> ")
    print(f"Thank you! Your response: {user_input}")
    return user_input

def load_metadata() -> Dict[str, Any]:
    """Load metadata from the metadata.json file."""
    try:
        metadata_path = os.path.join(parent_dir, "state", "metadata.json")
        with open(metadata_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metadata: {str(e)}")
        raise

def load_state_data(state_file: str) -> str:
    """Load state data from the specified state file.
    
    Returns:
        The raw JSON string from the state file
    """
    try:
        state_path = os.path.join(parent_dir, state_file)
        with open(state_path, "r") as f:
            # Return the raw JSON string, not a parsed dictionary
            return f.read()
    except Exception as e:
        logger.error(f"Error loading state data: {str(e)}")
        raise

async def run_interactive_task(task_id: str) -> None:
    """Run an interactive task with human input."""
    try:
        # Load metadata and state
        logger.info("Loading metadata...")
        metadata = load_metadata()
        state_file = metadata.get("state_file")
        
        if not state_file:
            logger.error("No state file found in metadata")
            return
        
        logger.info(f"Loading state from {state_file}...")
        json_str = load_state_data(state_file)
        state_data = json.loads(json_str)
        
        # Initialize the persistence model
        logger.info("Initializing persistence model...")
        persistence_model = PersistenceModelFactory().persistence_model()
        
        # We need to handle loading the collections manually since from_json expects nested JSON strings
        logger.info("Loading state into persistence model...")
        
        # Process tasksmanagers
        if "tasksmanagers" in state_data:
            for tm_id, tm_data in state_data["tasksmanagers"].items():
                tm = TasksManager(**tm_data)
                persistence_model.tasksmanagers.create(tm)
                logger.info(f"Loaded task manager: {tm.name} (ID: {tm.id})")
        
        # Process tasks
        if "tasks" in state_data:
            for task_id, task_data in state_data["tasks"].items():
                task = Task(**task_data)
                persistence_model.tasks.create(task)
                logger.info(f"Loaded task: {task.name} (ID: {task.id})")
        
        # Process messages
        if "messages" in state_data and state_data["messages"]:
            for msg_id, msg_data in state_data["messages"].items():
                msg = Message(**msg_data)
                persistence_model.messages.create(msg)
        
        # Process crewai_config
        if "crewai_config" in state_data:
            for config_id, config_data in state_data["crewai_config"].items():
                config = CrewAIConfig(**config_data)
                persistence_model.crewai_config.create(config)
                logger.info(f"Loaded CrewAI config: {config.id}")
        
        # Process curried_proxies
        if "curried_proxies" in state_data and state_data["curried_proxies"]:
            for proxy_id, proxy_data in state_data["curried_proxies"].items():
                # Create proxy info
                proxy_info = CurriedProxyInfo(**proxy_data)
                proxy = CurriedProxy.from_info(proxy_info)
                persistence_model.curried_proxies.create(proxy)
                logger.info(f"Loaded curried proxy: {proxy.id}")
        
        # Find the task
        logger.info(f"Looking for task with ID: {task_id}")
        task = persistence_model.tasks.read(task_id)
        if not task:
            logger.error(f"Task with ID {task_id} not found")
            return
        
        logger.info(f"Found task: {task.name}")
        
        # Override the HumanInputTool's _run method for this session
        original_run = HumanInputTool._run
        HumanInputTool._run = console_run
        
        try:
            # Initialize TaskRunner with our persistence model
            task_runner = TaskRunner(persistence_model)
            await task_runner.initialize()
            
            # Run the task
            logger.info(f"Running task: {task.name}")
            tasksmanager_id = task.tasksmanager_id
            result = await task_runner.run_task(tasksmanager_id, task_id)
            
            # Display the result
            logger.info("Task completed successfully!")
            print("\n==== TASK RESULT ====")
            print(result.get("result", "No result provided"))
            print("=====================")
            
        finally:
            # Restore the original _run method
            HumanInputTool._run = original_run
            
    except Exception as e:
        logger.error(f"Error running interactive task: {str(e)}")
        import traceback
        traceback.print_exc()

def select_task() -> str:
    """Let the user select a task from the available tasks."""
    try:
        # Load metadata
        metadata = load_metadata()
        state_file = metadata.get("state_file")
        
        if not state_file:
            logger.error("No state file found in metadata")
            raise ValueError("No state file found in metadata")
        
        # Load state data as JSON string then parse for display only
        json_str = load_state_data(state_file)
        state_data = json.loads(json_str)
        
        # Get tasks from state data - the tasks field contains a JSON string, not a dictionary
        tasks_str = state_data.get("tasks", "{}")
        if isinstance(tasks_str, dict):
            tasks_data = tasks_str
        else:
            tasks_data = json.loads(tasks_str)
        
        # Convert tasks to a list for selection
        tasks = []
        for task_id, task_data in tasks_data.items():
            # Simple dict-to-Task conversion for display purposes
            task_name = task_data.get("name", "Unknown Task")
            task_description = task_data.get("description", "No description")
            tasks.append((task_id, task_name, task_description))
        
        if not tasks:
            logger.error("No tasks found in state data")
            raise ValueError("No tasks found in state data")
        
        # Display available tasks
        print("\nAvailable tasks:")
        for i, (task_id, task_name, task_description) in enumerate(tasks, 1):
            print(f"{i}. {task_name}: {task_description}")
        
        # Let the user select a task
        while True:
            try:
                choice = int(input("\nSelect a task by number: "))
                if 1 <= choice <= len(tasks):
                    selected_task = tasks[choice - 1]
                    print(f"Selected task: {selected_task[1]}")
                    return selected_task[0]  # Return the task ID
                else:
                    print(f"Please enter a number between 1 and {len(tasks)}")
            except ValueError:
                print("Please enter a valid number")
    
    except Exception as e:
        logger.error(f"Error selecting task: {str(e)}")
        raise

async def main():
    """Main entry point for the script."""
    try:
        print("=== Human Input Test for CrewAI ===")
        print("This script demonstrates human-in-the-loop functionality with a console interface.")
        
        # Select a task
        task_id = select_task()
        
        # Run the selected task
        await run_interactive_task(task_id)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 