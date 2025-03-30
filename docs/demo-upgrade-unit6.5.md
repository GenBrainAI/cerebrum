# Unit 6.5: Task Manager Handover Sequence Implementation

## Overview
as for the tasks handover, I think that the task manager should have a flag to run an hand over syquence and than run the task within order, this way we can detect in the task runner that we should handover the syquesce and run it, and we can also easialy implement ui for that in the "task hierarchy view" -> "Task Management" view (need to have order for sub task in tasks manager.

This unit focuses on adding a handover sequence capability to the Task Manager, allowing it to run tasks in a specific order with automatic data handover between them. This feature will enable users to define task sequences within a TaskManager and visualize/execute them from the Task Hierarchy view.

## Code Implementation

### 1. Add Sequence Support to TasksManager Model

```python
# In src/server/models/tasks_manager.py

from typing import List, Dict, Any, Optional
from pydantic import Field
from uuid import uuid4
from datetime import datetime

class TaskSequence:
    """Represents an ordered sequence of tasks with handover enabled."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    task_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    enabled: bool = True
    
    def __init__(self, **data):
        """Initialize a task sequence."""
        for key, value in data.items():
            setattr(self, key, value)
        if not hasattr(self, 'created_at') or not self.created_at:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

class TasksManager:
    # Add to existing TasksManager class
    
    # Add task_sequences field
    task_sequences: Dict[str, TaskSequence] = Field(default_factory=dict)
    
    # Add methods for sequence management
    def add_sequence(self, sequence: TaskSequence) -> str:
        """Add a new task sequence to the manager."""
        if not hasattr(self, 'task_sequences'):
            self.task_sequences = {}
        self.task_sequences[sequence.id] = sequence
        self.updated_at = datetime.now()
        return sequence.id
    
    def update_sequence(self, sequence_id: str, sequence: TaskSequence) -> bool:
        """Update an existing task sequence."""
        if not hasattr(self, 'task_sequences'):
            self.task_sequences = {}
        if sequence_id in self.task_sequences:
            self.task_sequences[sequence_id] = sequence
            self.updated_at = datetime.now()
            return True
        return False
    
    def remove_sequence(self, sequence_id: str) -> bool:
        """Remove a task sequence."""
        if not hasattr(self, 'task_sequences'):
            return False
        if sequence_id in self.task_sequences:
            del self.task_sequences[sequence_id]
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_sequence(self, sequence_id: str) -> Optional[TaskSequence]:
        """Get a task sequence by ID."""
        if not hasattr(self, 'task_sequences'):
            return None
        return self.task_sequences.get(sequence_id)
    
    def get_sequences(self) -> List[TaskSequence]:
        """Get all task sequences."""
        if not hasattr(self, 'task_sequences'):
            self.task_sequences = {}
        return list(self.task_sequences.values())
```

### 2. Enhance TaskRunner to Support Sequences

```python
# In src/server/controllers/task_runner.py

from typing import List, Dict, Any, Optional
from ..models.tasks_manager import TasksManager, TaskSequence
from ..models.task import Task

class TaskRunner:
    # Add to existing TaskRunner class
    
    async def run_task_sequence_by_id(self, tasksmanager_id: str, sequence_id: str) -> Dict[str, Any]:
        """Run a task sequence by its ID."""
        # Get the TasksManager
        tasksmanager = self.persistence_model.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager not found: {tasksmanager_id}")
        
        # Get the TaskSequence
        sequence = tasksmanager.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Task sequence not found: {sequence_id}")
        
        # Run the sequence
        return await self.run_task_sequence(tasksmanager_id, sequence.task_ids)
    
    async def run_task_sequence(self, tasksmanager_id: str, task_ids: List[str]) -> Dict[str, Any]:
        """Run a sequence of tasks with handover between them."""
        results = {}
        task_outputs = {}
        
        # Track execution order and status
        execution_status = {
            "tasksmanager_id": tasksmanager_id,
            "sequence": task_ids,
            "current_task_index": 0,
            "completed_tasks": [],
            "failed_tasks": [],
            "task_results": {},
            "start_time": datetime.now(),
            "end_time": None,
            "status": "running"
        }
        
        # Store execution status in observable state
        if hasattr(self, '_active_observability_managers'):
            for task_id in task_ids:
                if task_id in self._active_observability_managers:
                    self._active_observability_managers[task_id].add_entry(
                        level="INFO",
                        message=f"Starting task sequence execution with {len(task_ids)} tasks",
                        metadata={"execution_status": execution_status}
                    )
        
        # Execute tasks in sequence
        for index, task_id in enumerate(task_ids):
            # Update execution status
            execution_status["current_task_index"] = index
            
            try:
                # Get the task
                task = self.persistence_model.tasks.read(task_id)
                if not task:
                    raise ValueError(f"Task not found: {task_id}")
                
                # Set up handover input if this isn't the first task
                if index > 0 and task_outputs:
                    # Create input_from_tasks if it doesn't exist
                    if not hasattr(task, 'input_from_tasks'):
                        task.input_from_tasks = []
                    
                    # Add previous task as input source if not already there
                    previous_task_id = task_ids[index - 1]
                    if previous_task_id not in task.input_from_tasks:
                        task.input_from_tasks.append(previous_task_id)
                    
                    # Set up input_data
                    if not hasattr(task, 'input_data'):
                        task.input_data = {}
                    
                    # Add previous tasks' outputs to input data
                    task.input_data["previous_task_outputs"] = {}
                    for prev_id, prev_output in task_outputs.items():
                        task.input_data["previous_task_outputs"][prev_id] = prev_output
                    
                    # Update the task with input data
                    self.persistence_model.tasks.update(task_id, task)
                
                # Log current task execution
                logger.info(f"Executing task {index+1}/{len(task_ids)}: {task.name} ({task_id})")
                
                # Run the task
                result = await self.run_task(tasksmanager_id, task_id)
                
                # Store result
                results[task_id] = result
                task_outputs[task_id] = result
                
                # Update execution status
                execution_status["completed_tasks"].append(task_id)
                execution_status["task_results"][task_id] = {
                    "status": "completed",
                    "execution_time": datetime.now().isoformat()
                }
                
                # Save output data to task
                updated_task = self.persistence_model.tasks.read(task_id)
                if not hasattr(updated_task, 'output_data'):
                    updated_task.output_data = {}
                updated_task.output_data["result"] = result
                self.persistence_model.tasks.update(task_id, updated_task)
                
            except Exception as e:
                logger.error(f"Error executing task {task_id} in sequence: {str(e)}")
                
                # Update execution status
                execution_status["failed_tasks"].append(task_id)
                execution_status["task_results"][task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "execution_time": datetime.now().isoformat()
                }
                
                # Log error to observability
                if hasattr(self, '_active_observability_managers'):
                    for obs_task_id in task_ids:
                        if obs_task_id in self._active_observability_managers:
                            self._active_observability_managers[obs_task_id].add_entry(
                                level="ERROR",
                                message=f"Task {task_id} failed: {str(e)}",
                                metadata={"error": str(e), "task_id": task_id}
                            )
                
                # Break sequence on error
                break
        
        # Update final execution status
        execution_status["end_time"] = datetime.now()
        execution_status["status"] = "completed" if len(execution_status["failed_tasks"]) == 0 else "failed"
        execution_status["execution_time"] = (execution_status["end_time"] - execution_status["start_time"]).total_seconds()
        
        # Log final status to observability
        if hasattr(self, '_active_observability_managers'):
            for task_id in task_ids:
                if task_id in self._active_observability_managers:
                    self._active_observability_managers[task_id].add_entry(
                        level="INFO",
                        message=f"Task sequence execution {execution_status['status']} in {execution_status['execution_time']} seconds",
                        metadata={"execution_status": execution_status}
                    )
        
        return {
            "results": results,
            "execution_status": execution_status
        }
```

### 3. Add TaskSequence Management to TaskHierarchyController

```python
# In src/server/views/controllers/task_view_controller.py

class TaskHierarchyController:
    # Add to existing TaskHierarchyController class
    
    async def create_task_sequence(self, tasksmanager_id: str, name: str, description: str, task_ids: List[str]) -> str:
        """Create a new task sequence."""
        # Get TasksManager
        tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager not found: {tasksmanager_id}")
        
        # Create sequence
        sequence = TaskSequence(
            name=name,
            description=description,
            task_ids=task_ids
        )
        
        # Add to TasksManager
        sequence_id = tasksmanager.add_sequence(sequence)
        
        # Update TasksManager
        self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
        
        return sequence_id
    
    async def update_task_sequence(self, tasksmanager_id: str, sequence_id: str, 
                                 name: Optional[str] = None, description: Optional[str] = None, 
                                 task_ids: Optional[List[str]] = None) -> bool:
        """Update an existing task sequence."""
        # Get TasksManager
        tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager not found: {tasksmanager_id}")
        
        # Get existing sequence
        sequence = tasksmanager.get_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Task sequence not found: {sequence_id}")
        
        # Update fields
        if name is not None:
            sequence.name = name
        if description is not None:
            sequence.description = description
        if task_ids is not None:
            sequence.task_ids = task_ids
        
        sequence.updated_at = datetime.now()
        
        # Update in TasksManager
        success = tasksmanager.update_sequence(sequence_id, sequence)
        
        # Update TasksManager
        self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
        
        return success
    
    async def delete_task_sequence(self, tasksmanager_id: str, sequence_id: str) -> bool:
        """Delete a task sequence."""
        # Get TasksManager
        tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager not found: {tasksmanager_id}")
        
        # Remove sequence
        success = tasksmanager.remove_sequence(sequence_id)
        
        # Update TasksManager
        if success:
            self.global_persistence.tasksmanagers.update(tasksmanager_id, tasksmanager)
        
        return success
    
    async def get_task_sequences(self, tasksmanager_id: str) -> List[Dict[str, Any]]:
        """Get all task sequences for a TasksManager."""
        # Get TasksManager
        tasksmanager = self.global_persistence.tasksmanagers.read(tasksmanager_id)
        if not tasksmanager:
            raise ValueError(f"TasksManager not found: {tasksmanager_id}")
        
        # Get sequences
        sequences = tasksmanager.get_sequences()
        
        # Convert to dicts for the view
        return [
            {
                "id": seq.id,
                "name": seq.name,
                "description": seq.description,
                "task_ids": seq.task_ids,
                "created_at": seq.created_at,
                "updated_at": seq.updated_at,
                "enabled": seq.enabled,
                "task_count": len(seq.task_ids)
            }
            for seq in sequences
        ]
    
    async def run_task_sequence(self, tasksmanager_id: str, sequence_id: str) -> Dict[str, Any]:
        """Run a task sequence."""
        # Initialize task runner if needed
        if not hasattr(self, 'task_runner'):
            self.task_runner = TaskRunner(self.global_persistence)
            await self.task_runner.initialize()
        
        # Run sequence
        result = await self.task_runner.run_task_sequence_by_id(tasksmanager_id, sequence_id)
        
        return result
```

### 4. Add TaskSequence Management Component to UI

```python
# In src/server/views/components/task_sequence_component.py

import streamlit as st
from typing import List, Dict, Any, Optional
import time

class TaskSequenceComponent:
    """Component for managing task sequences."""
    
    def __init__(self, controller):
        """Initialize the component."""
        self.controller = controller
    
    def render(self, tasksmanager_id: str):
        """Render the task sequence management component."""
        st.subheader("Task Sequences")
        
        # Get all tasks for this task manager
        tasks = self.controller.get_tasks_for_tasksmanager(tasksmanager_id)
        if not tasks:
            st.info("No tasks available for creating sequences.")
            return
        
        # Get existing sequences
        try:
            sequences = asyncio.run(self.controller.get_task_sequences(tasksmanager_id))
        except Exception as e:
            st.error(f"Error loading sequences: {str(e)}")
            sequences = []
        
        # Two tabs: View Sequences and Create Sequence
        view_tab, create_tab = st.tabs(["View Sequences", "Create Sequence"])
        
        with view_tab:
            self._render_sequences_list(tasksmanager_id, sequences, tasks)
        
        with create_tab:
            self._render_create_sequence_form(tasksmanager_id, tasks)
    
    def _render_sequences_list(self, tasksmanager_id: str, sequences: List[Dict[str, Any]], tasks: List[Any]):
        """Render the list of existing sequences."""
        if not sequences:
            st.info("No sequences defined yet. Create one using the 'Create Sequence' tab.")
            return
        
        # Create a task ID to name mapping for display
        task_id_to_name = {task.id: task.name for task in tasks}
        
        # Display each sequence
        for seq in sequences:
            with st.expander(f"{seq['name']} ({seq['task_count']} tasks)", expanded=False):
                st.write(f"**Description:** {seq['description']}")
                
                # Show tasks in sequence
                st.write("**Tasks (in order):**")
                for i, task_id in enumerate(seq['task_ids']):
                    task_name = task_id_to_name.get(task_id, f"Unknown Task ({task_id})")
                    st.write(f"{i+1}. {task_name}")
                
                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("Run Sequence", key=f"run_seq_{seq['id']}"):
                        with st.spinner("Running sequence..."):
                            try:
                                # Run the sequence
                                result = asyncio.run(self.controller.run_task_sequence(
                                    tasksmanager_id, seq['id']))
                                
                                # Show results
                                st.success("Sequence executed successfully!")
                                
                                # Show execution status
                                status = result.get("execution_status", {})
                                if status:
                                    st.json(status)
                            except Exception as e:
                                st.error(f"Error running sequence: {str(e)}")
                
                with col2:
                    if st.button("Edit", key=f"edit_seq_{seq['id']}"):
                        # Set session state for editing
                        st.session_state[f"edit_sequence_{seq['id']}"] = True
                
                with col3:
                    if st.button("Delete", key=f"delete_seq_{seq['id']}"):
                        try:
                            # Delete the sequence
                            success = asyncio.run(self.controller.delete_task_sequence(
                                tasksmanager_id, seq['id']))
                            
                            if success:
                                st.success("Sequence deleted!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to delete sequence.")
                        except Exception as e:
                            st.error(f"Error deleting sequence: {str(e)}")
                
                # Edit form (shown when edit button is clicked)
                if st.session_state.get(f"edit_sequence_{seq['id']}", False):
                    st.write("### Edit Sequence")
                    
                    # Edit form
                    name = st.text_input("Name", value=seq['name'], key=f"edit_name_{seq['id']}")
                    description = st.text_area("Description", value=seq['description'], key=f"edit_desc_{seq['id']}")
                    
                    # Task selection
                    selected_tasks = st.multiselect(
                        "Select Tasks (in execution order)",
                        options=[task.id for task in tasks],
                        default=seq['task_ids'],
                        format_func=lambda x: task_id_to_name.get(x, f"Unknown ({x})"),
                        key=f"edit_tasks_{seq['id']}"
                    )
                    
                    # Action buttons
                    save_col, cancel_col = st.columns(2)
                    
                    with save_col:
                        if st.button("Save Changes", key=f"save_edit_{seq['id']}"):
                            try:
                                # Update sequence
                                success = asyncio.run(self.controller.update_task_sequence(
                                    tasksmanager_id=tasksmanager_id,
                                    sequence_id=seq['id'],
                                    name=name,
                                    description=description,
                                    task_ids=selected_tasks
                                ))
                                
                                if success:
                                    st.success("Sequence updated!")
                                    # Clear edit state
                                    st.session_state[f"edit_sequence_{seq['id']}"] = False
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to update sequence.")
                            except Exception as e:
                                st.error(f"Error updating sequence: {str(e)}")
                    
                    with cancel_col:
                        if st.button("Cancel", key=f"cancel_edit_{seq['id']}"):
                            # Clear edit state
                            st.session_state[f"edit_sequence_{seq['id']}"] = False
                            st.rerun()
    
    def _render_create_sequence_form(self, tasksmanager_id: str, tasks: List[Any]):
        """Render the form for creating a new sequence."""
        st.write("### Create New Sequence")
        
        # Create form
        with st.form("create_sequence_form"):
            name = st.text_input("Sequence Name")
            description = st.text_area("Description")
            
            # Create task name mapping for display
            task_options = {task.id: f"{task.name}" for task in tasks}
            
            # Task selection
            selected_tasks = st.multiselect(
                "Select Tasks (in execution order)",
                options=list(task_options.keys()),
                format_func=lambda x: task_options[x]
            )
            
            # Submit button
            submitted = st.form_submit_button("Create Sequence")
            
            if submitted:
                if not name:
                    st.error("Sequence name is required.")
                elif not selected_tasks:
                    st.error("At least one task must be selected.")
                else:
                    try:
                        # Create sequence
                        sequence_id = asyncio.run(self.controller.create_task_sequence(
                            tasksmanager_id=tasksmanager_id,
                            name=name,
                            description=description,
                            task_ids=selected_tasks
                        ))
                        
                        st.success(f"Sequence '{name}' created successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating sequence: {str(e)}")
```

### 5. Integrate the TaskSequence Component into the Task Hierarchy View

```python
# In src/server/views/components/task_management_component.py

from .task_sequence_component import TaskSequenceComponent

class TaskManagementComponent:
    # Add to existing TaskManagementComponent class
    
    def _render_task_manager_details(self, tasksmanager: TasksManager):
        """Render details for a task manager."""
        # Existing implementation...
        
        # Add sequences tab
        details_tab, tasks_tab, sequences_tab = st.tabs(["Details", "Tasks", "Sequences"])
        
        with details_tab:
            # Existing details tab content...
            pass
            
        with tasks_tab:
            # Existing tasks tab content...
            pass
            
        with sequences_tab:
            # Add task sequence component
            sequence_component = TaskSequenceComponent(self.controller)
            sequence_component.render(tasksmanager.id)
```

### 6. Add Sequence Visualization to Task Tree View

```python
# In src/server/views/components/task_tree_component.py

class TaskTreeComponent:
    # Add to existing TaskTreeComponent class
    
    def render_sequence(self, tasksmanager_id: str, sequence_id: str):
        """Render a visual representation of a task sequence."""
        try:
            # Get TasksManager
            tasksmanager = self.controller.global_persistence.tasksmanagers.read(tasksmanager_id)
            if not tasksmanager:
                st.error(f"TasksManager not found: {tasksmanager_id}")
                return
            
            # Get sequence
            sequence = tasksmanager.get_sequence(sequence_id)
            if not sequence:
                st.error(f"Sequence not found: {sequence_id}")
                return
            
            # Get tasks
            tasks = []
            for task_id in sequence.task_ids:
                task = self.controller.global_persistence.tasks.read(task_id)
                if task:
                    tasks.append(task)
            
            # Render sequence diagram
            st.subheader(f"Sequence: {sequence.name}")
            st.write(f"**Description:** {sequence.description}")
            
            # Render sequence flow
            if tasks:
                # Draw boxes for each task with arrows between them
                html = """
                <style>
                .sequence-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 20px;
                }
                .sequence-flow {
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    overflow-x: auto;
                    padding: 10px;
                    width: 100%;
                }
                .task-box {
                    min-width: 150px;
                    max-width: 200px;
                    padding: 10px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    margin: 0 5px;
                    text-align: center;
                    background-color: #f9f9f9;
                }
                .arrow {
                    font-size: 24px;
                    margin: 0 5px;
                    color: #666;
                }
                .plugin-crewai { border-left: 4px solid #4CAF50; }
                .plugin-autogen { border-left: 4px solid #2196F3; }
                .plugin-smolagents { border-left: 4px solid #FF9800; }
                .plugin-default { border-left: 4px solid #9E9E9E; }
                </style>
                
                <div class="sequence-container">
                    <div class="sequence-flow">
                """
                
                # Add task boxes with arrows
                for i, task in enumerate(tasks):
                    # Determine plugin class
                    plugin_class = "plugin-default"
                    if hasattr(task, 'plugin'):
                        plugin_class = f"plugin-{task.plugin}"
                    
                    # Add task box
                    html += f"""
                    <div class="task-box {plugin_class}">
                        <div><b>{task.name}</b></div>
                        <div style="font-size: 0.8em; color: #666;">{task.id[:8]}...</div>
                    </div>
                    """
                    
                    # Add arrow if not the last task
                    if i < len(tasks) - 1:
                        html += '<div class="arrow">→</div>'
                
                html += """
                    </div>
                </div>
                """
                
                # Render HTML
                st.markdown(html, unsafe_allow_html=True)
                
                # Add run button
                if st.button("Run Sequence", key=f"run_vis_seq_{sequence_id}"):
                    with st.spinner("Running sequence..."):
                        try:
                            # Initialize task runner if needed
                            if not hasattr(self.controller, 'task_runner'):
                                self.controller.task_runner = TaskRunner(self.controller.global_persistence)
                                asyncio.run(self.controller.task_runner.initialize())
                            
                            # Run sequence
                            result = asyncio.run(self.controller.run_task_sequence(
                                tasksmanager_id, sequence_id))
                            
                            # Show results
                            st.success("Sequence executed successfully!")
                            
                            # Show execution status
                            status = result.get("execution_status", {})
                            if status:
                                st.json(status)
                        except Exception as e:
                            st.error(f"Error running sequence: {str(e)}")
            else:
                st.warning("No tasks found in this sequence.")
        except Exception as e:
            st.error(f"Error rendering sequence: {str(e)}")
```

## Unit Testing

### 1. Test TasksManager Sequence Support

```python
# tests/models/test_tasks_manager.py

import pytest
from src.server.models.tasks_manager import TasksManager, TaskSequence
import uuid

def test_task_sequence_creation():
    """Test creating a task sequence in a TasksManager."""
    # Create TasksManager
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager",
        description="Test manager description"
    )
    
    # Create sequence
    sequence = TaskSequence(
        name="Test Sequence",
        description="Test sequence description",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Add sequence to TasksManager
    sequence_id = tm.add_sequence(sequence)
    
    # Assertions
    assert sequence_id is not None
    assert hasattr(tm, 'task_sequences')
    assert sequence_id in tm.task_sequences
    assert tm.task_sequences[sequence_id].name == "Test Sequence"
    assert len(tm.task_sequences[sequence_id].task_ids) == 3

def test_task_sequence_update():
    """Test updating a task sequence."""
    # Create TasksManager with sequence
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id="seq1",
        name="Original Name",
        description="Original description",
        task_ids=["task1", "task2"]
    )
    
    tm.add_sequence(sequence)
    
    # Update sequence
    updated_sequence = TaskSequence(
        id="seq1",
        name="Updated Name",
        description="Updated description",
        task_ids=["task1", "task2", "task3"]
    )
    
    result = tm.update_sequence("seq1", updated_sequence)
    
    # Assertions
    assert result is True
    assert tm.task_sequences["seq1"].name == "Updated Name"
    assert tm.task_sequences["seq1"].description == "Updated description"
    assert len(tm.task_sequences["seq1"].task_ids) == 3

def test_task_sequence_remove():
    """Test removing a task sequence."""
    # Create TasksManager with sequence
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id="seq1",
        name="Test Sequence",
        task_ids=["task1", "task2"]
    )
    
    tm.add_sequence(sequence)
    
    # Remove sequence
    result = tm.remove_sequence("seq1")
    
    # Assertions
    assert result is True
    assert "seq1"
    ...
    ...


def test_task_sequence_remove():
    """Test removing a task sequence."""
    # Create TasksManager with sequence
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id="seq1",
        name="Test Sequence",
        task_ids=["task1", "task2"]
    )
    
    tm.add_sequence(sequence)
    
    # Remove sequence
    result = tm.remove_sequence("seq1")
    
    # Assertions
    assert result is True
    assert "seq1" not in tm.task_sequences

def test_get_sequences():
    """Test getting all sequences from a TasksManager."""
    # Create TasksManager
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    # Add sequences
    seq1 = TaskSequence(id="seq1", name="Sequence 1", task_ids=["task1", "task2"])
    seq2 = TaskSequence(id="seq2", name="Sequence 2", task_ids=["task3", "task4"])
    
    tm.add_sequence(seq1)
    tm.add_sequence(seq2)
    
    # Get sequences
    sequences = tm.get_sequences()
    
    # Assertions
    assert len(sequences) == 2
    assert any(s.id == "seq1" for s in sequences)
    assert any(s.id == "seq2" for s in sequences)
```

### 2. Test TaskRunner Sequence Execution

```python
# tests/controllers/test_task_runner.py

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.server.controllers.task_runner import TaskRunner
from src.server.models.tasks_manager import TasksManager, TaskSequence
from src.server.models.task import Task
import uuid

@pytest.fixture
def mock_persistence():
    """Create a mock persistence model for testing."""
    class MockPersistence:
        def __init__(self):
            self.tasksmanagers = MagicMock()
            self.tasks = MagicMock()
    
    return MockPersistence()

@pytest.mark.asyncio
async def test_run_task_sequence(mock_persistence):
    """Test running a task sequence."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tm_id, task_id):
        # Return a mock result
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "results" in result
    assert "execution_status" in result
    assert "task1" in result["results"]
    assert "task2" in result["results"]
    assert "task3" in result["results"]
    assert result["results"]["task1"] == "Result for task1"
    assert result["results"]["task2"] == "Result for task2"
    assert result["results"]["task3"] == "Result for task3"
    
    # Check execution status
    assert result["execution_status"]["tasksmanager_id"] == tasksmanager_id
    assert result["execution_status"]["sequence"] == ["task1", "task2", "task3"]
    assert result["execution_status"]["status"] == "completed"
    assert len(result["execution_status"]["completed_tasks"]) == 3
    assert len(result["execution_status"]["failed_tasks"]) == 0

@pytest.mark.asyncio
async def test_run_task_sequence_with_handover(mock_persistence):
    """Test running a task sequence with data handover."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tm_id, task_id):
        # Return a mock result
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "results" in result
    
    # Check that task2 has input from task1
    mock_persistence.tasks.update.assert_any_call("task2", task2)
    assert hasattr(task2, 'input_from_tasks')
    assert "task1" in task2.input_from_tasks
    assert hasattr(task2, 'input_data')
    assert "previous_task_outputs" in task2.input_data
    assert "task1" in task2.input_data["previous_task_outputs"]
    
    # Check that task3 has input from task2
    mock_persistence.tasks.update.assert_any_call("task3", task3)
    assert hasattr(task3, 'input_from_tasks')
    assert "task2" in task3.input_from_tasks
    assert hasattr(task3, 'input_data')
    assert "previous_task_outputs" in task3.input_data
    assert "task2" in task3.input_data["previous_task_outputs"]

@pytest.mark.asyncio
async def test_run_task_sequence_with_error(mock_persistence):
    """Test running a task sequence with an error."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    
    # Create task mocks
    task1 = Task(id="task1", name="Task 1", tasksmanager_id=tasksmanager_id)
    task2 = Task(id="task2", name="Task 2", tasksmanager_id=tasksmanager_id)
    task3 = Task(id="task3", name="Task 3", tasksmanager_id=tasksmanager_id)
    
    # Setup mock persistence
    def mock_read_task(task_id):
        if task_id == "task1":
            return task1
        elif task_id == "task2":
            return task2
        elif task_id == "task3":
            return task3
        return None
    
    mock_persistence.tasks.read.side_effect = mock_read_task
    
    # Setup TaskRunner with mock run_task method
    task_runner = TaskRunner(mock_persistence)
    
    async def mock_run_task(tm_id, task_id):
        if task_id == "task2":
            raise ValueError("Task 2 failed")
        return f"Result for {task_id}"
    
    task_runner.run_task = mock_run_task
    
    # Run sequence
    result = await task_runner.run_task_sequence(tasksmanager_id, ["task1", "task2", "task3"])
    
    # Assertions
    assert "execution_status" in result
    assert result["execution_status"]["status"] == "failed"
    assert "task1" in result["results"]
    assert "task2" not in result["results"]
    assert "task3" not in result["results"]
    assert len(result["execution_status"]["completed_tasks"]) == 1
    assert len(result["execution_status"]["failed_tasks"]) == 1
    assert "task2" in result["execution_status"]["failed_tasks"]
```

### 3. Test TaskHierarchyController Sequence Management

```python
# tests/views/controllers/test_task_view_controller.py

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.models.tasks_manager import TasksManager, TaskSequence
import uuid

@pytest.fixture
def mock_global_persistence():
    """Create a mock global persistence model."""
    class MockGlobalPersistence:
        def __init__(self):
            self.tasksmanagers = MagicMock()
            self.tasks = MagicMock()
    
    return MockGlobalPersistence()

@pytest.mark.asyncio
async def test_create_task_sequence(mock_global_persistence):
    """Test creating a task sequence."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    tasksmanager = TasksManager(id=tasksmanager_id, name="Test Manager")
    
    # Setup mock persistence
    mock_global_persistence.tasksmanagers.read.return_value = tasksmanager
    
    # Create controller
    controller = TaskHierarchyController(mock_global_persistence)
    
    # Create sequence
    sequence_id = await controller.create_task_sequence(
        tasksmanager_id=tasksmanager_id,
        name="Test Sequence",
        description="Test description",
        task_ids=["task1", "task2"]
    )
    
    # Assertions
    assert sequence_id is not None
    assert hasattr(tasksmanager, 'task_sequences')
    assert sequence_id in tasksmanager.task_sequences
    assert tasksmanager.task_sequences[sequence_id].name == "Test Sequence"
    assert tasksmanager.task_sequences[sequence_id].description == "Test description"
    assert len(tasksmanager.task_sequences[sequence_id].task_ids) == 2
    
    # Check that TasksManager was updated
    mock_global_persistence.tasksmanagers.update.assert_called_once_with(tasksmanager_id, tasksmanager)

@pytest.mark.asyncio
async def test_update_task_sequence(mock_global_persistence):
    """Test updating a task sequence."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    tasksmanager = TasksManager(id=tasksmanager_id, name="Test Manager")
    
    # Add a sequence to the manager
    sequence = TaskSequence(
        id="seq1",
        name="Original Name",
        description="Original description",
        task_ids=["task1", "task2"]
    )
    tasksmanager.add_sequence(sequence)
    
    # Setup mock persistence
    mock_global_persistence.tasksmanagers.read.return_value = tasksmanager
    
    # Create controller
    controller = TaskHierarchyController(mock_global_persistence)
    
    # Update sequence
    success = await controller.update_task_sequence(
        tasksmanager_id=tasksmanager_id,
        sequence_id="seq1",
        name="Updated Name",
        description="Updated description",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Assertions
    assert success is True
    assert tasksmanager.task_sequences["seq1"].name == "Updated Name"
    assert tasksmanager.task_sequences["seq1"].description == "Updated description"
    assert len(tasksmanager.task_sequences["seq1"].task_ids) == 3
    
    # Check that TasksManager was updated
    mock_global_persistence.tasksmanagers.update.assert_called_once_with(tasksmanager_id, tasksmanager)

@pytest.mark.asyncio
async def test_get_task_sequences(mock_global_persistence):
    """Test getting all task sequences for a TasksManager."""
    # Setup mock data
    tasksmanager_id = str(uuid.uuid4())
    tasksmanager = TasksManager(id=tasksmanager_id, name="Test Manager")
    
    # Add sequences to the manager
    seq1 = TaskSequence(id="seq1", name="Sequence 1", task_ids=["task1", "task2"])
    seq2 = TaskSequence(id="seq2", name="Sequence 2", task_ids=["task3", "task4"])
    
    tasksmanager.add_sequence(seq1)
    tasksmanager.add_sequence(seq2)
    
    # Setup mock persistence
    mock_global_persistence.tasksmanagers.read.return_value = tasksmanager
    
    # Create controller
    controller = TaskHierarchyController(mock_global_persistence)
    
    # Get sequences
    sequences = await controller.get_task_sequences(tasksmanager_id)
    
    # Assertions
    assert len(sequences) == 2
    assert any(s["id"] == "seq1" for s in sequences)
    assert any(s["id"] == "seq2" for s in sequences)
    assert any(s["name"] == "Sequence 1" for s in sequences)
    assert any(s["name"] == "Sequence 2" for s in sequences)
```

## UI/UX Implementation

### CSS for Sequence Flow Visualization

```css
/* Add to src/server/static/css/task_sequence.css */

.sequence-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 20px;
    overflow-x: auto;
    width: 100%;
}

.sequence-flow {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding: 15px;
    min-width: fit-content;
}

.task-box {
    min-width: 150px;
    max-width: 200px;
    padding: 15px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin: 0 8px;
    text-align: center;
    background-color: #f9f9f9;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

.task-box:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.arrow {
    font-size: 24px;
    margin: 0 10px;
    color: #666;
    display: flex;
    align-items: center;
}

.arrow::after {
    content: "";
    height: 2px;
    width: 20px;
    background-color: #666;
    margin-left: 5px;
}

.plugin-crewai { border-left: 5px solid #4CAF50; }
.plugin-autogen { border-left: 5px solid #2196F3; }
.plugin-smolagents { border-left: 5px solid #FF9800; }
.plugin-default { border-left: 5px solid #9E9E9E; }

.sequence-status {
    margin: 15px 0;
    padding: 10px;
    border-radius: 5px;
    background-color: #f1f1f1;
}

.sequence-controls {
    display: flex;
    justify-content: center;
    margin: 15px 0;
}

.sequence-progress {
    width: 100%;
    height: 5px;
    background-color: #e0e0e0;
    border-radius: 5px;
    margin: 10px 0;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background-color: #4CAF50;
    width: 0%;
    transition: width 0.3s ease;
}

.execution-log {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    margin: 15px 0;
    background-color: #f9f9f9;
    font-family: monospace;
}
```

### Integration into Task Management View

```python
# Update src/server/views/task_hierarchy_view.py

import streamlit as st
from src.server.views.controllers.task_view_controller import TaskHierarchyController
from src.server.views.components.task_management_component import TaskManagementComponent
from src.server.views.components.task_tree_component import TaskTreeComponent
from src.server.views.components.task_sequence_component import TaskSequenceComponent

def render_task_hierarchy_view():
    """Render the task hierarchy view."""
    st.title("Task Hierarchy")
    
    # Initialize controller
    controller = TaskHierarchyController()
    
    # Create tabs
    tree_tab, management_tab, sequences_tab = st.tabs(["Task Tree", "Task Management", "Task Sequences"])
    
    with tree_tab:
        # Tree component
        tree_component = TaskTreeComponent(controller)
        tree_component.render()
    
    with management_tab:
        # Management component
        management_component = TaskManagementComponent(controller)
        management_component.render()
    
    with sequences_tab:
        # Get task managers
        task_managers = controller.global_persistence.tasksmanagers.list()
        
        if not task_managers:
            st.info("No task managers available. Create a task manager first.")
            return
        
        # Select task manager
        selected_manager = st.selectbox(
            "Select Task Manager",
            options=[tm.id for tm in task_managers],
            format_func=lambda x: next((tm.name for tm in task_managers if tm.id == x), x),
            key="sequence_view_manager_selector"
        )
        
        # Render sequences for selected manager
        if selected_manager:
            st.subheader("Task Sequences")
            
            # Get sequences for this manager
            try:
                sequences = asyncio.run(controller.get_task_sequences(selected_manager))
                
                if not sequences:
                    st.info("No sequences defined for this task manager. Create one in the Task Management tab.")
                else:
                    # Select sequence to view
                    selected_sequence = st.selectbox(
                        "Select Sequence",
                        options=[seq["id"] for seq in sequences],
                        format_func=lambda x: next((seq["name"] for seq in sequences if seq["id"] == x), x),
                        key="sequence_viewer_selector"
                    )
                    
                    if selected_sequence:
                        # Render sequence visualization
                        tree_component = TaskTreeComponent(controller)
                        tree_component.render_sequence(selected_manager, selected_sequence)
                
            except Exception as e:
                st.error(f"Error loading sequences: {str(e)}")
```

## Summary

Unit 6.5 implements a task handover sequence capability that allows tasks to be executed in order with automatic data flow between them. The implementation includes:

1. **Enhanced Task Manager Model** with TaskSequence support, enabling ordered lists of tasks to be defined and stored.

2. **Task Runner Enhancements** to support running tasks in sequence with data handover between them.

3. **Task Hierarchy Controller Extensions** with methods for creating, updating, and deleting task sequences.

4. **UI Components** for managing and visualizing task sequences, including:
   - A sequence management component for creating and editing sequences
   - Task sequence visualization showing the flow of data between tasks
   - Integration into the Task Hierarchy view with a dedicated sequences tab

5. **Comprehensive Test Suite** testing all aspects of the implementation:
   - TaskSequence model tests
   - Task Runner sequence execution tests
   - Controller method tests

This implementation provides a streamlined way to demonstrate how tasks can be chained together with automatic handover of outputs to inputs, making it easy to create and run complex workflows through the UI.
