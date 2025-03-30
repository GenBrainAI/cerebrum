"""
Task Tree Demo State Setup

This module sets up a state for demonstrating task tree capabilities in Cerebrum.
It creates a hierarchical task structure with multiple plugins working together
on a data processing pipeline, showing execution strategies and data handover.
"""

import sys
import os
from pathlib import Path
import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.task import Task
from src.server.models.message import Message
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.tools_catalog import ToolsCatalog
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, TaskModel, ToolModel
from src.server.models.process import Process
from src.server.controllers.task_tree_flow import ExecutionStrategy
from src.server.tools.url_tools import URLTools
from src.server.tools.internal_file_tools import InternalFileTools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def setup_task_tree_demo_state():
    """Set up a state for demonstrating task tree capabilities."""
    
    print("\n🔄 Setting up Task Tree Demo state...")
    
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create and register tools
    url_tools = URLTools()
    internal_file_tools = InternalFileTools()
    
    # Create a curried proxy for the tools
    curried_proxy = CurriedProxy()
    
    # Add URL tools
    curried_proxy.add_tool("URLTools.get_data_from_url", url_tools.get_data_from_url)
    curried_proxy.add_tool("URLTools.get_documentation", url_tools.get_documentation)
    
    # Add internal file tools
    curried_proxy.add_tool("InternalFileTools.read_documentation", internal_file_tools.read_documentation)
    curried_proxy.add_tool("InternalFileTools.save_implementation", internal_file_tools.save_implementation)
    
    # Save the curried proxy
    curried_proxy = persistence_model.curried_proxies.create(curried_proxy)
    print(f"✅ Created curried proxy with ID: {curried_proxy.id}")
    
    # Convert UUID to string for Task creation
    curried_proxy_id_str = str(curried_proxy.id)
    
    # Create TasksManager for data pipeline
    data_pipeline_manager = TasksManager(
        name="Data Processing Pipeline",
        model="gpt-4o-mini",
        description="Manages a hierarchical data processing pipeline with multiple plugins",
        messages=[
            Message(
                role="system",
                content="""You are an AI assistant specializing in data processing pipelines.
                You oversee a task tree of operations that processes data through multiple stages
                using different AI frameworks. Your tasks form a hierarchical structure with
                various execution strategies."""
            )
        ]
    )
    data_pipeline_manager = persistence_model.tasksmanagers.create(data_pipeline_manager)
    print(f"✅ Created Data Pipeline manager with ID: {data_pipeline_manager.id}")
    
    # Create CrewAI config for data acquisition
    crewai_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        create_crew=CreateCrewRequest(
            description="Data Acquisition Crew",
            process=Process.sequential,
            agents=[
                AgentModel(
                    role="Data Engineer",
                    goal="Collect and prepare data from various sources",
                    backstory="""You are an expert data engineer specialized in 
                    collecting and preparing data from various sources. You ensure
                    data is correctly formatted and ready for analysis.""",
                    tools=[
                        ToolModel(
                            name="URLTools.get_data_from_url",
                            description="Get data from specified URL"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description="""Collect data from specified sources and prepare it for processing.
                    The data should be cleaned and formatted according to the pipeline requirements.""",
                    expected_output="Clean, formatted dataset ready for analysis",
                    agent_role="Data Engineer"
                )
            ]
        )
    )
    crewai_config = persistence_model.crewai_config.create(crewai_config)
    print(f"✅ Created CrewAI config with ID: {crewai_config.id}")
    
    # Create root task (Pipeline Coordinator)
    root_task = Task(
        id="data_pipeline_root",
        name="Data Pipeline Coordinator",
        description="Coordinates the entire data processing pipeline",
        tasksmanager_id=data_pipeline_manager.id,
        curried_proxy_id=curried_proxy_id_str,
        plugin="crewai",
        messages=[
            Message(
                role="system",
                content="""You are the coordinator for the entire data processing pipeline.
                You oversee and manage the execution of all subtasks in the pipeline,
                ensuring proper data flow and execution order."""
            )
        ]
    )
    root_task = persistence_model.tasks.create(root_task)
    print(f"✅ Created root task with ID: {root_task.id}")
    
    # Create data acquisition task
    data_acquisition_task = Task(
        id="data_acquisition",
        name="Data Acquisition",
        description="Collect and prepare data from various sources",
        tasksmanager_id=data_pipeline_manager.id,
        curried_proxy_id=curried_proxy_id_str,
        crewai_config_id=str(crewai_config.id),
        plugin="crewai",
        parent_id="data_pipeline_root",
        execution_strategy=ExecutionStrategy.SEQUENTIAL.value,
        messages=[
            Message(
                role="system",
                content="""Your task is to collect and prepare data from various sources.
                The data should be cleaned and formatted according to the pipeline requirements."""
            )
        ]
    )
    data_acquisition_task = persistence_model.tasks.create(data_acquisition_task)
    print(f"✅ Created data acquisition task with ID: {data_acquisition_task.id}")
    
    # Create parallel analysis subtasks
    market_analysis_task = Task(
        id="market_analysis",
        name="Market Analysis",
        description="Analyze market-related data and trends",
        tasksmanager_id=data_pipeline_manager.id,
        curried_proxy_id=curried_proxy_id_str,
        plugin="autogen",
        parent_id="data_pipeline_root",
        input_from_tasks=["data_acquisition"],
        execution_strategy=ExecutionStrategy.PARALLEL.value,
        messages=[
            Message(
                role="system",
                content="""Your task is to analyze market-related data from the data acquisition phase.
                Focus on market trends, competitive analysis, and economic indicators."""
            )
        ]
    )
    market_analysis_task = persistence_model.tasks.create(market_analysis_task)
    print(f"✅ Created market analysis task with ID: {market_analysis_task.id}")
    
    # Create technical analysis task
    technical_analysis_task = Task(
        id="technical_analysis",
        name="Technical Analysis",
        description="Analyze technical aspects of the data",
        tasksmanager_id=data_pipeline_manager.id,
        curried_proxy_id=curried_proxy_id_str,
        plugin="autogen",
        parent_id="data_pipeline_root",
        input_from_tasks=["data_acquisition"],
        execution_strategy=ExecutionStrategy.PARALLEL.value,
        messages=[
            Message(
                role="system",
                content="""Your task is to analyze the technical aspects of the data.
                Focus on technical indicators, patterns, and metrics."""
            )
        ]
    )
    technical_analysis_task = persistence_model.tasks.create(technical_analysis_task)
    print(f"✅ Created technical analysis task with ID: {technical_analysis_task.id}")
    
    # Create report generation task
    report_generation_task = Task(
        id="report_generation",
        name="Report Generation",
        description="Generate comprehensive reports from analysis results",
        tasksmanager_id=data_pipeline_manager.id,
        curried_proxy_id=curried_proxy_id_str,
        plugin="smolagents",
        parent_id="data_pipeline_root",
        input_from_tasks=["market_analysis", "technical_analysis"],
        execution_strategy=ExecutionStrategy.SEQUENTIAL.value,
        messages=[
            Message(
                role="system",
                content="""Your task is to generate a comprehensive report based on the analysis results.
                Combine insights from both market and technical analyses to create a complete picture."""
            )
        ]
    )
    report_generation_task = persistence_model.tasks.create(report_generation_task)
    print(f"✅ Created report generation task with ID: {report_generation_task.id}")
    
    # Add tree metadata directly as a custom property on the root task
    root_task.config = {
        "task_tree": {
            "name": "Data Processing Pipeline",
            "description": "A hierarchical data processing pipeline demonstrating task tree capabilities",
            "execution_strategy": "sequential",
            "created_at": datetime.now().isoformat(),
            "plugins": ["crewai", "autogen", "smolagents"],
            "visualization_config": {
                "show_plugin_colors": True,
                "show_data_flow": True,
                "show_execution_order": True
            },
            "execution_order": [
                "data_pipeline_root",
                "data_acquisition",
                ["market_analysis", "technical_analysis"],  # Parallel execution
                "report_generation"
            ],
            "data_flow": [
                {"from": "data_acquisition", "to": "market_analysis", "data_type": "Prepared Dataset"},
                {"from": "data_acquisition", "to": "technical_analysis", "data_type": "Prepared Dataset"},
                {"from": "market_analysis", "to": "report_generation", "data_type": "Market Analysis Results"},
                {"from": "technical_analysis", "to": "report_generation", "data_type": "Technical Analysis Results"}
            ]
        }
    }
    
    # Update the root task with metadata
    root_task = persistence_model.tasks.update(root_task.id, root_task)
    print(f"✅ Added tree metadata to root task")
    
    # Ensure the state directory exists
    os.makedirs("state", exist_ok=True)
    
    # Create context state with session info
    context_state = {
        'current_tasksmanager_id': data_pipeline_manager.id,
        'current_task_id': root_task.id,
        'tree_visualization': {
            'show_data_flow': True,
            'highlight_current_task': True
        }
    }
    
    # Manually add context to the serialized state
    json_str = persistence_model.to_json()
    state_dict = json.loads(json_str)
    state_dict["context_state"] = context_state
    
    # Add task tree info to state dict directly
    if "task_trees" not in state_dict:
        state_dict["task_trees"] = {}
        
    state_dict["task_trees"]["data_processing_pipeline"] = {
        "name": "Data Processing Pipeline",
        "description": "A hierarchical data processing pipeline demonstrating task tree capabilities",
        "root_task_id": "data_pipeline_root",
        "execution_strategy": "sequential",
        "created_at": datetime.now().isoformat(),
        "plugins": ["crewai", "autogen", "smolagents"],
        "visualization_config": {
            "show_plugin_colors": True,
            "show_data_flow": True,
            "show_execution_order": True
        }
    }
    
    # Add execution info to state dict directly
    if "task_tree_executions" not in state_dict:
        state_dict["task_tree_executions"] = {}
        
    state_dict["task_tree_executions"]["data_pipeline_execution"] = {
        "task_tree_id": "data_processing_pipeline",
        "execution_config": {
            "default_strategy": "sequential",
            "max_parallel_tasks": 2,
            "timeout_seconds": 300
        },
        "execution_order": [
            "data_pipeline_root",
            "data_acquisition",
            ["market_analysis", "technical_analysis"],
            "report_generation"
        ],
        "data_flow": [
            {"from": "data_acquisition", "to": "market_analysis", "data_type": "Prepared Dataset"},
            {"from": "data_acquisition", "to": "technical_analysis", "data_type": "Prepared Dataset"},
            {"from": "market_analysis", "to": "report_generation", "data_type": "Market Analysis Results"},
            {"from": "technical_analysis", "to": "report_generation", "data_type": "Technical Analysis Results"}
        ]
    }
    
    # Save state manually to include context
    state_file = Path("state") / "task_tree_demo_state.json"
    with open(state_file, "w") as f:
        json.dump(state_dict, f, indent=2)
    
    print(f"✅ State saved to: {state_file}")
    
    return {
        "tasksmanager_id": data_pipeline_manager.id,
        "root_task_id": root_task.id,
        "data_acquisition_task_id": data_acquisition_task.id,
        "market_analysis_task_id": market_analysis_task.id,
        "technical_analysis_task_id": technical_analysis_task.id,
        "report_generation_task_id": report_generation_task.id,
        "curried_proxy_id": curried_proxy.id,
        "state_file": str(state_file)
    }

if __name__ == "__main__":
    import asyncio
    import json
    
    result = asyncio.run(setup_task_tree_demo_state())
    print("\n✅ Task Tree Demo state setup completed successfully")
    print(f"📊 Task tree structure:")
    print(f"  Root: Data Pipeline Coordinator")
    print(f"    ├─ Data Acquisition (CrewAI)")
    print(f"    ├─ Market Analysis (AutoGen) ← Data Acquisition")
    print(f"    ├─ Technical Analysis (AutoGen) ← Data Acquisition")
    print(f"    └─ Report Generation (SmolAgents) ← Market Analysis, Technical Analysis")
    print(f"\n💾 State file saved to: {result['state_file']}") 