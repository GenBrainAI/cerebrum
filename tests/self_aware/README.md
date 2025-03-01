# Self-Aware Cerebrum Tests

This directory contains tests for the Self-Aware Cerebrum components, which enable the system to understand, modify, and extend its own capabilities.

## Test Organization

The tests are organized into the following subdirectories:

### Context

The `context` directory contains tests for context management components:

- `test_adaptive_context_manager.py`: Tests for the Adaptive Context Manager, which provides dynamic context management with compression and prioritization.
- `test_unified_context_manager.py`: Tests for the Unified Context Manager, which integrates various context providers into a cohesive system.

### System

The `system` directory contains tests for system access and interaction components:

- `test_terminal_command_executor.py`: Tests for the Terminal Command Executor, which provides secure command validation and execution.
- `test_codebase_vector_store.py`: Tests for the Codebase Vector Store, which enables semantic search of the codebase.

## Running Tests

To run all self-aware tests:

```bash
python -m pytest tests/self_aware
```

To run tests for a specific component:

```bash
python -m pytest tests/self_aware/context/test_adaptive_context_manager.py
```

## Test Coverage

These tests cover the first phase of the Self-Aware Cerebrum implementation, focusing on:

1. Context management and adaptation
2. Secure system access
3. Codebase understanding and search
4. Integration between components

Future phases will add tests for additional capabilities such as:

- Self-modification
- Planning and goal decomposition
- Long-running operations
- Advanced observability 