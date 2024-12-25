from typing import Dict, Any, Optional, List
import streamlit as st
from ...controllers.tasks_tree_controller import TaskStatus, TaskNode, TaskTreeManager, ExecutionStrategy, ExecutionConfig
import graphviz
from datetime import datetime

class TaskTreeVisualizer:
    """Component for visualizing task trees in Streamlit."""
    
    def __init__(self, theme: Optional[Dict[str, str]] = None):
        self.theme = theme or {
            'PENDING': '#808080',    # Gray
            'RUNNING': '#FFA500',    # Orange
            'COMPLETED': '#32CD32',  # Green
            'FAILED': '#FF0000',     # Red
            'SKIPPED': '#A9A9A9',    # Dark Gray
            'CANCELLED': '#DC143C'   # Crimson
        }

    def render_tree(self, tree_manager: TaskTreeManager):
        """Render the task tree visualization."""
        st.subheader("Task Tree Visualization")
        
        # Create graphviz digraph
        dot = graphviz.Digraph()
        dot.attr(rankdir='TB')
        
        # Add nodes and edges
        self._add_nodes_to_graph(dot, tree_manager.root_nodes)
        
        # Display graph
        st.graphviz_chart(dot)
        
        # Display execution stats
        self.render_execution_stats(tree_manager)

    def _add_nodes_to_graph(self, dot, nodes: List[TaskNode], parent_id: Optional[str] = None):
        """Recursively add nodes and edges to the graph."""
        for node in nodes:
            # Create node
            node_color = self.theme[node.state.status.value]
            execution_time = ""
            if node.state.started_at and node.state.completed_at:
                duration = (node.state.completed_at - node.state.started_at).total_seconds()
                execution_time = f"\nTime: {duration:.2f}s"
                
            label = f"{node.task.name}\n{node.state.status.value}{execution_time}"
            
            dot.node(str(node.task.id), label,
                    style='filled',
                    fillcolor=node_color,
                    fontcolor='white' if node.state.status in [TaskStatus.FAILED, TaskStatus.RUNNING] else 'black')
            
            # Add edge from parent
            if parent_id:
                dot.edge(str(parent_id), str(node.task.id))
            
            # Add dependency edges
            for dep in node.dependencies:
                dot.edge(str(dep.task.id), str(node.task.id), style='dashed')
            
            # Process children
            self._add_nodes_to_graph(dot, node.children, node.task.id)

    def render_execution_stats(self, tree_manager: TaskTreeManager):
        """Render execution statistics."""
        st.subheader("Execution Statistics")
        
        stats = tree_manager.get_execution_stats()
        
        # Create columns for different statuses
        cols = st.columns(len(TaskStatus))
        for i, status in enumerate(TaskStatus):
            with cols[i]:
                count = sum(1 for s in stats.values() if s['status'] == status.value)
                st.metric(status.value, count)
        
        # Display detailed stats
        if st.checkbox("Show Detailed Stats"):
            for task_id, task_stats in stats.items():
                with st.expander(f"Task: {task_stats['name']}"):
                    st.json(task_stats)

    def render_task_details(self, node: TaskNode):
        """Render detailed information for a task."""
        st.subheader(f"Task Details: {node.task.name}")
        
        # Basic info
        cols = st.columns(3)
        with cols[0]:
            st.metric("Status", node.state.status.value)
        with cols[1]:
            st.metric("Execution Count", node.state.execution_count)
        with cols[2]:
            st.metric("Retry Count", node.state.retry_count)
            
        # Timing information
        if node.state.execution_duration:
            st.metric("Execution Time", f"{node.state.execution_duration:.2f}s")
            
        # Results and errors
        if node.state.result:
            with st.expander("Task Result"):
                st.code(node.state.result)
                
        if node.state.error:
            with st.expander("Error Information", expanded=True):
                st.error(node.state.error)
                
        # Execution history
        if node.state.execution_history:
            with st.expander("Execution History"):
                for entry in node.state.execution_history:
                    st.write(f"{entry['timestamp']}: {entry['old_status']} → {entry['new_status']}")
                    if entry.get('error'):
                        st.error(entry['error'])
                        
        # Dependencies and children
        if node.dependencies:
            with st.expander("Dependencies"):
                for dep in node.dependencies:
                    st.write(f"- {dep.task.name} ({dep.state.status.value})")
                    
        if node.children:
            with st.expander("Child Tasks"):
                for child in node.children:
                    st.write(f"- {child.task.name} ({child.state.status.value})")

    def render_tree_controls(self, tree_manager: TaskTreeManager):
        """Render tree control panel."""
        st.sidebar.subheader("Tree Controls")
        
        # Execution strategy
        strategy = st.sidebar.selectbox(
            "Execution Strategy",
            options=[s.value for s in ExecutionStrategy],
            index=0
        )
        
        # Concurrency settings
        if strategy == ExecutionStrategy.PARALLEL_WITH_LIMIT.value:
            max_concurrency = st.sidebar.number_input(
                "Max Concurrency",
                min_value=1,
                max_value=10,
                value=3
            )
            
        # Retry settings
        max_retries = st.sidebar.number_input(
            "Max Retries",
            min_value=0,
            max_value=5,
            value=3
        )
        
        retry_delay = st.sidebar.number_input(
            "Retry Delay (seconds)",
            min_value=0.0,
            max_value=60.0,
            value=1.0
        )
        
        # Timeout settings
        timeout = st.sidebar.number_input(
            "Timeout (seconds)",
            min_value=0.0,
            max_value=300.0,
            value=30.0
        )
        
        # Fail fast option
        fail_fast = st.sidebar.checkbox("Fail Fast", value=False)
        
        # Apply settings button
        if st.sidebar.button("Apply Settings"):
            config = ExecutionConfig(
                strategy=ExecutionStrategy(strategy),
                max_concurrency=max_concurrency if strategy == ExecutionStrategy.PARALLEL_WITH_LIMIT.value else None,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
                fail_fast=fail_fast
            )
            
            # Update all nodes with new config
            for node in tree_manager.nodes.values():
                node.execution_config = config
            
            st.sidebar.success("Settings applied successfully") 