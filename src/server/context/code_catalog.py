from typing import Dict, List, Optional, Any
import ast
import os
import logging
from datetime import datetime

class CodeCatalog:
    """Maintains a high-level catalog of code files and their relationships."""
    
    def __init__(self):
        """Initialize the code catalog."""
        # Initialize all required attributes
        self.file_index: Dict[str, Dict[str, Any]] = {}
        self.module_descriptions: Dict[str, str] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.last_update: Optional[datetime] = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def index_directory(self, directory_path: str, exclude_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a catalog of all code files in the directory.
        
        Args:
            directory_path: Path to the directory to index
            exclude_dirs: List of directory names to exclude
            
        Returns:
            Dictionary containing indexing statistics
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        exclude_dirs = exclude_dirs or ['venv', '__pycache__', '.git', 'node_modules']

        try:
            for root, dirs, files in os.walk(directory_path):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            await self._catalog_file(file_path)
                            stats["processed"] += 1
                        except Exception as e:
                            self.logger.error(f"Error cataloging file {file_path}: {str(e)}")
                            stats["failed"] += 1
                            continue

            self.last_update = datetime.now()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error indexing directory: {str(e)}")
            raise

    async def _catalog_file(self, file_path: str) -> None:
        """
        Analyze and catalog a single Python file.
        
        Args:
            file_path: Path to the Python file to catalog
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_stats = {
                'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'size': os.path.getsize(file_path),
                'type': 'python',
                'imports': self._extract_imports(content),
                'classes': self._extract_classes(content),
                'functions': self._extract_functions(content),
                'doc_strings': self._extract_docstrings(content),
                'dependencies': []
            }

            # Update the file index
            self.file_index[file_path] = file_stats
            
            # Update dependencies
            self._update_dependencies(file_path, file_stats['imports'])
            
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