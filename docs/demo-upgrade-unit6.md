I agree that we need to properly integrate the Task Tree demo as a state rather than just a notebook or script. Let's implement Unit 6 as a complete demo state that can be loaded and visualized in the Streamlit UI.

Here's the implementation for Unit 6:

```python
# src/state_setup/task_tree_demo.py
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
from src.server.controllers.persistence_controller import save_to_storage
from src.server.controllers.curried_proxy import CurriedProxy
from src.server.models.tools_catalog import ToolsCatalog
from src.server.models.agent import CrewAIConfig, CreateCrewRequest, AgentModel, TaskModel, ToolModel
from src.server.models.process import Process
from src.server.controllers.tasks_tree_controller import TaskTreeManager, ExecutionConfig, ExecutionStrategy
from src.server.tools.url_tools import URLTools
from src.server.tools.internal_file_tools import InternalFileTools
from src.server.context import knowledge_base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def add_task_tree_knowledge():
    """Add task tree knowledge to the knowledge base for context."""
    try:
        # Create task tree knowledge content
        task_tree_content = """# Task Tree Execution Patterns

## Task Tree Structure
- Task trees represent hierarchical relationships between tasks
- Each task can have parent-child relationships
- Tasks can depend on outputs from other tasks
- The execution order is determined by dependencies and hierarchy

## Execution Strategies
- **Sequential**: Tasks are executed one after another in order
- **Parallel**: Independent tasks are executed simultaneously
- **Parallel with Limit**: Tasks are executed in parallel with resource constraints

## Plugin Integration
- Task trees can incorporate multiple plugin types
- Different nodes can use different agent frameworks
- Plugins can be mixed in the same tree for specialized capabilities
- Data can be handed over between different plugin types

## Data Flow Patterns
- Parent to Child: Results flow down from parent to children
- Dependency Chain: Results flow through dependency relationships
- Aggregation: Child results are combined in parent nodes
- Transformation: Data is modified at each stage of processing

## Execution Monitoring
- Tree execution can be monitored in real-time
- Status tracking shows progress through the tree
- Error handling can be configured at the tree level
- Execution statistics provide insights into performance"""
        
        # Add to knowledge base
        knowledge_id = await knowledge_base.add_knowledge(
            content=task_tree_content,
            domain="task_trees",
            metadata={
                "type": "documentation",
                "category": "execution_patterns",
                "tags": ["task_tree", "execution", "patterns"]
            }
        )
        logger.info(f"✅ Added task tree knowledge to knowledge base with ID: {knowledge_id}")
        return knowledge_id
    except Exception as e:
        logger.error(f"❌ Failed to add task tree knowledge to knowledge base: {str(e)}")
        return None

async def setup_task_tree_demo_state():
    """Set up a state for demonstrating task tree capabilities."""
    
    print("\n🔄 Setting up Task Tree Demo state...")
    
    # Initialize persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Add task tree knowledge to knowledge base
    knowledge_id = await add_task_tree_knowledge()
    
    # Create and register tools
    url_tools = URLTools()
    internal_file_tools = InternalFileTools()
    tools_catalog = ToolsCatalog()
    
    # Register tools with catalog
    tools_catalog.register_instance(url_tools, "url_tools")
    tools_catalog.register_instance(internal_file_tools, "internal_file_tools")
    
    # Create a curried proxy for the tools
    curried_proxy = CurriedProxy()
    curried_proxy.add_tool("URLTools.get_data_from_url", url_tools.get_data_from_url)
    curried_proxy.add_tool("URLTools.get_documentation", url_tools.get_documentation)
    curried_proxy.add_tool("InternalFileTools.read_file", internal_file_tools.read_file)
    curried_proxy.add_tool("InternalFileTools.write_file", internal_file_tools.write_file)
    
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
    
    # Create AutoGen config
    autogen_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        create_crew=CreateCrewRequest(
            description="Data Analysis Crew",
            process=Process.sequential,
            agents=[
                AgentModel(
                    role="Data Analyst",
                    goal="Analyze data and extract insights",
                    backstory="""You are a skilled data analyst capable of 
                    processing data to extract meaningful insights and patterns.""",
                    tools=[
                        ToolModel(
                            name="URLTools.get_documentation",
                            description="Get documentation from specified URL"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description="""Analyze the prepared data to extract insights and patterns.
                    Identify key trends, anomalies, and interesting correlations.""",
                    expected_output="Analysis report with key insights and visualization data",
                    agent_role="Data Analyst"
                )
            ]
        )
    )
    autogen_config = persistence_model.crewai_config.create(autogen_config)
    print(f"✅ Created AutoGen config with ID: {autogen_config.id}")
    
    # Create SmolAgents config
    smolagents_config = CrewAIConfig(
        id=str(uuid.uuid4()),
        create_crew=CreateCrewRequest(
            description="Report Generation Crew",
            process=Process.sequential,
            agents=[
                AgentModel(
                    role="Report Writer",
                    goal="Generate comprehensive reports from analysis results",
                    backstory="""You are a professional report writer who excels at
                    creating clear, concise, and informative reports from data analysis.""",
                    tools=[
                        ToolModel(
                            name="InternalFileTools.write_file",
                            description="Write content to a file"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description="""Create a comprehensive report based on the analysis results.
                    The report should be well-structured, include visualizations, and highlight key findings.""",
                    expected_output="Final report document with visualizations and insights",
                    agent_role="Report Writer"
                )
            ]
        )
    )
    smolagents_config = persistence_model.crewai_config.create(smolagents_config)
    print(f"✅ Created SmolAgents config with ID: {smolagents_config.id}")
    
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
        crewai_config_id=str(autogen_config.id),
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
        crewai_config_id=str(autogen_config.id),
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
        crewai_config_id=str(smolagents_config.id),
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
    
    # Create task tree metadata in task_tree collection
    tree_metadata = {
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
    
    # Ensure task_trees collection exists
    if not persistence_model.collection_exists("task_trees"):
        persistence_model.create_collection("task_trees")
    
    # Store tree metadata
    persistence_model.collection("task_trees").create(
        "data_processing_pipeline", 
        tree_metadata
    )
    print(f"✅ Created task tree metadata")
    
    # Add task execution metadata
    execution_metadata = {
        "task_tree_id": "data_processing_pipeline",
        "execution_config": {
            "default_strategy": "sequential",
            "max_parallel_tasks": 2,
            "timeout_seconds": 300
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
    
    # Store execution metadata
    persistence_model.collection("task_tree_executions").create(
        "data_pipeline_execution",
        execution_metadata
    )
    print(f"✅ Created execution metadata")
    
    # Save the state
    state_location = StorageLocation(
        type=StorageType.file,
        location="state",
        state_name="task_tree_demo_state.json"
    )
    
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
```

