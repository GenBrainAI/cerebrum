import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, patch

from src.server.self_modification.code_modification_engine import CodeModification, CodeModificationEngine
from src.server.self_modification.modification_validator import ModificationValidator, StaticAnalyzer, TestRunner
from src.server.self_modification.modification_version_control import ModificationVersionControl


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    return Mock()


@pytest.fixture
def mock_validation_engine():
    """Create a mock validation engine."""
    mock = Mock()
    async def mock_validate_code(*args, **kwargs):
        return {"passed": True, "syntax_check": {"passed": True}}
    mock.validate_code = mock_validate_code
    return mock


@pytest.fixture
def sample_code():
    """Return a sample Python code."""
    return '''
def hello_world():
    """Hello world function."""
    print("Hello, world!")
'''


@pytest.fixture
def modified_code():
    """Return a modified version of the sample code."""
    return '''
def hello_world():
    """Hello world function with name."""
    name = "World"
    print(f"Hello, {name}!")
'''


class TestCodeModification:
    def test_code_modification_creation(self):
        """Test the creation of a CodeModification instance."""
        modification = CodeModification(
            target_component="test.py",
            original_code="def test(): pass",
            modified_code="def test(): return True",
            modification_goal="Add return value",
            author="test"
        )
        
        assert modification.target_component == "test.py"
        assert modification.original_code == "def test(): pass"
        assert modification.modified_code == "def test(): return True"
        assert modification.modification_goal == "Add return value"
        assert modification.author == "test"
        assert modification.status == "proposed"
    
    def test_code_modification_to_dict(self):
        """Test the to_dict method of CodeModification."""
        modification = CodeModification(
            target_component="test.py",
            original_code="def test(): pass",
            modified_code="def test(): return True",
            modification_goal="Add return value",
            author="test"
        )
        
        modification_dict = modification.to_dict()
        
        assert modification_dict["target_component"] == "test.py"
        assert modification_dict["original_code"] == "def test(): pass"
        assert modification_dict["modified_code"] == "def test(): return True"
        assert modification_dict["modification_goal"] == "Add return value"
        assert modification_dict["author"] == "test"
        assert modification_dict["status"] == "proposed"
    
    def test_code_modification_from_dict(self):
        """Test the from_dict method of CodeModification."""
        modification_dict = {
            "id": "12345",
            "target_component": "test.py",
            "original_code": "def test(): pass",
            "modified_code": "def test(): return True",
            "modification_goal": "Add return value",
            "author": "test",
            "status": "validated",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T01:00:00",
            "metadata": {"key": "value"}
        }
        
        modification = CodeModification.from_dict(modification_dict)
        
        assert modification.id == "12345"
        assert modification.target_component == "test.py"
        assert modification.original_code == "def test(): pass"
        assert modification.modified_code == "def test(): return True"
        assert modification.modification_goal == "Add return value"
        assert modification.author == "test"
        assert modification.status == "validated"
        assert modification.created_at == "2023-01-01T00:00:00"
        assert modification.updated_at == "2023-01-01T01:00:00"
        assert modification.metadata == {"key": "value"}
    
    def test_code_modification_update_status(self):
        """Test the update_status method of CodeModification."""
        modification = CodeModification(
            target_component="test.py",
            original_code="def test(): pass"
        )
        
        original_updated_at = modification.updated_at
        modification.update_status("validated")
        
        assert modification.status == "validated"
        assert modification.updated_at != original_updated_at


class TestCodeModificationEngine:
    @pytest.mark.asyncio
    async def test_generate_code_modification(self, mock_knowledge_system, mock_validation_engine, sample_code, temp_dir):
        """Test generating a code modification."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write(sample_code)
        
        engine = CodeModificationEngine(mock_knowledge_system, mock_validation_engine)
        
        modification = await engine.generate_code_modification(
            target_component=test_file,
            modification_goal="Add name parameter"
        )
        
        assert modification.target_component == test_file
        assert modification.original_code == sample_code
        assert modification.modification_goal == "Add name parameter"
        assert modification.modified_code is not None
        assert "# Modified for: Add name parameter" in modification.modified_code
    
    @pytest.mark.asyncio
    async def test_validate_modification(self, mock_knowledge_system, mock_validation_engine, sample_code, temp_dir):
        """Test validating a code modification."""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write(sample_code)
        
        engine = CodeModificationEngine(mock_knowledge_system, mock_validation_engine)
        
        modification = CodeModification(
            target_component=test_file,
            original_code=sample_code,
            modified_code=sample_code + "\n# Added a comment",
            modification_goal="Add comment"
        )
        
        result = await engine.validate_modification(modification)
        
        assert result.get("passed") is True
        assert modification.status == "validated"
    
    @pytest.mark.asyncio
    async def test_apply_modification(self, mock_knowledge_system, mock_validation_engine, sample_code, modified_code, temp_dir):
        """Test applying a code modification."""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write(sample_code)
        
        engine = CodeModificationEngine(mock_knowledge_system, mock_validation_engine)
        
        modification = CodeModification(
            target_component=test_file,
            original_code=sample_code,
            modified_code=modified_code,
            modification_goal="Update function"
        )
        
        # Set status to validated
        modification.update_status("validated")
        
        result = await engine.apply_modification(modification)
        
        assert result.get("success") is True
        assert modification.status == "applied"
        
        # Verify the file was modified
        with open(test_file, "r") as f:
            content = f.read()
        
        assert content == modified_code
    
    @pytest.mark.asyncio
    async def test_rollback_modification(self, mock_knowledge_system, mock_validation_engine, sample_code, modified_code, temp_dir):
        """Test rolling back a code modification."""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write(modified_code)  # Start with the modified code
        
        engine = CodeModificationEngine(mock_knowledge_system, mock_validation_engine)
        
        modification = CodeModification(
            target_component=test_file,
            original_code=sample_code,  # Original is the sample code
            modified_code=modified_code,
            modification_goal="Update function"
        )
        
        # Set status to applied
        modification.update_status("applied")
        
        result = await engine.rollback_modification(modification)
        
        assert result.get("success") is True
        assert modification.status == "reverted"
        
        # Verify the file was restored to original
        with open(test_file, "r") as f:
            content = f.read()
        
        assert content == sample_code


class TestStaticAnalyzer:
    @pytest.mark.asyncio
    async def test_parse_syntax_valid(self):
        """Test parsing valid syntax."""
        analyzer = StaticAnalyzer()
        result = await analyzer.parse_syntax("def test(): pass")
        
        assert result.get("has_syntax_errors") is False
        assert len(result.get("errors", [])) == 0
    
    @pytest.mark.asyncio
    async def test_parse_syntax_invalid(self):
        """Test parsing invalid syntax."""
        analyzer = StaticAnalyzer()
        result = await analyzer.parse_syntax("def test() pass")  # Missing colon
        
        assert result.get("has_syntax_errors") is True
        assert len(result.get("errors", [])) > 0
    
    @pytest.mark.asyncio
    async def test_check_antipatterns(self):
        """Test checking for antipatterns."""
        analyzer = StaticAnalyzer()
        code = """
