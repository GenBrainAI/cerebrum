#!/usr/bin/env python3
"""
Concert Travel Planner State Generator

This script creates a specialized state for planning concert trips using CrewAI.
It properly sets up tasks, task managers, and the necessary CrewAI configurations.
"""

import os
import sys
import json
import logging
import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
import argparse

# Ensure src is in the path so imports work correctly
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Get the root directory
root_dir = os.path.dirname(parent_dir)

# Import server models 
from src.server.models.agent import CrewAIConfig, AgentModel, TaskModel, Process, CreateCrewRequest, AgentTool
from src.server.models.curried_proxy_info import CurriedProxyInfo, ToolInfo
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.task_runner import TaskRunner
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.message import Message
from src.server.tools.tools_catalog import tools_catalog
from src.server.tools.general_tools.datetime_tools import register_datetime_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class ToolType(str, Enum):
    """Type of tool."""
    OPENAPI_TOOL = "openapi_tool"
    PYTHON_FUNCTION = "python_function"
    CLASS_METHOD = "class_method"  
    CREWAI_TOOL = "crewai_tool"

def create_concert_travel_planner_state():
    """
    Create the concert travel planner specialized state.
    This function sets up all the necessary components for a functional concert travel planner.
    """
    logger.info("Creating Concert Travel Planner state...")
    
    # Initialize the persistence model
    persistence_model = PersistenceModelFactory().persistence_model()
    
    # 1. Create the task manager
    logger.info("Creating task manager...")
    manager_id = str(uuid4())
    manager = TasksManager(
        id=manager_id,
        name="Concert Travel Planner",
        description="Plan trips to concerts and music festivals",
        system_prompt="You are a helpful assistant specializing in concert and music festival planning."
    )
    persistence_model.tasksmanagers.create(manager)
    logger.info(f"Created task manager: {manager.name} (ID: {manager.id})")
    
    # 2. Create the CrewAI configuration
    logger.info("Creating CrewAI configuration...")
    
    # Create a curried proxy for tools and register the search tools
    proxy_id = str(uuid4())
    proxy = CurriedProxy(
        id=proxy_id,
        name="Concert Travel Planner Tools",
        description="Tools for the Concert Travel Planner"
    )
    
    # Create mock web search tools using a proper interface
    class MockSearchTool:
        """A mock of SerperDevTool that maintains the same interface."""
        
        def __init__(self, name):
            """Initialize the tool with the specified name."""
            self.name = name
            self.description = f"Search the web using {name}. Use parameter 'search_query' for your search."
            self.required_args = {"search_query": "str"}
            
            # Create a schema class similar to SerperDevToolSchema
            from pydantic import BaseModel, Field
            
            class MockSearchToolSchema(BaseModel):
                """Input schema for MockSearchTool."""
                search_query: str = Field(
                    ..., description="Mandatory search query you want to use to search the internet"
                )
            
            self.args_schema = MockSearchToolSchema
            
        async def __call__(self, **kwargs):
            """Search the web for information.
            
            Args:
                search_query: The search query to use
                
            Returns:
                str: Search results
            """
            search_query = kwargs.get('search_query', 'no query provided')
            return f"Mock search results for: {search_query}"
            
        def _run(self, search_query=None, **kwargs):
            """Run the tool synchronously.
            
            Args:
                search_query: The search query to use
                **kwargs: Additional keyword arguments
                
            Returns:
                str: Search results
            """
            # Get search_query from kwargs if not provided directly
            if search_query is None:
                search_query = kwargs.get("search_query", "no query provided")
            
            # Return the mock search result
            return f"Mock search results for: {search_query}"
            
    # Get the tools catalog
    from src.server.tools.tools_catalog import tools_catalog
    
    # Register the search tools directly with the tools catalog
    brave_search_tool = MockSearchTool("Brave Search")
    web_search_tool = MockSearchTool("Web Search")
    serper_tool = MockSearchTool("Serper.dev")
    
    # Register tools with both catalog and proxy
    tools_catalog.register_instance(brave_search_tool, "brave_search")
    tools_catalog.register_instance(web_search_tool, "web_search")
    tools_catalog.register_instance(serper_tool, "SerperDevTool")
    
    # Add tools to the proxy
    proxy.add_tool("brave_search", brave_search_tool)
    proxy.add_tool("web_search", web_search_tool)
    proxy.add_tool("SerperDevTool", serper_tool)
    
    # Store the allowed tools as a property of the crewai_config
    allowed_tools = ["brave_search", "web_search", "delegate", "datetime_tools"]
    
    # Register datetime tools
    datetime_tool_names = register_datetime_tools(tools_catalog)
    
    # Add datetime tools to proxy
    for tool_name in datetime_tool_names:
        if hasattr(tools_catalog, 'get_tool_instance'):
            tool_instance = tools_catalog.get_tool_instance(tool_name)
            if tool_instance:
                proxy.add_tool(tool_name, tool_instance)
    
    # Debug: Check what's in the tools catalog
    print("\n🔍 Verifying tools are correctly registered:")
    for tool_name in ["brave_search", "web_search", "datetime_tools"]:
        tool_metadata = tools_catalog.get_tool(tool_name)
        if tool_metadata:
            print(f"  ✅ {tool_name} found in tools_catalog")
            print(f"    Description: {tool_metadata.description}")
            print(f"    Parameters: {[p.name for p in tool_metadata.parameters] if tool_metadata.parameters else 'None'}")
            tool = tools_catalog.get_tool_instance(tool_name)
            print(f"    Has required_args: {hasattr(tool, 'required_args')}")
            if hasattr(tool, 'required_args'):
                print(f"    Required args: {tool.required_args}")
        else:
            print(f"  ❌ {tool_name} NOT found in tools_catalog")
            
    # Debug: Check what's in the CurriedProxy
    print("\n📦 Tools in CurriedProxy:")
    for tool_name in proxy.tool_names:
        print(f"  - {tool_name}")
        
    # DEBUG: Test exporting to CrewAI
    print("\n🔧 Testing export_to_crewai:")
    crewai_tools = proxy.export_to_crewai(allowed_tools=allowed_tools)
    print(f"🔢 Total CrewAI tools exported: {len(crewai_tools)}")
    for tool in crewai_tools:
        print(f"  - {tool.name}")
        if hasattr(tool, 'args_schema'):
            schema_json = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else 'No schema JSON method'
            print(f"    Args schema: {schema_json}")
            
            # Check if the schema is properly set up with search_query
            if hasattr(tool.args_schema, 'model_fields') and 'search_query' in tool.args_schema.model_fields:
                print(f"    ✅ Schema includes search_query parameter")
            else:
                print(f"    ❌ Schema missing search_query parameter")
            
            # Test direct execution of the tool with search_query
            try:
                result = tool._run(search_query="test query")
                print(f"    ✅ Tool execution test: {result[:50]}...")
            except Exception as e:
                print(f"    ❌ Tool execution test failed: {str(e)}")
    
    # Test SerperDevTool parameter handling issue
    print("\n🔍 Testing SerperDevTool parameter handling to diagnose issue:")
    # Create the SerperDevTool test instance
    serper_tool = MockSearchTool("SerperDevTool Test")
    
    # Test with proper parameter formatting
    try:
        result1 = serper_tool._run(search_query="test query")
        print(f"  ✅ Proper parameters work: {result1}")
    except Exception as e:
        print(f"  ❌ Proper parameters failed: {str(e)}")
    
    # Test with the incorrect parameter format (string instead of dict)
    try:
        result2 = serper_tool._run("search_query")
        print(f"  ⚠️ Incorrect parameters unexpectedly worked: {result2}")
    except Exception as e:
        print(f"  ✅ Incorrect parameters fail as expected: {str(e)}")
    
    # Test with empty parameters
    try:
        result3 = serper_tool._run()
        print(f"  ⚠️ Empty parameters unexpectedly worked: {result3}")
    except Exception as e:
        print(f"  ✅ Empty parameters fail as expected: {str(e)}")
    
    persistence_model.curried_proxies.create(proxy)
    logger.info(f"Created curried proxy with ID: {proxy.id}")
    
    # Define tools for the agents with explicit parameter instructions
    search_tool = AgentTool(
        name="SerperDevTool", 
        description="Search the web for information. Set the input parameter as: search_query"
    )
    
    brave_search_tool = AgentTool(
        name="brave_search",
        description="Search the web using Brave Search. Set the input parameter as: search_query"
    )
    
    web_search_tool = AgentTool(
        name="web_search",
        description="General web search capability. Set the input parameter as: search_query"
    )
    
    datetime_tool = AgentTool(
        name="datetime_tools",
        description="Get current date and time information"
    )
    
    # Define agent roles with explicit tool usage instructions
    concert_planner = AgentModel(
        role="Concert Planner",
        goal="Find the best concerts matching the user's preferences",
        backstory="You are an experienced concert finder with deep knowledge of venues, artists, and performances across the globe. You excel at matching people with perfect concert experiences based on their music preferences. IMPORTANT: When using search tools like brave_search, you must format your query as {\"search_query\": \"your search terms\"}. Always extract information about preferences directly from user messages.",
        tools=[brave_search_tool, web_search_tool, datetime_tool],
        verbose=True
    )
    
    travel_agent = AgentModel(
        role="Travel Agent",
        goal="Plan the best travel arrangements for concert attendees",
        backstory="You are a travel expert with years of experience planning trips around music events. You know the best ways to get to venues, where to stay, and how to make the trip smooth and enjoyable. IMPORTANT: When using search tools like brave_search, you must format your query as {\"search_query\": \"your search terms\"}. Always extract information about preferences directly from user messages.",
        tools=[brave_search_tool, web_search_tool, datetime_tool],
        verbose=True
    )
    
    local_expert = AgentModel(
        role="Local Expert",
        goal="Provide insider information about concert venues and local attractions",
        backstory="You have visited countless concert venues worldwide and know the best spots in each city. From where to get the best pre-show dinner to the perfect places to celebrate after the concert. IMPORTANT: When using search tools like brave_search, you must format your query as {\"search_query\": \"your search terms\"}. Always extract information about preferences directly from user messages.",
        tools=[brave_search_tool, web_search_tool, datetime_tool],
        verbose=True
    )
    
    # Define crew tasks with human input enabled
    concert_task = TaskModel(
        description="""Research concerts and music festivals that match the user's preferences in their chosen destination.

CRITICAL SYSTEM INSTRUCTIONS:
1. When using search tools like brave_search, ALWAYS format your parameters as: 
   {'search_query': 'your search terms', 'kwargs': {}}
2. NEVER pass just the string 'search_query' as a parameter.
3. Example correct usage: search({'search_query': 'upcoming concerts in Tokyo'})
4. Example INCORRECT usage: search('search_query') <- THIS WILL FAIL

The user is interested in traveling to see live music. Ask them where they're planning to travel and what type of music they enjoy. Then find upcoming concerts and festivals in that location that match their preferences. Include dates, venues, ticket prices, and featured artists where available.

Use datetime_tools to get the current date for relevant event searches.""",
        expected_output="A list of relevant concerts and music festivals at the user's chosen destination, with information about date, venue, price, and participating artists.",
        agent_role="Concert Planner",
        human_input=True
    )
    
    travel_task = TaskModel(
        description="""Create an optimal travel plan around the identified concerts or festivals.

CRITICAL SYSTEM INSTRUCTIONS:
1. When using search tools like brave_search, ALWAYS format your parameters as: 
   {'search_query': 'your search terms', 'kwargs': {}}  
2. NEVER pass just the string 'search_query' as a parameter value.
3. Example correct usage: search({'search_query': 'hotels near Madison Square Garden'})
4. Example INCORRECT usage: search('search_query') <- THIS WILL FAIL

First, gather essential information about the concert location and date from the Concert Planner. Then, plan the ideal travel experience including:
- Transportation options to the destination (flights, trains, etc.)
- Local transportation in the area
- Accommodation recommendations near the venue
- Pre and post-concert activities that complement the music experience

Consider the traveler's preferences and budget when making recommendations.

Use datetime_tools to reference current dates when scheduling travel.""",
        expected_output="A detailed travel plan with dates, transportation, and accommodations",
        agent_role="Travel Agent",
        human_input=True
    )
    
    local_task = TaskModel(
        description="""Provide insider information about concert venues and local music scenes.

CRITICAL SYSTEM INSTRUCTIONS:
1. When using search tools like brave_search, ALWAYS format your parameters as: 
   {'search_query': 'your search terms', 'kwargs': {}}
2. NEVER pass just the string 'search_query' as a parameter.
3. Example correct usage: search({'search_query': 'best seats at Radio City Music Hall'})
4. Example INCORRECT usage: search('search_query') <- THIS WILL FAIL

Based on the concert or festival selected by the user, provide insider tips such as:
- The best seating areas or viewing spots at the venue
- Pre-show or after-party locations frequented by locals
- Local transportation advice for getting to/from the venue
- Safety tips for the area around the venue
- Local food recommendations near the venue
- Special venue policies or customs to be aware of

Your advice should help the traveler experience the event like a local music fan rather than a tourist.

Use datetime_tools to check if specific recommendations are relevant based on current date and concert timing.""",
        expected_output="Detailed venue information and local recommendations",
        agent_role="Local Expert",
        human_input=True
    )
    
    # Create the crew request
    create_crew = CreateCrewRequest(
        description="A crew specializing in planning concert trips",
        process=Process.sequential,
        agents=[concert_planner, travel_agent, local_expert],
        tasks=[concert_task, travel_task, local_task],
        allowed_tools=allowed_tools
    )
    
    # Create the crew configuration
    crewai_config_id = str(uuid4())
    crewai_config = CrewAIConfig(
        id=crewai_config_id,
        create_crew=create_crew,
        process=Process.sequential,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    persistence_model.crewai_config.create(crewai_config)
    logger.info(f"Created CrewAI config: {crewai_config_id}")
    
    # 3. Create the concert planning tasks
    logger.info("Creating concert planning tasks...")
    
    # Task 1: Plan Concert Trip
    plan_task_id = str(uuid4())
    plan_task = Task(
        id=plan_task_id,
        name="Plan Concert Trip",
        description="Plan a complete trip to a concert, including travel, accommodation, and activities",
        tasksmanager_id=manager_id,
        framework="crewai",
        crewai_config_id=crewai_config_id,
        curried_proxy_id=str(proxy.id),
            messages=[
                Message(
                    role="system",
                content="""You are a Concert Trip Planner with a team of specialized agents.

Your job is to coordinate a crew of specialized agents to plan a comprehensive concert trip based on user preferences.

Your crew consists of:
1. Concert Planner - Finds the best concerts matching user preferences
2. Travel Agent - Plans travel arrangements and accommodations
3. Local Expert - Provides insider information about venues and attractions

CRITICAL INSTRUCTION: When using search tools like brave_search, you MUST use the exact format: {"search_query": "your search here"} - using the string "search_query" will cause errors.
IMPORTANT: Extract information directly from user messages rather than asking them to provide it separately.
IMPORTANT: If you need additional information, ask the user directly instead of delegating to a non-existent role.
IMPORTANT: When asked for human input, provide explicit options or suggestions to help the user respond.

Follow a structured approach:
1. First, understand the user's concert preferences (genres, artists, locations, dates) from their messages
2. Use web search tools to search for suitable concerts and festivals using format {"search_query": "rock concerts in New York August 2025"}
3. Use web search to gather transportation and accommodation options based on concert dates
4. Use web search to find information about venues and local attractions
5. Compile all information into a comprehensive trip plan
6. Present the plan in a clear, organized format

Provide a complete concert trip plan with:
- Concert/festival details (venue, date, lineup)
- Travel arrangements (transportation options, costs)
- Accommodation suggestions (hotels, alternatives)
- Local recommendations (restaurants, attractions, activities)
- Practical tips (venue info, local customs, weather considerations)

Use datetime_tools to reference current dates and ensure recommendations are timely.

Always be enthusiastic about the music and travel experiences!"""
            )
        ],
        status="pending"
    )
    persistence_model.tasks.create(plan_task)
    logger.info(f"Created task: {plan_task.name} (ID: {plan_task.id})")
    
    # Task 2: Search for Specific Concerts
    search_task_id = str(uuid4())
    search_task = Task(
        id=search_task_id,
        name="Search for Specific Concerts",
        description="Find concerts and performances by specific artists or in specific locations",
        tasksmanager_id=manager_id,
        framework="crewai",
        crewai_config_id=crewai_config_id,
        curried_proxy_id=str(proxy.id),
        messages=[
            Message(
                role="system",
                content="""You are a Concert Search Specialist with a team of specialized agents.

Your job is to find specific concerts based on user criteria using your specialized crew.

Your crew consists of:
1. Concert Planner - Finds concerts matching specific criteria (artist, venue, date)
2. Travel Agent - Provides transportation information to/from venues
3. Local Expert - Offers venue-specific information and tips

CRITICAL INSTRUCTION: When using search tools like brave_search, you MUST use the exact format: {"search_query": "your search here"} - using the string "search_query" will cause errors.
IMPORTANT: Extract information directly from user messages rather than asking them to provide it separately.
IMPORTANT: If you need additional information, ask the user directly instead of delegating to a non-existent role.
IMPORTANT: When asked for human input, provide explicit options or suggestions to help the user respond.

Follow a structured approach:
1. First, understand exactly what concerts the user is looking for (specific artist, genre, location, timeframe)
2. Use web search tools to find matching concerts and provide details using format {"search_query": "taylor swift concerts boston 2025"}
3. For each potential concert, search for transportation information
4. Search for venue information and nearby amenities
5. Compile all information into a detailed list of options
6. Present findings in a clear, organized format with all relevant details

Use datetime_tools to get the current date and find timely concerts.

Provide comprehensive concert search results with:
- Concert details (artist, date, venue, ticket prices)
- Venue information (capacity, seating options, acoustics)
- Transportation options to/from the venue
- Nearby accommodations and places to eat
- Any special considerations (parking, security, etc.)

Be thorough and provide as many matches as possible to the user's criteria!"""
            )
        ],
        status="pending"
    )
    persistence_model.tasks.create(search_task)
    logger.info(f"Created task: {search_task.name} (ID: {search_task.id})")
    
    # Task 3: Recommend Music Festivals
    recommend_task_id = str(uuid4())
    recommend_task = Task(
        id=recommend_task_id,
        name="Recommend Music Festivals",
        description="Get personalized music festival recommendations based on preferences",
        tasksmanager_id=manager_id,
        framework="crewai",
        crewai_config_id=crewai_config_id,
        curried_proxy_id=str(proxy.id),
        messages=[
            Message(
                role="system",
                content="""You are a Music Festival Specialist with a team of specialized agents.

Your job is to recommend music festivals based on user preferences using your crew of experts.

Your crew consists of:
1. Concert Planner - Researches festivals matching user preferences
2. Travel Agent - Provides logistical information about festival travel
3. Local Expert - Offers insider knowledge about festival locations

CRITICAL INSTRUCTION: When using search tools like brave_search, you MUST use the exact format: {"search_query": "your search here"} - using the string "search_query" will cause errors.
IMPORTANT: Extract information directly from user messages rather than asking them to provide it separately.
IMPORTANT: If you need additional information, ask the user directly instead of delegating to a non-existent role.
IMPORTANT: When asked for human input, provide explicit options or suggestions to help the user respond.

Follow a structured approach:
1. First, understand the user's festival preferences (music genres, location preferences, timing, budget)
2. Use web search tools to identify suitable music festivals using format {"search_query": "rock music festivals new york august 2025"}
3. Search for travel requirements and accommodations
4. Search for inside information about each festival experience
5. Compile recommendations into a comprehensive guide
6. Present recommendations in an organized, engaging format

Use datetime_tools to get current dates and recommend timely festivals.

Provide comprehensive festival recommendations with:
- Festival details (name, dates, location, typical lineup style)
- Travel considerations (how to get there, best transportation options)
- Accommodation options (camping, hotels, alternatives)
- Festival experience (size, vibe, unique features, stages)
- Practical tips (what to bring, weather considerations, festival hacks)

Be enthusiastic and help the user find their perfect festival experience!"""
            )
        ],
        status="pending"
    )
    persistence_model.tasks.create(recommend_task)
    logger.info(f"Created task: {recommend_task.name} (ID: {recommend_task.id})")
    
    # 4. Save the state to a file
    logger.info("Saving state to file...")
    state_location = StorageLocation(
        type=StorageType.file,
        location=os.path.join(root_dir, "state"),
        state_name="concert_travel_planner_state.json"
    )
    
    # Get the state from the persistence model
    state = {
        "toolsets": {},
        "tools": {},
        "tasksmanagers": {manager.id: manager},
        "tasks": {
            plan_task.id: plan_task,
            search_task.id: search_task,
            recommend_task.id: recommend_task
        },
        "messages": {},
        "crewai_config": {crewai_config.id: crewai_config},
        "curried_proxies": {str(proxy.id): proxy},
        "task_flows": {}
    }
    
    # Save state using our custom function
    result = save_state_to_disk(state_location, state, logger)
    logger.info(f"State saved: {result}")
    
    # 5. Create metadata file
    logger.info("Creating metadata...")
    metadata = {
        "last_used_state": "concert_travel_planner_state",
        "last_task_manager_id": manager_id,
        "last_task_id": recommend_task_id,
        "crewai_config_id": crewai_config_id,
        "curried_proxy_id": str(proxy.id),
        "state_file": "state/concert_travel_planner_state.json"
    }
    
    # Ensure state directory exists
    os.makedirs(os.path.join(root_dir, "state"), exist_ok=True)
    
    # Save metadata
    with open(os.path.join(root_dir, "state", "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Concert Travel Planner state created successfully!")
    return {
        "manager_id": manager_id,
        "tasks": [
            {"id": plan_task_id, "name": plan_task.name},
            {"id": search_task_id, "name": search_task.name},
            {"id": recommend_task_id, "name": recommend_task.name}
        ],
        "crewai_config_id": crewai_config_id,
        "curried_proxy_id": proxy.id,
        "state_file": "state/concert_travel_planner_state.json"
    }

def save_state_to_disk(storage_location, state, logger=None):
    """Save the state to disk as a JSON file."""
    try:
        location_dir = storage_location.location
        
        # Create directory if it doesn't exist
        os.makedirs(location_dir, exist_ok=True)
        
        # Combine location and state name
        file_path = os.path.join(location_dir, storage_location.state_name)
        
        # Clean state to ensure proper serialization
        cleaned_state = {}
        for key, value in state.items():
            if key in ["tasksmanagers", "tasks", "crewai_config", "curried_proxies"]:
                cleaned_state[key] = {}
                for item_id, item in value.items():
                    # Ensure keys are strings to avoid JSON serialization issues
                    str_id = str(item_id)
                    
                    # Handle Pydantic models properly
                    if hasattr(item, 'model_dump'):
                        cleaned_state[key][str_id] = item.model_dump()
                    elif hasattr(item, 'dict'):
                        cleaned_state[key][str_id] = item.dict()
                    else:
                        # For non-Pydantic objects, use the encoder
                        cleaned_state[key][str_id] = json_encoder(item)
            else:
                cleaned_state[key] = value
        
        # Add debug logging
        if logger:
            logger.debug(f"Serializing {len(cleaned_state)} top-level keys")
            for k in cleaned_state.keys():
                logger.debug(f"Key: {k}, Type: {type(cleaned_state[k])}")
        
        # Convert state to JSON and write to file
        with open(file_path, 'w') as f:
            # Use custom encoder to handle special types
            json_string = json.dumps(cleaned_state, default=json_encoder, indent=2)
            
            # Verify the JSON is valid before writing
            try:
                # Parse the JSON string to validate it
                json.loads(json_string)
                # Write the validated JSON
                f.write(json_string)
            except json.JSONDecodeError as e:
                if logger:
                    logger.error(f"Generated invalid JSON: {str(e)}")
                    logger.error(f"Error context: {json_string[max(0, e.pos-50):min(len(json_string), e.pos+50)]}")
                else:
                    print(f"  Error: Generated invalid JSON: {str(e)}")
                    print(f"  Error context: {json_string[max(0, e.pos-50):min(len(json_string), e.pos+50)]}")
                raise
            
        # Print confirmation with full path
        if logger:
            logger.info(f"State saved to {os.path.abspath(file_path)}")
        else:
            print(f"  Save result: State saved to {os.path.abspath(file_path)}")
            
        return file_path
    except Exception as e:
        if logger:
            logger.error(f"Error saving state: {str(e)}")
        else:
            print(f"  Error saving state: {str(e)}")
        return None

def json_encoder(obj):
    """Handle serialization of special types with focus on Pydantic models."""
    try:
        # Handle None values
        if obj is None:
            return None
            
        # Handle basic types that are JSON-serializable
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
            
        # Handle UUID objects
        if isinstance(obj, UUID):
            return str(obj)
            
        # Handle datetime objects
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
            
        # Handle lists and tuples recursively
        if isinstance(obj, (list, tuple)):
            return [json_encoder(item) for item in obj]
            
        # Handle dictionaries recursively
        if isinstance(obj, dict):
            return {str(k): json_encoder(v) for k, v in obj.items()}
            
        # Handle Pydantic V2 models - preferred method
        if hasattr(obj, 'model_dump_json'):
            try:
                # First try model_dump_json which handles serialization properly
                return json.loads(obj.model_dump_json())
            except Exception as e:
                # Fall back to model_dump if json method fails
                try:
                    return json_encoder(obj.model_dump())
                except Exception as e2:
                    return f"<Error serializing Pydantic model: {str(e2)}>"
                
        # Alternative for Pydantic V2 models
        elif hasattr(obj, 'model_dump'):
            try:
                return json_encoder(obj.model_dump())
            except Exception as e:
                return f"<Error serializing model_dump: {str(e)}>"
                
        # Handle Pydantic V1 models
        elif hasattr(obj, 'json') and callable(obj.json):
            try:
                return json.loads(obj.json())
            except Exception as e:
                try:
                    return json_encoder(obj.dict())
                except Exception as e2:
                    return f"<Error serializing Pydantic V1 model: {str(e2)}>"
                
        # Fallback for Pydantic V1 models
        elif hasattr(obj, 'dict') and callable(obj.dict):
            try:
                return json_encoder(obj.dict())
            except Exception as e:
                return f"<Error serializing dict: {str(e)}>"
                
        # Handle objects with to_dict method
        elif hasattr(obj, 'to_dict') and callable(obj.to_dict):
            try:
                return json_encoder(obj.to_dict())
            except Exception as e:
                return f"<Error serializing to_dict: {str(e)}>"
                
        # Handle general objects with a __dict__
        elif hasattr(obj, '__dict__'):
            try:
                # Create a clean dictionary without private attributes
                result = {}
                for key, value in obj.__dict__.items():
                    # Skip private attributes
                    if isinstance(key, str) and not key.startswith('_'):
                        # Ensure keys are strings
                        str_key = str(key)
                        # Recursively encode values
                        result[str_key] = json_encoder(value)
                return result
            except Exception as e:
                return f"<Error serializing __dict__: {str(e)}>"
                
        # For other types, convert to string safely
        return str(obj)
    except Exception as e:
        # Fallback for any serialization errors
        return f"<Error during serialization: {str(e)}>"

def test_serialization_deserialization(state_data, state_location):
    """Test the serialization and deserialization process.
    
    This function will:
    1. Save the state to disk
    2. Load it back to verify deserialization works
    3. Report any issues found
    """
    print("\n🧪 Testing serialization and deserialization cycle...")
    
    # 1. Save the state to disk
    file_path = save_state_to_disk(state_location, state_data)
    if not file_path:
        print("❌ Failed to save state to disk")
        return False
    
    print(f"✅ State saved to {file_path}")
    
    # 2. Load it back to verify deserialization works
    try:
        print(f"🔄 Loading state from {file_path}")
        with open(file_path, 'r') as f:
            json_str = f.read()
        
        # Test basic JSON parsing
        print("🔍 Testing basic JSON parsing...")
        loaded_data = json.loads(json_str)
        print(f"✅ Basic JSON parsing successful, loaded {len(loaded_data)} top-level keys")
        
        # 3. Now test loading with the actual model code
        print("🔍 Testing model deserialization...")
        
        # Import the PersistenceModel here to avoid circular imports
        from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
        test_model = InMemoryPersistenceModel()
        
        # Test the from_json method directly
        print("🔍 Testing from_json method...")
        try:
            test_model.from_json(json_str)
            print("✅ Model deserialization successful!")
            return True
        except Exception as e:
            print(f"❌ Model deserialization failed: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            
            # Special handling for the unhashable slice error
            if "unhashable type: 'slice'" in str(e):
                print("\n🔎 Detected 'unhashable type: slice' error - this usually occurs when:")
                print("  - A dictionary is passed to json.loads() instead of a string")
                print("  - The error handling code attempts to print a slice of the data")
                
                # Check the specific case in in_memory_crud.py
                print("\n🔧 Recommended fix:")
                print("  Check in_memory_crud.py's from_json method, to handle the case where data is already a dictionary")
                print("  Add a check like: if isinstance(data, dict): return data")
            
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Concert Travel Planner State Generator')
    parser.add_argument('--test-serialization', action='store_true',
                        help='Test serialization and deserialization cycle')
    args = parser.parse_args()
    
    # Regular execution - create the state
    result = create_concert_travel_planner_state()
    
    print("\nConcert Travel Planner State Created:")
    print(f"Task Manager ID: {result['manager_id']}")
    print("Tasks:")
    for task in result["tasks"]:
        print(f"  - {task['name']} (ID: {task['id']})")
    print(f"CrewAI Config ID: {result['crewai_config_id']}")
    print(f"Curried Proxy ID: {result['curried_proxy_id']}")
    print(f"State File: {result['state_file']}")
    
    # If test flag is set, run the serialization test
    if args.test_serialization:
        # Get the state from the persistence model
        persistence_model = PersistenceModelFactory().persistence_model()
        
        # Get the state data (similar to what's in create_concert_travel_planner_state)
        manager = persistence_model.tasksmanagers.read(result['manager_id'])
        
        # Reconstruct the state data
        state = {
            "toolsets": {},
            "tools": {},
            "tasksmanagers": {manager.id: manager},
            "tasks": {},
            "messages": {},
            "crewai_config": {},
            "curried_proxies": {},
            "task_flows": {}
        }
        
        # Add the tasks
        for task_info in result["tasks"]:
            task_id = task_info["id"]
            task = persistence_model.tasks.read(task_id)
            if task:
                state["tasks"][task_id] = task
        
        # Add the crewai_config
        crewai_config = persistence_model.crewai_config.read(result["crewai_config_id"])
        if crewai_config:
            state["crewai_config"][result["crewai_config_id"]] = crewai_config
        
        # Add the curried_proxy
        curried_proxy = persistence_model.curried_proxies.read(result["curried_proxy_id"])
        if curried_proxy:
            state["curried_proxies"][result["curried_proxy_id"]] = curried_proxy
        
        # Create the state location
        state_location = StorageLocation(
            type=StorageType.file,
            location=os.path.join(root_dir, "state"),
            state_name="concert_travel_planner_test_state.json"
        )
        
        # Run the test
        test_result = test_serialization_deserialization(state, state_location)
        
        if test_result:
            print("\n✅ Serialization and deserialization test passed!")
        else:
            print("\n❌ Serialization and deserialization test failed!")
    
    print("\nYou can now use the Concert Travel Planner state!") 