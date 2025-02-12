"""Context management sidebar component for Streamlit."""

import streamlit as st
from typing import Dict, Any, List, Optional
from src.context_catalog.metadata import SourceType
from src.context_catalog.models import ContextEntry
from ...models.tree_node import TreeNode
from pathlib import Path
import json

class ContextManagementSidebar:
    """Sidebar component for context management."""
    
    def __init__(self, context_manager=None):
        self.context_manager = context_manager
        self.storage_type_indicators = {
            SourceType.KNOWLEDGE_BASE: "📚",
            SourceType.VECTOR_STORE: "🔢",
            SourceType.CODE: "💻",
            SourceType.SYSTEM: "⚙️"
        }
    
    def get_current_state_name(self) -> str:
        """Get the name of the currently loaded state."""
        try:
            # Get state directory from project root
            state_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "state"
            metadata_path = state_dir / "metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    state_name = metadata.get("last_used_state", "").replace(".json", "")
                    return state_name or "Default"
            return "Default"
        except Exception as e:
            print(f"Error getting state name: {str(e)}")
            return "Default"
    
    async def render(self):
        """Render the context management sidebar."""
        with st.sidebar:
            st.header("Context Management")
            
            # Get state status from context manager
            if self.context_manager:
                try:
                    # Get current state name
                    state_name = self.get_current_state_name()
                    st.markdown(f"🟢 **{state_name} Context Loaded**")
                    
                    # Get context associations from state
                    contexts = await self._get_context_associations()
                    if contexts:
                        st.markdown(f"**Context Associations:** {len(contexts)}")
                    else:
                        st.info("No context associations in current state")
                        
                except Exception as e:
                    print(f"Error getting state info: {str(e)}")
                    st.markdown("🔴 Error loading state")
            else:
                st.markdown("🔴 No context manager loaded")
            
            st.markdown("---")
            
            # Build and render context tree
            if self.context_manager:
                try:
                    # Build tree structure
                    root = await self._build_context_tree()
                    
                    if root and root.children:
                        await self._render_tree_node(root)
                    else:
                        st.info("No context data available")
                                
                except Exception as e:
                    print(f"Error rendering context tree: {str(e)}")
                    st.error("Error loading context tree")
    
    async def _build_context_tree(self) -> TreeNode:
        """Build hierarchical tree of data and their associations."""
        root = TreeNode(name="Data Sources", type="root", data=None)
        
        try:
            # Get all global data sources
            global_contexts = await self.context_manager.global_context_provider.get_all_contexts()
            
            # Create nodes for each data source
            for ctx in global_contexts:
                # Get data source title
                title = (
                    ctx.get("metadata", {}).get("title") or 
                    ctx.get("metadata", {}).get("name") or 
                    ctx.get("metadata", {}).get("path") or 
                    str(ctx["id"])
                )
                
                # Create data node with storage type indicator
                storage_type = ctx["type"]
                type_icon = self.storage_type_indicators.get(storage_type, "📄")
                node_name = f"{title} ({storage_type})"
                data_node = TreeNode(name=node_name, type="data", data=ctx)
                root.add_child(data_node)
                
                # Add task associations
                contexts = await self.context_manager.context_provider.get_contexts_by_source(
                    source_id=ctx["id"],
                    type=storage_type
                )
                
                if contexts:
                    # Group by task first
                    task_nodes = {}
                    
                    for assoc in contexts:
                        task = self._get_task_info(assoc.get("task_id"))
                        if task:
                            if task["id"] not in task_nodes:
                                task_node = TreeNode(
                                    name=f"📋 {task['name']} (Priority: {assoc['priority']})",
                                    type="task",
                                    data={"type": "task", "id": task["id"], "priority": assoc["priority"]}
                                )
                                task_nodes[task["id"]] = task_node
                                data_node.add_child(task_node)
                        
                        # Add manager if it exists
                        manager = self._get_manager_info(assoc.get("manager_id"))
                        if manager:
                            manager_node = TreeNode(
                                name=f"📊 {manager['name']}",
                                type="manager",
                                data={"type": "manager", "id": manager["id"]}
                            )
                            data_node.add_child(manager_node)
            
            return root
            
        except Exception as e:
            print(f"Error building context tree: {str(e)}")
            return root
    
    async def _render_tree_node(self, node: TreeNode, level: int = 0):
        """Render a tree node and its children recursively."""
        if not node:
            return
            
        # Skip root node display
        if level > 0:
            # Create indentation
            indent = "  " * (level - 1)
            
            # Display node
            if node.type == "data":
                st.markdown(f"{indent}{node.name}")
                if st.button("View", key=f"view_{node.data['id']}", use_container_width=True):
                    st.session_state.selected_context = node.data["id"]
                    st.session_state.context_view = node.data["type"]
            else:
                st.markdown(f"{indent}{node.name}")
        
        # Render children
        for child in node.children:
            await self._render_tree_node(child, level + 1)
    
    async def _get_context_associations(self) -> List[Dict[str, Any]]:
        """Get all context associations from current state."""
        try:
            # Get all tasks and managers
            persistence_model = self.context_manager.persistence_model
            tasks = persistence_model.tasks.list()
            managers = persistence_model.tasksmanagers.list()
            
            associations = []
            
            # Get contexts for each task
            for task in tasks:
                contexts = await self.context_manager.context_provider.get_task_contexts(task.id)
                if contexts:
                    associations.extend(contexts)
            
            # Get contexts for each manager
            for manager in managers:
                contexts = await self.context_manager.context_provider.get_manager_contexts(manager.id)
                if contexts:
                    associations.extend(contexts)
                    
            return associations
            
        except Exception as e:
            print(f"Error getting context associations: {str(e)}")
            return []
    
    def _get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information from persistence model."""
        try:
            persistence_model = self.context_manager.persistence_model
            task = persistence_model.tasks.get(task_id)
            if task:
                return {"id": task.id, "name": task.name}
        except Exception as e:
            print(f"Error getting task info: {str(e)}")
        return None
    
    def _get_manager_info(self, manager_id: str) -> Optional[Dict[str, Any]]:
        """Get task manager information from persistence model."""
        try:
            persistence_model = self.context_manager.persistence_model
            manager = persistence_model.tasksmanagers.get(manager_id)
            if manager:
                return {"id": manager.id, "name": manager.name}
        except Exception as e:
            print(f"Error getting manager info: {str(e)}")
        return None

async def render_context_mng_sidebar():
    """Render the context management sidebar."""
    if 'context_manager' in st.session_state:
        sidebar = ContextManagementSidebar(st.session_state.context_manager)
        await sidebar.render()
    else:
        with st.sidebar:
            st.warning("Context manager not initialized") 