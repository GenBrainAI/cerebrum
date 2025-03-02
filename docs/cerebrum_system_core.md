# Cerebrum System Core

The Cerebrum System Core provides a unified interface for interacting with the Cerebrum framework's core capabilities, bringing together context management, system access, and codebase understanding into a cohesive system.

## Overview

The Cerebrum System Core serves as the central integration point for Cerebrum's system components, enabling advanced capabilities through a simple, unified API. It is designed to be the foundation for the Self-Aware Cerebrum system, providing the essential capabilities needed for self-understanding, self-modification, and autonomous operation.

Key capabilities include:

- **Codebase Understanding**: Semantic search and navigation of the codebase
- **System Access**: Secure command execution with approval workflows
- **Context Management**: Adaptive context handling with compression and prioritization
- **Integrated Operations**: Coordinated workflows across multiple components

## Architecture

The Cerebrum System Core integrates several specialized components:

```
CerebrumSystemCore
├── UnifiedContextManager
│   ├── AdaptiveContextManager
│   │   ├── Context Compression Engine
│   │   └── Context Storage
│   ├── TerminalCommandExecutor
│   │   ├── Command Validation
│   │   ├── Sandboxed Execution
│   │   └── Approval Workflow
│   └── CodebaseVectorStore
│       ├── Embedding Generation
│       ├── Semantic Search
│       └── Code Indexing
└── Operation Management
    ├── Operation Context
    ├── Operation Metadata
    └── Operation Persistence
```

### Key Components

1. **UnifiedContextManager**: Central hub for context management across the system
   - Integrates multiple specialized context providers
   - Maintains operation state and context
   - Coordinates interactions between components

2. **AdaptiveContextManager**: Manages context with dynamic compression and prioritization
   - Stores and retrieves context items
   - Compresses context to fit within token limits
   - Prioritizes context based on importance

3. **TerminalCommandExecutor**: Provides secure command execution capabilities
   - Validates commands against security policies
   - Executes commands in sandboxed environments
   - Manages approval workflows for sensitive commands

4. **CodebaseVectorStore**: Enables semantic search of the codebase
   - Indexes code files with embeddings
   - Provides semantic search capabilities
   - Tracks codebase changes for incremental updates

## Installation

The Cerebrum System Core is part of the Cerebrum framework. To use it, you need to have the Cerebrum framework installed:

```bash
# Clone the repository
git clone https://github.com/yourusername/cerebrum.git
cd cerebrum

# Install dependencies
pip install -r requirements.txt
```

## Configuration

The Cerebrum System Core is configured through a JSON configuration file. Here's an example configuration:

```json
{
    "base_path": "persistent_state/cerebrum_system",
    "context": {
        "max_tokens": 8192,
        "default_model": "gpt-4",
        "enable_history": true,
        "history_max_items": 10,
        "default_compression_strategy": "summarize"
    },
    "security": {
        "max_execution_time": 60,
        "max_output_size": 1048576,
        "blocked_commands": [
            "rm -rf /",
            "sudo",
            "chmod 777"
        ]
    },
    "vector_store": {
        "embedding_model": "text-embedding-ada-002",
        "embedding_dimension": 1536,
        "similarity_threshold": 0.7,
        "max_files": 10000,
        "excluded_dirs": [
            ".git", "node_modules", "venv", "env", "__pycache__", 
            "dist", "build", ".vscode", ".idea"
        ],
        "excluded_patterns": [
            "\\.pyc$", "\\.class$", "\\.o$", "\\.so$", "\\.a$",
            "\\.dll$", "\\.exe$", "\\.bin$", "\\.dat$", "\\.log$"
        ],
        "included_extensions": [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
            ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs",
            ".rb", ".php", ".swift", ".kt", ".sh", ".md",
            ".json", ".yml", ".yaml", ".toml", ".sql"
        ],
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
}
```

## Usage

### Basic Usage

