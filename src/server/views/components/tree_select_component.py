from typing import Optional, List, Dict, Any, Callable
from uuid import UUID
import streamlit as st
from streamlit_tree_select import tree_select
from ..models.tree_node import TreeNode

class TreeSelectComponent:
    """Wrapper for streamlit-tree-select component."""
    
    def __init__(self, on_node_click: Optional[Callable] = None):
        print("\n🔧 Initializing TreeSelectComponent")
        self.on_node_click = on_node_click
        self._expanded_nodes: List[str] = []
        self._selected_nodes: List[str] = []
        print(f"  Initial state:")
        print(f"    Expanded nodes: {self._expanded_nodes}")
        print(f"    Selected nodes: {self._selected_nodes}")
    
    def _convert_tree_node_to_dict(self, node: TreeNode) -> Dict[str, Any]:
        """Convert TreeNode to format expected by streamlit-tree-select."""
        # print(f"\n🔄 Converting node: {node.name} ({node.type})")
        
        # Add icon based on type
        icon = {
            "root": "🗃️",
            "category": "📂",
            "agent": "🤖",
            "agentic": "🤖",
            "group": "👥",
            "task": "📋",
            "tool": "🔧",
            "empty": "📄"
        }.get(node.type.lower(), "📄")
        
        result = {
            "label": f"{icon} {node.name}",
            "value": str(node.id),
            "children": [],
            "data": node.data or {}
        }
        
        # Add class name based on type
        result["className"] = f"{node.type.lower()}-node"
        
        # Convert children recursively
        if hasattr(node, 'children'):
            result["children"] = [
                self._convert_tree_node_to_dict(child) 
                for child in node.children
            ]
        
        # print(f"  Converted to: {result['label']}")
        return result
    
    def render(self, root_node: Optional[TreeNode], key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Render the tree select component."""
        try:
            print(f"\n🎨 Rendering TreeSelectComponent with key: {key}")
            print(f"  Current state before render:")
            print(f"    Expanded nodes: {self._expanded_nodes}")
            print(f"    Selected nodes: {self._selected_nodes}")
            
            if not root_node:
                print("❌ No root node provided")
                return None
                
            # Convert TreeNode structure to dictionary format
            nodes = [self._convert_tree_node_to_dict(root_node)]
            print(f"\n📊 Converted tree structure:")
            print(f"  Root node: {nodes[0]['label']}")
            print(f"  Children count: {len(nodes[0]['children'])}")
            
            # Add CSS for node styling
            st.markdown("""
                <style>
                    .root-node { font-weight: bold; }
                    .category-node { font-weight: 500; }
                    .task-node { padding-left: 0.5rem; }
                    .tool-node { padding-left: 0.5rem; }
                    .empty-node { color: #666; font-style: italic; }
                    /* Fix for leaf node thickness */
                    .st-emotion-cache-1gulkj5 { margin-bottom: 0 !important; }
                    /* Improve indentation */
                    .streamlit-tree { padding-left: 0.5rem; }
                    .streamlit-tree ul { padding-left: 1.5rem !important; }
                </style>
            """, unsafe_allow_html=True)
            
            print("\n🎯 Calling tree_select with:")
            print(f"  Checked nodes: {self._selected_nodes}")
            print(f"  Expanded nodes: {self._expanded_nodes}")
            
            # Render tree select with enhanced options
            result = tree_select(
                nodes,
                checked=self._selected_nodes,
                expanded=self._expanded_nodes,
                show_expand_all=True,
                expand_on_click=True,
                check_model="leaf",
                only_leaf_checkboxes=True,
                key=key or "tree_select"
            )
            
            print(f"\n📊 Tree select result: {result}")
            
            # Handle the result based on its type
            if isinstance(result, dict):
                print("\n🔄 Updating component state:")
                # Update internal state
                self._selected_nodes = result.get("checked", [])
                self._expanded_nodes = result.get("expanded", [])
                print(f"  New expanded nodes: {self._expanded_nodes}")
                print(f"  New selected nodes: {self._selected_nodes}")
                
                # Handle node selection if callback provided
                if self.on_node_click and self._selected_nodes:
                    selected_id = UUID(self._selected_nodes[-1])
                    print(f"  Calling node click callback with ID: {selected_id}")
                    self.on_node_click(selected_id)
                    
                return {
                    "id": self._selected_nodes[-1] if self._selected_nodes else None,
                    "type": "selected",
                    "data": result
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error in tree select render: {str(e)}")
            st.error(f"Error rendering tree select: {str(e)}")
            return None