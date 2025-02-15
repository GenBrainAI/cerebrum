"""Context management sidebar component for Streamlit."""

import streamlit as st
from typing import Dict, Any, List, Optional
from src.context_catalog.metadata import SourceType
from src.context_catalog.models import ContextEntry
from ...models.tree_node import TreeNode
from pathlib import Path
import json
from ...components.tree_select_component import TreeSelectComponent
from uuid import UUID
import traceback

class ContextManagementSidebar:
    """Sidebar component for context management."""
    
    def __init__(self, context_manager=None):
        print("\n🔍 Initializing ContextManagementSidebar")
        self.context_manager = context_manager
        self.storage_type_indicators = {
            SourceType.KNOWLEDGE_BASE: "📚",
            SourceType.VECTOR_STORE: "🔢",
            SourceType.CODE: "💻",
            SourceType.SYSTEM: "⚙️"
        }
        
        # Initialize tree state in session state if not exists
        if 'context_tree_state' not in st.session_state:
            print("  Initializing context tree state")
            st.session_state.context_tree_state = {
                'expanded': [],
                'selected': []
            }
        
        # Use shared tree component from session state
        if 'context_tree_component' not in st.session_state:
            print("  Creating new TreeSelectComponent in session state")
            st.session_state.context_tree_component = TreeSelectComponent()
        else:
            print("  Using existing TreeSelectComponent from session state")
        self.tree_component = st.session_state.context_tree_component
        
        # Initialize tree component with session state
        self.tree_component._expanded_nodes = st.session_state.context_tree_state['expanded']
        self.tree_component._selected_nodes = st.session_state.context_tree_state['selected']
        
        # Debug session state
        print("\n📊 Current Session State:")
        print(f"  Tree state: {st.session_state.context_tree_state}")
        for key, value in st.session_state.items():
            if 'context' in key.lower():
                print(f"  {key}: {value}")
    
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
        print("\n🎨 Rendering Context Management Sidebar")
        
        with st.sidebar:
            st.header("Context Management")
            
            # Get state status from context manager
            if self.context_manager:
                try:
                    state_name = self.get_current_state_name()
                    print(f"  Current state name: {state_name}")
                    st.markdown(f"🟢 **{state_name} Context Loaded**")
                    
                    contexts = await self._get_context_associations()
                    if contexts:
                        print(f"  Found {len(contexts)} context associations")
                        st.markdown(f"**Context Associations:** {len(contexts)}")
                        
                except Exception as e:
                    print(f"❌ Error getting state info: {str(e)}")
                    st.markdown("🔴 Error loading state")
            else:
                print("❌ No context manager loaded")
                st.markdown("🔴 No context manager loaded")
            
            st.markdown("---")
            
            # Build and render context tree using tree component
            if self.context_manager:
                try:
                    print("\n🌳 Building context tree")
                    tree_data = await self._build_context_tree()
                    if tree_data:
                        print(f"  Tree built successfully with {len(tree_data.children)} root children")
                        print("  Tree structure:")
                        self._print_tree_structure(tree_data)
                        
                        print("\n🎯 Rendering tree with TreeSelectComponent")
                        print(f"  Component state before render:")
                        print(f"    Expanded nodes: {self.tree_component._expanded_nodes}")
                        print(f"    Selected nodes: {self.tree_component._selected_nodes}")
                        
                        result = self.tree_component.render(
                            tree_data,
                            key="context_tree_sidebar"
                        )
                        
                        print(f"\n📊 Render result: {result}")
                        
                        if result is None:
                            print("❌ Tree render returned None")
                            st.warning("Failed to load context tree")
                        elif result:  # Handle selection
                            print(f"✅ Tree rendered with selection: {result}")
                            
                            # Update tree state in session state
                            st.session_state.context_tree_state['expanded'] = result['data'].get('expanded', [])
                            st.session_state.context_tree_state['selected'] = result['data'].get('checked', [])
                            print(f"  Updated tree state: {st.session_state.context_tree_state}")
                            
                            # Update component state
                            self.tree_component._expanded_nodes = st.session_state.context_tree_state['expanded']
                            self.tree_component._selected_nodes = st.session_state.context_tree_state['selected']
                            
                            if result.get('data') and 'id' in result['data']:
                                print(f"  Updating selection in session state:")
                                print(f"    selected_context: {result['data']['id']}")
                                print(f"    context_view: {result['data'].get('type', 'vector')}")
                                st.session_state.selected_context = result['data']['id']
                                st.session_state.context_view = result['data'].get('type', 'vector')
                    else:
                        print("❌ No tree data available")
                        st.info("No context data available")
                                
                except Exception as e:
                    print(f"❌ Error rendering context tree: {str(e)}")
                    print(f"Stack trace: {traceback.format_exc()}")
                    st.error("Error loading context tree")
    
    def _print_tree_structure(self, node: TreeNode, level: int = 0):
        """Helper method to print tree structure for debugging."""
        indent = "  " * level
        print(f"{indent}- {node.name} ({node.type})")
        for child in node.children:
            self._print_tree_structure(child, level + 1)
    
    async def _build_context_tree(self) -> TreeNode:
        """Build hierarchical tree of data catalog and task connections."""
        print("\n🔍 Starting to build context tree...")
        
        # Use fixed UUIDs for consistent tree structure
        ROOT_ID = UUID('00000000-0000-0000-0000-000000000000')
        VECTOR_ID = UUID('11111111-1111-1111-1111-111111111111')
        KNOWLEDGE_ID = UUID('22222222-2222-2222-2222-222222222222')
        CODE_ID = UUID('33333333-3333-3333-3333-333333333333')
        
        root = TreeNode(
            id=ROOT_ID,
            name="Data Catalog",
            type="root",
            metadata={"icon": "📚"},
            data={"type": "root"}
        )
        
        try:
            print("  Creating category nodes...")
            # Create category nodes with fixed IDs
            vector_node = TreeNode(
                id=VECTOR_ID,
                name="Vector Store",
                type="category",
                metadata={"icon": "🔢"},
                data={"type": "vector"}
            )
            knowledge_node = TreeNode(
                id=KNOWLEDGE_ID,
                name="Knowledge Base",
                type="category",
                metadata={"icon": "📚"},
                data={"type": "knowledge"}
            )
            code_node = TreeNode(
                id=CODE_ID,
                name="Code",
                type="category",
                metadata={"icon": "💻"},
                data={"type": "code"}
            )
            root.add_child(vector_node)
            root.add_child(knowledge_node)
            root.add_child(code_node)
            
            print("\n  Getting global contexts...")
            # Get all global data sources
            global_contexts = await self.context_manager.global_context_provider.get_all_contexts()
            print(f"  Found {len(global_contexts)} global contexts")
            
            # Get task associations and build lookups
            task_associations = {}
            task_info = {}
            manager_info = {}
            
            print("\n  Getting task associations...")
            if not self.context_manager.global_context_provider.is_global:
                persistence_model = self.context_manager.persistence_model
                tasks = persistence_model.tasks.list()
                managers = persistence_model.tasksmanagers.list()
                
                print(f"  Found {len(tasks)} tasks and {len(managers)} managers")
                
                # Build lookups
                task_info = {t.id: t for t in tasks}
                manager_info = {m.id: m for m in managers}
                
                # Get all task associations for each source
                for ctx in global_contexts:
                    print(f"\n  Getting associations for context {ctx['id']} ({ctx['type']})")
                    source_assocs = await self.context_manager.context_provider.get_contexts_by_source(
                        source_id=ctx["id"],
                        type=ctx["type"]
                    )
                    if source_assocs:
                        print(f"    Found {len(source_assocs)} associations")
                        task_associations[ctx["id"]] = source_assocs
                    else:
                        print("    No associations found")
            
            # Group contexts by type
            type_contexts = {
                "vector": [],
                "knowledge": [],
                "code": []
            }
            
            for ctx in global_contexts:
                type_contexts[ctx["type"]].append(ctx)
            
            print("\n  Processing Vector Store contexts...")
            # Process Vector Store contexts
            for ctx in type_contexts["vector"]:
                print(f"\n    Processing vector store: {ctx['id']}")
                index_name = ctx["metadata"].get("name", ctx["id"])
                doc_count = ctx["metadata"].get("document_count", 0)
                print(f"    Name: {index_name}, Documents: {doc_count}")
                
                # Use consistent ID based on the context ID
                index_node = TreeNode(
                    id=UUID(f"00000000-0000-4000-8000-{abs(hash(ctx['id'])) % 0xFFFFFFFFF:012x}"),  # Generate stable UUID from hash
                    name=index_name,
                    type="index",
                    metadata={
                        "icon": "📁",
                        "description": f"{doc_count} documents",
                        "actions": [{"name": "view", "icon": "📄", "tooltip": "View contents"}]
                    },
                    data={"type": "index", "id": ctx["id"]}  # Store original ID in data
                )
                vector_node.add_child(index_node)
                
                # Add task connections if any
                assocs = task_associations.get(ctx["id"], [])
                if assocs:
                    print(f"    Found {len(assocs)} task connections")
                    connections_node = TreeNode(
                        id=UUID(f"{ctx['id']}-connections"),  # Consistent ID for connections node
                        name="Task Connections",
                        type="connections",
                        metadata={"icon": "📎"},
                        data={"type": "connections"}
                    )
                    index_node.add_child(connections_node)
                    
                    # Group by manager
                    manager_tasks = {}
                    standalone_tasks = []
                    
                    for assoc in assocs:
                        if assoc.get("manager_id"):
                            if assoc["manager_id"] not in manager_tasks:
                                manager_tasks[assoc["manager_id"]] = []
                            manager_tasks[assoc["manager_id"]].append(assoc)
                        elif assoc.get("task_id"):
                            standalone_tasks.append(assoc)
                    
                    # Add manager groups
                    for manager_id, manager_assocs in manager_tasks.items():
                        manager = manager_info.get(manager_id)
                        if manager:
                            print(f"      Adding manager node: {manager.name}")
                            manager_node = TreeNode(
                                id=UUID(manager_id) if isinstance(manager_id, str) else manager_id,
                                name=manager.name,
                                type="manager",
                                metadata={"icon": "📊"},
                                data={"type": "manager", "id": manager_id}
                            )
                            connections_node.add_child(manager_node)
                            
                            # Add tasks under manager
                            for assoc in manager_assocs:
                                if assoc.get("task_id"):
                                    task = task_info.get(assoc["task_id"])
                                    if task:
                                        print(f"        Adding task node: {task.name}")
                                        task_node = TreeNode(
                                            id=UUID(task.id) if isinstance(task.id, str) else task.id,
                                            name=task.name,
                                            type="task",
                                            metadata={
                                                "icon": "📋",
                                                "description": f"Priority: {assoc.get('priority', 50)}"
                                            },
                                            data={"type": "task", "id": task.id}
                                        )
                                        manager_node.add_child(task_node)
                    
                    # Add standalone tasks
                    for assoc in standalone_tasks:
                        task = task_info.get(assoc["task_id"])
                        if task:
                            print(f"      Adding standalone task node: {task.name}")
                            task_node = TreeNode(
                                id=UUID(task.id) if isinstance(task.id, str) else task.id,
                                name=task.name,
                                type="task",
                                metadata={
                                    "icon": "📋",
                                    "description": f"Priority: {assoc.get('priority', 50)}"
                                },
                                data={"type": "task", "id": task.id}
                            )
                            connections_node.add_child(task_node)
                else:
                    print("    No task connections found")
            
            print("\n✅ Context tree built successfully")
            return root
            
        except Exception as e:
            print(f"\n❌ Error building context tree: {str(e)}")
            traceback.print_exc()
            return root
    
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