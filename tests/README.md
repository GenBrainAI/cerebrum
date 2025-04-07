# Cerebrum Testing Framework

This directory contains the test suite for the Cerebrum framework. Tests are organized by component type and follow standard pytest conventions.

## Test Structure

The tests are organized into the following directories:

- `controllers/`: Tests for controller components, including:
  - `test_crewai_runner.py`: Tests for CrewAI task execution and sanitization
  - `test_crewai_task.py`: Tests for CrewAI task functionality
  - `test_delegation_tool.py`: Tests for delegation tool functionality

- `tools/`: Tests for tool implementations, including:
  - `test_general_tools.py`: Tests for network and system monitoring tools

- `tasktree/`: Tests for task tree implementation, including:
  - `test_crewai_tasktree.py`: Tests for CrewAI integration with task tree

## Running Tests

To run all tests:

```bash
pytest
```

To run tests with verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/controllers/test_crewai_runner.py
```

To run a specific test case:

```bash
pytest tests/controllers/test_crewai_runner.py::TestCrewAISanitization
```

To run a specific test method:

```bash
pytest tests/controllers/test_crewai_runner.py::TestCrewAISanitization::test_sanitize_basic_types
```

## Test Guidelines

When adding new tests, please follow these guidelines:

1. Place tests in the appropriate directory based on the component being tested
2. Use pytest fixtures for common setup and teardown
3. Use proper mocking for external dependencies
4. Test both success and error cases
5. Follow naming conventions:
   - Test files: `test_<component>.py`
   - Test classes: `Test<Component>`
   - Test methods: `test_<functionality>`
6. Add proper docstrings to test classes and methods
7. Use appropriate assertions for checking expected behavior

## Running Tests in CI/CD

Tests are automatically run in CI/CD pipelines. To ensure your tests pass in CI:

1. Avoid hardcoding paths or environment-specific values
2. Use proper mocking for external dependencies
3. Clean up any resources created during tests
4. Ensure tests are deterministic and don't depend on execution order

## Code Coverage

To generate a code coverage report:

```bash
pytest --cov=src
```

To generate an HTML coverage report:

```bash
pytest --cov=src --cov-report=html
```

The HTML report will be generated in the `htmlcov/` directory.

## Async Testing

Many components in Cerebrum use async/await. For testing async code:

1. Use the `@pytest.mark.asyncio` decorator for async test functions
2. Use `AsyncMock` for mocking async functions
3. Consider using `pytest-asyncio` fixtures for async setup and teardown

Example:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_function():
    # Test async code
    result = await some_async_function()
    assert result == expected_value
``` 