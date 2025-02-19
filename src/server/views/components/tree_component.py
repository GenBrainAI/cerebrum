import streamlit as st
from typing import Callable, Optional, List, Dict, Any
from uuid import UUID
from ..models.tree_node import TreeNode  # Import the Pydantic TreeNode model

class TreeComponent:
    """Reusable tree visualization component."""
    
    def __init__(self, on_node_click: Optional[Callable[[TreeNode], None]] = None):
        self.on_node_click = on_node_click
    
    def render(self, root_node: Optional[TreeNode], key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Render the tree component."""
        try:
            if not root_node:
                return None
            
            # Initialize session state for expanded nodes if not exists
            if f"{key}_expanded" not in st.session_state:
                st.session_state[f"{key}_expanded"] = set()
            
            # Render the root node and its children recursively
            return self._render_node(root_node, 0, key)
            
        except Exception as e:
            import traceback
            print(f"Error rendering tree: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return None
    
    def _render_node(self, node: TreeNode, level: int, key: str) -> Optional[Dict[str, Any]]:
        """Render a single node and its children."""
        try:
            # Create indentation based on level
            indent = "    " * level
            
            # Choose icon based on node type
            icon = {
                "root": "🗃️",
                "category": "📂",
                "agent": "🤖",
                "agentic": "🤖",
                "group": "👥",
                "task": "📋",
                "tool": "🔧"
            }.get(node.type, "📄")
            
            # Create unique key for this node
            node_key = f"{key}_{node.id}_{level}"
            
            # Create expand/collapse button
            if node.children:
                is_expanded = node_key in st.session_state[f"{key}_expanded"]
                expander = st.button(
                    f"{'▼' if is_expanded else '▶'} {icon} {node.name}",
                    key=f"exp_{node_key}"
                )
                if expander:
                    if is_expanded:
                        st.session_state[f"{key}_expanded"].remove(node_key)
                    else:
                        st.session_state[f"{key}_expanded"].add(node_key)
                    st.rerun()
            else:
                # Leaf node - just show the icon and name
                if st.button(f"{indent}{icon} {node.name}", key=node_key):
                    if self.on_node_click:
                        return {
                            "id": str(node.id),
                            "type": node.type,
                            "data": node.data
                        }
            
            # Render children if expanded
            if node.children and node_key in st.session_state[f"{key}_expanded"]:
                for child in node.children:
                    result = self._render_node(child, level + 1, key)
                    if result:
                        return result
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Error rendering node: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return None