def test():
    import *  # Wildcard import
    a = 1; b = 2  # Multiple statements
    very_long_line = "This is a very long line that exceeds the recommended line length in PEP 8 which is 79 characters"
"""
        result = await analyzer.check_antipatterns(code)
        
        assert result.get("has_antipatterns") is True
        assert len(result.get("issues", [])) > 0


class TestModificationValidator:
    @pytest.mark.asyncio
    async def test_validate_code(self, temp_dir):
        """Test validating code."""
        # Create a simple test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass")
        
        # Create a modified version
        modified_code = "def test():\n    return True"
        
        validator = ModificationValidator()
        
        # Mock the validation methods to return awaitable results
        async def mock_validate_syntax(code):
            return {"has_syntax_errors": False, "errors": []}
        
        async def mock_validate_semantics(code):
            return {"passed": True, "issues": []}
        
        async def mock_run_tests(code, file_path):
            return {"passed": True, "summary": {}, "run": True}
        
        async def mock_assess_impact(code, original_code, file_path):
            return {"high_risk": False, "metrics": {"risk_score": 30}, "reasons": []}
        
        # Create a mock StaticAnalyzer
        mock_static_analyzer = Mock()
        async def mock_analyze_code(code):
            return {"passed": True, "issues": []}
        mock_static_analyzer.analyze_code = mock_analyze_code
        
        # Replace the actual methods with mocks
        validator.validate_syntax = mock_validate_syntax
        validator.validate_semantics = mock_validate_semantics
        validator.run_tests = mock_run_tests
        validator.assess_impact = mock_assess_impact
        validator.static_analyzer = mock_static_analyzer
        
        result = await validator.validate_code(modified_code, test_file, "def test(): pass")
        
        assert "passed" in result
        assert "syntax_check" in result
        assert "semantics_check" in result
        assert "static_analysis" in result
        assert "test_results" in result
        assert "impact_assessment" in result


class TestModificationVersionControl:
    @pytest.mark.asyncio
    async def test_backup_file(self, temp_dir):
        """Test backing up a file."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass")
        
        version_control = ModificationVersionControl(temp_dir)
        
        result = await version_control.backup_file("test.py")
        
        assert result.get("success") is True
        assert result.get("file") == "test.py"
        assert "backup" in result
        assert os.path.exists(result.get("backup"))
    
    @pytest.mark.asyncio
    async def test_restore_backup(self, temp_dir):
        """Test restoring a file from backup."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass")
        
        version_control = ModificationVersionControl(temp_dir)
        
        # Create a backup
        backup_result = await version_control.backup_file("test.py")
        
        # Modify the file
        with open(test_file, "w") as f:
            f.write("def modified(): pass")
        
        # Restore from backup
        restore_result = await version_control.restore_backup("test.py")
        
        assert restore_result.get("success") is True
        
        # Verify the file was restored
        with open(test_file, "r") as f:
            content = f.read()
        
        assert content == "def test(): pass"
    
    @pytest.mark.asyncio
    async def test_handle_modification(self, temp_dir):
        """Test handling a complete modification."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass")
        
        version_control = ModificationVersionControl(temp_dir)
        
        # Create a simulated CodeModification
        modification = Mock()
        modification.target_component = "test.py"
        modification.author = "test"
        
        # For simulated version control without git, we need to modify the file manually
        with open(test_file, "w") as f:
            f.write("def modified(): pass")
        
        result = await version_control.handle_modification(modification, "Update function")
        
        assert result.get("success") is True 