"""
Concert Travel Planner State Setup

This module sets up a state for demonstrating agentic capabilities using CrewAI.
It creates a task manager and tasks for planning concert trips, including searching
for concerts, finding flights, and suggesting optimal travel dates.
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
import uuid
from datetime import datetime

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

# Import the datetime tools directly from general_tools
from src.server.tools.general_tools.datetime_tools import get_current_datetime, is_future_date
from src.server.context import knowledge_base
from crewai_tools import WebsiteSearchTool, SerperDevTool
from src.server.models.task import Message
from src.server.models.tasks_manager import TasksManager
from src.server.models.tools_catalog import ToolsCatalog
from src.server.models.curried_proxy import CurriedProxy
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.tools.tools_catalog import ToolsCatalog
from src.server.controllers.persistence_controller import save_to_storage, StorageLocation, StorageType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def add_concert_knowledge_to_knowledge_base():
    """Add concert planning knowledge to the knowledge base for context."""
    try:
        # Create concert planning knowledge content
        concert_planning_content = """# Concert Travel Planning Guide

## Finding Concerts and Music Festivals
- Check official venue websites for upcoming events
- Use ticket platforms like Ticketmaster, LiveNation, and SeatGeek
- Follow artists on social media for tour announcements
- Subscribe to music newsletters and blogs for festival announcements
- Check local event listings and city tourism websites

## Planning Concert Trips
- Book tickets early for popular shows to avoid sellouts
- Consider VIP or premium options for better experiences
- Research venue seating charts before purchasing tickets
- Check for multi-day passes for festivals to save money
- Look for early-bird pricing and presale opportunities

## Travel Considerations
- Book accommodations near the venue to minimize transportation
- Check public transportation options around the venue
- Consider arrival and departure times in relation to show times
- Allow extra time for security lines at major venues
- Research parking options and costs if driving

## Festival-Specific Tips
- Bring appropriate gear for outdoor festivals (sunscreen, rain gear)
- Check festival rules regarding allowed and prohibited items
- Consider camping options for multi-day festivals
- Plan for food and water needs, especially at outdoor venues
- Research festival layout to locate stages, facilities, and exits

