#!/usr/bin/env python3
"""
Repair script for the Concert Travel Planner state file.
This script fixes the missing crewai_config_id in tasks.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

STATE_FILE_PATH = os.path.join(project_root, "state", "concert_travel_planner_state.json")

def repair_concert_planner_state():
    """Repair the concert travel planner state file by adding missing crewai_config_id to tasks."""
    logger.info(f"Starting repair of concert travel planner state")

    # Backup the existing state file
    backup_path = STATE_FILE_PATH + ".bak"
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            state_data = json.load(f)
            
        # Create backup
        with open(backup_path, 'w') as f:
            json.dump(state_data, f, indent=2)
        logger.info(f"Created backup of state file at {backup_path}")
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return False

    try:
        # Get the first crewai_config_id from the state
        crewai_config_id = None
        crewai_configs = json.loads(state_data.get("crewai_config", "{}"))
        
        if crewai_configs:
            # Get the first config ID
            for config_id in crewai_configs.keys():
                crewai_config_id = config_id
                logger.info(f"Found CrewAI config ID: {crewai_config_id}")
                break
                
        if not crewai_config_id:
            logger.error("No CrewAI config found in state file")
            return False
            
        # Parse tasks from the state
        tasks_str = state_data.get("tasks", "{}")
        tasks = json.loads(tasks_str)
        
        # Count tasks to fix
        tasks_to_fix = 0
        
        # Fix tasks with missing crewai_config_id
        for task_id, task in tasks.items():
            # Check if this task has framework='crewai' but missing crewai_config_id
            if task.get("framework") == "crewai" and not task.get("crewai_config_id"):
                tasks_to_fix += 1
                logger.info(f"Fixing task: {task.get('name')} (ID: {task_id})")
                
                # Add crewai_config_id
                task["crewai_config_id"] = crewai_config_id
                
                # Clear error status if it's about missing crewai_config_id
                if task.get("error") == "CrewAI configuration ID not found in task attributes":
                    task["status"] = "pending"
                    task["error"] = None
                    task["result"] = None
                    
                    # Clear execution logs with the same error
                    if "execution_logs" in task:
                        new_logs = []
                        for log in task["execution_logs"]:
                            if log.get("content") != "CrewAI configuration ID not found in task attributes":
                                new_logs.append(log)
                        task["execution_logs"] = new_logs
                
        # Update the state file with fixed tasks
        state_data["tasks"] = json.dumps(tasks)
        
        # Write the fixed state back to the file
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state_data, f, indent=2)
            
        logger.info(f"✅ Repair completed. Fixed {tasks_to_fix} tasks.")
        return True
    
    except Exception as e:
        logger.error(f"Error repairing state file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Attempt to restore backup
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            with open(STATE_FILE_PATH, 'w') as f:
                json.dump(backup_data, f, indent=2)
            logger.info("Restored backup after error")
        except Exception as restore_error:
            logger.error(f"Error restoring backup: {str(restore_error)}")
            
        return False

if __name__ == "__main__":
    logger.info("="*50)
    logger.info("CONCERT TRAVEL PLANNER STATE REPAIR TOOL")
    logger.info("="*50)
    
    success = repair_concert_planner_state()
    
    if success:
        logger.info("="*50)
        logger.info("✅ REPAIR COMPLETED SUCCESSFULLY")
        logger.info("="*50)
    else:
        logger.info("="*50)
        logger.info("❌ REPAIR FAILED")
        logger.info("="*50) 