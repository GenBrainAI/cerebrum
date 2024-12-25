# Task Tree Management System

A comprehensive guide to Cerebrum's task tree management system, which provides hierarchical task execution with robust state management and monitoring capabilities.

## Overview

The task tree management system allows you to:
- Organize tasks in hierarchical structures
- Control execution flow with dependencies
- Monitor and track task states
- Aggregate results from multiple tasks
- Persist and recover execution states

## Components

### Task Tree Structure

#### TaskNode
The fundamental building block that represents a task in the tree:
```python
node = TaskNode(
    task=Task(id="unique_id", name="Task Name"),
    aggregator=AllAggregator(),
    execution_config=ExecutionConfig()
)
```

#### TaskTreeManager
Manages the entire task tree structure:
```python
manager = TaskTreeManager()
manager.create_node(task)
manager.set_as_root("task_id")
manager.add_child("parent_id", "child_id")
```

### Execution Control

#### Execution Strategies
Three main strategies for task execution:

1. **Sequential** (`ExecutionStrategy.SEQUENTIAL`)
   - Tasks execute one after another
   - Useful for dependent operations
   ```python
   config = ExecutionConfig(strategy=ExecutionStrategy.SEQUENTIAL)
   ```

2. **Parallel** (`ExecutionStrategy.PARALLEL`)
   - Tasks execute concurrently
   - Best for independent operations
   ```python
   config = ExecutionConfig(strategy=ExecutionStrategy.PARALLEL)
   ```

3. **Parallel with Limit** (`ExecutionStrategy.PARALLEL_WITH_LIMIT`)
   - Concurrent execution with max concurrency
   - Controls resource usage
   ```python
   config = ExecutionConfig(
       strategy=ExecutionStrategy.PARALLEL_WITH_LIMIT,
       max_concurrency=3
   )
   ```

#### Execution Configuration
Configure execution behavior:
```python
config = ExecutionConfig(
    max_retries=3,
    retry_delay=1.0,
    timeout=30.0,
    fail_fast=False
)
```

### State Management

#### TaskNodeState
Tracks the state of individual tasks:
```python
state = TaskNodeState(
    task_id="task_id",
    name="Task Name",
    status=TaskStatus.PENDING
)
```

#### State Persistence
Save and restore task tree states:
```python
# Save state
state_manager = TaskTreeStateManager(base_path="states")
await state_manager.save_tree_state("tree_id", manager)

# Load state
state_data = await state_manager.load_tree_state("tree_id")
```

### Result Aggregation

#### Available Aggregators

1. **AllAggregator**
   ```python
   # Concatenates all responses with newlines
   aggregator = AllAggregator()
   result = aggregator.aggregate(["res1", "res2"])  # "res1\nres2"
   ```

2. **CombineAggregator**
   ```python
   # Combines responses into a single flow
   aggregator = CombineAggregator()
   result = aggregator.aggregate(["res1", "res2"])  # "res1 res2"
   ```

3. **SummarizeAllAggregator**
   ```python
   # Creates a summary of responses
   aggregator = SummarizeAllAggregator()
   result = aggregator.aggregate(["res1", "res2"])  # "Summary: res1, res2"
   ```

4. **FilterAggregator**
   ```python
   # Filters responses based on a condition
   aggregator = FilterAggregator(lambda x: len(x) > 3)
   result = aggregator.aggregate(["long", "short"])  # "long"
   ```

5. **PrioritizeAggregator**
   ```python
   # Prioritizes responses based on scoring
   aggregator = PrioritizeAggregator(lambda x: len(x))
   result = aggregator.aggregate(["a", "abc"])  # "[Score: 3.00] abc\n[Score: 1.00] a"
   ```

6. **ConsensusAggregator**
   ```python
   # Requires consensus among responses
   aggregator = ConsensusAggregator(threshold=0.7)
   result = aggregator.aggregate(["same", "same", "different"])  # "same"
   ```

## Monitoring and Statistics

### Execution Statistics
Get detailed execution stats:
```python
stats = node.get_execution_stats()
print(f"Status: {stats['status']}")
print(f"Duration: {stats['execution_duration']}s")
print(f"Error: {stats['error']}")
```

