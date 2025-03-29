import streamlit as st
from typing import Dict, Any, Optional, List
from ..models.tree_node import TreeNode
from ..components.tree_component import TreeComponent
import uuid

class TaskTreeHandoverComponent(TreeComponent):
    """Enhanced tree component for visualizing task handover relationships."""
    
    def __init__(self, on_node_click=None):
        super().__init__(on_node_click)
        
    def render(self, tree_data: TreeNode, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Render the tree with handover relationships."""
        # Get base rendering from parent class
        result = super().render(tree_data, key)
        
        # Add handover connections visualization
        self._render_handover_connections(tree_data)
        
        return result
    
    def _render_handover_connections(self, tree_data: TreeNode):
        """Render visual connections showing handover relationships."""
        # First, collect all nodes with handover relationships
        nodes_with_handover = []
        self._collect_handover_nodes(tree_data, nodes_with_handover)
        
        if not nodes_with_handover:
            return
            
        # Render connections container
        st.markdown("""
        <style>
        .task-flow-container {
            position: relative;
            margin-top: 10px;
        }
        .task-flow-line {
            stroke: #2196F3;
            stroke-width: 2;
            stroke-dasharray: 5, 5;
        }
        .task-node.has-inputs {
            border-left: 3px solid #4CAF50 !important;
        }
        .task-node.has-outputs {
            border-right: 3px solid #2196F3 !important;
        }
        </style>
        <div class="task-flow-container" id="task-flow-container"></div>
        """, unsafe_allow_html=True)
        
        # Generate JavaScript for drawing connections
        js_code = """
        <script>
        function connectNodes(sourceId, targetId) {
            const sourceNode = document.getElementById(sourceId);
            const targetNode = document.getElementById(targetId);
            
            if (!sourceNode || !targetNode) return;
            
            const container = document.getElementById('task-flow-container');
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%');
            svg.style.position = 'absolute';
            svg.style.top = '0';
            svg.style.left = '0';
            svg.style.pointerEvents = 'none';
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            line.classList.add('task-flow-line');
            
            // Calculate positions
            const sourceRect = sourceNode.getBoundingClientRect();
            const targetRect = targetNode.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            const x1 = sourceRect.right - containerRect.left;
            const y1 = sourceRect.top + sourceRect.height/2 - containerRect.top;
            const x2 = targetRect.left - containerRect.left;
            const y2 = targetRect.top + targetRect.height/2 - containerRect.top;
            
            // Draw curved path
            const dx = Math.abs(x2 - x1) * 0.5;
            const path = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
            line.setAttribute('d', path);
            
            svg.appendChild(line);
            container.appendChild(svg);
        }
        </script>
        """
        st.markdown(js_code, unsafe_allow_html=True)
        
        # Generate connection calls for each handover relationship
        for node in nodes_with_handover:
            if "outputs_to" in node.data:
                for target_id in node.data["outputs_to"]:
                    # Create JS to connect the nodes
                    connect_js = f"""
                    <script>
                    // Connect {node.id} to {target_id}
                    (function() {{
                        setTimeout(function() {{
                            connectNodes("{node.id}", "{target_id}");
                        }}, 500);
                    }})();
                    </script>
                    """
                    st.markdown(connect_js, unsafe_allow_html=True)
    
    def _collect_handover_nodes(self, node: TreeNode, result: List):
        """Recursively collect nodes with handover relationships."""
        if node.data and (node.data.get("has_inputs") or node.data.get("outputs_to")):
            result.append(node)
            
        for child in node.children:
            self._collect_handover_nodes(child, result)
    
    def _render_node(self, node: TreeNode, level: int, key: str) -> Optional[Dict[str, Any]]:
        """Override render_node to add handover indicators."""
        # Start with standard node rendering from parent
        result = super()._render_node(node, level, key)
        
        # Add handover-specific classes
        if node.data:
            has_inputs = node.data.get("has_inputs", False)
            has_outputs = "outputs_to" in node.data and len(node.data["outputs_to"]) > 0
            
            # Add visual indicators for nodes with handover
            if has_inputs or has_outputs:
                node_id = str(node.id)
                css_classes = []
                if has_inputs:
                    css_classes.append("has-inputs")
                if has_outputs:
                    css_classes.append("has-outputs")
                
                # Add custom styling
                st.markdown(f"""
                <style>
                #{node_id} {{
                    {f"border-left: 3px solid #4CAF50 !important;" if has_inputs else ""}
                    {f"border-right: 3px solid #2196F3 !important;" if has_outputs else ""}
                }}
                </style>
                """, unsafe_allow_html=True)
        
        return result 