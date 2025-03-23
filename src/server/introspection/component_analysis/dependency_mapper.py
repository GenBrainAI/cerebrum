import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx
from dataclasses import dataclass

@dataclass
class DependencyNode:
    name: str
    path: str
    type: str  # 'module', 'class', or 'function'
    imports: List[str]

class DependencyMapper:
    """Maps dependencies between components."""
    
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.module_cache: Dict[str, DependencyNode] = {}
    
    def map_direct_dependencies(self, imports: List[str]) -> List[str]:
        """
        Map direct dependencies from import statements.
        
        Args:
            imports (List[str]): List of import statements
            
        Returns:
            List[str]: List of direct dependencies
        """
        direct_deps = []
        for imp in imports:
            # Handle relative imports
            if imp.startswith('.'):
                continue
                
            # Handle package imports
            parts = imp.split('.')
            for i in range(len(parts)):
                module_path = '.'.join(parts[:i+1])
                direct_deps.append(module_path)
                
        return list(set(direct_deps))
    
    def find_dependents(
        self, component_path: str, codebase_path: str
    ) -> List[str]:
        """
        Find components that depend on the given component.
        
        Args:
            component_path (str): Path to the component
            codebase_path (str): Root path of the codebase
            
        Returns:
            List[str]: List of dependent components
        """
        dependents = []
        codebase = Path(codebase_path)
        target = Path(component_path).relative_to(codebase)
        target_module = str(target).replace('/', '.').replace('.py', '')
        
        # Search through all Python files in the codebase
        for file_path in codebase.rglob('*.py'):
            if file_path == Path(component_path):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    tree = ast.parse(f.read(), filename=str(file_path))
                    
                imports = self._extract_imports(tree)
                if target_module in imports:
                    dependents.append(str(file_path.relative_to(codebase)))
            except Exception:
                continue
                
        return dependents
    
    def detect_circular_dependencies(
        self, direct_deps: List[str], indirect_deps: List[str]
    ) -> List[List[str]]:
        """
        Detect circular dependencies in the dependency map.
        
        Args:
            direct_deps (List[str]): Direct dependencies
            indirect_deps (List[str]): Indirect dependencies
            
        Returns:
            List[List[str]]: List of circular dependency chains
        """
        # Build dependency graph
        graph = nx.DiGraph()
        
        # Add direct dependencies
        for dep in direct_deps:
            graph.add_edge("root", dep)
            
        # Add indirect dependencies
        for dep in indirect_deps:
            parts = dep.split('.')
            for i in range(len(parts)-1):
                parent = '.'.join(parts[:i+1])
                child = '.'.join(parts[:i+2])
                graph.add_edge(parent, child)
                
        # Find cycles
        try:
            cycles = list(nx.simple_cycles(graph))
            return [list(cycle) for cycle in cycles]
        except nx.NetworkXNoCycle:
            return []
    
    def generate_dependency_graph(
        self, direct_deps: List[str], 
        indirect_deps: List[str], 
        dependents: List[str]
    ) -> Dict[str, any]:
        """
        Generate a visual representation of dependencies.
        
        Args:
            direct_deps (List[str]): Direct dependencies
            indirect_deps (List[str]): Indirect dependencies
            dependents (List[str]): Components that depend on this one
            
        Returns:
            Dict: Graph representation data
        """
        graph = nx.DiGraph()
        
        # Add nodes
        graph.add_node("root", type="component")
        for dep in direct_deps:
            graph.add_node(dep, type="direct")
        for dep in indirect_deps:
            graph.add_node(dep, type="indirect")
        for dep in dependents:
            graph.add_node(dep, type="dependent")
            
        # Add edges
        for dep in direct_deps:
            graph.add_edge("root", dep)
        for dep in indirect_deps:
            parts = dep.split('.')
            for i in range(len(parts)-1):
                parent = '.'.join(parts[:i+1])
                child = '.'.join(parts[:i+2])
                if parent in graph and child in graph:
                    graph.add_edge(parent, child)
        for dep in dependents:
            graph.add_edge(dep, "root")
            
        # Convert to dictionary representation
        return {
            "nodes": [
                {
                    "id": node,
                    "type": data["type"],
                    "label": node.split('.')[-1]
                }
                for node, data in graph.nodes(data=True)
            ],
            "edges": [
                {
                    "source": source,
                    "target": target
                }
                for source, target in graph.edges()
            ]
        }
    
    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract all imports from an AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports
    
    def _normalize_module_name(self, module_name: str) -> str:
        """Normalize a module name for consistent comparison."""
        return module_name.replace('/', '.').replace('.py', '') 