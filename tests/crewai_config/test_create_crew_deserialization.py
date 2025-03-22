import unittest
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.server.models.agent import (
    CrewAIConfig, 
    CreateCrewRequest, 
    AgentModel, 
    TaskModel, 
    ToolModel,
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
        # Create a sample CrewAI configuration with a CreateCrewRequest
        self.tool1 = ToolModel(
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
            id="test-config-id",
            create_crew=self.create_crew_request,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            process=Process.sequential
        )

    def test_create_crew_type_after_serialization(self):
        """Test that create_crew maintains its type after serialization and deserialization."""
        # Serialize the configuration to JSON
        json_data = self.crewai_config.model_dump_json()
        
        # Print the JSON for debugging
        print(f"Serialized JSON: {json_data[:200]}...")
        
        # Deserialize back to CrewAIConfig
        deserialized_config = CrewAIConfig.model_validate_json(json_data)
        
        # Check the type of create_crew
        print(f"Type of create_crew before serialization: {type(self.crewai_config.create_crew)}")
        print(f"Type of create_crew after deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that create_crew is a CreateCrewRequest
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Verify that we can access attributes of create_crew
        self.assertEqual(deserialized_config.create_crew.description, "Test Crew")
        self.assertEqual(deserialized_config.create_crew.process, Process.sequential)
        self.assertEqual(len(deserialized_config.create_crew.agents), 1)
        self.assertEqual(deserialized_config.create_crew.agents[0].role, "Researcher")
        
        print("✅ create_crew maintains its type after direct serialization and deserialization")

    def test_create_crew_type_after_crud_serialization(self):
        """Test that create_crew maintains its type after CRUD serialization and deserialization."""
        # Create a CRUD handler and add the configuration
        crud = CrewAIConfigCrud()
        crud.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = crud.to_json()
        
        # Print the JSON for debugging
        print(f"CRUD Serialized JSON: {json_data[:200]}...")
        
        # Create a new CRUD handler and deserialize
        new_crud = CrewAIConfigCrud()
        new_crud.from_json(json_data)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_crud.read("test-config-id")
        
        # Check the type of create_crew
        print(f"Type of create_crew before CRUD serialization: {type(self.crewai_config.create_crew)}")
        print(f"Type of create_crew after CRUD deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that create_crew is a CreateCrewRequest
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Verify that we can access attributes of create_crew
        self.assertEqual(deserialized_config.create_crew.description, "Test Crew")
        self.assertEqual(deserialized_config.create_crew.process, Process.sequential)
        self.assertEqual(len(deserialized_config.create_crew.agents), 1)
        self.assertEqual(deserialized_config.create_crew.agents[0].role, "Researcher")
        
        print("✅ create_crew maintains its type after CRUD serialization and deserialization")

    def test_create_crew_type_after_persistence_serialization(self):
        """Test that create_crew maintains its type after persistence serialization and deserialization."""
        # Create a persistence model and add the configuration
        persistence_model = InMemoryPersistenceModel()
        persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = persistence_model.to_json()
        
        # Print the JSON for debugging
        print(f"Persistence Serialized JSON: {json_data[:200]}...")
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(json_data)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_persistence_model.crewai_config.read("test-config-id")
        
        # Check the type of create_crew
        print(f"Type of create_crew before persistence serialization: {type(self.crewai_config.create_crew)}")
        print(f"Type of create_crew after persistence deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that create_crew is a CreateCrewRequest
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Verify that we can access attributes of create_crew
        self.assertEqual(deserialized_config.create_crew.description, "Test Crew")
        self.assertEqual(deserialized_config.create_crew.process, Process.sequential)
        self.assertEqual(len(deserialized_config.create_crew.agents), 1)
        self.assertEqual(deserialized_config.create_crew.agents[0].role, "Researcher")
        
        print("✅ create_crew maintains its type after persistence serialization and deserialization")

    def test_create_crew_type_after_file_serialization(self):
        """Test that create_crew maintains its type after file serialization and deserialization."""
        # Create a file to store the serialized data
        test_file_path = "tests/crewai_config/test_create_crew.json"
        
        # Create a persistence model and add the configuration
        persistence_model = InMemoryPersistenceModel()
        persistence_model.crewai_config.create(self.crewai_config)
        
        # Save to file
        storage_location = StorageLocation(
            type=StorageType.file,
            location="tests/crewai_config",
            state_name="test_create_crew.json"
        )
        save_to_storage(persistence_model, storage_location)
        
        # Load from file
        json_str = load_from_storage(storage_location)
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(json_str)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_persistence_model.crewai_config.read("test-config-id")
        
        # Check the type of create_crew
        print(f"Type of create_crew before file serialization: {type(self.crewai_config.create_crew)}")
        print(f"Type of create_crew after file deserialization: {type(deserialized_config.create_crew)}")
        
        # Verify that create_crew is a CreateCrewRequest
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Verify that we can access attributes of create_crew
        self.assertEqual(deserialized_config.create_crew.description, "Test Crew")
        self.assertEqual(deserialized_config.create_crew.process, Process.sequential)
        self.assertEqual(len(deserialized_config.create_crew.agents), 1)
        self.assertEqual(deserialized_config.create_crew.agents[0].role, "Researcher")
        
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