#!/usr/bin/env python3
"""
Test script for the Concert Travel Planner task with CrewAI
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
import traceback
from pydantic import BaseModel, Field

# Add the project root to the path
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

from src.server.controllers.task_runner import TaskRunner
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.message import Message
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.agent import CrewAIConfig
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.curried_proxy_info import CurriedProxyInfo
from src.server.tools.tools_catalog import tools_catalog  # Import the global catalog
from crewai_tools import SerperDevTool # <<< ADD THIS IMPORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Define the schema for the mock search tool
class MockSearchToolInput(BaseModel):
    search_query: str = Field(..., description="The search query string.")

# Mock Tool Implementation
class MockSearchTool:
    mock_tool_name: str = "Mock Search Tool"
    description: str = "A mock tool for testing search functionality."
    args_schema: type[BaseModel] = MockSearchToolInput # Assign the explicit schema

    def __init__(self, name="Default Mock Search"):
        self.mock_tool_name = name

    def run(self, search_query: str):
        # Simulate API call or processing
        print(f"\n MOCK TOOL RUNNING ")
        print(f" MockSearchTool '{self.mock_tool_name}' received query: {search_query}")
        return f"Mock results for '{search_query}'"

async def test_concert_task():
    """Async implementation of the concert task test."""
    try:
        # Path to the state file
        state_file_path = os.path.join(project_root, "state", "concert_travel_planner_state.json")
        
        # Check if the state file exists
        if not os.path.exists(state_file_path):
            logging.error(f"State file not found: {state_file_path}")
            return False
        
        logging.info(f"Loading state file: {state_file_path}")
        
        # Get the current tools catalog instance
        local_tools_catalog = tools_catalog 
        logging.info(f"Using ToolsCatalog instance: {id(local_tools_catalog)}")

        # Register mock tools
        mock_tool_instance_brave = MockSearchTool(name="brave_search")
        mock_tool_instance_web = MockSearchTool(name="web_search")
        # Use the actual SerperDevTool for the third one, as its schema needs testing
        # Note: We might still need a mock Serper if API keys are an issue
        try:
            # Try registering the actual tool first
            serper_tool = SerperDevTool()
            local_tools_catalog.register_tool(serper_tool, "SerperDevTool")
            print(f"✅ Registered ACTUAL SerperDevTool")
        except Exception as e:
            print(f"⚠️ Could not register actual SerperDevTool ({e}), using mock.")
            # Fallback to mock if needed (e.g., missing API key)
            mock_tool_instance_serper = MockSearchTool(name="SerperDevTool") # Still use mock structure if needed
            local_tools_catalog.register_tool(mock_tool_instance_serper, "SerperDevTool") # <<< REMOVE EXTRA KWARGS

        local_tools_catalog.register_tool(mock_tool_instance_brave, "brave_search") # <<< REMOVE EXTRA KWARGS
        local_tools_catalog.register_tool(mock_tool_instance_web, "web_search") # <<< REMOVE EXTRA KWARGS

        print(f"🔧 Catalog tools after mock registration: {list(local_tools_catalog._tools.keys())}")
        print(f"   Catalog ID after mock registration: {id(local_tools_catalog)}")

        # Load the state file
        with open(state_file_path, 'r') as f:
            state_data = json.load(f)
        
        # Initialize persistence model
        persistence_model = PersistenceModelFactory().persistence_model()
        logging.info(f"Existing persistence model has {len(persistence_model.tasks.list())} tasks")
        
        # Debug: print available attributes in the persistence model
        logging.info(f"Available persistence model attributes: {dir(persistence_model)}")
        
        # Parse managers from the state - each section contains string-encoded JSON that needs parsing again
        managers_str = state_data.get('tasksmanagers', '{}')
        managers_dict = json.loads(managers_str)
        
        for manager_id, manager_dict in managers_dict.items():
            manager = TasksManager.parse_obj(manager_dict)
            persistence_model.tasksmanagers.create(manager)
            logging.info(f"Added task manager: {manager.name} (ID: {manager.id})")
        
        # Parse CrewAI configs from the state
        crewai_configs_str = state_data.get('crewai_config', '{}')
        crewai_configs_dict = json.loads(crewai_configs_str)
        
        for config_id, config_dict in crewai_configs_dict.items():
            config = CrewAIConfig.parse_obj(config_dict)
            persistence_model.crewai_config.create(config)
            logging.info(f"Added CrewAI config: {config.id}")
        
        # Parse curried proxies from the state
        proxies_str = state_data.get('curried_proxies', '{}')
        if not proxies_str:
            proxies_str = state_data.get('curried_proxy', '{}')
        proxies_dict = json.loads(proxies_str)
        
        loaded_proxy = None # Keep track of the loaded proxy
        for proxy_id, proxy_dict in proxies_dict.items():
            # Convert dict to CurriedProxyInfo instance first
            try:
                proxy_info = CurriedProxyInfo(**proxy_dict) 
                # Use the custom from_info method, passing the populated local catalog
                proxy = CurriedProxy.from_info(proxy_info, catalog=local_tools_catalog)
                persistence_model.curried_proxies.create(proxy)
                logging.info(f"Added curried proxy: {proxy.id} using catalog {id(proxy.catalog)}")
                loaded_proxy = proxy # Store the loaded proxy
            except Exception as e:
                logging.error(f"Error loading proxy {proxy_id}: {e}")
                traceback.print_exc()
        
        # Parse tasks from the state
        tasks_str = state_data.get('tasks', '{}')
        tasks_dict = json.loads(tasks_str)
        
        for task_id, task_dict in tasks_dict.items():
            task = Task.parse_obj(task_dict)
            persistence_model.tasks.create(task)
            
            # Only log concert tasks
            if task.framework == "crewai" and task.crewai_config_id:
                logging.info(f"Added concert task: {task.name} (ID: {task.id})")
                logging.info(f"  Framework: {task.framework}")
                logging.info(f"  CrewAI Config ID: {task.crewai_config_id}")
                logging.info(f"  Curried Proxy ID: {task.curried_proxy_id}")
        
        # Find a concert task
        concert_tasks = [
            task for task in persistence_model.tasks.list()
            if task.framework == "crewai" and task.crewai_config_id
        ]
        
        if not concert_tasks:
            logging.error("No concert tasks found with CrewAI config")
            return False
        
        # Get the first concert task
        concert_task = concert_tasks[0]
        logging.info(f"Testing concert task: {concert_task.name} (ID: {concert_task.id})")
        
        # Get the CrewAI config
        crewai_config_id = concert_task.crewai_config_id
        crew_config = persistence_model.crewai_config.read(crewai_config_id)
        
        if not crew_config:
            logging.error(f"CrewAI config not found: {crewai_config_id}")
            return False
        
        logging.info(f"Found CrewAI config: {crew_config.id}")
        
        # Get the curried proxy ID from the task
        curried_proxy_id = concert_task.curried_proxy_id
        # Retrieve the already loaded proxy using the ID
        curried_proxy = persistence_model.curried_proxies.read(curried_proxy_id)

        if curried_proxy:
            logging.info(f"Retrieved curried proxy for task: {curried_proxy.id}")
            logging.info(f"  Proxy Tool Names: {curried_proxy.tool_names}")
            logging.info(f"  Proxy is using catalog: {id(curried_proxy.catalog)}")
        else:
            logging.error(f"Curried proxy {curried_proxy_id} not found in persistence for task.")
            return False

        # Run the task
        task_runner = TaskRunner(persistence_model)
        logging.info("Attempting to run the concert task...")
        tasksmanager_id = concert_task.tasksmanager_id
        
        # Initialize TaskRunner
        await task_runner.initialize()
        
        # Run the task (with await)
        result = await task_runner.run_task(tasksmanager_id, concert_task.id)
        
        logging.info(f"Task execution result: {result}")
        return True
    except Exception as e:
        logging.error(f"Error testing concert task: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_concert_task())
    exit_code = 0 if success else 1
    logger.info(f"Test {'succeeded' if success else 'failed'} with exit code {exit_code}")
    sys.exit(exit_code) 