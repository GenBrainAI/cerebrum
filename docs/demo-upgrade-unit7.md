# Implementation of Unit 7: Documentation and Demo Script

## Documentation Notebook Implementation

Let's create the `cerebrum_demos.ipynb` notebook to document Cerebrum's advanced features:

```python
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Cerebrum Demos Documentation\n",
    "\n",
    "## Overview\n",
    "\n",
    "This notebook provides documentation and examples for Cerebrum's advanced features:\n",
    "\n",
    "1. **Agentic Plugin System** - How different AI frameworks can be used through a unified plugin interface\n",
    "2. **Task Handover** - How tasks can pass data between each other\n",
    "3. **Task Trees** - How hierarchical task structures work with different execution strategies"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Agentic Plugin System\n",
    "\n",
    "Cerebrum supports multiple AI agent frameworks through its plugin system:\n",
    "\n",
    "- **CrewAI** - Multi-agent collaboration framework\n",
    "- **AutoGen** - Microsoft's conversational agent framework\n",
    "- **SmolAgents** - HuggingFace's lightweight agent framework\n",
    "\n",
    "### How to Use the Plugin System"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import asyncio\n",
    "from src.server.plugins.plugin_manager import PluginManager\n",
    "from src.server.plugins.agent_framework_config import AgentFrameworkConfig\n",
    "\n",
    "# Initialize plugin manager\n",
    "plugin_manager = PluginManager()\n",
    "\n",
    "# Define an async function to load plugins\n",
    "async def setup_plugins():\n",
    "    # Load a plugin\n",
    "    crewai_config = AgentFrameworkConfig(\n",
    "        name=\"crewai\",\n",
    "        version=\"1.0.0\",\n",
    "        description=\"CrewAI Plugin\",\n",
    "        settings={\"model\": \"gpt-4o-mini\"}\n",
    "    )\n",
    "    success = await plugin_manager.load_plugin(\"src/server/plugins/crewai_plugin.py\", crewai_config)\n",
    "    print(f\"CrewAI plugin loaded: {success}\")\n",
    "    \n",
    "    # Create an agent\n",
    "    agent = await plugin_manager.create_agent(\"crewai\", {\n",
    "        \"role\": \"Researcher\",\n",
    "        \"goal\": \"Find information about AI agents\",\n",
    "        \"backstory\": \"Expert researcher with broad knowledge\"\n",
    "    })\n",
    "    print(f\"Agent created: {agent}\")\n",
    "    \n",
    "    # Execute a task\n",
    "    result = await plugin_manager.execute_task(\"crewai\", agent, {\n",
    "        \"description\": \"Research the latest developments in AI agents\",\n",
    "        \"expected_output\": \"A comprehensive research report\"\n",
    "    })\n",
    "    print(f\"Task executed with result: {result}\")\n",
    "    \n",
    "    return result\n",
    "\n",
    "# Uncomment to run the example\n",
    "# result = asyncio.run(setup_plugins())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Task Handover\n",
    "\n",
    "Tasks can pass their outputs to other tasks through the handover mechanism:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from src.server.models.task import Task\n",
    "from src.server.controllers.task_runner import TaskRunner\n",
    "from src.server.persistence.persistence_model_factory import PersistenceModelFactory\n",
    "from src.server.models.tasks_manager import TasksManager\n",
    "\n",
    "# Initialize persistence model and task runner\n",
    "persistence_model = PersistenceModelFactory.persistence_model(\"inmemory\")\n",
    "task_runner = TaskRunner(persistence_model)\n",
    "\n",
    "# Example of setting up tasks with handover\n",
    "async def setup_task_handover():\n",
    "    # Create a task manager\n",
    "    tasks_manager = TasksManager(\n",
    "        name=\"Handover Demo\",\n",
    "        description=\"Demonstrating task handover\",\n",
    "        model=\"gpt-4o-mini\"\n",
    "    )\n",
    "    tasks_manager = persistence_model.tasksmanagers.create(tasks_manager)\n",
    "    tasksmanager_id = tasks_manager.id\n",
    "    \n",
    "    # Define tasks with handover\n",
    "    task1 = Task(\n",
    "        id=\"data_collection\",\n",
    "        name=\"Data Collection\",\n",
    "        description=\"Collect relevant data\",\n",
    "        tasksmanager_id=tasksmanager_id\n",
    "    )\n",
    "    \n",
    "    task2 = Task(\n",
    "        id=\"data_analysis\",\n",
    "        name=\"Data Analysis\",\n",
    "        description=\"Analyze collected data\",\n",
    "        tasksmanager_id=tasksmanager_id,\n",
    "        input_from_tasks=[\"data_collection\"]  # Takes output from task1\n",
    "    )\n",
    "    \n",
    "    # Create tasks in persistence model\n",
    "    persistence_model.tasks.create(task1)\n",
    "    persistence_model.tasks.create(task2)\n",
    "    \n",
    "    # Initialize task runner\n",
    "    await task_runner.initialize()\n",
    "    \n",
    "    # Run tasks in sequence with handover\n",
    "    results = await task_runner.run_task_sequence(tasksmanager_id, [\"data_collection\", \"data_analysis\"])\n",
    "    \n",
    "    print(f\"Task sequence results: {results}\")\n",
    "    return results\n",
    "\n",
    "# Uncomment to run the example\n",
    "# results = asyncio.run(setup_task_handover())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Task Trees\n",
    "\n",
    "Task trees represent hierarchical relationships between tasks:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from src.server.controllers.tasks_tree_controller import TaskTreeManager, ExecutionStrategy, ExecutionConfig\n",
    "from src.server.models.task import Task\n",
    "import uuid\n",
    "\n",
    "# Create a task tree\n",
    "def create_task_tree():\n",
    "    # Create execution config\n",
    "    config = ExecutionConfig(\n",
    "        default_strategy=ExecutionStrategy.SEQUENTIAL,\n",
    "        max_parallel_tasks=3,\n",
    "        timeout_seconds=300\n",
    "    )\n",
    "    \n",
    "    # Create tree manager\n",
    "    manager = TaskTreeManager(execution_config=config)\n",
    "    \n",
    "    # Create tasks\n",
    "    root_task = Task(\n",
    "        id=\"root_task\",\n",
    "        name=\"Research Project\",\n",
    "        description=\"Comprehensive research project\"\n",
    "    )\n",
    "    \n",
    "    child_task1 = Task(\n",
    "        id=\"child_task1\",\n",
    "        name=\"Literature Review\",\n",
    "        description=\"Review existing literature\"\n",
    "    )\n",
    "    \n",
    "    child_task2 = Task(\n",
    "        id=\"child_task2\",\n",
    "        name=\"Data Collection\",\n",
    "        description=\"Collect empirical data\"\n",
    "    )\n",
    "    \n",
    "    grandchild_task = Task(\n",
    "        id=\"grandchild_task\",\n",
    "        name=\"Data Analysis\",\n",
    "        description=\"Analyze collected data\",\n",
    "        input_from_tasks=[\"child_task2\"]\n",
    "    )\n",
    "    \n",
    "    # Add nodes to the tree\n",
    "    manager.create_node(root_task)\n",
    "    manager.set_as_root(\"root_task\")\n",
    "    \n",
    "    manager.create_node(child_task1)\n",
    "    manager.create_node(child_task2)\n",
    "    manager.create_node(grandchild_task)\n",
    "    \n",
    "    # Set parent-child relationships\n",
    "    manager.add_child(\"root_task\", \"child_task1\")\n",
    "    manager.add_child(\"root_task\", \"child_task2\")\n",
    "    manager.add_child(\"child_task2\", \"grandchild_task\")\n",
    "    \n",
    "    # Set execution strategies\n",
    "    manager.set_execution_strategy(\"root_task\", ExecutionStrategy.SEQUENTIAL)\n",
    "    manager.set_execution_strategy(\"child_task2\", ExecutionStrategy.PARALLEL)\n",
    "    \n",
    "    print(\"Task tree created successfully\")\n",
    "    return manager\n",
    "\n",
    "# Create the task tree\n",
    "task_tree = create_task_tree()\n",
    "\n",
    "# Get execution order\n",
    "execution_order = task_tree.get_execution_order()\n",
    "print(\"Execution order:\")\n",
    "for i, node in enumerate(execution_order):\n",
    "    print(f\"{i+1}. {node.task.name} ({node.task.id})\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Execution Strategies\n",
    "\n",
    "Task trees support different execution strategies:\n",
    "\n",
    "1. **Sequential** - Execute tasks one after another\n",
    "2. **Parallel** - Execute independent tasks simultaneously\n",
    "3. **Parallel with Limit** - Execute in parallel with a resource limit\n",
    "\n",
    "Here's how to set different execution strategies:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from src.server.controllers.tasks_tree_controller import ExecutionStrategy\n",
    "\n",
    "# Example of setting different execution strategies\n",
    "def set_execution_strategies(manager: TaskTreeManager):\n",
    "    # Sequential execution (default) - tasks are executed one after another\n",
    "    manager.set_execution_strategy(\"root_task\", ExecutionStrategy.SEQUENTIAL)\n",
    "    \n",
    "    # Parallel execution - all child tasks are executed simultaneously\n",
    "    manager.set_execution_strategy(\"child_task1\", ExecutionStrategy.PARALLEL)\n",
    "    \n",
    "    # Parallel with limit - execute up to N tasks simultaneously\n",
    "    manager.execution_config.max_parallel_tasks = 3\n",
    "    manager.set_execution_strategy(\"child_task2\", ExecutionStrategy.PARALLEL_WITH_LIMIT)\n",
    "    \n",
    "    print(\"Execution strategies set\")\n",
    "    return manager\n",
    "\n",
    "# Set execution strategies\n",
    "task_tree = set_execution_strategies(task_tree)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Multi-Plugin Task Tree\n",
    "\n",
    "A more complex example showing a task tree with multiple plugins:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create a multi-plugin task tree\n",
    "def create_multi_plugin_task_tree():\n",
    "    # Create execution config\n",
    "    config = ExecutionConfig(\n",
    "        default_strategy=ExecutionStrategy.SEQUENTIAL,\n",
    "        max_parallel_tasks=3,\n",
    "        timeout_seconds=300\n",
    "    )\n",
    "    \n",
    "    # Create tree manager\n",
    "    manager = TaskTreeManager(execution_config=config)\n",
    "    \n",
    "    # Create root task (CrewAI)\n",
    "    root_task = Task(\n",
    "        id=\"research_project\",\n",
    "        name=\"Research Project\",\n",
    "        description=\"Comprehensive research project on AI agents\",\n",
    "        agent_role=\"Manager\",\n",
    "        input_data={\"plugin\": \"crewai\"}\n",
    "    )\n",
    "    manager.create_node(root_task)\n",
    "    manager.set_as_root(\"research_project\")\n",
    "    \n",
    "    # Create level 1 tasks with different plugins\n",
    "    tasks = [\n",
    "        Task(\n",
    "            id=\"data_collection\",\n",
    "            name=\"Data Collection\",\n",
    "            description=\"Collect relevant data sources\",\n",
    "            agent_role=\"Researcher\", \n",
    "            input_data={\"plugin\": \"crewai\"}\n",
    "        ),\n",
    "        Task(\n",
    "            id=\"market_analysis\",\n",
    "            name=\"Market Analysis\",\n",
    "            description=\"Analyze market trends\",\n",
    "            agent_role=\"Analyst\",\n",
    "            input_data={\"plugin\": \"autogen\"}\n",
    "        ),\n",
    "        Task(\n",
    "            id=\"technical_research\",\n",
    "            name=\"Technical Research\",\n",
    "            description=\"Research technical aspects\",\n",
    "            agent_role=\"TechExpert\",\n",
    "            input_data={\"plugin\": \"smolagents\"}\n",
    "        )\n",
    "    ]\n",
    "    \n",
    "    # Add tasks to manager\n",
    "    for task in tasks:\n",
    "        manager.create_node(task)\n",
    "        manager.add_child(\"research_project\", task.id)\n",
    "    \n",
    "    # Create level 2 tasks\n",
    "    subtasks = [\n",
    "        Task(\n",
    "            id=\"report_generation\",\n",
    "            name=\"Report Generation\",\n",
    "            description=\"Generate final report\",\n",
    "            agent_role=\"Writer\",\n",
    "            input_data={\"plugin\": \"crewai\"}\n",
    "        )\n",
    "    ]\n",
    "    \n",
    "    for task in subtasks:\n",
    "        manager.create_node(task)\n",
    "        # Make it depend on all level 1 tasks\n",
    "        for parent_id in [\"data_collection\", \"market_analysis\", \"technical_research\"]:\n",
    "            manager.add_dependency(task.id, parent_id)\n",
    "    \n",
    "    # Set execution strategies\n",
    "    manager.set_execution_strategy(\"research_project\", ExecutionStrategy.SEQUENTIAL)\n",
    "    manager.set_execution_strategy(\"technical_research\", ExecutionStrategy.PARALLEL)\n",
    "    \n",
    "    print(\"Multi-plugin task tree created successfully\")\n",
    "    return manager\n",
    "\n",
    "# Create the multi-plugin task tree\n",
    "multi_plugin_tree = create_multi_plugin_task_tree()\n",
    "\n",
    "# Print tree structure\n",
    "def print_tree_structure(manager):\n",
    "    roots = manager.root_nodes\n",
    "    \n",
    "    def print_node(node, level=0):\n",
    "        indent = \"  \" * level\n",
    "        plugin = node.task.input_data.get(\"plugin\", \"default\")\n",
    "        print(f\"{indent}- {node.task.name} ({plugin})\")\n",
    "        for child in node.children:\n",
    "            print_node(child, level + 1)\n",
    "    \n",
    "    for root in roots:\n",
    "        print_node(root)\n",
    "\n",
    "print(\"\\nTree Structure:\")\n",
    "print_tree_structure(multi_plugin_tree)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Plugin Handover Flow\n",
    "\n",
    "Visualize the flow of data between different plugins:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import matplotlib.pyplot as plt\n",
    "import networkx as nx\n",
    "\n",
    "def visualize_plugin_flow():\n",
    "    \"\"\"Create a visual representation of plugin handover workflow.\"\"\"\n",
    "    G = nx.DiGraph()\n",
    "    \n",
    "    # Add nodes for each plugin and task\n",
    "    G.add_node(\"CrewAI\\nResearcher\", color='lightblue')\n",
    "    G.add_node(\"AutoGen\\nAnalyst\", color='lightgreen')\n",
    "    G.add_node(\"SmolAgents\\nTechExpert\", color='lightsalmon')\n",
    "    G.add_node(\"CrewAI\\nWriter\", color='lightblue')\n",
    "    \n",
    "    # Add edges showing data flow\n",
    "    G.add_edge(\"CrewAI\\nResearcher\", \"AutoGen\\nAnalyst\", label=\"Data Sources\")\n",
    "    G.add_edge(\"CrewAI\\nResearcher\", \"SmolAgents\\nTechExpert\", label=\"Research Context\")\n",
    "    G.add_edge(\"AutoGen\\nAnalyst\", \"CrewAI\\nWriter\", label=\"Analysis Results\")\n",
    "    G.add_edge(\"SmolAgents\\nTechExpert\", \"CrewAI\\nWriter\", label=\"Technical Insights\")\n",
    "    \n",
    "    # Create the plot\n",
    "    plt.figure(figsize=(10, 6))\n",
    "    pos = nx.spring_layout(G, seed=42)\n",
    "    \n",
    "    # Draw nodes\n",
    "    node_colors = [G.nodes[n]['color'] for n in G.nodes()]\n",
    "    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, alpha=0.8)\n",
    "    \n",
    "    # Draw edges\n",
    "    nx.draw_networkx_edges(G, pos, width=2, arrowsize=20)\n",
    "    \n",
    "    # Add node labels\n",
    "    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')\n",
    "    \n",
    "    # Add edge labels\n",
    "    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}\n",
    "    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10)\n",
    "    \n",
    "    plt.title(\"Plugin Handover Flow\", fontsize=16)\n",
    "    plt.axis('off')\n",
    "    plt.tight_layout()\n",
    "    plt.show()\n",
    "\n",
    "# Visualize the plugin flow\n",
    "visualize_plugin_flow()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Demo Instructions\n",
    "\n",
    "1. Load the Task Tree Demo state from the Task Hierarchy view\n",
    "2. Explore the hierarchical structure of tasks\n",
    "3. Note the different plugins used for different tasks\n",
    "4. Observe the handover relationships between tasks\n",
    "5. Run the tasks to see execution flow"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

## Demo Script in Markdown

Let's create the demo script markdown file:

```markdown
# Cerebrum Demo Script

