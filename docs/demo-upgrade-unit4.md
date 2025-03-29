# Unit 4 Implementation: Notebook Viewer Component

I'll now implement the Notebook Viewer Component that allows embedding Jupyter notebooks in the Streamlit UI.

## Step 1: Create the notebook_viewer_component.py file

```python
# src/server/views/components/notebook_viewer_component.py
import streamlit as st
from pathlib import Path
import subprocess
import tempfile
import os
import base64

class NotebookViewerComponent:
    """Component for displaying Jupyter notebooks in Streamlit."""
    
    def __init__(self):
        """Initialize the component."""
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            # Try importing streamlit_jupyter if available
            import streamlit_jupyter
            self.has_streamlit_jupyter = True
        except ImportError:
            self.has_streamlit_jupyter = False
            st.info("For better notebook rendering, install: pip install streamlit-jupyter")
    
    def render(self, notebook_path: str):
        """Render a Jupyter notebook in Streamlit."""
        st.write("## Notebook Demo")
        
        # Check if the notebook exists
        if not Path(notebook_path).exists():
            st.error(f"Notebook not found: {notebook_path}")
            return
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["Interactive Notebook", "Code View"])
        
        with tab1:
            if self.has_streamlit_jupyter:
                # Use StreamlitPython to render the notebook
                try:
                    from streamlit_jupyter import StreamlitPython
                    StreamlitPython(notebook_path)
                except Exception as e:
                    st.error(f"Error rendering notebook with streamlit-jupyter: {str(e)}")
                    st.info("Falling back to static HTML rendering...")
                    self.render_as_iframe(notebook_path)
            else:
                # Use fallback method
                self.render_as_iframe(notebook_path)
        
        with tab2:
            # Show the notebook source code
            try:
                with open(notebook_path, 'r') as f:
                    notebook_content = f.read()
                st.code(notebook_content, language="python")
            except Exception as e:
                st.error(f"Error loading notebook source: {str(e)}")
    
    def render_as_iframe(self, notebook_path: str, width="100%", height="800px"):
        """Render a Jupyter notebook as an iframe (fallback method)."""
        try:
            # Convert notebook to HTML
            html_content = self._convert_notebook_to_html(notebook_path)
            if not html_content:
                st.error("Failed to convert notebook to HTML")
                return
            
            # Encode content to display in iframe
            encoded_html = base64.b64encode(html_content.encode()).decode()
            
            # Display in iframe
            st.markdown(
                f'<iframe src="data:text/html;base64,{encoded_html}" width="{width}" height="{height}" frameborder="0"></iframe>', 
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Error rendering notebook: {str(e)}")
    
    def _convert_notebook_to_html(self, notebook_path: str) -> str:
        """Convert a Jupyter notebook to HTML string."""
        try:
            # Create temporary file for HTML output
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_file:
                tmp_html_path = tmp_file.name
            
            # Convert notebook to HTML
            result = subprocess.run(
                [
                    "jupyter", "nbconvert", 
                    "--to", "html", 
                    "--template", "basic",
                    "--output", tmp_html_path,
                    notebook_path
                ], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                st.error(f"Error converting notebook: {result.stderr}")
                return None
            
            # Read HTML content
            with open(tmp_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Clean up temporary file
            try:
                os.unlink(tmp_html_path)
            except:
                pass
                
            return html_content
            
        except Exception as e:
            st.error(f"Error converting notebook: {str(e)}")
            return None
```

## Step 2: Create example notebooks for demonstration

