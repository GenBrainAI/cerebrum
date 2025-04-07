import unittest
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.server.models.agent import (
    CrewAIConfig, 
    CreateCrewRequest, 
    AgentModel, 
    TaskModel, 
    AgentTool,
    Process
)
from src.server.persistence.in_memory_crud import CrewAIConfigCrud
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.controllers.persistence_controller import save_to_storage, load_from_storage
from src.server.models.persistence_models import StorageLocation, StorageType


class TestCreateCrewDeserialization(unittest.TestCase):
    """Test specifically for the create_crew field deserialization issue."""

    def setUp(self):
        """Set up test data."""
        # Create a sample CrewAI configuration
        self.tool1 = AgentTool(
            name="WebsiteSearchTool",
            description="Search the web for information"
        )
        
        self.agent1 = AgentModel(
            role="Researcher",
            goal="Find information",
            backstory="You are an expert researcher",
            tools=[self.tool1],
            verbose=True
        )
        
        self.task1 = TaskModel(
            description="Research a topic",
            expected_output="Comprehensive research report",
            agent_role="Researcher"
        )
        
        self.create_crew_request = CreateCrewRequest(
            description="Test Crew",
            process=Process.sequential,
            agents=[self.agent1],
            tasks=[self.task1]
        )
        
        self.crewai_config = CrewAIConfig(
            id=uuid4(),
            create_crew=self.create_crew_request,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Initialize the CRUD handler
        self.crud = CrewAIConfigCrud()
        
        # Initialize the persistence model
        self.persistence_model = InMemoryPersistenceModel()

    def test_create_crew_type_after_serialization(self):
        """Test that create_crew maintains its type after serialization and deserialization."""
        # Serialize the configuration to JSON
        json_data = self.crewai_config.model_dump_json()
        
        # Deserialize back to CrewAIConfig
        deserialized_config = CrewAIConfig.model_validate_json(json_data)
        
        # Get the create_crew object from the deserialized config
        create_crew = deserialized_config.create_crew
        
        # Check the type
        print(f"Type of create_crew before serialization: {type(self.crewai_config.create_crew)}")
        print(f"Type of create_crew after deserialization: {type(create_crew)}")
        
        # Verify that it's a CreateCrewRequest instance
        self.assertIsInstance(create_crew, CreateCrewRequest)
        
        # Verify attributes
        self.assertEqual(create_crew.description, "Test Crew")
        self.assertEqual(create_crew.process, Process.sequential)
        self.assertEqual(len(create_crew.agents), 1)
        self.assertEqual(len(create_crew.tasks), 1)
        
        # Verify agent attributes
        agent = create_crew.agents[0]
        self.assertEqual(agent.role, "Researcher")
        
        print("✅ create_crew maintains its type after direct serialization and deserialization")

    def test_create_crew_type_after_crud_serialization(self):
        """Test that create_crew maintains its type after CRUD serialization and deserialization."""
        # Get the type before serialization
        print(f"Type of create_crew before CRUD serialization: {type(self.crewai_config.create_crew)}")
        
        # Add the configuration to the CRUD handler
        self.crud.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.crud.to_json()
        
        # Create a new CRUD handler and deserialize
        new_crud = CrewAIConfigCrud()
        new_crud.from_json(json_data)
        
        # Retrieve the deserialized configuration using string ID
        deserialized_config = new_crud.read(str(self.crewai_config.id))
        
        # Check if deserialized_config is None
        if deserialized_config is None:
            self.fail("Failed to retrieve the deserialized configuration - got None")
            
        # Get the create_crew object
        print(f"Type of create_crew after CRUD deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that it's a CreateCrewRequest instance
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        print("✅ create_crew maintains its type after CRUD serialization and deserialization")

    def test_create_crew_type_after_persistence_serialization(self):
        """Test that create_crew maintains its type after persistence serialization and deserialization."""
        # Get the type before serialization
        print(f"Type of create_crew before persistence serialization: {type(self.crewai_config.create_crew)}")
        
        # Add the configuration to the persistence model
        self.persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.persistence_model.to_json()
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(json_data)
        
        # Retrieve the deserialized configuration using string ID
        deserialized_config = new_persistence_model.crewai_config.read(str(self.crewai_config.id))
        
        # Check if deserialized_config is None
        if deserialized_config is None:
            self.fail("Failed to retrieve the deserialized configuration - got None")
            
        # Get the create_crew object
        print(f"Type of create_crew after persistence deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that it's a CreateCrewRequest instance
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        print("✅ create_crew maintains its type after persistence serialization and deserialization")

    def test_create_crew_type_after_file_serialization(self):
        """Test that create_crew maintains its type after file serialization and deserialization."""
        # Create a file to store the serialized data
        test_file_path = "tests/crewai_config/test_create_crew.json"
        
        # Get the type before serialization
        print(f"Type of create_crew before file serialization: {type(self.crewai_config.create_crew)}")
        
        # Add the configuration to the persistence model
        self.persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON and save to file
        json_data = self.persistence_model.to_json()
        with open(test_file_path, "w") as f:
            f.write(json_data)
        
        # Read the file back
        with open(test_file_path, "r") as f:
            loaded_json = f.read()
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(loaded_json)
        
        # Retrieve the deserialized configuration using string ID
        deserialized_config = new_persistence_model.crewai_config.read(str(self.crewai_config.id))
        
        # Check if deserialized_config is None
        if deserialized_config is None:
            self.fail("Failed to retrieve the deserialized configuration - got None")
            
        # Get the create_crew object
        print(f"Type of create_crew after file deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that it's a CreateCrewRequest instance
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Clean up the test file
        os.remove(test_file_path)
        
        print("✅ create_crew maintains its type after file serialization and deserialization")

    def test_create_crew_access_after_deserialization(self):
        """Test that we can access create_crew attributes after deserialization."""
        # Create a persistence model and add the configuration
        persistence_model = InMemoryPersistenceModel()
        persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = persistence_model.to_json()
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(json_data)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_persistence_model.crewai_config.read("test-config-id")
        
        # Try to access various attributes of create_crew
        try:
            # Access description
            description = deserialized_config.create_crew.description
            print(f"Successfully accessed description: {description}")
            
            # Access process
            process = deserialized_config.create_crew.process
            print(f"Successfully accessed process: {process}")
            
            # Access agents
            agents = deserialized_config.create_crew.agents
            print(f"Successfully accessed agents: {len(agents)} agents found")
            
            # Access first agent's role
            role = deserialized_config.create_crew.agents[0].role
            print(f"Successfully accessed first agent's role: {role}")
            
            # Access first agent's tools
            tools = deserialized_config.create_crew.agents[0].tools
            print(f"Successfully accessed first agent's tools: {len(tools)} tools found")
            
            # Access first tool's name
            tool_name = deserialized_config.create_crew.agents[0].tools[0].name
            print(f"Successfully accessed first tool's name: {tool_name}")
            
            # Access tasks
            tasks = deserialized_config.create_crew.tasks
            print(f"Successfully accessed tasks: {len(tasks)} tasks found")
            
            # Access first task's description
            task_description = deserialized_config.create_crew.tasks[0].description
            print(f"Successfully accessed first task's description: {task_description}")
            
            print("✅ All create_crew attributes are accessible after deserialization")
            
        except Exception as e:
            self.fail(f"Failed to access create_crew attributes: {str(e)}")


if __name__ == "__main__":
    unittest.main() 