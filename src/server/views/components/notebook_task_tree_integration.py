"""
Notebook Task Tree Integration Component

This component integrates the notebook viewer with the task tree demo,
allowing users to view and interact with task tree demonstrations through notebooks.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..components.notebook_viewer_component import NotebookViewerComponent
from ..components.task_tree_demo_component import TaskTreeDemoComponent

class NotebookTaskTreeIntegration:
    """Component for integrating notebook viewer with task tree demo."""
    
    def __init__(self, controller):
        """Initialize the integration component."""
        self.controller = controller
        self.notebook_viewer = NotebookViewerComponent()
        self.task_tree_demo = TaskTreeDemoComponent(controller)
        
    def render(self):
        """Render the notebook task tree integration component."""
        st.write("## Task Tree Notebook Demonstrations")
        
        tab1, tab2, tab3 = st.tabs([
            "Task Tree Overview", 
            "Multi-Plugin Integration", 
            "Concert Trip Planner"
        ])
        
        with tab1:
            st.write("### Task Tree Overview")
            st.write("""
            This demonstration shows the basic structure and capabilities of the task tree system.
            It includes visualization of task dependencies, execution strategies, and data flow.
            """)
            
            notebook_path = Path("notebooks/task_tree_example.ipynb")
            if notebook_path.exists():
                self.notebook_viewer.render(str(notebook_path))
            else:
                st.warning(f"Notebook not found: {notebook_path}")
                
            if st.button("Load Task Tree Demo", key="load_task_tree_demo_overview"):
                with st.spinner("Loading task tree demo..."):
                    result = self.controller.load_state("state/task_tree_demo.json")
                    if result and "successfully" in str(result).lower():
                        st.success("Demo state loaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to load demo state: {result}")
        
        with tab2:
            st.write("### Multi-Plugin Integration")
            st.write("""
            This demonstration shows how different agent frameworks (CrewAI, AutoGen, SmolAgents)
            can work together in a task tree, with data handover between tasks.
            """)
            
            notebook_path = Path("notebooks/plugin_handover_demo.ipynb")
            if notebook_path.exists():
                self.notebook_viewer.render(str(notebook_path))
            else:
                st.warning(f"Notebook not found: {notebook_path}")
                
            st.write("### Multi-Plugin Task Tree Visualization")
            self.task_tree_demo.render()
        
        with tab3:
            st.write("### Concert Trip Planner")
            st.write("""
            This demonstration shows a concert trip planning system using CrewAI agents,
            with weather state integration and handover capabilities between tasks.
            """)
            
            notebook_path = Path("notebooks/weather-example.ipynb")
            if notebook_path.exists():
                self.notebook_viewer.render(str(notebook_path))
            else:
                st.warning(f"Notebook not found: {notebook_path}")
                
            if st.button("Load Concert Trip Planner Demo", key="load_concert_trip_demo"):
                with st.spinner("Loading concert trip planner demo..."):
                    result = self.controller.load_state("state/concert_travel_planner.json")
                    if result and "successfully" in str(result).lower():
                        st.success("Demo state loaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to load demo state: {result}")