```python
# notebooks/plugin_handover_demo.ipynb
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Plugin Handover Demonstration\n",
    "\n",
    "This notebook demonstrates how different agent frameworks can work together through Cerebrum's plugin system."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "# Import necessary components\n",
    "from src.server.plugins.plugin_manager import PluginManager\n",
    "from src.server.plugins.agent_framework_config import AgentFrameworkConfig\n",
    "import asyncio\n",
    "import matplotlib.pyplot as plt\n",
    "import networkx as nx"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Initialize Plugin Manager\n",
    "\n",
    "First, we initialize the plugin manager and load the available plugins."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "# Initialize plugin manager\n",
    "plugin_manager = PluginManager()\n",
    "\n",
    "# Load plugins\n",
    "async def load_demo_plugins():\n",
    "    \"\"\"Load the necessary plugins for demonstration.\"\"\"\n",
    "    # Configure and load CrewAI\n",
    "    crewai_config = AgentFrameworkConfig(\n",
    "        name=\"crewai\",\n",
    "        version=\"1.0.0\",\n",
    "        description=\"CrewAI Plugin\",\n",
    "        settings={\"model\": \"gpt-4o-mini\"}\n",
    "    )\n",
    "    await plugin_manager.load_plugin(\"src/server/plugins/crewai_plugin.py\", crewai_config)\n",
    "    \n",
    "    # Configure and load AutoGen\n",
    "    autogen_config = AgentFrameworkConfig(\n",
    "        name=\"autogen\",\n",
    "        version=\"1.0.0\",\n",
    "        description=\"AutoGen Plugin\",\n",
    "        settings={\"model\": \"gpt-4o-mini\"}\n",
    "    )\n",
    "    await plugin_manager.load_plugin(\"src/server/plugins/autogen_plugin.py\", autogen_config)\n",
    "    \n",
    "    # Configure and load SmolAgents\n",
    "    smolagents_config = AgentFrameworkConfig(\n",
    "        name=\"smolagents\",\n",
    "        version=\"1.0.0\",\n",
    "        description=\"SmolAgents Plugin\",\n",
    "        settings={\"model\": \"gpt-4o-mini\"}\n",
    "    )\n",
    "    await plugin_manager.load_plugin(\"src/server/plugins/smolagents_plugin.py\", smolagents_config)\n",
    "\n",
    "await load_demo_plugins()\n",
    "print(\"✅ Plugins loaded successfully\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Visualize Plugin Flow\n",
    "\n",
    "Let's create a visual representation of how the plugins will work together."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "# Visualize the plugin flow\n",
    "def visualize_plugin_flow():\n",
    "    \"\"\"Create a visual representation of plugin handover workflow.\"\"\"\n",
    "    G = nx.DiGraph()\n",
    "    \n",
    "    # Add nodes for each plugin and task\n",
    "    G.add_node(\"CrewAI\\nResearcher\", color='lightblue')\n",
    "    G.add_node(\"AutoGen\\nAnalyst\", color='lightgreen')\n",
    "    G.add_node(\"SmolAgents\\nWriter\", color='lightsalmon')\n",
    "    \n",
    "    # Add edges showing data flow\n",
    "    G.add_edge(\"CrewAI\\nResearcher\", \"AutoGen\\nAnalyst\", label=\"Research Results\")\n",
    "    G.add_edge(\"AutoGen\\nAnalyst\", \"SmolAgents\\nWriter\", label=\"Analysis Results\")\n",
    "    \n",
    "    # Create the plot\n",
    "    plt.figure(figsize=(10, 6))\n",
    "    pos = nx.spring_layout(G)\n",
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
    "visualize_plugin_flow()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Multi-Plugin Workflow\n",
    "\n",
    "Now let's implement a workflow that demonstrates handover between different plugins."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "# Demo multi-plugin workflow\n",
    "async def run_multi_plugin_workflow(topic=\"AI agents\"):\n",
    "    \"\"\"Run a workflow that hands off between multiple plugins.\"\"\"\n",
    "    results = {\n",
    "        \"steps\": [],\n",
    "        \"outputs\": {}\n",
    "    }\n",
    "    \n",
    "    # Step 1: CrewAI for research\n",
    "    print(\"🔍 Step 1: CrewAI Research\")\n",
    "    results[\"steps\"].append(\"Creating CrewAI researcher agent\")\n",
    "    researcher = await plugin_manager.create_agent(\"crewai\", {\n",
    "        \"role\": \"Researcher\",\n",
    "        \"goal\": f\"Find detailed information about {topic}\",\n",
    "        \"backstory\": \"Expert researcher with broad knowledge of AI and technology\"\n",
    "    })\n",
    "    \n",
    "    research_task = {\n",
    "        \"description\": f\"Research the latest developments in {topic}, focusing on real-world applications, key technologies, and future trends.\",\n",
    "        \"expected_output\": \"A comprehensive research report with key findings and insights\"\n",
    "    }\n",
    "    \n",
    "    results[\"steps\"].append(f\"Executing research task with CrewAI: {research_task['description']}\")\n",
    "    research_result = await plugin_manager.execute_task(\"crewai\", researcher, research_task)\n",
    "    print(f\"✅ CrewAI Research completed\")\n",
    "    \n",
    "    results[\"outputs\"][\"research\"] = research_result.get(\"result\", research_result)\n",
    "    \n",
    "    # Step 2: AutoGen for analysis\n",
    "    print(\"\\n📊 Step 2: AutoGen Analysis\")\n",
    "    results[\"steps\"].append(\"Creating AutoGen analyst agent\")\n",
    "    analyst = await plugin_manager.create_agent(\"autogen\", {\n",
    "        \"role\": \"Analyst\",\n",
    "        \"goal\": \"Analyze research findings and identify key trends and patterns\",\n",
    "        \"previous_results\": results[\"outputs\"][\"research\"]\n",
    "    })\n",
    "    \n",
    "    analysis_task = {\n",
    "        \"description\": \"Analyze the research findings, identify key trends, and extract actionable insights\",\n",
    "        \"input_data\": {\"research\": results[\"outputs\"][\"research\"]}\n",
    "    }\n",
    "    \n",
    "    results[\"steps\"].append(f\"Executing analysis task with AutoGen: {analysis_task['description']}\")\n",
    "    analysis_result = await plugin_manager.execute_task(\"autogen\", analyst, analysis_task)\n",
    "    print(f\"✅ AutoGen Analysis completed\")\n",
    "    \n",
    "    results[\"outputs\"][\"analysis\"] = analysis_result.get(\"result\", analysis_result)\n",
    "    \n",
    "    # Step 3: SmolAgents for report generation\n",
    "    print(\"\\n📝 Step 3: SmolAgents Report Generation\")\n",
    "    results[\"steps\"].append(\"Creating SmolAgents writer agent\")\n",
    "    report_writer = await plugin_manager.create_agent(\"smolagents\", {\n",
    "        \"role\": \"Writer\",\n",
    "        \"goal\": \"Create a final report based on the analysis\",\n",
    "        \"previous_results\": results[\"outputs\"][\"analysis\"]\n",
    "    })\n",
    "    \n",
    "    report_task = {\n",
    "        \"description\": \"Create a comprehensive final report based on the analysis, including executive summary, key findings, and recommendations\",\n",
    "        \"input_data\": {\n",
    "            \"analysis\": results[\"outputs\"][\"analysis\"],\n",
    "            \"research\": results[\"outputs\"][\"research\"]\n",
    "        }\n",
    "    }\n",
    "    \n",
    "    results[\"steps\"].append(f\"Executing report task with SmolAgents: {report_task['description']}\")\n",
    "    report_result = await plugin_manager.execute_task(\"smolagents\", report_writer, report_task)\n",
    "    print(f\"✅ SmolAgents Report Generation completed\")\n",
    "    \n",
    "    results[\"outputs\"][\"report\"] = report_result.get(\"result\", report_result)\n",
    "    \n",
    "    return results\n",
    "\n",
    "# Run the demo with a specific topic\n",
    "workflow_results = await run_multi_plugin_workflow(\"agentic frameworks and their business applications\")\n",
    "\n",
    "# Display the final output\n",
    "print(\"\\n🎉 Final Report:\")\n",
    "print(workflow_results[\"outputs\"][\"report\"])"
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
   "version": "3.8.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

## Step 3: Create test file for notebook viewer component

```python
# tests/views/components/test_notebook_viewer_component.py
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import sys
import os
import streamlit as st
from src.server.views.components.notebook_viewer_component import NotebookViewerComponent