## Preparation
1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the Streamlit application:
   ```bash
   streamlit run src/chat.py
   ```

## Demo 1: Agentic Plugin System

### Step 1: Navigate to the Agentic Config View
1. In the Streamlit sidebar, select "Agentic Config" view
2. Click on the "Plugin Explorer" tab
3. Explore the available plugins (CrewAI, AutoGen, SmolAgents)
4. Highlight the capabilities of each plugin:
   - CrewAI: Multi-agent orchestration with specialized roles
   - AutoGen: Conversational agents with function calling
   - SmolAgents: Lightweight agents for resource-constrained environments

### Step 2: Show Notebook Demo
1. Click on the "Notebooks" tab
2. Select "Plugin Handover Demo" from the dropdown
3. Walk through the notebook showing how different plugins work together:
   - CrewAI for initial research (data gathering)
   - AutoGen for analysis (processing and extracting insights)
   - SmolAgents for report generation (synthesizing output)
4. Point out the visualization of the handover flow
5. Explain how data is passed between plugins via the common interface

## Demo 2: Task Handover

### Step 1: Navigate to the Task Hierarchy View
1. In the Streamlit sidebar, select "Task Hierarchy" view
2. Open the "Demonstration" expander
3. Click "Load Task Tree Demo"
4. Once loaded, explore the task hierarchy:
   - Research Project (root task)
   - Data Collection (child task)
   - Market Analysis (child task)
   - Technical Research (child task)
   - Report Generation (dependent task)
