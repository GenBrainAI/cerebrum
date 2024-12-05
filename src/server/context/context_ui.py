import streamlit as st
from typing import Optional, Dict, Any
from pathlib import Path

from src.server.context.context_database import ContextDatabase
from src.server.context.code_catalog import CodeCatalog
from src.server.context.knowledge_base import KnowledgeBase
from src.server.controllers import context_state_controller
from src.server.models.persistence_models import StorageLocation, StorageType
from ..controllers.persistence_controller import load_from_storage, save_to_storage

class ContextManagerUI:
    """Enhanced UI component for managing and visualizing the context system."""
    
    def __init__(self):
        """Initialize context management components."""
        self.context_db = ContextDatabase()
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase()
        
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of all context components."""
        return {
            "context_db": {
                # Add context DB state data
                "collections": self.context_db.get_collection_stats()
            },
            "code_catalog": {
                "files": len(self.code_catalog.file_index),
                "dependencies": len(self.code_catalog.dependencies)
            },
            "knowledge_base": {
                "entries": len(self.knowledge_base.knowledge_index.get("entries", {})),
                "domains": len(self.knowledge_base.knowledge_index.get("domains", {})),
                "tags": len(self.knowledge_base.knowledge_index.get("tags", {}))
            }
        }
        
    def render_persistent_state_ui(self):
        """Render UI for managing persistent state."""
        with st.expander("Persistent State Management", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Save State")
                state_name = st.text_input("State Name")
                if st.button("Save Current State"):
                    if state_name:
                        try:
                            current_state = self.get_current_state()
                            result = context_state_controller.save_context_state(
                                name=state_name,
                                state_data=current_state
                            )
                            st.success(result)
                        except Exception as e:
                            st.error(f"Error saving state: {str(e)}")
            
            with col2:
                st.subheader("Load State")
                saved_states = context_state_controller.list_saved_states()
                if saved_states:
                    selected_state = st.selectbox(
                        "Select saved state",
                        list(saved_states.keys()),
                        format_func=lambda x: f"{x} (Saved: {saved_states[x]['saved_at']})"
                    )
                    if st.button("Load Selected State"):
                        try:
                            state_data = context_state_controller.load_context_state(selected_state)
                            # Here we would restore the state to components
                            st.success(f"State '{selected_state}' loaded successfully")
                            st.rerun()  # Refresh the UI
                        except Exception as e:
                            st.error(f"Error loading state: {str(e)}")
                            
            # Add delete button for states
            if saved_states:
                st.markdown("---")
                state_to_delete = st.selectbox(
                    "Select state to delete",
                    list(saved_states.keys()),
                    key="delete_state_select"
                )
                if st.button("Delete Selected State", type="secondary"):
                    if context_state_controller.delete_state(state_to_delete):
                        st.success(f"State '{state_to_delete}' deleted successfully")
                        st.rerun()
                    else:
                        st.error("Failed to delete state")
        
    def render_header(self):
        """Render the header section with improved layout."""
        # Create a container for the header
        header_container = st.container()
        
        with header_container:
            # Use columns for better layout control
            logo_col, title_col = st.columns([1, 4])
            
            with logo_col:
                # Place logo in the top-left
                logo_path = self._get_logo_path()
                if logo_path:
                    st.image(logo_path, width=100)
            
            with title_col:
                st.title("Context Management")
                st.markdown("""
                Manage code repositories, domain knowledge, and context settings 
                in one centralized interface.
                """)
    
    def render_navigation(self):
        """Render the horizontal navigation menu."""
        st.markdown("---")
        nav_cols = st.columns(4)
        
        with nav_cols[0]:
            if st.button("📚 Knowledge Base", use_container_width=True):
                st.session_state.context_view = "knowledge"
                
        with nav_cols[1]:
            if st.button("🔍 Code Analysis", use_container_width=True):
                st.session_state.context_view = "code"
                
        with nav_cols[2]:
            if st.button("🔄 Vector Store", use_container_width=True):
                st.session_state.context_view = "vector"
                
        with nav_cols[3]:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state.context_view = "settings"
        
        st.markdown("---")
    
    def render_status_bar(self):
        """Render a status bar showing system metrics."""
        stats = self.get_statistics()
        
        status_cols = st.columns(4)
        with status_cols[0]:
            st.metric("Indexed Files", stats.get("total_files", 0))
        with status_cols[1]:
            st.metric("Knowledge Entries", stats.get("total_entries", 0))
        with status_cols[2]:
            st.metric("Vector Chunks", stats.get("total_chunks", 0))
        with status_cols[3]:
            st.metric("Memory Usage", f"{stats.get('memory_usage', 0)}MB")
    
    def render_persistent_state_ui(self):
        """Render UI for managing persistent state."""
        with st.expander("Persistent State Management", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Save State")
                state_name = st.text_input("State Name")
                if st.button("Save Current State"):
                    if state_name:
                        location = StorageLocation(
                            type=StorageType.file,
                            location="state",
                            state_name=f"{state_name}.json"
                        )
                        result = save_to_storage(location)
                        st.success(f"State saved: {result}")
            
            with col2:
                st.subheader("Load State")
                state_files = list(Path("state").glob("*.json"))
                if state_files:
                    selected_state = st.selectbox(
                        "Select saved state",
                        [f.stem for f in state_files]
                    )
                    if st.button("Load Selected State"):
                        location = StorageLocation(
                            type=StorageType.file,
                            location="state",
                            state_name=f"{selected_state}.json"
                        )
                        result = load_from_storage(location)
                        st.success(f"State loaded: {result}")
    
    def render_main_view(self):
        """Render the main content based on selected view."""
        if "context_view" not in st.session_state:
            st.session_state.context_view = "knowledge"
            
        view = st.session_state.context_view
        
        if view == "knowledge":
            self.render_knowledge_view()
        elif view == "code":
            self.render_code_view()
        elif view == "vector":
            self.render_vector_view()
        elif view == "settings":
            self.render_settings_view()
    
    def render(self):
        """Main render method for the context manager UI."""
        self.render_header()
        self.render_navigation()
        self.render_status_bar()
        self.render_persistent_state_ui()
        self.render_main_view()

    def _get_logo_path(self) -> Optional[str]:
        """Get the path to the logo file."""
        potential_paths = [
            Path(__file__).parent.parent.parent / "logo.png",
            Path(__file__).parent.parent / "logo.png",
            Path.cwd() / "logo.png"
        ]
        
        for path in potential_paths:
            if path.exists():
                return str(path)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        import psutil
        
        stats = {
            "total_files": len(self.code_catalog.file_index),
            "total_entries": len(self.knowledge_base.knowledge_index.get("entries", {})),
            "total_chunks": 0,  # To be implemented with vector store
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # MB
        }
        
        return stats
    
    def render_knowledge_view(self):
        """Render the knowledge base management view."""
        st.subheader("Knowledge Base Management")

        # Add knowledge section
        with st.expander("Add Knowledge Entry", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                domain = st.text_input("Domain")
                content = st.text_area("Content")
                description = st.text_input("Description (optional)")
                
            with col2:
                tags = st.text_input("Tags (comma-separated)")
                metadata = st.text_area("Additional Metadata (JSON)", value="{}")
                
            if st.button("Add Knowledge Entry"):
                try:
                    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
                    meta_dict = json.loads(metadata) if metadata.strip() else {}
                    
                    entry_id = self.knowledge_base.add_knowledge(
                        content=content,
                        domain=domain,
                        metadata={
                            "description": description,
                            "tags": tags_list,
                            **meta_dict
                        },
                        tags=tags_list
                    )
                    st.success(f"Knowledge entry added with ID: {entry_id}")
                except Exception as e:
                    st.error(f"Error adding knowledge: {str(e)}")

        # Browse knowledge section
        st.markdown("---")
        st.subheader("Browse Knowledge")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_domain = st.selectbox(
                "Filter by Domain",
                options=["All"] + list(self.knowledge_base.knowledge_index.get("domains", {}).keys())
            )
        
        with col2:
            selected_tags = st.multiselect(
                "Filter by Tags",
                options=list(self.knowledge_base.knowledge_index.get("tags", {}).keys())
            )
        
        entries = self.knowledge_base.get_knowledge(
            domain=None if selected_domain == "All" else selected_domain,
            tags=selected_tags if selected_tags else None
        )
        
        for entry in entries:
            with st.expander(f"{entry['domain']} - {entry.get('metadata', {}).get('description', 'No description')}"):
                st.markdown(entry['content'])
                st.json(entry.get('metadata', {}))

    def render_code_view(self):
        """Render the code analysis view."""
        st.subheader("Code Analysis")

        # Code ingestion section
        with st.expander("Ingest Code Repository", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                repo_path = st.text_input("Repository Path")
                exclude_dirs = st.text_input(
                    "Exclude Directories",
                    value="venv,__pycache__,.git,node_modules"
                ).split(",")
                
            with col2:
                st.markdown("### Options")
                analyze_deps = st.checkbox("Analyze Dependencies", value=True)
                parse_docs = st.checkbox("Parse Documentation", value=True)
                
            if st.button("Analyze Repository"):
                with st.spinner("Analyzing code..."):
                    try:
                        stats = asyncio.run(self.code_catalog.index_directory(
                            repo_path,
                            exclude_dirs=exclude_dirs
                        ))
                        st.success(f"Repository analyzed: {stats}")
                    except Exception as e:
                        st.error(f"Error analyzing repository: {str(e)}")

        # Code browser section
        st.markdown("---")
        st.subheader("Code Browser")
        
        if self.code_catalog.file_index:
            selected_file = st.selectbox(
                "Select File",
                options=list(self.code_catalog.file_index.keys())
            )
            
            if selected_file:
                file_info = self.code_catalog.get_file_info(selected_file)
                if file_info:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.code(file_info.get('content', ''), language='python')
                        
                    with col2:
                        st.markdown("### File Info")
                        st.write(f"Size: {file_info['size']} bytes")
                        st.write(f"Last Modified: {file_info['last_modified']}")
                        
                        st.markdown("### Dependencies")
                        for dep in file_info.get('imports', []):
                            st.write(f"- {dep}")

    def render_vector_view(self):
        """Render the vector store management view."""
        st.subheader("Vector Store Management")

        # Vector store statistics
        stats = self.context_db.vector_store.get_collection_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Items", stats.get("total_items", 0))
        with col2:
            st.metric("Embedding Dimension", stats.get("embedding_dimension", 0))
        with col3:
            st.metric("Collections", len(stats.get("metadata_value_counts", {})))

        # Search interface
        st.markdown("---")
        st.subheader("Search Vector Store")
        
        col1, col2 = st.columns(2)
        
        with col1:
            query = st.text_input("Search Query")
            limit = st.number_input("Number of Results", min_value=1, value=5)
            
        with col2:
            st.markdown("### Filters")
            metadata_keys = stats.get("sample_metadata_keys", [])
            selected_filters = {}
            
            for key in metadata_keys:
                value = st.text_input(f"Filter by {key}")
                if value:
                    selected_filters[key] = value
        
        if st.button("Search"):
            with st.spinner("Searching..."):
                try:
                    results = asyncio.run(self.context_db.search_context(
                        query=query,
                        limit=limit,
                        filters=selected_filters
                    ))
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"Result {i} (Score: {result['relevance']:.3f})"):
                            st.markdown(result['content'])
                            st.json(result['metadata'])
                except Exception as e:
                    st.error(f"Error during search: {str(e)}")

    def render_settings_view(self):
        """Render the context system settings view."""
        st.subheader("Context System Settings")

        # Vector store settings
        with st.expander("Vector Store Settings", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.number_input(
                    "Batch Size",
                    min_value=1,
                    value=self.context_db.vector_store.config.batch_size
                )
                st.number_input(
                    "Max Retries",
                    min_value=1,
                    value=self.context_db.vector_store.config.max_retries
                )
                
            with col2:
                st.number_input(
                    "Connection Timeout",
                    min_value=1,
                    value=self.context_db.vector_store.config.connection_timeout
                )
                st.number_input(
                    "Max Concurrent Requests",
                    min_value=1,
                    value=self.context_db.vector_store.config.max_concurrent_requests
                )

        # Knowledge base settings
        with st.expander("Knowledge Base Settings", expanded=False):
            st.text_input(
                "Base Path",
                value=self.knowledge_base.base_path
            )
            
            if st.button("Export Knowledge Base"):
                try:
                    export_path = self.knowledge_base.export_domain(
                        domain="all",
                        export_path="knowledge_export.json"
                    )
                    st.success(f"Knowledge base exported to: {export_path}")
                except Exception as e:
                    st.error(f"Error exporting knowledge base: {str(e)}")

        # System context settings
        with st.expander("System Context Settings", expanded=False):
            st.markdown("### Embedder Configuration")
            st.selectbox(
                "Embedder Provider",
                options=["openai", "cohere", "huggingface"]
            )
            
            st.markdown("### Cache Settings")
            st.number_input(
                "URL Cache TTL (seconds)",
                min_value=0,
                value=3600
            )