### Execution History
Track state transitions:
```python
for entry in node.state.execution_history:
    print(f"{entry['timestamp']}: {entry['old_status']} → {entry['new_status']}")
```

## Best Practices

### Task Organization
1. Keep trees shallow when possible
2. Group related tasks together
3. Use meaningful task IDs and names
4. Document task dependencies clearly

### Execution Strategy Selection
1. Use `SEQUENTIAL` for:
   - Tasks with dependencies
   - Operations that must happen in order
   - Resource-sensitive operations

2. Use `PARALLEL` for:
   - Independent tasks
   - IO-bound operations
   - Tasks with similar execution times

3. Use `PARALLEL_WITH_LIMIT` for:
   - Resource-intensive tasks
   - Large numbers of concurrent tasks
   - Controlled load distribution

### State Management
1. Save states at meaningful points
2. Implement regular cleanup of old states
3. Monitor state file sizes
4. Validate restored states

### Error Handling
1. Set appropriate retry counts
2. Use fail-fast for critical paths
3. Log all errors with context
4. Monitor retry patterns

## Common Patterns

### Pipeline Pattern
```python
# Create a linear pipeline of tasks
manager = TaskTreeManager()
tasks = ["prep", "process", "analyze", "report"]

for task_id in tasks:
    task = Task(id=task_id, name=f"{task_id.title()} Data")
    manager.create_node(task)

manager.set_as_root(tasks[0])
for i in range(len(tasks)-1):
    manager.add_child(tasks[i], tasks[i+1])
```

### Fan-out Pattern
```python
# Create parallel processing branches
manager = TaskTreeManager()
root = Task(id="root", name="Distributor")
manager.create_node(root)
manager.set_as_root("root")

for i in range(3):
    worker = Task(id=f"worker_{i}", name=f"Worker {i}")
    manager.create_node(worker)
    manager.add_child("root", f"worker_{i}")
```

### Aggregation Pattern
```python
# Collect and combine results
manager = TaskTreeManager()
collector = Task(id="collector", name="Result Collector")
node = manager.create_node(collector)
node.aggregator = SummarizeAllAggregator()

# Add worker tasks
for i in range(3):
    worker = Task(id=f"worker_{i}", name=f"Worker {i}")
    manager.create_node(worker)
    manager.add_child("collector", f"worker_{i}")
```

## Error Handling

### Retry Mechanism
```python
config = ExecutionConfig(
    max_retries=3,
    retry_delay=1.0
)

try:
    result = await node.run(context)
except TaskExecutionError as e:
    print(f"Task failed after {node.state.retry_count} retries")
```

### State Recovery
```python
try:
    state_data = await state_manager.load_tree_state("tree_id")
    if state_data is None:
        # Handle corrupted state
        state_data = create_default_state()
    manager.restore_state(state_data)
except Exception as e:
    # Handle recovery error
    logger.error(f"State recovery failed: {e}")
```

## Performance Considerations

1. **Memory Management**
   - Monitor task result sizes
   - Clean up completed task data
   - Use streaming for large results

2. **Concurrency Control**
   - Set appropriate max_concurrency
   - Monitor system resources
   - Balance parallel execution

3. **State Storage**
   - Implement state cleanup policies
   - Monitor state file sizes
   - Use compression for large states

4. **Error Recovery**
   - Set reasonable retry limits
   - Implement backoff strategies
   - Monitor retry patterns

## Troubleshooting

### Common Issues

1. **Task Execution Failures**
   - Check task dependencies
   - Verify execution configuration
   - Review error logs

2. **State Management Issues**
   - Verify file permissions
   - Check disk space
   - Validate state format

3. **Performance Problems**
   - Monitor resource usage
   - Review concurrency settings
   - Check task granularity

### Debugging Tips

1. Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. Monitor task states:
```python
for node_id, node in manager.nodes.items():
    print(f"Node {node_id}: {node.state.status}")
```

3. Track execution times:
```python
stats = node.get_execution_stats()
print(f"Duration: {stats['execution_duration']}s")
``` 