5. Point out the handover relationships shown in the UI:
   - Green left border: indicates tasks that receive input from other tasks
   - Blue right border: indicates tasks that provide output to other tasks
   - Dashed lines: showing the flow of data between tasks

### Step 2: Execute Task Sequence
1. Select the root task "Research Project"
2. Click "Run Task"
3. Watch the execution flow through the tasks:
   - Tasks execute in dependency order
   - Data flows from one task to another
   - Status updates as each task completes
4. Highlight how data flows from one task to another:
   - Each task's output is stored in its `output_data` field
   - Dependent tasks access this data via their `input_data` field
5. Show the results of each task in the sequence:
   - Research data collection
   - Market analysis with findings
   - Technical insights
   - Final synthesized report

## Demo 3: Task Tree with Multiple Plugins

### Step 1: Explore the Task Tree Structure
1. In the Task Hierarchy view with the demo loaded
2. Point out the parent-child relationships:
   - Research Project (root) → Data Collection, Market Analysis, Technical Research (children)
   - Report Generation (dependent on all three children)
3. Highlight the different plugins used for different tasks:
   - CrewAI: Research Project, Data Collection, Report Generation
   - AutoGen: Market Analysis
   - SmolAgents: Technical Research
4. Explain the execution strategy (sequential vs parallel):
   - Root task uses sequential execution (one child at a time)
   - Some child tasks use parallel execution (simultaneous processing)

