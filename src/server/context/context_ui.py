import streamlit as st
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import asyncio
import PyPDF2
import docx
import io
import time
import tempfile

from src.server.context.context_database import ContextDatabase
from src.server.context.code_catalog import CodeCatalog
from src.server.context.knowledge_base import KnowledgeBase
from src.server.controllers import context_state_controller
from src.server.models.persistence_models import StorageLocation, StorageType
from ..controllers.persistence_controller import load_from_storage, save_to_storage
from server.persistence.persistence_model_factory import PersistenceModelFactory

class ContextManagerUI:
    """Enhanced UI component for managing and visualizing the context system."""
    
    def __init__(self):
        """Initialize context management components."""
        self.context_db = ContextDatabase()
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase()
        
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
    
    async def render_status_bar(self):
        """Render a status bar showing system metrics."""
        stats = self.get_statistics()
        
        try:
            vector_stats = await self.context_db.vector_store.get_stats()
        except Exception as e:
            st.error(f"Error getting vector store stats: {str(e)}")
            vector_stats = {}
        
        status_cols = st.columns(4)
        with status_cols[0]:
            st.metric("Indexed Files", stats.get("total_files", 0))
        with status_cols[1]:
            st.metric("Knowledge Entries", stats.get("total_entries", 0))
        with status_cols[2]:
            st.metric("Vector Chunks", vector_stats.get("total_vectors", 0))
        with status_cols[3]:
            # Combine storage sizes
            total_storage = stats.get("memory_usage", 0) + vector_stats.get("storage_size", 0)
            st.metric("Disk Usage", f"{total_storage:.2f}MB")
    
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
    
    async def render_main_view(self):
        """Render the main content based on selected view."""
        if "context_view" not in st.session_state:
            st.session_state.context_view = "knowledge"
                
        view = st.session_state.context_view
        
        if view == "knowledge":
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
        self.render_persistent_state_ui()
        
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
        st.subheader("Knowledge Base Management")

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
            # Get available tasks from persistence model
            persistence_model = PersistenceModelFactory.persistence_model()
            tasks = persistence_model.tasks.list()
            if tasks:
                task_options = {f"{t.name} ({t.id})": t.id for t in tasks}
                selected_task = st.selectbox(
                    "Select Task",
                    options=list(task_options.keys())
                )
                if selected_task:
                    task_id = task_options[selected_task]

        elif associate_type == "Tasks Manager":
            # Get available tasksmanagers from persistence model
            persistence_model = PersistenceModelFactory.persistence_model()
            tasksmanagers = persistence_model.tasksmanagers.list()
            if tasksmanagers:
                tm_options = {f"{tm.name} ({tm.id})": tm.id for tm in tasksmanagers}
                selected_tm = st.selectbox(
                    "Select Tasks Manager",
                    options=list(tm_options.keys())
                )
                if selected_tm:
                    tasksmanager_id = tm_options[selected_tm]

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
                
                st.success(f"Knowledge entry added with ID: {entry_id}")
            except Exception as e:
                st.error(f"Error adding knowledge: {str(e)}")

        # Knowledge browse section
        st.markdown("---")
        st.subheader("Browse Knowledge")
        
        # Add task/tasksmanager filter
        filter_by = st.radio(
            "Filter by:",
            ["All", "Task", "Tasks Manager", "Domain & Tags"]
        )

        entries = []
        if filter_by == "Task":
            task_id = st.selectbox(
                "Select Task",
                options=list(task_options.keys())
            )
            if task_id:
                entries = self.knowledge_base.get_task_knowledge(task_options[task_id])
        elif filter_by == "Tasks Manager":
            tm_id = st.selectbox(
                "Select Tasks Manager",
                options=list(tm_options.keys())
            )
            if tm_id:
                entries = self.knowledge_base.get_tasksmanager_knowledge(tm_options[tm_id])
        else:
            # Existing domain and tag filtering
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

        # Display entries with task associations
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

        # Get stats first for use in multiple places
        try:
            stats = await self.context_db.vector_store.get_stats()
            
            # Display total files at the top
            st.metric("Indexed Files", stats.get('total_files', 0))
            
        except Exception as e:
            st.error(f"Error getting vector store statistics: {str(e)}")
            stats = {}

        # File ingestion section
        st.subheader("Add Files to Vector Store")
        
        # Source selection
        source_type = st.radio(
            "Source Type",
            ["Local Files", "Directory"]
        )

        # File upload section
        uploaded_files = st.file_uploader(
            "Upload Files",
            type=["txt", "md", "py", "json", "yaml", "pdf", "doc", "docx"],
            accept_multiple_files=True
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    metadata = {
                        "original_name": uploaded_file.name,
                        "file_type": uploaded_file.type,
                        "size": uploaded_file.size
                    }
                    await self.context_db.vector_store.add_file(uploaded_file, metadata)
                    st.success(f"Added {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

        # List and manage existing files
        st.markdown("---")
        st.subheader("Manage Vector Store Files")
        
        try:
            vector_files = await self.context_db.vector_store.list_files()
            
            if not vector_files:
                st.info("No files in vector store")
                return
                
            # Display files with delete buttons
            for file_info in vector_files:
                col1, col2 = st.columns([20, 1])
                
                with col1:
                    with st.expander(f"📄 {file_info.get('original_name', 'Unnamed')}"):
                        st.write("File Information:")
                        st.json({
                            'Added': file_info.get('added_at', 'Unknown'),
                            'Size': file_info.get('size', 'Unknown'),
                            'Type': file_info.get('file_type', 'Unknown'),
                            'Chunks': file_info.get('chunk_count', 0)
                        })
                
                with col2:
                    if st.button("🗑️", key=f"delete_{file_info['id']}", 
                               help=f"Delete {file_info.get('original_name', 'file')}"):
                        try:
                            await self.context_db.vector_store.delete_file(file_info['id'])
                            st.success("File deleted!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        except Exception as e:
            st.error(f"Error listing vector store files: {str(e)}")

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

    def render_code_section(self):
        """Render the code management section."""
        st.header("Code Management")
        
        # Repository input section
        with st.expander("Add Repository", expanded=True):
            repo_url = st.text_input(
                "GitHub Repository URL or org/repo",
                placeholder="e.g. openai/whisper or https://github.com/openai/whisper"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                branch = st.text_input("Branch", value="main")
            with col2:
                deep_scan = st.checkbox("Deep Scan", value=False, 
                    help="Scan non-Python files like JavaScript, TypeScript")
            
            if st.button("Add Repository"):
                if repo_url:
                    with st.spinner("Cloning and analyzing repository..."):
                        try:
                            stats = self.code_catalog.index_github_repo(
                                repo_url=repo_url,
                                branch=branch,
                                deep_scan=deep_scan
                            )
                            st.success(f"Repository indexed successfully: {stats}")
                        except Exception as e:
                            st.error(f"Error indexing repository: {str(e)}")
                else:
                    st.warning("Please enter a repository URL")
        
        # Repository list section
        st.subheader("Indexed Repositories")
        from src.pages.context_management import render_repository_list
        render_repository_list(st, self.code_catalog)