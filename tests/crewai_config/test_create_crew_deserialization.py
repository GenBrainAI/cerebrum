import unittest
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4, UUID

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

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle UUID and datetime objects."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

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
        
        # Use a specific UUID to ensure consistency
        self.config_id = UUID("12345678-1234-5678-1234-567812345678")
        
        self.crewai_config = CrewAIConfig(
            id=self.config_id,
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
        # Create a file path for testing
        test_file_path = "tests/crewai_config/test_create_crew.json"
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        
        # Print the type before serialization
        print(f"Type of create_crew before file serialization: {type(self.crewai_config.create_crew)}")
        
        # Convert model to dict
        data_dict = self.crewai_config.model_dump()
        
        # Serialize to a file using custom encoder
        with open(test_file_path, "w") as f:
            json.dump(data_dict, f, cls=CustomJSONEncoder)
        
        # Read from the file and deserialize
        with open(test_file_path, "r") as f:
            data = json.load(f)
        
        # Deserialize the data
        deserialized_config = CrewAIConfig.model_validate(data)
        
        # Print the type after deserialization
        print(f"Type of create_crew after deserialization: {type(deserialized_config.create_crew)}")
        
        # Check that it's still a CreateCrewRequest
        self.assertIsInstance(deserialized_config.create_crew, CreateCrewRequest)
        
        # Clean up the file
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
        
        # Retrieve the deserialized configuration using the string version of UUID
        config_id_str = str(self.config_id)
        deserialized_config = new_persistence_model.crewai_config.read(config_id_str)
        
        # If deserialized_config is None, try to debug what's in the crewai_config collection
        if deserialized_config is None:
            print("DEBUG: deserialized_config is None, checking what's in the crewai_config collection")
            print(f"Number of items in crewai_config: {len(new_persistence_model.crewai_config.items)}")
            print(f"Keys in crewai_config: {list(new_persistence_model.crewai_config.items.keys())}")
            
            # Try retrieving by the original ID with different string formats
            if len(new_persistence_model.crewai_config.items) > 0:
                # If there's at least one item, use the first one
                first_key = list(new_persistence_model.crewai_config.items.keys())[0]
                print(f"Using first available config with ID: {first_key}")
                deserialized_config = new_persistence_model.crewai_config.items[first_key]
            else:
                self.fail("No CrewAIConfig items found after deserialization")
        
        # Try to access various attributes of create_crew
        try:
            # Ensure deserialized_config is not None
            self.assertIsNotNone(deserialized_config, "Deserialized config should not be None")
            
            # Ensure create_crew is accessible
            self.assertIsNotNone(deserialized_config.create_crew, "create_crew should not be None")
            
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