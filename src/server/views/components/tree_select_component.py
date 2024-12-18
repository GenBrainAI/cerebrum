from typing import Optional, List, Dict, Any, Callable
from uuid import UUID
import streamlit as st
from streamlit_tree_select import tree_select

class TreeSelectComponent:
    """Wrapper for streamlit-tree-select component."""
    
    def __init__(self, on_node_click: Optional[Callable] = None):
        self.on_node_click = on_node_click
        self._expanded_nodes: List[str] = []
        self._selected_nodes: List[str] = []
    
    def _convert_tree_node_to_dict(self, node) -> Dict[str, Any]:
        """Convert TreeNode to format expected by streamlit-tree-select."""
        result = {
            "label": node.name,
            "value": str(node.id),
            "children": [],
            "type": node.node_type
        }
        
        if hasattr(node, 'children'):
            result["children"] = [
                self._convert_tree_node_to_dict(child) 
                for child in node.children
            ]
            
        return result
    
    def render(self, root_node, key: Optional[str] = None) -> Dict[str, List[str]]:
        """Render the tree select component."""
        if not root_node:
            return None
            
        # Convert TreeNode structure to dictionary format
        nodes = [self._convert_tree_node_to_dict(root_node)]
        
        # Add custom styling based on node type
        def add_class_names(node_dict):
            if node_dict.get("type") == "manager":
                node_dict["className"] = "manager-node"
            elif node_dict.get("type") == "task":
                node_dict["className"] = "task-node"
            elif node_dict.get("type") == "tool":
                node_dict["className"] = "tool-node"
            elif node_dict.get("type") == "category":
                node_dict["className"] = "category-node"
            elif node_dict.get("type") == "agentic":
                node_dict["className"] = "agentic-node"
            
            # Recursively process children
            for child in node_dict.get("children", []):
                add_class_names(child)
        
        # Process all nodes including children
        for node in nodes:
            add_class_names(node)
        
        try:
            # Render tree select with enhanced options
            result = tree_select(
                nodes,
                checked=self._selected_nodes,
                expanded=self._expanded_nodes,
                show_expand_all=True,
                expand_on_click=True,
                check_model="leaf",  # Only allow selecting leaf nodes
                only_leaf_checkboxes=True,  # Only show checkboxes on leaf nodes
                key=key or "tree_select"
            )
            
            # Handle the result based on its type
            if isinstance(result, dict):
                # Update internal state if result has the expected structure
                if "checked" in result:
                    self._selected_nodes = result["checked"]
                if "expanded" in result:
                    self._expanded_nodes = result["expanded"]
                
                # Handle node selection if callback provided
                if self.on_node_click and self._selected_nodes:
                    selected_id = UUID(self._selected_nodes[-1])
                    self.on_node_click(selected_id)
            else:
                # If result is not a dict, it might be the selected values directly
                self._selected_nodes = result if isinstance(result, list) else []
                
                # Handle node selection if callback provided and we have selections
                if self.on_node_click and self._selected_nodes:
                    selected_id = UUID(self._selected_nodes[-1])
                    self.on_node_click(selected_id)
            
            return result
            
        except Exception as e:
            st.error(f"Error rendering tree select: {str(e)}")
            return None