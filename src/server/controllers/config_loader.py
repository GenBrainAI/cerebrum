import json
from typing import Dict, Any
from ..models.agent import CreateCrewRequest, CrewAIConfig
from ..persistence.persistence_model_factory import PersistenceModelFactory

async def load_config(config_path: str) -> None:
    """Load configuration and initialize CrewAI setup"""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    crew_request = CreateCrewRequest(**config_data)
        
    # Store in persistence model
    config_id = persistence_model.crewai_config.create(
        CrewAIConfig(create_crew=crew_request)
    )
    
    return config_id