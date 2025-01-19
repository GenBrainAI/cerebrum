# Save as: scripts/setup_application_state.py

import sys
import os
from pathlib import Path
import asyncio

# Add the project root to the Python path
project_root = str(Path(__file__).parents[1])
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.agent import (
    CreateCrewRequest, 
    AgentModel, 
    TaskModel, 
    ToolModel,
    ToolsProxyCollection,
    ObjectToolSpec,
    ToolSpec,
    CrewAIConfig
)
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.sms_tool import SMSTool
from src.server.controllers.agents_controller import create_crew
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage

async def setup_application_state():
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create SMS tool and add it to curried proxy
    smstool = SMSTool()
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool("SMSTool", smstool)
    
    # Create and store the curried proxy
    curried_proxy_id = persistence_model.curried_proxies.create(curried_proxy).id
    
    # Create CrewAI configuration with tools_proxy_collection
    crew_request = CreateCrewRequest(
        description="Email Application Response Handler",
        agents=[
            AgentModel(
                role="Application Response Analyzer",
                goal="Analyze email responses to job applications and identify positive responses",
                backstory="An expert at interpreting job application responses and extracting key information for candidates",
                tools=[
                    ToolModel(
                        name="SMSTool.send_application_success_sms",
                        description="Send SMS notifications to candidates about successful applications"
                    ),
                    ToolModel(
                        name="SMSTool.send_sms",
                        description="Send general SMS notifications"
                    )
                ]
            )
        ],
        tasks=[
            TaskModel(
                description="Analyze the email response and if positive, extract key information and notify the candidate via SMS",
                expected_output="SMS notification sent to candidate with relevant details",
                agent_role="Application Response Analyzer"
            )
        ],
        tools_proxy_collection=ToolsProxyCollection(
            toolsets=[],
            functions=[],
            objects=[
                ObjectToolSpec(
                    name="SMSTool",
                    object_type="SMSTool",
                    methods=[
                        "SMSTool.send_sms",
                        "SMSTool.send_application_success_sms"
                    ]
                )
            ]
        )
    )
    
    # Create crew and store configuration
    crew = await create_crew(crew_request, curried_proxy)
    crewai_config = persistence_model.crewai_config.create(CrewAIConfig(create_crew=crew_request))
    
    # Create TasksManager
    tasksmanager = TasksManager(
        name="Application Response Handler",
        model="gpt-4o-mini",
        description="Handles job application email responses and sends notifications",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in analyzing job application responses. 
                When you receive a positive response:
                1. Extract the company name, position, and any key details
                2. Use the SMS tool to send a notification to the candidate
                3. Format the information clearly and professionally
                
                You have access to the following tools:
                - SMSTool.send_application_success_sms: For sending formatted success notifications
                - SMSTool.send_sms: For sending general SMS messages
                
                Always use send_application_success_sms when notifying about positive responses."""
            ).dict()
        ]
    )
    tasksmanager = persistence_model.tasksmanagers.create(tasksmanager)
    
    # Create Task
    task = Task(
        name="Process Application Response",
        description="Analyze email response and send SMS notification if positive",
        tasksmanager_id=tasksmanager.id,
        crewai_config_id=crewai_config.id,
        curried_proxy_id=curried_proxy_id
    )
    task = persistence_model.tasks.create(task)
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="application_handler_state.json"
    )
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    result = save_to_storage(state_location)
    print(f"State saved: {result}")
    
    return {
        "tasksmanager_id": tasksmanager.id,
        "task_id": task.id,
        "curried_proxy_id": curried_proxy_id,
        "crewai_config_id": crewai_config.id
    }

if __name__ == "__main__":
    asyncio.run(setup_application_state())