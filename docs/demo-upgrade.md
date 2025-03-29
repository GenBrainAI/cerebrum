# Cerebrum Demo Updrade 

## Reuirements 
As we are progressing with the development I realize that this framework is raising interest among other firms and colleges.
The issue is that the demonstrations that we have now (see the state directory) are relatively simple, except for the crewai, which is a good demonstration of the framework using crewai,
yet the core technologies are not presented in the demo.
Some of those technologies were not fully tested other than the unit test, for example  the task tree and the agentic plugins.
Further, the task manager is just a structure that runs only one task at a time, it's even not showing handover from task to the next.

I would  like to have the  ability to present more complex mechanisms, 
I am thinking maybe having handover between tasks may be nice and easy to implement, 
maybe we can demonstrated a simple task tree using two or three crewai plugins in the notebook (and if it may be easy to implement jupyter notebook embedding in the streamlit ui),
the only small issue is that we have two days for the upgrade.
 
I would like to construct a plan, do able plan that will significantly upgrade  Cerebrum presentability and usable featureset 

## Day 1: Agentic Plugin System & Task Handover

### Task 1: Enhanced Agentic Config View (4 hours)
1. Extend the existing Agentic Config View:
   - Add a "Plugin Explorer" tab to show available plugins
   - Create a visualization component for plugin handover flows
   - Add capabilities to load and display different plugin types

2. Create a Plugin Handover Demo State:
   - Create a specialized state showing multiple plugins
   - Configure tasks to demonstrate handover between plugins
   - Include sample data and results to showcase the flow

### Task 2: Task Hierarchy View Enhancement (5 hours)
1. Update the Task Hierarchy View:
   - Enhance to show task dependencies and handover relationships
   - Add visual indicators for data flow between tasks
   - Include task status tracking to show progression

2. Implement Handover Visualization:
   - Add a data flow diagram component
   - Show how outputs from one task feed into inputs of another
   - Color-code by plugin type to distinguish different frameworks

## Day 2: Notebook Integration & Advanced Demos

### Task 3: Multi-Plugin Notebook Demo (5 hours)
1. Create a Jupyter notebook demonstrating plugin system:
   - Show how to initialize and use multiple plugins
   - Demonstrate handover between CrewAI, AutoGen, and SmolAgents
   - Include visualizations of the execution flow
   - Add real examples with tool usage across plugins

2. Implement Notebook Integration with Streamlit:
   - Add streamlit-jupyter integration component
   - Create UI for selecting and viewing example notebooks
   - Add interactive controls for modifying notebook parameters

### Task 4: Task Tree Demo Implementation (4 hours)
1. Create a task tree demonstration:
   - Implement a hierarchical task structure with mixed plugins
   - Show different execution strategies (sequential, parallel)
   - Add visualization of execution flow through the tree
   - Include real-time progress tracking

### Task 5: Documentation and Demo Script (2 hours)
1. Create comprehensive documentation:
   - How-to guides for setting up plugin handover
   - Examples of task trees with different plugins
   - Explanation of execution strategies and their use cases

2. Prepare a demo script:
   - Step-by-step demonstration flow
   - Key features to highlight
   - Example prompts and scenarios

## Implementation Details

### Extending the Agentic Config View

```python
# Add to agentic_config_view.py
def render_plugin_explorer_tab():
    """Render the plugin explorer tab."""
    st.subheader("Agentic Plugin Explorer")
    
    # Get plugin manager from controller
    plugin_manager = st.session_state.agentic_controller.plugin_manager
    
    # Get all loaded plugins
    plugins = plugin_manager.list_plugins()
    
    if not plugins:
        st.warning("No plugins are currently loaded.")
        return
    
    # Create tabs for each plugin
    tabs = st.tabs([plugin["name"] for plugin in plugins])
    
    for i, plugin in enumerate(plugins):
        with tabs[i]:
            st.subheader(f"{plugin['name']} v{plugin['version']}")
            st.write(plugin["description"])
            
            # Show capabilities
            st.write("### Capabilities")
            for capability in plugin["capabilities"]:
                st.write(f"- {capability}")
            
            # Show status
            status = "Active" if plugin["is_initialized"] else "Inactive"
            st.write(f"**Status**: {status}")
            
            # Show example usage
            st.write("### Example Usage")
            st.code(f"""
# Create an agent with {plugin['name']}
agent = await plugin_manager.create_agent("{plugin['name']}", {{
    "role": "Researcher",
    "goal": "Find information about AI agents",
    "backstory": "Expert researcher with broad knowledge"
}})

# Execute a task with the agent
result = await plugin_manager.execute_task("{plugin['name']}", agent, {{
    "description": "Research the latest developments in AI agents",
    "expected_output": "A comprehensive research report"
}})
            """, language="python")
```

