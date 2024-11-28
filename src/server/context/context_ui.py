import streamlit as st
import os
from typing import Optional, Dict, Any, List
import asyncio
from pathlib import Path
from datetime import datetime

from .context_management import ContextDatabase, CodeCatalog

class ContextManagerUI:
    """
    StreamLit UI component for managing and visualizing the context system.
    """
    def __init__(self):
        self.context_db = ContextDatabase()
        self.code_catalog = CodeCatalog()
        
    async def render_sidebar(self):
        """Render the context management controls in the sidebar."""
        with st.sidebar:
            st.subheader("Context Management")
            
            # Code Ingestion Section
            st.write("##### Code Ingestion")
            code_path = st.text_input("Code Directory Path", value="./")
            exclude_dirs = st.text_input(
                "Exclude Directories",
                value="venv,__pycache__,.git,node_modules"
            ).split(",")
            
            if st.button("Ingest Code"):
                with st.spinner("Ingesting code..."):
                    asyncio.run(self.context_db.ingest_code_directory(code_path, exclude_dirs))
                st.success("Code ingestion complete!")
            
            # Domain Knowledge Section
            st.write("##### Domain Knowledge")
            domain_content = st.text_area("Add Domain Knowledge")
            domain = st.text_input("Domain")
            subdomain = st.text_input("Subdomain")
            
            if st.button("Add Knowledge"):
                with st.spinner("Adding domain knowledge..."):
                    metadata = {
                        "domain": domain,
                        "subdomain": subdomain,
                        "timestamp": datetime.now().isoformat()
                    }
                    asyncio.run(self.context_db.add_domain_knowledge(domain_content, metadata))
                st.success("Domain knowledge added!")
                
            # Display Collection Stats
            stats = await self.context_db.vector_store.get_collection_stats()
            st.write("##### Collection Statistics")
            for collection, collection_stats in stats.items():
                st.write(f"{collection}: {collection_stats['total_chunks']} chunks")
    
    def render_main(self):
        """Render the main context visualization and search interface."""
        st.title("Context Management System")
        
        # Search Interface
        st.write("### Context Search")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            query = st.text_input("Search Query")
        
        with col2:
            collection = st.selectbox(
                "Collection",
                ["both", "code", "domain_knowledge"]
            )
            
        with col3:
            num_results = st.number_input("Results", min_value=1, value=5)
        
        # Add filters expander
        with st.expander("Search Filters"):
            metadata_filters = {}
            
            # Domain filter for domain knowledge
            if collection in ["both", "domain_knowledge"]:
                domain_filter = st.text_input("Domain Filter")
                if domain_filter:
                    metadata_filters["domain"] = domain_filter
            
            # File type filter for code
            if collection in ["both", "code"]:
                file_type = st.selectbox(
                    "File Type",
                    ["", ".py", ".md", ".yaml", ".yml", ".json"]
                )
                if file_type:
                    metadata_filters["file_type"] = file_type
        
        if st.button("Search"):
            with st.spinner("Searching..."):
                try:
                    if collection == "both":
                        results = asyncio.run(self.context_db.combine_context(
                            query=query,
                            num_results=num_results
                        ))
                        
                        # Display code context
                        st.write("#### Code Context")
                        for result in results["code_context"]:
                            self._render_result(result, "code")
                            
                        # Display domain context
                        st.write("#### Domain Knowledge")
                        for result in results["domain_context"]:
                            self._render_result(result, "domain")
                            
                    else:
                        results = asyncio.run(self.context_db.search_context(
                            query=query,
                            collection_name=collection,
                            num_results=num_results,
                            metadata_filter=metadata_filters if metadata_filters else None
                        ))
                        
                        for result in results:
                            self._render_result(result, collection)
                            
                except Exception as e:
                    st.error(f"Error during search: {str(e)}")
        
        # Code Catalog Browser
        st.write("### Code Catalog")
        if st.button("Update Catalog"):
            with st.spinner("Updating code catalog..."):
                asyncio.run(self.code_catalog.index_directory("./"))
                st.success("Catalog updated!")
        
        # Display catalog information in a tree view
        if self.code_catalog.file_index:
            selected_file = st.selectbox(
                "Select File",
                list(self.code_catalog.file_index.keys())
            )
            
            if selected_file:
                file_info = self.code_catalog.get_file_info(selected_file)
                if file_info:
                    st.write("##### File Information")
                    st.json(file_info)
    
    def _render_result(self, result: Dict[str, Any], result_type: str):
        """Render a single search result."""
        with st.expander(f"Score: {result['relevance_score']:.3f}"):
            # Display the content
            st.code(result['content'], language="python" if result_type == "code" else "text")
            
            # Display metadata
            st.write("Metadata:")
            st.json(result['metadata'])

def initialize_context_manager():
    """Initialize the context manager in the Streamlit session state."""
    if 'context_manager' not in st.session_state:
        st.session_state.context_manager = ContextManagerUI()

def render_context_manager():
    """Render the context manager UI."""
    initialize_context_manager()
    manager = st.session_state.context_manager
    
    # Render the UI components
    manager.render_sidebar()
    manager.render_main()