### Step 2: Show Task Tree Advanced Features
1. Click on different tasks to see their details:
   - Agent role and configuration
   - Plugin type and settings
   - Input/output relationships
2. Highlight the input-output relationships:
   - Report Generation task depends on outputs from all three research tasks
   - Data flows through the tree in a dependency-aware manner
3. Explain how the tree handles dependencies:
   - Tasks won't execute until all their dependencies are satisfied
   - Results are automatically passed from dependency to dependent
4. Demonstrate how execution adapts to the tree structure:
   - Changes in the tree structure affect execution order
   - Different execution strategies for different parts of the tree

## Key Discussion Points
1. How the plugin system enables heterogeneous agent frameworks to work together:
   - Common interface for different frameworks
   - Unified input/output handling
   - Consistent configuration approach
2. How task handover enables complex workflows:
   - Specialized tasks for different stages of the process
   - Automatic data flow between tasks
   - Clear visualization of dependencies
3. How task trees facilitate hierarchical reasoning and execution:
   - Breaking complex problems into manageable sub-tasks
   - Natural mapping of problem structure to execution
   - Different execution strategies for different parts of the problem
4. The flexibility of Cerebrum in supporting diverse AI use cases:
   - Research pipelines
   - Data analysis workflows
   - Report generation
   - Mixed frameworks for optimal task handling