def test_notebook_viewer_init():
    """Test notebook viewer initialization."""
    # Test with streamlit_jupyter available
    with patch.dict('sys.modules', {'streamlit_jupyter': MagicMock()}):
        component = NotebookViewerComponent()
        assert component.has_streamlit_jupyter is True
    
    # Test without streamlit_jupyter
    with patch.dict('sys.modules', {'streamlit_jupyter': None}):
        with patch('importlib.import_module', side_effect=ImportError):
            component = NotebookViewerComponent()
            assert component.has_streamlit_jupyter is False

def test_notebook_viewer_render_file_not_found():
    """Test notebook viewer when file is not found."""
    component = NotebookViewerComponent()
    
    # Mock Path.exists to return False
    with patch.object(Path, 'exists', return_value=False), \
         patch('streamlit.error') as mock_error, \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]):
        
        component.render('nonexistent.ipynb')
        
        # Check error was displayed
        mock_error.assert_called_once()
        assert "Notebook not found" in mock_error.call_args[0][0]

def test_notebook_viewer_render_with_streamlit_jupyter():
    """Test notebook viewer rendering with streamlit_jupyter."""
    component = NotebookViewerComponent()
    component.has_streamlit_jupyter = True
    
    # Mock a successful render
    with patch.object(Path, 'exists', return_value=True), \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]), \
         patch('streamlit.code') as mock_code, \
         patch('builtins.open', mock_open(read_data='notebook content')), \
         patch('streamlit_jupyter.StreamlitPython') as mock_streamlit_python:
        
        component.render('test.ipynb')
        
        # Check if StreamlitPython was called
        mock_streamlit_python.assert_called_once_with('test.ipynb')
        mock_code.assert_called_once()

