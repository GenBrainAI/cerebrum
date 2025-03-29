"""
Demo state setup for task handover feature.

This script creates a specialized state file that demonstrates the task handover capability.
It sets up a task manager with a sequence of tasks that have dependencies between them.
"""

import logging
import json
import uuid
from pathlib import Path
from datetime import datetime

from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from src.server.models.message import Message
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage

logger = logging.getLogger(__name__)

def get_state_dir() -> Path:
    """Get the path to the state directory."""
    return Path(__file__).parent.parent.parent / "state"

def setup_task_handover_demo():
    """Set up a demo state for task handover."""
    
    # Create a fresh persistence model
    persistence_model = InMemoryPersistenceModel()
    
    # Create a task manager for the demo
    task_manager = TasksManager(
        id="handover_demo_tm",
        name="Task Handover Demo",
        description="A demo task manager for showcasing task handover capabilities",
        messages=[
            Message(role="system", content="You are a helpful assistant specialized in research, analysis, and content creation.")
        ],
        model="gpt-4o-mini"
    )
    
    persistence_model.tasksmanagers.create(task_manager)
    print(f"✅ Created task manager: {task_manager.name}")
    
    # Create a sequence of tasks with dependencies between them
    
    # Task 1: Research Task
    research_task = Task(
        id="research_task",
        name="Research Task",
        description="Research a topic and gather key information",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are a research assistant specialized in gathering accurate information. Your task is to research the requested topic and provide a structured summary of your findings.")
        ],
        output_to_tasks=["analysis_task"]
    )
    
    persistence_model.tasks.create(research_task)
    print(f"✅ Created task: {research_task.name}")
    
    # Task 2: Analysis Task (depends on Research Task)
    analysis_task = Task(
        id="analysis_task",
        name="Analysis Task",
        description="Analyze the research findings and extract key insights",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are an analyst specialized in extracting meaningful insights from research data. Your task is to analyze the research findings, identify patterns and trends, and provide meaningful conclusions.")
        ],
        input_from_tasks=["research_task"],
        output_to_tasks=["report_task"]
    )
    
    persistence_model.tasks.create(analysis_task)
    print(f"✅ Created task: {analysis_task.name}")
    
    # Task 3: Report Generation Task (depends on Analysis Task)
    report_task = Task(
        id="report_task",
        name="Report Generation Task",
        description="Generate a comprehensive report based on the analysis",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are a professional report writer specialized in creating clear, concise, and comprehensive reports. Your task is to take the analysis provided and create a well-structured report with executive summary, key findings, and recommendations.")
        ],
        input_from_tasks=["analysis_task", "research_task"]  # Depends on both research and analysis
    )
    
    persistence_model.tasks.create(report_task)
    print(f"✅ Created task: {report_task.name}")
    
    # Create an additional parallel branch to demonstrate complex dependencies
    
    # Task 4: Data Collection Task
    data_task = Task(
        id="data_task",
        name="Data Collection Task",
        description="Collect numerical data on the research topic",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are a data specialist. Your task is to collect relevant numerical data points, statistics, and metrics related to the research topic.")
        ],
        output_to_tasks=["visualization_task"]
    )
    
    persistence_model.tasks.create(data_task)
    print(f"✅ Created task: {data_task.name}")
    
    # Task 5: Visualization Task (depends on Data Collection Task)
    visualization_task = Task(
        id="visualization_task",
        name="Visualization Task",
        description="Create visual representations of the collected data",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are a data visualization specialist. Your task is to take numerical data and describe how it should be visually represented through charts, graphs, or other visualizations.")
        ],
        input_from_tasks=["data_task"],
        output_to_tasks=["report_task"]
    )
    
    persistence_model.tasks.create(visualization_task)
    print(f"✅ Created task: {visualization_task.name}")
    
    # Task 6: Final Summary Task (depends on Report Task)
    summary_task = Task(
        id="summary_task",
        name="Executive Summary Task",
        description="Create a concise executive summary of the entire project",
        tasksmanager_id="handover_demo_tm",
        status="pending",
        model="gpt-4o-mini",
        messages=[
            Message(role="system", content="You are an executive summary specialist. Your task is to distill complex information into clear, concise summaries suitable for decision-makers.")
        ],
        input_from_tasks=["report_task", "visualization_task"]  # Depends on both report and visualizations
    )
    
    persistence_model.tasks.create(summary_task)
    print(f"✅ Created task: {summary_task.name}")
    
    # Save the state
    state_name = "task_handover_demo"
    state_dir = get_state_dir()
    
    location = StorageLocation(
        type=StorageType.file,
        location=str(state_dir),
        state_name=state_name
    )
    
    result = save_to_storage(persistence_model, location)
    
    # Save metadata
    metadata_path = state_dir / "metadata.json"
    
    try:
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}
            
        metadata.update({
            "last_used_state": state_name,
            "last_used_tasksmanager_id": task_manager.id,
            "last_used_task_id": research_task.id,
            "last_modified": datetime.now().isoformat()
        })
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"✅ Updated metadata with last used state: {state_name}")
        
    except Exception as e:
        print(f"❌ Error updating metadata: {str(e)}")
        
    print(f"✅ State saved as '{state_name}' in {state_dir}")
    return result

if __name__ == "__main__":
    setup_task_handover_demo()
    print("✅ Task handover demo setup complete.") 