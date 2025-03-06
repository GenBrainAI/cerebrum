import ast
from typing import Dict, List, Optional
from pathlib import Path

class CodeParser:
    """Parses Python code to extract structure and semantics."""
    
    def parse_file(self, file_path: str) -> ast.AST:
        """
        Parse a Python file and extract its AST.
        
        Args:
            file_path (str): Path to the Python file
            
        Returns:
            ast.AST: Abstract Syntax Tree of the file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with path.open('r') as f:
            source = f.read()
            
        return ast.parse(source, filename=file_path)
    
    def extract_classes(self, ast_tree: ast.AST) -> List[Dict[str, any]]:
        """
        Extract class definitions from AST.
        
        Args:
            ast_tree (ast.AST): Abstract Syntax Tree
            
        Returns:
            List[Dict]: List of class definitions with their details
        """
        classes = []
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "methods": self._extract_methods(node),
                    "attributes": self._extract_attributes(node),
                    "bases": [self._get_base_name(base) for base in node.bases],
                    "decorators": self._extract_decorators(node),
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno
                }
                classes.append(class_info)
        return classes
    
    def extract_functions(self, ast_tree: ast.AST) -> List[Dict[str, any]]:
        """
        Extract function definitions from AST.
        
        Args:
            ast_tree (ast.AST): Abstract Syntax Tree
            
        Returns:
            List[Dict]: List of function definitions with their details
        """
        functions = []
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.FunctionDef) and not self._is_method(node):
                function_info = {
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "parameters": self._extract_parameters(node),
                    "returns": self._extract_return_annotation(node),
                    "decorators": self._extract_decorators(node),
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno
                }
                functions.append(function_info)
        return functions
    
    def extract_imports(self, ast_tree: ast.AST) -> List[str]:
        """
        Extract import statements from AST.
        
        Args:
            ast_tree (ast.AST): Abstract Syntax Tree
            
        Returns:
            List[str]: List of imported module names
        """
        imports = []
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
    
    def _extract_methods(self, class_node: ast.ClassDef) -> List[Dict[str, any]]:
        """Extract method definitions from a class."""
        methods = []
        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, ast.FunctionDef):
                method_info = {
                    "name": node.name,
                    "docstring": ast.get_docstring(node),
                    "parameters": self._extract_parameters(node),
                    "returns": self._extract_return_annotation(node),
                    "decorators": self._extract_decorators(node),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno
                }
                methods.append(method_info)
        return methods
    
    def _extract_attributes(self, class_node: ast.ClassDef) -> List[Dict[str, any]]:
        """Extract class attributes from assignments."""
        attributes = []
        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    attr_info = {
                        "name": node.target.id,
                        "annotation": self._get_annotation_name(node.annotation),
                        "lineno": node.lineno
                    }
                    attributes.append(attr_info)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        attr_info = {
                            "name": target.id,
                            "lineno": node.lineno
                        }
                        attributes.append(attr_info)
        return attributes
    
    def _extract_parameters(self, func_node: ast.FunctionDef) -> List[Dict[str, any]]:
        """Extract function parameters with their annotations."""
        parameters = []
        for arg in func_node.args.args:
            param_info = {
                "name": arg.arg,
                "annotation": self._get_annotation_name(arg.annotation)
            }
            parameters.append(param_info)
        return parameters
    
    def _extract_return_annotation(self, func_node: ast.FunctionDef) -> Optional[str]:
        """Extract function return annotation."""
        if func_node.returns:
            return self._get_annotation_name(func_node.returns)
        return None
    
    def _extract_decorators(self, node: ast.AST) -> List[str]:
        """Extract decorator names from a node."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
        return decorators
    
    def _get_annotation_name(self, node: Optional[ast.AST]) -> Optional[str]:
        """Get the string representation of a type annotation."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation_name(node.value)}[{self._get_annotation_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return None
    
    def _get_base_name(self, node: ast.AST) -> str:
        """Get the string representation of a base class."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_base_name(node.value)}.{node.attr}"
        return str(node)
    
    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function definition is a method (defined in a class)."""
        return any(
            isinstance(parent, ast.ClassDef) 
            for parent in ast.walk(node.parent) 
            if hasattr(node, 'parent')
        ) 