```python
import asyncio
from src.server.self_aware_core import CerebrumSystemCore

async def main():
    # Initialize the Cerebrum System Core
    core = CerebrumSystemCore(
        base_path="persistent_state/cerebrum_system",
        codebase_root=".",
        config=None  # Will load from config file
    )
    
    # Initialize the core
    await core.initialize()
    
    # Use the core capabilities
    results = await core.search_code("context management")
    print(f"Found {len(results)} results")
    
    # Execute a command
    result = await core.execute_command("ls -la")
    print(f"Command output: {result.stdout}")
    
    # Add to context
    await core.add_to_context(
        content="Important information to remember",
        source="user",
        priority=80
    )
    
    # Get context
    context = await core.get_context(max_tokens=1000)
    print(f"Context: {context}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Searching the Codebase

```python
# Search for code related to context management
results = await core.search_code("context management")
for result in results:
    print(f"{result.file_path} (lines {result.start_line}-{result.end_line})")
    print(result.content)
```

### Executing Commands

```python
# Execute a command
result = await core.execute_command("ls -la")
print(f"Command output: {result.stdout}")

# Execute a command that requires approval
result = await core.execute_command("rm -rf temp_dir", requires_approval=True)
if isinstance(result, str):
    print(f"Command submitted for approval. Approval ID: {result}")
    
    # Later, approve the command
    approvals = await core.get_pending_approvals()
    result = await core.execute_approved_command(approvals[0]["id"])
    print(f"Command output: {result.stdout}")
```

### Managing Context

```python
# Add information to the context
await core.add_to_context(
    content="Important information to remember",
    source="user",
    priority=80,
    metadata={"key": "value"}
)

# Get the current context
context = await core.get_context(max_tokens=1000)
print(context)

# Get context with metadata
context = await core.get_context(include_metadata=True)
print(context)
```

### Working with Files

```python
# Get the content of a file
content = await core.get_file_content("src/server/self_aware_core.py")
print(content)

# Get codebase statistics
stats = await core.get_codebase_stats()
print(f"Total Files: {stats.get('total_files', 0)}")
print(f"Total Lines: {stats.get('total_lines', 0)}")
```

## API Reference

### CerebrumSystemCore

#### Constructor

```python
CerebrumSystemCore(
    base_path: str = "persistent_state/cerebrum_system",
    codebase_root: str = ".",
    config: Optional[Dict[str, Any]] = None
)
```

- `base_path`: Base path for persistent storage
- `codebase_root`: Root directory of the codebase
- `config`: Configuration dictionary with settings for all components

#### Methods

- `initialize()`: Initialize the system operation if not already initialized
- `index_codebase(incremental: bool = True)`: Index the codebase for semantic search
- `execute_command(command, working_directory, environment_vars, timeout, requires_approval)`: Execute a terminal command
- `search_code(query, top_k)`: Search the codebase for relevant code snippets
- `get_file_content(file_path)`: Get the content of a file
- `get_context(max_tokens, include_metadata)`: Get the current context of the system
- `add_to_context(content, source, priority, metadata)`: Add information to the system context
- `get_pending_approvals()`: Get pending command approvals
- `execute_approved_command(approval_id)`: Execute a previously approved command
- `reject_command(approval_id)`: Reject a pending command
- `get_codebase_stats()`: Get statistics about the indexed codebase
- `refresh_codebase()`: Refresh the codebase index

## Development

### Adding New Capabilities

To add new capabilities to the Cerebrum System Core:

1. Identify the component that should provide the capability
2. Implement the capability in the appropriate component
3. Add a method to the CerebrumSystemCore class that delegates to the component
4. Update the documentation to reflect the new capability

### Testing

The Cerebrum System Core includes comprehensive tests to ensure reliability:

```bash
# Run all tests
pytest tests/server/test_self_aware_core.py

# Run specific test
pytest tests/server/test_self_aware_core.py::test_search_code
```

## Contributing

Contributions to the Cerebrum System Core are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Submit a pull request

## License

The Cerebrum System Core is licensed under the MIT License. See the LICENSE file for details. 