#!/usr/bin/env python3
"""
Comprehensive Fix for Concert Travel Planner

This script performs a complete fix for the Concert Travel Planner:
1. Checks for proper configuration in the state file
2. Regenerates the state if needed
3. Tests the concert planner tasks with CrewAI
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
from pathlib import Path

# Add the project root to the path
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def check_concert_config():
    """
    Check the concert travel planner state file for properly configured CrewAI tasks.
    """
    state_file = os.path.join(project_root, "state", "concert_travel_planner_state.json")
    
    if not os.path.exists(state_file):
        logger.error(f"State file not found: {state_file}")
        return False
    
    logger.info(f"Checking state file: {state_file}")
    
    try:
        # Load the state file
        with open(state_file, "r") as f:
            state_data = json.load(f)
        
        # Parse tasks
        tasks_str = state_data.get("tasks", "{}")
        tasks_data = json.loads(tasks_str)
        logger.info(f"Found {len(tasks_data)} tasks in state file")
        
        # Parse CrewAI configs
        crewai_config_str = state_data.get("crewai_config", "{}")
        crewai_configs = json.loads(crewai_config_str)
        logger.info(f"Found {len(crewai_configs)} CrewAI configurations in state file")
        
        config_ids = list(crewai_configs.keys())
        
        # Parse curried proxies
        curried_proxies_str = state_data.get("curried_proxies", "{}")
        curried_proxies = json.loads(curried_proxies_str)
        proxy_ids = list(curried_proxies.keys())
        
        # Check each task for CrewAI framework and config
        concert_tasks = []
        issue_found = False
        
        for task_id, task in tasks_data.items():
            task_name = task.get("name", "Unknown")
            
            # Check if this is a concert-related task
            is_concert_task = any(keyword in task_name.lower() for keyword in ["concert", "music", "festival"])
            
            if is_concert_task:
                concert_tasks.append(task)
                
                # Check framework
                framework = task.get("framework")
                if framework != "crewai":
                    logger.error(f"Task {task_name} has incorrect framework: {framework}")
                    issue_found = True
                
                # Check crewai_config_id
                config_id = task.get("crewai_config_id")
                if not config_id:
                    logger.error(f"Task {task_name} has no CrewAI config ID")
                    issue_found = True
                elif config_id not in config_ids:
                    logger.error(f"Task {task_name} has invalid CrewAI config ID: {config_id}")
                    issue_found = True
                
                # Check curried_proxy_id
                proxy_id = task.get("curried_proxy_id")
                if not proxy_id:
                    logger.error(f"Task {task_name} has no curried proxy ID")
                    issue_found = True
                elif proxy_id not in proxy_ids:
                    logger.error(f"Task {task_name} has invalid curried proxy ID: {proxy_id}")
                    issue_found = True
        
        if not concert_tasks:
            logger.error("No concert tasks found in state file")
            return False
        
        if issue_found:
            logger.error("Issues found in concert task configuration")
            return False
        
        logger.info("All concert tasks are properly configured")
        return True
        
    except Exception as e:
        logger.error(f"Error checking concert configuration: {str(e)}", exc_info=True)
        return False

async def repair_missing_config_ids():
    """
    Repair missing CrewAI config IDs in tasks.
    """
    state_file = os.path.join(project_root, "state", "concert_travel_planner_state.json")
    backup_file = f"{state_file}.bak"
    
    try:
        # Create a backup
        logger.info(f"Creating backup of state file: {backup_file}")
        with open(state_file, "r") as src:
            with open(backup_file, "w") as dst:
                dst.write(src.read())
        
        # Load the state file
        with open(state_file, "r") as f:
            state_data = json.load(f)
        
        # Parse tasks and CrewAI configs
        tasks_str = state_data.get("tasks", "{}")
        tasks_data = json.loads(tasks_str)
        
        crewai_config_str = state_data.get("crewai_config", "{}")
        crewai_configs = json.loads(crewai_config_str)
        
        if not crewai_configs:
            logger.error("No CrewAI configurations found in state file")
            return False
        
        # Get the first available CrewAI config ID
        first_config_id = list(crewai_configs.keys())[0]
        logger.info(f"Using CrewAI config ID: {first_config_id}")
        
        # Check each task and fix if necessary
        tasks_fixed = 0
        
        for task_id, task in tasks_data.items():
            task_name = task.get("name", "Unknown")
            is_concert_task = any(keyword in task_name.lower() for keyword in ["concert", "music", "festival"])
            
            if is_concert_task:
                # Check if the task is missing a config ID
                if not task.get("crewai_config_id") and task.get("framework") == "crewai":
                    logger.info(f"Fixing task {task_name} (ID: {task_id})")
                    tasks_data[task_id]["crewai_config_id"] = first_config_id
                    tasks_fixed += 1
        
        if tasks_fixed > 0:
            # Update the tasks in the state data
            state_data["tasks"] = json.dumps(tasks_data)
            
            # Save the updated state file
            with open(state_file, "w") as f:
                json.dump(state_data, f, indent=4)
            
            logger.info(f"Fixed {tasks_fixed} tasks with missing CrewAI config IDs")
            return True
        else:
            logger.info("No tasks needed repair")
            return True
        
    except Exception as e:
        logger.error(f"Error repairing state file: {str(e)}", exc_info=True)
        # Try to restore backup
        if os.path.exists(backup_file):
            logger.info("Restoring from backup")
            try:
                with open(backup_file, "r") as src:
                    with open(state_file, "w") as dst:
                        dst.write(src.read())
                logger.info("Backup restored successfully")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup: {str(restore_error)}")
        return False

async def regenerate_state():
    """
    Regenerate the concert travel planner state.
    """
    try:
        state_setup_script = os.path.join(project_root, "src", "state_setup", "concert_travel_planner.py")
        
        if not os.path.exists(state_setup_script):
            logger.error(f"State setup script not found: {state_setup_script}")
            return False
        
        logger.info(f"Running state setup script: {state_setup_script}")
        
        # Run the state setup script
        process = subprocess.Popen(
            [sys.executable, state_setup_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("State regeneration successful")
            logger.info(f"Output: {stdout.strip()}")
            return True
        else:
            logger.error(f"State regeneration failed with exit code {process.returncode}")
            logger.error(f"Error: {stderr.strip()}")
            return False
            
    except Exception as e:
        logger.error(f"Error regenerating state: {str(e)}", exc_info=True)
        return False

async def test_concert_task():
    """
    Test the concert travel planner task with CrewAI.
    """
    try:
        # Import required modules for task testing
        from src.server.controllers.task_runner import TaskRunner
        from src.server.persistence.persistence_model_factory import PersistenceModelFactory
        from src.server.models.message import Message
        from src.server.models.task import Task
        from src.server.models.tasks_manager import TasksManager
        from src.server.models.agent import CrewAIConfig
        from src.server.controllers.curried_proxy import CurriedProxy
        
        # Load the state file
        state_file = os.path.join(project_root, "state", "concert_travel_planner_state.json")
        
        with open(state_file, "r") as f:
            state_data = json.load(f)
        
        # Initialize persistence model
        persistence_model = PersistenceModelFactory().persistence_model()
        
        # Load state data
        tasks_str = state_data.get("tasks", "{}")
        tasks_data = json.loads(tasks_str)
        
        crewai_config_str = state_data.get("crewai_config", "{}")
        crewai_configs = json.loads(crewai_config_str)
        
        curried_proxies_str = state_data.get("curried_proxies", "{}")
        curried_proxies = json.loads(curried_proxies_str)
        
        tasksmanagers_str = state_data.get("tasksmanagers", "{}")
        tasksmanagers_data = json.loads(tasksmanagers_str)
        
        # Convert dictionaries to Pydantic models and load them into the persistence model
        logger.info("Creating task managers...")
        for manager_id, manager_dict in tasksmanagers_data.items():
            manager = TasksManager.parse_obj(manager_dict)
            persistence_model.tasksmanagers.create(manager)
            logger.info(f"Created task manager: {manager.name} (ID: {manager.id})")
        
        logger.info("Creating tasks...")
        for task_id, task_dict in tasks_data.items():
            task = Task.parse_obj(task_dict)
            persistence_model.tasks.create(task)
            logger.info(f"Created task: {task.name} (ID: {task.id})")
        
        logger.info("Creating CrewAI configs...")
        for config_id, config_dict in crewai_configs.items():
            config = CrewAIConfig.parse_obj(config_dict)
            persistence_model.crewai_config.create(config)
            logger.info(f"Created CrewAI config: {config.id}")
        
        logger.info("Creating curried proxies...")
        for proxy_id, proxy_dict in curried_proxies.items():
            proxy = CurriedProxy.parse_obj(proxy_dict)
            persistence_model.curried_proxies.create(proxy)
            logger.info(f"Created curried proxy: {proxy.id}")
        
        # Find a CrewAI concert task
        concert_tasks = []
        for task in persistence_model.tasks.list():
            if hasattr(task, "name"):
                task_name = task.name
                is_concert_task = any(keyword in task_name.lower() for keyword in ["concert", "music", "festival"])
                
                if (is_concert_task and 
                    hasattr(task, "framework") and task.framework == "crewai" and 
                    hasattr(task, "crewai_config_id") and task.crewai_config_id):
                    concert_tasks.append(task)
                    logger.info(f"Found CrewAI concert task: {task.name} (ID: {task.id})")
        
        if not concert_tasks:
            logger.error("No suitable concert tasks found for testing")
            return False
        
        # Use the first task for testing
        test_task = concert_tasks[0]
        logger.info(f"Testing task: {test_task.name} (ID: {test_task.id})")
        
        # Create a task runner
        task_runner = TaskRunner(persistence_model)
        
        # Create a test message
        test_message = Message(
            role="user",
            content="I'm looking for rock concerts in New York City next month. Can you help me find some options?"
        )
        
        # Run the task
        logger.info("Running the concert task...")
        result = await task_runner.run_task(test_task.id, test_message)
        
        # Check result
        if result and result.get("status") == "success":
            logger.info("Task execution successful!")
            response = result.get("response", "")
            logger.info(f"Response preview: {response[:200]}..." if len(response) > 200 else response)
            return True
        else:
            error = result.get("error") if result else "Unknown error"
            logger.error(f"Task execution failed: {error}")
            return False
        
    except Exception as e:
        logger.error(f"Error testing concert task: {str(e)}", exc_info=True)
        return False

async def fix_concert_planner():
    """
    Fix the concert travel planner by performing all necessary fixes.
    """
    logger.info("=== CONCERT TRAVEL PLANNER FIX SCRIPT ===")
    
    # Step 1: Check current configuration
    logger.info("\n== STEP 1: Checking current configuration ==")
    config_ok = check_concert_config()
    
    # Step 2: Repair or regenerate the state if needed
    if not config_ok:
        logger.info("\n== STEP 2: Attempting to repair state ==")
        repair_success = await repair_missing_config_ids()
        
        if not repair_success:
            logger.info("\n== STEP 3: Regenerating state ==")
            regen_success = await regenerate_state()
            if not regen_success:
                logger.error("Failed to fix the concert travel planner state")
                return False
        
        # Verify the fix
        config_ok = check_concert_config()
        if not config_ok:
            logger.error("State is still not properly configured after repair attempts")
            return False
    else:
        logger.info("State is already properly configured, skipping repair")
    
    # Step 3: Test a concert planner task
    logger.info("\n== STEP 4: Testing concert planner task ==")
    test_success = await test_concert_task()
    
    if test_success:
        logger.info("\n✅ Concert Travel Planner Fix Complete! ✅")
        return True
    else:
        logger.error("\n❌ Concert Travel Planner Fix Failed! ❌")
        logger.info("Troubleshooting tips:")
        logger.info("1. Check logs for specific errors")
        logger.info("2. Verify that CrewAI is properly installed")
        logger.info("3. Ensure all necessary credentials are available")
        logger.info("4. Check that the vector database is working")
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_concert_planner())
    sys.exit(0 if success else 1) 