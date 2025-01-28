import sys
import os
from pathlib import Path
import asyncio
import json

# Add the project root to the Python path
project_root = str(Path(__file__).parents[1])
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage

async def setup_scifi_analysis_state():
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create first TasksManager for book analysis
    book_analysis_manager = TasksManager(
        name="Science Fiction Book Analysis",
        model="gpt-4o-mini",
        description="Analyzes science fiction books to extract and analyze technological capabilities",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in analyzing science fiction literature 
                and technological capabilities. Your role is to:
                1. Extract and catalog technological capabilities described in science fiction works
                2. Compare these capabilities with real-world technological developments
                3. Provide detailed analysis of which predictions came true and which remain fictional
                
                Format your responses clearly and include:
                - Detailed description of each technology
                - Time period when it was described in the book
                - Current status (developed/not developed)
                - Relevant historical development information"""
            ).dict()
        ]
    )
    book_analysis_manager = persistence_model.tasksmanagers.create(book_analysis_manager)
    
    # Create tasks for book analysis
    capability_extraction_task = Task(
        name="Extract Science Fiction Capabilities",
        description="Extract and catalog all technological capabilities described in the science fiction book",
        tasksmanager_id=book_analysis_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""Analyze the provided science fiction text and:
                1. Identify all technological capabilities and inventions
                2. Describe each capability in detail
                3. Note when it was first described in the book
                4. Categorize by type (transportation, communication, computing, etc.)
                5. List any specific technical details provided"""
            ).dict()
        ]
    )
    capability_extraction_task = persistence_model.tasks.create(capability_extraction_task)
    
    development_analysis_task = Task(
        name="Analyze Historical Development",
        description="Compare extracted capabilities with historical technological developments",
        tasksmanager_id=book_analysis_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""For each technological capability identified:
                1. Research when/if it was developed in real life
                2. Compare book's description with actual implementation
                3. Analyze accuracy of the prediction
                4. Document key differences between fiction and reality
                5. Provide timeline of related technological developments"""
            ).dict()
        ]
    )
    development_analysis_task = persistence_model.tasks.create(development_analysis_task)
    
    # Create second TasksManager for feasibility analysis
    feasibility_manager = TasksManager(
        name="Modern Feasibility Analysis",
        model="gpt-40-mini",
        description="Analyzes the feasibility of implementing science fiction concepts with current technology",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in analyzing the feasibility of 
                science fiction concepts using modern technology. Your role is to:
                1. Evaluate each concept against current technological capabilities
                2. Identify required technological breakthroughs
                3. Estimate feasibility timeline
                4. Suggest potential implementation approaches
                
                Consider:
                - Current state of relevant technologies
                - Required scientific breakthroughs
                - Technical limitations
                - Resource requirements
                - Practical implementation challenges"""
            ).dict()
        ]
    )
    feasibility_manager = persistence_model.tasksmanagers.create(feasibility_manager)
    
    # Create tasks for feasibility analysis
    implementation_analysis_task = Task(
        name="Modern Implementation Analysis",
        description="Analyze feasibility of implementing science fiction capabilities with current technology",
        tasksmanager_id=feasibility_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""For each science fiction capability:
                1. Assess current technological readiness level
                2. Identify existing similar technologies
                3. List required technological breakthroughs
                4. Estimate development timeline
                5. Analyze resource requirements
                6. Consider practical implementation challenges
                7. Suggest potential modern approaches"""
            ).dict()
        ]
    )
    implementation_analysis_task = persistence_model.tasks.create(implementation_analysis_task)
    
    future_development_task = Task(
        name="Future Development Roadmap",
        description="Create development roadmap for implementing science fiction capabilities",
        tasksmanager_id=feasibility_manager.id,
        use_context=True,
        inherit_manager_context=True,
        messages=[
            Message(
                role="system",
                content="""For implementable capabilities:
                1. Create detailed development roadmap
                2. Identify key technological milestones
                3. Suggest research and development approaches
                4. Estimate resource requirements
                5. Analyze potential challenges and solutions
                6. Consider ethical and practical implications
                7. Propose timeline for development phases"""
            ).dict()
        ]
    )
    future_development_task = persistence_model.tasks.create(future_development_task)
    
    # Get the state as JSON and add context state
    state_data = json.loads(persistence_model.to_json())
    state_data['context_state'] = {
        'current_tasksmanager_id': book_analysis_manager.id,
        'current_task_id': capability_extraction_task.id,
        'current_session_id': None
    }
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="scifi_analysis_state.json"
    )
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    # Save the state with context
    state_path = Path("state") / "scifi_analysis_state.json"
    with open(state_path, "w") as f:
        json.dump(state_data, f)
    
    print(f"State saved with context: {state_path}")
    
    return {
        "book_analysis_manager_id": book_analysis_manager.id,
        "capability_extraction_task_id": capability_extraction_task.id,
        "development_analysis_task_id": development_analysis_task.id,
        "feasibility_manager_id": feasibility_manager.id,
        "implementation_analysis_task_id": implementation_analysis_task.id,
        "future_development_task_id": future_development_task.id
    }

if __name__ == "__main__":
    asyncio.run(setup_scifi_analysis_state())