### Enhancing Task Hierarchy View for Handover

```python
# Add to task_view_controller.py
async def get_task_tree_with_handover(self):
    """Get the task hierarchy with handover relationships."""
    try:
        self.logger.info("Building task hierarchy tree with handover relationships...")
        
        # Create root node
        root = TreeNode(
            id=UUID('00000000-0000-0000-0000-000000000000'),
            name="Task Hierarchy",
            type="root",
            children=[]
        )
        
        # Get all task managers
        task_managers = self.global_persistence.tasksmanagers.list()
        
        # Create task manager nodes
        for tm in task_managers:
            tm_node = TreeNode(
                id=UUID(tm.id),
                name=f"{tm.name}",
                type="tasksmanager",
                data={"id": tm.id, "model": tm.model},
                children=[]
            )
            
            # Get tasks for this task manager
            tasks = [t for t in self.global_persistence.tasks.list() if t.tasksmanager_id == tm.id]
            
            # Create task nodes
            task_nodes = {}
            for task in tasks:
                task_node = TreeNode(
                    id=UUID(task.id),
                    name=f"{task.name}",
                    type="task",
                    data={
                        "id": task.id, 
                        "model": task.model, 
                        "tasksmanager_id": tm.id,
                        "plugin": getattr(task, "plugin", "default")
                    },
                    children=[]
                )
                task_nodes[task.id] = task_node
                tm_node.children.append(task_node)
            
            # Add handover relationships
            for task in tasks:
                if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
                    task_node = task_nodes[task.id]
                    # Add visual indicator for inputs
                    task_node.data["has_inputs"] = True
                    
                    # Create connections for each input
                    for input_task_id in task.input_from_tasks:
                        if input_task_id in task_nodes:
                            # Add connection indicator
                            input_node = task_nodes[input_task_id]
                            input_node.data["outputs_to"] = input_node.data.get("outputs_to", []) + [task.id]
            
            # Add the manager node
            root.children.append(tm_node)
        
        return root
    except Exception as e:
        self.logger.error(f"Error building task hierarchy tree: {str(e)}")
        return None
```

### Task Handover Implementation

```python
# Add to task_runner.py
async def run_task_sequence(self, tasksmanager_id: str, task_ids: List[str]):
    """Run a sequence of tasks with handover between them."""
    results = {}
    task_outputs = {}
    
    for task_id in task_ids:
        task = self.persistence_model.tasks.read(task_id)
        
        # If this task takes input from previous tasks
        if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
            # Gather inputs from all dependency tasks
            inputs = {}
            for input_task_id in task.input_from_tasks:
                if input_task_id in task_outputs:
                    inputs[input_task_id] = task_outputs[input_task_id]
            
            # Set input data
            if not hasattr(task, 'input_data'):
                task.input_data = {}
            task.input_data["previous_task_outputs"] = inputs
            self.persistence_model.tasks.update(task_id, task)
        
        # Run the task
        result = await self.run_task(tasksmanager_id, task_id)
        results[task_id] = result
        
        # Store output for potential dependent tasks
        task_outputs[task_id] = result
        
        # Update task output data
        if not hasattr(task, 'output_data'):
            task.output_data = {}
        task.output_data["result"] = result
        self.persistence_model.tasks.update(task_id, task)
    
    return results
```

### Multi-Plugin Notebook Demo

