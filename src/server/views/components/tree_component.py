import streamlit as st
from typing import Callable, Optional, List, Dict, Any
from uuid import UUID

class TreeNode:
    """Tree node component for hierarchical data structures."""
    
    def __init__(self, id: UUID, name: str, type: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.type = type
        self.metadata = metadata or {}
        self.children: List[TreeNode] = []
        self.expanded: bool = False
        
    def traverse(self):
        """Generator to traverse all nodes in the tree."""
        yield self
        for child in self.children:
            yield from child.traverse()
            
    def find_node(self, node_id: UUID) -> Optional['TreeNode']:
        """Find node by ID in the tree."""
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find_node(node_id)
            if found:
                return found
        return None

class TreeComponent:
    """Reusable tree visualization component."""
    
    def __init__(self, on_node_click: Optional[Callable] = None):
        self.on_node_click = on_node_click
        
    def render(self, root_node: TreeNode, level: int = 0):
        """Render a tree node and its children."""
        if not root_node:
            return
            
        # Create columns for node layout
        cols = st.columns([0.5, 3, 0.5])
        
        with cols[1]:
            # Render node with indentation
            label = "  " * level + ("▼ " if root_node.expanded else "▶ ")
            if st.button(f"{label} {root_node.name}", key=str(root_node.id)):
                root_node.expanded = not root_node.expanded
                if self.on_node_click:
                    self.on_node_click(root_node)
        
        # Render children if expanded
        if root_node.expanded:
            for child in root_node.children:
                self.render(child, level + 1)
