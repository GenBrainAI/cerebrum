import streamlit as st
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import PyPDF2
import docx
import io
import time
import tempfile
from uuid import uuid4, UUID
import asyncio

from src.server.context.context_database import ContextDatabase
from src.server.context.code_catalog import CodeCatalog
from src.server.context.knowledge_base import KnowledgeBase
from server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.context.context_provider import ContextProvider
from src.server.context.vector_store import VectorStore

class ContextManagerUI:
    """Enhanced UI component for managing and visualizing the context system."""
    
    def __init__(self):
        """Initialize context management UI components."""
        # Initialize session state if needed
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            
        # Initialize components
        self.context_provider = ContextProvider()
        self.vector_store = VectorStore()
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase()
        
        # Initialize context provider
        asyncio.run(self.context_provider.initialize())
        
        # Load contexts from persistence model
        try:
            persistence_model = PersistenceModelFactory.persistence_model()
            # Sync task contexts
            tasks = persistence_model.tasks.list()
            for task in tasks:
                self.context_provider.sync_task_contexts(task.id, task)
            
            # Sync manager contexts
            managers = persistence_model.tasksmanagers.list()
            for manager in managers:
                self.context_provider.sync_manager_contexts(manager.id, manager)
            
        except Exception as e:
            print(f"Error loading contexts: {e}")
        
        # Initialize context analytics
        try:
            from src.server.context.context_analytics import ContextAnalytics
            self.context_analytics = ContextAnalytics()
        except ImportError:
            self.context_analytics = None
        
        # Initialize or load code catalog state
        if 'code_catalog_state' not in st.session_state:
            st.session_state.code_catalog_state = self.code_catalog.get_state()
        else:
            self.code_catalog.load_state(st.session_state.code_catalog_state)
        
        # Initialize memory tracking
        if 'last_memory_update' not in st.session_state:
            st.session_state.last_memory_update = 0
        if 'cached_memory_usage' not in st.session_state:
            st.session_state.cached_memory_usage = 0
        
        # Initialize dialog state
        if 'show_dialog_for_task' not in st.session_state:
            st.session_state.show_dialog_for_task = None
        
    @property
    def persistence_model(self):
        """Get persistence model instance when needed"""
        return PersistenceModelFactory.persistence_model()
    
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
        
        # Initialize layout state if not exists
        if 'layout_style' not in st.session_state:
            st.session_state.layout_style = 'horizontal'
        
        nav_cols = st.columns(5)
        
        with nav_cols[0]:
            if st.button("Task Contexts", 
                        key="nav_task_contexts",
                        use_container_width=True):
                st.session_state.context_view = "task_contexts"
                st.session_state.layout_style = 'horizontal'
                
        with nav_cols[1]:
            if st.button("📚 Knowledge Base", 
                        key="nav_knowledge",
                        use_container_width=True):
                st.session_state.context_view = "knowledge"
                st.session_state.layout_style = 'horizontal'
                
        with nav_cols[2]:
            if st.button("🔍 Code Analysis", 
                        key="nav_code",
                        use_container_width=True):
                st.session_state.context_view = "code"
                st.session_state.layout_style = 'horizontal'
                
        with nav_cols[3]:
            if st.button("🔄 Vector Store", 
                        key="nav_vector",
                        use_container_width=True):
                st.session_state.context_view = "vector"
                st.session_state.layout_style = 'horizontal'
                
        with nav_cols[4]:
            if st.button("⚙️ Settings", 
                        key="nav_settings",
                        use_container_width=True):
                st.session_state.context_view = "settings"
                st.session_state.layout_style = 'horizontal'
                
        st.markdown("---")
    
    async def render_status_bar(self):
        """Render a status bar showing system metrics."""
        stats = self.get_statistics()
        
        try:
            vector_stats = await self.vector_store.get_stats()
        except Exception as e:
            st.error(f"Error getting vector store stats: {str(e)}")
            vector_stats = {}
        
        status_cols = st.columns(4)
        with status_cols[0]:
            st.metric("Indexed Files", vector_stats.get('total_vectors', 0))
        with status_cols[1]:
            st.metric("Vector Indices", vector_stats.get('indices_count', 0))
        with status_cols[2]:
            st.metric("Storage Size", f"{vector_stats.get('storage_size', 0):.2f} MB")
        with status_cols[3]:
            st.metric("Active Contexts", len(self.context_provider.task_context_manager.task_contexts))
                
    async def render_main_view(self):
        """Render the main content based on selected view."""
        if "context_view" not in st.session_state:
            st.session_state.context_view = "task_contexts"
            
        view = st.session_state.context_view
        
        if view == "task_contexts":
            await self.render_task_context_associations()
        elif view == "knowledge":
            await self.render_knowledge_view()
        elif view == "code":
            await self.render_code_view()
        elif view == "vector":
            await self.render_vector_view()
        elif view == "settings":
            self.render_settings_view()

    async def render(self):
        """Main render method for the context manager UI."""
        self.render_header()
        self.render_navigation()
        await self.render_status_bar()
        
        # Remove persistent state UI from main render
        # Only show it in settings view via render_main_view
        
        # Use the async render_main_view
        try:
            await self.render_main_view()
        except Exception as e:
            st.error(f"Error in main view: {str(e)}")

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
        import os
        import json
        from datetime import datetime
        
        # Custom JSON encoder to handle datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        # Update disk usage only every 5 seconds
        current_time = time.time()
        if current_time - st.session_state.last_memory_update > 5:
            try:
                # Knowledge base size
                kb_path = Path(self.knowledge_base.base_path)
                kb_size = sum(f.stat().st_size for f in kb_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                
                # Code catalog size
                cc_path = Path("persistent_state/context/code_catalog")
                cc_size = sum(f.stat().st_size for f in cc_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                
                # Vector store size
                vs_path = Path("persistent_state/context/vector_store")
                vs_size = sum(f.stat().st_size for f in vs_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                
                # Debug prints
                # st.sidebar.write("Disk Usage (MB):")
                # st.sidebar.write(f"Knowledge Base: {int(kb_size)}")
                # st.sidebar.write(f"Code Catalog: {int(cc_size)}")
                # st.sidebar.write(f"Vector Store: {int(vs_size)}")
                
                total_size = int(kb_size + cc_size + vs_size)
                
            except Exception as e:
                st.sidebar.write(f"Error calculating sizes: {str(e)}")
                total_size = 0
                
            st.session_state.cached_memory_usage = total_size
            st.session_state.last_memory_update = current_time
        
        stats = {
            "total_files": len(self.code_catalog.file_index),
            "total_entries": len(self.knowledge_base.knowledge_index.get("entries", {})),
            "total_chunks": 0,  # To be implemented with vector store
            "memory_usage": st.session_state.cached_memory_usage
        }
        
        return stats
    
    async def render_knowledge_view(self):
        """Render the knowledge base management view."""
        # Initialize session state for knowledge view
        if 'knowledge_filter_type' not in st.session_state:
            st.session_state.knowledge_filter_type = "All"
        if 'selected_filter_task' not in st.session_state:
            st.session_state.selected_filter_task = None
        if 'selected_filter_tm' not in st.session_state:
            st.session_state.selected_filter_tm = None

        st.subheader("Knowledge Base Management")

        # Get available tasks and managers first
        persistence_model = PersistenceModelFactory.persistence_model()
        tasks = persistence_model.tasks.list()
        tasksmanagers = persistence_model.tasksmanagers.list()
        
        # Create options dictionaries
        task_options = {f"{t.name} ({t.id})": t.id for t in tasks} if tasks else {}
        tm_options = {f"{tm.name} ({tm.id})": tm.id for tm in tasksmanagers} if tasksmanagers else {}

        # Add knowledge section
        st.subheader("Add Knowledge Entry")
        
        col1, col2 = st.columns(2)
        
        with col1:
            domain = st.text_input("Domain")
            content = st.text_area("Content")
            description = st.text_input("Description (optional)")
            
        with col2:
            tags = st.text_input("Tags (comma-separated)")
            source_type = st.selectbox(
                "Source Type",
                ["documentation", "code", "research", "tutorial", "other"]
            )

        # Task Association Section
        st.subheader("Task Association")
        associate_type = st.radio(
            "Associate with:",
            ["None", "Task", "Tasks Manager"]
        )

        task_id = None
        tasksmanager_id = None

        if associate_type == "Task":
            if task_options:
                selected_task = st.selectbox(
                    "Select Task",
                    options=list(task_options.keys()),
                    key="add_task_select"
                )
                if selected_task:
                    task_id = task_options[selected_task]
            else:
                st.info("No tasks available")

        elif associate_type == "Tasks Manager":
            if tm_options:
                selected_tm = st.selectbox(
                    "Select Tasks Manager",
                    options=list(tm_options.keys()),
                    key="add_tm_select"
                )
                if selected_tm:
                    tasksmanager_id = tm_options[selected_tm]
            else:
                st.info("No task managers available")

        # File upload option
        uploaded_file = st.file_uploader(
            "Upload File (optional)",
            type=["txt", "md", "py", "json", "yaml", "pdf", "doc", "docx"]
        )
                
        # Initialize meta_dict outside the upload block
        meta_dict = {}
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                    content = "\n".join(page.extract_text() for page in pdf_reader.pages)
                elif uploaded_file.name.endswith(('.doc', '.docx')):
                    doc = docx.Document(io.BytesIO(uploaded_file.read()))
                    content = "\n".join(paragraph.text for paragraph in doc.paragraphs)
                else:
                    content = uploaded_file.getvalue().decode()
                
                # Create metadata with filename
                tags_list = [t.strip() for t in tags.split(",") if t.strip()]
                meta_dict = {
                    "description": description or uploaded_file.name,
                    "source_type": source_type,
                    "tags": tags_list,
                    "added_at": datetime.now().isoformat(),
                    "filename": uploaded_file.name
                }
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                
        if st.button("Add Knowledge Entry"):
            try:
                tags_list = [t.strip() for t in tags.split(",") if t.strip()]
                
                # Update meta_dict instead of creating new one
                if not meta_dict:  # Only create new if not already set by file upload
                    meta_dict = {
                        "description": description,
                        "source_type": source_type,
                        "tags": tags_list,
                        "added_at": datetime.now().isoformat()
                    }
                
                # Add to knowledge base with task association
                entry_id = await self.knowledge_base.add_knowledge_with_task(
                    content=content,
                    domain=domain,
                    metadata=meta_dict,
                    task_id=task_id,
                    tasksmanager_id=tasksmanager_id,
                    tags=tags_list
                )
                
                # Also add to vector store for semantic search
                embeddings = self.context_db.vector_store._safe_embed([content])
                await self.context_db.vector_store.add_items(
                    embeddings=embeddings,
                    metadatas=[{
                        **meta_dict,
                        "task_id": task_id,
                        "tasksmanager_id": tasksmanager_id
                    }],
                    contents=[content]
                )
                
                st.success(f"Knowledge entry added successfully!")
            except Exception as e:
                st.error(f"Error adding knowledge: {str(e)}")

        # Knowledge browse section
        st.markdown("---")
        st.subheader("Browse Knowledge")
        
        def on_filter_change():
            """Callback for filter type change"""
            # Reset selected filters when type changes
            st.session_state.selected_filter_task = None
            st.session_state.selected_filter_tm = None
        
        # Add task/tasksmanager filter
        filter_by = st.radio(
            "Filter by:",
            ["All", "Task", "Tasks Manager", "Domain & Tags"],
            key="knowledge_filter_type",
            on_change=on_filter_change
        )

        entries = []
        if filter_by == "Task":
            if task_options:
                selected_task = st.selectbox(
                    "Select Task",
                    options=[""] + list(task_options.keys()),
                    key="selected_filter_task"
                )
                if selected_task:
                    entries = self.knowledge_base.get_task_knowledge(task_options[selected_task])
            else:
                st.info("No tasks available to filter by")
        elif filter_by == "Tasks Manager":
            if tm_options:
                selected_tm = st.selectbox(
                    "Select Tasks Manager",
                    options=[""] + list(tm_options.keys()),
                    key="selected_filter_tm"
                )
                if selected_tm:
                    entries = self.knowledge_base.get_tasksmanager_knowledge(tm_options[selected_tm])
            else:
                st.info("No task managers available to filter by")
        else:
            # Existing domain and tag filtering
            col1, col2 = st.columns(2)
            with col1:
                selected_domain = st.selectbox(
                    "Filter by Domain",
                    options=["All"] + list(self.knowledge_base.knowledge_index.get("domains", {}).keys()),
                    key="selected_domain"
                )
            with col2:
                selected_tags = st.multiselect(
                    "Filter by Tags",
                    options=list(self.knowledge_base.knowledge_index.get("tags", {}).keys()),
                    key="selected_tags"
                )
            
            entries = self.knowledge_base.get_knowledge(
                domain=None if selected_domain == "All" else selected_domain,
                tags=selected_tags if selected_tags else None
            )

        # Display entries
        for entry in entries:
            entry_id = entry.get('id')
            metadata = entry.get('metadata', {})
            
            # Get file name and description
            file_name = metadata.get('filename', '')
            description = metadata.get('description', 'No description')
            display_title = file_name or description  # Use description if filename is empty
            
            with st.expander(f"{metadata.get('source_type', 'Unknown')} - {display_title}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(entry['content'])
                    st.write("Tags:", ", ".join(metadata.get('tags', [])))
                    st.write("Added:", metadata.get('added_at', 'Unknown'))
                    st.write("Domain:", entry.get('domain', 'Unknown'))
                
                with col2:
                    st.empty()  # Add some spacing
                    if st.button("🗑️", key=f"delete_{entry_id}"):
                        try:
                            await self.knowledge_base.delete_knowledge(entry_id)
                            st.success("Entry deleted!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

    async def render_code_view(self):
        """Render the code analysis view."""
        st.subheader("Code Analysis")

        # Code source selection
        source_type = st.radio(
            "Repository Source",
            ["Local Directory", "GitHub Repository"]
        )

        # Code ingestion section
        st.subheader("Add Repository")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if source_type == "Local Directory":
                repo_path = st.text_input("Local Repository Path")
                # Validate that local path is not a GitHub URL
                if repo_path and ('github.com' in repo_path or 'gitlab.com' in repo_path):
                    st.error("For GitHub/GitLab repositories, please select 'GitHub Repository' option above")
                    return
                
                uploaded_file = st.file_uploader(
                    "Or upload directory",
                    type=["zip"],
                    accept_multiple_files=False
                )

                exclude_dirs = st.text_input(
                    "Exclude Directories",
                    value="venv,__pycache__,.git,node_modules,build,dist"
                ).split(",")
                
            else:
                repo_url = st.text_input("GitHub Repository URL")
                branch = st.text_input("Branch (optional)", value="main")
                
        with col2:
            st.markdown("### Analysis Options")
            analyze_deps = st.checkbox("Analyze Dependencies", value=True)
            parse_docs = st.checkbox("Parse Documentation", value=True)
            deep_scan = st.checkbox("Deep Scan", value=False)
            
            if source_type == "GitHub Repository":
                use_auth = st.checkbox("Use Authentication")
                if use_auth:
                    github_token = st.text_input("GitHub Token", type="password")
        
        if st.button("Analyze Repository"):
            with st.spinner("Analyzing code..."):
                try:
                    if source_type == "Local Directory":
                        if uploaded_file:
                            # Get repository name from zip file (remove .zip extension)
                            repo_name = Path(uploaded_file.name).stem
                            
                            # Create a temporary directory for the zip contents
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # Save the uploaded file
                                zip_path = Path(temp_dir) / uploaded_file.name
                                with open(zip_path, 'wb') as f:
                                    f.write(uploaded_file.getvalue())
                                
                                # Extract the zip file
                                import zipfile
                                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(temp_dir)
                                
                                # Get the root directory from the zip
                                extracted_contents = list(Path(temp_dir).glob('*'))
                                if len(extracted_contents) == 1 and extracted_contents[0].is_dir():
                                    analysis_path = str(extracted_contents[0])
                                else:
                                    analysis_path = temp_dir
                                
                                # Analyze the extracted contents
                                stats = await self.code_catalog.index_directory(
                                    directory_path=analysis_path,
                                    exclude_dirs=exclude_dirs,
                                    analyze_deps=analyze_deps,
                                    parse_docs=parse_docs,
                                    deep_scan=deep_scan,
                                    repo_name=repo_name
                                )
                        elif repo_path:
                            stats = await self.code_catalog.index_directory(
                                directory_path=repo_path,
                                exclude_dirs=exclude_dirs,
                                analyze_deps=analyze_deps,
                                parse_docs=parse_docs,
                                deep_scan=deep_scan
                            )
                        else:
                            st.error("Please provide either a local path or upload a zip file")
                            return
                    else:  # GitHub Repository
                        stats = await self.code_catalog.index_github_repo(
                            repo_url=repo_url,
                            branch=branch,
                            github_token=github_token if use_auth else None,
                            exclude_dirs=exclude_dirs,
                            analyze_deps=analyze_deps,
                            parse_docs=parse_docs,
                            deep_scan=deep_scan
                        )
                    
                    # Save state to session
                    st.session_state.code_catalog_state = self.code_catalog.get_state()
                    
                    st.success("Repository analyzed successfully!")
                    st.json(stats)
                except Exception as e:
                    st.error(f"Error analyzing repository: {str(e)}")

        # Repository browser section
        await self._render_repository_browser()

    async def _render_repository_browser(self):
        """Render the repository browser section."""
        st.markdown("---")
        st.subheader("Browse Repositories")
                
        if self.code_catalog.file_index:
            # Initialize selected_repo in session state if not present
            if 'selected_repo' not in st.session_state:
                st.session_state.selected_repo = "All"

            # Get unique repository names
            repos = list(set(path.split('/')[0] for path in self.code_catalog.file_index.keys()))
            
            # Add repository filter if multiple repos
            if len(repos) > 1:
                st.session_state.selected_repo = st.selectbox(
                    "Select Repository",
                    options=["All"] + repos
                )
            
            # File tree view
            st.markdown("### File Explorer")
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Create tree structure
                file_tree = {}
                for path in self.code_catalog.file_index.keys():
                    if st.session_state.selected_repo != "All" and not path.startswith(st.session_state.selected_repo):
                        continue
                    parts = path.split('/')
                    current = file_tree
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = path
                
                # Display tree
                selected_file = self._render_file_tree(file_tree)
            
            with col2:
                if selected_file and selected_file in self.code_catalog.file_index:
                    file_info = self.code_catalog.get_file_info(selected_file)
                    if file_info:
                        # File content and info tabs
                        tab1, tab2 = st.tabs(["Content", "Info"])
                        
                        with tab1:
                            st.code(file_info.get('content', ''), 
                                  language=self._get_language(selected_file))
                            
                        with tab2:
                            st.markdown("### File Information")
                            st.write(f"Size: {file_info['size']} bytes")
                            st.write(f"Last Modified: {file_info['last_modified']}")
                            
                            if file_info.get('imports'):
                                st.markdown("### Dependencies")
                                for dep in file_info['imports']:
                                    st.write(f"- {dep}")
                            
                            if file_info.get('documentation'):
                                st.markdown("### Documentation")
                                st.markdown(file_info['documentation'])
                            
                            # Add delete button
                            if st.button("🗑️", key=f"delete_file_{selected_file}"):
                                try:
                                    self.code_catalog.remove_file(selected_file)
                                    st.success("File removed from catalog!")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

    def _render_file_tree(self, tree, prefix=""):
        """Render repositories with delete buttons and expandable file content."""
        selected = None
        
        # Get top-level repositories
        repositories = {k: v for k, v in tree.items() if isinstance(v, dict)}
        
        for repo_name, repo_files in repositories.items():
            # Create columns for repo name and delete button
            col1, col2 = st.columns([20, 1])
            
            with col1:
                # Create expander for repository
                with st.expander(f" {repo_name}"):
                    # Function to recursively display files
                    def display_files(files, indent=""):
                        for name, value in sorted(files.items()):
                            if isinstance(value, dict):
                                # Directory
                                st.markdown(f"{indent}📁 **{name}**")
                                display_files(value, indent + "  ")
                            else:
                                # File - make it clickable
                                if st.button(f"{indent}📄 {name}", key=f"file_{value}"):
                                    selected = value
                
                    # Display files in repository
                    display_files(repo_files)
            
            with col2:
                # Delete button for repository
                if st.button("🗑️", key=f"delete_repo_{repo_name}", help=f"Delete {repo_name}"):
                    if st.warning(f"Delete repository {repo_name}?"):
                        try:
                            # Delete repository logic here
                            if self.code_catalog.remove_repository(repo_name):
                                # Update session state with new catalog state
                                st.session_state.code_catalog_state = self.code_catalog.get_state()
                                st.success(f"Repository {repo_name} deleted!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"Failed to delete repository {repo_name}")
                        except Exception as e:
                            st.error(f"Error deleting repository: {str(e)}")
        
        return selected

    def _get_language(self, filename):
        """Get language for syntax highlighting based on file extension."""
        ext = filename.split('.')[-1].lower()
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'bash',
            'bash': 'bash',
            'dockerfile': 'dockerfile',
        }
        return language_map.get(ext, 'text')

    async def render_vector_view(self):
        """Render the vector store management view."""
        st.subheader("Vector Store Management")

        # Force refresh vector store state
        try:
            self.vector_store._reload_indices()
        except Exception as e:
            st.error(f"Error refreshing vector store state: {str(e)}")

        # Index management section
        st.subheader("Manage Indices")
        
        # Create new index
        with st.expander("Create New Index", expanded=False):
            new_index_name = st.text_input("Index Name")
            description = st.text_area("Description")
            if st.button("Create Index", use_container_width=True):
                if new_index_name:
                    try:
                        index_name = self.vector_store.create_index(
                            name=new_index_name,
                            description=description
                        )
                        st.success(f"Created index: {index_name}")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating index: {str(e)}")
                else:
                    st.warning("Please provide an index name")

        # File ingestion section
        st.subheader("Add Files to Vector Store")
        
        # Index selection
        indices = await self.vector_store.list_indices()
        if not indices:
            st.info("No indices available. Create an index first.")
            return
        
        selected_index = st.selectbox(
            "Select Index",
            options=[""] + [idx["name"] for idx in indices],
            format_func=lambda x: x.replace("vs_", "") if x else "Select an index..."
        )
        
        if not selected_index:
            st.warning("Please select an index to add files")
            return

        # Source selection
        source_type = st.radio(
            "Source Type",
            ["Local Files", "Directory"],
            horizontal=True
        )

        # File upload section
        if source_type == "Local Files":
            uploaded_files = st.file_uploader(
                "Upload Files",
                type=["txt", "md", "py", "json", "yaml", "pdf", "doc", "docx"],
                accept_multiple_files=True
            )

            if uploaded_files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{len(uploaded_files)} file(s) ready to process")
                with col2:
                    if st.button("Add to Index", use_container_width=True):
                        if not selected_index:
                            st.error("Please select an index first")
                        else:
                            # Create a progress bar
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for uploaded_file in uploaded_files:
                                try:
                                    def update_progress(message: str, current: int, total: int):
                                        if total > 0:
                                            progress_bar.progress(current / total)
                                        status_text.text(message)
                                    
                                    metadata = {
                                        "original_name": uploaded_file.name,
                                        "file_type": uploaded_file.type,
                                        "size": uploaded_file.size,
                                        "index": selected_index,
                                        "added_at": datetime.now().isoformat(),
                                        "file_id": str(uuid4()),
                                        "is_root": True
                                    }
                                    
                                    chunk_ids = await self.vector_store.add_file_to_index(
                                        index_name=selected_index,
                                        file_path_or_obj=uploaded_file,
                                        metadata=metadata,
                                        progress_callback=update_progress
                                    )
                                    
                                    st.success(f"Added {uploaded_file.name} to {selected_index} ({len(chunk_ids)} chunks)")
                                except Exception as e:
                                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                            
                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()
                            
                            time.sleep(0.5)
                            st.rerun()
        else:
            # Directory processing
            dir_path = st.text_input("Directory Path")
            if dir_path and selected_index:
                if st.button("Process Directory", use_container_width=True):
                    try:
                        processed = await self.vector_store.process_directory(
                            index_name=selected_index,
                            directory_path=dir_path
                        )
                        st.success(f"Processed {processed} files from directory")
                    except Exception as e:
                        st.error(f"Error processing directory: {str(e)}")

        # List and manage existing files
        st.markdown("---")
        st.subheader("Vector Store Contents")
        
        try:
            # Show indices and their contents
            for idx in indices:
                # Get unique files (root items) in this index
                files = await self.vector_store.get_index_contents(idx['name'])
                
                # Add debug logging
                st.write(f"Debug - Processing index: {idx['name']}")
                st.write(f"Debug - Number of raw files: {len(files)}")
                
                # Deduplicate files based on file_id
                unique_files = {}
                for file_info in files:
                    metadata = file_info.get('metadata', {})
                    file_id = metadata.get('file_id')
                    if file_id:
                        # Keep the most recent version if duplicate
                        if file_id not in unique_files or (
                            metadata.get('added_at', '') > unique_files[file_id].get('metadata', {}).get('added_at', '')
                        ):
                            unique_files[file_id] = file_info
                
                # Convert back to list and sort by added_at
                files = sorted(
                    unique_files.values(),
                    key=lambda x: x.get('metadata', {}).get('added_at', ''),
                    reverse=True
                )
                
                st.write(f"Debug - Number of unique files: {len(files)}")
                
                # Display index with file count
                with st.expander(f"📁 {idx['name'].replace('vs_', '')} ({len(files)} files)"):
                    st.write(f"Description: {idx.get('description', 'No description')}")
                    
                    if files:
                        # Keep track of used keys to ensure uniqueness
                        used_keys = set()
                        
                        for file_idx, file_info in enumerate(files):
                            metadata = file_info.get('metadata', {})
                            chunks = metadata.get('chunks', [])
                            file_id = metadata.get('file_id', f'unknown_{file_idx}')
                            
                            # Debug logging for file info
                            st.write(f"Debug - Processing file {file_idx}:")
                            st.write(f"  Name: {metadata.get('original_name', 'Unnamed')}")
                            st.write(f"  ID: {file_id}")
                            st.write(f"  Added at: {metadata.get('added_at', 'Unknown')}")
                            
                            col1, col2 = st.columns([20, 1])
                            with col1:
                                st.write(f"📄 {metadata.get('original_name', 'Unnamed')}")
                                st.write(f"Added: {metadata.get('added_at', 'Unknown')}")
                                st.write(f"Size: {metadata.get('size', 'Unknown')} bytes")
                                st.write(f"Chunks: {metadata.get('total_chunks', len(chunks))}")
                            with col2:
                                # Create a unique key for each delete button
                                base_key = f"delete_{idx['name']}_{file_id}"
                                delete_key = base_key
                                counter = 0
                                
                                # Ensure key uniqueness
                                while delete_key in used_keys:
                                    counter += 1
                                    delete_key = f"{base_key}_{counter}"
                                
                                used_keys.add(delete_key)
                                st.write(f"Debug - Delete button key: {delete_key}")
                                
                                if st.button("🗑️", key=delete_key, 
                                           help=f"Delete {metadata.get('original_name', 'file')}"):
                                    try:
                                        await self.vector_store.delete_file_from_index(
                                            index_name=idx['name'],
                                            file_id=file_id
                                        )
                                        st.success("File deleted!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                    else:
                        st.info("No files in this index")
                    
                    # Create a unique key for the index delete button using counter
                    base_index_key = f"delete_index_{idx['name']}"
                    index_delete_key = base_index_key
                    counter = 0
                    
                    while index_delete_key in used_keys:
                        counter += 1
                        index_delete_key = f"{base_index_key}_{counter}"
                    
                    used_keys.add(index_delete_key)
                    st.write(f"Debug - Index delete button key: {index_delete_key}")
                    
                    if st.button("Delete Index", key=index_delete_key, 
                               help=f"Delete entire index {idx['name']}"):
                        try:
                            await self.vector_store.delete_index(idx['name'])
                            st.success("Index deleted!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        except Exception as e:
            st.error(f"Error listing vector store contents: {str(e)}")
            # Add stack trace for debugging
            import traceback
            st.error(f"Stack trace: {traceback.format_exc()}")

    async def render_task_context_associations(self):
        """Render the task context associations view."""
        st.subheader("Task Context Associations")

        # Get all tasks and task managers
        persistence_model = PersistenceModelFactory.persistence_model()
        tasks = persistence_model.tasks.list()
        tasksmanagers = persistence_model.tasksmanagers.list()

        # Create dictionaries for easy lookup
        task_dict = {task.id: task for task in tasks}
        manager_dict = {tm.id: tm for tm in tasksmanagers}

        # Get available indices for vector store
        vector_indices = await self.vector_store.list_indices()
        
        # Add New Context Section
        st.markdown("### Add New Context")
        # Task selection
        selected_task = st.selectbox(
            "Select Task",
            options=[""] + [f"{task.name} ({task.id})" for task in tasks],
            format_func=lambda x: x.split(" (")[0] if x else "Select a task..."
        )

        if selected_task:
            task_id = selected_task.split("(")[-1].strip(")")
            task = task_dict[task_id]

            # Show current task context configuration
            st.markdown("#### Context Configuration")
            
            use_context = st.checkbox(
                "Use Context",
                value=getattr(task, 'use_context', True),
                key=f"use_context_{task_id}"
            )
            
            inherit_manager = st.checkbox(
                "Inherit Manager Context",
                value=getattr(task, 'inherit_manager_context', True),
                key=f"inherit_manager_{task_id}"
            )

            if st.button("Update Configuration"):
                try:
                    await self.context_provider.update_task_context_config(
                        task_id=task_id,
                        use_context=use_context,
                        inherit_manager_context=inherit_manager
                    )
                    st.success("Context configuration updated!")
                except Exception as e:
                    st.error(f"Error updating configuration: {str(e)}")

            # Get existing contexts for duplicate checking
            existing_contexts = await self.context_provider.get_task_contexts(task_id)
            existing_sources = {(ctx['type'], ctx['source_id']) for ctx in existing_contexts}

            # Add new context section
            st.markdown("#### Add Context")
            
            context_type = st.selectbox(
                "Context Type",
                options=["vector", "system", "knowledge"]
            )

            if context_type == "vector":
                # Vector store context
                if vector_indices:
                    selected_index = st.selectbox(
                        "Select Vector Index",
                        options=[""] + [idx["name"] for idx in vector_indices],
                        format_func=lambda x: x.replace("vs_", "") if x else "Select an index..."
                    )
                    
                    if selected_index:
                        # Check for duplicate
                        if (context_type, selected_index) in existing_sources:
                            st.warning("This vector index is already associated with this task!")
                        else:
                            priority = st.slider("Priority", 0, 100, 50)
                            
                            if st.button("Add Vector Context"):
                                try:
                                    # Get index contents for metadata
                                    index_contents = await self.vector_store.get_index_contents(selected_index)
                                    
                                    # Create context metadata
                                    metadata = {
                                        "index_name": selected_index,
                                        "file_count": len(index_contents),
                                        "added_at": datetime.now().isoformat()
                                    }
                                    
                                    # Add context to task
                                    await self.context_provider.add_context_to_task(
                                        task_id=task_id,
                                        type="vector",
                                        source_id=selected_index,
                                        metadata=metadata,
                                        priority=priority
                                    )
                                    
                                    st.success(f"Added vector context from index {selected_index}")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error adding vector context: {str(e)}")
                else:
                    st.warning("No vector indices available. Create one in the Vector Store section.")

            elif context_type == "system":
                # System context
                name = st.text_input("Context Name")
                if name:
                    # Check for duplicate
                    if (context_type, name) in existing_sources:
                        st.warning("A system context with this name already exists for this task!")
                    else:
                        content = st.text_area("Content")
                        description = st.text_input("Description (optional)")
                        priority = st.slider("Priority", 0, 100, 50)
                        
                        if st.button("Add System Context"):
                            try:
                                await self.context_provider.add_system_context(
                                    task_id=task_id,
                                    name=name,
                                    content=content,
                                    description=description,
                                    priority=priority
                                )
                                st.success("Added system context")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding system context: {str(e)}")

            elif context_type == "knowledge":
                # Knowledge base context
                st.info("Knowledge base context integration coming soon...")

        else:
            st.info("Select a task to add new contexts")

        # Visual separator
        st.markdown("---")

        # Existing Contexts Section
        st.markdown("### Existing Task Contexts")
        
        # Show tasks with contexts
        has_contexts = False
        for task in tasks:
            contexts = await self.context_provider.get_task_contexts(task.id)
            if contexts:  # Only show tasks that have contexts
                has_contexts = True
                with st.expander(f"📋 {task.name} ({len(contexts)} contexts)", expanded=True):
                    st.write(f"Task ID: {task.id}")
                    st.write("Context Configuration:")
                    st.write(f"- Use Context: {getattr(task, 'use_context', True)}")
                    st.write(f"- Inherit Manager Context: {getattr(task, 'inherit_manager_context', True)}")
                    
                    st.markdown("#### Associated Contexts:")
                    for ctx in contexts:
                        with st.container():
                            cols = st.columns([6, 1])
                            with cols[0]:
                                st.markdown(f"**{ctx['type'].title()} Context**")
                                st.write(f"Priority: {ctx.get('priority', 50)}")
                                if ctx['type'] == 'vector':
                                    st.write(f"Index: {ctx['metadata'].get('index_name', 'Unknown')}")
                                    st.write(f"Files: {ctx['metadata'].get('file_count', 0)}")
                                elif ctx['type'] == 'system':
                                    st.write(f"Name: {ctx['metadata'].get('name', 'Unnamed')}")
                            with cols[1]:
                                if st.button("🗑️", key=f"delete_ctx_{task.id}_{ctx['id']}", 
                                           help=f"Remove this context from {task.name}"):
                                    try:
                                        await self.context_provider.remove_context_from_task(
                                            task_id=task.id,
                                            context_id=ctx['id']
                                        )
                                        st.success("Context removed!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error removing context: {str(e)}")
                            st.markdown("---")
        
        if not has_contexts:
            st.info("No tasks have any contexts associated with them yet.")