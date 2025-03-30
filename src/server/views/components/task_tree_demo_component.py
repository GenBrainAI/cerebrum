"""
Task Tree Demo Component

This component provides UI elements for launching and interacting with the task tree demo.
It allows users to generate, load, and visualize the task tree demo state.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging
import asyncio
import sys

logger = logging.getLogger(__name__)

class TaskTreeDemoComponent:
    """Component for launching and visualizing the task tree demo."""
    
    def __init__(self, controller):
        """Initialize the component with the task hierarchy controller."""
        self.controller = controller
        
    def render(self):
        """Render the task tree demo component."""
        st.write("## Task Tree Demonstration")
        
        # Check if demo state exists
        demo_state_path = Path("state/task_tree_demo_state.json")
        demo_state_exists = demo_state_path.exists()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("### Demo Controls")
            
            if demo_state_exists:
                st.success("Task Tree demo state is available")
                
                # Load demo button
                if st.button("Load Task Tree Demo", key="load_task_tree_demo"):
                    with st.spinner("Loading demo state..."):
                        try:
                            result = self.controller.load_state("state/task_tree_demo_state.json")
                            if result and "successfully" in str(result).lower():
                                st.success("Demo state loaded successfully!")
                                # Force rerun to update UI
                                st.rerun()
                            else:
                                st.error(f"Failed to load demo state: {result}")
                        except Exception as e:
                            st.error(f"Error loading demo state: {str(e)}")
            else:
                st.warning("Task Tree demo state is not available")
                
                # Create demo button
                if st.button("Generate Task Tree Demo", key="generate_task_tree_demo"):
                    with st.spinner("Generating task tree demo state..."):
                        try:
                            # Import the setup function and run it
                            from src.state_setup.task_tree_demo import setup_task_tree_demo_state
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(setup_task_tree_demo_state())
                            loop.close()
                            
                            st.success("Demo state created successfully!")
                            st.info("Click 'Load Task Tree Demo' to load the created state")
                            # Force rerun to update UI
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate demo state: {str(e)}")
                            logger.exception("Error generating demo state")
            
            # Demo explanation
            st.write("### About This Demo")
            st.write("""
            This demo showcases the Task Tree capabilities of Cerebrum, including:
            
            - Hierarchical task structures
            - Multiple plugin integration (CrewAI, AutoGen, SmolAgents)
            - Task dependencies and data flow
            - Different execution strategies
            
            The demo presents a data processing pipeline with:
            1. Data acquisition using CrewAI
            2. Parallel analysis using AutoGen
            3. Report generation using SmolAgents
            """)
            
            # Technical capabilities
            st.write("### Technical Capabilities")
            st.write("""
            The task tree implementation demonstrates:
            
            - **Plugin system integration**: Different agent frameworks working together
            - **Execution strategies**: Sequential and parallel task execution
            - **Data handover**: Results flowing between tasks across plugin boundaries
            - **Visualization**: Interactive task tree visualization
            - **State management**: Proper serialization of complex task structures
            """)
        
        with col2:
            if demo_state_exists:
                st.write("### Demo Preview")
                
                try:
                    # Read preview data from state file
                    with open(demo_state_path, "r") as f:
                        state_data = json.load(f)
                    
                    # Check if we have task_trees collection data
                    try:
                        # Safely access collections
                        if "collections" in state_data and "task_trees" in state_data["collections"]:
                            task_trees = state_data["collections"]["task_trees"]
                            if task_trees and isinstance(task_trees, dict) and len(task_trees) > 0:
                                tree_id = list(task_trees.keys())[0]
                                tree_data = task_trees[tree_id]
                                
                                # Display tree information
                                st.write(f"**Tree Name:** {tree_data['name']}")
                                st.write(f"**Description:** {tree_data['description']}")
                                st.write(f"**Plugins:** {', '.join(tree_data.get('plugins', []))}")
                                
                                # Display task structure
                                st.write("**Task Structure:**")
                                st.code("""
Root: Data Pipeline Coordinator
  ├─ Data Acquisition (CrewAI)
  ├─ Market Analysis (AutoGen) ← Data Acquisition
  ├─ Technical Analysis (AutoGen) ← Data Acquisition
  └─ Report Generation (SmolAgents) ← Market Analysis, Technical Analysis
                                """)
                                
                                # Display data flow preview
                                if "task_tree_executions" in state_data.get("collections", {}):
                                    executions = state_data["collections"]["task_tree_executions"]
                                    if executions and isinstance(executions, dict) and len(executions) > 0:
                                        exec_id = list(executions.keys())[0]
                                        exec_data = executions[exec_id]
                                        
                                        if "data_flow" in exec_data:
                                            st.write("**Data Flow Preview:**")
                                            for flow in exec_data["data_flow"]:
                                                st.write(f"- {flow['from']} → {flow['to']}: {flow.get('data_type', 'Data')}")
                                
                                # Display a simple preview of execution strategy
                                st.write("**Execution Strategy Preview:**")
                                st.write("- Root and Data Acquisition: Sequential")
                                st.write("- Market and Technical Analysis: Parallel")
                                st.write("- Report Generation: Sequential (after analyses complete)")
                                
                                st.write("Load the demo to see the full interactive visualization")
                        else:
                            st.info("Load the demo to view the task tree")
                    except Exception as e:
                        logger.error(f"Error rendering task tree preview: {str(e)}")
                        st.info("Load the demo to view the task tree")
                except Exception as e:
                    st.error(f"Error reading demo preview: {str(e)}")
            else:
                st.info("Generate the demo to preview the task tree")
                
                # Display a preview of what will be created
                st.write("### What will be created:")
                st.write("""
                The demo will create a complete task tree with the following components:
                
                **Tasks**:
                - Data Pipeline Coordinator (Root)
                - Data Acquisition (CrewAI plugin)
                - Market Analysis (AutoGen plugin)
                - Technical Analysis (AutoGen plugin)
                - Report Generation (SmolAgents plugin)
                
                **Data Flow**:
                - Data Acquisition → Market Analysis and Technical Analysis
                - Market Analysis and Technical Analysis → Report Generation
                
                **Execution Strategy**:
                - Sequential execution for the overall pipeline
                - Parallel execution for analysis tasks
                """)
                
                # Show sample visualization preview
                st.write("### Sample Visualization Preview:")
                st.image("https://via.placeholder.com/800x400?text=Task+Tree+Visualization+Preview", use_column_width=True)

    def update_visualization(self, tasksmanager_id: Optional[str] = None):
        """Update the visualization based on the current state."""
        from src.server.views.components.task_tree_visualization_component import TaskTreeVisualizationComponent
        
        if not tasksmanager_id and hasattr(self.controller, 'global_persistence'):
            # Try to get current tasksmanager_id from controller
            if hasattr(self.controller, 'current_tasksmanager_id'):
                tasksmanager_id = self.controller.current_tasksmanager_id
        
        if tasksmanager_id:
            st.write("### Task Tree Visualization")
            visualization = TaskTreeVisualizationComponent(self.controller.global_persistence)
            visualization.render(tasksmanager_id=tasksmanager_id)
        else:
            st.info("Load the demo to view the visualization") 