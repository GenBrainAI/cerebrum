# Self-Aware Cerebrum Components

This document describes the implementation of the first phase of the Self-Aware Cerebrum components, which enable the system to understand, modify, and extend its own capabilities.

## Components Overview

### 1. Adaptive Context Manager

Located in `src/server/context/adaptive_context_manager.py`, this component provides a dynamic context management system that can adapt to different AI engines and operational needs. It handles context storage, retrieval, compression, and prioritization to optimize context usage across the system.

Key features:
- Dynamic context compression based on priority and token limits
- Engine-specific context adaptation
- Context prioritization for optimal token usage
- Persistent storage of context with metadata

### 2. Terminal Command Executor

Located in `src/server/system/terminal_command_executor.py`, this component provides secure command validation and execution with sandboxing for safety. It ensures that commands are properly validated, executed in a controlled environment, and logged for auditing purposes.

Key features:
- Command validation against security policies
- Risk assessment and approval workflow
- Sandboxed execution environment
- Comprehensive logging and history tracking

### 3. Codebase Vector Store

Located in `src/server/system/codebase_vector_store.py`, this component provides a vector store for codebase files, enabling semantic search and retrieval of code snippets based on natural language queries. It uses embeddings to represent code files and supports incremental updates to the vector store as the codebase evolves.

Key features:
- Semantic search of codebase using embeddings
- Incremental updates to track code changes
- Language-specific handling of code files
- Relevance scoring and snippet extraction

### 4. Unified Context Manager

Located in `src/server/context/unified_context_manager.py`, this component integrates the above components into a cohesive context management system. It provides a central hub for all context operations, ensuring consistent context management across the system.

Key features:
- Operation-based context management
- Integrated terminal command execution
- Codebase search and retrieval
- Unified interface for all context operations

## Usage

See the demonstration script in `src/server/examples/self_aware_demo.py` for examples of how to use these components.

### Basic Usage Example

```python
import asyncio
from src.server.context.unified_context_manager import UnifiedContextManager

async def main():
    # Initialize the unified context manager
    manager = UnifiedContextManager(
        base_path="persistent_state",
        codebase_root="."
    )
    
    # Initialize the codebase index
    await manager.initialize_codebase_index()
    
    # Create an operation
    operation_id = "example_operation"
    await manager.create_operation(
        operation_id=operation_id,
        description="Example operation",
        operation_type="development"
    )
    
    # Add context
    await manager.add_to_operation_context(
        operation_id=operation_id,
        content="This is an example context item.",
        source="example",
        priority=70
    )
    
    # Execute a command
    result = await manager.execute_command(
        operation_id=operation_id,
        command="echo 'Hello, World!'",
        requires_approval=False
    )
    print(f"Command output: {result.stdout}")
    
    # Search the codebase
    results = await manager.search_codebase(
        operation_id=operation_id,
        query="context manager"
    )
    
    # Get file content
    if results:
        content = await manager.get_file_content(
            operation_id=operation_id,
            file_path=results[0].file_path
        )
        print(f"File content: {content[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing

Unit tests for each component are located in the `tests/self_aware` directory:

- `test_adaptive_context_manager.py`: Tests for the Adaptive Context Manager
- `test_terminal_command_executor.py`: Tests for the Terminal Command Executor
- `test_codebase_vector_store.py`: Tests for the Codebase Vector Store
- `test_unified_context_manager.py`: Tests for the Unified Context Manager

Run the tests using pytest:

```bash
pytest tests/self_aware
```

## Architecture

These components implement the Self-Aware Cerebrum architecture as described in the high-level design document (`docs/self_aware_hld.md`). They form the foundation for the system's ability to understand and modify its own codebase.

The architecture follows these key principles:

1. **Context-Aware Operation**: All components maintain and utilize context to inform their operations.
2. **Safe Self-Modification**: Terminal commands and code modifications are validated and sandboxed for safety.
3. **Semantic Understanding**: The codebase vector store enables semantic understanding of the system's own code.
4. **Unified Interface**: The unified context manager provides a consistent interface for all context operations.

## Future Enhancements

Planned enhancements for these components include:

1. **Advanced Context Compression**: Implement LLM-based summarization for more intelligent context compression.
2. **Docker Sandboxing**: Complete the Docker sandboxing implementation for more secure command execution.
3. **Improved Snippet Extraction**: Enhance the relevance-based snippet extraction for more accurate code retrieval.
4. **Multi-Agent Integration**: Integrate with CrewAI and other agent frameworks for collaborative self-modification.

## Contributing

When contributing to these components, please ensure:

1. All code is well-documented with docstrings and comments.
2. Unit tests are added for new functionality.
3. Security considerations are addressed, especially for the Terminal Command Executor.
4. The unified interface is maintained for consistency.

## License

These components are part of the Cerebrum project and are subject to the same license terms as the overall project. 