# Implementation of Unit 2: Task Hierarchy View Enhancement

Let's implement the code for enhancing the Task Hierarchy View to display task handover relationships. I'll provide the complete implementation for all files that need to be created or modified.

## 1. Task Hierarchy Controller Enhancement

First, let's add the `get_task_tree_with_handover` method to the task view controller:

```python
# src/server/views/controllers/task_view_controller.py

# Add to existing imports
from uuid import UUID
from typing import Optional, List, Dict, Any
from ..models.tree_node import TreeNode

# Add this method to the TaskHierarchyController class
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
                        "model": getattr(task, "model", None), 
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

## 2. Enhanced Tree Component with Handover Visualization

Now, let's create an enhanced tree component that can visualize the handover relationships:

```python
# src/server/views/components/task_tree_handover_component.py

import streamlit as st
from typing import Dict, Any, Optional, List
from ..models.tree_node import TreeNode
from ..components.tree_component import TreeComponent
import uuid

class TaskTreeHandoverComponent(TreeComponent):
    """Enhanced tree component for visualizing task handover relationships."""
    
    def __init__(self, on_node_click=None):
        super().__init__(on_node_click)
        
    def render(self, tree_data: TreeNode, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Render the tree with handover relationships."""
        # Get base rendering from parent class
        result = super().render(tree_data, key)
        
        # Add handover connections visualization
        self._render_handover_connections(tree_data)
        
        return result
    
    def _render_handover_connections(self, tree_data: TreeNode):
        """Render visual connections showing handover relationships."""
        # First, collect all nodes with handover relationships
        nodes_with_handover = []
        self._collect_handover_nodes(tree_data, nodes_with_handover)
        
        if not nodes_with_handover:
            return
            
        # Render connections container
        st.markdown("""
        <style>
        .task-flow-container {
            position: relative;
            margin-top: 10px;
        }
        .task-flow-line {
            stroke: #2196F3;
            stroke-width: 2;
            stroke-dasharray: 5, 5;
        }
        .task-node.has-inputs {
            border-left: 3px solid #4CAF50 !important;
        }
        .task-node.has-outputs {
            border-right: 3px solid #2196F3 !important;
        }
        </style>
        <div class="task-flow-container" id="task-flow-container"></div>
        """, unsafe_allow_html=True)
        
        # Generate JavaScript for drawing connections
        js_code = """
        <script>
        function connectNodes(sourceId, targetId) {
            const sourceNode = document.getElementById(sourceId);
            const targetNode = document.getElementById(targetId);
            
            if (!sourceNode || !targetNode) return;
            
            const container = document.getElementById('task-flow-container');
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.style.position = 'absolute';
            svg.style.top = '0';
            svg.style.left = '0';
            svg.style.pointerEvents = 'none';
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            line.classList.add('task-flow-line');
            
            // Calculate positions
            const sourceRect = sourceNode.getBoundingClientRect();
            const targetRect = targetNode.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            const x1 = sourceRect.right - containerRect.left;
            const y1 = sourceRect.top + sourceRect.height/2 - containerRect.top;
            const x2 = targetRect.left - containerRect.left;
            const y2 = targetRect.top + targetRect.height/2 - containerRect.top;
            
            // Draw curved path
            const dx = Math.abs(x2 - x1) * 0.5;
            const path = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
            line.setAttribute('d', path);
            
            svg.appendChild(line);
            container.appendChild(svg);
        }
        </script>
        """
        st.markdown(js_code, unsafe_allow_html=True)
        
        # Generate connection calls for each handover relationship
        for node in nodes_with_handover:
            if "outputs_to" in node.data:
                for target_id in node.data["outputs_to"]:
                    # Create JS to connect the nodes
                    connect_js = f"""
                    <script>
                    // Connect {node.id} to {target_id}
                    (function() {{
                        setTimeout(function() {{
                            connectNodes("{node.id}", "{target_id}");
                        }}, 500);
                    }})();
                    </script>
                    """
                    st.markdown(connect_js, unsafe_allow_html=True)
    
    def _collect_handover_nodes(self, node: TreeNode, result: List):
        """Recursively collect nodes with handover relationships."""
        if node.data.get("has_inputs") or node.data.get("outputs_to"):
            result.append(node)
            
        for child in node.children:
            self._collect_handover_nodes(child, result)
    
    def render_task_node(self, node: TreeNode, parent_id=None) -> str:
        """Render a task node with handover indicators."""
        # Start with standard node rendering
        html = super().render_node(node, parent_id)
        
        # Add handover-specific classes
        has_inputs = node.data.get("has_inputs", False)
        has_outputs = "outputs_to" in node.data and len(node.data["outputs_to"]) > 0
        
        css_classes = []
        if has_inputs:
            css_classes.append("has-inputs")
        if has_outputs:
            css_classes.append("has-outputs")
        
        # Add classes to node HTML
        if css_classes and '<div class="tree-node' in html:
            html = html.replace('<div class="tree-node', 
                               f'<div class="tree-node {" ".join(css_classes)}')
        
        return html
```

## 3. Create CSS for Task Handover Styling

Let's add the necessary CSS to style the handover relationships:

```python
# src/server/static/css/task_handover.css

/* Task node with handover styling */
.tree-node.has-inputs {
    border-left: 3px solid #4CAF50 !important;
    position: relative;
}

.tree-node.has-outputs {
    border-right: 3px solid #2196F3 !important;
    position: relative;
}

.tree-node.has-inputs::before {
    content: '↓';
    position: absolute;
    left: -10px;
    top: 50%;
    transform: translateY(-50%);
    color: #4CAF50;
    font-weight: bold;
}

.tree-node.has-outputs::after {
    content: '↓';
    position: absolute;
    right: -10px;
    top: 50%;
    transform: translateY(-50%) rotate(270deg);
    color: #2196F3;
    font-weight: bold;
}

/* Task flow visualization */
.task-flow-container {
    position: relative;
    width: 100%;
    height: 100%;
}

.task-flow-line {
    stroke: #2196F3;
    stroke-width: 2;
    stroke-dasharray: 5, 5;
    fill: none;
}

.handover-tooltip {
    position: absolute;
    padding: 5px 10px;
    background-color: rgba(0, 0, 0, 0.7);
    color: white;
    border-radius: 4px;
    font-size: 12px;
    z-index: 1000;
    pointer-events: none;
}
```

## 4. Update Task Hierarchy View to Use Enhanced Component

Now, let's update the task hierarchy view to use our enhanced component:

```python
# src/pages/task_hierarchy_view.py

# Add to imports
from src.server.views.components.task_tree_handover_component import TaskTreeHandoverComponent

# Replace the existing tree component initialization with:
def init_components(self):
    """Initialize view components."""
    self.logger.info("Initializing task hierarchy components")
    self.tree_component = TaskTreeHandoverComponent(self.handle_node_click)
    # Other component initializations can stay the same
```

## 5. Add Handover Information Panel

Let's add a panel to show handover information when a task is selected:

```python
# src/server/views/components/handover_info_component.py

import streamlit as st
from typing import Optional, Dict, Any
from ...models.task import Task

class HandoverInfoComponent:
    """Component for displaying task handover information."""
    
    def __init__(self, persistence_model):
        """Initialize the component."""
        self.persistence_model = persistence_model
    
    def render(self, task_id: Optional[str] = None):
        """Render handover information for the selected task."""
        if not task_id:
            return
            
        # Get the task
        task = self.persistence_model.tasks.read(task_id)
        if not task:
            return
            
        # Check if task has handover relationships
        has_inputs = hasattr(task, 'input_from_tasks') and task.input_from_tasks
        has_outputs = False
        
        # Find tasks that use this task as input
        output_tasks = []
        for other_task in self.persistence_model.tasks.list():
            if (hasattr(other_task, 'input_from_tasks') and 
                other_task.input_from_tasks and 
                task_id in other_task.input_from_tasks):
                output_tasks.append(other_task)
                has_outputs = True
        
        # Only show panel if there are handover relationships
        if not has_inputs and not has_outputs:
            return
            
        # Render handover information
        st.subheader("Task Handover Information")
        
        if has_inputs:
            st.write("### Input From Tasks")
            for input_task_id in task.input_from_tasks:
                input_task = self.persistence_model.tasks.read(input_task_id)
                if input_task:
                    with st.expander(f"Input from: {input_task.name}"):
                        st.write(f"**Task ID:** {input_task.id}")
                        st.write(f"**Description:** {input_task.description}")
                        
                        # Show data passed if available
                        if hasattr(task, 'input_data') and task.input_data:
                            if input_task_id in task.input_data.get('previous_task_outputs', {}):
                                st.write("**Data received:**")
                                st.json(task.input_data['previous_task_outputs'][input_task_id])
        
        if has_outputs:
            st.write("### Output To Tasks")
            for output_task in output_tasks:
                with st.expander(f"Output to: {output_task.name}"):
                    st.write(f"**Task ID:** {output_task.id}")
                    st.write(f"**Description:** {output_task.description}")
                    
                    # Show data passed if available
                    if (hasattr(task, 'output_data') and task.output_data and 
                        hasattr(output_task, 'input_data') and output_task.input_data):
                        if task_id in output_task.input_data.get('previous_task_outputs', {}):
                            st.write("**Data sent:**")
                            st.json(output_task.input_data['previous_task_outputs'][task_id])
```

## 6. Update Task Hierarchy View to Show Handover Info

Now, let's add the handover info component to the task hierarchy view:

```python
# src/pages/task_hierarchy_view.py

# Add to imports
from src.server.views.components.handover_info_component import HandoverInfoComponent

# Add this to the task details section
def render_task_details(self, task_id):
    """Render details for the selected task."""
    # Existing task details rendering...
    
    # Add handover information
    handover_info = HandoverInfoComponent(self.controller.global_persistence)
    handover_info.render(task_id)
```

## 7. Unit Tests for Task Handover Visualization

Let's create unit tests for our handover visualization components:

```python
# tests/views/controllers/test_task_view_controller.py

import pytest
from unittest.mock import MagicMock, patch
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.task import Task
from src.server.models.tasks_manager import TasksManager
from uuid import UUID

@pytest.mark.asyncio
async def test_get_task_tree_with_handover():
    # Setup persistence model with tasksmanager and tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasksmanager
    tm = TasksManager(id="tm1", name="Test Manager")
    persistence_model.tasksmanagers.create(tm)
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Task 1", tasksmanager_id="tm1", description="First task")
    task2 = Task(
        id="task2", 
        name="Task 2", 
        tasksmanager_id="tm1",
        description="Second task",
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

@pytest.mark.asyncio
async def test_get_task_tree_with_handover_empty():
    # Setup empty persistence model
    persistence_model = InMemoryPersistenceModel()
    
    # Create controller
    controller = TaskHierarchyController(persistence_model)
    
    # Get tree with handover
    tree = await controller.get_task_tree_with_handover()
    
    # Assertions
    assert tree is not None
    assert len(tree.children) == 0  # No tasksmanagers
```

```python
# tests/views/components/test_handover_info_component.py

import pytest
from unittest.mock import MagicMock, patch
from src.server.views.components.handover_info_component import HandoverInfoComponent
from src.server.persistence.in_memory_persistence import InMemoryPersistenceModel
from src.server.models.task import Task

def test_handover_info_component_with_inputs():
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasks with dependencies
    task1 = Task(id="task1", name="Input Task", description="Provider task")
    task2 = Task(
        id="task2", 
        name="Current Task", 
        description="Consumer task",
        input_from_tasks=["task1"],
        input_data={
            "previous_task_outputs": {
                "task1": {"result": "Sample data from task1"}
            }
        }
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.json") as mock_json:
        
        mock_expander.return_value.__enter__.return_value = MagicMock()
        
        # Call render
        component.render("task2")
        
        # Assertions
        mock_subheader.assert_called_once()
        assert mock_write.call_count >= 1  # Called at least once
        assert mock_expander.call_count >= 1  # Called at least once
        assert mock_json.call_count >= 1  # Called at least once

def test_handover_info_component_with_outputs():
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create tasks with dependencies
    task1 = Task(
        id="task1", 
        name="Provider Task", 
        description="Provider task",
        output_data={"result": "Sample data from task1"}
    )
    task2 = Task(
        id="task2", 
        name="Consumer Task", 
        description="Consumer task",
        input_from_tasks=["task1"],
        input_data={
            "previous_task_outputs": {
                "task1": {"result": "Sample data from task1"}
            }
        }
    )
    
    persistence_model.tasks.create(task1)
    persistence_model.tasks.create(task2)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.json") as mock_json:
        
        mock_expander.return_value.__enter__.return_value = MagicMock()
        
        # Call render
        component.render("task1")
        
        # Assertions
        mock_subheader.assert_called_once()
        assert mock_write.call_count >= 1  # Called at least once
        assert mock_expander.call_count >= 1  # Called at least once
        assert mock_json.call_count >= 1  # Called at least once

def test_handover_info_component_no_handover():
    # Setup persistence model with tasks
    persistence_model = InMemoryPersistenceModel()
    
    # Create task with no handover
    task = Task(id="task1", name="Solo Task", description="Task with no handover")
    persistence_model.tasks.create(task)
    
    # Create component
    component = HandoverInfoComponent(persistence_model)
    
    # Test render with mocked streamlit
    with patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.write") as mock_write, \
         patch("streamlit.expander") as mock_expander:
        
        # Call render
        component.render("task1")
        
        # Assertions
        mock_subheader.assert_not_called()  # Should not be called for tasks without handover
        mock_write.assert_not_called()
        mock_expander.assert_not_called()
```

## 8. UI/UX Instructions for Task Hierarchy View Enhancement

To complete the task hierarchy view enhancement, follow these steps:

1. Copy all the code provided above to the appropriate files
2. Make sure the CSS file is loaded in the task hierarchy view by adding:

```python
# At the top of src/pages/task_hierarchy_view.py
def load_css():
    with open("src/server/static/css/task_handover.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Call this at the beginning of render_task_hierarchy_view()
load_css()
```

3. Update the view to use the enhanced tree component as shown above
4. Add the handover info component to the task details section
5. Run the tests to ensure everything works as expected

This implementation enhances the Task Hierarchy View to clearly show handover relationships between tasks, with visual indicators for tasks that provide inputs to or consume outputs from other tasks. The connections between related tasks are visualized with curved lines, and detailed handover information is shown when a task is selected.
