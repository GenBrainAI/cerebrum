"""
Goal Tree Viewer Component for the Self-Aware Cerebrum system.

This module provides a Streamlit component to visualize goal trees.
"""

import os
import streamlit as st
from typing import Dict, Optional, Any, List
import logging
import json
from pathlib import Path
import base64
import tempfile

from src.server.planning.goal_decomposition import DecomposedGoal, GoalType, DecompositionStrategy
from src.server.planning.goal_visualization import GoalTreeVisualization

logger = logging.getLogger(__name__)

class GoalTreeViewer:
    """Streamlit component for viewing goal trees."""
    
    def __init__(self, goal_decomposition_engine, temp_dir: Optional[str] = None):
        """
        Initialize the goal tree viewer.
        
        Args:
            goal_decomposition_engine: Instance of GoalDecompositionEngine
            temp_dir: Directory to store temporary files
        """
        self.goal_decomposition_engine = goal_decomposition_engine
        self.visualizer = GoalTreeVisualization(temp_dir)
        
    async def render(self, decomposed_goal_id: Optional[str] = None):
        """
        Render the goal tree viewer in the Streamlit UI.
        
        Args:
            decomposed_goal_id: ID of the decomposed goal to display
        """
        # Create container
        container = st.container()
        
        with container:
            # Header
            st.header("Goal Tree Visualization")
            
            # Get all decomposed goals
            all_goals = await self.goal_decomposition_engine.get_all_decomposed_goals()
            
            if not all_goals:
                st.info("No decomposed goals available. Create a goal to visualize it.")
                return
            
            # Select goal to visualize
            goal_options = {f"{g.name} ({g.id})": g.id for g in all_goals.values()}
            selected_goal_id = decomposed_goal_id or list(goal_options.values())[0]
            
            selected_goal_label = st.selectbox(
                "Select a goal to visualize:",
                options=list(goal_options.keys()),
                index=list(goal_options.values()).index(selected_goal_id) if selected_goal_id in goal_options.values() else 0
            )
            
            selected_goal_id = goal_options[selected_goal_label]
            decomposed_goal = all_goals.get(selected_goal_id)
            
            if not decomposed_goal:
                st.error(f"Goal with ID {selected_goal_id} not found.")
                return
            
            # Display goal info
            with st.expander("Goal Details", expanded=True):
                st.write(f"**Name:** {decomposed_goal.name}")
                st.write(f"**Description:** {decomposed_goal.description}")
                st.write(f"**Type:** {decomposed_goal.goal_type.name}")
                st.write(f"**Strategy:** {decomposed_goal.strategy.name}")
                st.write(f"**Created:** {decomposed_goal.creation_time}")
                st.write(f"**Status:** {decomposed_goal.status}")
                
                # Resource info
                st.write("**Resources:**")
                st.write(f"- Time required: {decomposed_goal.total_resources.time_hours} hours")
                st.write(f"- Complexity: {decomposed_goal.total_resources.complexity}/10")
                st.write(f"- Risk level: {decomposed_goal.total_resources.risk_level}/10")
                
                if decomposed_goal.total_resources.knowledge_requirements:
                    st.write("**Knowledge Requirements:**")
                    for req in decomposed_goal.total_resources.knowledge_requirements:
                        st.write(f"- {req}")
            
            # Visualization options
            st.subheader("Visualization")
            viz_type = st.radio(
                "Visualization type:",
                options=["Interactive", "SVG", "JSON"],
                horizontal=True
            )
            
            # Generate visualization
            if viz_type == "Interactive":
                html_path = await self.visualizer.create_interactive_html(decomposed_goal)
                
                # Read and display HTML
                with open(html_path, "r") as f:
                    html_content = f.read()
                    st.components.v1.html(html_content, height=600, scrolling=True)
                    
                # Download button
                with open(html_path, "rb") as f:
                    st.download_button(
                        label="Download HTML",
                        data=f,
                        file_name=f"goal_tree_{decomposed_goal.id}.html",
                        mime="text/html"
                    )
                    
            elif viz_type == "SVG":
                svg_path = await self.visualizer.create_svg_visualization(decomposed_goal)
                
                # Display SVG
                with open(svg_path, "rb") as f:
                    svg_content = f.read()
                    b64 = base64.b64encode(svg_content).decode("utf-8")
                    html = f'<img src="data:image/svg+xml;base64,{b64}" width="100%" />'
                    st.markdown(html, unsafe_allow_html=True)
                
                # Download button
                with open(svg_path, "rb") as f:
                    st.download_button(
                        label="Download SVG",
                        data=f,
                        file_name=f"goal_tree_{decomposed_goal.id}.svg",
                        mime="image/svg+xml"
                    )
                    
            elif viz_type == "JSON":
                json_path = await self.visualizer.create_json_export(decomposed_goal)
                
                # Display JSON
                with open(json_path, "r") as f:
                    json_content = json.load(f)
                    st.json(json_content)
                
                # Download button
                with open(json_path, "r") as f:
                    st.download_button(
                        label="Download JSON",
                        data=f,
                        file_name=f"goal_tree_{decomposed_goal.id}.json",
                        mime="application/json"
                    )
            
            # Critical path analysis
            with st.expander("Critical Path Analysis", expanded=False):
                critical_path = decomposed_goal.get_critical_path()
                
                if critical_path:
                    st.write("**Critical Path:**")
                    for i, subgoal_id in enumerate(critical_path):
                        subgoal = decomposed_goal.subgoals.get(subgoal_id)
                        if subgoal:
                            st.write(f"{i+1}. {subgoal.name} ({subgoal.resources.time_hours} hours)")
                    
                    total_critical_time = sum(
                        decomposed_goal.subgoals[sg_id].resources.time_hours 
                        for sg_id in critical_path if sg_id in decomposed_goal.subgoals
                    )
                    st.write(f"**Total critical path time:** {total_critical_time} hours")
                else:
                    st.write("No critical path found.")
                    
            # Subgoals table
            with st.expander("All Subgoals", expanded=False):
                if decomposed_goal.subgoals:
                    # Create dataframe-friendly structure
                    subgoals_data = []
                    for sg_id, subgoal in decomposed_goal.subgoals.items():
                        subgoals_data.append({
                            "ID": sg_id,
                            "Name": subgoal.name,
                            "Priority": subgoal.priority,
                            "Time (hrs)": subgoal.resources.time_hours,
                            "Status": subgoal.status,
                            "Parent": subgoal.parent_id or "None"
                        })
                    
                    # Display as table
                    st.dataframe(subgoals_data)
                else:
                    st.write("No subgoals available.") 