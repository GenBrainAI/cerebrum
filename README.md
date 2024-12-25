# Cerebrum

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)](https://fastapi.tiangolo.com/)

Cerebrum is an advanced AI task orchestration and management system designed to handle complex, hierarchical task execution with robust state management and monitoring capabilities.

## 🌟 Features

- **Task Orchestration**: Hierarchical task management with dependency tracking
- **Parallel Processing**: Efficient execution of concurrent tasks
- **State Management**: Robust state persistence and recovery
- **Real-time Monitoring**: Comprehensive execution statistics and visualization
- **Error Handling**: Sophisticated retry mechanisms and failure recovery
- **Result Aggregation**: Flexible strategies for combining task results

## 📋 Requirements

- Python 3.11 or higher
- FastAPI
- Pydantic
- asyncio
- pytest (for testing)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cerebrum.git
cd cerebrum

# Install dependencies
poetry install
# OR
pip install -r requirements.txt
```

### Running the Server

```bash
# Using poetry
poetry run uvicorn src.server.main:app --host 0.0.0.0 --port 8080 --reload

# OR using pip
uvicorn src.server.main:app --host 0.0.0.0 --port 8080 --reload
```

Visit `http://localhost:8080/docs` to access the Swagger documentation.

## 🏗️ Architecture

### Core Components

1. **Task Management**
   - Task definition and creation
   - Dependency management
   - Execution strategies

2. **State Management**
   - State persistence
   - Recovery mechanisms
   - Version control

3. **Execution Engine**
   - Parallel processing
   - Resource management
   - Error handling

4. **Monitoring System**
   - Real-time statistics
   - Performance metrics
   - Visualization tools

## 📚 Documentation

### Task Tree Management

The task tree management system provides a flexible framework for organizing and executing hierarchical tasks. Key features include:

- Hierarchical task organization
- Multiple execution strategies (Sequential, Parallel, Limited Parallel)
- Comprehensive state tracking
- Result aggregation strategies
- Execution monitoring

[Detailed Task Tree Documentation](docs/task_tree.md)

### Usage Examples

```python
from src.server.controllers.tasks_tree_controller import TaskTreeManager, Task

# Create a task tree
manager = TaskTreeManager()
root_task = Task(id="root", name="Root Task")
manager.create_node(root_task)

# Execute tasks
result = await manager.execute_group("main_group", strategy="parallel")
```

More examples can be found in the [examples directory](examples/).

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/task_view/

# Run with coverage
pytest --cov=src tests/
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

1. Code Style
2. Development Process
3. Testing Requirements
4. Pull Request Process

### Development Setup

```bash
# Create development environment
poetry install --with dev

# Run pre-commit hooks
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](docs/)
- [Issue Tracker](https://github.com/yourusername/cerebrum/issues)
- [Project Wiki](https://github.com/yourusername/cerebrum/wiki)

## 🙏 Acknowledgments

- Contributors
- Supporting Libraries
- Inspiration Sources

## 📞 Contact

- Project Maintainer: [Your Name](mailto:your.email@example.com)
- Project Website: [https://cerebrum.ai](https://cerebrum.ai)

---

Made with ❤️ by the Cerebrum Team
