from typing import Dict, Any, Optional, Union
import asyncio
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.curried_proxy import CurriedProxy

def format_response(response: Union[str, Dict[str, Any], Any]) -> str:
    """Format the crew response into a string."""
    if isinstance(response, str):
        return response
    elif isinstance(response, dict):
        try:
            return json.dumps(response)
        except TypeError:
            # Handle non-serializable objects in the dict
            serializable_dict = {}
            for key, value in response.items():
                try:
                    json.dumps(value)  # Test if value is JSON serializable
                    serializable_dict[key] = value
                except (TypeError, ValueError):
                    serializable_dict[key] = "N/S"  # Non-serializable
            return json.dumps(serializable_dict)
    else:
        try:
            return str(response)
        except Exception:
            return "N/S"  # Non-serializable object

async def run_crew_task(task_id: str, task_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a CrewAI task."""
    try:
        persistence_model = PersistenceModelFactory.persistence_model()
        
        # Get the task and its CrewAI configuration
        task = persistence_model.tasks.read(task_id)
        if not task or not task.crewai_config_id:
            raise ValueError(f"Task {task_id} not found or is not a CrewAI task")
            
        crewai_config = persistence_model.crewai_config.read(task.crewai_config_id)
        if not crewai_config:
            raise ValueError(f"CrewAI configuration {task.crewai_config_id} not found")
        
        # Create or get the curried proxy
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)
        else:
            curried_proxy = CurriedProxy()
        
        # Create and execute the crew
        from .agents_controller import create_crew
        crew = await create_crew(crewai_config.create_crew, curried_proxy)
        
        # Execute the crew with the provided input using run_in_executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff, task_input or {})
        
        # Format the result into a string response
        formatted_result = format_response(result)
        
        return {
            "response": formatted_result,
            "status": "success"
        }
    except Exception as e:
        return {
            "response": f"run_crew_task failed with error: {str(e)}",
            "status": "error"
        }
