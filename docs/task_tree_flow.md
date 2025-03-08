# Task Tree Flow

## Overview

Task Tree Flow is a powerful extension to the Task Tree framework that enables transformation capabilities between task nodes. It provides a flexible way to organize tasks in a hierarchical structure, with support for different execution strategies, aggregation methods, and transformations between tasks.

## Key Features

- **Hierarchical Task Organization**: Organize tasks in a tree structure with parent-child relationships.
- **Execution Strategies**: Support for sequential, parallel, and parallel with concurrency limit execution strategies.
- **Transformers**: Apply transformations to task outputs before they are passed to child tasks or aggregated.
- **Aggregators**: Combine results from multiple tasks using different aggregation strategies.
- **Dependencies**: Define dependencies between tasks to ensure proper execution order.
- **Error Handling**: Robust error handling with retry mechanisms and timeout support.
- **State Persistence**: Track and persist the state of task execution for monitoring and debugging.

## Core Components

### TaskNode

The `TaskNode` class represents a node in the task tree. It encapsulates a task and provides methods for executing the task, managing child nodes, and handling dependencies.

Key properties:
- `task_id`: The ID of the task associated with this node.
- `children`: A list of child nodes.
- `dependencies`: A list of dependency nodes that must be executed before this node.
- `aggregator`: The aggregator used to combine results from child nodes.
- `transformer`: The transformer used to transform the task output.
- `execution_config`: Configuration for task execution, including strategy, retries, timeout, etc.
- `state`: The current state of the node, including execution status and results.

### TaskTreeFlowManager

The `TaskTreeFlowManager` class manages a collection of task nodes and provides methods for creating, updating, and executing task trees.

Key methods:
- `create_node`: Create a new task node.
- `add_child`: Add a child relationship between nodes.
- `add_dependency`: Add a dependency relationship between nodes.
- `execute_node`: Execute a specific node in the tree.
- `execute_tree`: Execute the entire task tree.
- `create_from_model`: Create a manager from a model.
- `to_model`: Convert the manager to a model for persistence.

### Transformers

Transformers are used to modify the output of a task before it is passed to child tasks or aggregated. The framework includes several built-in transformers:

- **PromptTransformer**: Transforms the output using a prompt-based approach, with instructions, prefix, and suffix.
- **JSONTransformer**: Transforms the output to a JSON format.
- **XMLTransformer**: Transforms the output to an XML format.
- **MarkdownTransformer**: Transforms the output to a Markdown format.

### Aggregators

Aggregators are used to combine results from multiple tasks. The framework includes several built-in aggregators:

- **AllAggregator**: Returns the result of the current node without aggregating child results.
- **CombineAggregator**: Combines the results of the current node and all child nodes.
- **SummarizeAllAggregator**: Summarizes the results of the current node and all child nodes.
- **FirstSuccessAggregator**: Returns the result of the first successful child node.
- **VoteAggregator**: Selects the most common result from child nodes.

## API Usage

### Creating a Task Tree Flow

```python
from src.server.controllers.task_tree_flow import TaskTreeFlowManager
from src.server.models.task_tree_flow import TaskTreeFlow

# Create a new task tree flow
tree_flow = TaskTreeFlow(
    id="tree1",
    name="My Task Tree",
    description="A sample task tree",
    tasksmanager_id="tm1",
    nodes={},
    roots=[],
    execution_groups={}
)

# Save the tree flow to the persistence model
persistence_model.create("tree_flows", "tree1", tree_flow)

# Create a manager
manager = TaskTreeFlowManager(task_manager, persistence_model)
await manager.initialize()
manager.create_from_model("tree1")
```

### Adding Nodes

```python
# Create a root node
manager.create_node(
    task_id="task1",
    aggregator_type="combine",
    transformer={
        "type": "prompt",
        "instructions": "Transform this",
        "prefix": "PREFIX: ",
        "suffix": " :SUFFIX"
    },
    execution_config={
        "strategy": "sequential",
        "execute_children": True,
        "propagate_context": True
    }
)

# Create child nodes
manager.create_node(
    task_id="task2",
    aggregator_type="all",
    transformer=None,
    execution_config={
        "strategy": "sequential",
        "execute_children": True,
        "propagate_context": True
    }
)

manager.create_node(
    task_id="task3",
    aggregator_type="all",
    transformer=None,
    execution_config={
        "strategy": "sequential",
        "execute_children": True,
        "propagate_context": True
    }
)

# Add child relationships
manager.add_child("task1", "task2")
manager.add_child("task1", "task3")

# Add dependencies
manager.add_dependency("task3", "task2")  # task3 depends on task2
```

### Executing Tasks

```python
# Execute the entire tree
results = await manager.execute_tree({"input": "test"})

# Execute a specific node
result = await manager.execute_node("task2", {"input": "test"})
```

## REST API

The Task Tree Flow feature provides a comprehensive REST API for managing task trees:

### Tree Flow Management

- `POST /tasksmanager/{tasksmanager_id}/tree_flow`: Create a new task tree flow.
- `GET /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}`: Get a task tree flow.
- `PUT /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}`: Update a task tree flow.
- `DELETE /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}`: Delete a task tree flow.

### Node Management

- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node`: Create a new node.
- `PUT /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}`: Update a node.
- `DELETE /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}`: Delete a node.

### Relationship Management

- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/relationship`: Add a parent-child relationship.
- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/dependency`: Add a dependency relationship.

### Node Configuration

- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}/transformer`: Set a transformer for a node.
- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}/aggregator`: Set an aggregator for a node.
- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}/execution_config`: Set execution configuration for a node.

### Execution

- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/execute`: Execute the entire tree.
- `POST /tasksmanager/{tasksmanager_id}/tree_flow/{tree_flow_id}/node/{node_id}/execute`: Execute a specific node.

## Execution Strategies

The Task Tree Flow framework supports several execution strategies:

### Sequential

Tasks are executed one after another, in the order they are defined. This is the default strategy.

```python
execution_config = {
    "strategy": "sequential",
    "execute_children": True,
    "propagate_context": True
}
```

### Parallel

Tasks are executed concurrently, with no limit on the number of concurrent executions.

```python
execution_config = {
    "strategy": "parallel",
    "execute_children": True,
    "propagate_context": True
}
```

### Parallel with Concurrency Limit

Tasks are executed concurrently, with a limit on the number of concurrent executions.

```python
execution_config = {
    "strategy": "parallel",
    "max_concurrency": 5,
    "execute_children": True,
    "propagate_context": True
}
```

## Error Handling

The Task Tree Flow framework provides robust error handling capabilities:

### Retries

You can configure a task to retry on failure:

```python
execution_config = {
    "strategy": "sequential",
    "max_retries": 3,
    "retry_delay": 1.0,  # seconds
    "execute_children": True,
    "propagate_context": True
}
```

### Timeout

You can set a timeout for task execution:

```python
execution_config = {
    "strategy": "sequential",
    "timeout": 30.0,  # seconds
    "execute_children": True,
    "propagate_context": True
}
```

### Fail Fast

You can configure a task to fail fast if any of its child tasks fail:

```python
execution_config = {
    "strategy": "sequential",
    "fail_fast": True,
    "execute_children": True,
    "propagate_context": True
}
```

## Transformers

Transformers are used to modify the output of a task before it is passed to child tasks or aggregated.

### Prompt Transformer

The `PromptTransformer` transforms the output using a prompt-based approach:

```python
transformer = {
    "type": "prompt",
    "instructions": "Transform this output into a concise summary",
    "prefix": "SUMMARY: ",
    "suffix": " :END"
}
```

### JSON Transformer

The `JSONTransformer` transforms the output to a JSON format:

```python
transformer = {
    "type": "json",
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "details": {"type": "array", "items": {"type": "string"}}
        }
    }
}
```

## Aggregators

Aggregators are used to combine results from multiple tasks.

### All Aggregator

The `AllAggregator` returns the result of the current node without aggregating child results:

```python
aggregator_type = "all"
```

### Combine Aggregator

The `CombineAggregator` combines the results of the current node and all child nodes:

```python
aggregator_type = "combine"
```

### Summarize All Aggregator

The `SummarizeAllAggregator` summarizes the results of the current node and all child nodes:

```python
aggregator_type = "summarize_all"
```

### First Success Aggregator

The `FirstSuccessAggregator` returns the result of the first successful child node:

```python
aggregator_type = "first_success"
```

### Vote Aggregator

The `VoteAggregator` selects the most common result from child nodes:

```python
aggregator_type = "vote"
threshold = 0.5  # Optional threshold for voting
```

## Migration

If you have existing task trees, you can migrate them to the new Task Tree Flow format using the provided migration script:

```bash
python -m src.scripts.migrate_task_trees
```

This script will:
1. Retrieve all existing task trees from the persistence model.
2. Convert them to the new Task Tree Flow format.
3. Save the migrated trees back to the persistence model.

## Best Practices

### Task Organization

- Organize tasks in a logical hierarchy, with parent tasks representing higher-level operations and child tasks representing more specific operations.
- Use dependencies to ensure proper execution order when tasks have prerequisites.
- Group related tasks together using execution groups.

### Execution Configuration

- Use the appropriate execution strategy for your use case:
  - `sequential` for tasks that must be executed in order.
  - `parallel` for tasks that can be executed concurrently.
  - `parallel` with `max_concurrency` for tasks that can be executed concurrently but with a limit on the number of concurrent executions.
- Configure retries and timeouts based on the expected behavior of the task.
- Use `fail_fast` for tasks where any failure should stop the entire execution.

### Transformers and Aggregators

- Use transformers to modify task outputs to match the expected input format of child tasks.
- Choose the appropriate aggregator based on how you want to combine results:
  - `all` for tasks where only the current node's result matters.
  - `combine` for tasks where all results should be combined.
  - `summarize_all` for tasks where results should be summarized.
  - `first_success` for tasks where only the first successful result matters.
  - `vote` for tasks where the most common result should be selected.

### Error Handling

- Configure appropriate retry settings for tasks that may fail transiently.
- Set timeouts to prevent tasks from running indefinitely.
- Use `fail_fast` judiciously to balance between robustness and early failure detection.

## Troubleshooting

### Common Issues

#### Task Execution Failures

If a task fails to execute, check:
- The task implementation for errors.
- The execution configuration, including retries and timeouts.
- The dependencies to ensure they are executing correctly.

#### Transformer Issues

If a transformer is not working as expected, check:
- The transformer configuration, including type, instructions, prefix, and suffix.
- The output format of the task to ensure it matches the expected input format of the transformer.

#### Aggregator Issues

If an aggregator is not combining results as expected, check:
- The aggregator type to ensure it matches your use case.
- The output format of child tasks to ensure they can be properly aggregated.

### Debugging

To debug task execution:
1. Check the state of the task node after execution, which includes execution status, result, and any errors.
2. Use the API to execute specific nodes to isolate issues.
3. Review the logs for detailed information about task execution.

## Conclusion

Task Tree Flow provides a powerful framework for organizing and executing tasks in a hierarchical structure, with support for different execution strategies, transformations, and aggregations. By following the guidelines and best practices outlined in this documentation, you can create robust and flexible task trees that meet your specific needs. 