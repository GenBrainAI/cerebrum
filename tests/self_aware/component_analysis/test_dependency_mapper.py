import pytest
import ast
import tempfile
import os
from pathlib import Path
from src.server.introspection.component_analysis.dependency_mapper import (
    DependencyMapper, DependencyNode
)

@pytest.fixture
def dependency_code():
    """Fixture providing code with dependencies."""
    return '''
import os
import sys
from pathlib import Path
from typing import List, Dict

from my_package.module1 import Class1
from my_package.module2 import function1
from .local_module import LocalClass

class TestClass:
    def __init__(self):
        self.path = Path('.')
        
    def test_method(self):
        return os.path.join(self.path, 'test')
'''

@pytest.fixture
def dependency_files(dependency_code):
    """Fixture providing temporary Python files with dependencies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create main module
        main_path = Path(temp_dir) / "main.py"
        with open(main_path, 'w') as f:
            f.write(dependency_code)
            
        # Create dependent module
        dep_path = Path(temp_dir) / "dependent.py"
        with open(dep_path, 'w') as f:
            f.write('''
from main import TestClass

def use_test_class():
    return TestClass()
''')
            
        yield temp_dir, main_path, dep_path

class TestDependencyMapper:
    def setup_method(self):
        self.mapper = DependencyMapper()
        
    def test_map_direct_dependencies(self, dependency_code):
        """Test mapping direct dependencies from imports."""
        ast_tree = ast.parse(dependency_code)
        imports = [
            name.name for node in ast.walk(ast_tree) 
            if isinstance(node, ast.Import)
            for name in node.names
        ]
        
        deps = self.mapper.map_direct_dependencies(imports)
        assert isinstance(deps, list)
        assert "os" in deps
        assert "sys" in deps
        
    def test_find_dependents(self, dependency_files):
        """Test finding components that depend on a given component."""
        temp_dir, main_path, dep_path = dependency_files
        
        dependents = self.mapper.find_dependents(
            str(main_path), str(Path(temp_dir))
        )
        assert isinstance(dependents, list)
        assert any("dependent.py" in d for d in dependents)
        
    def test_detect_circular_dependencies(self):
        """Test detecting circular dependencies."""
        direct_deps = ["module1", "module2"]
        indirect_deps = ["module2.submodule", "module1.submodule"]
        
        cycles = self.mapper.detect_circular_dependencies(
            direct_deps, indirect_deps
        )
        assert isinstance(cycles, list)
        
    def test_generate_dependency_graph(self):
        """Test generating dependency graph visualization."""
        direct_deps = ["module1", "module2"]
        indirect_deps = ["module2.submodule", "module1.submodule"]
        dependents = ["dependent1", "dependent2"]
        
        graph = self.mapper.generate_dependency_graph(
            direct_deps, indirect_deps, dependents
        )
        
        assert isinstance(graph, dict)
        assert "nodes" in graph
        assert "edges" in graph
        
        # Check nodes
        assert len(graph["nodes"]) == len(direct_deps) + len(indirect_deps) + len(dependents) + 1
        assert any(n["type"] == "component" for n in graph["nodes"])
        assert any(n["type"] == "direct" for n in graph["nodes"])
        assert any(n["type"] == "indirect" for n in graph["nodes"])
        assert any(n["type"] == "dependent" for n in graph["nodes"])
        
        # Check edges
        assert isinstance(graph["edges"], list)
        assert len(graph["edges"]) > 0
        
    def test_extract_imports(self, dependency_code):
        """Test extracting imports from AST."""
        ast_tree = ast.parse(dependency_code)
        imports = self.mapper._extract_imports(ast_tree)
        
        assert isinstance(imports, set)
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "my_package.module1" in imports
        assert "my_package.module2" in imports
        
    def test_normalize_module_name(self):
        """Test normalizing module names."""
        assert self.mapper._normalize_module_name("path/to/module.py") == "path.to.module"
        assert self.mapper._normalize_module_name("module.py") == "module"
        assert self.mapper._normalize_module_name("path.to.module") == "path.to.module" 