def test_notebook_viewer_render_fallback():
    """Test notebook viewer fallback rendering."""
    component = NotebookViewerComponent()
    component.has_streamlit_jupyter = False
    
    # Mock the fallback render
    with patch.object(Path, 'exists', return_value=True), \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]), \
         patch('streamlit.code') as mock_code, \
         patch('builtins.open', mock_open(read_data='notebook content')), \
         patch.object(component, 'render_as_iframe') as mock_render_iframe:
        
        component.render('test.ipynb')
        
        # Check if fallback was called
        mock_render_iframe.assert_called_once_with('test.ipynb')
        mock_code.assert_called_once()

def test_convert_notebook_to_html():
    """Test notebook conversion to HTML."""
    component = NotebookViewerComponent()
    
    # Mock subprocess.run for successful conversion
    with patch('tempfile.NamedTemporaryFile', return_value=MagicMock(name='test.html')), \
         patch('subprocess.run', return_value=MagicMock(returncode=0)), \
         patch('builtins.open', mock_open(read_data='<html>content</html>')), \
         patch('os.unlink'):
        
        html = component._convert_notebook_to_html('test.ipynb')
        
        # Check if HTML was returned
        assert html == '<html>content</html>'

def test_convert_notebook_to_html_error():
    """Test notebook conversion error handling."""
    component = NotebookViewerComponent()
    
    # Mock subprocess.run for failed conversion
    with patch('tempfile.NamedTemporaryFile', return_value=MagicMock(name='test.html')), \
         patch('subprocess.run', return_value=MagicMock(returncode=1, stderr='conversion error')), \
         patch('streamlit.error') as mock_error:
        
        html = component._convert_notebook_to_html('test.ipynb')
        
        # Check if error was displayed
        mock_error.assert_called_once()
        assert html is None
```

## Step 4: Add the notebook tab to the agentic config view

```python
# Update src/pages/agentic_config_view.py - modify render_agentic_config_view()

async def render_agentic_config_view():
    """Render the agentic configuration view."""
    try:
        # ... existing code ...
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "🧩 Plugin Explorer", "📓 Notebooks", "📊 Observability"])
        
        # Chat View
        with tab1:
            st.subheader("Agentic Framework Chat")
            render_chat_view()
        
        # Plugin Explorer View
        with tab2:
            from src.server.views.components.plugin_explorer_component import PluginExplorerComponent
            
            if 'agentic_controller' in st.session_state and hasattr(st.session_state.agentic_controller, 'plugin_manager'):
                plugin_explorer = PluginExplorerComponent(st.session_state.agentic_controller.plugin_manager)
                plugin_explorer.render()
            else:
                st.warning("Plugin manager not initialized")
        
        # Notebook View - new
You're right. We should keep the predefined notebooks list as the primary set of demonstration notebooks, but also support loading from disk and creating new ones. Here's an improved implementation that maintains the predefined demos while adding support for discovering other existing notebooks and creating new ones:

