"""
Streamlit UI for the Research Planner component.

This module provides a UI for knowledge gap identification, research planning,
and research task management.
"""

import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import json
import os

from src.server.planning.research_planner import (
    ResearchPlanner,
    KnowledgeGap,
    ResearchTask,
    ResearchPlan,
    ResearchStrategyType
)
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem

class ResearchPlannerView:
    """Streamlit UI for the Research Planner."""
    
    def __init__(
        self,
        research_planner: Optional[ResearchPlanner] = None,
        knowledge_system: Optional[KnowledgeIntegrationSystem] = None
    ):
        """
        Initialize the Research Planner UI.
        
        Args:
            research_planner: Research planner instance
            knowledge_system: Knowledge integration system
        """
        self.knowledge_system = knowledge_system
        
        if not research_planner and knowledge_system:
            self.research_planner = ResearchPlanner(knowledge_system=knowledge_system)
        else:
            self.research_planner = research_planner
    
    def render(self):
        """Render the Research Planner UI."""
        st.title("Research Planner")
        
        if not self.research_planner:
            st.error("Research Planner not initialized. Please initialize with a Knowledge Integration System.")
            return
            
        # Initialize session state
        if "selected_tab" not in st.session_state:
            st.session_state.selected_tab = "Knowledge Gaps"
        if "knowledge_gaps" not in st.session_state:
            st.session_state.knowledge_gaps = {}
        if "current_plan_id" not in st.session_state:
            st.session_state.current_plan_id = None
        if "search_results" not in st.session_state:
            st.session_state.search_results = {}
        
        # Create tabs
        tabs = ["Knowledge Gaps", "Research Plans", "Task Dashboard"]
        selected_tab = st.radio("Select View:", tabs, index=tabs.index(st.session_state.selected_tab))
        st.session_state.selected_tab = selected_tab
        
        if selected_tab == "Knowledge Gaps":
            self._render_knowledge_gaps_tab()
        elif selected_tab == "Research Plans":
            self._render_research_plans_tab()
        elif selected_tab == "Task Dashboard":
            self._render_task_dashboard_tab()
    
    def _render_knowledge_gaps_tab(self):
        """Render the knowledge gaps identification tab."""
        st.header("Knowledge Gap Analysis")
        
        # Topic input and search button
        col1, col2 = st.columns([3, 1])
        with col1:
            topic = st.text_input("Enter a topic to analyze for knowledge gaps:", 
                                 placeholder="e.g., Machine Learning in Healthcare")
        with col2:
            search_button = st.button("Identify Gaps", key="search_gaps")
        
        # Run search when button is clicked
        if search_button and topic:
            with st.spinner(f"Analyzing knowledge gaps in '{topic}'..."):
                gaps = asyncio.run(self.research_planner.identify_knowledge_gaps(topic))
                st.session_state.knowledge_gaps = gaps
                st.session_state.search_results = {"topic": topic, "gaps": gaps}
        
        # Display search results
        if st.session_state.search_results and "gaps" in st.session_state.search_results:
            topic = st.session_state.search_results["topic"]
            gaps = st.session_state.search_results["gaps"]
            
            st.subheader(f"Knowledge Gaps for: {topic}")
            
            if not gaps:
                st.info("No knowledge gaps identified. The system has comprehensive knowledge on this topic.")
                return
            
            # Create a DataFrame for better visualization
            gap_data = []
            for gap_id, gap in gaps.items():
                gap_data.append({
                    "ID": gap_id,
                    "Topic": gap.topic,
                    "Description": gap.description,
                    "Confidence": gap.confidence,
                    "Importance": gap.importance,
                    "Related Gaps": len(gap.related_gaps)
                })
            
            if gap_data:
                # Sort by importance and confidence
                df = pd.DataFrame(gap_data).sort_values(by=["Importance", "Confidence"], 
                                                      ascending=[False, True])
                
                # Display the gaps
                st.dataframe(df, hide_index=True)
                
                # Gap visualization
                self._visualize_knowledge_gaps(gaps)
                
                # Create research plan from gaps
                st.subheader("Create Research Plan")
                
                # Select gaps to include
                selected_gaps = st.multiselect(
                    "Select knowledge gaps to address:",
                    options=[(gap_id, gap.topic) for gap_id, gap in gaps.items()],
                    format_func=lambda x: x[1],
                    default=[(gap_id, gap.topic) for gap_id, gap in gaps.items()]
                )
                
                # Plan details
                plan_title = st.text_input("Plan title:", 
                                         placeholder=f"Research Plan for {topic}")
                plan_description = st.text_area("Plan description:", 
                                             placeholder=f"Comprehensive research plan to address knowledge gaps in {topic}")
                
                # Create plan button
                if st.button("Create Research Plan") and selected_gaps and plan_title and plan_description:
                    with st.spinner("Creating research plan..."):
                        selected_gap_ids = [gap_id for gap_id, _ in selected_gaps]
                        plan = asyncio.run(self.research_planner.create_research_plan(
                            title=plan_title,
                            description=plan_description,
                            knowledge_gaps=selected_gap_ids
                        ))
                        
                        st.session_state.current_plan_id = plan.id
                        st.success(f"Research plan '{plan_title}' created successfully!")
                        st.session_state.selected_tab = "Research Plans"
                        st.rerun()
    
    def _visualize_knowledge_gaps(self, gaps: Dict[str, KnowledgeGap]):
        """
        Visualize knowledge gaps.
        
        Args:
            gaps: Dictionary of knowledge gaps
        """
        if not gaps:
            return
        
        st.subheader("Knowledge Gap Visualization")
        
        # Create a confidence vs importance scatter plot
        fig = px.scatter(
            x=[gap.confidence for gap in gaps.values()],
            y=[gap.importance for gap in gaps.values()],
            text=[gap.topic for gap in gaps.values()],
            size=[len(gap.related_gaps) + 1 for gap in gaps.values()],
            color=[gap.importance for gap in gaps.values()],
            color_continuous_scale="Viridis",
            labels={"x": "Confidence", "y": "Importance"},
            title="Knowledge Gaps by Confidence and Importance"
        )
        
        # Add quadrant labels for interpretation
        fig.add_shape(
            type="line", x0=0.5, y0=0, x1=0.5, y1=10,
            line=dict(color="Gray", width=1, dash="dot")
        )
        fig.add_shape(
            type="line", x0=0, y0=5.5, x1=1, y1=5.5,
            line=dict(color="Gray", width=1, dash="dot")
        )
        
        # Add quadrant annotations
        fig.add_annotation(x=0.25, y=7.5, text="Critical Gaps", showarrow=False)
        fig.add_annotation(x=0.75, y=7.5, text="Important Strengths", showarrow=False)
        fig.add_annotation(x=0.25, y=2.5, text="Low Priority", showarrow=False)
        fig.add_annotation(x=0.75, y=2.5, text="Well Understood", showarrow=False)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Network graph of related gaps
        if len(gaps) > 1:
            st.subheader("Knowledge Gap Relationships")
            
            # Create network data
            nodes = []
            for gap_id, gap in gaps.items():
                nodes.append({
                    "id": gap_id,
                    "label": gap.topic,
                    "size": gap.importance * 5
                })
            
            edges = []
            processed_pairs = set()
            for gap_id, gap in gaps.items():
                for related_id in gap.related_gaps:
                    # Avoid duplicates
                    pair = tuple(sorted([gap_id, related_id]))
                    if pair not in processed_pairs and related_id in gaps:
                        processed_pairs.add(pair)
                        edges.append({
                            "from": gap_id,
                            "to": related_id,
                            "width": 2
                        })
            
            # If there are edges to display
            if edges:
                # Create a simplified visualization using Plotly
                edge_x = []
                edge_y = []
                
                # Simple force-directed layout
                pos = self._simple_layout(nodes, edges)
                
                # Create edges
                for edge in edges:
                    x0, y0 = pos[edge["from"]]
                    x1, y1 = pos[edge["to"]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                # Create edge trace
                edge_trace = go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=0.5, color="#888"),
                    hoverinfo="none",
                    mode="lines"
                )
                
                # Create node trace
                node_x = [pos[node["id"]][0] for node in nodes]
                node_y = [pos[node["id"]][1] for node in nodes]
                
                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode="markers+text",
                    text=[node["label"] for node in nodes],
                    textposition="bottom center",
                    hoverinfo="text",
                    marker=go.scatter.Marker(
                        showscale=True,
                        colorscale="YlGnBu",
                        size=[node["size"] for node in nodes],
                        color=[gaps[node["id"]].importance for node in nodes],
                        colorbar=dict(
                            thickness=15,
                            title="Importance",
                            xanchor="left",
                            title_side="right"
                        ),
                        line=dict(width=2)
                    )
                )
                
                # Create figure with explicit Layout
                fig = go.Figure(
                    data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title="Knowledge Gap Relationships",
                        showlegend=False,
                        hovermode="closest",
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    def _simple_layout(self, nodes, edges, iterations=50):
        """
        Simple force-directed layout for network visualization.
        
        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            iterations: Number of layout iterations
            
        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        import random
        import math
        
        # Initialize random positions
        pos = {node["id"]: [random.uniform(0, 1), random.uniform(0, 1)] for node in nodes}
        
        # Build adjacency list
        adj = {node["id"]: [] for node in nodes}
        for edge in edges:
            adj[edge["from"]].append(edge["to"])
            adj[edge["to"]].append(edge["from"])
        
        # Force-directed layout
        for _ in range(iterations):
            # Repulsive forces (node-node)
            forces = {node["id"]: [0, 0] for node in nodes}
            
            for i, node1 in enumerate(nodes):
                for node2 in nodes[i+1:]:
                    dx = pos[node1["id"]][0] - pos[node2["id"]][0]
                    dy = pos[node1["id"]][1] - pos[node2["id"]][1]
                    
                    # Avoid division by zero
                    distance = max(0.1, math.sqrt(dx*dx + dy*dy))
                    
                    # Repulsive force
                    force = 0.1 / (distance * distance)
                    
                    # Normalize direction
                    fx = dx * force / distance
                    fy = dy * force / distance
                    
                    forces[node1["id"]][0] += fx
                    forces[node1["id"]][1] += fy
                    forces[node2["id"]][0] -= fx
                    forces[node2["id"]][1] -= fy
            
            # Attractive forces (connected nodes)
            for edge in edges:
                n1, n2 = edge["from"], edge["to"]
                
                dx = pos[n1][0] - pos[n2][0]
                dy = pos[n1][1] - pos[n2][1]
                
                # Avoid division by zero
                distance = max(0.1, math.sqrt(dx*dx + dy*dy))
                
                # Attractive force
                force = 0.1 * distance
                
                # Normalize direction
                fx = dx * force / distance
                fy = dy * force / distance
                
                forces[n1][0] -= fx
                forces[n1][1] -= fy
                forces[n2][0] += fx
                forces[n2][1] += fy
            
            # Apply forces
            for node in nodes:
                pos[node["id"]][0] += min(0.1, max(-0.1, forces[node["id"]][0]))
                pos[node["id"]][1] += min(0.1, max(-0.1, forces[node["id"]][1]))
        
        # Normalize positions to [0,1] range
        min_x = min(p[0] for p in pos.values())
        max_x = max(p[0] for p in pos.values())
        min_y = min(p[1] for p in pos.values())
        max_y = max(p[1] for p in pos.values())
        
        x_range = max(0.1, max_x - min_x)
        y_range = max(0.1, max_y - min_y)
        
        for node_id in pos:
            pos[node_id][0] = (pos[node_id][0] - min_x) / x_range
            pos[node_id][1] = (pos[node_id][1] - min_y) / y_range
        
        return pos
    
    def _render_research_plans_tab(self):
        """Render the research plans management tab."""
        st.header("Research Plans")
        
        # Get all plans
        plans = asyncio.run(self.research_planner.get_all_research_plans())
        
        if not plans:
            st.info("No research plans available. Create a new plan from the Knowledge Gaps tab.")
            return
        
        # Plan selection
        plan_options = [(plan_id, plan.title) for plan_id, plan in plans.items()]
        selected_plan = st.selectbox(
            "Select Research Plan:",
            options=plan_options,
            format_func=lambda x: x[1],
            index=next((i for i, (plan_id, _) in enumerate(plan_options) 
                       if plan_id == st.session_state.current_plan_id), 0)
        )
        
        if selected_plan:
            plan_id = selected_plan[0]
            st.session_state.current_plan_id = plan_id
            plan = plans[plan_id]
            
            # Plan details
            st.subheader(plan.title)
            st.write(plan.description)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tasks", len(plan.tasks))
            with col2:
                st.metric("Estimated Time", f"{plan.total_estimated_time:.1f} hours")
            with col3:
                status_colors = {
                    "pending": "🟡",
                    "in_progress": "🔵",
                    "completed": "🟢",
                    "blocked": "🔴",
                    "failed": "⚫"
                }
                st.metric("Status", f"{status_colors.get(plan.status, '⚪')} {plan.status.title()}")
            
            # Research plan progress
            task_statuses = [task.status for task in plan.tasks.values()]
            status_counts = {
                "pending": task_statuses.count("pending"),
                "in_progress": task_statuses.count("in_progress"),
                "completed": task_statuses.count("completed"),
                "blocked": task_statuses.count("blocked"),
                "failed": task_statuses.count("failed")
            }
            
            # Progress bar
            if task_statuses:
                progress = status_counts["completed"] / len(task_statuses)
                st.progress(progress)
                st.write(f"Progress: {int(progress * 100)}% complete")
            
            # Status breakdown
            st.subheader("Task Status Breakdown")
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Task Status Distribution",
                color=list(status_counts.keys()),
                color_discrete_map={
                    "completed": "green",
                    "in_progress": "blue",
                    "pending": "yellow",
                    "blocked": "red",
                    "failed": "gray"
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Knowledge gaps
            st.subheader("Knowledge Gaps")
            if plan.knowledge_gaps:
                gap_data = []
                for gap_id, gap in plan.knowledge_gaps.items():
                    # Find related tasks
                    related_tasks = [
                        task.title for task in plan.tasks.values()
                        if gap_id in task.knowledge_gaps
                    ]
                    
                    gap_data.append({
                        "Topic": gap.topic,
                        "Description": gap.description,
                        "Confidence": gap.confidence,
                        "Importance": gap.importance,
                        "Related Tasks": ", ".join(related_tasks)
                    })
                
                st.dataframe(pd.DataFrame(gap_data), hide_index=True)
            else:
                st.info("No knowledge gaps defined for this plan.")
            
            # Task sequence
            st.subheader("Task Sequence")
            if plan.task_sequence:
                sequence_data = []
                for i, task_id in enumerate(plan.task_sequence):
                    if task_id in plan.tasks:
                        task = plan.tasks[task_id]
                        sequence_data.append({
                            "Order": i + 1,
                            "Task": task.title,
                            "Strategy": task.strategy.name,
                            "Estimated Time": f"{task.estimated_time_hours:.1f} hours",
                            "Status": task.status.title(),
                            "Priority": task.priority
                        })
                
                st.dataframe(pd.DataFrame(sequence_data), hide_index=True)
            else:
                st.info("No task sequence defined for this plan.")
            
            # Actions
            st.subheader("Actions")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Re-prioritize Tasks"):
                    with st.spinner("Re-prioritizing tasks..."):
                        new_sequence = asyncio.run(
                            self.research_planner.prioritize_research_tasks(plan_id=plan_id)
                        )
                        st.success(f"Tasks re-prioritized successfully!")
                        st.rerun()
            
            with col2:
                if st.button("Delete Plan"):
                    if st.checkbox("Confirm deletion"):
                        with st.spinner("Deleting plan..."):
                            result = asyncio.run(
                                self.research_planner.delete_research_plan(plan_id=plan_id)
                            )
                            if result:
                                st.session_state.current_plan_id = None
                                st.success("Research plan deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete research plan.")
    
    def _render_task_dashboard_tab(self):
        """Render the task dashboard tab."""
        st.header("Research Task Dashboard")
        
        # Get current plan
        if not st.session_state.current_plan_id:
            plans = asyncio.run(self.research_planner.get_all_research_plans())
            if not plans:
                st.info("No research plans available. Create a new plan from the Knowledge Gaps tab.")
                return
            
            # Select the first plan
            plan_id, plan = next(iter(plans.items()))
            st.session_state.current_plan_id = plan_id
        else:
            plan_id = st.session_state.current_plan_id
            plan = asyncio.run(self.research_planner.get_research_plan(plan_id))
            
            if not plan:
                st.error("Selected plan not found.")
                return
        
        # Plan selection
        plans = asyncio.run(self.research_planner.get_all_research_plans())
        plan_options = [(p_id, p.title) for p_id, p in plans.items()]
        selected_plan = st.selectbox(
            "Select Research Plan:",
            options=plan_options,
            format_func=lambda x: x[1],
            index=next((i for i, (p_id, _) in enumerate(plan_options) 
                      if p_id == plan_id), 0)
        )
        
        if selected_plan:
            new_plan_id = selected_plan[0]
            if new_plan_id != plan_id:
                st.session_state.current_plan_id = new_plan_id
                st.rerun()
        
        # Display tasks
        st.subheader(f"Tasks for: {plan.title}")
        
        # Filter by status
        status_filter = st.multiselect(
            "Filter by Status:",
            options=["pending", "in_progress", "completed", "blocked", "failed"],
            default=["pending", "in_progress"]
        )
        
        # Sort options
        sort_options = {
            "Priority (High to Low)": lambda t: -t.priority,
            "Priority (Low to High)": lambda t: t.priority,
            "Estimated Time (High to Low)": lambda t: -t.estimated_time_hours,
            "Estimated Time (Low to High)": lambda t: t.estimated_time_hours,
            "Status": lambda t: t.status
        }
        
        sort_by = st.selectbox("Sort by:", options=list(sort_options.keys()))
        
        # Display tasks
        filtered_tasks = [
            task for task in plan.tasks.values()
            if not status_filter or task.status in status_filter
        ]
        
        # Sort tasks
        sorted_tasks = sorted(filtered_tasks, key=sort_options[sort_by])
        
        if sorted_tasks:
            st.write(f"Showing {len(sorted_tasks)} of {len(plan.tasks)} tasks")
            
            for task in sorted_tasks:
                with st.expander(f"{task.title} - {task.status.title()}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(task.description)
                        
                        # Knowledge gaps addressed
                        if task.knowledge_gaps:
                            gap_topics = [
                                plan.knowledge_gaps[gap_id].topic 
                                for gap_id in task.knowledge_gaps 
                                if gap_id in plan.knowledge_gaps
                            ]
                            st.write("Addresses gaps: " + ", ".join(gap_topics))
                        
                        # Dependencies
                        if task.dependencies:
                            dependency_titles = [
                                plan.tasks[dep_id].title 
                                for dep_id in task.dependencies 
                                if dep_id in plan.tasks
                            ]
                            st.write("Dependencies: " + ", ".join(dependency_titles))
                    
                    with col2:
                        st.metric("Priority", task.priority)
                        st.metric("Est. Time", f"{task.estimated_time_hours:.1f}h")
                        st.write(f"Strategy: {task.strategy.name}")
                    
                    with col3:
                        # Status update
                        new_status = st.selectbox(
                            "Status:",
                            options=["pending", "in_progress", "completed", "blocked", "failed"],
                            index=["pending", "in_progress", "completed", "blocked", "failed"].index(task.status),
                            key=f"status_{task.id}"
                        )
                        
                        if new_status != task.status:
                            if st.button("Update", key=f"update_{task.id}"):
                                with st.spinner("Updating task status..."):
                                    result = asyncio.run(
                                        self.research_planner.update_research_task(
                                            plan_id=plan_id,
                                            task_id=task.id,
                                            status=new_status
                                        )
                                    )
                                    if result:
                                        st.success("Task updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to update task.")
        else:
            st.info("No tasks match the current filters.")
        
        # Task distribution by strategy
        if plan.tasks:
            st.subheader("Task Distribution by Strategy")
            
            strategy_counts = {}
            for task in plan.tasks.values():
                strategy_name = task.strategy.name
                if strategy_name in strategy_counts:
                    strategy_counts[strategy_name] += 1
                else:
                    strategy_counts[strategy_name] = 1
            
            fig = px.bar(
                x=list(strategy_counts.keys()),
                y=list(strategy_counts.values()),
                title="Tasks by Research Strategy",
                labels={"x": "Strategy", "y": "Number of Tasks"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Time allocation
            st.subheader("Estimated Time Allocation")
            
            strategy_times = {}
            for task in plan.tasks.values():
                strategy_name = task.strategy.name
                if strategy_name in strategy_times:
                    strategy_times[strategy_name] += task.estimated_time_hours
                else:
                    strategy_times[strategy_name] = task.estimated_time_hours
            
            fig = px.pie(
                values=list(strategy_times.values()),
                names=list(strategy_times.keys()),
                title="Estimated Research Time by Strategy"
            )
            st.plotly_chart(fig, use_container_width=True)


def main():
    """Run the Research Planner UI."""
    # Initialize the KnowledgeIntegrationSystem (simplified for demo)
    knowledge_system = KnowledgeIntegrationSystem()
    
    # Initialize the Research Planner
    research_planner = ResearchPlanner(knowledge_system=knowledge_system)
    
    # Initialize and render the UI
    view = ResearchPlannerView(research_planner=research_planner)
    view.render()


if __name__ == "__main__":
    main() 