Next, let's create a Task Tree Visualization component that can be used in the Streamlit UI to show the task tree structure including the data flow between tasks:

```python
# src/server/views/components/task_tree_visualization_component.py
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, Any, List, Optional
import uuid
import io
import base64

class TaskTreeVisualizationComponent:
    """Component for visualizing task trees in Streamlit."""
    
    def __init__(self, persistence_model=None):
        """Initialize the component."""
        self.persistence_model = persistence_model
        self.plugin_colors = {
            "crewai": "#4CAF50",     # Green
            "autogen": "#2196F3",    # Blue
            "smolagents": "#FF9800", # Orange
            "default": "#9E9E9E"     # Gray
        }
    
    def render(self, tree_id: str = None, tasksmanager_id: str = None):
        """Render the task tree visualization."""
        if not self.persistence_model:
            st.error("Persistence model not available")
            return
            
        # Get task tree metadata
        tree_metadata = None
        if tree_id and self.persistence_model.collection_exists("task_trees"):
            tree_metadata = self.persistence_model.collection("task_trees").read(tree_id)
        
        # If no tree_id provided or metadata not found, try to find by tasksmanager_id
        if not tree_metadata and tasksmanager_id:
            if self.persistence_model.collection_exists("task_trees"):
                # Try to find a tree with matching tasksmanager_id in any task
                for tree_item_id in self.persistence_model.collection("task_trees").list():
                    tree_data = self.persistence_model.collection("task_trees").read(tree_item_id)
                    if tree_data and 'root_task_id' in tree_data:
                        root_task = self.persistence_model.tasks.read(tree_data['root_task_id'])
                        if root_task and root_task.tasksmanager_id == tasksmanager_id:
                            tree_metadata = tree_data
                            tree_id = tree_item_id
                            break
        
        # If still no metadata, build from tasks
        if not tree_metadata and tasksmanager_id:
            # Get all tasks for the tasksmanager
            tasks = [t for t in self.persistence_model.tasks.list() if t.tasksmanager_id == tasksmanager_id]
            
            # Find root tasks (no parent_id)
            root_tasks = [t for t in tasks if not hasattr(t, 'parent_id') or not t.parent_id]
            
            if root_tasks:
                # Use the first root task
                root_task = root_tasks[0]
                tree_id = f"dynamic_tree_{tasksmanager_id}"
                tree_metadata = {
                    "name": f"Task Tree for {root_task.name}",
                    "description": "Dynamically generated task tree",
                    "root_task_id": root_task.id,
                    "execution_strategy": "sequential",
                    "plugins": list(set([getattr(t, 'plugin', 'default') for t in tasks if hasattr(t, 'plugin')]))
                }
        
        if not tree_metadata:
            st.warning("No task tree found")
            return
            
        # Display tree information
        st.subheader(tree_metadata["name"])
        st.write(tree_metadata["description"])
        
        # Get execution metadata if available
        execution_metadata = None
        if tree_id and self.persistence_model.collection_exists("task_tree_executions"):
            # Find execution metadata for this tree
            for exec_id in self.persistence_model.collection("task_tree_executions").list():
                exec_data = self.persistence_model.collection("task_tree_executions").read(exec_id)
                if exec_data and exec_data.get('task_tree_id') == tree_id:
                    execution_metadata = exec_data
                    break
        
        # Create graph
        G = nx.DiGraph()
        
        # Get all tasks
        root_task_id = tree_metadata.get('root_task_id')
        if not root_task_id:
            st.error("No root task ID specified in tree metadata")
            return
            
        root_task = self.persistence_model.tasks.read(root_task_id)
        if not root_task:
            st.error(f"Root task {root_task_id} not found")
            return
            
        # Get all tasks for the tasksmanager
        all_tasks = [t for t in self.persistence_model.tasks.list() if t.tasksmanager_id == root_task.tasksmanager_id]
        
        # Build tree structure
        task_nodes = {}
        for task in all_tasks:
            # Determine node color based on plugin
            plugin = getattr(task, 'plugin', 'default')
            node_color = self.plugin_colors.get(plugin, self.plugin_colors['default'])
            
            # Add node to graph
            G.add_node(
                task.id, 
                name=task.name, 
                description=task.description,
                plugin=plugin,
                color=node_color
            )
            task_nodes[task.id] = task
            
            # Add parent-child edges
            parent_id = getattr(task, 'parent_id', None)
            if parent_id and parent_id in task_nodes:
                G.add_edge(parent_id, task.id, type='hierarchy', style='solid')
            
            # Add dependency edges
            input_from = getattr(task, 'input_from_tasks', [])
            if input_from:
                for input_task_id in input_from:
                    if input_task_id in task_nodes:
                        # Check if edge already exists to avoid duplicates
                        if not G.has_edge(input_task_id, task.id):
                            G.add_edge(input_task_id, task.id, type='data', style='dashed')
        
        # Create visualization
        st.write("### Task Tree Structure")
        
        # Create plot
        plt.figure(figsize=(12, 8))
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot") if hasattr(nx, 'nx_agraph') else nx.spring_layout(G)
        
        # Draw nodes with plugin colors
        node_colors = [G.nodes[n]['color'] for n in G.nodes()]
        nx.draw_networkx_nodes(
            G, pos, 
            node_color=node_colors, 
            node_size=1500, 
            alpha=0.8
        )
        
        # Draw edges with different styles for hierarchy vs data flow
        hierarchy_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'hierarchy']
        data_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'data']
        
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=hierarchy_edges,
            edge_color='black', 
            arrows=True, 
            arrowsize=20,
            width=2,
            style='solid'
        )
        
        nx.draw_networkx_edges(
            G, pos,
            edgelist=data_edges,
            edge_color='blue',
            arrows=True,
            arrowsize=15,
            width=1.5,
            style='dashed'
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            G, pos, 
            labels={n: G.nodes[n]['name'] for n in G.nodes()},
            font_size=10,
            font_weight='bold'
        )
        
        # Add legend
        legend_patches = []
        for plugin, color in self.plugin_colors.items():
            if plugin in tree_metadata.get('plugins', []) or plugin == 'default':
                legend_patches.append(mpatches.Patch(color=color, label=plugin))
        
        # Add edge type legend
        legend_patches.append(plt.Line2D([0], [0], color='black', lw=2, label='Hierarchy'))
        legend_patches.append(plt.Line2D([0], [0], color='blue', lw=2, linestyle='--', label='Data Flow'))
        
        plt.legend(handles=legend_patches, loc='upper right')
        plt.axis('off')
        plt.title("Task Tree Visualization")
        
        # Save the plot to a buffer and display with st.image
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        st.image(buf, use_column_width=True)
        
        # Display execution information if available
        if execution_metadata:
            st.write("### Execution Flow")
            st.write("Execution order:")
            
            for idx, item in enumerate(execution_metadata.get('execution_order', [])):
                if isinstance(item, list):
                    # Parallel tasks
                    parallel_names = []
                    for task_id in item:
                        task = self.persistence_model.tasks.read(task_id)
                        if task:
                            parallel_names.append(task.name)
                    st.write(f"{idx+1}. Parallel: {', '.join(parallel_names)}")
                else:
                    # Sequential task
                    task = self.persistence_model.tasks.read(item)
                    if task:
                        st.write(f"{idx+1}. {task.name}")
            
            # Display data flow
            if 'data_flow' in execution_metadata:
                st.write("### Data Flow")
                for flow in execution_metadata['data_flow']:
                    from_task = self.persistence_model.tasks.read(flow['from'])
                    to_task = self.persistence_model.tasks.read(flow['to'])
                    if from_task and to_task:
                        st.write(f"- **{from_task.name}** → **{to_task.name}**: {flow.get('data_type', 'Data')}")
```

