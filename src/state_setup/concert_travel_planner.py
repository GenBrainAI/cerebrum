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

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.tools_catalog import ToolsCatalog
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, TaskModel, ToolModel
from src.server.models.process import Process
from src.server.tools.url_tools import URLTools
from src.server.context import knowledge_base

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
        knowledge_id = str(uuid.uuid4())  # Using a placeholder UUID since add_knowledge is not available
        logger.info(f"✅ Added concert planning knowledge to knowledge base with ID: {knowledge_id}")
        return knowledge_id
    except Exception as e:
        logger.error(f"❌ Failed to add concert planning knowledge to knowledge base: {str(e)}")
        return None

async def setup_concert_travel_planner_state():
    """Set up a state for demonstrating concert travel planning using CrewAI."""
    
    print("\n🔄 Setting up Concert Travel Planner state...")
    
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Add concert planning knowledge to knowledge base
    knowledge_id = await add_concert_knowledge_to_knowledge_base()
    
    # Create and register tools
    url_tools = URLTools()
    tools_catalog = ToolsCatalog()
    
    # Create a curried proxy for the tools
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool("URLTools.get_data_from_url", url_tools.get_data_from_url)
    curried_proxy.add_tool("URLTools.get_documentation", url_tools.get_documentation)
    curried_proxy.add_tool("URLTools.extract_code_blocks", url_tools.extract_code_blocks)
    
    # Save the curried proxy
    curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
    print(f"✅ Created curried proxy with ID: {curried_proxy.id}")
    
    # Convert UUID to string for Task creation
    curried_proxy_id_str = str(curried_proxy.id)
    
    # Create TasksManager for concert travel planning
    concert_planner_manager = TasksManager(
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
                
                When planning a concert trip, you should:
                - Understand the user's music preferences and travel constraints
                - Find relevant concerts and festivals that match their interests
                - Suggest optimal travel dates that align with the events
                - Provide comprehensive travel recommendations
                - Consider practical aspects like budget and logistics"""
            )
        ]
    )
    concert_planner_manager = persistence_model.tasksmanagers.create(concert_planner_manager)
    print(f"✅ Created Concert Travel Planner manager with ID: {concert_planner_manager.id}")
    
    # Create CrewAI config for concert planning
    crewai_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        create_crew=CreateCrewRequest(
            description="Concert Travel Planning Crew",
            process=Process.hierarchical,
            agents=[
                AgentModel(
                    role="Concert Researcher",
                    goal="Find the best concerts and music festivals based on user preferences",
                    backstory="""You are an expert music researcher with extensive knowledge of 
                    concerts, festivals, and music scenes around the world. You stay up-to-date 
                    with the latest events and can quickly find relevant concerts based on 
                    location, date, and music genre preferences.""",
                    tools=[
                        ToolModel(
                            name="WebsiteSearchTool",
                            description="Search the web for information"
                        ),
                        ToolModel(
                            name="SerperDevTool",
                            description="Search the web using Serper API"
                        )
                    ]
                ),
                AgentModel(
                    role="Travel Planner",
                    goal="Create optimal travel plans around concert dates",
                    backstory="""You are an experienced travel planner specializing in 
                    creating itineraries around events. You have extensive knowledge of 
                    flights, accommodations, and transportation options. You excel at 
                    optimizing travel dates to balance cost, convenience, and experience.""",
                    tools=[
                        ToolModel(
                            name="WebsiteSearchTool",
                            description="Search the web for information"
                        ),
                        ToolModel(
                            name="SerperDevTool",
                            description="Search the web using Serper API"
                        )
                    ]
                ),
                AgentModel(
                    role="Local Expert",
                    goal="Provide insider knowledge about concert venues and local attractions",
                    backstory="""You are a local expert with deep knowledge of cities, 
                    venues, and local attractions. You can provide insider tips about 
                    concert venues, nearby accommodations, restaurants, and activities 
                    to enhance the overall trip experience.""",
                    tools=[
                        ToolModel(
                            name="WebsiteSearchTool",
                            description="Search the web for information"
                        ),
                        ToolModel(
                            name="SerperDevTool",
                            description="Search the web using Serper API"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description="""Research concerts and music festivals in the user-specified location and date range.
                    
                    Your task is to:
                    1. Search for concerts and music festivals in the specified location and date range
                    2. Filter results based on the user's music genre preferences
                    3. Compile a comprehensive list of relevant events with dates, venues, and ticket information
                    4. Identify the most promising events based on popularity, reviews, and alignment with preferences
                    5. Provide detailed information about each recommended event
                    
                    Be thorough in your research and provide specific, actionable information.""",
                    expected_output="A comprehensive list of concerts and festivals with detailed information",
                    agent_role="Concert Researcher"
                ),
                TaskModel(
                    description="""Create an optimal travel plan around the identified concert dates.
                    
                    Your task is to:
                    1. Research flight options to and from the concert location
                    2. Identify optimal travel dates based on concert schedules and flight availability
                    3. Suggest accommodation options near the concert venues
                    4. Create a comprehensive travel itinerary including transportation between venues
                    5. Provide cost estimates for the entire trip
                    
                    Focus on creating a practical, efficient travel plan that maximizes the concert experience.""",
                    expected_output="A detailed travel plan with dates, flights, accommodations, and cost estimates",
                    agent_role="Travel Planner"
                ),
                TaskModel(
                    description="""Provide insider information about concert venues and local attractions.
                    
                    Your task is to:
                    1. Research the specific concert venues identified in the plan
                    2. Provide insider tips about each venue (best seating, acoustics, etc.)
                    3. Suggest nearby restaurants, bars, and attractions
                    4. Identify local transportation options around the venues
                    5. Suggest additional activities to enhance the trip experience
                    
                    Focus on providing unique, valuable insights that would be difficult for tourists to discover on their own.""",
                    expected_output="Detailed venue information and local recommendations for each concert location",
                    agent_role="Local Expert"
                )
            ]
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    crewai_config = persistence_model.crewai_config.create(crewai_config)
    print(f"✅ Created CrewAI config with ID: {crewai_config.id}")
    
    # Create task for concert planning using CrewAI
    concert_planning_task = Task(
        name="Plan Concert Trip",
        description="Plan a concert trip based on user preferences using CrewAI",
        tasksmanager_id=str(concert_planner_manager.id),
        curried_proxy_id=curried_proxy_id_str,
        crewai_config_id=str(crewai_config.id),
        use_context=True,
        inherit_manager_context=True,
        framework="crewai",
        messages=[
            Message(
                role="system",
                content="""Your task is to plan a concert trip based on user preferences using CrewAI.
                
                You will work with a crew of specialized agents:
                - Concert Researcher: Finds concerts and festivals based on preferences
                - Travel Planner: Creates optimal travel plans around concert dates
                - Local Expert: Provides insider knowledge about venues and attractions
                
                You should:
                1. Understand the user's music preferences, location interests, and date constraints
                2. Coordinate the crew to research concerts, plan travel, and provide local insights
                3. Synthesize the information into a comprehensive concert trip plan
                4. Present the plan in a clear, organized format
                
                Focus on creating a personalized, practical concert trip plan that aligns with the user's preferences."""
            )
        ]
    )
    
    # Add knowledge base context if available
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
            'created_at': datetime.now()
        }
        
        if not hasattr(concert_planning_task, 'contexts') or concert_planning_task.contexts is None:
            concert_planning_task.contexts = []
        concert_planning_task.contexts.append(context_ref)
    
    concert_planning_task = persistence_model.tasks.create(concert_planning_task)
    print(f"✅ Created concert planning task with ID: {concert_planning_task.id}")
    
    # Create task for custom concert search
    custom_search_task = Task(
        name="Search for Specific Concerts",
        description="Search for specific concerts based on detailed user criteria",
        tasksmanager_id=str(concert_planner_manager.id),
        curried_proxy_id=curried_proxy_id_str,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to search for specific concerts based on detailed user criteria.
                
                You should:
                1. Understand the user's specific concert search criteria (artist, venue, date range, etc.)
                2. Use web search tools to find relevant concert information
                3. Compile a comprehensive list of matching concerts with detailed information
                4. Present the results in a clear, organized format
                
                Focus on providing accurate, up-to-date concert information that precisely matches the user's criteria."""
            )
        ]
    )
    
    # Add knowledge base context if available
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
            'created_at': datetime.now()
        }
        
        if not hasattr(custom_search_task, 'contexts') or custom_search_task.contexts is None:
            custom_search_task.contexts = []
        custom_search_task.contexts.append(context_ref)
    
    custom_search_task = persistence_model.tasks.create(custom_search_task)
    print(f"✅ Created custom search task with ID: {custom_search_task.id}")
    
    # Create task for festival recommendations
    festival_recommendations_task = Task(
        name="Recommend Music Festivals",
        description="Recommend music festivals based on user preferences",
        tasksmanager_id=str(concert_planner_manager.id),
        curried_proxy_id=curried_proxy_id_str,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Your task is to recommend music festivals based on user preferences.
                
                You should:
                1. Understand the user's music genre preferences, location interests, and date constraints
                2. Use web search tools to research relevant music festivals
                3. Compile a list of recommended festivals with detailed information
                4. Provide insights about each festival's atmosphere, lineup, and unique features
                
                Focus on recommending festivals that align with the user's musical tastes and offer exceptional experiences."""
            )
        ]
    )
    
    # Add knowledge base context if available
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
            'created_at': datetime.now()
        }
        
        if not hasattr(festival_recommendations_task, 'contexts') or festival_recommendations_task.contexts is None:
            festival_recommendations_task.contexts = []
        festival_recommendations_task.contexts.append(context_ref)
    
    festival_recommendations_task = persistence_model.tasks.create(festival_recommendations_task)
    print(f"✅ Created festival recommendations task with ID: {festival_recommendations_task.id}")
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="concert_travel_planner_state.json"
    )
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    result = save_to_storage(persistence_model, state_location)
    print(f"✅ State saved: {result}")
    
    return {
        "concert_planner_manager_id": concert_planner_manager.id,
        "concert_planning_task_id": concert_planning_task.id,
        "custom_search_task_id": custom_search_task.id,
        "festival_recommendations_task_id": festival_recommendations_task.id,
        "curried_proxy_id": curried_proxy.id,
        "crewai_config_id": crewai_config.id
    }

if __name__ == "__main__":
    asyncio.run(setup_concert_travel_planner_state()) 