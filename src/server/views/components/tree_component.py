import streamlit as st
from typing import Callable, Optional, List, Dict, Any
from uuid import UUID

class TreeNode:
    """Tree node component for hierarchical data structures."""
    
    def __init__(self, id: UUID, name: str, node_type: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.node_type = node_type
        self.metadata = metadata or {}
        self.children: List[TreeNode] = []
        self.expanded: bool = True  # Default to expanded
        
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
    
    def __init__(self, on_node_click: Optional[Callable[[TreeNode], None]] = None):
        self.on_node_click = on_node_click
        
    def render_node(self, node: TreeNode, level: int = 0):
        """Render a single node."""
        # Create indentation
        
        # Choose icon based on node type
        icon = {
            "root": "🗃️", #concider this as well 🗂️
            "category": "📂",
            "agent": "🤖",
            "agentic": "🤖",
            "group": "👥",
            "task": "📋",
            "tool": "🔧"
        }.get(node.node_type, "📄")
        
        # Create unique key for the node
        node_key = f"tree_node_{node.id}_{level}"
        
        # Render node with click handler
        if st.button(f"{icon} {node.name}", key=node_key):
            if self.on_node_click:
                self.on_node_click(node)
        
        # Render children if expanded
        if node.expanded:
            for child in node.children:
                self.render_node(child, level + 1)
    
    def render(self, root_node: Optional[TreeNode], in_sidebar: bool = True):
        """Render the entire tree."""
        if not root_node:
            st.warning("No tree data available")
            return
            
        self.render_node(root_node)