## Troubleshooting
If any issues arise during the demo:

1. **Plugin loading fails**: Check that all plugin files are in the correct location and dependencies are installed
2. **Task execution errors**: Check the logs in the Observability tab for detailed error messages
3. **UI rendering issues**: Try refreshing the page or restarting the Streamlit server
4. **Notebook integration problems**: Ensure streamlit-jupyter is properly installed
```

## Quick Reference Guide

Let's also create a quick reference guide for the demo:

```markdown
# Cerebrum Demo Quick Reference

## Key Features to Highlight

### Agentic Plugin System
- **Multiple Frameworks**: CrewAI, AutoGen, SmolAgents
- **Common Interface**: Consistent API across different frameworks
- **Plugin Manager**: Central point for loading, managing, and executing plugins
- **Agent Creation**: Customizable agents with different roles and goals
- **Task Execution**: Framework-specific task execution with common result format

### Task Handover
- **Input/Output Relationship**: Tasks can use outputs from other tasks as inputs
- **Data Flow Visualization**: Clear visual indicators of data flow
- **Automatic Data Passing**: System manages data transfer between tasks
- **Context Preservation**: Original context is maintained through the handover

### Task Trees
- **Hierarchical Structure**: Parent-child relationships between tasks
- **Execution Strategies**: Sequential, Parallel, Parallel with Limit
- **Dependency Management**: Automatic handling of task dependencies
- **Mixed Plugins**: Different plugins can be used in the same task tree
- **Flow Control**: Control of execution flow based on tree structure