```python
# Update the notebook tab section in src/pages/agentic_config_view.py

# Notebook View - improved to maintain predefined notebooks, load from disk, and create new ones
with tab3:
    st.subheader("Plugin Handover Demonstration Notebooks")
    
    from src.server.views.components.notebook_viewer_component import NotebookViewerComponent
    from pathlib import Path
    import json
    import os
    
    notebook_viewer = NotebookViewerComponent()
    
    # Ensure notebooks directory exists
    notebook_dir = Path("notebooks")
    if not notebook_dir.exists():
        notebook_dir.mkdir(parents=True)
    
    # Define predefined demonstration notebooks
    predefined_notebooks = {
        "Plugin Handover Demo": "notebooks/plugin_handover_demo.ipynb",
        "Task Tree Example": "notebooks/task_tree_example.ipynb",
        "Multi-Agent Collaboration": "notebooks/multi_agent_collaboration.ipynb"
    }
    
    # Create a tab section to separate predefined demos from other options
    demo_tab, browse_tab, create_tab = st.tabs(["Demo Notebooks", "Browse Notebooks", "Create Notebook"])
    
    # Tab 1: Demo Notebooks (Predefined)
    with demo_tab:
        # Check which predefined notebooks exist
        existing_demos = {
            name: path for name, path in predefined_notebooks.items() 
            if Path(path).exists()
        }
        
        if not existing_demos:
            st.warning("No demonstration notebooks have been created yet.")
            st.info("Please run the demo generation script to create the demonstration notebooks.")
        else:
            # Let user select from predefined demos
            selected_demo = st.selectbox(
                "Select a demonstration notebook:", 
                list(existing_demos.keys()),
                key="predefined_notebook_selector"
            )
            
            # Render the selected notebook
            notebook_path = existing_demos[selected_demo]
            notebook_viewer.render(notebook_path)
    
    # Tab 2: Browse Notebooks (Load from disk)
    with browse_tab:
        # Find all .ipynb files in the notebooks directory
        available_notebooks = list(notebook_dir.glob("*.ipynb"))
        
        # Filter out predefined notebooks to avoid duplication
        predefined_paths = set(predefined_notebooks.values())
        custom_notebooks = [nb for nb in available_notebooks if str(nb) not in predefined_paths]
        
        if not custom_notebooks:
            st.info("No custom notebooks found in the notebooks directory.")
        else:
            # Create a dictionary mapping display names to file paths
            custom_options = {
                notebook_path.stem.replace("_", " ").title(): str(notebook_path)
                for notebook_path in custom_notebooks
            }
            
            # Let the user select a notebook
            selected_custom = st.selectbox(
                "Select a notebook from disk:", 
                list(custom_options.keys()),
                key="custom_notebook_selector"
            )
            
            # Render the selected notebook
            notebook_path = custom_options[selected_custom]
            notebook_viewer.render(notebook_path)
            
        # Add a file uploader for notebook files
        uploaded_file = st.file_uploader("Upload a notebook", type=["ipynb"])
        if uploaded_file is not None:
            # Save the uploaded file
            save_path = notebook_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"Notebook uploaded successfully: {uploaded_file.name}")
            
            # Option to view the uploaded notebook
            if st.button("View Uploaded Notebook"):
                notebook_viewer.render(str(save_path))
    
    # Tab 3: Create Notebook
    with create_tab:
        st.write("Create a new notebook template")
        
        # Basic notebook creation form
        new_notebook_name = st.text_input("Notebook Name", key="new_notebook_name")
        notebook_type = st.selectbox(
            "Notebook Type", 
            ["Empty Notebook", "Plugin Handover Template", "Task Tree Template"],
            key="notebook_type"
        )
        
        if st.button("Create Notebook"):
            if not new_notebook_name:
                st.error("Please enter a notebook name")
            else:
                # Create filename from the provided name
                filename = new_notebook_name.lower().replace(" ", "_")
                if not filename.endswith(".ipynb"):
                    filename += ".ipynb"
                
                new_notebook_path = notebook_dir / filename
                
                # Check if the file already exists
                if new_notebook_path.exists():
                    st.error(f"A notebook with the name '{filename}' already exists.")
                else:
                    # Create basic notebook structure based on selected type
                    if notebook_type == "Empty Notebook":
                        notebook_content = {
                            "cells": [
                                {
                                    "cell_type": "markdown",
                                    "metadata": {},
                                    "source": [f"# {new_notebook_name}\n\nCreated with Cerebrum notebook creator."]
                                },
                                {
                                    "cell_type": "code",
                                    "execution_count": None,
                                    "metadata": {},
                                    "source": ["# Your code here"],
                                    "outputs": []
                                }
                            ],
                            "metadata": {
                                "kernelspec": {
                                    "display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"
                                }
                            },
                            "nbformat": 4,
                            "nbformat_minor": 4
                        }
                    elif notebook_type == "Plugin Handover Template":
                        # Get the content from the predefined demo if it exists
                        template_path = predefined_notebooks["Plugin Handover Demo"]
                        if Path(template_path).exists():
                            with open(template_path, 'r') as f:
                                notebook_content = json.load(f)
                                
                            # Update the title to reflect the new notebook name
                            if notebook_content["cells"][0]["cell_type"] == "markdown":
                                notebook_content["cells"][0]["source"] = [f"# {new_notebook_name}\n\nBased on the Plugin Handover Demo template."]
                        else:
                            st.error("Template not available. Please generate demo notebooks first.")
                            notebook_content = None
                    else:  # Task Tree Template
                        # Similar to the Plugin Handover template
                        template_path = predefined_notebooks["Task Tree Example"]
                        if Path(template_path).exists():
                            with open(template_path, 'r') as f:
                                notebook_content = json.load(f)
                                
                            # Update the title
                            if notebook_content["cells"][0]["cell_type"] == "markdown":
                                notebook_content["cells"][0]["source"] = [f"# {new_notebook_name}\n\nBased on the Task Tree Example template."]
                        else:
                            st.error("Template not available. Please generate demo notebooks first.")
                            notebook_content = None
                    
                    # Save the new notebook
                    if notebook_content:
                        with open(new_notebook_path, 'w') as f:
                            json.dump(notebook_content, f, indent=2)
                        
                        st.success(f"Notebook '{filename}' created successfully!")
                        
                        # Option to view the new notebook
                        if st.button("View New Notebook"):
                            notebook_viewer.render(str(new_notebook_path))

    # Add refresh button at the bottom
    if st.button("Refresh Notebooks"):
        st.rerun()
```

