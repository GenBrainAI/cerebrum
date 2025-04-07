#!/usr/bin/env python3
"""
Check Concert Travel Planner Configuration

This script checks the concert travel planner state file to verify that 
the tasks are properly configured with CrewAI framework and config IDs.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the path
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

# Import model classes for reference only - we don't need to instantiate them
# for basic validation
from src.server.models.task import Task

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
    # Determine project root
    state_file = os.path.join(project_root, "state", "concert_travel_planner_state.json")
    
    if not os.path.exists(state_file):
        logger.error(f"State file not found: {state_file}")
        return False
    
    logger.info(f"Loading state file: {state_file}")
    
    try:
        # Load the state file
        with open(state_file, "r") as f:
            state_data = json.load(f)
        
        # The state file has string-encoded JSON values, so we need to parse them
        
        # Parse tasks
        tasks_str = state_data.get("tasks", "{}")
        tasks_data = json.loads(tasks_str)
        logger.info(f"Found {len(tasks_data)} tasks in state file")
        
        # Parse CrewAI configs
        crewai_config_str = state_data.get("crewai_config", "{}")
        crewai_configs = json.loads(crewai_config_str)
        logger.info(f"Found {len(crewai_configs)} CrewAI configurations in state file")
        
        config_ids = list(crewai_configs.keys())
        logger.info(f"CrewAI config IDs: {config_ids}")
        
        # Parse curried proxies
        curried_proxies_str = state_data.get("curried_proxies", "{}")
        curried_proxies = json.loads(curried_proxies_str)
        logger.info(f"Found {len(curried_proxies)} curried proxies in state file")
        proxy_ids = list(curried_proxies.keys())
        logger.info(f"Curried proxy IDs: {proxy_ids}")
        
        # Check each task for CrewAI framework and config
        concert_tasks = []
        issue_found = False
        
        for task_id, task in tasks_data.items():
            task_name = task.get("name", "Unknown")
            
            # Check if this is a concert-related task
            is_concert_task = any(keyword in task_name.lower() for keyword in ["concert", "music", "festival"])
            
            if is_concert_task:
                concert_tasks.append(task)
                logger.info(f"Found concert task: {task_name} (ID: {task_id})")
                
                # Check framework
                framework = task.get("framework")
                logger.info(f"  Framework: {framework}")
                
                if framework != "crewai":
                    logger.error(f"  Task {task_name} has incorrect framework: {framework}")
                    issue_found = True
                
                # Check crewai_config_id
                config_id = task.get("crewai_config_id")
                logger.info(f"  CrewAI Config ID: {config_id}")
                
                if not config_id:
                    logger.error(f"  Task {task_name} has no CrewAI config ID")
                    issue_found = True
                elif config_id not in config_ids:
                    logger.error(f"  Task {task_name} has invalid CrewAI config ID: {config_id}")
                    issue_found = True
                
                # Check curried_proxy_id
                proxy_id = task.get("curried_proxy_id")
                logger.info(f"  Curried Proxy ID: {proxy_id}")
                
                if not proxy_id:
                    logger.error(f"  Task {task_name} has no curried proxy ID")
                    issue_found = True
                elif proxy_id not in proxy_ids:
                    logger.error(f"  Task {task_name} has invalid curried proxy ID: {proxy_id}")
                    issue_found = True
                
                # Display task structure for more information
                logger.info(f"  Task structure:")
                logger.info(f"  - messages: {len(task.get('messages', []))} messages")
                logger.info(f"  - status: {task.get('status', 'Not set')}")
        
        if not concert_tasks:
            logger.error("No concert tasks found in state file")
            return False
        
        if issue_found:
            logger.error("Issues found in concert task configuration")
            return False
        
        # Check CrewAI configuration
        for config_id, config in crewai_configs.items():
            if config_id in [task.get("crewai_config_id") for task in concert_tasks]:
                logger.info(f"Examining CrewAI config: {config_id}")
                
                create_crew = config.get("create_crew", {})
                agents = create_crew.get("agents", [])
                tasks = create_crew.get("tasks", [])
                process = create_crew.get("process")
                
                logger.info(f"  Process: {process}")
                logger.info(f"  Agents: {len(agents)}")
                for i, agent in enumerate(agents):
                    logger.info(f"    Agent {i+1}: {agent.get('role')}")
                
                logger.info(f"  Tasks: {len(tasks)}")
                for i, task in enumerate(tasks):
                    logger.info(f"    Task {i+1}: {task.get('description')}")
        
        logger.info("All concert tasks are properly configured")
        return True
        
    except Exception as e:
        logger.error(f"Error checking concert configuration: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    result = check_concert_config()
    logger.info(f"Configuration check {'succeeded' if result else 'failed'}")
    sys.exit(0 if result else 1) 