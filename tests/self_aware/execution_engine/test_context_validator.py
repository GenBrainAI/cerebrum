import pytest
import re
from unittest.mock import MagicMock

from src.server.execution_engine.context_validator import ContextValidator
from src.server.execution_engine.context_manager import ContextManager, ContextType


@pytest.fixture
def context_manager():
    """Create a mocked ContextManager for testing."""
    manager = ContextManager()
    # Spy on the add_validation_rule method
    manager.add_validation_rule = MagicMock(wraps=manager.add_validation_rule)
    return manager


@pytest.fixture
def context_validator(context_manager):
    """Create a ContextValidator instance for testing."""
    return ContextValidator(context_manager)


class TestContextValidator:
    """Tests for the ContextValidator class."""

    def test_type_validator(self, context_validator, context_manager):
        """Test adding and using type validators."""
        # Add string type validator
        context_validator.add_type_validator("string_key", "string")
        
        # Check that validation rule was added to context manager
        context_manager.add_validation_rule.assert_called()
        
        # Test with valid value
        context_manager.set_context("string_key", "valid string", ContextType.GLOBAL)
        assert context_manager.get_context("string_key") == "valid string"
        
        # Test with invalid value (should raise ValueError)
        with pytest.raises(ValueError):
            context_manager.set_context("string_key", 123, ContextType.GLOBAL)
        
        # Test number type validator
        context_validator.add_type_validator("number_key", "number")
        
        # Valid number
        context_manager.set_context("number_key", 42, ContextType.GLOBAL)
        assert context_manager.get_context("number_key") == 42
        
        # Invalid number
        with pytest.raises(ValueError):
            context_manager.set_context("number_key", "not a number", ContextType.GLOBAL)

    def test_schema_validator(self, context_validator, context_manager):
        """Test adding and using schema validators."""
        # Define a simple schema
        schema = {
            "properties": {
                "name": {"type": "string", "required": True},
                "age": {"type": "number", "required": True},
                "tags": {"type": "array", "required": False}
            }
        }
        
        # Add schema validator
        context_validator.add_schema_validator("person", schema)
        
        # Valid object
        valid_person = {
            "name": "John Doe",
            "age": 30,
            "tags": ["developer", "python"]
        }
        context_manager.set_context("person", valid_person, ContextType.GLOBAL)
        assert context_manager.get_context("person") == valid_person
        
        # Invalid object - missing required field
        invalid_person1 = {
            "name": "Jane Doe"
            # Missing age
        }
        with pytest.raises(ValueError):
            context_manager.set_context("person", invalid_person1, ContextType.GLOBAL)
        
        # Invalid object - wrong type
        invalid_person2 = {
            "name": "Bob Smith",
            "age": "thirty"  # String instead of number
        }
        with pytest.raises(ValueError):
            context_manager.set_context("person", invalid_person2, ContextType.GLOBAL)
        
        # Invalid - not an object
        with pytest.raises(ValueError):
            context_manager.set_context("person", "not an object", ContextType.GLOBAL)

    def test_range_validator(self, context_validator, context_manager):
        """Test adding and using range validators."""
        # Add range validator (1-100)
        context_validator.add_range_validator("score", 1, 100)
        
        # Valid values
        context_manager.set_context("score", 1, ContextType.GLOBAL)  # Min
        assert context_manager.get_context("score") == 1
        
        context_manager.set_context("score", 50, ContextType.GLOBAL)  # Middle
        assert context_manager.get_context("score") == 50
        
        context_manager.set_context("score", 100, ContextType.GLOBAL)  # Max
        assert context_manager.get_context("score") == 100
        
        # Invalid values
        with pytest.raises(ValueError):
            context_manager.set_context("score", 0, ContextType.GLOBAL)  # Below min
        
        with pytest.raises(ValueError):
            context_manager.set_context("score", 101, ContextType.GLOBAL)  # Above max
        
        with pytest.raises(ValueError):
            context_manager.set_context("score", "fifty", ContextType.GLOBAL)  # Not a number

    def test_regex_validator(self, context_validator, context_manager):
        """Test adding and using regex validators."""
        # Add regex validator for email pattern
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        context_validator.add_regex_validator("email", email_pattern)
        
        # Valid email
        context_manager.set_context("email", "test@example.com", ContextType.GLOBAL)
        assert context_manager.get_context("email") == "test@example.com"
        
        # Invalid emails
        with pytest.raises(ValueError):
            context_manager.set_context("email", "not-an-email", ContextType.GLOBAL)
        
        with pytest.raises(ValueError):
            context_manager.set_context("email", "missing-domain@", ContextType.GLOBAL)
        
        with pytest.raises(ValueError):
            context_manager.set_context("email", 12345, ContextType.GLOBAL)  # Not a string

    def test_enum_validator(self, context_validator, context_manager):
        """Test adding and using enum validators."""
        # Add enum validator
        allowed_values = ["red", "green", "blue"]
        context_validator.add_enum_validator("color", allowed_values)
        
        # Valid values
        context_manager.set_context("color", "red", ContextType.GLOBAL)
        assert context_manager.get_context("color") == "red"
        
        context_manager.set_context("color", "green", ContextType.GLOBAL)
        assert context_manager.get_context("color") == "green"
        
        context_manager.set_context("color", "blue", ContextType.GLOBAL)
        assert context_manager.get_context("color") == "blue"
        
        # Invalid values
        with pytest.raises(ValueError):
            context_manager.set_context("color", "yellow", ContextType.GLOBAL)
        
        with pytest.raises(ValueError):
            context_manager.set_context("color", "RED", ContextType.GLOBAL)  # Case sensitive

    def test_custom_validator(self, context_validator, context_manager):
        """Test adding and using custom validators."""
        # Define a custom validation function
        def is_even_number(value):
            return isinstance(value, int) and value % 2 == 0
        
        # Add custom validator
        context_validator.add_custom_validator("even_number", is_even_number)
        
        # Valid values
        context_manager.set_context("even_number", 2, ContextType.GLOBAL)
        assert context_manager.get_context("even_number") == 2
        
        context_manager.set_context("even_number", 100, ContextType.GLOBAL)
        assert context_manager.get_context("even_number") == 100
        
        # Invalid values
        with pytest.raises(ValueError):
            context_manager.set_context("even_number", 3, ContextType.GLOBAL)  # Odd number
        
        with pytest.raises(ValueError):
            context_manager.set_context("even_number", "2", ContextType.GLOBAL)  # String

    def test_validate_context(self, context_validator, context_manager):
        """Test validating the entire context."""
        # Set up validators
        context_validator.add_type_validator("string_key", "string")
        context_validator.add_range_validator("number_key", 1, 10)
        context_validator.add_enum_validator("enum_key", ["a", "b", "c"])
        
        # Set valid values
        context_manager.set_context("string_key", "valid", ContextType.GLOBAL)
        context_manager.set_context("number_key", 5, ContextType.GLOBAL)
        context_manager.set_context("enum_key", "b", ContextType.GLOBAL)
        context_manager.set_context("unvalidated_key", "anything", ContextType.GLOBAL)
        
        # Validate context - should pass
        is_valid, errors = context_validator.validate_context()
        assert is_valid is True
        assert not errors
        
        # Set invalid value
        context_manager.set_context("number_key", 20, ContextType.GLOBAL, skip_validation=True)
        
        # Mock validation function for bypassing ContextManager validation
        original_validation = context_manager.validation_rules["number_key"]
        context_manager.validation_rules["number_key"] = lambda x: True  # Always passes in context_manager
        
        # Validate context - should fail
        is_valid, errors = context_validator.validate_context()
        assert is_valid is False
        assert "number_key" in errors
        
        # Restore original validation function
        context_manager.validation_rules["number_key"] = original_validation

    def test_validate_against_schema(self, context_validator):
        """Test the internal schema validation method."""
        # Define a nested schema
        schema = {
            "properties": {
                "name": {"type": "string", "required": True},
                "address": {
                    "type": "object",
                    "required": True,
                    "properties": {
                        "street": {"type": "string", "required": True},
                        "city": {"type": "string", "required": True},
                        "zip": {"type": "string", "required": False}
                    }
                }
            }
        }
        
        # Valid object
        valid_obj = {
            "name": "John Doe",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "zip": "12345"
            }
        }
        errors = context_validator._validate_against_schema(valid_obj, schema)
        assert not errors
        
        # Invalid - missing nested required field
        invalid_obj = {
            "name": "John Doe",
            "address": {
                "street": "123 Main St"
                # Missing city
            }
        }
        errors = context_validator._validate_against_schema(invalid_obj, schema)
        assert len(errors) == 1
        assert "address.city" in errors[0] or "Missing required field" in errors[0] 