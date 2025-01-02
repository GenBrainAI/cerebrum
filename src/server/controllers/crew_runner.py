from typing import Dict, Any, Optional, Union
import asyncio
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.curried_proxy import CurriedProxy

def format_response(response: Union[str, Dict[str, Any], Any]) -> str:
    """Format the crew response into a string."""
    if isinstance(response, str):
        try:
            # Try to parse as JSON first
            parsed = json.loads(response)
            # If it's already a string representation of JSON, return it
            if isinstance(parsed, str):
                try:
                    json.loads(parsed)  # Try to parse again to validate
                    return parsed
                except json.JSONDecodeError:
                    return json.dumps(parsed)
            return response
        except json.JSONDecodeError:
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

async def run_crew_task(
    task_id: str, 
    task_input: Optional[Dict[str, Any]] = None,
    persistence_model: Optional[Any] = None
) -> Dict[str, Any]:
    """Execute a CrewAI task.
    
    Args:
        task_id: The ID of the task to run
        task_input: Optional input parameters for the task
        persistence_model: Optional persistence model to use. If None, uses global persistence.
    """
    try:
        # Use provided persistence model or get global one
        if persistence_model is None:
            persistence_model = PersistenceModelFactory.persistence_model()
            print("🌍 Using global persistence model")
        else:
            print(f"🔧 Using provided persistence model: {type(persistence_model)}")
        
        # Debug task lookup
        print(f"\n🔍 Looking for task {task_id} in persistence model")
        task = persistence_model.tasks.read(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in persistence model")
        print(f"✅ Found task: {task.name}")
        
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
        error_msg = f"run_crew_task failed with error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "response": f"run_crew_task failed with error: {str(e)}",
            "status": "error"
        }