"""
Goal Tree Visualization for the Self-Aware Cerebrum system.

This module provides capabilities for creating visual representations
of goal trees, supporting different export formats.
"""

from typing import Dict, List, Optional, Any, Tuple
import asyncio
import json
import os
import logging
from pathlib import Path
import uuid
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src.server.planning.goal_decomposition import DecomposedGoal, SubGoal, GoalType

logger = logging.getLogger(__name__)

class GoalTreeVisualization:
    """Tool for visualizing goal trees in various formats."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the goal tree visualization tool.
        
        Args:
            output_dir: Directory to save visualizations. Defaults to a temporary directory.
        """
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "../../..", "temp/visualizations")
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def create_json_export(self, decomposed_goal: DecomposedGoal) -> str:
        """
        Create a JSON representation of the goal tree.
        
        Args:
            decomposed_goal: The decomposed goal to visualize
            
        Returns:
            Path to the JSON file
        """
        tree_data = self._build_tree_data(decomposed_goal)
        
        file_path = os.path.join(self.output_dir, f"goal_tree_{decomposed_goal.id}.json")
        with open(file_path, "w") as f:
            json.dump(tree_data, f, indent=2)
            
        return file_path
    
    async def create_svg_visualization(self, decomposed_goal: DecomposedGoal) -> str:
        """
        Create a visual SVG representation of the decomposed goal.
        
        Args:
            decomposed_goal: The decomposed goal to visualize
            
        Returns:
            Path to the SVG file
        """
        # Set the matplotlib backend to Agg (non-interactive) for testing environments
        import matplotlib
        matplotlib.use('Agg')
        
        # Create a directed graph
        G = self._create_networkx_graph(decomposed_goal)
        
        # Generate layout - use spring_layout instead of graphviz_layout which requires pygraphviz
        pos = nx.spring_layout(G, seed=42)  # Use spring layout with fixed seed for reproducibility
        
        # Create figure
        plt.figure(figsize=(12, 8))
        
        # Node colors based on priority
        priority_values = [G.nodes[n].get('priority', 5) for n in G.nodes()]
        norm = plt.Normalize(1, 10)
        cmap = plt.cm.YlOrRd
        
        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos, 
            node_color=[cmap(norm(priority)) for priority in priority_values],
            node_size=1500, 
            alpha=0.9
        )
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
        
        # Add title
        plt.title(f"Goal Tree: {decomposed_goal.name}")
        plt.axis('off')
        
        # Save to file
        file_path = os.path.join(self.output_dir, f"goal_tree_{decomposed_goal.id}.svg")
        plt.savefig(file_path, format="svg", bbox_inches="tight")
        plt.close()
        
        return file_path
    
    async def create_interactive_html(self, decomposed_goal: DecomposedGoal) -> str:
        """
        Create an interactive HTML visualization of the goal tree.
        
        Args:
            decomposed_goal: The decomposed goal to visualize
            
        Returns:
            Path to the HTML file
        """
        tree_data = self._build_tree_data(decomposed_goal)
        
        # Create simple HTML with D3.js
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Goal Tree: {decomposed_goal.name}</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .node circle {{ fill: #fff; stroke: steelblue; stroke-width: 3px; }}
                .node text {{ font: 12px sans-serif; }}
                .link {{ fill: none; stroke: #ccc; stroke-width: 2px; }}
                .tooltip {{ position: absolute; background-color: white; border: 1px solid #ddd; 
                           padding: 10px; border-radius: 5px; pointer-events: none; }}
            </style>
        </head>
        <body>
            <h1>Goal Tree: {decomposed_goal.name}</h1>
            <div id="tree-container"></div>
            <script>
                const treeData = {json.dumps(tree_data)};
                
                // Set dimensions
                const margin = {{top: 20, right: 90, bottom: 30, left: 90}},
                    width = 960 - margin.left - margin.right,
                    height = 800 - margin.top - margin.bottom;
                
                // Create SVG
                const svg = d3.select("#tree-container").append("svg")
                    .attr("width", width + margin.left + margin.right)
                    .attr("height", height + margin.top + margin.bottom)
                    .append("g")
                    .attr("transform", `translate(${{margin.left}},${{margin.top}})`);
                
                // Create tooltip
                const tooltip = d3.select("body").append("div")
                    .attr("class", "tooltip")
                    .style("opacity", 0);
                    
                // Create tree layout
                const tree = d3.tree().size([height, width]);
                
                // Assign hierarchical data
                const root = d3.hierarchy(treeData, d => d.children);
                
                // Map the node data to the tree layout
                tree(root);
                
                // Add links
                svg.selectAll(".link")
                    .data(root.descendants().slice(1))
                    .enter().append("path")
                    .attr("class", "link")
                    .attr("d", d => `M${{d.y}},${{d.x}}C${{(d.y + d.parent.y) / 2}},${{d.x}} ${{(d.y + d.parent.y) / 2}},${{d.parent.x}} ${{d.parent.y}},${{d.parent.x}}`);
                
                // Add nodes
                const node = svg.selectAll(".node")
                    .data(root.descendants())
                    .enter().append("g")
                    .attr("class", "node")
                    .attr("transform", d => `translate(${{d.y}},${{d.x}})`)
                    .on("mouseover", function(event, d) {{
                        tooltip.transition().duration(200).style("opacity", .9);
                        tooltip.html(`<b>${{d.data.name}}</b><br/>Priority: ${{d.data.priority}}<br/>Time: ${{d.data.time_hours}} hours<br/>${{d.data.description}}`)
                            .style("left", (event.pageX + 10) + "px")
                            .style("top", (event.pageY - 28) + "px");
                    }})
                    .on("mouseout", function(d) {{
                        tooltip.transition().duration(500).style("opacity", 0);
                    }});
                
                // Add circles to nodes
                node.append("circle")
                    .attr("r", 10)
                    .style("fill", d => d3.interpolateYlOrRd(d.data.priority / 10));
                
                // Add labels to nodes
                node.append("text")
                    .attr("dy", ".35em")
                    .attr("x", d => d.children ? -13 : 13)
                    .style("text-anchor", d => d.children ? "end" : "start")
                    .text(d => d.data.name);
            </script>
        </body>
        </html>
        """
        
        file_path = os.path.join(self.output_dir, f"goal_tree_{decomposed_goal.id}.html")
        with open(file_path, "w") as f:
            f.write(html_content)
            
        return file_path
    
    def _build_tree_data(self, decomposed_goal: DecomposedGoal) -> Dict[str, Any]:
        """Build hierarchical tree data structure from decomposed goal."""
        
        def build_node(subgoal_id: str, visited: set) -> Dict[str, Any]:
            if subgoal_id in visited:  # Avoid cycles
                return {"name": "Circular Reference", "children": []}
            
            visited.add(subgoal_id)
            subgoal = decomposed_goal.subgoals.get(subgoal_id)
            if not subgoal:
                return {"name": "Unknown", "children": []}
                
            node = {
                "name": subgoal.name,
                "id": subgoal.id,
                "description": subgoal.description,
                "priority": subgoal.priority,
                "time_hours": subgoal.resources.time_hours,
                "type": subgoal.goal_type.name if hasattr(subgoal, 'goal_type') else "UNKNOWN",
                "children": [build_node(child_id, visited.copy()) for child_id in subgoal.children_ids]
            }
            return node
        
        # Root node
        root = {
            "name": decomposed_goal.name,
            "id": decomposed_goal.id,
            "description": decomposed_goal.description,
            "type": decomposed_goal.goal_type.name,
            "children": [build_node(root_id, set()) for root_id in decomposed_goal.root_subgoal_ids]
        }
        
        return root
    
    def _create_networkx_graph(self, decomposed_goal: DecomposedGoal) -> nx.DiGraph:
        """Create a NetworkX graph from a decomposed goal."""
        G = nx.DiGraph()
        
        # Add goal node
        G.add_node(
            "goal",
            name=decomposed_goal.name,
            type="GOAL",
            priority=0
        )
        
        # Add subgoal nodes
        for sg_id, subgoal in decomposed_goal.subgoals.items():
            G.add_node(
                sg_id,
                name=subgoal.name,
                type=subgoal.goal_type.name,
                priority=subgoal.priority
            )
        
        # Add root connections
        for root_id in decomposed_goal.root_subgoal_ids:
            G.add_edge("goal", root_id)
        
        # Add child connections
        for sg_id, subgoal in decomposed_goal.subgoals.items():
            for child_id in subgoal.children_ids:
                G.add_edge(sg_id, child_id)
                
        return G 