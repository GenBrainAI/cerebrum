#!/usr/bin/env python3
"""
Test script to run the Recommend Music Festivals task directly.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
import argparse
import traceback

# Ensure src is in the path
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Import necessary components
from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.message import Message
from src.server.tools.human_tools.human_tool import HumanInputTool, human_input_tool

async def run_task_async():
    try:
        logger.info("Starting task test...")
        
        # Configure human input tool for test mode with mock responses
        logger.info("Configuring HumanInputTool for test mode...")
        mock_responses = [
            "I'm interested in rock and electronic music festivals in Europe, specifically in Germany, Spain, and the UK.",
            "My budget is around 500 euros for tickets, and I can travel anytime between May and September 2025.",
            "I'd prefer festivals with camping options and good transportation links.",
            "Yes, that sounds great! I'm particularly interested in Primavera Sound in Barcelona."
        ]
        HumanInputTool.configure_test_mode(enable=True, mock_responses=mock_responses)
        logger.info("HumanInputTool configured for test mode with mock responses")
        
        # Initialize a dedicated persistence model (not using factory to avoid Streamlit conflicts)
        logger.info("Initializing persistence model...")
        persistence_model = InMemoryPersistenceModel()
        
        # Load state from file
        logger.info("Loading state from file...")
        state_file = "state/concert_travel_planner_state.json"
        
        logger.info("Loading state using from_json method...")
        try:
            with open(state_file, 'r') as f:
                json_str = f.read()
                persistence_model.from_json(json_str)
            logger.info("State loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load state: {str(e)}")
            logger.error(traceback.format_exc())
            return
        
        # Get task
        task_id = "a1fbedc4-f54b-41f4-90d5-8103bd8f53c0"  # The Recommend Music Festivals task
        logger.info(f"Getting task: {task_id}")
        
        task = persistence_model.tasks.read(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
            
        # Get tasksmanager
        tasksmanager_id = task.tasksmanager_id
        logger.info(f"Using tasksmanager: {tasksmanager_id}")
            
        # Initialize task runner
        logger.info("Initializing task runner...")
        task_runner = TaskRunner(persistence_model)
        await task_runner.initialize()
        
        # Prepare running_extra_params with the query
        running_extra_params = {
            "query": "I'm looking for popular music festivals in Europe 2025",
            "test_mode": True,  # Add flag to indicate we're running in test mode
            "mock_responses": [
                "I'm interested in rock and electronic music festivals in Europe, specifically in Germany, Spain, and the UK.",
                "My budget is around 500 euros for tickets, and I can travel anytime between May and September 2025.",
                "I'd prefer festivals with camping options and good transportation links.",
                "Yes, that sounds great! I'm particularly interested in Primavera Sound in Barcelona."
            ]
        }
        
        # Run task
        try:
            task_result = await task_runner.run_task(
                tasksmanager_id=tasksmanager_id,
                task_id=task_id,
                running_extra_params=running_extra_params
            )
            
            # Log result
            logger.info("Task completed successfully!")
            logger.info("\n=== TASK RESULT ===")
            
            # Handle different result types (string or dictionary)
            if isinstance(task_result, dict):
                logger.info(task_result.get("response", "No response"))
            else:
                # If task_result is a string, log it directly
                logger.info(str(task_result))
        except Exception as e:
            logger.error(f"Error running task: {str(e)}")
            logger.error(traceback.format_exc())
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Disable test mode when done
        HumanInputTool.configure_test_mode(enable=False)
        logger.info("Task test completed!")

def run_task():
    asyncio.run(run_task_async())

if __name__ == "__main__":
    run_task() 