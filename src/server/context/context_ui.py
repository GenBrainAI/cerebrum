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
import traceback
import os
from dotenv import load_dotenv

from src.server.context.context_database import ContextDatabase
from src.server.context.code_catalog import CodeCatalog
from src.server.context.knowledge_base import KnowledgeBase
from server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.context.context_provider import ContextProvider
from src.server.context.vector_store import VectorStore
from ..tools.web_scraper_tool import WebScraperTool
from ..tools.repo_scraper import RepoScraper
from src.context_catalog.models import ContextEntry, TreeNode
from src.server.views.components.tree_select_component import TreeSelectComponent

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / '.env')

class ContextManagerUI:
    """Enhanced UI component for managing and visualizing the context system."""
    
    def __init__(self, skip_init=False):
        """Initialize context management UI components."""
        # Initialize session state if needed
        if 'persistence_model' not in st.session_state:
            st.session_state.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
            
        # Initialize global components
        self.global_context_provider = ContextProvider()
        self.global_context_provider.persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        self.global_vector_store = VectorStore()
        self.global_code_catalog = CodeCatalog()
        self.global_knowledge_base = KnowledgeBase(base_path="persistent_state/global_knowledge_base")
        
        # Initialize state-specific components
        self.context_provider = ContextProvider()
        self.context_provider.persistence_model = st.session_state.persistence_model
        self.vector_store = VectorStore()
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase()
        self.context_db = ContextDatabase()
        
        # Initialize tree component
        if 'context_tree_component' not in st.session_state:
            st.session_state.context_tree_component = TreeSelectComponent(self.handle_node_click)
        self.tree_component = st.session_state.context_tree_component
        
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
            
        # Initialize catalog view state
        if 'catalog_view' not in st.session_state:
            st.session_state.catalog_view = 'state'  # 'state' or 'global'
        
    @property
    def persistence_model(self):
        """Get persistence model instance when needed"""
        return PersistenceModelFactory.persistence_model()
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current UI state from session state."""
        return {
            "selected_context": st.session_state.get("selected_context"),
            "context_view": st.session_state.get("context_view", "knowledge"),
            "show_new_context_form": st.session_state.get("show_new_context_form", False)
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
        
        nav_cols = st.columns(6)  # Changed from 5 to 6 columns
        
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
            if st.button("🌐 Scraper", 
                        key="nav_scraper",
                        use_container_width=True):
                st.session_state.context_view = "scraper"
                st.session_state.layout_style = 'horizontal'
                
        with nav_cols[5]:
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
        elif view == "scraper":
            await self.render_scraper_view()
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
        import time
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
                print("\nCalculating component sizes:")
                
                # Knowledge base size
                kb_path = Path(self.knowledge_base.base_path)
                kb_size = sum(f.stat().st_size for f in kb_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                print(f"\nKnowledge Base Path: {kb_path}")
                print(f"Knowledge Base Size: {kb_size:.2f} MB")
                
                # Code catalog size
                cc_path = Path("persistent_state/context/code_catalog")
                cc_size = sum(f.stat().st_size for f in cc_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                print(f"\nCode Catalog Path: {cc_path}")
                print(f"Code Catalog Size: {cc_size:.2f} MB")
                
                # Vector store size
                vs_path = Path("persistent_state/context/vector_store")
                vs_size = sum(f.stat().st_size for f in vs_path.rglob('*') if f.is_file()) / (1024 * 1024)  # MB
                print(f"\nVector Store Path: {vs_path}")
                print(f"Vector Store Size: {vs_size:.2f} MB")
                
                total_size = int(kb_size + cc_size + vs_size)
                print(f"\nTotal Size: {total_size} MB")
                
            except Exception as e:
                print(f"\nError calculating sizes: {str(e)}")
                st.sidebar.write(f"Error calculating sizes: {str(e)}")
                total_size = 0
                
            st.session_state.cached_memory_usage = total_size
            st.session_state.last_memory_update = current_time
            
        return {
            "storage_size": st.session_state.cached_memory_usage
        }
    
    async def render_knowledge_view(self):
        """Render the knowledge base management view."""
        st.subheader("Knowledge Base Management")
        
        # Add view selector
        view = st.radio(
            "Select View",
            ["State-Specific", "Global Catalog"],
            key="knowledge_view_selector",
            horizontal=True,
            index=0 if st.session_state.catalog_view == 'state' else 1
        )
        st.session_state.catalog_view = 'state' if view == "State-Specific" else 'global'
        
        # Get appropriate knowledge base
        kb = self.knowledge_base if st.session_state.catalog_view == 'state' else self.global_knowledge_base
        
        # Get persistence model for task associations
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

        # Task Association Section (only for state-specific view)
        if st.session_state.catalog_view == 'state':
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

        # File upload section
        st.subheader("File Upload")
        uploaded_file = st.file_uploader(
            "Upload File",
            type=["txt", "md", "py", "json", "yaml", "pdf", "doc", "docx"]
        )
        
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
                
                # Update content area with file contents
                st.text_area("File Contents (editable)", value=content, key="file_content")
                
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

        # Add button
        if st.button("Add Knowledge Entry"):
            try:
                # Get content from file content area if it exists
                if "file_content" in st.session_state:
                    content = st.session_state.file_content
                
                # Prepare metadata
                tags_list = [t.strip() for t in tags.split(",") if t.strip()]
                metadata = {
                    "description": description,
                    "source_type": source_type,
                    "tags": tags_list,
                    "added_at": datetime.now().isoformat()
                }
                
                if uploaded_file:
                    metadata["filename"] = uploaded_file.name
                
                # Add to knowledge base
                entry_id = await kb.add_knowledge(
                    content=content,
                    domain=domain,
                    metadata=metadata,
                    tags=tags_list
                )
                
                # Handle task associations for state-specific view
                if st.session_state.catalog_view == 'state':
                    if task_id:
                        await self.context_provider.add_context_to_task(
                            task_id=task_id,
                            type="knowledge",
                            source_id=entry_id,
                            metadata=metadata
                        )
                    elif tasksmanager_id:
                        await self.context_provider.add_context_to_manager(
                            manager_id=tasksmanager_id,
                            type="knowledge",
                            source_id=entry_id,
                            metadata=metadata
                        )
                
                st.success("Knowledge entry added successfully!")
                time.sleep(0.5)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error adding knowledge entry: {str(e)}")

        # Display existing entries
        st.subheader("Existing Knowledge Entries")
        
        # Get entries from appropriate knowledge base
        try:
            entries = await kb.get_knowledge()
            
            if not entries:
                st.info("No knowledge entries found")
                return
                
            for entry in entries:
                with st.expander(f"📚 {entry['domain']} - {entry['metadata'].get('description', 'No description')}"):
                    st.write("Content:")
                    st.markdown(entry['content'])
                    
                    st.write("Metadata:")
                    st.json(entry['metadata'])
                    
                    if entry['tags']:
                        st.write("Tags:", ", ".join(entry['tags']))
                    
                    st.write(f"Created: {entry['created_at']}")
                    
                    # Show task associations for state-specific entries
                    if st.session_state.catalog_view == 'state':
                        contexts = await self.context_provider.get_contexts_by_source(
                            source_id=entry['id'],
                            type="knowledge"
                        )
                        if contexts:
                            st.write("Associated with:")
                            for ctx in contexts:
                                if ctx.get('task_id'):
                                    task = next((t for t in tasks if t.id == ctx['task_id']), None)
                                    if task:
                                        st.write(f"- Task: {task.name}")
                                elif ctx.get('manager_id'):
                                    manager = next((m for m in tasksmanagers if m.id == ctx['manager_id']), None)
                                    if manager:
                                        st.write(f"- Manager: {manager.name}")
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{entry['id']}"):
                        try:
                            await kb.delete_knowledge(entry['id'])
                            # Also remove task associations for state-specific entries
                            if st.session_state.catalog_view == 'state':
                                await self.context_provider.remove_contexts_by_source(
                                    source_id=entry['id'],
                                    type="knowledge"
                                )
                            st.success("Entry deleted!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting entry: {str(e)}")
                            
        except Exception as e:
            st.error(f"Error loading knowledge entries: {str(e)}")

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

    def _sanitize_index_name(self, name: str) -> str:
        """Sanitize index name to meet Qdrant requirements."""
        # Replace spaces and special characters with underscores
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure it starts with a letter
        if not sanitized[0].isalpha():
            sanitized = 'idx_' + sanitized
        # Ensure length is between 3-63 characters
        if len(sanitized) < 3:
            sanitized = sanitized + '_index'
        elif len(sanitized) > 63:
            sanitized = sanitized[:60] + '_idx'
        return sanitized

    async def render_vector_view(self):
        """Render the vector store management view."""
        st.subheader("Vector Store Management")

        # Force refresh vector store state
        try:
            print("\nDEBUG - Vector Store View:")
            self.vector_store._reload_indices()
            print("  Reloaded indices")
        except Exception as e:
            print(f"  Error reloading indices: {str(e)}")
            st.error(f"Error refreshing vector store state: {str(e)}")

        # Get all indices
        indices = await self.vector_store.list_indices()
        print(f"  All indices: {[idx['name'] for idx in indices]}")
        
        # Filter out non-vs_ indices for display
        display_indices = [idx for idx in indices if idx["name"].startswith("vs_")]
        print(f"  Filtered indices: {[idx['name'] for idx in display_indices]}")
        
        # Index selection
        col1, col2 = st.columns([3, 1])
        with col1:
            # Initialize the session state for index selection if not present
            if 'selected_index' not in st.session_state:
                st.session_state.selected_index = ""
            
            # Get the list of options
            index_options = [""] + [idx["name"] for idx in display_indices]
            print("\nDEBUG - Index Selection:")
            print(f"  Available options: {index_options}")
            print(f"  Current session state: {st.session_state.selected_index}")
            
            # If we have a new index, update the session state
            if 'new_index' in st.session_state:
                st.session_state.selected_index = st.session_state.new_index
                print(f"  Updating selected index to new index: {st.session_state.selected_index}")
                del st.session_state.new_index
            
            selected_index = st.selectbox(
                "Add scraped content to",
                options=index_options,
                format_func=lambda x: x.replace("vs_", "") if x else "Select an index...",
                key="selected_index"
            )
            print(f"  Final selected index: {selected_index}")
        
        # New index creation
        with st.expander("Create New Index"):
            new_index_name = st.text_input("New Index Name")
            if new_index_name and st.button("Create Index", use_container_width=True):
                try:
                    print("\nDEBUG - Creating New Index:")
                    print(f"  Raw name input: {new_index_name}")
                    
                    # Clean the index name - remove any existing vs_ prefix and sanitize
                    clean_name = new_index_name.lower().replace(' ', '_')
                    if clean_name.startswith('vs_'):
                        clean_name = clean_name[3:]
                    print(f"  Cleaned name: {clean_name}")
                    
                    # Create the final index name with vs_ prefix
                    index_name = f"vs_{clean_name}"
                    print(f"  Final index name: {index_name}")
                    
                    print("  Creating index in vector store...")
                    # Create index with metadata (properly awaited)
                    await self.vector_store.create_index(
                        clean_name,  # Pass the clean name without vs_ prefix
                        description=f"Index for {clean_name} content"
                    )
                    print("  Index created successfully")
                    
                    # Store the new index name in session state (with vs_ prefix)
                    st.session_state.new_index = f"vs_{clean_name}"
                    print(f"  Stored in session state: new_index = {st.session_state.new_index}")
                    
                    st.success(f"Created index: {clean_name}")
                    print("  Success message displayed, rerunning...")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    print(f"\nDEBUG - Error Creating Index:")
                    print(f"  Error type: {type(e)}")
                    print(f"  Error message: {str(e)}")
                    print(f"  Stack trace: {traceback.format_exc()}")
                    st.error(f"Error creating index: {str(e)}")
                    st.error(f"Stack trace: {traceback.format_exc()}")

        if selected_index:
            # Source selection and file upload UI
            source_type = st.radio(
                "Source Type",
                ["Local Files", "Directory"],
                horizontal=True
            )

            # Content filters
            with st.expander("Content Filters"):
                col1, col2 = st.columns(2)
                with col1:
                    exclude_headers = st.checkbox("Exclude headers", value=True)
                    exclude_footers = st.checkbox("Exclude footers", value=True)
                with col2:
                    exclude_nav = st.checkbox("Exclude navigation", value=True)
                    exclude_ads = st.checkbox("Exclude ads", value=True)

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
                            # Create a progress bar
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            def update_progress(message: str, current: int, total: int):
                                if total > 0:
                                    progress_bar.progress(current / total)
                                status_text.text(message)
                            
                            processed = await self.vector_store.process_directory(
                                index_name=selected_index,
                                directory_path=dir_path,
                                progress_callback=update_progress
                            )
                            
                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()
                            
                            st.success(f"Processed {processed} files from directory")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error processing directory: {str(e)}")

            # Show contents of selected index
            st.markdown("---")
            st.subheader("Vector Store Contents")
            
            try:
                # Show only the selected index
                if selected_index:
                    idx = next((i for i in indices if i['name'] == selected_index), None)
                    if idx:
                        print(f"\nDEBUG - Processing index: {idx['name']}")
                        print(f"  Index details: {idx}")
                        
                        # Get files from collection using get_filtered_items_from_index instead of get_index_contents
                        files = await self.vector_store.get_filtered_items_from_index(
                            index_name=idx['name'],
                            limit=100  # Increase limit to get more items
                        )
                        print(f"  Raw files retrieved: {len(files)}")
                        
                        # Debug raw files
                        print("  Raw files details:")
                        for i, file_info in enumerate(files):
                            print(f"    File {i}:")
                            print(f"      ID: {file_info.get('id')}")
                            print(f"      Metadata: {file_info.get('metadata', {})}")
                        
                        # Deduplicate files based on file_id
                        unique_files = {}
                        for file_info in files:
                            metadata = file_info.get('metadata', {})
                            file_id = metadata.get('file_id', file_info.get('id'))
                            if file_id:
                                # Keep the most recent version if duplicate
                                if file_id not in unique_files or (
                                    metadata.get('added_at', '') > unique_files[file_id].get('metadata', {}).get('added_at', '')
                                ):
                                    unique_files[file_id] = file_info
                        
                        print(f"  Number of unique files: {len(unique_files)}")
                        print("  Unique files metadata:")
                        for file_id, file_info in unique_files.items():
                            print(f"    {file_id}: {file_info.get('metadata', {})}")
                        
                        # Convert back to list and sort by added_at
                        files = sorted(
                            unique_files.values(),
                            key=lambda x: x.get('metadata', {}).get('added_at', ''),
                            reverse=True
                        )
                        
                        # Display index with file count
                        with st.expander(f"📁 {idx['name'].replace('vs_', '')} ({len(files)} files)", expanded=True):
                            st.write(f"Description: {idx.get('description', 'No description')}")
                            
                            # Initialize used_keys set
                            used_keys = set()
                            
                            if files:
                                for file_idx, file_info in enumerate(files):
                                    metadata = file_info.get('metadata', {})
                                    content = file_info.get('content', '')
                                    file_id = metadata.get('file_id', file_info.get('id', f'unknown_{file_idx}'))
                                    
                                    print(f"\nDEBUG - Displaying file {file_idx}:")
                                    print(f"  ID: {file_id}")
                                    print(f"  Metadata: {metadata}")
                                    
                                    col1, col2 = st.columns([20, 1])
                                    with col1:
                                        st.write(f"📄 {metadata.get('title', metadata.get('original_name', 'Unnamed'))}")
                                        st.write(f"Added: {metadata.get('added_at', 'Unknown')}")
                                        if metadata.get('size'):
                                            st.write(f"Size: {metadata.get('size')} bytes")
                                        if metadata.get('total_chunks'):
                                            st.write(f"Total chunks: {metadata.get('total_chunks')}")
                                        
                                        # Show chunks if this is a root document
                                        if metadata.get('is_root', False):
                                            chunk_files = [f for f in files if 
                                                         f.get('metadata', {}).get('file_id') == file_id and 
                                                         not f.get('metadata', {}).get('is_root', False)]
                                            
                                            if chunk_files:
                                                with st.expander(f"Show {len(chunk_files)} chunks"):
                                                    for chunk in sorted(chunk_files, 
                                                                      key=lambda x: x.get('metadata', {}).get('chunk_index', 0)):
                                                        chunk_meta = chunk.get('metadata', {})
                                                        st.write(f"Chunk {chunk_meta.get('chunk_index')}")
                                                        st.write(f"Size: {chunk_meta.get('chunk_size')} bytes")
                                                        st.text(chunk.get('content', '')[:200] + "...")
                                        else:
                                            st.write("Content preview:")
                                            st.text(content[:200] + "..." if len(content) > 200 else content)
                                            
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
                                        print(f"  Delete button key: {delete_key}")
                                        
                                        if st.button("🗑️", key=delete_key, 
                                                   help=f"Delete {metadata.get('title', 'file')}"):
                                            try:
                                                collection = self.vector_store.client.get_collection(
                                                    name=idx['name'],
                                                    embedding_function=self.vector_store.embedding_function
                                                )
                                                collection.delete(ids=[file_id])
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
                            print(f"  Index delete button key: {index_delete_key}")
                            
                            if st.button("Delete Index", key=index_delete_key, 
                                       help=f"Delete entire index {idx['name']}", type="secondary"):
                                try:
                                    await self.vector_store.delete_index(idx['name'])
                                    st.success("Index deleted!")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                    else:
                        st.info("Please select an index to view its contents")

            except Exception as e:
                st.error(f"Error listing vector store contents: {str(e)}")
                # Add stack trace for debugging
                import traceback
                st.error(f"Stack trace: {traceback.format_exc()}")
        else:
            st.info("Please select an index to view its contents")

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
                                    # Get index contents for metadata using get_filtered_items_from_index
                                    index_contents = await self.vector_store.get_filtered_items_from_index(
                                        index_name=selected_index,
                                        limit=1000  # High limit to get an accurate count
                                    )
                                    
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

    async def render_scraper_view(self):
        """Render the web and repository scraping interface."""
        st.subheader("Content Scraper")
        
        # Get all vector store indices
        indices = await self.vector_store.list_indices()
        
        # Ensure all indices have vs_ prefix
        display_indices = []
        for idx in indices:
            name = idx["name"]
            if not name.startswith("vs_"):
                # Add vs_ prefix if missing
                idx["name"] = f"vs_{name}"
            display_indices.append(idx)
        
        print(f"\nDEBUG - Vector Store Indices:")
        print(f"  Raw indices: {[idx['name'] for idx in indices]}")
        print(f"  Display indices: {[idx['name'] for idx in display_indices]}")
        
        # Index selection
        col1, col2 = st.columns([3, 1])
        with col1:
            # Initialize the session state for index selection if not present
            if 'selected_index' not in st.session_state:
                st.session_state.selected_index = ""
            
            # Get the list of options
            index_options = [""] + [idx["name"] for idx in display_indices]
            print("\nDEBUG - Index Selection:")
            print(f"  Available options: {index_options}")
            print(f"  Current session state: {st.session_state.selected_index}")
            
            selected_index = st.selectbox(
                "Add scraped content to",
                options=index_options,
                format_func=lambda x: x.replace("vs_", "") if x else "Select an index...",
                key="selected_index"
            )
            print(f"  Final selected index: {selected_index}")
        
        # New index creation
        with st.expander("Create New Index"):
            new_index_name = st.text_input("New Index Name")
            if new_index_name and st.button("Create Index", use_container_width=True):
                try:
                    print("\nDEBUG - Creating New Index:")
                    print(f"  Raw name input: {new_index_name}")
                    
                    # Clean the index name - remove any existing vs_ prefix and sanitize
                    clean_name = new_index_name.lower().replace(' ', '_')
                    if clean_name.startswith('vs_'):
                        clean_name = clean_name[3:]
                    print(f"  Cleaned name: {clean_name}")
                    
                    # Create the final index name with vs_ prefix
                    index_name = f"vs_{clean_name}"
                    print(f"  Final index name: {index_name}")
                    
                    print("  Creating index in vector store...")
                    # Create index with metadata (properly awaited)
                    await self.vector_store.create_index(
                        clean_name,  # Pass the clean name without vs_ prefix
                        description=f"Index for {clean_name} content"
                    )
                    print("  Index created successfully")
                    
                    # Store the new index name in session state (with vs_ prefix)
                    st.session_state.new_index = f"vs_{clean_name}"
                    print(f"  Stored in session state: new_index = {st.session_state.new_index}")
                    
                    st.success(f"Created index: {clean_name}")
                    print("  Success message displayed, rerunning...")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    print(f"\nDEBUG - Error Creating Index:")
                    print(f"  Error type: {type(e)}")
                    print(f"  Error message: {str(e)}")
                    print(f"  Stack trace: {traceback.format_exc()}")
                    st.error(f"Error creating index: {str(e)}")
                    st.error(f"Stack trace: {traceback.format_exc()}")

        # Source type selection
        source_type = st.radio(
            "Source Type",
            ["Web Page", "GitHub Repository"],
            horizontal=True
        )

        if source_type == "Web Page":
            # URL input
            url = st.text_input("URL to scrape")
            
            # Domain and URL pattern restrictions
            col1, col2 = st.columns(2)
            with col1:
                allowed_domains = st.text_input(
                    "Allowed domains (comma-separated, leave empty for no restriction)"
                )
            with col2:
                url_pattern = st.text_input(
                    "URL pattern (regex)",
                    help="Only URLs matching this pattern will be scraped"
                )
            
            # Link following and depth control
            col1, col2 = st.columns(2)
            with col1:
                follow_links = st.checkbox(
                    "Follow links on page",
                    value=False,
                    help="If unchecked, will only scrape the provided URL"
                )
            with col2:
                max_depth = st.number_input(
                    "Max link depth",
                    min_value=0,
                    max_value=5,
                    value=0,
                    help="0 = only scrape the provided URL, 1 = also scrape linked pages, etc.",
                    disabled=not follow_links
                )

            if st.button("Start Web Scraping", use_container_width=True):
                if not selected_index:
                    st.error("Please select or create an index first")
                    return
                
                if not url:
                    st.error("Please enter a URL to scrape")
                    return
                
                try:
                    with st.spinner("Scraping web content..."):
                        # Initialize web scraper
                        scraper = WebScraperTool(
                            allowed_domains=[d.strip() for d in allowed_domains.split(',')] if allowed_domains else None,
                            max_depth=max_depth if follow_links else 0
                        )
                        if url_pattern:
                            scraper.url_pattern = url_pattern
                        
                        # Get URLs to scrape
                        if follow_links:
                            urls_to_scrape = await scraper.get_urls_to_scrape(url)
                        else:
                            urls_to_scrape = [url]
                        
                        if not urls_to_scrape:
                            st.warning("No URLs found to scrape")
                            return
                        
                        st.info(f"Found {len(urls_to_scrape)} URLs to scrape")
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        successful_scrapes = 0
                        failed_scrapes = 0
                        
                        # Process each URL
                        for i, url_to_scrape in enumerate(urls_to_scrape):
                            try:
                                status_text.text(f"Processing: {url_to_scrape}")
                                result = await scraper.scrape_page(url_to_scrape)
                                
                                if result and result.get('content'):
                                    # Prepare metadata
                                    current_time = datetime.now().isoformat()
                                    metadata = {
                                        'url': url_to_scrape,
                                        'title': result.get('metadata', {}).get('title', ''),
                                        'description': result.get('metadata', {}).get('description', ''),  # Already string from web_scraper
                                        'scraped_at': current_time,
                                        'added_at': current_time,
                                        'type': 'web_content'
                                    }
                                    
                                    # Ensure all metadata values are strings
                                    for key, value in metadata.items():
                                        if isinstance(value, list):
                                            metadata[key] = ' '.join(str(v) for v in value)
                                        elif not isinstance(value, (str, int, float, bool)):
                                            metadata[key] = str(value)
                                    
                                    # Add to vector store
                                    await self.vector_store.add_file_to_index(
                                        index_name=selected_index,
                                        file_path_or_obj=io.StringIO(result['content']),
                                        metadata=metadata,
                                        progress_callback=lambda msg, cur, tot: status_text.text(msg)
                                    )
                                    successful_scrapes += 1
                                
                                progress_bar.progress((i + 1) / len(urls_to_scrape))
                                
                            except Exception as e:
                                failed_scrapes += 1
                                st.error(f"Error processing {url_to_scrape}: {str(e)}")
                                continue
                        
                        # Show final status
                        if successful_scrapes > 0:
                            st.success(f"Successfully scraped {successful_scrapes} pages")
                        if failed_scrapes > 0:
                            st.warning(f"Failed to scrape {failed_scrapes} pages")
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        if successful_scrapes > 0:
                            time.sleep(0.5)
                            st.rerun()
                        
                except Exception as e:
                    st.error(f"Error during web scraping: {str(e)}")
                    import traceback
                    st.error(f"Stack trace: {traceback.format_exc()}")

        else:  # GitHub Repository
            # Get GitHub token from environment with debug info
            default_token = os.getenv("GITHUB_ACCESS_TOKEN")
            print(f"\nDEBUG - GitHub Authentication:")
            print(f"  Project root: {project_root}")
            print(f"  Current working directory: {os.getcwd()}")
            print(f"  Default token from env: {'Present' if default_token else 'Not found'}")
            
            # Repository URL and branch
            repo_url = st.text_input("Repository URL")
            col1, col2 = st.columns([3, 1])
            with col1:
                branch = st.text_input("Branch (optional)", value="main")
            with col2:
                use_auth = st.checkbox("Use Authentication", value=bool(default_token))
            
            # Token handling
            token = default_token  # Set token to default value initially
            if use_auth:
                token = st.text_input(
                    "GitHub Token", 
                    value=default_token,  # Use the default token directly
                    type="password",
                    help="Enter your GitHub token or ensure GITHUB_ACCESS_TOKEN is set in your .env file"
                )
                print(f"  Use authentication: {use_auth}")
                print(f"  Token status: {'Using default token' if token == default_token else 'Using custom token' if token else 'No token'}")
            
            # Scraping options
            st.markdown("### Repository Scraping Options")
            col1, col2 = st.columns(2)
            with col1:
                include_docs = st.checkbox("Include Documentation", value=True)
                include_tests = st.checkbox("Include Tests", value=False)
            with col2:
                max_files = st.number_input("Max Files", min_value=1, value=100)
                path_pattern = st.text_input(
                    "Path Pattern (regex)",
                    help="Optional regex pattern to filter which files to scrape (e.g., 'docs/.*\\.md$' for markdown files in docs folder)"
                )
            
            if st.button("Start Repository Scraping", use_container_width=True):
                if not selected_index:
                    st.error("Please select or create an index first")
                    return
                
                if not repo_url:
                    st.error("Please enter a repository URL")
                    return
                
                try:
                    with st.spinner("Scraping repository..."):
                        # Initialize repo scraper
                        scraper = RepoScraper(
                            github_token=token if use_auth else None,
                            gitlab_token=token if use_auth else None
                        )
                        
                        # Scrape repository
                        result = await scraper.scrape_repository(
                            url=repo_url,
                            branch=branch,
                            max_files=max_files,
                            include_docs=include_docs,
                            include_tests=include_tests,
                            path_pattern=path_pattern if path_pattern else None
                        )
                        
                        # Add files to vector store
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(message: str, current: int, total: int):
                            if total > 0:
                                progress_bar.progress(current / total)
                            status_text.text(message)
                        
                        total_files = len(result['files'])
                        for i, file_info in enumerate(result['files']):
                            try:
                                update_progress(f"Processing file {i+1}/{total_files}: {file_info['path']}", i, total_files)
                                
                                # Prepare metadata for repository files
                                current_time = datetime.now().isoformat()
                                metadata = {
                                    'repository_url': result['url'],
                                    'repository_owner': result['owner'],
                                    'repository_name': result['repo'],
                                    'branch': result['branch'],
                                    'platform': result['platform'],
                                    'file_path': file_info['path'],
                                    'file_type': file_info['type'],
                                    'file_size': file_info['size'],
                                    'sha': file_info.get('sha', ''),  # Ensure not None
                                    'id': file_info.get('id', ''),    # Ensure not None
                                    'scraped_at': result['scraped_at'],
                                    'added_at': current_time,
                                    'is_root': True,
                                    'title': f"{result['repo']}/{file_info['path']}"  # Add meaningful title
                                }
                                
                                # Ensure no None values in metadata
                                metadata = {k: str(v) if v is None else v 
                                          for k, v in metadata.items()}
                                
                                # Add to vector store
                                print(f"\nDEBUG - Adding file to vector store:")
                                print(f"  Selected index: {selected_index}")
                                print(f"  File path: {file_info['path']}")
                                print(f"  Metadata: {metadata}")
                                
                                # Add to vector store (keep the vs_ prefix)
                                await self.vector_store.add_file_to_index(
                                    index_name=selected_index,  # Keep the vs_ prefix
                                    file_path_or_obj=io.StringIO(file_info['content']),
                                    metadata=metadata,
                                    progress_callback=lambda msg, cur, tot: update_progress(
                                        f"File {i+1}/{total_files} - {msg}", cur, tot
                                    )
                                )
                                print("  File added successfully")
                                
                            except Exception as e:
                                st.error(f"Error processing file {file_info['path']}: {str(e)}")
                                continue
                        
                        st.success(f"Successfully scraped {total_files} files from repository")
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        time.sleep(0.5)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error scraping repository: {str(e)}")
                    import traceback
                    st.error(f"Stack trace: {traceback.format_exc()}")

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
                    value=self.vector_store.config.batch_size
                )
                st.number_input(
                    "Max Retries",
                    min_value=1,
                    value=self.vector_store.config.max_retries
                )
                
            with col2:
                st.number_input(
                    "Connection Timeout",
                    min_value=1,
                    value=self.vector_store.config.connection_timeout
                )
                st.number_input(
                    "Max Concurrent Requests",
                    min_value=1,
                    value=self.vector_store.config.max_concurrent_requests
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

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the context manager."""
        try:
            # Get current state
            state = self.get_current_state()
            
            # Get total contexts
            total_contexts = 0
            if self.context_provider:
                contexts = self.context_provider.get_all_contexts()
                total_contexts = len(contexts) if contexts else 0
            
            return {
                "loaded": True,
                "active_context": state.get("selected_context"),
                "context_type": state.get("context_view", "knowledge"),
                "total_contexts": total_contexts
            }
        except Exception as e:
            print(f"Error getting context manager status: {str(e)}")
            return {
                "loaded": False,
                "error": str(e)
            }

    def get_context_tree(self) -> Optional[TreeNode]:
        """Get the hierarchical tree of contexts organized by type."""
        try:
            if not self.context_provider:
                return None
                
            # Create root node
            root = TreeNode(name="Contexts", data=None)
            
            # Get all contexts
            contexts = self.context_provider.get_all_contexts()
            if not contexts:
                return root
                
            # Group contexts by type
            type_groups: Dict[str, List[ContextEntry]] = {}
            for context in contexts:
                source_type = context.metadata.source_type.value
                if source_type not in type_groups:
                    type_groups[source_type] = []
                type_groups[source_type].append(context)
            
            # Create type nodes
            for source_type, type_contexts in type_groups.items():
                type_node = TreeNode(name=source_type, data=None)
                root.add_child(type_node)
                
                # Add context nodes under type
                for context in type_contexts:
                    context_node = TreeNode(
                        name=context.metadata.purpose,
                        data=context
                    )
                    type_node.add_child(context_node)
                    
                    # Add associated task managers and tasks
                    if hasattr(context, "task_managers"):
                        for manager in context.task_managers:
                            manager_node = TreeNode(
                                name=manager.name,
                                data=manager
                            )
                            context_node.add_child(manager_node)
                            
                            # Add tasks under manager
                            for task in manager.tasks:
                                task_node = TreeNode(
                                    name=task.name,
                                    data=task
                                )
                                manager_node.add_child(task_node)
            
            return root
            
        except Exception as e:
            print(f"Error building context tree: {str(e)}")
            return None

    def set_active_context(self, context_id: str) -> None:
        """Set the active context."""
        if not self.context_provider:
            return
            
        state = self.get_current_state()
        state["selected_context"] = context_id
        
        # Get context type and update view
        context = self.context_provider.get_context(context_id)
        if context:
            state["context_view"] = context.metadata.source_type.value.lower()

    def handle_node_click(self, node):
        """Handle tree node click events."""
        if node and hasattr(node, 'data') and node.data:
            if 'id' in node.data:
                st.session_state.selected_context = node.data['id']
                st.session_state.context_view = node.data.get('type', 'vector')
                # Force a rerun to update the UI
                st.rerun()