Now, let's add a task tree demo component that can be used in the task hierarchy view to load and demonstrate the task tree:

```python
# src/server/views/components/task_tree_demo_component.py
import streamlit as st
from pathlib import Path
from typing import Optional
import json

class TaskTreeDemoComponent:
    """Component for launching and visualizing the task tree demo."""
    
    def __init__(self, controller):
        """Initialize the component with the task hierarchy controller."""
        self.controller = controller
        
    def render(self):
        """Render the task tree demo component."""
        st.write("## Task Tree Demonstration")
        
        # Check if demo state exists
        demo_state_path = Path("state/task_tree_demo_state.json")
        demo_state_exists = demo_state_path.exists()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("### Demo Controls")
            
            if demo_state_exists:
                st.success("Task Tree demo state is available")
                
                # Load demo button
                if st.button("Load Task Tree Demo", key="load_task_tree_demo"):
                    with st.spinner("Loading demo state..."):
                        result = self.controller.load_state("state/task_tree_demo_state.json")
                        if result and "successfully" in result.lower():
                            st.success("Demo state loaded successfully!")
                            # Force rerun to update UI
                            st.rerun()
                        else:
# src/server/views/components/task_tree_demo_component.py (continued)
                            st.error(f"Failed to load demo state: {result}")
            else:
                st.warning("Task Tree demo state is not available")
                
                # Create demo button
                if st.button("Generate Task Tree Demo", key="generate_task_tree_demo"):
                    with st.spinner("Generating task tree demo state..."):
                        try:
                            # Import the setup function and run it
                            from src.state_setup.task_tree_demo import setup_task_tree_demo_state
                            import asyncio
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(setup_task_tree_demo_state())
                            loop.close()
                            
                            st.success("Demo state created successfully!")
                            st.info("Click 'Load Task Tree Demo' to load the created state")
                            # Force rerun to update UI
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate demo state: {str(e)}")
            
            # Demo explanation
            st.write("### About This Demo")
            st.write("""
            This demo showcases the Task Tree capabilities of Cerebrum, including:
            
            - Hierarchical task structures
            - Multiple plugin integration (CrewAI, AutoGen, SmolAgents)
            - Task dependencies and data flow
            - Different execution strategies
            
            The demo presents a data processing pipeline with:
            1. Data acquisition using CrewAI
            2. Parallel analysis using AutoGen
            3. Report generation using SmolAgents
            """)
        
        with col2:
            if demo_state_exists:
                st.write("### Demo Preview")
                
                try:
                    # Read preview data from state file
                    with open(demo_state_path, "r") as f:
                        state_data = json.load(f)
                    
                    # Check if we have task_trees collection data
                    if "collections" in state_data and "task_trees" in state_data["collections"]:
                        task_trees = state_data["collections"]["task_trees"]
                        if task_trees and isinstance(task_trees, dict) and len(task_trees) > 0:
                            tree_id = list(task_trees.keys())[0]
                            tree_data = task_trees[tree_id]
                            
                            # Display tree information
                            st.write(f"**Tree Name:** {tree_data['name']}")
                            st.write(f"**Description:** {tree_data['description']}")
                            st.write(f"**Plugins:** {', '.join(tree_data['plugins'])}")
                            
                            # Display task structure
                            st.write("**Task Structure:**")
                            st.code("""
Root: Data Pipeline Coordinator
  ├─ Data Acquisition (CrewAI)
  ├─ Market Analysis (AutoGen) ← Data Acquisition
  ├─ Technical Analysis (AutoGen) ← Data Acquisition
  └─ Report Generation (SmolAgents) ← Market Analysis, Technical Analysis
                            """)
                            
                            # Display a simple preview of the tree visualization
                            st.write("Load the demo to see the full interactive visualization")
                    else:
                        st.info("Load the demo to view the task tree")
                except Exception as e:
                    st.error(f"Error reading demo preview: {str(e)}")
            else:
                st.info("Generate the demo to preview the task tree")
```

