import pytest
import ast
from cerebrum.introspection.component_analysis.complexity_analyzer import (
    ComplexityAnalyzer, ComplexityMetrics
)

@pytest.fixture
def complex_code():
    """Fixture providing code with known complexity."""
    return '''
def complex_function(x: int, y: int) -> int:
    """A function with known complexity metrics."""
    result = 0
    
    # Cyclomatic complexity: 5 (base + 3 conditions + 1 loop)
    if x > 0:
        if y > 0:
            result = x + y
        else:
            result = x - y
    
    for i in range(10):
        result += i
        
    return result

def simple_function(x: int) -> int:
    """A simple function."""
    return x + 1
'''

@pytest.fixture
def complex_ast(complex_code):
    """Fixture providing AST of complex code."""
    return ast.parse(complex_code)

class TestComplexityAnalyzer:
    def setup_method(self):
        self.analyzer = ComplexityAnalyzer()
        
    def test_calculate_metrics(self, complex_ast):
        """Test calculating all complexity metrics."""
        metrics = self.analyzer.calculate_metrics(complex_ast)
        assert isinstance(metrics, dict)
        assert "cyclomatic_complexity" in metrics
        assert "cognitive_complexity" in metrics
        assert "maintainability_index" in metrics
        assert "halstead_metrics" in metrics
        
    def test_calculate_cyclomatic_complexity(self, complex_ast):
        """Test calculating cyclomatic complexity."""
        complexity = self.analyzer.calculate_cyclomatic_complexity(complex_ast)
        assert complexity > 1  # Base complexity + at least some conditions
        
        # Test individual functions
        for node in ast.walk(complex_ast):
            if isinstance(node, ast.FunctionDef):
                if node.name == "complex_function":
                    func_complexity = self.analyzer.calculate_cyclomatic_complexity(node)
                    assert func_complexity == 5  # Base + 3 conditions + 1 loop
                elif node.name == "simple_function":
                    func_complexity = self.analyzer.calculate_cyclomatic_complexity(node)
                    assert func_complexity == 1  # Just base complexity
                    
    def test_calculate_cognitive_complexity(self, complex_ast):
        """Test calculating cognitive complexity."""
        complexity = self.analyzer.calculate_cognitive_complexity(complex_ast)
        assert complexity > 0
        
        # Test individual functions
        for node in ast.walk(complex_ast):
            if isinstance(node, ast.FunctionDef):
                if node.name == "complex_function":
                    func_complexity = self.analyzer.calculate_cognitive_complexity(node)
                    assert func_complexity > 0  # Should have significant complexity
                elif node.name == "simple_function":
                    func_complexity = self.analyzer.calculate_cognitive_complexity(node)
                    assert func_complexity == 0  # No cognitive complexity
                    
    def test_calculate_maintainability_index(self, complex_ast):
        """Test calculating maintainability index."""
        mi = self.analyzer.calculate_maintainability_index(complex_ast)
        assert 0 <= mi <= 100  # MI is normalized to 0-100
        
    def test_calculate_halstead_metrics(self, complex_ast):
        """Test calculating Halstead metrics."""
        metrics = self.analyzer.calculate_halstead_metrics(complex_ast)
        assert isinstance(metrics, dict)
        assert "volume" in metrics
        assert "difficulty" in metrics
        assert "effort" in metrics
        assert "time" in metrics
        assert "bugs" in metrics
        
        # All metrics should be non-negative
        assert all(v >= 0 for v in metrics.values())
        
    def test_identify_complex_sections(self, complex_ast):
        """Test identifying complex sections of code."""
        sections = self.analyzer.identify_complex_sections(complex_ast, threshold=1)
        assert isinstance(sections, list)
        
        # Should identify complex_function as complex
        complex_sections = [s for s in sections if s["name"] == "complex_function"]
        assert len(complex_sections) == 1
        assert isinstance(complex_sections[0]["metrics"], ComplexityMetrics)
        
        # simple_function should not be identified as complex
        simple_sections = [s for s in sections if s["name"] == "simple_function"]
        assert len(simple_sections) == 0
        
    def test_cognitive_complexity_recursive(self, complex_ast):
        """Test recursive cognitive complexity calculation."""
        # Test on a nested structure
        for node in ast.walk(complex_ast):
            if isinstance(node, ast.FunctionDef) and node.name == "complex_function":
                complexity = self.analyzer._cognitive_complexity_recursive(node, 0)
                assert complexity > 0  # Should have some complexity due to nesting
                
    def test_count_lines_of_code(self, complex_ast):
        """Test counting lines of code."""
        for node in ast.walk(complex_ast):
            if isinstance(node, ast.FunctionDef):
                loc = self.analyzer._count_lines_of_code(node)
                if node.name == "complex_function":
                    assert loc > 1  # Should have multiple lines
                elif node.name == "simple_function":
                    assert loc > 0  # Should have at least one line
                    
    def test_count_comments(self, complex_ast):
        """Test counting comments."""
        comments = self.analyzer._count_comments(complex_ast)
        assert isinstance(comments, int)
        assert comments >= 0 