```python
# notebook/plugin_handover_demo.ipynb

# Import necessary components
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.agent_framework_config import AgentFrameworkConfig
import asyncio
import matplotlib.pyplot as plt
import networkx as nx

# Initialize plugin manager
plugin_manager = PluginManager()

# Load plugins
async def load_demo_plugins():
    """Load the necessary plugins for demonstration."""
    # Configure and load CrewAI
    crewai_config = AgentFrameworkConfig(
        name="crewai",
        version="1.0.0",
        description="CrewAI Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    await plugin_manager.load_plugin("src/server/plugins/crewai_plugin.py", crewai_config)
    
    # Configure and load AutoGen
    autogen_config = AgentFrameworkConfig(
        name="autogen",
        version="1.0.0",
        description="AutoGen Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    await plugin_manager.load_plugin("src/server/plugins/autogen_plugin.py", autogen_config)
    
    # Configure and load SmolAgents
    smolagents_config = AgentFrameworkConfig(
        name="smolagents",
        version="1.0.0",
        description="SmolAgents Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    await plugin_manager.load_plugin("src/server/plugins/smolagents_plugin.py", smolagents_config)

await load_demo_plugins()
print("✅ Plugins loaded successfully")

# Visualize the plugin flow
def visualize_plugin_flow():
    """Create a visual representation of plugin handover workflow."""
    G = nx.DiGraph()
    
    # Add nodes for each plugin and task
    G.add_node("CrewAI\nResearcher", color='lightblue')
    G.add_node("AutoGen\nAnalyst", color='lightgreen')
    G.add_node("SmolAgents\nWriter", color='lightsalmon')
    
    # Add edges showing data flow
    G.add_edge("CrewAI\nResearcher", "AutoGen\nAnalyst", label="Research Results")
    G.add_edge("AutoGen\nAnalyst", "SmolAgents\nWriter", label="Analysis Results")
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    pos = nx.spring_layout(G)
    
    # Draw nodes
    node_colors = [G.nodes[n]['color'] for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, width=2, arrowsize=20)
    
    # Add node labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Add edge labels
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10)
    
    plt.title("Plugin Handover Flow", fontsize=16)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

visualize_plugin_flow()

# Demo multi-plugin workflow
async def run_multi_plugin_workflow(topic="AI agents"):
    """Run a workflow that hands off between multiple plugins."""
    results = {
        "steps": [],
        "outputs": {}
    }
    
    # Step 1: CrewAI for research
    print("🔍 Step 1: CrewAI Research")
    results["steps"].append("Creating CrewAI researcher agent")
    researcher = await plugin_manager.create_agent("crewai", {
        "role": "Researcher",
        "goal": f"Find detailed information about {topic}",
        "backstory": "Expert researcher with broad knowledge of AI and technology"
    })
    
    research_task = {
        "description": f"Research the latest developments in {topic}, focusing on real-world applications, key technologies, and future trends.",
        "expected_output": "A comprehensive research report with key findings and insights"
    }
    
    results["steps"].append(f"Executing research task with CrewAI: {research_task['description']}")
    research_result = await plugin_manager.execute_task("crewai", researcher, research_task)
    print(f"✅ CrewAI Research completed")
    
    results["outputs"]["research"] = research_result.get("result", research_result)
    
    # Step 2: AutoGen for analysis
    print("\n📊 Step 2: AutoGen Analysis")
    results["steps"].append("Creating AutoGen analyst agent")
    analyst = await plugin_manager.create_agent("autogen", {
        "role": "Analyst",
        "goal": "Analyze research findings and identify key trends and patterns",
        "previous_results": results["outputs"]["research"]
    })
    
    analysis_task = {
        "description": "Analyze the research findings, identify key trends, and extract actionable insights",
        "input_data": {"research": results["outputs"]["research"]}
    }
    
    results["steps"].append(f"Executing analysis task with AutoGen: {analysis_task['description']}")
    analysis_result = await plugin_manager.execute_task("autogen", analyst, analysis_task)
    print(f"✅ AutoGen Analysis completed")
    
    results["outputs"]["analysis"] = analysis_result.get("result", analysis_result)
    
    # Step 3: SmolAgents for report generation
    print("\n📝 Step 3: SmolAgents Report Generation")
    results["steps"].append("Creating SmolAgents writer agent")
    report_writer = await plugin_manager.create_agent("smolagents", {
        "role": "Writer",
        "goal": "Create a final report based on the analysis",
        "previous_results": results["outputs"]["analysis"]
    })
    
    report_task = {
        "description": "Create a comprehensive final report based on the analysis, including executive summary, key findings, and recommendations",
        "input_data": {
            "analysis": results["outputs"]["analysis"],
            "research": results["outputs"]["research"]
        }
    }
    
    results["steps"].append(f"Executing report task with SmolAgents: {report_task['description']}")
    report_result = await plugin_manager.execute_task("smolagents", report_writer, report_task)
    print(f"✅ SmolAgents Report Generation completed")
    
    results["outputs"]["report"] = report_result.get("result", report_result)
    
    return results

# Run the demo with a specific topic
workflow_results = await run_multi_plugin_workflow("agentic frameworks and their business applications")

# Display the final output
print("\n🎉 Final Report:")
print(workflow_results["outputs"]["report"])
```
Yes, you can embed Jupyter notebooks in a Streamlit UI using the `streamlit-jupyter` package. This library provides a way to preview and develop Streamlit apps directly within Jupyter notebooks, and it also enables embedding Jupyter notebook content into Streamlit applications.