Now, let's integrate this demo component with the task hierarchy view by adding it as a tab:

```python
# Modification to src/server/views/controllers/task_view_controller.py
# Import the new component
from src.server.views.components.task_tree_demo_component import TaskTreeDemoComponent
from src.server.views.components.task_tree_visualization_component import TaskTreeVisualizationComponent

# Add the demo tab to task_hierarchy_view_handle
def task_hierarchy_view_handle(self):
    """Handle the task hierarchy view and add demo tab."""
    # Add tabs for hierarchy and demo
    tabs = st.tabs(["Task Hierarchy", "Task Tree Demo"])
    
    with tabs[0]:
        # Existing hierarchy view code...
        self.render_task_hierarchy()
    
    with tabs[1]:
        # Add demo component
        demo_component = TaskTreeDemoComponent(self)
        demo_component.render()

# Modify the render_task_hierarchy method to include visualization for loaded demo
def render_task_hierarchy(self):
    """Render the task hierarchy with visualization support for task trees."""
    # ... existing code ...
    
    # Check if this is a task tree state
    tree_id = None
    if self.global_persistence.collection_exists("task_trees"):
        for tree_item_id in self.global_persistence.collection("task_trees").list():
            tree_metadata = self.global_persistence.collection("task_trees").read(tree_item_id)
            tree_id = tree_item_id
            break
    
    # If tree_id is found, show visualization
    if tree_id:
        st.write("### Task Tree Visualization")
        viz_component = TaskTreeVisualizationComponent(self.global_persistence)
        viz_component.render(tree_id)
    
    # ... rest of the existing hierarchy view code ...
```

