import streamlit as st
from typing import Optional, Dict, Any
from ....models.task import Task
from ...models.view_state import ViewState

class TaskDialog:
    """Dialog for creating and editing tasks."""
    
    def __init__(self, view_state: ViewState, persistence_model):
        self.view_state = view_state
        self.persistence_model = persistence_model
        
    def render(self, parent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Render task creation/editing dialog."""
        st.subheader("Task Details")
        
        # Task basic info
        name = st.text_input("Task Name", key="task_name")
        description = st.text_area("Description", key="task_description")
        
        # Task metadata
        col1, col2 = st.columns(2)
        with col1:
            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High"],
                key="task_priority"
            )
        with col2:
            status = st.selectbox(
                "Status",
                ["Pending", "In Progress", "Completed"],
                key="task_status"
            )
            
        # Task relationships
        if parent_id:
            st.info(f"This task will be created under parent task: {parent_id}")
            
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save", use_container_width=True):
                if name:
                    task_data = {
                        "name": name,
                        "description": description,
                        "priority": priority.lower(),
                        "status": status.lower(),
                        "parent_id": parent_id
                    }
                    return task_data
                else:
                    st.error("Task name is required")
                    
        with col2:
            if st.button("Cancel", use_container_width=True):
                return None
