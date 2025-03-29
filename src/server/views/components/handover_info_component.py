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
                            if hasattr(task.input_data, 'get') and task.input_data.get('previous_task_outputs', {}).get(input_task_id):
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
                        if hasattr(output_task.input_data, 'get') and output_task.input_data.get('previous_task_outputs', {}).get(task_id):
                            st.write("**Data sent:**")
                            st.json(output_task.input_data['previous_task_outputs'][task_id]) 