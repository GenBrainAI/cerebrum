# Cerebrum Demo Upgrade Workplan

This workplan outlines the tasks required to enhance Cerebrum's demonstration capabilities, focusing on the agentic plugin system and task handover features. The plan is structured into manageable units of work, each with implementation, testing, and UI/UX components.

## Day 1: Agentic Plugin System & Task Handover

### Unit 1: Task Handover Implementation (4 hours)

#### Code Implementation
1. Add input/output data fields to Task model:
```python
# In src/server/models/task.py
class Task:
    # Add fields for task handover
    input_from_tasks: List[str] = Field(default_factory=list)
    output_to_tasks: List[str] = Field(default_factory=list)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
```

2. Implement task sequence execution in TaskRunner:
```python
# In src/server/controllers/task_runner.py
async def run_task_sequence(self, tasksmanager_id: str, task_ids: List[str]):
    """Run a sequence of tasks with handover between them."""
    results = {}
    task_outputs = {}
    
    for task_id in task_ids:
        task = self.persistence_model.tasks.read(task_id)
        
        # If this task takes input from previous tasks
        if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
            # Gather inputs from dependency tasks
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

#### Unit Testing
1. Create test for task sequence execution:
```python
# In tests/controllers/test_task_runner.py
@pytest.mark.asyncio
async def test_run_task_sequence():
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasksmanager
    tm = TasksManager(id="tm1", name="Test Manager")
    persistence_model.tasksmanagers.create(tm)
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Task 1", tasksmanager_id="tm1")
    task2 = Task(
        id="task2", 
        name="Task 2", 
        tasksmanager_id="tm1",
        input_from_tasks=["task1"]
    )
    task3 = Task(
        id="task3", 
        name="Task 3", 
        tasksmanager_id="tm1",
        input_from_tasks=["task2"]
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    persistence_model.tasks.create(task3)
    
    # Create task runner
    task_runner = TaskRunner(persistence_model)
    await task_runner.initialize()
    
    # Test sequence execution
    results = await task_runner.run_task_sequence("tm1", ["task1", "task2", "task3"])
    
    # Assertions
    assert len(results) == 3
    assert "task1" in results
    assert "task2" in results
    assert "task3" in results
    
    # Verify that dependencies were passed correctly
    task2_updated = persistence_model.tasks.read("task2")
    task3_updated = persistence_model.tasks.read("task3")
    
    assert "previous_task_outputs" in task2_updated.input_data
    assert "task1" in task2_updated.input_data["previous_task_outputs"]
    
    assert "previous_task_outputs" in task3_updated.input_data
    assert "task2" in task3_updated.input_data["previous_task_outputs"]
```

#### UI/UX Implementation
No UI changes required for this unit, as this is backend functionality.

### Unit 2: Task Hierarchy View Enhancement (5 hours)

#### Code Implementation
1. Add handover relationship rendering to task hierarchy tree:
```python
# In src/server/views/controllers/task_view_controller.py
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

#### Unit Testing
1. Test for task hierarchy with handover relationships:
```python
# In tests/views/controllers/test_task_view_controller.py
@pytest.mark.asyncio
async def test_get_task_tree_with_handover():
    # Setup persistence model with tasksmanager and tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasksmanager
    tm = TasksManager(id="tm1", name="Test Manager")
    persistence_model.tasksmanagers.create(tm)
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Task 1", tasksmanager_id="tm1")
    task2 = Task(
        id="task2", 
        name="Task 2", 
        tasksmanager_id="tm1",
        input_from_tasks=["task1"]
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create controller
    controller = TaskHierarchyController(persistence_model)
    
    # Get tree with handover
    tree = await controller.get_task_tree_with_handover()
    
    # Assertions
    assert tree is not None
    assert len(tree.children) == 1  # One tasksmanager
    
    tm_node = tree.children[0]
    assert len(tm_node.children) == 2  # Two tasks
    
    # Find task nodes
    task1_node = next((n for n in tm_node.children if n.name == "Task 1"), None)
    task2_node = next((n for n in tm_node.children if n.name == "Task 2"), None)
    
    assert task1_node is not None
    assert task2_node is not None
    
    # Check handover indicators
    assert task2_node.data.get("has_inputs", False) is True
    assert "outputs_to" in task1_node.data
    assert "task2" in task1_node.data["outputs_to"]
```

#### UI/UX Implementation
1. Add CSS for task handover indicators:
```css
/* In src/server/static/css/task_hierarchy.css */
.task-node.has-inputs {
    border-left: 3px solid #4CAF50;
}

.task-node.has-outputs {
    border-right: 3px solid #2196F3;
}

.task-flow-line {
    stroke: #2196F3;
    stroke-width: 2;
    stroke-dasharray: 5, 5;
    fill: none;
}
```

2. Update the tree rendering component to show connections:
```python
# In src/server/views/components/task_tree_component.py
def render_task_node(self, node, parent_id=None):
    """Render a task node with handover indicators."""
    # Base class rendering
    node_html = super().render_task_node(node, parent_id)
    
    # Add handover indicators
    has_inputs = node.data.get("has_inputs", False)
    has_outputs = "outputs_to" in node.data and len(node.data["outputs_to"]) > 0
    
    css_classes = []
    if has_inputs:
        css_classes.append("has-inputs")
    if has_outputs:
        css_classes.append("has-outputs")
    
    # Add classes to node HTML
    if css_classes:
        node_html = node_html.replace('<div class="task-node"', 
                                     f'<div class="task-node {" ".join(css_classes)}"')
    
    return node_html

def render_task_connections(self, nodes_data):
    """Render connections between tasks showing handover relationships."""
    connections_html = []
    
    for node in nodes_data:
        if "outputs_to" in node.data:
            for target_id in node.data["outputs_to"]:
                # Generate unique IDs for the SVG elements
                line_id = f"flow_{node.id}_{target_id}"
                
                # Add SVG path connecting the nodes
                connections_html.append(f'''
                <svg class="task-flow-diagram">
                    <path id="{line_id}" class="task-flow-line"></path>
                </svg>
                <script>
                    // Connect nodes with a curved line
                    connect_nodes("{node.id}", "{target_id}", "{line_id}");
                </script>
                ''')
    
    return "\n".join(connections_html)
```

## Day 2: Plugin System & Notebook Integration

### Unit 3: Plugin Explorer Component (3 hours)

#### Code Implementation
1. Create a component for exploring available plugins:
```python
# In src/server/views/components/plugin_explorer_component.py
import streamlit as st
from typing import Dict, Any, List

class PluginExplorerComponent:
    """Component for exploring available plugins."""
    
    def __init__(self, plugin_manager):
        """Initialize the component."""
        self.plugin_manager = plugin_manager
    
    def render(self):
        """Render the plugin explorer UI."""
        st.write("## Agent Framework Plugin Explorer")
        
        # Get all loaded plugins
        plugins = self.plugin_manager.list_plugins()
        
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

2. Add the plugin explorer to agentic config view:
```python
# In src/server/views/controllers/agentic_view_controller.py
async def initialize(self):
    # Existing initialization code...
    
    # Initialize plugin manager
    from server.plugins.plugin_manager import PluginManager
    self.plugin_manager = PluginManager()
    
    # Load available plugins
    from server.plugins.agent_framework_config import AgentFrameworkConfig
    
    # Load CrewAI plugin
    crewai_config = AgentFrameworkConfig(
        name="crewai",
        version="1.0.0",
        description="CrewAI Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    crewai_path = "src/server/plugins/crewai_plugin.py"
    await self.plugin_manager.load_plugin(crewai_path, crewai_config)
    
    # Load AutoGen plugin if available
    autogen_config = AgentFrameworkConfig(
        name="autogen",
        version="1.0.0",
        description="AutoGen Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    autogen_path = "src/server/plugins/autogen_plugin.py"
    await self.plugin_manager.load_plugin(autogen_path, autogen_config)
    
    # Load SmolAgents plugin if available
    smolagents_config = AgentFrameworkConfig(
        name="smolagents",
        version="1.0.0",
        description="SmolAgents Plugin",
        settings={"model": "gpt-4o-mini"}
    )
    smolagents_path = "src/server/plugins/smolagents_plugin.py"
    await self.plugin_manager.load_plugin(smolagents_path, smolagents_config)
```

#### Unit Testing
1. Test for plugin explorer component:
```python
# In tests/views/components/test_plugin_explorer_component.py
import pytest
from unittest.mock import MagicMock, patch
from src.server.views.components.plugin_explorer_component import PluginExplorerComponent

@pytest.mark.asyncio
async def test_plugin_explorer_component():
    # Create mock plugin manager
    mock_plugin_manager = MagicMock()
    mock_plugin_manager.list_plugins.return_value = [
        {
            "name": "crewai",
            "version": "1.0.0",
            "description": "CrewAI Plugin",
            "capabilities": ["agent_creation", "task_execution"],
            "is_initialized": True
        },
        {
            "name": "autogen",
            "version": "1.0.0",
            "description": "AutoGen Plugin",
            "capabilities": ["function_calling", "agent_handoff"],
            "is_initialized": True
        }
    ]
    
    # Create component
    component = PluginExplorerComponent(mock_plugin_manager)
    
    # Test render with mocked streamlit
    with patch("streamlit.write") as mock_write, \
         patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.code") as mock_code, \
         patch("streamlit.warning") as mock_warning:
        
        mock_tabs.return_value = [MagicMock(), MagicMock()]
        
        # Call render
        component.render()
        
        # Assertions
        mock_plugin_manager.list_plugins.assert_called_once()
        mock_tabs.assert_called_once()
        assert mock_subheader.call_count >= 2  # Called for each plugin
        assert mock_code.call_count >= 2  # Called for each plugin
        assert mock_warning.call_count == 0  # No warning shown
```

#### UI/UX Implementation
1. Update agentic_config_view.py to include a plugins tab:
```python
# In src/pages/agentic_config_view.py - add to render_agentic_config_view()
# After existing tabs creation
plugin_explorer_tab, observability_tab = st.tabs(["Plugin Explorer", "Observability"])

with plugin_explorer_tab:
    if 'agentic_controller' in st.session_state and hasattr(st.session_state.agentic_controller, 'plugin_manager'):
        plugin_explorer = PluginExplorerComponent(st.session_state.agentic_controller.plugin_manager)
        plugin_explorer.render()
    else:
        st.warning("Plugin manager not initialized")

with observability_tab:
    render_observability_view()
```

### Unit 4: Notebook Viewer Component (3 hours)

#### Code Implementation
1. Create notebook viewer component:
```python
# In src/server/views/components/notebook_viewer_component.py
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
            try:
                StreamlitPython(notebook_path)
            except Exception as e:
                st.error(f"Error rendering notebook: {str(e)}")
        
        with tab2:
            # Show the notebook source code
            try:
                with open(notebook_path, 'r') as f:
                    st.code(f.read(), language='python')
            except Exception as e:
                st.error(f"Error loading notebook source: {str(e)}")
```

2. Create a fallback iframe renderer if streamlit-jupyter isn't available:
```python
# In src/server/views/components/notebook_viewer_component.py - add this method
def render_as_iframe(self, notebook_path: str, width="100%", height="800px"):
    """Render a Jupyter notebook as an iframe (fallback method)."""
    st.write("## Notebook Demo (Static View)")
    
    try:
        # Check if notebook exists
        if not Path(notebook_path).exists():
            st.error(f"Notebook not found: {notebook_path}")
            return
            
        # Convert notebook to HTML first (requires nbconvert)
        import subprocess
        html_path = notebook_path.replace('.ipynb', '.html')
        result = subprocess.run([
            "jupyter", "nbconvert", 
            "--to", "html", 
            notebook_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error(f"Error converting notebook: {result.stderr}")
            return
            
        # Get the HTML file path
        html_file = Path(html_path)
        if not html_file.exists():
            st.error(f"HTML conversion failed, file not found: {html_file}")
            return
            
        # Embed the HTML file in an iframe
        st.markdown(
            f'<iframe src="{html_file}" width="{width}" height="{height}" frameborder="0"></iframe>', 
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Error rendering notebook: {str(e)}")
```

#### Unit Testing
1. Test for notebook viewer component:
```python
# In tests/views/components/test_notebook_viewer_component.py
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
from src.server.views.components.notebook_viewer_component import NotebookViewerComponent

def test_notebook_viewer_render():
    # Create component
    component = NotebookViewerComponent()
    
    # Mock notebook path
    notebook_path = "test_notebook.ipynb"
    
    # Mock Path.exists to return True
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="test notebook content")), \
         patch("streamlit_jupyter.StreamlitPython") as mock_streamlit_python, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.code") as mock_code, \
         patch("streamlit.error") as mock_error:
        
        mock_tabs.return_value = [MagicMock(), MagicMock()]
        
        # Call render
        component.render(notebook_path)
        
        # Assertions
        mock_write.assert_called_once()
        mock_tabs.assert_called_once()
        mock_streamlit_python.assert_called_once_with(notebook_path)
        mock_code.assert_called_once()
        mock_error.assert_not_called()

def test_notebook_viewer_file_not_found():
    # Create component
    component = NotebookViewerComponent()
    
    # Mock notebook path
    notebook_path = "nonexistent_notebook.ipynb"
    
    # Mock Path.exists to return False for the notebook
    with patch.object(Path, "exists", return_value=False), \
         patch("streamlit_jupyter.StreamlitPython") as mock_streamlit_python, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.error") as mock_error:
        
        mock_tabs.return_value = [MagicMock(), MagicMock()]
        
        # Call render
        component.render(notebook_path)
        
        # Assertions
        mock_write.assert_called_once()
        mock_tabs.assert_called_once()
        mock_error.assert_called()  # Error should be shown
        mock_streamlit_python.assert_not_called()  # StreamlitPython shouldn't be called
```

#### UI/UX Implementation
1. Add notebook tab to agentic config view:
```python
# In src/pages/agentic_config_view.py - add after plugin explorer tab
notebook_tab = st.tabs(["Plugins", "Notebooks", "Observability"])[1]

with notebook_tab:
    st.subheader("Plugin Handover Demonstration")
    
    # Create notebook viewer component
    from server.views.components.notebook_viewer_component import NotebookViewerComponent
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

2. Install required package in requirements.txt:
```
streamlit-jupyter==0.3.0
```

### Unit 5: Plugin Handover Demo Notebook (4 hours)

#### Code Implementation
1. Create demo notebook:
```python
# notebooks/plugin_handover_demo.ipynb

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

#### Unit Testing
1. Create test for the notebook execution (mock version):
```python
# tests/notebooks/test_plugin_handover.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import asyncio

@pytest.mark.asyncio
async def test_plugin_handover_notebook():
    """Test that the plugin handover notebook can be executed."""
    # Mock plugin manager
    mock_plugin_manager = MagicMock()
    mock_plugin_manager.load_plugin = AsyncMock(return_value=True)
    mock_plugin_manager.create_agent = AsyncMock(return_value="mock_agent")
    mock_plugin_manager.execute_task = AsyncMock(
        side_effect=[
            {"result": "Mock research results about agentic frameworks"},
            {"result": "Mock analysis of agentic frameworks research"},
            {"result": "Mock final report on agentic frameworks"}
        ]
    )
    
    # Prepare mocks
    with patch("src.server.plugins.plugin_manager.PluginManager", return_value=mock_plugin_manager), \
         patch("matplotlib.pyplot.figure"), \
         patch("matplotlib.pyplot.show"), \
         patch("networkx.spring_layout", return_value={}), \
         patch("networkx.draw_networkx_nodes"), \
         patch("networkx.draw_networkx_edges"), \
         patch("networkx.draw_networkx_labels"), \
         patch("networkx.draw_networkx_edge_labels"):
        
        # Execute notebook code (simplified without cell execution)
        # Load plugins
        await load_demo_plugins()
        
        # Visualize plugin flow
        visualize_plugin_flow()
        
        # Run workflow
        results = await run_multi_plugin_workflow("agentic frameworks")
        
        # Assertions
        assert mock_plugin_manager.load_plugin.call_count == 3  # Three plugins loaded
        assert mock_plugin_manager.create_agent.call_count == 3  # Three agents created
        assert mock_plugin_manager.execute_task.call_count == 3  # Three tasks executed
        
        # Check workflow results
        assert "research" in results["outputs"]
        assert "analysis" in results["outputs"]
        assert "report" in results["outputs"]
        assert "Mock research results" in results["outputs"]["research"]
        assert "Mock analysis" in results["outputs"]["analysis"]
        assert "Mock final report" in results["outputs"]["report"]
```

#### UI/UX Implementation
No specific UI implementation needed as the notebook provides its own visualization.

### Unit 6: Task Tree Demo State (4 hours)

#### Code Implementation
1. Create a task tree demo state generator:
```python
# In src/server/demos/task_tree_demo.py
from src.server.controllers.tasks_tree_controller import TaskTreeManager, ExecutionConfig, ExecutionStrategy
from src.server.models.task import Task
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.models.tasks_manager import TasksManager
from src.server.models.persistence_models import StorageLocation, StorageType
from src.server.controllers.persistence_controller import save_to_storage
from pathlib import Path
import json
import uuid

def create_multi_plugin_task_tree():
    """Create a task tree with multiple plugins for demonstration."""
    # Create persistence model
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Create tasksmanager
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Research Pipeline",
        description="A research pipeline using multiple AI frameworks",
        model="gpt-4o-mini"
    )
    persistence_model.tasksmanagers.create(tm)
    
    # Create root task (CrewAI)
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
    
    # Create level 1 tasks with different plugins
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
    
    # Create level 2 tasks
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
    
    # Create all tasks in persistence model
    for task in level1_tasks + level2_tasks:
        persistence_model.tasks.create(task)
    
    # Create task tree metadata
    tree_metadata = {
        "name": "Research Pipeline",
        "description": "A multi-plugin task tree demonstrating handover between different AI frameworks",
        "execution_strategy": "sequential",
        "root_task_id": "research_project"
    }
    
    # Store tree metadata
    persistence_model.collection("task_trees").create(
        "research_pipeline", 
        tree_metadata
    )
    
    return persistence_model, tm.id

def save_task_tree_demo_state():
    """Generate and save the task tree demo state."""
    # Create state
    persistence_model, tasksmanager_id = create_multi_plugin_task_tree()
    
    # Setup storage location
    state_dir = Path("state")
    state_dir.mkdir(exist_ok=True)
    
    location = StorageLocation(
        type=StorageType.file,
        location=str(state_dir),
        state_name="task_tree_demo"
    )
    
    # Create context state
    context_state = {
        "current_tasksmanager_id": tasksmanager_id,
        "current_task_id": "research_project"
    }
    
    # Manually add context to the serialized state
    json_str = persistence_model.to_json()
    state_dict = json.loads(json_str)
    state_dict["context_state"] = context_state
    
    # Save state manually
    state_file = state_dir / "task_tree_demo.json"
    with open(state_file, "w") as f:
        json.dump(state_dict, f, indent=2)
    
    return str(state_file)
```

#### Unit Testing
1. Test for task tree demo state creation:
```python
# In tests/demos/test_task_tree_demo.py
import pytest
from unittest.mock import patch, mock_open
from src.server.demos.task_tree_demo import create_multi_plugin_task_tree, save_task_tree_demo_state
import json
import os
from pathlib import Path

def test_create_multi_plugin_task_tree():
    # Create task tree
    persistence_model, tasksmanager_id = create_multi_plugin_task_tree()
    
    # Assertions
    # Verify tasksmanager
    tasksmanagers = persistence_model.tasksmanagers.list()
    assert len(tasksmanagers) == 1
    assert tasksmanagers[0].id == tasksmanager_id
    
    # Verify tasks
    tasks = persistence_model.tasks.list()
    assert len(tasks) >= 5  # Root + 3 level 1 + 1 level 2
    
    # Verify root task
    root_task = persistence_model.tasks.read("research_project")
    assert root_task is not None
    assert root_task.name == "Research Project"
    assert root_task.plugin == "crewai"
    
    # Verify task relationships
    level1_tasks = [t for t in tasks if t.parent_id == "research_project"]
    assert len(level1_tasks) == 3
    
    # Verify handover relationships
    market_analysis = persistence_model.tasks.read("market_analysis")
    assert "data_collection" in market_analysis.input_from_tasks
    
    report_task = persistence_model.tasks.read("report_generation")
    assert "market_analysis" in report_task.input_from_tasks
    assert "technical_research" in report_task.input_from_tasks
    
    # Verify tree metadata
    tree_collection = persistence_model.collection("task_trees")
    tree_metadata = tree_collection.read("research_pipeline")
    assert tree_metadata is not None
    assert tree_metadata["root_task_id"] == "research_project"

@pytest.mark.asyncio
async def test_save_task_tree_demo_state(tmp_path):
    # Mock state directory
    with patch("src.server.demos.task_tree_demo.Path") as mock_path:
        mock_path.return_value = tmp_path
        mock_path.mkdir.return_value = None
        
        # Mock open for write
        with patch("builtins.open", mock_open()) as mock_file:
            # Call save function
            state_file = save_task_tree_demo_state()
            
            # Assertions
            assert state_file is not None
            assert mock_file.call_count >= 1
            # Check JSON was written with context_state
            args, kwargs = mock_file().write.call_args
            assert "context_state" in args[0]
            assert "current_tasksmanager_id" in args[0]
            assert "current_task_id" in args[0]
            assert "research_project" in args[0]
```

#### UI/UX Implementation
1. Create a task tree demo launcher in the Task Hierarchy view:
```python
# In src/server/views/components/task_tree_demo_launcher.py
import streamlit as st
from pathlib import Path

class TaskTreeDemoLauncher:
    """Component for launching the task tree demo."""
    
    def __init__(self, task_controller):
        """Initialize the launcher."""
        self.controller = task_controller
    
    def render(self):
        """Render the task tree demo launcher."""
        st.write("## Task Tree Demonstration")
        
        # Check if demo state exists
        demo_state_path = Path("state/task_tree_demo.json")
        demo_state_exists = demo_state_path.exists()
        
        if demo_state_exists:
            st.info(
                "This demo showcases a multi-plugin task tree with handover between " +
                "different AI frameworks (CrewAI, AutoGen, SmolAgents)."
            )
            
            # Load demo button
            if st.button("Load Task Tree Demo"):
                # Load the demo state
                result = self.controller.load_state(str(demo_state_path))
                if result and "success" in result.lower():
                    st.success("Demo state loaded successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to load demo state: {result}")
        else:
            st.warning("Task tree demo state file not found. Generate it first.")
            
            # Generate demo button
            if st.button("Generate Task Tree Demo"):
                from src.server.demos.task_tree_demo import save_task_tree_demo_state
                try:
                    state_file = save_task_tree_demo_state()
                    st.success(f"Demo state generated successfully: {state_file}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate demo state: {str(e)}")
```

2. Add the launcher to the task hierarchy view:
```python
# In src/pages/task_hierarchy_view.py - add to render_task_hierarchy_view()
# Add demo section
with st.expander("Demonstration", expanded=False):
    from server.views.components.task_tree_demo_launcher import TaskTreeDemoLauncher
    demo_launcher = TaskTreeDemoLauncher(st.session_state.task_hierarchy_controller)
    demo_launcher.render()
```

### Unit 7: Documentation and Demo Script (2 hours)

#### Code Implementation
1. Create a documentation notebook:
```python
# notebooks/cerebrum_demos.ipynb

# Cerebrum Demos Documentation

## Overview

This notebook provides documentation and examples for Cerebrum's advanced features:

1. **Agentic Plugin System** - How different AI frameworks can be used through a unified plugin interface
2. **Task Handover** - How tasks can pass data between each other
3. **Task Trees** - How hierarchical task structures work with different execution strategies

## Agentic Plugin System

Cerebrum supports multiple AI agent frameworks through its plugin system:

- **CrewAI** - Multi-agent collaboration framework
- **AutoGen** - Microsoft's conversational agent framework
- **SmolAgents** - HuggingFace's lightweight agent framework

### How to Use the Plugin System

```python
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

# Initialize plugin manager
plugin_manager = PluginManager()

# Load a plugin
crewai_config = AgentFrameworkConfig(
    name="crewai",
    version="1.0.0",
    description="CrewAI Plugin",
    settings={"model": "gpt-4o-mini"}
)
await plugin_manager.load_plugin("src/server/plugins/crewai_plugin.py", crewai_config)

# Create an agent
agent = await plugin_manager.create_agent("crewai", {
    "role": "Researcher",
    "goal": "Find information about AI agents",
    "backstory": "Expert researcher with broad knowledge"
})

# Execute a task
result = await plugin_manager.execute_task("crewai", agent, {
    "description": "Research the latest developments in AI agents",
    "expected_output": "A comprehensive research report"
})
```

## Task Handover

Tasks can pass their outputs to other tasks through the handover mechanism:

```python
# Define tasks with handover
task1 = Task(
    id="data_collection",
    name="Data Collection",
    description="Collect relevant data"
)

task2 = Task(
    id="data_analysis",
    name="Data Analysis",
    description="Analyze collected data",
    input_from_tasks=["data_collection"]  # Takes output from task1
)

# Run tasks in sequence with handover
await task_runner.run_task_sequence(tasksmanager_id, ["data_collection", "data_analysis"])
```

## Task Trees

Task trees represent hierarchical relationships between tasks:

```python
from src.server.controllers.tasks_tree_controller import TaskTreeManager, ExecutionStrategy

# Create a task tree
manager = TaskTreeManager()

# Add nodes to the tree
manager.create_node(root_task)
manager.set_as_root(root_task.id)

manager.create_node(child_task1)
manager.create_node(child_task2)

# Set parent-child relationships
manager.add_child(root_task.id, child_task1.id)
manager.add_child(root_task.id, child_task2.id)

# Set execution strategy
manager.set_execution_strategy(root_task.id, ExecutionStrategy.SEQUENTIAL)
```

## Execution Strategies

Task trees support different execution strategies:

1. **Sequential** - Execute tasks one after another
2. **Parallel** - Execute independent tasks simultaneously
3. **Parallel with Limit** - Execute in parallel with a resource limit

## Demo Instructions

1. Load the Task Tree Demo state from the Task Hierarchy view
2. Explore the hierarchical structure of tasks
3. Note the different plugins used for different tasks
4. Observe the handover relationships between tasks
5. Run the tasks to see execution flow
```

#### Documentation Files
1. Create a demo script in Markdown:
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
4. Highlight the capabilities of each plugin

### Step 2: Show Notebook Demo
1. Click on the "Notebooks" tab
2. Select "Plugin Handover Demo" from the dropdown
3. Walk through the notebook showing how different plugins work together
4. Point out the visualization of the handover flow
5. Explain how data is passed between plugins

## Demo 2: Task Handover

### Step 1: Navigate to the Task Hierarchy View
1. In the Streamlit sidebar, select "Task Hierarchy" view
2. Open the "Demonstration" expander
3. Click "Load Task Tree Demo"
4. Once loaded, explore the task hierarchy
5. Point out the handover relationships shown in the UI

### Step 2: Execute Task Sequence
1. Select the root task "Research Project"
2. Click "Run Task"
3. Watch the execution flow through the tasks
4. Highlight how data flows from one task to another
5. Show the results of each task in the sequence

## Demo 3: Task Tree Visualization

### Step 1: Explore the Task Tree Structure
1. In the Task Hierarchy view with the demo loaded
2. Point out the parent-child relationships
3. Highlight the different plugins used for different tasks
4. Explain the execution strategy (sequential vs parallel)

### Step 2: Show Task Tree Advanced Features
1. Click on different tasks to see their details
2. Highlight the input-output relationships
3. Explain how the tree handles dependencies
4. Demonstrate how execution adapts to the tree structure

## Key Discussion Points
1. How the plugin system enables heterogeneous agent frameworks to work together
2. How task handover enables complex workflows
3. How task trees facilitate hierarchical reasoning and execution
4. The flexibility of Cerebrum in supporting diverse AI use cases
```

#### UI/UX Implementation
No specific UI implementation needed for documentation, only the demo itself.

## Final Steps

### Unit 8: Integration and Testing (2 hours)

1. Ensure all components work together
2. Verify demo states load correctly
3. Test all UI elements and interactions
4. Ensure notebook integration works properly
5. Check error handling and edge cases

### Unit 9: Final Polish (1 hour)

1. Add any missing CSS styling
2. Ensure consistent UI appearance
3. Check performance of all components
4. Verify documentation accuracy
5. Create a final demo state package

This workplan provides a comprehensive approach to enhancing Cerebrum's demonstration capabilities, focusing on the agentic plugin system and task handover features. Each unit has clear implementation tasks, testing procedures, and UI/UX considerations to ensure a successful upgrade within the two-day timeframe.
