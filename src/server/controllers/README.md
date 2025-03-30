# Task Sequence Controller

## Overview

This directory contains controllers for task execution and sequence management. We've implemented a separation of concerns approach to prevent recursion issues and improve maintainability.

## Key Components

### TaskRunner

The `TaskRunner` class is responsible for executing individual tasks. It delegates sequence execution to the `TaskSequenceController` to avoid circular dependencies.

Key features:
- Executes individual tasks with appropriate frameworks (standard, CrewAI, etc.)
- Detects when tasks are part of a sequence and delegates to the sequence controller
- Maintains observability and monitoring of task execution

### TaskSequenceController

The `TaskSequenceController` is a dedicated controller for executing task sequences. It handles the flow of execution between tasks and manages the handover of context and data.

Key features:
- Executes sequences of tasks in order
- Manages the handover of outputs between tasks
- Tracks sequence execution status and results
- Prevents recursive sequence execution
- Provides robust error handling for sequence execution

## Task Sequence Execution Flow

1. When a user triggers a task that is part of a sequence, the `TaskRunner` detects this through the `_check_if_task_starts_sequence` method.
2. The `TaskRunner` delegates sequence execution to the `TaskSequenceController`.
3. The `TaskSequenceController` executes each task in the sequence, passing outputs between tasks as needed.
4. The controller tracks execution progress and handles any errors that occur during sequence execution.
5. The controller returns consolidated results that include individual task results and overall sequence status.

## Preventing Recursion

The refactored implementation prevents recursion through several mechanisms:

1. The `inside_sequence` flag ensures that tasks within a sequence don't trigger new sequence executions.
2. The `TaskSequenceController` tracks active sequences in the `_active_sequences` set.
3. If a sequence tries to execute while it's already running, the controller returns cached results instead of triggering a new execution.

## Error Handling

The sequence controller includes comprehensive error handling:

1. Individual task failures are caught and don't crash the entire sequence.
2. Task status is properly updated in the persistence model.
3. Execution results include detailed error information.
4. The controller ensures cleanup of resources even in error cases through try/finally blocks.

## Testing

The implementation includes comprehensive tests in the `tests/controllers` directory, including:
- Basic sequence execution
- Sequence execution by ID
- Handling of task errors
- Recursion prevention

## Usage Examples

```python
# Execute a sequence by providing task IDs
await task_runner.run_task_sequence(
    tasksmanager_id=tasksmanager_id,
    task_ids=task_ids,
    initial_context={"some_context": "value"}
)

# Execute a sequence by sequence ID
await task_runner.run_task_sequence_by_id(
    tasksmanager_id=tasksmanager_id,
    sequence_id=sequence_id
)
``` 