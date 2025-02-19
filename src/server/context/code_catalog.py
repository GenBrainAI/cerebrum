from typing import Dict, List, Optional, Any
import ast
import os
import logging
from datetime import datetime
import git
import tempfile
import shutil
from pathlib import Path
import json

class CodeCatalog:
    """Maintains a high-level catalog of code files and their relationships."""
    
    def __init__(self):
        """Initialize the code catalog."""
        # Set up logging first
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Initialize all required attributes
        self.file_index: Dict[str, Dict[str, Any]] = {}
        self.module_descriptions: Dict[str, str] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.last_update: Optional[datetime] = None
        
        # Create fixed directories for repositories and state
        self.base_dir = Path("persistent_state/context/code_catalog")
        self.repos_dir = self.base_dir / "repos"
        self.state_file = self.base_dir / "catalog_state.json"
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(exist_ok=True)
        
        # Load existing state if available
        self._load_persistent_state()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _save_persistent_state(self):
        """Save current state to persistent storage."""
        try:
            state = self.get_state()
            # Ensure the directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use atomic write to prevent corruption
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.state_file)
            
            self.logger.info(f"Successfully saved state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Error saving persistent state: {str(e)}")
            raise

    def _load_persistent_state(self):
        """Load state from persistent storage if available."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # Convert ISO format strings back to datetime objects
                file_index = state.get('file_index', {})
                for path, info in file_index.items():
                    if 'last_modified' in info:
                        info['last_modified'] = datetime.fromisoformat(info['last_modified'])
                
                self.load_state(state)
                self.logger.info(f"Successfully loaded state from {self.state_file}")
        except Exception as e:
            self.logger.error(f"Error loading persistent state: {str(e)}")
            # Create a backup of the corrupted file
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix('.bak')
                shutil.copy2(self.state_file, backup_file)
                self.logger.info(f"Created backup of corrupted state file at {backup_file}")
            # Initialize with empty state
            self.file_index = {}
            self.module_descriptions = {}
            self.dependencies = {}
            self.last_update = None

    async def index_directory(
        self,
        directory_path: str,
        exclude_dirs: Optional[List[str]] = None,
        analyze_deps: bool = True,
        parse_docs: bool = True,
        deep_scan: bool = False,
        repo_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a catalog of all code files in the directory.
        
        Args:
            directory_path: Path to directory to index
            exclude_dirs: List of directory names to exclude
            analyze_deps: Whether to analyze dependencies
            parse_docs: Whether to parse documentation
            deep_scan: Whether to scan non-Python files
            repo_name: Optional repository name for organizing files
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        exclude_dirs = exclude_dirs or ['venv', '__pycache__', '.git', 'node_modules']

        try:
            for root, dirs, files in os.walk(directory_path):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')) if deep_scan else file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            # Create catalog path with repo name if provided
                            if repo_name:
                                relative_path = os.path.relpath(file_path, directory_path)
                                catalog_path = f"{repo_name}/{relative_path}"
                            else:
                                catalog_path = file_path

                            await self._catalog_file(
                                file_path=file_path,
                                catalog_path=catalog_path,
                                analyze_deps=analyze_deps,
                                parse_docs=parse_docs
                            )
                            stats["processed"] += 1
                        except Exception as e:
                            self.logger.error(f"Error cataloging file {file_path}: {str(e)}")
                            stats["failed"] += 1
                            continue

            self.last_update = datetime.now()
            # Save state after successful indexing
            self._save_persistent_state()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error indexing directory: {str(e)}")
            raise

    async def _catalog_file(
        self, 
        file_path: str,
        catalog_path: str,
        analyze_deps: bool = True,
        parse_docs: bool = True
    ) -> None:
        """
        Analyze and catalog a single Python file.
        
        Args:
            file_path: Actual path to the Python file to read
            catalog_path: Path to use in the catalog (may include repo name)
            analyze_deps: Whether to analyze dependencies
            parse_docs: Whether to parse documentation
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_stats = {
                'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'size': os.path.getsize(file_path),
                'type': 'python',
                'content': content,
                'imports': self._extract_imports(content) if analyze_deps else [],
                'classes': self._extract_classes(content) if parse_docs else [],
                'functions': self._extract_functions(content) if parse_docs else [],
                'doc_strings': self._extract_docstrings(content) if parse_docs else {},
                'dependencies': []
            }

            # Use catalog_path instead of file_path for the index
            self.file_index[catalog_path] = file_stats
            
            # Update dependencies if requested
            if analyze_deps:
                self._update_dependencies(catalog_path, file_stats['imports'])
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_path}: {str(e)}")
            raise

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from code."""
        try:
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(f"import {name.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"from {module} import {name.name}")
                        
            return imports
            
        except Exception:
            return []

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract class definitions and their details from code.
        
        Returns list of dictionaries containing class information.
        """
        try:
            tree = ast.parse(content)
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                        'methods': [],
                        'doc_string': ast.get_docstring(node)
                    }
                    
                    # Extract methods
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_info = {
                                'name': child.name,
                                'doc_string': ast.get_docstring(child),
                                'decorators': [d.id for d in child.decorator_list if isinstance(d, ast.Name)]
                            }
                            class_info['methods'].append(method_info)
                            
                    classes.append(class_info)
                    
            return classes
            
        except Exception:
            return []

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract function definitions and their details from code.
        
        Returns list of dictionaries containing function information.
        """
        try:
            tree = ast.parse(content)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not isinstance(node.parent, ast.ClassDef):
                    function_info = {
                        'name': node.name,
                        'doc_string': ast.get_docstring(node),
                        'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
                    functions.append(function_info)
                    
            return functions
            
        except Exception:
            return []

    def _extract_docstrings(self, content: str) -> Dict[str, str]:
        """Extract all docstrings from the code."""
        try:
            tree = ast.parse(content)
            docstrings = {}
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        if isinstance(node, ast.Module):
                            docstrings['module'] = doc
                        else:
                            docstrings[node.name] = doc
                            
            return docstrings
            
        except Exception:
            return {}

    def _update_dependencies(self, file_path: str, imports: List[str]) -> None:
        """Update the dependency graph based on imports."""
        self.dependencies[file_path] = imports

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific file."""
        return self.file_index.get(file_path)

    def get_dependencies(self, file_path: str) -> List[str]:
        """Get list of dependencies for a specific file."""
        return self.dependencies.get(file_path, [])

    def get_reverse_dependencies(self, file_path: str) -> List[str]:
        """Get list of files that depend on the specified file."""
        reverse_deps = []
        for dep_file, deps in self.dependencies.items():
            if file_path in deps:
                reverse_deps.append(dep_file)
        return reverse_deps

    def search_code(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for code elements matching the query.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching code elements with their locations
        """
        results = []
        query = query.lower()
        
        for file_path, info in self.file_index.items():
            # Search in classes
            for class_info in info.get('classes', []):
                if query in class_info['name'].lower():
                    results.append({
                        'type': 'class',
                        'name': class_info['name'],
                        'file': file_path,
                        'doc_string': class_info.get('doc_string')
                    })
                    
            # Search in functions
            for func_info in info.get('functions', []):
                if query in func_info['name'].lower():
                    results.append({
                        'type': 'function',
                        'name': func_info['name'],
                        'file': file_path,
                        'doc_string': func_info.get('doc_string')
                    })
                    
            # Search in docstrings
            for name, doc in info.get('doc_strings', {}).items():
                if query in doc.lower():
                    results.append({
                        'type': 'documentation',
                        'name': name,
                        'file': file_path,
                        'doc_string': doc
                    })
                    
        return results

    def get_catalog_stats(self) -> Dict[str, Any]:
        """Get statistics about the code catalog."""
        return {
            'total_files': len(self.file_index),
            'total_classes': sum(len(info.get('classes', [])) for info in self.file_index.values()),
            'total_functions': sum(len(info.get('functions', [])) for info in self.file_index.values()),
            'total_dependencies': len(self.dependencies),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

    async def index_github_repo(
        self,
        repo_url: str,
        branch: str = "main",
        github_token: Optional[str] = None,
        exclude_dirs: List[str] = None,
        analyze_deps: bool = True,
        parse_docs: bool = True,
        deep_scan: bool = False
    ) -> Dict[str, Any]:
        """Index a GitHub repository by cloning it locally first."""
        try:
            self.logger.info(f"Starting to clone repository: {repo_url}")
            
            # Clean and validate the repository URL
            repo_url = repo_url.strip()
            if not repo_url.startswith(('http://', 'https://')):
                repo_url = f"https://github.com/{repo_url}"
            if not repo_url.endswith('.git'):
                repo_url = f"{repo_url}.git"
                
            # Extract repository name from URL
            repo_name = repo_url.rstrip('/').split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            
            self.logger.info(f"Using repository URL: {repo_url}")
            
            # Use fixed directory for this repository
            repo_dir = self.repos_dir / repo_name
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
            repo_dir.mkdir(exist_ok=True)
            
            # Clone repository
            clone_url = repo_url
            if github_token:
                if repo_url.startswith('https://'):
                    clone_url = repo_url.replace('https://', f'https://{github_token}@')
                else:
                    clone_url = repo_url.replace('http://', f'http://{github_token}@')
            
            self.logger.info(f"Cloning to directory: {repo_dir}")
            repo = git.Repo.clone_from(
                clone_url,
                repo_dir,
                branch=branch,
                depth=1
            )
            
            self.logger.info(f"Clone successful, starting analysis")
            
            # Store the original file_index to merge later
            original_index = self.file_index.copy()
            
            # Analyze the repository
            stats = await self.index_directory(
                directory_path=str(repo_dir),
                exclude_dirs=exclude_dirs,
                analyze_deps=analyze_deps,
                parse_docs=parse_docs,
                deep_scan=deep_scan
            )
            
            # Update file paths to be repository-relative
            new_index = {}
            for file_path, file_info in self.file_index.items():
                if str(repo_dir) in file_path:
                    # Convert absolute path to repository-relative path
                    rel_path = os.path.relpath(file_path, repo_dir)
                    new_path = f"{repo_name}/{rel_path}"
                    new_index[new_path] = file_info
                else:
                    new_index[file_path] = file_info
            
            # Restore original files and add new ones with repository-relative paths
            self.file_index = {**original_index, **new_index}
            
            # Save state after successful analysis
            self._save_persistent_state()
            
            return stats
                
        except git.GitCommandError as e:
            self.logger.error(f"Git clone error: {str(e)}")
            raise Exception(f"Error cloning repository: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error indexing GitHub repository: {str(e)}")
            raise Exception(f"Error indexing GitHub repository: {str(e)}")

    def get_state(self) -> Dict[str, Any]:
        """Get serializable state of the catalog."""
        # Create a serializable copy of file_index
        file_index_with_content = {}
        for path, info in self.file_index.items():
            # Convert datetime objects to ISO format strings
            serializable_info = {}
            for key, value in info.items():
                if isinstance(value, datetime):
                    serializable_info[key] = value.isoformat()
                else:
                    serializable_info[key] = value
            
            file_index_with_content[path] = serializable_info
            
        return {
            'file_index': file_index_with_content,
            'module_descriptions': self.module_descriptions,
            'dependencies': self.dependencies,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

    def load_state(self, state: Dict[str, Any]):
        """Load catalog state from dictionary."""
        self.file_index = state.get('file_index', {})
        self.module_descriptions = state.get('module_descriptions', {})
        self.dependencies = state.get('dependencies', {})
        last_update = state.get('last_update')
        self.last_update = datetime.fromisoformat(last_update) if last_update else None

    def delete_repository(self, repo_name: str) -> bool:
        """
        Delete a repository from the catalog and disk.
        
        Args:
            repo_name: Name of the repository to delete
            
        Returns:
            bool: True if repository was deleted successfully
        """
        try:
            # Remove repository directory
            repo_dir = self.repos_dir / repo_name
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
            
            # Remove entries from file index
            new_index = {}
            for file_path, file_info in self.file_index.items():
                # Keep only files that don't belong to this repository
                if not file_path.startswith(f"{repo_name}/"):
                    new_index[file_path] = file_info
            
            self.file_index = new_index
            
            # Clean up dependencies
            new_dependencies = {}
            for file_path, deps in self.dependencies.items():
                if not file_path.startswith(f"{repo_name}/"):
                    new_dependencies[file_path] = [
                        d for d in deps 
                        if not d.startswith(f"{repo_name}/")
                    ]
            
            self.dependencies = new_dependencies
            
            # Save updated state
            self._save_persistent_state()
            
            self.logger.info(f"Successfully deleted repository: {repo_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting repository {repo_name}: {str(e)}")
            return False

    def remove_repository(self, repo_name: str) -> bool:
        """Remove a repository and all its files from the catalog.
        
        Args:
            repo_name: Name of the repository to remove
            
        Returns:
            bool: True if repository was removed, False otherwise
        """
        try:
            # Get all files in this repository
            repo_files = [
                path for path in self.file_index.keys()
                if path.startswith(f"{repo_name}/")
            ]
            
            # Remove all files
            for file_path in repo_files:
                del self.file_index[file_path]
                
            # Remove any dependencies
            self.dependencies = {
                k: v for k, v in self.dependencies.items()
                if not k.startswith(f"{repo_name}/")
            }
            
            # Save the updated state
            self._save_persistent_state()
            
            return True
        except Exception as e:
            logging.error(f"Error removing repository {repo_name}: {str(e)}")
            return False

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files in the catalog with their content and metadata."""
        try:
            files = []
            for path, info in self.file_index.items():
                files.append({
                    "path": path,
                    "content": info.get("content", ""),
                    "size": info.get("size", 0),
                    "last_modified": info.get("last_modified", ""),
                    "type": info.get("type", "unknown"),
                    "imports": info.get("imports", []),
                    "classes": info.get("classes", []),
                    "functions": info.get("functions", []),
                    "doc_strings": info.get("doc_strings", {})
                })
            return files
        except Exception as e:
            self.logger.error(f"Error getting all files: {str(e)}")
            return []