from typing import Dict, Any, Optional, Union
import asyncio
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..controllers.curried_proxy import CurriedProxy
from datetime import datetime
from ..tools.human_tools import human_input_tool

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
        
        # Debug dump of task attributes
        task_attrs = {
            'id': getattr(task, 'id', None),
            'name': getattr(task, 'name', None),
            'framework': getattr(task, 'framework', None),
            'crewai_config_id': getattr(task, 'crewai_config_id', None),
            'curried_proxy_id': getattr(task, 'curried_proxy_id', None),
            'human_input': getattr(task, 'human_input', False)
        }
        print(f"📋 Task details: {task_attrs}")
        
        # Check if crewai_config_id is available
        if not hasattr(task, 'crewai_config_id') or not task.crewai_config_id:
            error_msg = f"CrewAI configuration ID not found in task attributes"
            print(f"❌ {error_msg}")
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
            
        print(f"🔍 Looking for CrewAI config {task.crewai_config_id} in persistence model")
        
        try:
            # Get configuration with error tracing
            crewai_config = persistence_model.crewai_config.read(task.crewai_config_id)
            if not crewai_config:
                error_msg = f"CrewAI configuration {task.crewai_config_id} not found in persistence model"
                print(f"❌ {error_msg}")
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
            print(f"✅ Found CrewAI config: {getattr(crewai_config, 'name', 'Unnamed config')}")
        except Exception as config_e:
            error_msg = f"Error retrieving CrewAI configuration: {str(config_e)}"
            print(f"❌ {error_msg}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
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
        try:
            if task.curried_proxy_id:
                print(f"🔍 Getting curried proxy with ID: {task.curried_proxy_id}")
                curried_proxy = persistence_model.curried_proxies.read(task.curried_proxy_id)
                if not curried_proxy:
                    print(f"⚠️ Curried proxy {task.curried_proxy_id} not found, creating new one")
                    curried_proxy = CurriedProxy()
                else:
                    print(f"✅ Found curried proxy with ID: {task.curried_proxy_id}")
            else:
                print(f"⚠️ No curried proxy ID specified, creating new one")
                curried_proxy = CurriedProxy()
            
            # Check if human input is enabled
            human_input_enabled = False
            if hasattr(task, 'human_input') and task.human_input:
                human_input_enabled = True
                print(f"🧠 Human input is enabled for this task")
                
                # Check if we're in test mode
                is_test_mode = task_input and task_input.get('test_mode', False)
                if is_test_mode:
                    from ..tools.human_tools.human_tool import HumanInputTool
                    print(f"🤖 Test mode detected - configuring HumanInputTool for automated responses")
                    
                    # Define default test responses if not provided
                    mock_responses = task_input.get('mock_responses', [
                        "I'm interested in rock and electronic music festivals in Europe.",
                        "My budget is around 500 euros for tickets.",
                        "I'd prefer festivals with camping options and good transportation.",
                        "That sounds great! Please provide more details."
                    ])
                    
                    # Configure the tool for test mode
                    HumanInputTool.configure_test_mode(enable=True, mock_responses=mock_responses)
                    print(f"🤖 HumanInputTool configured for test mode with {len(mock_responses)} responses")
                
                # Add human input tool to tools
                if not hasattr(curried_proxy, 'tools'):
                    curried_proxy.tools = {}
                
                # Register human input tool in the curried_proxy
                curried_proxy.add_tool('human_input', human_input_tool)
                print(f"✅ Registered human input tool")
                
            # Ensure we pass allowed_tools from the CrewAIConfig to create_crew
            from .agents_controller import create_crew
            
            # Check if crewai_config has allowed_tools
            create_crew_request = crewai_config.create_crew
            if hasattr(crewai_config, 'allowed_tools') and crewai_config.allowed_tools:
                # Add human_input to allowed_tools if enabled
                if human_input_enabled and 'human_input' not in crewai_config.allowed_tools:
                    crewai_config.allowed_tools.append('human_input')
                    
                print(f"📋 Found allowed_tools in CrewAIConfig: {', '.join(crewai_config.allowed_tools)}")
                # Make sure allowed_tools is accessible to CreateCrewRequest
                if not hasattr(create_crew_request, 'allowed_tools'):
                    # Add allowed_tools as an attribute
                    create_crew_request.allowed_tools = crewai_config.allowed_tools
                else:
                    # Update existing attribute
                    create_crew_request.allowed_tools = crewai_config.allowed_tools
            elif human_input_enabled:
                # If no allowed_tools defined but human_input is enabled, create the list
                allowed_tools = ['human_input']
                print(f"📋 Setting allowed_tools to include human_input: {', '.join(allowed_tools)}")
                if not hasattr(create_crew_request, 'allowed_tools'):
                    create_crew_request.allowed_tools = allowed_tools
                else:
                    create_crew_request.allowed_tools = allowed_tools
            else:
                print("📋 No allowed_tools found in CrewAIConfig, will use defaults")
            
            crew = await create_crew(crewai_config.create_crew, curried_proxy)
            
            # Validate agent role exists in crew configuration
            if hasattr(task, 'agent_role') and task.agent_role:
                try:
                    agent_roles = [getattr(agent, 'role', None) for agent in getattr(crewai_config, 'agents', [])]
                    if task.agent_role not in agent_roles:
                        error_msg = f"Agent role '{task.agent_role}' not found in crew configuration. Available roles: {', '.join(agent_roles)}"
                        print(f"❌ {error_msg}")
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
                    print(f"✅ Validated agent role: {task.agent_role}")
                except Exception as role_e:
                    print(f"⚠️ Error validating agent role: {str(role_e)}. Proceeding without role validation.")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
            
            # Add start log
            task.execution_logs.append({
                "timestamp": str(datetime.now()),
                "type": "info",
                "content": "Starting CrewAI task execution"
            })
            persistence_model.tasks.update(task_id, task)
            
            # Set human_input flag in task parameters if enabled
            if human_input_enabled and task_input:
                task_input['human_input_enabled'] = True
            
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