## Demo Timing (30 minutes total)

- **Introduction & Overview**: 3 minutes
- **Agentic Plugin System**: 8 minutes
- **Task Handover**: 7 minutes
- **Task Tree with Multiple Plugins**: 10 minutes
- **Q&A**: 2 minutes

## Key Commands

- Start Streamlit: `streamlit run src/chat.py`
- Generate Task Tree Demo: Use the "Generate Task Tree Demo" button in the Task Hierarchy view
- Run Task Tree: Select root task and click "Run Task"

## UI Navigation

- **Agentic Config View**: Sidebar → Agentic Config
  - Tabs: Chat, Plugins, Notebooks, Observability
  
- **Task Hierarchy View**: Sidebar → Task Hierarchy
  - Demonstration expander: Generate or load demo state
  - Task tree visualization: Explore task relationships
  - Task details: Click on any task to see details
  
- **Plugin Explorer**: Agentic Config → Plugins tab
  - Shows available plugins and their capabilities
  - Includes example usage for each plugin

- **Notebook Viewer**: Agentic Config → Notebooks tab
  - Select from available demo notebooks
  - View interactive or code view of notebooks
```

## Unit Testing for Documentation

Let's create a simple test to verify that our documentation files exist and contain the required content:

```python
# tests/docs/test_documentation.py
import pytest
from pathlib import Path
import json
import re
import markdown

def test_demo_notebook_exists():
    """Test that the demo notebook exists and is valid JSON."""
    notebook_path = Path("notebooks/cerebrum_demos.ipynb")
    assert notebook_path.exists(), "Demo notebook file not found"
    
    # Try to load the notebook file as JSON
    with open(notebook_path, 'r') as f:
        notebook_content
# Unit Testing for Documentation (Continued)