## Embedding Jupyter Notebooks in Streamlit

The `streamlit-jupyter` package offers a straightforward way to embed notebooks:

```python
import streamlit as st
from streamlit_jupyter import StreamlitPython

# Embed a Jupyter notebook
StreamlitPython("path/to/your/notebook.ipynb")
```

### Key Features:

1. **Simple integration**: The package allows for easy embedding of Jupyter notebooks in your Streamlit app.
2. **Interactive elements**: Supports many Jupyter interactive elements, including markdown, headings, data entry components, and plots.
3. **Development workflow**: You can develop in a notebook environment and then present the same content in Streamlit.

### Implementation for Plugin Handover Demo

For your plugin handover demo, you can create a component like this:

```python
# src/server/views/components/notebook_viewer_component.py
import streamlit as st
from streamlit_jupyter import StreamlitPython
from pathlib import Path

class NotebookViewerComponent:
    """Component for displaying Jupyter notebooks in Streamlit."""
    
    def __init__(self):
        """Initialize the component."""
        pass
    
    def render(self, notebook_path: str):
        """Render a Jupyter notebook in Streamlit."""
        st.write("## Notebook Demo")
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["Interactive Notebook", "Code View"])
        
        with tab1:
            # Use StreamlitPython to render the notebook
            StreamlitPython(notebook_path)
        
        with tab2:
            # Show the notebook source code
            with open(notebook_path, 'r') as f:
                st.code(f.read(), language='python')
```

Then, you can use this component in your Agentic Config View to display your plugin handover demo:

```python
# In agentic_config_view.py
def render_notebook_tab():
    """Render the notebook demonstration tab."""
    st.subheader("Plugin Handover Demonstration")
    
    # Create notebook viewer component
    notebook_viewer = NotebookViewerComponent()
    
    # Define available notebooks
    notebooks = {
        "Plugin Handover Demo": "notebooks/plugin_handover_demo.ipynb",
        "Task Tree Example": "notebooks/task_tree_example.ipynb",
        "Multi-Agent Collaboration": "notebooks/multi_agent_collaboration.ipynb"
    }
    
    # Let the user select a notebook
    selected_notebook = st.selectbox(
        "Select a demonstration notebook:", 
        list(notebooks.keys())
    )
    
    # Render the selected notebook
    notebook_path = notebooks[selected_notebook]
    if Path(notebook_path).exists():
        notebook_viewer.render(notebook_path)
    else:
        st.error(f"Notebook not found: {notebook_path}")
```

### Installation

You'll need to add the `streamlit-jupyter` package to your project dependencies:

```bash
pip install streamlit-jupyter
```

### Limitations

According to the GitHub repository, some Streamlit methods may not be fully supported in the Jupyter preview. However, they will work correctly when the notebook is embedded in Streamlit.

### Alternative Approach: Using iframes

If `streamlit-jupyter` doesn't meet your needs, you can also consider using an iframe to embed a Jupyter notebook that's been converted to HTML:

```python
def render_notebook_as_iframe(notebook_path: str, width="100%", height="800px"):
    """Render a Jupyter notebook as an iframe."""
    # Convert notebook to HTML first (requires nbconvert)
    import subprocess
    html_path = notebook_path.replace('.ipynb', '.html')
    subprocess.run(["jupyter", "nbconvert", "--to", "html", notebook_path])
    
    # Embed the HTML file in an iframe
    st.markdown(f'<iframe src="{html_path}" width="{width}" height="{height}"></iframe>', unsafe_allow_html=True)
```

This approach would require saving the HTML output somewhere accessible via a URL.

## Conclusion

Embedding Jupyter notebooks in your Streamlit UI is definitely possible and would be an excellent way to showcase your plugin handover and task tree capabilities. The `streamlit-jupyter` package offers the most straightforward integration, allowing you to display your notebooks with minimal effort.

This approach aligns well with your goal of demonstrating Cerebrum's advanced features and would provide an interactive, engaging way for users to understand the plugin system and task handover mechanisms.

[Source: GitHub - ddobrinskiy/streamlit-jupyter](https://github.com/ddobrinskiy/streamlit-jupyter)


This updated plan leverages the existing agentic config view and enhances it to showcase the plugin system and task handover capabilities. The implementation details provide concrete code examples that you can adapt and implement within your two-day timeframe.

By focusing on the visualization of task handover and plugin interactions, you'll create a compelling demonstration of Cerebrum's advanced features that will be impressive to potential customers and collaborators.
