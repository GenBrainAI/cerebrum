import pytest
from cerebrum.introspection.component_analysis.analyzer import (
    ComponentAnalyzer, ComponentAnalysisResult
)

@pytest.mark.asyncio
class TestComponentAnalyzer:
    def setup_method(self):
        self.analyzer = ComponentAnalyzer(mock_knowledge_system)
        
    async def test_analyze_component(self, temp_python_file, mock_knowledge_system):
        """Test analyzing a component."""
        result = await self.analyzer.analyze_component(temp_python_file)
        
        assert isinstance(result, ComponentAnalysisResult)
        assert len(result.class_definitions) > 0
        assert len(result.function_definitions) > 0
        assert isinstance(result.imports, list)
        assert isinstance(result.complexity_metrics, dict)
        assert isinstance(result.documentation_coverage, float)
        
        # Check caching
        cached_result = await self.analyzer.analyze_component(temp_python_file)
        assert cached_result is result
        
        # Check knowledge system storage
        assert f"analysis_{temp_python_file}" in mock_knowledge_system.stored_data
        
    async def test_map_dependencies(self, temp_python_file, mock_knowledge_system):
        """Test mapping component dependencies."""
        dep_map = await self.analyzer.map_dependencies(temp_python_file)
        
        assert isinstance(dep_map, dict)
        assert "direct_imports" in dep_map
        assert "indirect_imports" in dep_map
        assert "dependents" in dep_map
        assert "circular_dependencies" in dep_map
        assert "dependency_graph" in dep_map
        
        # Check knowledge system storage
        assert f"deps_{temp_python_file}" in mock_knowledge_system.stored_data
        
    async def test_identify_optimization_opportunities(
        self, temp_python_file, mock_knowledge_system
    ):
        """Test identifying optimization opportunities."""
        opportunities = await self.analyzer.identify_optimization_opportunities(
            temp_python_file
        )
        
        assert isinstance(opportunities, list)
        
        # Check knowledge system storage
        assert f"opps_{temp_python_file}" in mock_knowledge_system.stored_data
        
    async def test_generate_component_documentation(
        self, temp_python_file, mock_knowledge_system
    ):
        """Test generating component documentation."""
        docs = await self.analyzer.generate_component_documentation(
            temp_python_file
        )
        
        assert isinstance(docs, dict)
        assert "overview" in docs
        assert "class_documentation" in docs
        assert "function_documentation" in docs
        assert "usage_examples" in docs
        assert "dependency_diagram" in docs
        
        # Check knowledge system storage
        assert f"docs_{temp_python_file}" in mock_knowledge_system.stored_data
        
    def test_calculate_documentation_coverage(self):
        """Test calculating documentation coverage."""
        classes = [
            {"docstring": "Test"},
            {"docstring": None}
        ]
        functions = [
            {"docstring": "Test"},
            {"docstring": "Test"},
            {"docstring": None}
        ]
        
        coverage = self.analyzer._calculate_documentation_coverage(
            classes, functions
        )
        assert coverage == 0.6  # 3 documented out of 5 total
        
        # Test empty case
        coverage = self.analyzer._calculate_documentation_coverage([], [])
        assert coverage == 1.0
        
    async def test_map_indirect_dependencies(self):
        """Test mapping indirect dependencies."""
        direct_imports = ["module1", "module2"]
        indirect = await self.analyzer._map_indirect_dependencies(direct_imports)
        
        assert isinstance(indirect, list)
        
    def test_identify_redundant_code(self):
        """Test identifying redundant code."""
        analysis = ComponentAnalysisResult(
            class_definitions=[],
            function_definitions=[],
            imports=[],
            complexity_metrics={},
            documentation_coverage=1.0
        )
        
        redundant = self.analyzer._identify_redundant_code(analysis)
        assert isinstance(redundant, list)
        
    def test_identify_complexity_issues(self):
        """Test identifying complexity issues."""
        analysis = ComponentAnalysisResult(
            class_definitions=[],
            function_definitions=[],
            imports=[],
            complexity_metrics={
                "cyclomatic_complexity": 10,
                "cognitive_complexity": 15
            },
            documentation_coverage=1.0
        )
        
        issues = self.analyzer._identify_complexity_issues(analysis)
        assert isinstance(issues, list)
        
    async def test_identify_coupling_issues(self):
        """Test identifying coupling issues."""
        analysis = ComponentAnalysisResult(
            class_definitions=[],
            function_definitions=[],
            imports=["module1", "module2"],
            complexity_metrics={},
            documentation_coverage=1.0
        )
        
        issues = await self.analyzer._identify_coupling_issues(
            "test.py", analysis
        )
        assert isinstance(issues, list)
        
    def test_identify_documentation_gaps(self):
        """Test identifying documentation gaps."""
        analysis = ComponentAnalysisResult(
            class_definitions=[{"name": "Test", "docstring": None}],
            function_definitions=[{"name": "test", "docstring": None}],
            imports=[],
            complexity_metrics={},
            documentation_coverage=0.0
        )
        
        gaps = self.analyzer._identify_documentation_gaps(analysis)
        assert isinstance(gaps, list)
        
    def test_generate_component_overview(self):
        """Test generating component overview."""
        analysis = ComponentAnalysisResult(
            class_definitions=[{"name": "Test", "docstring": "Test class"}],
            function_definitions=[{"name": "test", "docstring": "Test function"}],
            imports=[],
            complexity_metrics={},
            documentation_coverage=1.0
        )
        
        overview = self.analyzer._generate_component_overview(analysis)
        assert isinstance(overview, str)
        
    def test_generate_class_documentation(self):
        """Test generating class documentation."""
        classes = [
            {
                "name": "Test",
                "docstring": "Test class",
                "methods": [
                    {
                        "name": "test_method",
                        "docstring": "Test method"
                    }
                ]
            }
        ]
        
        docs = self.analyzer._generate_class_documentation(classes)
        assert isinstance(docs, dict)
        assert "Test" in docs
        
    def test_generate_function_documentation(self):
        """Test generating function documentation."""
        functions = [
            {
                "name": "test",
                "docstring": "Test function",
                "parameters": [{"name": "x", "annotation": "int"}],
                "returns": "int"
            }
        ]
        
        docs = self.analyzer._generate_function_documentation(functions)
        assert isinstance(docs, dict)
        assert "test" in docs
        
    def test_generate_usage_examples(self):
        """Test generating usage examples."""
        classes = [
            {
                "name": "Test",
                "methods": [
                    {
                        "name": "test_method",
                        "parameters": [{"name": "x", "annotation": "int"}],
                        "returns": "int"
                    }
                ]
            }
        ]
        functions = [
            {
                "name": "test",
                "parameters": [{"name": "x", "annotation": "int"}],
                "returns": "int"
            }
        ]
        
        examples = self.analyzer._generate_usage_examples(classes, functions)
        assert isinstance(examples, list)
        assert len(examples) > 0 