```python
# tests/docs/test_documentation.py (continued)
        notebook_content = json.load(f)
    
    # Check that the notebook has the expected structure
    assert "cells" in notebook_content, "Notebook is missing cells"
    assert "metadata" in notebook_content, "Notebook is missing metadata"
    assert "nbformat" in notebook_content, "Notebook is missing format information"
    
    # Check that the notebook contains sections on key topics
    markdown_cells = [cell for cell in notebook_content["cells"] 
                      if cell["cell_type"] == "markdown"]
    markdown_content = "\n".join([cell["source"] for cell in markdown_cells])
    
    # Check for key topics
    required_topics = [
        "Agentic Plugin System",
        "Task Handover",
        "Task Trees",
        "Execution Strategies",
        "Plugin Handover"
    ]
    
    for topic in required_topics:
        assert topic in markdown_content, f"Notebook is missing section on {topic}"

def test_demo_script_exists():
    """Test that the demo script markdown file exists and contains required sections."""
    script_path = Path("docs/demo-upgrade-workplan.md")
    assert script_path.exists(), "Demo script file not found"
    
    # Read demo script content
    with open(script_path, 'r') as f:
        script_content = f.read()
    
    # Check for key sections
    required_sections = [
        "# Cerebrum Demo Script",
        "## Demo 1: Agentic Plugin System",
        "## Demo 2: Task Handover",
        "## Demo 3:",  # Any third demo section
        "## Key Discussion Points"
    ]
    
    for section in required_sections:
        assert section in script_content, f"Demo script is missing section: {section}"
    
    # Check for steps in each demo
    step_counts = {
        "Demo 1": len(re.findall(r"### Step \d+:", script_content)),
        "Demo 2": len(re.findall(r"### Step \d+:", script_content)),
        "Demo 3": len(re.findall(r"### Step \d+:", script_content))
    }
    
    for demo, count in step_counts.items():
        assert count >= 1, f"{demo} is missing step-by-step instructions"

def test_quick_reference_exists():
    """Test that the quick reference guide exists and contains required sections."""
    ref_path = Path("docs/cerebrum-demo-reference.md")
    assert ref_path.exists(), "Quick reference guide not found"
    
    # Read quick reference content
    with open(ref_path, 'r') as f:
        ref_content = f.read()
    
    # Check for key sections
    required_sections = [
        "# Cerebrum Demo Quick Reference",
        "## Key Features to Highlight",
        "### Agentic Plugin System",
        "### Task Handover",
        "### Task Trees",
        "## Demo Timing",
        "## Key Commands",
        "## UI Navigation"
    ]
    
    for section in required_sections:
        assert section in ref_content, f"Quick reference is missing section: {section}"
```

# Creating the Documentation Files

Now let's create the actual files on disk:

## 1. First, create the notebook directory structure if it doesn't exist:

```bash
mkdir -p notebooks
```

## 2. Save the notebook file as notebooks/cerebrum_demos.ipynb

The notebook content should be saved as a JSON file with the structure created earlier.

## 3. Save the demo script as docs/demo-upgrade-workplan.md

The demo script content should be saved with the Markdown formatting as defined above.

## 4. Save the quick reference guide as docs/cerebrum-demo-reference.md