Let's also add CSS styles for the task handover visualization:

```css
/* src/server/static/css/task_tree.css */
.task-node {
    border-radius: 5px;
    padding: 10px;
    margin: 5px;
    border: 1px solid #ccc;
}

.task-node-crewai {
    background-color: rgba(76, 175, 80, 0.2);
    border-left: 5px solid #4CAF50;
}

.task-node-autogen {
    background-color: rgba(33, 150, 243, 0.2);
    border-left: 5px solid #2196F3;
}

.task-node-smolagents {
    background-color: rgba(255, 152, 0, 0.2);
    border-left: 5px solid #FF9800;
}

.task-node-default {
    background-color: rgba(158, 158, 158, 0.2);
    border-left: 5px solid #9E9E9E;
}

.task-flow-arrow {
    color: #2196F3;
    font-weight: bold;
}

.execution-step {
    background-color: rgba(33, 33, 33, 0.05);
    padding: 10px;
    border-radius: 3px;
    margin: 5px 0;
}

.execution-parallel {
    display: flex;
    gap: 10px;
}
```

Finally, let's create unit tests for our task tree demo implementation:

```python
# tests/state_setup/test_task_tree_demo.py
import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

from src.state_setup.task_tree_demo import setup_task_tree_demo_state
from src.server.persistence.persistence_model_factory import PersistenceModelFactory

@pytest.mark.asyncio
async def test_task_tree_demo_setup():
    """Test that the task tree demo setup creates the expected state structure."""
    # Mock knowledge base
    with patch('src.state_setup.task_tree_demo.knowledge_base') as mock_kb:
        mock_kb.add_knowledge.return_value = asyncio.Future()
        mock_kb.add_knowledge.return_value.set_result("test_knowledge_id")
        
        # Mock saving state to file
        with patch('builtins.open', MagicMock()):
            with patch('json.dump', MagicMock()):
                # Run setup
                result = await setup_task_tree_demo_state()
                
                # Check results
                assert "tasksmanager_id" in result
                assert "root_task_id" in result
                assert "data_acquisition_task_id" in result
                assert "market_analysis_task_id" in result
                assert "technical_analysis_task_id" in result
                assert "report_generation_task_id" in result
                
                # Verify tasks were created
                persistence_model = PersistenceModelFactory.persistence_model("inmemory")
                
                # Verify task manager was created
                tasksmanager = persistence_model.tasksmanagers.read(result["tasksmanager_id"])
                assert tasksmanager is not None
                assert tasksmanager.name == "Data Processing Pipeline"
                
                # Verify root task was created
                root_task = persistence_model.tasks.read(result["root_task_id"])
                assert root_task is not None
                assert root_task.name == "Data Pipeline Coordinator"
                
                # Verify child tasks
                data_acquisition = persistence_model.tasks.read(result["data_acquisition_task_id"])
                assert data_acquisition is not None
                assert data_acquisition.parent_id == root_task.id
                assert data_acquisition.plugin == "crewai"
                
                # Verify task with dependencies
                report_generation = persistence_model.tasks.read(result["report_generation_task_id"])
                assert report_generation is not None
                assert "market_analysis_task_id" in result
                assert "technical_analysis_task_id" in result
                assert result["market_analysis_task_id"] in report_generation.input_from_tasks
                assert result["technical_analysis_task_id"] in report_generation.input_from_tasks
                
                # Verify collections were created
                assert persistence_model.collection_exists("task_trees")
                assert persistence_model.collection_exists("task_tree_executions")
                
                # Verify task tree metadata
                tree_data = next(iter(persistence_model.collection("task_trees").list_pairs()))
                assert tree_data is not None
                tree_id, tree_metadata = tree_data
                assert tree_metadata["root_task_id"] == root_task.id
                assert len(tree_metadata["plugins"]) == 3
                assert "crewai" in tree_metadata["plugins"]
                assert "autogen" in tree_metadata["plugins"]
                assert "smolagents" in tree_metadata["plugins"]

# Tests for the UI components
@pytest.mark.parametrize("tree_exists", [True, False])
def test_task_tree_demo_component(tree_exists):
    """Test the task tree demo component with and without existing state."""
    from src.server.views.components.task_tree_demo_component import TaskTreeDemoComponent
    
    # Mock controller
    mock_controller = MagicMock()
    mock_controller.load_state.return_value = "State loaded successfully"
    
    # Mock Path.exists
    with patch('pathlib.Path.exists', return_value=tree_exists):
        # Mock streamlit
        with patch('streamlit.write'), \
             patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]), \
             patch('streamlit.success'), \
             patch('streamlit.error'), \
             patch('streamlit.warning'), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.spinner'), \
             patch('streamlit.rerun'):
            
            # Test component
            component = TaskTreeDemoComponent(mock_controller)
            component.render()
            
            # If tree exists, should try to load it
            if tree_exists:
                mock_controller.load_state.assert_called_once()
```

