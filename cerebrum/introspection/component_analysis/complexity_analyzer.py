import ast
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class ComplexityMetrics:
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: float
    halstead_metrics: Dict[str, float]

class ComplexityAnalyzer:
    """Analyzes code complexity metrics."""
    
    def calculate_metrics(self, ast_tree: ast.AST) -> Dict[str, float]:
        """
        Calculate various complexity metrics for the code.
        
        Args:
            ast_tree (ast.AST): Abstract Syntax Tree
            
        Returns:
            Dict[str, float]: Dictionary of complexity metrics
        """
        metrics = {
            "cyclomatic_complexity": self.calculate_cyclomatic_complexity(ast_tree),
            "cognitive_complexity": self.calculate_cognitive_complexity(ast_tree),
            "maintainability_index": self.calculate_maintainability_index(ast_tree),
            "halstead_metrics": self.calculate_halstead_metrics(ast_tree)
        }
        return metrics
    
    def calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Calculate McCabe's cyclomatic complexity.
        
        Args:
            node (ast.AST): AST node to analyze
            
        Returns:
            int: Cyclomatic complexity score
        """
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            # Control flow statements increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Boolean operations (and, or) increase complexity
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
        return complexity
    
    def calculate_cognitive_complexity(self, node: ast.AST) -> int:
        """
        Calculate cognitive complexity.
        
        Args:
            node (ast.AST): AST node to analyze
            
        Returns:
            int: Cognitive complexity score
        """
        return self._cognitive_complexity_recursive(node, nesting_level=0)
    
    def calculate_maintainability_index(self, ast_tree: ast.AST) -> float:
        """
        Calculate maintainability index.
        
        Args:
            ast_tree (ast.AST): AST to analyze
            
        Returns:
            float: Maintainability index score
        """
        # Calculate component metrics
        halstead_volume = self.calculate_halstead_metrics(ast_tree)["volume"]
        cyclomatic = self.calculate_cyclomatic_complexity(ast_tree)
        
        # Count lines of code and comments
        loc = self._count_lines_of_code(ast_tree)
        comments = self._count_comments(ast_tree)
        
        # Calculate maintainability index using the standard formula
        mi = 171 - 5.2 * halstead_volume - 0.23 * cyclomatic - 16.2 * loc
        mi = max(0, min(100, mi))  # Normalize to 0-100 scale
        
        return mi
    
    def calculate_halstead_metrics(self, node: ast.AST) -> Dict[str, float]:
        """
        Calculate Halstead complexity metrics.
        
        Args:
            node (ast.AST): AST node to analyze
            
        Returns:
            Dict[str, float]: Halstead metrics
        """
        # Count operators and operands
        operators = set()
        operands = set()
        total_operators = 0
        total_operands = 0
        
        for child in ast.walk(node):
            if isinstance(child, ast.operator):
                operators.add(type(child).__name__)
                total_operators += 1
            elif isinstance(child, (ast.Name, ast.Constant)):
                operands.add(ast.dump(child))
                total_operands += 1
        
        # Calculate Halstead metrics
        n1 = len(operators)  # Unique operators
        n2 = len(operands)   # Unique operands
        N1 = total_operators # Total operators
        N2 = total_operands  # Total operands
        
        # Avoid division by zero
        if n1 == 0 or n2 == 0:
            return {
                "volume": 0,
                "difficulty": 0,
                "effort": 0,
                "time": 0,
                "bugs": 0
            }
        
        # Calculate metrics
        vocabulary = n1 + n2
        length = N1 + N2
        volume = length * (vocabulary.bit_length())
        difficulty = (n1 * N2) / (2 * n2)
        effort = difficulty * volume
        time = effort / 18  # Estimated time in seconds
        bugs = volume / 3000  # Estimated number of bugs
        
        return {
            "volume": volume,
            "difficulty": difficulty,
            "effort": effort,
            "time": time,
            "bugs": bugs
        }
    
    def identify_complex_sections(
        self, ast_tree: ast.AST, threshold: int = 10
    ) -> List[Dict[str, any]]:
        """
        Identify sections exceeding complexity threshold.
        
        Args:
            ast_tree (ast.AST): AST to analyze
            threshold (int): Complexity threshold
            
        Returns:
            List[Dict]: Complex sections with their metrics
        """
        complex_sections = []
        
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                metrics = ComplexityMetrics(
                    cyclomatic_complexity=self.calculate_cyclomatic_complexity(node),
                    cognitive_complexity=self.calculate_cognitive_complexity(node),
                    maintainability_index=self.calculate_maintainability_index(node),
                    halstead_metrics=self.calculate_halstead_metrics(node)
                )
                
                if (metrics.cyclomatic_complexity > threshold or 
                    metrics.cognitive_complexity > threshold):
                    complex_sections.append({
                        "name": node.name,
                        "type": type(node).__name__,
                        "lineno": node.lineno,
                        "end_lineno": node.end_lineno,
                        "metrics": metrics
                    })
        
        return complex_sections
    
    def _cognitive_complexity_recursive(
        self, node: ast.AST, nesting_level: int
    ) -> int:
        """Calculate cognitive complexity recursively."""
        complexity = 0
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                # Base cost for control flow
                complexity += 1 + nesting_level
                # Recursive cost for nested structures
                complexity += self._cognitive_complexity_recursive(
                    child, nesting_level + 1
                )
            elif isinstance(child, ast.BoolOp):
                # Cost for boolean operations
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.Try, ast.ExceptHandler)):
                complexity += 1 + nesting_level
            else:
                complexity += self._cognitive_complexity_recursive(
                    child, nesting_level
                )
                
        return complexity
    
    def _count_lines_of_code(self, node: ast.AST) -> int:
        """Count non-empty, non-comment lines of code."""
        if not hasattr(node, 'end_lineno') or not hasattr(node, 'lineno'):
            return 0
        return node.end_lineno - node.lineno + 1
    
    def _count_comments(self, node: ast.AST) -> int:
        """Count number of comment lines."""
        # This is a simplified implementation
        # A more accurate implementation would need source code access
        return sum(
            1 for child in ast.walk(node) 
            if isinstance(child, ast.Expr) and 
            isinstance(child.value, ast.Str)
        ) 