This implementation provides a complete solution with three tabs:

1. **Demo Notebooks**: Shows the predefined demonstration notebooks that are central to showcasing Cerebrum's capabilities.

2. **Browse Notebooks**: Allows users to browse and load custom notebooks from the notebooks directory, as well as upload their own notebooks.

3. **Create Notebook**: Enables users to create new notebooks from scratch or based on templates. This would be especially useful for your future AI helper that will generate notebooks to explain Cerebrum.

The code maintains your predefined notebooks as the primary demonstration set while adding flexibility for custom notebooks. The refresh button allows users to update the list if new notebooks are added externally.
        
        # Observability View
        with tab4:
            st.subheader("Agentic Framework Observability")
            render_observability_view()
            
        # ... existing code ...
        
    except Exception as e:
        st.error(f"Error rendering agentic config view: {str(e)}")
        print(f"Error in render_agentic_config_view: {str(e)}")
        raise
```

## Step 5: Update requirements.txt to include needed packages

```
# Add to requirements.txt
streamlit-jupyter>=0.3.0
jupyterlab>=3.0.0
nbconvert>=6.0.0
ipykernel>=6.0.0
matplotlib>=3.5.0
networkx>=2.7.0
```

## Step 6: Create notebook directory if it doesn't exist

```python
# Add to the main application startup script to ensure the notebooks directory exists

def ensure_notebook_directory():
    """Ensure the notebooks directory exists."""
    notebook_dir = Path("notebooks")
    if not notebook_dir.exists():
        notebook_dir.mkdir(parents=True)
    return notebook_dir

# Call this function during application startup
ensure_notebook_directory()
```

## UX/UI Instructions

1. The NotebookViewerComponent will appear on the Agentic Config View under the new "Notebooks" tab
2. It offers two views: Interactive Notebook and Code View
3. The Interactive View shows the notebook with live outputs if streamlit-jupyter is installed
4. The Code View shows the raw notebook code for reference
5. If streamlit-jupyter is not available, it falls back to a static HTML rendering

## Implementation Summary

The Notebook Viewer Component:
1. Allows viewing Jupyter notebooks directly in the Streamlit UI
2. Supports two different rendering methods:
   - Interactive rendering with streamlit-jupyter
   - Static HTML rendering as a fallback
3. Provides a tabs interface to switch between interactive view and code view
4. Includes error handling for missing notebooks or conversion issues
5. Comes with comprehensive tests for all functionality

This implementation enables users to explore notebook demonstrations of plugin handover and task tree functionality directly within the Cerebrum UI, providing a more integrated experience for understanding these advanced features.
