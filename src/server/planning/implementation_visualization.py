"""
Implementation Visualization for the Self-Aware Cerebrum.

This module provides visualization capabilities for implementation plans,
including Gantt charts and dependency graph visualization.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import json
import os
import uuid
import io
import base64
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.server.planning.implementation_planner import ImplementationPlan, ImplementationTask, TaskType

logger = logging.getLogger(__name__)

@dataclass
class GanttChartTask:
    """Task representation for Gantt chart."""
    id: str
    name: str
    start: float  # Start time in hours from project start
    duration: float  # Duration in hours
    dependencies: List[str]
    progress: float = 0.0  # 0.0 to 1.0
    color: str = "#3498db"  # Default blue color
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "start": self.start,
            "duration": self.duration,
            "dependencies": self.dependencies,
            "progress": self.progress,
            "color": self.color
        }

@dataclass
class GanttChart:
    """Gantt chart representation for implementation plan."""
    tasks: List[GanttChartTask]
    title: str
    start_date: str
    end_date: str
    critical_path: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tasks": [task.to_dict() for task in self.tasks],
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "critical_path": self.critical_path
        }
    
    def to_html(self) -> str:
        """Generate HTML representation of the Gantt chart."""
        # This would generate HTML using a library like plotly or a custom renderer
        # For now, we'll return a placeholder HTML
        tasks_json = json.dumps([task.to_dict() for task in self.tasks])
        critical_path_json = json.dumps(self.critical_path)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .chart-container {{ position: relative; height: {len(self.tasks) * 40 + 100}px; width: 100%; }}
                .critical-path {{ color: red; font-weight: bold; }}
                .task-info {{ margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>{self.title}</h1>
            <div class="task-info">
                <p>Start Date: {self.start_date}</p>
                <p>End Date: {self.end_date}</p>
                <p class="critical-path">Critical Path: {', '.join(self.critical_path)}</p>
            </div>
            <div class="chart-container">
                <canvas id="ganttChart"></canvas>
            </div>
            
            <script>
                const tasks = {tasks_json};
                const criticalPath = {critical_path_json};
                
                // Setup data for Chart.js
                const data = {{
                    datasets: tasks.map(task => {{
                        return {{
                            label: task.name,
                            data: [{{
                                x: [task.start, task.start + task.duration],
                                y: task.name
                            }}],
                            backgroundColor: criticalPath.includes(task.id) ? 'rgba(255, 0, 0, 0.5)' : task.color,
                            borderColor: criticalPath.includes(task.id) ? 'rgb(255, 0, 0)' : 'rgb(52, 152, 219)',
                            borderWidth: criticalPath.includes(task.id) ? 2 : 1
                        }};
                    }})
                }};
                
                // Render chart
                const ctx = document.getElementById('ganttChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'bar',
                    data: data,
                    options: {{
                        indexAxis: 'y',
                        scales: {{
                            x: {{
                                title: {{
                                    display: true,
                                    text: 'Time (hours)'
                                }},
                                min: 0
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
    def to_svg(self) -> str:
        """Generate SVG representation of the Gantt chart."""
        # This is a simplified representation using SVG
        # In a real implementation, use a proper SVG generation library
        
        # Calculate dimensions
        width = 1000
        height = len(self.tasks) * 30 + 50
        
        # Calculate scale
        max_end = max([task.start + task.duration for task in self.tasks])
        time_scale = (width - 200) / max_end
        
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <style>
                .task {{ fill: #3498db; stroke: #2980b9; }}
                .critical {{ fill: #e74c3c; stroke: #c0392b; }}
                .task-text {{ font-family: Arial; font-size: 12px; }}
                .time-label {{ font-family: Arial; font-size: 10px; fill: #7f8c8d; }}
                .title {{ font-family: Arial; font-size: 16px; font-weight: bold; }}
            </style>
            <text x="10" y="20" class="title">{self.title}</text>
        '''
        
        # Draw time scale
        for i in range(0, int(max_end) + 1, 8):
            x = 150 + i * time_scale
            svg += f'<line x1="{x}" y1="30" x2="{x}" y2="{height}" stroke="#ecf0f1" stroke-width="1" />'
            svg += f'<text x="{x}" y="45" class="time-label" text-anchor="middle">{i}h</text>'
        
        # Draw tasks
        critical_path_set = set(self.critical_path)
        
        for i, task in enumerate(self.tasks):
            y = 60 + i * 30
            x = 150 + task.start * time_scale
            width = task.duration * time_scale
            
            task_class = "critical" if task.id in critical_path_set else "task"
            svg += f'<rect x="{x}" y="{y}" width="{width}" height="20" rx="3" class="{task_class}" />'
            svg += f'<text x="140" y="{y + 15}" class="task-text" text-anchor="end">{task.name}</text>'
            
            # Draw progress
            if task.progress > 0:
                progress_width = width * task.progress
                svg += f'<rect x="{x}" y="{y}" width="{progress_width}" height="20" rx="3" fill="rgba(0,0,0,0.2)" />'
            
            # Draw dependencies
            for dep_id in task.dependencies:
                # Find the dependent task
                for j, dep_task in enumerate(self.tasks):
                    if dep_task.id == dep_id:
                        dep_y = 60 + j * 30 + 10
                        dep_x = 150 + (dep_task.start + dep_task.duration) * time_scale
                        
                        svg += f'<line x1="{dep_x}" y1="{dep_y}" x2="{x}" y2="{y + 10}" stroke="#95a5a6" stroke-width="1" marker-end="url(#arrowhead)" stroke-dasharray="4" />'
                        break
        
        # Add arrowhead marker
        svg += '''
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#95a5a6" />
                </marker>
            </defs>
        '''
        
        svg += '</svg>'
        
        return svg

@dataclass
class DependencyNode:
    """Node in dependency graph."""
    id: str
    name: str
    task_type: str
    component_id: str
    estimated_hours: float
    complexity: int
    dependencies: List[str]
    is_critical: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "component_id": self.component_id,
            "estimated_hours": self.estimated_hours,
            "complexity": self.complexity,
            "dependencies": self.dependencies,
            "is_critical": self.is_critical
        }

@dataclass
class DependencyEdge:
    """Edge in dependency graph."""
    source: str
    target: str
    is_critical: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "is_critical": self.is_critical
        }

@dataclass
class DependencyGraph:
    """Dependency graph representation for implementation plan."""
    nodes: List[DependencyNode]
    edges: List[DependencyEdge]
    title: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "title": self.title
        }
    
    def to_html(self) -> str:
        """Generate HTML representation of the dependency graph."""
        # This would generate HTML using a library like d3.js
        # For now, we'll return a placeholder HTML
        nodes_json = json.dumps([node.to_dict() for node in self.nodes])
        edges_json = json.dumps([edge.to_dict() for edge in self.edges])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; }}
                #graph {{ width: 100%; height: 800px; }}
                .node {{ cursor: pointer; }}
                .link {{ stroke: #999; stroke-opacity: 0.6; }}
                .critical {{ stroke: red; stroke-width: 2px; }}
                .critical-node {{ stroke: red; stroke-width: 2px; }}
            </style>
        </head>
        <body>
            <h1>{self.title}</h1>
            <div id="graph"></div>
            
            <script>
                const nodes = {nodes_json};
                const edges = {edges_json};
                
                // Set up D3.js force layout
                const width = window.innerWidth;
                const height = 800;
                
                const simulation = d3.forceSimulation(nodes)
                    .force("link", d3.forceLink(edges).id(d => d.id).distance(100))
                    .force("charge", d3.forceManyBody().strength(-300))
                    .force("center", d3.forceCenter(width / 2, height / 2));
                
                const svg = d3.select("#graph")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);
                
                // Add links
                const link = svg.append("g")
                    .selectAll("line")
                    .data(edges)
                    .enter().append("line")
                    .attr("class", d => d.is_critical ? "link critical" : "link")
                    .attr("marker-end", "url(#arrow)");
                
                // Add nodes
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(nodes)
                    .enter().append("circle")
                    .attr("class", d => d.is_critical ? "node critical-node" : "node")
                    .attr("r", d => 5 + d.complexity)
                    .attr("fill", d => {{
                        // Color based on task type
                        const colors = {{
                            "SETUP": "#3498db",
                            "CORE_IMPLEMENTATION": "#2ecc71",
                            "INTERFACE_IMPLEMENTATION": "#9b59b6",
                            "TESTING": "#e74c3c",
                            "DOCUMENTATION": "#f39c12",
                            "INTEGRATION": "#1abc9c",
                            "REFACTORING": "#34495e"
                        }};
                        return colors[d.task_type] || "#95a5a6";
                    }});
                
                // Add text labels
                const text = svg.append("g")
                    .selectAll("text")
                    .data(nodes)
                    .enter().append("text")
                    .attr("dx", 12)
                    .attr("dy", ".35em")
                    .text(d => d.name);
                
                // Add arrowhead marker
                svg.append("defs").append("marker")
                    .attr("id", "arrow")
                    .attr("viewBox", "0 -5 10 10")
                    .attr("refX", 15)
                    .attr("refY", 0)
                    .attr("markerWidth", 6)
                    .attr("markerHeight", 6)
                    .attr("orient", "auto")
                    .append("path")
                    .attr("d", "M0,-5L10,0L0,5");
                
                // Set up simulation tick function
                simulation.on("tick", () => {{
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);
                    
                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);
                    
                    text
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                }});
                
                // Add zoom functionality
                svg.call(d3.zoom()
                    .extent([[0, 0], [width, height]])
                    .scaleExtent([0.1, 10])
                    .on("zoom", event => {{
                        link.attr("transform", event.transform);
                        node.attr("transform", event.transform);
                        text.attr("transform", event.transform);
                    }}));
            </script>
        </body>
        </html>
        """
    
    def to_svg(self) -> str:
        """Generate SVG representation of the dependency graph."""
        # This is a simplified representation using SVG
        # In a real implementation, use a proper graph visualization library
        
        # Calculate dimensions
        width = 800
        height = 600
        
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <style>
                .node {{ fill: #3498db; stroke: #2980b9; }}
                .critical-node {{ fill: #e74c3c; stroke: #c0392b; }}
                .edge {{ stroke: #95a5a6; stroke-width: 1.5; }}
                .critical-edge {{ stroke: #e74c3c; stroke-width: 2.5; }}
                .node-text {{ font-family: Arial; font-size: 10px; }}
                .title {{ font-family: Arial; font-size: 16px; font-weight: bold; }}
            </style>
            <text x="10" y="20" class="title">{self.title}</text>
        '''
        
        # Add arrowhead marker
        svg += '''
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#95a5a6" />
                </marker>
                <marker id="critical-arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#e74c3c" />
                </marker>
            </defs>
        '''
        
        # For a simple visualization, arrange nodes in a tree-like structure
        # In a real implementation, use a force-directed layout algorithm
        
        # First, determine node levels based on dependencies
        node_levels: Dict[str, int] = {}
        
        def calculate_level(node_id: str, visited: Set[str]) -> int:
            if node_id in node_levels:
                return node_levels[node_id]
            
            if node_id in visited:
                # Circular dependency, break cycle
                return 0
            
            visited.add(node_id)
            
            # Find the node
            node = next((n for n in self.nodes if n.id == node_id), None)
            if not node:
                return 0
            
            # Calculate max level of dependencies
            if not node.dependencies:
                level = 0
            else:
                level = max([calculate_level(dep, visited.copy()) for dep in node.dependencies], default=-1) + 1
            
            node_levels[node_id] = level
            return level
        
        # Calculate levels for all nodes
        for node in self.nodes:
            if node.id not in node_levels:
                calculate_level(node.id, set())
        
        # Group nodes by level
        nodes_by_level: Dict[int, List[DependencyNode]] = {}
        for node in self.nodes:
            level = node_levels[node.id]
            if level not in nodes_by_level:
                nodes_by_level[level] = []
            nodes_by_level[level].append(node)
        
        # Calculate positions
        max_level = max(nodes_by_level.keys()) if nodes_by_level else 0
        node_positions: Dict[str, Tuple[float, float]] = {}
        
        for level, nodes in nodes_by_level.items():
            level_width = width - 100
            level_height = 100 + (level * 100)
            
            for i, node in enumerate(nodes):
                x = 50 + ((i + 1) * level_width) / (len(nodes) + 1)
                y = level_height
                node_positions[node.id] = (x, y)
        
        # Draw edges first (so they're under the nodes)
        for edge in self.edges:
            if edge.source in node_positions and edge.target in node_positions:
                source_pos = node_positions[edge.source]
                target_pos = node_positions[edge.target]
                
                edge_class = "critical-edge" if edge.is_critical else "edge"
                marker_end = "url(#critical-arrowhead)" if edge.is_critical else "url(#arrowhead)"
                
                svg += f'<line x1="{source_pos[0]}" y1="{source_pos[1]}" x2="{target_pos[0]}" y2="{target_pos[1]}" class="{edge_class}" marker-end="{marker_end}" />'
        
        # Draw nodes
        for node in self.nodes:
            if node.id in node_positions:
                pos = node_positions[node.id]
                node_class = "critical-node" if node.is_critical else "node"
                
                # Size based on complexity
                radius = 5 + (node.complexity / 2)
                
                svg += f'<circle cx="{pos[0]}" cy="{pos[1]}" r="{radius}" class="{node_class}" />'
                svg += f'<text x="{pos[0]}" y="{pos[1] + radius + 10}" class="node-text" text-anchor="middle">{node.name}</text>'
        
        svg += '</svg>'
        
        return svg

class ImplementationVisualization:
    """Visualization generator for implementation plans."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Implementation Visualization.
        
        Args:
            storage_path: Path to store visualizations
        """
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "visualizations", "implementation")
        os.makedirs(self.storage_path, exist_ok=True)
    
    async def generate_gantt_chart(
        self,
        plan: ImplementationPlan,
        start_date: Optional[str] = None,
        include_progress: bool = True
    ) -> GanttChart:
        """
        Generate a Gantt chart for an implementation plan.
        
        Args:
            plan: The implementation plan to visualize
            start_date: Optional start date (ISO format), defaults to now
            include_progress: Whether to include progress in the chart
            
        Returns:
            A GanttChart object
        """
        if not start_date:
            start_date = datetime.now().isoformat()
        
        start_datetime = datetime.fromisoformat(start_date)
        
        # Create Gantt chart tasks
        chart_tasks = []
        
        # Calculate earliest start time for each task based on dependencies
        earliest_starts = self._calculate_earliest_start_times(plan.tasks)
        
        # Create task representation for each implementation task
        for task_id, task in plan.tasks.items():
            # Calculate progress based on task status
            progress = 0.0
            if task.status == "completed":
                progress = 1.0
            elif task.status == "in_progress":
                progress = 0.5
            
            # Get color based on task type
            color = self._get_color_for_task_type(task.task_type)
            
            chart_task = GanttChartTask(
                id=task_id,
                name=task.title,
                start=earliest_starts[task_id],
                duration=task.estimated_hours,
                dependencies=task.dependencies,
                progress=progress,
                color=color
            )
            chart_tasks.append(chart_task)
        
        # Sort tasks by start time
        chart_tasks.sort(key=lambda t: t.start)
        
        # Calculate end date
        total_duration = max([t.start + t.duration for t in chart_tasks]) if chart_tasks else 0
        end_datetime = start_datetime + timedelta(hours=total_duration)
        
        gantt_chart = GanttChart(
            tasks=chart_tasks,
            title=f"Implementation Plan: {plan.name}",
            start_date=start_date,
            end_date=end_datetime.isoformat(),
            critical_path=plan.critical_path
        )
        
        # Save the chart
        self._save_gantt_chart(plan.id, gantt_chart)
        
        return gantt_chart
    
    async def generate_dependency_graph(
        self,
        plan: ImplementationPlan
    ) -> DependencyGraph:
        """
        Generate a dependency graph for an implementation plan.
        
        Args:
            plan: The implementation plan to visualize
            
        Returns:
            A DependencyGraph object
        """
        # Create nodes for each task
        nodes = []
        critical_path_set = set(plan.critical_path)
        
        for task_id, task in plan.tasks.items():
            node = DependencyNode(
                id=task_id,
                name=task.title,
                task_type=task.task_type.name,
                component_id=task.component_id,
                estimated_hours=task.estimated_hours,
                complexity=task.estimated_complexity,
                dependencies=task.dependencies,
                is_critical=task_id in critical_path_set
            )
            nodes.append(node)
        
        # Create edges for dependencies
        edges = []
        for task_id, task in plan.tasks.items():
            for dep_id in task.dependencies:
                # Check if this edge is on the critical path
                is_critical = task_id in critical_path_set and dep_id in critical_path_set
                
                # Check if they are adjacent in the critical path
                if is_critical:
                    try:
                        dep_idx = plan.critical_path.index(dep_id)
                        task_idx = plan.critical_path.index(task_id)
                        is_critical = abs(dep_idx - task_idx) == 1
                    except ValueError:
                        is_critical = False
                
                edge = DependencyEdge(
                    source=dep_id,
                    target=task_id,
                    is_critical=is_critical
                )
                edges.append(edge)
        
        graph = DependencyGraph(
            nodes=nodes,
            edges=edges,
            title=f"Dependency Graph: {plan.name}"
        )
        
        # Save the graph
        self._save_dependency_graph(plan.id, graph)
        
        return graph
    
    def _calculate_earliest_start_times(self, tasks: Dict[str, ImplementationTask]) -> Dict[str, float]:
        """Calculate earliest start time for each task based on dependencies."""
        earliest_starts: Dict[str, float] = {}
        
        def calculate_earliest_start(task_id: str, visited: Set[str]) -> float:
            if task_id in earliest_starts:
                return earliest_starts[task_id]
            
            if task_id in visited:
                # Circular dependency, break cycle
                return 0.0
            
            visited.add(task_id)
            
            task = tasks[task_id]
            
            if not task.dependencies:
                earliest_starts[task_id] = 0.0
                return 0.0
            
            # Calculate max end time of dependencies
            max_end_time = 0.0
            for dep_id in task.dependencies:
                if dep_id in tasks:
                    dep_start = calculate_earliest_start(dep_id, visited.copy())
                    dep_end = dep_start + tasks[dep_id].estimated_hours
                    max_end_time = max(max_end_time, dep_end)
            
            earliest_starts[task_id] = max_end_time
            return max_end_time
        
        # Calculate earliest start for all tasks
        for task_id in tasks:
            if task_id not in earliest_starts:
                calculate_earliest_start(task_id, set())
        
        return earliest_starts
    
    def _get_color_for_task_type(self, task_type: TaskType) -> str:
        """Get color for task type."""
        colors = {
            TaskType.SETUP: "#3498db",  # Blue
            TaskType.CORE_IMPLEMENTATION: "#2ecc71",  # Green
            TaskType.INTERFACE_IMPLEMENTATION: "#9b59b6",  # Purple
            TaskType.TESTING: "#e74c3c",  # Red
            TaskType.DOCUMENTATION: "#f39c12",  # Orange
            TaskType.INTEGRATION: "#1abc9c",  # Turquoise
            TaskType.REFACTORING: "#34495e"  # Dark Blue
        }
        
        return colors.get(task_type, "#95a5a6")  # Default to gray
    
    def _save_gantt_chart(self, plan_id: str, gantt_chart: GanttChart) -> None:
        """Save Gantt chart to storage."""
        chart_dir = os.path.join(self.storage_path, "gantt")
        os.makedirs(chart_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(chart_dir, f"{plan_id}.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(gantt_chart.to_dict(), f, indent=2)
            logger.info(f"Saved Gantt chart JSON: {json_path}")
        except Exception as e:
            logger.error(f"Error saving Gantt chart JSON: {e}")
        
        # Save as HTML
        html_path = os.path.join(chart_dir, f"{plan_id}.html")
        try:
            with open(html_path, 'w') as f:
                f.write(gantt_chart.to_html())
            logger.info(f"Saved Gantt chart HTML: {html_path}")
        except Exception as e:
            logger.error(f"Error saving Gantt chart HTML: {e}")
        
        # Save as SVG
        svg_path = os.path.join(chart_dir, f"{plan_id}.svg")
        try:
            with open(svg_path, 'w') as f:
                f.write(gantt_chart.to_svg())
            logger.info(f"Saved Gantt chart SVG: {svg_path}")
        except Exception as e:
            logger.error(f"Error saving Gantt chart SVG: {e}")
    
    def _save_dependency_graph(self, plan_id: str, graph: DependencyGraph) -> None:
        """Save dependency graph to storage."""
        graph_dir = os.path.join(self.storage_path, "graphs")
        os.makedirs(graph_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(graph_dir, f"{plan_id}.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(graph.to_dict(), f, indent=2)
            logger.info(f"Saved dependency graph JSON: {json_path}")
        except Exception as e:
            logger.error(f"Error saving dependency graph JSON: {e}")
        
        # Save as HTML
        html_path = os.path.join(graph_dir, f"{plan_id}.html")
        try:
            with open(html_path, 'w') as f:
                f.write(graph.to_html())
            logger.info(f"Saved dependency graph HTML: {html_path}")
        except Exception as e:
            logger.error(f"Error saving dependency graph HTML: {e}")
        
        # Save as SVG
        svg_path = os.path.join(graph_dir, f"{plan_id}.svg")
        try:
            with open(svg_path, 'w') as f:
                f.write(graph.to_svg())
            logger.info(f"Saved dependency graph SVG: {svg_path}")
        except Exception as e:
            logger.error(f"Error saving dependency graph SVG: {e}")
    
    async def load_gantt_chart(self, plan_id: str) -> Optional[GanttChart]:
        """Load Gantt chart from storage."""
        json_path = os.path.join(self.storage_path, "gantt", f"{plan_id}.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                tasks = []
                for task_data in data["tasks"]:
                    tasks.append(GanttChartTask(
                        id=task_data["id"],
                        name=task_data["name"],
                        start=task_data["start"],
                        duration=task_data["duration"],
                        dependencies=task_data["dependencies"],
                        progress=task_data["progress"],
                        color=task_data["color"]
                    ))
                
                return GanttChart(
                    tasks=tasks,
                    title=data["title"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    critical_path=data["critical_path"]
                )
        except Exception as e:
            logger.error(f"Error loading Gantt chart: {e}")
            return None
    
    async def load_dependency_graph(self, plan_id: str) -> Optional[DependencyGraph]:
        """Load dependency graph from storage."""
        json_path = os.path.join(self.storage_path, "graphs", f"{plan_id}.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                nodes = []
                for node_data in data["nodes"]:
                    nodes.append(DependencyNode(
                        id=node_data["id"],
                        name=node_data["name"],
                        task_type=node_data["task_type"],
                        component_id=node_data["component_id"],
                        estimated_hours=node_data["estimated_hours"],
                        complexity=node_data["complexity"],
                        dependencies=node_data["dependencies"],
                        is_critical=node_data["is_critical"]
                    ))
                
                edges = []
                for edge_data in data["edges"]:
                    edges.append(DependencyEdge(
                        source=edge_data["source"],
                        target=edge_data["target"],
                        is_critical=edge_data["is_critical"]
                    ))
                
                return DependencyGraph(
                    nodes=nodes,
                    edges=edges,
                    title=data["title"]
                )
        except Exception as e:
            logger.error(f"Error loading dependency graph: {e}")
            return None 