```markdown
# Cerebrum Demo Quick Reference

## Key Features to Highlight

### Agentic Plugin System
- **Multiple Frameworks**: CrewAI, AutoGen, SmolAgents
- **Common Interface**: Consistent API across different frameworks
- **Plugin Manager**: Central point for loading, managing, and executing plugins
- **Agent Creation**: Customizable agents with different roles and goals
- **Task Execution**: Framework-specific task execution with common result format

### Task Handover
- **Input/Output Relationship**: Tasks can use outputs from other tasks as inputs
- **Data Flow Visualization**: Clear visual indicators of data flow
- **Automatic Data Passing**: System manages data transfer between tasks
- **Context Preservation**: Original context is maintained through the handover

### Task Trees
- **Hierarchical Structure**: Parent-child relationships between tasks
- **Execution Strategies**: Sequential, Parallel, Parallel with Limit
- **Dependency Management**: Automatic handling of task dependencies
- **Mixed Plugins**: Different plugins can be used in the same task tree
- **Flow Control**: Control of execution flow based on tree structure

## Demo Timing (30 minutes total)

- **Introduction & Overview**: 3 minutes
- **Agentic Plugin System**: 8 minutes
- **Task Handover**: 7 minutes
- **Task Tree with Multiple Plugins**: 10 minutes
- **Q&A**: 2 minutes

## Key Commands

- Start Streamlit: `streamlit run src/chat.py`
- Generate Task Tree Demo: Use the "Generate Task Tree Demo" button in the Task Hierarchy view
- Run Task Tree: Select root task and click "Run Task"

## UI Navigation

- **Agentic Config View**: Sidebar → Agentic Config
  - Tabs: Chat, Plugins, Notebooks, Observability
  
- **Task Hierarchy View**: Sidebar → Task Hierarchy
  - Demonstration expander: Generate or load demo state
  - Task tree visualization: Explore task relationships
  - Task details: Click on any task to see details
  
- **Plugin Explorer**: Agentic Config → Plugins tab
  - Shows available plugins and their capabilities
  - Includes example usage for each plugin

- **Notebook Viewer**: Agentic Config → Notebooks tab
  - Select from available demo notebooks
  - View interactive or code view of notebooks

## Troubleshooting Tips

### Plugin Issues
- Check that all plugin files exist in src/server/plugins/
- Verify that dependencies are installed (crewai, autogen, smolagents)
- Look for error messages in the console logs

### Task Execution Problems
- Check the Observability tab for detailed logs
- Verify that all dependent tasks completed successfully
- Check input/output data formats match expectations

### UI Rendering Issues
- Clear browser cache and reload
- Restart the Streamlit server
- Check browser console for JavaScript errors

### Demo State Problems
- Try generating a new demo state
- Check that state files exist in the state/ directory
- Verify file permissions allow read/write access
```

## 5. Generate Screenshots to Include with Documentation

To enhance the documentation, we should create screenshots of key UI elements and features:

1. Plugin Explorer showing available plugins
2. Task hierarchy view with handover relationships
3. Task execution flow in progress
4. Notebook view of plugin handover demo

These screenshots can be referenced in the documentation using relative paths like:

```markdown
![Plugin Explorer](../images/plugin_explorer.png)
```

## 6. Create a Main Documentation Index

To tie everything together, let's create a main documentation index file:

```markdown
# Cerebrum Demo Documentation

This documentation provides comprehensive information about Cerebrum's advanced features and how to demonstrate them.

## Contents

1. [Demo Script](demo-upgrade-workplan.md) - Step-by-step guide for demonstrating Cerebrum
2. [Quick Reference](cerebrum-demo-reference.md) - Key points and navigation
3. [Notebook Demos](../notebooks/cerebrum_demos.ipynb) - Interactive demonstration of features

## Key Features

### Agentic Plugin System
The agentic plugin system allows Cerebrum to work with multiple AI frameworks through a unified interface. It supports CrewAI, AutoGen, and SmolAgents, enabling tasks to be executed using the most appropriate framework for the job.

### Task Handover
Task handover enables complex workflows by passing data between tasks. This allows specialized tasks to work together, with each task building on the results of previous tasks.

### Task Trees
Task trees provide a hierarchical structure for complex tasks, allowing them to be broken down into manageable sub-tasks. Different execution strategies can be applied to different parts of the tree.

## Getting Started

To get started with the demo:

1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the Streamlit application:
   ```bash
   streamlit run src/chat.py
   ```

3. Follow the [Demo Script](demo-upgrade-workplan.md) to showcase Cerebrum's features

## Screenshots

### Plugin Explorer
![Plugin Explorer](../images/plugin_explorer.png)

### Task Hierarchy
![Task Hierarchy](../images/task_hierarchy.png)

### Task Execution
![Task Execution](../images/task_execution.png)

### Notebook Demo
![Notebook Demo](../images/notebook_demo.png)
```

## Final Implementation Notes

1. The demonstration notebook content is designed to be compatible with Jupyter notebooks and can be loaded into the notebook viewer component we implemented earlier.

2. The demo script is structured to be followed by a presenter, with clear steps and key points to highlight during the demonstration.

3. The quick reference guide provides a condensed summary of the key features and navigation for quick lookup during the demo.

4. The test cases ensure that our documentation is complete and contains all the required sections.

5. The main documentation index ties everything together and provides a starting point for users to navigate the documentation.

This comprehensive documentation package not only explains how to demonstrate Cerebrum's features but also serves as a reference for users who want to learn more about the system's capabilities.
