import streamlit as st
import asyncio
from typing import Dict, List, Any, Optional
import pandas as pd
import time
import logging

from ...models.task import Task
from ...models.tasks_manager import TasksManager
from ..controllers.task_view_controller import TaskHierarchyController

logger = logging.getLogger(__name__)

class TaskHandoverComponent:
    """Component for executing task sequences with handover."""
    
    def __init__(self, controller: TaskHierarchyController):
        """Initialize the component."""
        self.controller = controller
        self.logger = logging.getLogger(__name__)
    
    def render(self):
        """Render the task handover component."""
        st.subheader("Task Handover Execution")
        
        # Display explanation of task handover
        with st.expander("About Task Handover", expanded=False):
            st.markdown("""
            **Task Handover** allows you to run multiple tasks in sequence, with the output of each task 
            automatically passed as input to dependent tasks. This enables creating workflow pipelines 
            where each task builds on the previous ones.
            
            **How it works:**
            1. Tasks are executed in the order you select
            2. Each task can specify which previous tasks it depends on using the `input_from_tasks` field
            3. When a task runs, it receives the outputs from its dependencies
            4. Results are tracked and can be viewed after execution
            
            **Example uses:**
            - Research → Analysis → Report Generation
            - Data Collection → Data Cleaning → Visualization
            - Problem Definition → Brainstorming → Solution Implementation
            """)
        
        # Get available task managers and their tasks
        task_managers = self.controller.get_task_managers()
        
        if not task_managers:
            st.warning("No task managers found. Please create a task manager first.")
            return
        
        # Step 1: Select a task manager
        tm_options = {tm.id: f"{tm.name}" for tm in task_managers}
        selected_tm_id = st.selectbox(
            "Select Task Manager",
            options=list(tm_options.keys()),
            format_func=lambda x: tm_options[x],
            key="handover_tm_select"
        )
        
        # Get tasks for the selected task manager
        tasks = self.controller.get_tasks(selected_tm_id)
        
        if not tasks:
            st.warning(f"No tasks found for this task manager. Please create some tasks first.")
            st.info("Tasks need to have the 'input_from_tasks' field set to establish dependencies.")
            return
        
        # Display the dependency structure
        self._render_dependency_graph(tasks)
        
        # Step 2: Select tasks to run in sequence
        task_options = {task.id: f"{task.name}" for task in tasks}
        
        st.write("### Select Tasks to Run in Sequence")
        st.info("Tasks will be executed in the order selected. Choose carefully to ensure proper data flow.")
        
        # Using multiselect to allow selecting multiple tasks in order
        selected_task_ids = st.multiselect(
            "Select Tasks to Execute",
            options=list(task_options.keys()),
            format_func=lambda x: task_options[x],
            key="handover_tasks_select"
        )
        
        # Show dependency validation
        if selected_task_ids:
            is_valid, message = self._validate_task_sequence(tasks, selected_task_ids)
            if not is_valid:
                st.error(message)
            else:
                st.success(message)
        
        # Step 3: Execution controls
        st.write("### Execution Controls")
        
        # Optional input parameters
        with st.expander("Additional Input Parameters", expanded=False):
            input_data = st.text_area(
                "Input JSON (optional)",
                value="{}",
                help="JSON formatted input data to pass to the first task in the sequence"
            )
        
        # Execute button
        if st.button("Execute Task Sequence", disabled=not selected_task_ids or (selected_task_ids and not is_valid)):
            # Run the task sequence
            self._run_task_sequence(selected_tm_id, selected_task_ids, input_data)
    
    def _validate_task_sequence(self, tasks: List[Task], selected_task_ids: List[str]) -> tuple:
        """Validate that the selected task sequence satisfies all dependencies."""
        # Create a map of tasks for easy lookup
        task_map = {task.id: task for task in tasks}
        
        # Check if all selected tasks exist
        for task_id in selected_task_ids:
            if task_id not in task_map:
                return False, f"Task with ID {task_id} not found"
        
        # Check dependencies
        executed_tasks = set()
        
        for task_id in selected_task_ids:
            task = task_map[task_id]
            
            # Check if this task depends on any tasks
            if hasattr(task, 'input_from_tasks') and task.input_from_tasks:
                # For each dependency, check if it appears earlier in the sequence
                for dep_id in task.input_from_tasks:
                    if dep_id not in executed_tasks:
                        dep_name = task_map.get(dep_id, Task(name=dep_id)).name
                        return False, f"Task '{task.name}' depends on task '{dep_name}' which is not earlier in the sequence"
            
            # Mark this task as executed
            executed_tasks.add(task_id)
        
        return True, "Task sequence is valid. All dependencies are satisfied."
    
    def _render_dependency_graph(self, tasks: List[Task]):
        """Render a visualization of task dependencies."""
        # Create a dataframe for tasks with their dependencies
        task_data = []
        for task in tasks:
            dependencies = getattr(task, 'input_from_tasks', [])
            task_data.append({
                "ID": task.id,
                "Name": task.name,
                "Dependencies": ", ".join(dependencies) if dependencies else "None"
            })
        
        if task_data:
            st.write("### Task Dependencies")
            df = pd.DataFrame(task_data)
            st.dataframe(df, use_container_width=True)
    
    def _run_task_sequence(self, tasksmanager_id: str, task_ids: List[str], input_data: str):
        """Run the task sequence and display results."""
        # Create a placeholder for progress
        progress_placeholder = st.empty()
        results_placeholder = st.empty()
        
        # Create progress containers
        with progress_placeholder.container():
            st.write("### Executing Task Sequence")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create an async function to run the tasks
            async def execute_tasks():
                try:
                    # Parse input data as JSON
                    import json
                    try:
                        running_extra_params = json.loads(input_data) if input_data.strip() else {}
                    except json.JSONDecodeError:
                        st.error("Invalid JSON input. Using empty object instead.")
                        running_extra_params = {}
                    
                    # Call the controller to run the task sequence
                    status_text.write(f"Starting execution of {len(task_ids)} tasks...")
                    
                    # Execute the task sequence
                    results = await self.controller.run_task_sequence(
                        tasksmanager_id=tasksmanager_id,
                        task_ids=task_ids,
                        running_extra_params=running_extra_params
                    )
                    
                    # Display results
                    with results_placeholder.container():
                        st.write("### Task Sequence Results")
                        
                        # Create tabs for each task result
                        tabs = st.tabs([f"Task {i+1}: {task_ids[i]}" for i in range(len(task_ids))])
                        
                        for i, (task_id, tab) in enumerate(zip(task_ids, tabs)):
                            with tab:
                                # Get task details
                                task = self.controller.persistence_model.tasks.read(task_id)
                                
                                st.write(f"**Task Name:** {task.name}")
                                st.write(f"**Status:** {task.status}")
                                
                                # Show inputs (for tasks with dependencies)
                                if hasattr(task, 'input_data') and task.input_data:
                                    with st.expander("Input Data", expanded=False):
                                        st.json(task.input_data)
                                
                                # Show the result
                                if task_id in results:
                                    result_data = results[task_id]
                                    if "error" in result_data:
                                        st.error(f"Task failed: {result_data['error']}")
                                    elif "response" in result_data:
                                        st.write("**Result:**")
                                        st.write(result_data["response"])
                                    else:
                                        st.json(result_data)
                                else:
                                    st.warning("No result data available")
                                
                                # Show outputs (for reference by later tasks)
                                if hasattr(task, 'output_data') and task.output_data:
                                    with st.expander("Output Data", expanded=False):
                                        st.json(task.output_data)
                    
                    # Clear the progress display
                    progress_placeholder.empty()
                    
                except Exception as e:
                    self.logger.error(f"Error executing task sequence: {str(e)}", exc_info=True)
                    status_text.error(f"Error: {str(e)}")
            
            # Create a background task to update the progress
            async def update_progress():
                total_tasks = len(task_ids)
                for i in range(total_tasks):
                    # Update the progress bar
                    progress = (i) / total_tasks
                    progress_bar.progress(progress)
                    
                    # Update status text
                    if i < total_tasks:
                        task = self.controller.persistence_model.tasks.read(task_ids[i])
                        status_text.write(f"Executing task {i+1}/{total_tasks}: {task.name}")
                    
                    # Wait for a bit before checking again
                    await asyncio.sleep(0.5)
            
            # Run the tasks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create tasks and wait for them
            tasks_future = asyncio.gather(execute_tasks(), update_progress())
            loop.run_until_complete(tasks_future) 