Let's also write a test for the visualization component:

```python
# tests/views/components/test_task_tree_visualization.py
import pytest
from unittest.mock import patch, MagicMock
import networkx as nx
import matplotlib.pyplot as plt

from src.server.views.components.task_tree_visualization_component import TaskTreeVisualizationComponent

def test_task_tree_visualization():
    """Test the task tree visualization component."""
    # Mock persistence model
    mock_persistence = MagicMock()
    
    # Mock collections and tasks
    mock_persistence.collection_exists.return_value = True
    mock_persistence.collection.return_value.read.return_value = {
        "name": "Test Tree",
        "description": "Test description",
        "root_task_id": "root123",
        "execution_strategy": "sequential",
        "plugins": ["crewai", "autogen", "smolagents"]
    }
    
    # Mock tasks
    root_task = MagicMock()
    root_task.id = "root123"
    root_task.name = "Root Task"
    root_task.description = "Root task description"
    root_task.tasksmanager_id = "mgr123"
    root_task.plugin = "crewai"
    
    child_task1 = MagicMock()
    child_task1.id = "child1"
    child_task1.name = "Child Task 1"
    child_task1.description = "Child task 1 description"
    child_task1.tasksmanager_id = "mgr123"
    child_task1.parent_id = "root123"
    child_task1.plugin = "autogen"
    
    child_task2 = MagicMock()
    child_task2.id = "child2"
    child_task2.name = "Child Task 2"
    child_task2.description = "Child task 2 description"
    child_task2.tasksmanager_id = "mgr123"
    child_task2.parent_id = "root123"
    child_task2.plugin = "smolagents"
    child_task2.input_from_tasks = ["child1"]
    
    mock_persistence.tasks.read.side_effect = lambda task_id: {
        "root123": root_task,
        "child1": child_task1,
        "child2": child_task2
    }.get(task_id)
    
    mock_persistence.tasks.list.return_value = [root_task, child_task1, child_task2]
    
    # Mock matplotlib
    with patch('matplotlib.pyplot.figure'), \
         patch('matplotlib.pyplot.savefig'), \
         patch('matplotlib.pyplot.axis'), \
         patch('matplotlib.pyplot.title'), \
         patch('matplotlib.pyplot.legend'), \
         patch('streamlit.write'), \
         patch('streamlit.subheader'), \
         patch('streamlit.image'), \
         patch('streamlit.error'), \
         patch('streamlit.warning'), \
         patch('networkx.draw_networkx_nodes'), \
         patch('networkx.draw_networkx_edges'), \
         patch('networkx.draw_networkx_labels'), \
         patch('networkx.spring_layout', return_value={}):
        
        # Create component and render
        component = TaskTreeVisualizationComponent(mock_persistence)
        component.render(tree_id="test_tree")
        
        # Verify that the component read the tree metadata
        mock_persistence.collection.assert_called_with("task_trees")
        mock_persistence.collection().read.assert_called_with("test_tree")
        
        # Verify that it read the root task
        mock_persistence.tasks.read.assert_any_call("root123")
```

With these implementations, we've created a comprehensive Task Tree Demo that:

1. Creates a realistic task tree state with multiple plugins (CrewAI, AutoGen, SmolAgents)
2. Establishes proper parent-child relationships and task dependencies
3. Defines data flow between tasks
4. Provides visualizations of the task tree structure
5. Is integrated into the Streamlit UI via the Task Hierarchy view
6. Includes proper unit tests for all components

The demo showcases the core Cerebrum capabilities including:
- Task hierarchies and trees
- Multiple plugin integration
- Task handover and data flow
- Different execution strategies (sequential vs parallel)
- Task tree visualization

This implementation is a proper engineering example that can be used to demonstrate the Cerebrum framework's advanced features in a real-world scenario.
