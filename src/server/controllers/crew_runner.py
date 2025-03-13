from typing import Dict, Any, Optional, Union
import asyncio
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.curried_proxy import CurriedProxy
from datetime import datetime

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

def sanitize_data(data):
    """
    Recursively sanitize data for CrewAI by converting datetime objects to strings
    and ensuring all data is of supported types (str, int, float, bool, dict, list).
    
    Args:
        data: The data to sanitize
        
    Returns:
        Sanitized data safe for CrewAI
    """
    import datetime
    
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, (datetime.datetime, datetime.date)):
        return str(data)
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # Convert any other types to strings
        return str(data)

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
            print("🔄 Using existing persistence model from session state")
        
        # Debug task lookup
        print(f"\n🔍 Looking for task {task_id} in persistence model")
        task = persistence_model.tasks.read(task_id)
        if not task:
            error_msg = f"Task {task_id} not found in persistence model"
            print(f"❌ {error_msg}")
            return {
                "response": error_msg,
                "status": "failed",
                "error": error_msg
            }
        print(f"✅ Found task: {task.name}")
        
        # Initialize execution logs if not present
        if task.execution_logs is None:
            task.execution_logs = []
        
        crewai_config = persistence_model.crewai_config.read(task.crewai_config_id)
        if not crewai_config:
            error_msg = f"CrewAI configuration {task.crewai_config_id} not found"
            task.execution_logs.append({
                "timestamp": str(datetime.now()),
                "type": "error",
                "content": error_msg
            })
            persistence_model.tasks.update(task_id, task)
            return {
                "response": error_msg,
                "status": "failed",
                "error": error_msg
            }
        
        # Create or get the curried proxy
        curried_proxy = None
        if task.curried_proxy_id:
            curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)
        else:
            curried_proxy = CurriedProxy()
        
        # Validate agent role exists in crew configuration
        if task.agent_role:
            agent_roles = [agent.role for agent in crewai_config.create_crew.agents]
            if task.agent_role not in agent_roles:
                error_msg = f"Agent role '{task.agent_role}' not found in crew configuration. Available roles: {', '.join(agent_roles)}"
                task.execution_logs.append({
                    "timestamp": str(datetime.now()),
                    "type": "error",
                    "content": error_msg
                })
                persistence_model.tasks.update(task_id, task)
                return {
                    "response": error_msg,
                    "status": "failed",
                    "error": error_msg
                }
        
        # Create and execute the crew
        from .agents_controller import create_crew
        crew = await create_crew(crewai_config.create_crew, curried_proxy)
        
        # Add start log
        task.execution_logs.append({
            "timestamp": str(datetime.now()),
            "type": "info",
            "content": "Starting CrewAI task execution"
        })
        persistence_model.tasks.update(task_id, task)
        
        # Ensure task_input is sanitized for CrewAI
        sanitized_input = sanitize_data(task_input or {})
        print(f"🧹 Task input sanitized for CrewAI compatibility")
        
        # Execute the crew with the provided input using run_in_executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff, sanitized_input)
        
        # Format the result into a string response
        formatted_result = format_response(result)
        
        # Extract tool information from input data
        tool_info = None
        if task.input_data and 'tool_request' in task.input_data:
            tool_info = task.input_data['tool_request']
        
        # Add completion log
        task.execution_logs.append({
            "timestamp": str(datetime.now()),
            "type": "info",
            "content": "CrewAI task execution completed",
            "result": formatted_result
        })
        
        # Save the updated task
        persistence_model.tasks.update(task_id, task)
        
        return {
            "response": formatted_result,
            "status": "success",
            "generated_tool": tool_info
        }
    except Exception as e:
        error_msg = f"Error in CrewAI task execution: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Add error log if task exists
        if 'task' in locals() and task:
            if task.execution_logs is None:
                task.execution_logs = []
            task.execution_logs.append({
                "timestamp": str(datetime.now()),
                "type": "error",
                "content": error_msg
            })
            persistence_model.tasks.update(task_id, task)
        
        return {
            "response": error_msg,
            "status": "failed",
            "error": error_msg
        }