# Cerebrum

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)](https://fastapi.tiangolo.com/)

Cerebrum is an advanced AI task orchestration and management system designed to handle complex, hierarchical task execution with robust state management and monitoring capabilities. It represents a revolutionary approach to AI framework development, offering a self-evolving system that grows and adapts through natural conversation.

## 🌟 Features

- **Self-Evolution**: System learns and adapts through natural conversation
- **Task Orchestration**: Hierarchical task management with dependency tracking
- **Multi-Framework Integration**: Seamless integration with CrewAI, LangChain, and custom frameworks
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

Cerebrum's architecture is designed with three primary goals:
1. Enabling natural interaction and self-evolution
2. Maintaining robust security and stability
3. Supporting seamless integration with existing enterprise systems

For a comprehensive understanding of Cerebrum's architecture, please refer to our [Architecture Documentation](architecture.md).

### Core Components

1. **Core Engine**
   - Central orchestrator for all operations
   - Dynamic tool management
   - State coordination
   - Task orchestration

2. **State Management**
   - Multi-layer state management
   - State isolation
   - Recovery mechanisms
   - Transaction management

3. **Task Management**
   - Hierarchical task organization
   - Multiple execution strategies
   - Dependency handling
   - Progress tracking

4. **Integration Layer**
   - Multi-framework support
   - API adapters
   - Framework connectors
   - Resource sharing

5. **Self-Evolution Mechanism**
   - Capability discovery
   - Pattern learning
   - Automated improvement
   - Safety validation

## 📚 Documentation

### Customer Management

For detailed instructions on managing customer access, subscriptions, and repository synchronization, see our [Customer Management Guide](docs/customer_management.md).

### Task Tree Management

The task tree management system provides a flexible framework for organizing and executing hierarchical tasks. Key features include:

- Hierarchical task organization
- Multiple execution strategies (Sequential, Parallel, Limited Parallel)
- Comprehensive state tracking
- Result aggregation strategies
- Execution monitoring

[Detailed Task Tree Documentation](docs/task_tree.md)

### Task Flow Framework

The task flow framework enables the creation and execution of sequences of tasks with transformations between them. Key features include:

- Sequential task execution with data transformation
- Multiple transformer types for different transformation needs
- Pre-execute and post-execute hooks for custom processing
- Comprehensive status tracking and error handling
- Support for complex multi-task workflows

[Task Flow Documentation](docs/README_FLOW.md)

### Self-Aware Components

The Self-Aware Components enable the system to understand, modify, and extend its own capabilities. Key features include:

- Adaptive Context Management for optimized context usage
- Secure Terminal Command Execution with sandboxing
- Codebase Vector Store for semantic code search
- Unified Context Manager for integrated context operations

[Self-Aware Components Documentation](docs/self_aware_components.md)

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

- [Architecture Documentation](architecture.md)
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

## Syncing with Base Repository

As a customer with a private fork of Cerebrum, you can automatically sync your fork with the base repository to receive updates. Follow these steps to set up automatic syncing:

1. **Generate a Personal Access Token (PAT)**:
   - Go to your GitHub Settings > Developer settings > Personal access tokens
   - Generate a new token with `repo` scope
   - Copy the token value

2. **Add the Token to Your Fork**:
   - Go to your fork's Settings > Secrets and variables > Actions
   - Create a new repository secret named `SYNC_TOKEN`
   - Paste your PAT as the value

3. **Enable Workflows**:
   - Go to your fork's Actions tab
   - Enable workflows if they are disabled
   - You should see the "Sync with Base Repository" workflow

4. **Using the Sync Workflow**:
   - The workflow runs automatically every day at midnight
   - You can also trigger it manually from the Actions tab
   - When updates are available, it creates a pull request for you to review
   - If there are conflicts, it creates a special PR with instructions for manual resolution

5. **Best Practices**:
   - Always review the changes in the sync PR before merging
   - If you have local customizations, keep them well-documented
   - Consider creating a separate branch for your customizations
   - Test your application after merging updates

For any issues or questions about syncing, please contact our support team.

---

Made with ❤️ by the Cerebrum Team
