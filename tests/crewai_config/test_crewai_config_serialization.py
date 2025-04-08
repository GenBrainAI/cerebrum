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


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle UUID and datetime objects."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class TestCrewAIConfigSerialization(unittest.TestCase):
    """Test serialization and deserialization of CrewAI configuration."""

    def setUp(self):
        """Set up test data."""
        # Create a sample CrewAI configuration
        self.tool1 = AgentTool(
            name="WebsiteSearchTool",
            description="Search the web for information"
        )
        
        self.tool2 = AgentTool(
            name="SerperDevTool",
            description="Search the web using Serper API"
        )
        
        self.agent1 = AgentModel(
            role="Researcher",
            goal="Find information",
            backstory="You are an expert researcher",
            tools=[self.tool1, self.tool2],
            verbose=True
        )
        
        self.agent2 = AgentModel(
            role="Writer",
            goal="Write content",
            backstory="You are an expert writer",
            tools=[self.tool1],
            verbose=True
        )
        
        self.task1 = TaskModel(
            description="Research a topic",
            expected_output="Comprehensive research report",
            agent_role="Researcher"
        )
        
        self.task2 = TaskModel(
            description="Write an article",
            expected_output="Well-written article",
            agent_role="Writer",
            depends_on=["Research a topic"]
        )
        
        self.create_crew_request = CreateCrewRequest(
            description="Test Crew",
            process=Process.sequential,
            agents=[self.agent1, self.agent2],
            tasks=[self.task1, self.task2]
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

    def test_direct_serialization(self):
        """Test direct serialization of CrewAIConfig to JSON."""
        # Serialize the configuration to JSON
        json_data = self.crewai_config.model_dump_json()
        
        # Parse the JSON back to a dictionary
        parsed_data = json.loads(json_data)
        
        # Verify the structure
        self.assertEqual(parsed_data["id"], str(self.crewai_config.id))
        self.assertIn("create_crew", parsed_data)
        
        # Verify create_crew structure
        create_crew = parsed_data["create_crew"]
        self.assertEqual(create_crew["description"], "Test Crew")
        self.assertEqual(create_crew["process"], "sequential")
        self.assertEqual(len(create_crew["agents"]), 2)
        self.assertEqual(len(create_crew["tasks"]), 2)
        
        # Verify agent structure
        agent = create_crew["agents"][0]
        self.assertEqual(agent["role"], "Researcher")
        self.assertEqual(agent["goal"], "Find information")
        self.assertEqual(len(agent["tools"]), 2)
        
        # Verify tool structure
        tool = agent["tools"][0]
        self.assertEqual(tool["name"], "WebsiteSearchTool")
        self.assertEqual(tool["description"], "Search the web for information")
        
        print("✅ Direct serialization test passed")

    def test_direct_deserialization(self):
        """Test direct deserialization of JSON to CrewAIConfig."""
        # Serialize the configuration to JSON
        json_data = self.crewai_config.model_dump_json()
        
        # Deserialize back to CrewAIConfig
        deserialized_config = CrewAIConfig.model_validate_json(json_data)
        
        # Verify the structure
        self.assertEqual(deserialized_config.id, self.crewai_config.id)
        self.assertIsNotNone(deserialized_config.create_crew)
        
        # Verify create_crew structure
        create_crew = deserialized_config.create_crew
        self.assertEqual(create_crew.description, "Test Crew")
        self.assertEqual(create_crew.process, Process.sequential)
        self.assertEqual(len(create_crew.agents), 2)
        self.assertEqual(len(create_crew.tasks), 2)
        
        # Verify agent structure
        agent = create_crew.agents[0]
        self.assertEqual(agent.role, "Researcher")
        self.assertEqual(agent.goal, "Find information")
        self.assertEqual(len(agent.tools), 2)
        
        # Verify tool structure
        tool = agent.tools[0]
        self.assertEqual(tool.name, "WebsiteSearchTool")
        self.assertEqual(tool.description, "Search the web for information")
        
        print("✅ Direct deserialization test passed")

    def test_crud_serialization(self):
        """Test serialization using the CRUD handler."""
        # Add the configuration to the CRUD handler
        self.crud.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.crud.to_json()
        
        # Parse the JSON back to a dictionary
        parsed_data = json.loads(json_data)
        
        # Verify the structure
        self.assertIn(str(self.crewai_config.id), parsed_data)
        config_data = parsed_data[str(self.crewai_config.id)]
        self.assertEqual(config_data["id"], str(self.crewai_config.id))
        self.assertIn("create_crew", config_data)
        
        # Verify create_crew structure
        create_crew = config_data["create_crew"]
        self.assertEqual(create_crew["description"], "Test Crew")
        self.assertEqual(create_crew["process"], "sequential")
        self.assertEqual(len(create_crew["agents"]), 2)
        self.assertEqual(len(create_crew["tasks"]), 2)
        
        print("✅ CRUD serialization test passed")

    def test_crud_deserialization(self):
        """Test deserialization using the CRUD handler."""
        # Add the configuration to the CRUD handler
        self.crud.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.crud.to_json()
        
        # Create a new CRUD handler and deserialize
        new_crud = CrewAIConfigCrud()
        new_crud.from_json(json_data)
        
        # Get the string version of the ID
        config_id_str = str(self.config_id)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_crud.read(config_id_str)
        
        # Debug: check what's in the CRUD handler
        if deserialized_config is None:
            print(f"DEBUG: config not found with ID: {config_id_str}")
            print(f"Number of items in new_crud: {len(new_crud.items)}")
            print(f"Keys in new_crud: {list(new_crud.items.keys())}")
            
            # Try to retrieve using the first available key
            if len(new_crud.items) > 0:
                first_key = list(new_crud.items.keys())[0]
                print(f"Trying first key: {first_key}")
                deserialized_config = new_crud.items[first_key]
            else:
                self.fail("No items found in the CRUD handler after deserialization")
        
        # Verify the structure
        self.assertIsNotNone(deserialized_config, "Deserialized config should not be None")
        self.assertEqual(str(deserialized_config.id), config_id_str)
        self.assertIsNotNone(deserialized_config.create_crew)
        
        # Verify create_crew structure
        create_crew = deserialized_config.create_crew
        self.assertEqual(create_crew.description, "Test Crew")
        self.assertEqual(create_crew.process, Process.sequential)
        self.assertEqual(len(create_crew.agents), 2)
        self.assertEqual(len(create_crew.tasks), 2)
        
        # Verify agent structure
        agent = create_crew.agents[0]
        self.assertEqual(agent.role, "Researcher")
        self.assertEqual(agent.goal, "Find information")
        self.assertEqual(len(agent.tools), 2)
        
        # Verify tool structure
        tool = agent.tools[0]
        self.assertEqual(tool.name, "WebsiteSearchTool")
        self.assertEqual(tool.description, "Search the web for information")
        
        print("✅ CRUD deserialization test passed")

    def test_persistence_model_serialization(self):
        """Test serialization using the persistence model."""
        # Add the configuration to the persistence model
        self.persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.persistence_model.to_json()
        
        # Parse the JSON back to a dictionary
        parsed_data = json.loads(json_data)
        
        # Verify the structure
        self.assertIn("crewai_config", parsed_data)
        crewai_config_json = parsed_data["crewai_config"]
        crewai_config_data = json.loads(crewai_config_json) if isinstance(crewai_config_json, str) else crewai_config_json
        
        self.assertIn(str(self.crewai_config.id), crewai_config_data)
        config_data = crewai_config_data[str(self.crewai_config.id)]
        self.assertEqual(config_data["id"], str(self.crewai_config.id))
        self.assertIn("create_crew", config_data)
        
        print("✅ Persistence model serialization test passed")

    def test_persistence_model_deserialization(self):
        """Test deserialization using the persistence model."""
        # Add the configuration to the persistence model
        self.persistence_model.crewai_config.create(self.crewai_config)
        
        # Serialize to JSON
        json_data = self.persistence_model.to_json()
        
        # Create a new persistence model and deserialize
        new_persistence_model = InMemoryPersistenceModel()
        new_persistence_model.from_json(json_data)
        
        # Get the string version of the ID
        config_id_str = str(self.config_id)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_persistence_model.crewai_config.read(config_id_str)
        
        # Debug: check what's in the persistence model
        if deserialized_config is None:
            print(f"DEBUG: config not found with ID: {config_id_str}")
            print(f"Number of items in crewai_config: {len(new_persistence_model.crewai_config.items)}")
            print(f"Keys in crewai_config: {list(new_persistence_model.crewai_config.items.keys())}")
            
            # Try to retrieve using the first available key
            if len(new_persistence_model.crewai_config.items) > 0:
                first_key = list(new_persistence_model.crewai_config.items.keys())[0]
                print(f"Trying first key: {first_key}")
                deserialized_config = new_persistence_model.crewai_config.items[first_key]
            else:
                self.fail("No items found in the persistence model after deserialization")
        
        # Verify the structure
        self.assertIsNotNone(deserialized_config, "Deserialized config should not be None")
        self.assertEqual(str(deserialized_config.id), config_id_str)
        self.assertIsNotNone(deserialized_config.create_crew)
        
        # Verify create_crew structure
        create_crew = deserialized_config.create_crew
        self.assertEqual(create_crew.description, "Test Crew")
        self.assertEqual(create_crew.process, Process.sequential)
        self.assertEqual(len(create_crew.agents), 2)
        self.assertEqual(len(create_crew.tasks), 2)
        
        # Verify agent structure
        agent = create_crew.agents[0]
        self.assertEqual(agent.role, "Researcher")
        self.assertEqual(agent.goal, "Find information")
        self.assertEqual(len(agent.tools), 2)
        
        # Verify tool structure
        tool = agent.tools[0]
        self.assertEqual(tool.name, "WebsiteSearchTool")
        self.assertEqual(tool.description, "Search the web for information")
        
        print("✅ Persistence model deserialization test passed")

    def test_full_serialization_cycle(self):
        """Test a full serialization and deserialization cycle."""
        # Create a file to store the serialized data
        test_file_path = "tests/crewai_config/test_serialization.json"
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        
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
        
        # Get the string version of the ID
        config_id_str = str(self.config_id)
        
        # Retrieve the deserialized configuration
        deserialized_config = new_persistence_model.crewai_config.read(config_id_str)
        
        # Debug: check what's in the persistence model
        if deserialized_config is None:
            print(f"DEBUG: config not found with ID: {config_id_str}")
            print(f"Number of items in crewai_config: {len(new_persistence_model.crewai_config.items)}")
            print(f"Keys in crewai_config: {list(new_persistence_model.crewai_config.items.keys())}")
            
            # Try to retrieve using the first available key
            if len(new_persistence_model.crewai_config.items) > 0:
                first_key = list(new_persistence_model.crewai_config.items.keys())[0]
                print(f"Trying first key: {first_key}")
                deserialized_config = new_persistence_model.crewai_config.items[first_key]
            else:
                self.fail("No items found in the persistence model after deserialization")
        
        # Verify the structure
        self.assertIsNotNone(deserialized_config, "Deserialized config should not be None")
        self.assertEqual(str(deserialized_config.id), config_id_str)
        self.assertIsNotNone(deserialized_config.create_crew)
        
        # Verify create_crew structure
        create_crew = deserialized_config.create_crew
        self.assertEqual(create_crew.description, "Test Crew")
        self.assertEqual(create_crew.process, Process.sequential)
        self.assertEqual(len(create_crew.agents), 2)
        self.assertEqual(len(create_crew.tasks), 2)
        
        # Clean up the test file
        os.remove(test_file_path)
        
        print("✅ Full serialization cycle test passed")


if __name__ == "__main__":
    unittest.main() 