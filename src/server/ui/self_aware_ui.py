"""
Streamlit UI for the Cerebrum System Core.

This module provides a Streamlit-based user interface for interacting with
the Cerebrum System Core, allowing users to execute commands, search
the codebase, and view system context.
"""

import os
import json
import asyncio
import streamlit as st
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.server.self_aware_core import CerebrumSystemCore

# Helper function to run async functions in Streamlit
def run_async(func, *args, **kwargs):
    """Run an async function from Streamlit."""
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(func(*args, **kwargs))
    loop.close()
    return result

class CerebrumSystemUI:
    """
    Streamlit UI for the Cerebrum System Core.
    
    This class provides a user interface for interacting with the Cerebrum
    System Core, allowing users to execute commands, search the codebase,
    and view system context.
    """
    
    def __init__(self):
        """Initialize the Cerebrum System UI."""
        self._initialize_session_state()
        self._initialize_core()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'core' not in st.session_state:
            st.session_state.core = None
        if 'command_history' not in st.session_state:
            st.session_state.command_history = []
        if 'search_history' not in st.session_state:
            st.session_state.search_history = []
        if 'pending_approvals' not in st.session_state:
            st.session_state.pending_approvals = []
        if 'codebase_stats' not in st.session_state:
            st.session_state.codebase_stats = {}
        if 'context' not in st.session_state:
            st.session_state.context = ""
    
    def _initialize_core(self):
        """Initialize the Cerebrum System Core."""
        if st.session_state.core is None:
            # Load configuration
            config_path = os.environ.get("CEREBRUM_CONFIG", "config/cerebrum_system_config.json")
            config = {}
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            # Initialize core
            st.session_state.core = CerebrumSystemCore(
                base_path=config.get("base_path", "persistent_state/cerebrum_system"),
                codebase_root=config.get("codebase_root", "."),
                config=config
            )
    
    def render_sidebar(self):
        """Render the sidebar with configuration and status information."""
        st.sidebar.title("Cerebrum System Core")
        
        # Component status
        st.sidebar.header("Component Status")
        st.sidebar.success("✅ Context Manager: Active")
        st.sidebar.success("✅ Vector Store: Active")
        st.sidebar.success("✅ Terminal Executor: Active")
        
        # Codebase stats
        st.sidebar.header("Codebase Statistics")
        if st.sidebar.button("Refresh Stats"):
            stats = run_async(st.session_state.core.get_codebase_stats)
            st.session_state.codebase_stats = stats
        
        if st.session_state.codebase_stats:
            st.sidebar.metric("Indexed Files", st.session_state.codebase_stats.get("total_files", 0))
            st.sidebar.metric("Total Lines", st.session_state.codebase_stats.get("total_lines", 0))
            st.sidebar.text(f"Last Updated: {st.session_state.codebase_stats.get('last_updated', 'Never')}")
        
        # Pending approvals
        st.sidebar.header("Pending Approvals")
        if st.sidebar.button("Check Approvals"):
            approvals = run_async(st.session_state.core.get_pending_approvals)
            st.session_state.pending_approvals = approvals
        
        if st.session_state.pending_approvals:
            st.sidebar.warning(f"{len(st.session_state.pending_approvals)} commands pending approval")
        else:
            st.sidebar.info("No pending approvals")
    
    def render_terminal_section(self):
        """Render the terminal command execution section."""
        st.header("Terminal Command Execution")
        
        # Command input
        command = st.text_input("Enter command:")
        col1, col2 = st.columns(2)
        with col1:
            working_dir = st.text_input("Working directory:", value=".")
        with col2:
            timeout = st.number_input("Timeout (seconds):", value=30, min_value=1, max_value=300)
        
        requires_approval = st.checkbox("Requires approval", value=True)
        
        if st.button("Execute") and command:
            with st.spinner("Executing command..."):
                result = run_async(
                    st.session_state.core.execute_command,
                    command=command,
                    working_directory=working_dir,
                    timeout=timeout,
                    requires_approval=requires_approval
                )
                
                if isinstance(result, str):
                    # Command requires approval
                    st.info(f"Command submitted for approval. Approval ID: {result}")
                    st.session_state.command_history.append({
                        "command": command,
                        "status": "pending",
                        "approval_id": result,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    # Command executed
                    if result.success:
                        st.success("Command executed successfully")
                    else:
                        st.error("Command execution failed")
                    
                    st.code(result.stdout if result.success else result.stderr)
                    
                    st.session_state.command_history.append({
                        "command": command,
                        "status": "executed",
                        "success": result.success,
                        "output": result.stdout if result.success else result.stderr,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Command history
        if st.session_state.command_history:
            st.subheader("Command History")
            for i, cmd in enumerate(reversed(st.session_state.command_history)):
                if cmd["status"] == "pending":
                    with st.expander(f"🕒 {cmd['command']} (Pending approval)"):
                        st.text(f"Approval ID: {cmd['approval_id']}")
                        st.text(f"Submitted: {cmd['timestamp']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Approve", key=f"approve_{i}"):
                                with st.spinner("Executing approved command..."):
                                    result = run_async(
                                        st.session_state.core.execute_approved_command,
                                        approval_id=cmd["approval_id"]
                                    )
                                    
                                    if result.success:
                                        st.success("Command executed successfully")
                                    else:
                                        st.error("Command execution failed")
                                    
                                    st.code(result.stdout if result.success else result.stderr)
                                    
                                    # Update command history
                                    cmd["status"] = "executed"
                                    cmd["success"] = result.success
                                    cmd["output"] = result.stdout if result.success else result.stderr
                        
                        with col2:
                            if st.button("Reject", key=f"reject_{i}"):
                                rejected = run_async(
                                    st.session_state.core.reject_command,
                                    approval_id=cmd["approval_id"]
                                )
                                
                                if rejected:
                                    st.info("Command rejected")
                                    cmd["status"] = "rejected"
                                else:
                                    st.error("Failed to reject command")
                else:
                    status = "✅" if cmd.get("success", False) else "❌"
                    with st.expander(f"{status} {cmd['command']}"):
                        st.text(f"Executed: {cmd['timestamp']}")
                        st.code(cmd.get("output", "No output"))
    
    def render_search_section(self):
        """Render the code search section."""
        st.header("Code Search")
        
        # Search input
        query = st.text_input("Search query:")
        top_k = st.slider("Number of results:", min_value=1, max_value=20, value=5)
        
        if st.button("Search") and query:
            with st.spinner("Searching codebase..."):
                results = run_async(
                    st.session_state.core.search_code,
                    query=query,
                    top_k=top_k
                )
                
                st.session_state.search_history.append({
                    "query": query,
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Search results
        if st.session_state.search_history:
            st.subheader("Search Results")
            for i, search in enumerate(reversed(st.session_state.search_history)):
                with st.expander(f"Query: {search['query']} ({len(search['results'])} results)"):
                    st.text(f"Searched: {search['timestamp']}")
                    
                    for j, result in enumerate(search['results']):
                        st.markdown(f"**Result {j+1}**: {result.file_path} (lines {result.start_line}-{result.end_line})")
                        st.markdown(f"Relevance: {result.relevance_score:.4f}")
                        st.code(result.content, language=result.language)
                        
                        if st.button("View File", key=f"view_{i}_{j}"):
                            file_content = run_async(
                                st.session_state.core.get_file_content,
                                file_path=result.file_path
                            )
                            
                            if file_content:
                                st.code(file_content, language=result.language)
                            else:
                                st.error("Failed to load file content")
    
    def render_context_section(self):
        """Render the context section."""
        st.header("System Context")
        
        col1, col2 = st.columns(2)
        with col1:
            max_tokens = st.number_input("Max tokens:", value=1000, min_value=100, max_value=8192)
        with col2:
            include_metadata = st.checkbox("Include metadata", value=False)
        
        if st.button("Refresh Context"):
            with st.spinner("Loading context..."):
                context = run_async(
                    st.session_state.core.get_context,
                    max_tokens=max_tokens,
                    include_metadata=include_metadata
                )
                
                st.session_state.context = context
        
        if st.session_state.context:
            if isinstance(st.session_state.context, str):
                st.text_area("Current Context:", value=st.session_state.context, height=400)
            else:
                st.json(st.session_state.context)
    
    def render_indexing_section(self):
        """Render the codebase indexing section."""
        st.header("Codebase Indexing")
        
        incremental = st.checkbox("Incremental indexing", value=True)
        
        if st.button("Index Codebase"):
            with st.spinner("Indexing codebase..."):
                result = run_async(
                    st.session_state.core.index_codebase,
                    incremental=incremental
                )
                
                st.success(f"Indexed {result.get('indexed_files', 0)} files")
                st.session_state.codebase_stats = run_async(st.session_state.core.get_codebase_stats)
    
    def render(self):
        """Render the complete UI."""
        st.set_page_config(
            page_title="Cerebrum System Core",
            page_icon="🧠",
            layout="wide"
        )
        
        self.render_sidebar()
        
        st.title("Cerebrum System Core")
        st.markdown("""
        This interface provides human interaction with the Cerebrum System Core.
        Use the tools below to interact with the system's capabilities.
        """)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Terminal Commands", 
            "Code Search", 
            "Context Management",
            "Codebase Indexing"
        ])
        
        with tab1:
            self.render_terminal_section()
        
        with tab2:
            self.render_search_section()
        
        with tab3:
            self.render_context_section()
        
        with tab4:
            self.render_indexing_section()

def main():
    """Main entry point for the Streamlit app."""
    ui = CerebrumSystemUI()
    ui.render()

if __name__ == "__main__":
    main() 