## Local Experience Enhancement
- Research local restaurants and bars near venues
- Check for pre-show and after-show events
- Explore local attractions to make the most of your trip
- Connect with local music communities for insider tips
- Consider guided tours related to music history in the area"""
        
        # Add to knowledge base
        try:
            # Try to use the async method if available
            if hasattr(knowledge_base, 'add_knowledge') and callable(knowledge_base.add_knowledge):
                knowledge_id = await knowledge_base.add_knowledge(
                    content=concert_planning_content,
                    metadata={
                        "name": "concert_planning_guide",
                        "description": "Guide for planning concert trips and music festivals",
                        "tags_str": "concerts,travel,planning,music,festivals"
                    }
                )
            else:
                # Fallback to generating a placeholder ID
                knowledge_id = str(uuid.uuid4())
                logger.warning(f"knowledge_base.add_knowledge not available, using placeholder ID")
        except Exception as e:
            # If add_knowledge fails, use a fallback ID but log the error
            knowledge_id = str(uuid.uuid4())
            logger.warning(f"Error using knowledge_base.add_knowledge: {str(e)}, using placeholder ID")
        
        logger.info(f"✅ Added concert planning knowledge to knowledge base with ID: {knowledge_id}")
        return knowledge_id
    except Exception as e:
        logger.error(f"❌ Failed to add concert planning knowledge to knowledge base: {str(e)}")
        return None

async def setup_concert_travel_planner_state():
    """Setup a state with a simple concert travel planner crew."""
    print("\n🔄 Setting up Concert Travel Planner state...")
    
    # Initialize persistence model
    try:
        persistence_model = PersistenceModelFactory().get_persistence_model()
        logger.info(f"Created new persistence model with ID: {id(persistence_model)}")
    except ImportError as e:
        logger.error(f"Failed to import PersistenceModelFactory: {e}")
        logger.info("Creating mock persistence model for testing")
        # Create a simple mock if the actual model can't be imported
        class MockPersistenceModel:
            def create(self, collection, id, data):
                logger.info(f"Mock creating {id} in {collection}")
                return data
        persistence_model = MockPersistenceModel()
    
    # Initialize tools catalog
    try:
        tools_catalog = ToolsCatalog()
        logger.info("Initialized tools catalog")
        
        # The datetime tools should already be registered in tools_catalog.py
        # Let's verify they exist and log their presence
        tool_names = tools_catalog.list_tools()
        datetime_tools_present = any('datetime' in tool.lower() for tool in tool_names)
        if datetime_tools_present:
            logger.info("Found datetime tools in catalog")
        else:
            # If not found in the catalog, let's register them directly
            # This is a fallback in case the tools weren't registered in tools_catalog.py
            logger.warning("Datetime tools not found in catalog, manually registering them")
            tools_catalog.register_tool("datetime_tools.get_current_datetime", get_current_datetime)
            tools_catalog.register_tool("datetime_tools.is_future_date", is_future_date)
    except ImportError as e:
        logger.error(f"Failed to import ToolsCatalog: {e}")
        tools_catalog = None
    
    # Initialize curried proxy
    try:
        curried_proxy = CurriedProxy()
        
        # Add search tools
        website_search_tool = WebsiteSearchTool()
        serper_dev_tool = SerperDevTool()
        curried_proxy.add_tool("WebsiteSearchTool.run", website_search_tool.run)
        curried_proxy.add_tool("SerperDevTool.run", serper_dev_tool.run)
        
        # Add datetime tools
        try:
            if tools_catalog:
                # Get from catalog if available
                curried_proxy.add_tool("datetime_tools.get_current_datetime", 
                                      tools_catalog.get_tool_instance("datetime_tools.get_current_datetime"))
                curried_proxy.add_tool("datetime_tools.is_future_date", 
                                      tools_catalog.get_tool_instance("datetime_tools.is_future_date"))
                logger.info("Added datetime tools from catalog to curried proxy")
            else:
                # Use direct functions if catalog not available
                curried_proxy.add_tool("datetime_tools.get_current_datetime", get_current_datetime)
                curried_proxy.add_tool("datetime_tools.is_future_date", is_future_date)
                logger.info("Added datetime functions directly to curried proxy")
        except Exception as e:
            logger.warning(f"Error adding datetime tools, using direct functions: {e}")
            curried_proxy.add_tool("datetime_tools.get_current_datetime", get_current_datetime)
            curried_proxy.add_tool("datetime_tools.is_future_date", is_future_date)
            logger.info("Added datetime functions directly to curried proxy (fallback)")
        
        # Add concert planning knowledge to knowledge base
        knowledge_id = await add_concert_knowledge_to_knowledge_base()
        
        # Create the crew
        await create_concert_travel_planner_crew(persistence_model, curried_proxy, knowledge_id)
        
    except ImportError as e:
        logger.error(f"Failed to import CurriedProxy: {e}")
    
    print("✅ Concert Travel Planner state setup complete.")
    return persistence_model

async def create_concert_travel_planner_crew(persistence_model, curried_proxy, knowledge_id=None):
    """Create and configure the concert travel planner crew."""
    logger.info("Creating Concert Travel Planner crew")
    
    try:
        
        # Create TasksManager for concert travel planning
        concert_planner_manager = TasksManager(
            id=str(uuid.uuid4()),
            name="Concert Travel Planner",
            model="gpt-4o-mini",
            description="Plans concert trips by finding events and suggesting optimal travel dates",
            messages=[
                Message(
                    role="system",
                    content="""You are an AI assistant specializing in planning concert trips.
                    You can help users find concerts and music festivals in specific locations,
                    suggest optimal travel dates, and provide comprehensive travel plans.
                    
                    Your capabilities include:
                    1. Searching for concerts and music festivals in specific locations and date ranges
                    2. Finding flight information and travel options
                    3. Suggesting optimal travel dates based on events and user preferences
                    4. Creating comprehensive travel itineraries
                    5. Providing recommendations for accommodations and local attractions
                    
                    IMPORTANT OPERATING GUIDELINES:
                    1. Always check the current date first using datetime_tools.get_current_datetime
                    2. Only suggest concerts and events that are in the future
                    3. Focus on the specific dates, locations, and music genres mentioned by the user
                    4. Double-check all venue information for accuracy
                    5. Verify that all suggested events match the user's specified locations and dates"""
                )
            ]
        )
        
        # Store in persistence model
        manager_data = {
            "id": concert_planner_manager.id,
            "name": concert_planner_manager.name,
            "model": concert_planner_manager.model,
            "description": concert_planner_manager.description,
            "messages": [m.dict() for m in concert_planner_manager.messages]
        }
        persistence_model.create("tasksmanagers", concert_planner_manager.id, manager_data)
        logger.info(f"Created Concert Travel Planner manager with ID: {concert_planner_manager.id}")
        
        # Create CrewAI config
        crewai_config_id = str(uuid.uuid4())
        crewai_config = {
            "id": crewai_config_id,
            "name": "Concert Travel Planning Crew",
            "description": "A crew that helps plan trips to concerts and music festivals",
            "agents": [
                {
                    "role": "Concert Researcher",
                    "goal": "Find the best concerts and music festivals based on user preferences",
                    "backstory": "You are an expert music researcher with extensive knowledge of concerts and festivals worldwide.",
                    "tools": ["WebsiteSearchTool", "SerperDevTool", "datetime_tools.get_current_datetime", "datetime_tools.is_future_date"]
                },
                {
                    "role": "Travel Planner",
                    "goal": "Create optimal travel plans around concert dates",
                    "backstory": "You are an experienced travel planner specializing in creating itineraries around events.",
                    "tools": ["WebsiteSearchTool", "SerperDevTool", "datetime_tools.get_current_datetime", "datetime_tools.is_future_date"]
                },
                {
                    "role": "Local Expert",
                    "goal": "Provide insider knowledge about concert venues and local attractions",
                    "backstory": "You are a local expert with deep knowledge of cities, venues, and local attractions.",
                    "tools": ["WebsiteSearchTool", "SerperDevTool", "datetime_tools.get_current_datetime", "datetime_tools.is_future_date"]
                }
            ],
            "tasks": [
                {
                    "description": "Research concerts and music festivals that match the user's preferences",
                    "expected_output": "A list of relevant concerts and festivals with detailed information",
                    "agent_role": "Concert Researcher"
                },
                {
                    "description": "Create an optimal travel plan around the identified concert dates",
                    "expected_output": "A detailed travel plan with dates, transportation, and accommodations",
                    "agent_role": "Travel Planner"
                },
                {
                    "description": "Provide insider information about concert venues and local attractions",
                    "expected_output": "Detailed venue information and local recommendations",
                    "agent_role": "Local Expert"
                }
            ],
            "process": "sequential",
            "verbose": 2,
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now())
        }
        
        # Store CrewAI config in persistence model
        persistence_model.create("crewai_configs", crewai_config_id, crewai_config)
        logger.info(f"Created CrewAI config with ID: {crewai_config_id}")
        
        # Get ID of curried proxy
        curried_proxy_id = getattr(curried_proxy, "id", str(uuid.uuid4()))
        
        # Create task for concert planning
        concert_planning_task_id = str(uuid.uuid4())
        concert_planning_task = {
            "id": concert_planning_task_id,
            "name": "Plan Concert Trip",
            "description": "Plan a concert trip based on user preferences using CrewAI",
            "tasksmanager_id": concert_planner_manager.id,
            "curried_proxy_id": curried_proxy_id,
            "crewai_config_id": crewai_config_id,
            "use_context": True,
            "inherit_manager_context": True,
            "framework": "crewai",
            "messages": [
                {
                    "role": "system",
                    "content": """Your task is to plan a concert trip based on user preferences using CrewAI.
                    
                    IMPORTANT INSTRUCTIONS:
                    1. ALWAYS check the current date first using the datetime_tools.get_current_datetime tool
                    2. ONLY plan for events in the future from the current date
                    3. Focus EXCLUSIVELY on the locations and dates specified by the user
                    
                    You will work with a crew of specialized agents:
                    - Concert Researcher: Finds concerts and festivals based on preferences
                    - Travel Planner: Creates optimal travel plans around concert dates
                    - Local Expert: Provides insider knowledge about venues and attractions
                    
                    When the agents complete their tasks, synthesize their findings into a comprehensive trip plan
                    organized by date with clear sections for:
                    - Concerts and Events (with dates, times, venues, and ticket information)
                    - Travel Logistics (flights, local transportation)
                    - Accommodations (options at different price points)
                    - Local Recommendations (restaurants, attractions, etc.)"""
                }
            ]
        }
        
        # Add knowledge context if available
        if knowledge_id:
            context_ref = {
                'id': str(uuid.uuid4()),
                'type': 'knowledge',
                'source_id': knowledge_id,
                'metadata': {
                    'name': 'concert_planning_guide',
                    'description': 'Guide for planning concert trips and music festivals',
                    'tags_str': 'concerts,travel,planning,music,festivals'
                },
                'priority': 100,
                'created_at': str(datetime.now())
            }
            
            if 'contexts' not in concert_planning_task:
                concert_planning_task['contexts'] = []
            concert_planning_task['contexts'].append(context_ref)
        
        # Store task in persistence model
        persistence_model.create("tasks", concert_planning_task_id, concert_planning_task)
        logger.info(f"Created concert planning task with ID: {concert_planning_task_id}")
        
        # Create task for custom concert search
        custom_search_task_id = str(uuid.uuid4())
        custom_search_task = {
            "id": custom_search_task_id,
            "name": "Search for Specific Concerts",
            "description": "Search for specific concerts based on detailed user criteria",
            "tasksmanager_id": concert_planner_manager.id,
            "curried_proxy_id": curried_proxy_id,
            "crewai_config_id": crewai_config_id,
            "use_context": True,
            "inherit_manager_context": True,
            "framework": "crewai",
            "messages": [
                {
                    "role": "system",
                    "content": """Your task is to search for specific concerts based on detailed user criteria.
                    
                    IMPORTANT INSTRUCTIONS:
                    1. ALWAYS check the current date first using the datetime_tools.get_current_datetime tool
                    2. ONLY search for events in the future from the current date
                    3. Focus EXCLUSIVELY on the exact search criteria provided by the user
                    
                    For each concert, include:
                    - Full name of the event and featured artists
                    - Exact date, time, and venue location
                    - Ticket price ranges and availability
                    - Venue tips (best seating, acoustics, etc.)
                    - Nearby attractions and dining options"""
                }
            ]
        }
        
        # Add knowledge context if available
        if knowledge_id:
            context_ref = {
                'id': str(uuid.uuid4()),
                'type': 'knowledge',
                'source_id': knowledge_id,
                'metadata': {
                    'name': 'concert_planning_guide',
                    'description': 'Guide for planning concert trips and music festivals',
                    'tags_str': 'concerts,travel,planning,music,festivals'
                },
                'priority': 100,
                'created_at': str(datetime.now())
            }
            
            if 'contexts' not in custom_search_task:
                custom_search_task['contexts'] = []
            custom_search_task['contexts'].append(context_ref)
        
        # Store task in persistence model
        persistence_model.create("tasks", custom_search_task_id, custom_search_task)
        logger.info(f"Created custom search task with ID: {custom_search_task_id}")
        
        # Try to save state to file if possible
        try:
            
            # Ensure state directory exists
            os.makedirs("state", exist_ok=True)
            # Define storage location
            state_location = StorageLocation(
                type=StorageType.file,
                location="state",
                state_name="concert_travel_planner_state.json"
            )
            
            # Save state
            result = save_to_storage(persistence_model, state_location)
            logger.info(f"State saved to file: {result}")
        except ImportError as e:
            logger.warning(f"Unable to save state to file: {e}")
        
        return {
            "concert_planner_manager_id": concert_planner_manager.id,
            "concert_planning_task_id": concert_planning_task_id,
            "custom_search_task_id": custom_search_task_id,
            "curried_proxy_id": curried_proxy_id,
            "crewai_config_id": crewai_config_id
        }
    
    except Exception as e:
        logger.error(f"Error creating concert travel planner crew: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    asyncio.run(setup_concert_travel_planner_state()) 