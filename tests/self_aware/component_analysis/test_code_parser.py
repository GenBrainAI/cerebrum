import pytest
from cerebrum.introspection.component_analysis.code_parser import CodeParser

@pytest.mark.asyncio
class TestCodeParser:
    def setup_method(self):
        self.parser = CodeParser()
        
    def test_parse_file(self, temp_python_file):
        """Test parsing a Python file."""
        ast_tree = self.parser.parse_file(temp_python_file)
        assert ast_tree is not None
        
    def test_parse_file_not_found(self):
        """Test parsing a non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("nonexistent.py")
            
    def test_extract_classes(self, sample_ast):
        """Test extracting class definitions."""
        classes = self.parser.extract_classes(sample_ast)
        assert len(classes) == 1
        test_class = classes[0]
        assert test_class["name"] == "TestClass"
        assert test_class["docstring"] == "Test class docstring."
        assert len(test_class["methods"]) == 2  # __init__ and test_method
        assert len(test_class["attributes"]) == 1  # value
        
    def test_extract_functions(self, sample_ast):
        """Test extracting function definitions."""
        functions = self.parser.extract_functions(sample_ast)
        assert len(functions) == 1
        test_func = functions[0]
        assert test_func["name"] == "test_function"
        assert test_func["docstring"] == "Test function docstring."
        assert len(test_func["parameters"]) == 2
        
    def test_extract_imports(self, sample_ast):
        """Test extracting import statements."""
        imports = self.parser.extract_imports(sample_ast)
        assert isinstance(imports, list)
        
    def test_extract_methods(self, sample_ast):
        """Test extracting methods from a class."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).ClassDef):
                methods = self.parser._extract_methods(node)
                assert len(methods) == 2
                assert any(m["name"] == "__init__" for m in methods)
                assert any(m["name"] == "test_method" for m in methods)
                
    def test_extract_attributes(self, sample_ast):
        """Test extracting attributes from a class."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).ClassDef):
                attrs = self.parser._extract_attributes(node)
                assert len(attrs) == 1
                assert attrs[0]["name"] == "value"
                
    def test_extract_parameters(self, sample_ast):
        """Test extracting function parameters."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).FunctionDef):
                params = self.parser._extract_parameters(node)
                assert len(params) == 2
                assert all(p["annotation"] == "int" for p in params)
                
    def test_extract_return_annotation(self, sample_ast):
        """Test extracting return type annotations."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).FunctionDef):
                ret_type = self.parser._extract_return_annotation(node)
                assert ret_type == "int"
                
    def test_extract_decorators(self, sample_ast):
        """Test extracting decorators."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).FunctionDef):
                decorators = self.parser._extract_decorators(node)
                assert isinstance(decorators, list)
                
    def test_get_annotation_name(self, sample_ast):
        """Test getting annotation names."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).FunctionDef):
                for arg in node.args.args:
                    name = self.parser._get_annotation_name(arg.annotation)
                    assert name == "int"
                    
    def test_get_base_name(self, sample_ast):
        """Test getting base class names."""
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).ClassDef):
                for base in node.bases:
                    name = self.parser._get_base_name(base)
                    assert isinstance(name, str)
                    
    def test_is_method(self, sample_ast):
        """Test checking if a function is a method."""
        method_found = False
        function_found = False
        
        for node in sample_ast.body:
            if isinstance(node, type(sample_ast).ClassDef):
                for subnode in node.body:
                    if isinstance(subnode, type(sample_ast).FunctionDef):
                        method_found = True
                        assert self.parser._is_method(subnode)
            elif isinstance(node, type(sample_ast).FunctionDef):
                function_found = True
                assert not self.parser._is_method(node)
                
        assert method_found and function_found 