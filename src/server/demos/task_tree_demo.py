from src.server.controllers.task_tree_flow import TaskTreeFlowManager as TaskTreeManager
from src.server.controllers.task_tree_flow import ExecutionConfig, ExecutionStrategy
from src.server.models.task import Task
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from pathlib import Path
import json
import uuid
from pydantic import BaseModel

class TaskTreeMetadata(BaseModel):
    """Metadata for a task tree."""
    id: str
    name: str
    description: str
    execution_strategy: str
    root_task_id: str

def create_multi_plugin_task_tree():
    """Create a task tree with multiple plugins for demonstration."""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Research Pipeline",
        description="A research pipeline using multiple AI frameworks",
        model="gpt-4o-mini"
    )
    persistence_model.tasksmanagers.create(tm)
    
    root_task = Task(
        id="research_project",
        name="Research Project",
        description="Comprehensive research project on AI agents",
        tasksmanager_id=tm.id,
        agent_role="Manager",
        plugin="crewai",
        input_data={"topic": "AI frameworks"}
    )
    persistence_model.tasks.create(root_task)
    
    level1_tasks = [
        Task(
            id="data_collection",
            name="Data Collection",
            description="Collect relevant data sources",
            tasksmanager_id=tm.id,
            agent_role="Researcher", 
            plugin="crewai",
            parent_id="research_project"
        ),
        Task(
            id="market_analysis",
            name="Market Analysis",
            description="Analyze market trends",
            tasksmanager_id=tm.id,
            agent_role="Analyst",
            plugin="autogen",
            parent_id="research_project",
            input_from_tasks=["data_collection"]
        ),
        Task(
            id="technical_research",
            name="Technical Research",
            description="Research technical aspects",
            tasksmanager_id=tm.id,
            agent_role="TechExpert",
            plugin="smolagents",
            parent_id="research_project"
        )
    ]
    
    level2_tasks = [
        Task(
            id="report_generation",
            name="Report Generation",
            description="Generate final report",
            tasksmanager_id=tm.id,
            agent_role="Writer",
            plugin="crewai",
            parent_id="market_analysis",
            input_from_tasks=["market_analysis", "technical_research"]
        )
    ]
    
    for task in level1_tasks + level2_tasks:
        persistence_model.tasks.create(task)
    
    tree_metadata = TaskTreeMetadata(
        id="research_pipeline",
        name="Research Pipeline",
        description="A multi-plugin task tree demonstrating handover between different AI frameworks",
        execution_strategy="sequential",
        root_task_id="research_project"
    )
    
    persistence_model.collection("task_trees").create(tree_metadata)
    
    return persistence_model, tm.id

def save_task_tree_demo_state():
    """Generate and save the task tree demo state."""
    persistence_model, tasksmanager_id = create_multi_plugin_task_tree()
    
    state_dir = Path("state")
    state_dir.mkdir(exist_ok=True)
    
    location = StorageLocation(
        type=StorageType.file,
        location=str(state_dir),
        state_name="task_tree_demo"
    )
    
    context_state = {
        "current_tasksmanager_id": tasksmanager_id,
        "current_task_id": "research_project"
    }
    
    json_str = persistence_model.to_json()
    state_dict = json.loads(json_str)
    state_dict["context_state"] = context_state
    
    state_file = state_dir / "task_tree_demo.json"
    with open(state_file, "w") as f:
        json.dump(state_dict, f, indent=2)
    
    return str(state_file)
