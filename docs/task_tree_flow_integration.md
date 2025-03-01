# Task Tree Flow Integration with Tasks

This document explains how to integrate Task Tree Flows with the existing Task Management system in Cerebrum.

## Overview

The Task Tree Flow system provides a powerful way to organize tasks in hierarchical structures with various execution strategies. By integrating it with the existing Task Management system, you can:

1. Associate regular tasks with tree flows
2. Execute tree flows through the task runner
3. Manage complex task dependencies and execution patterns

## Task Model Extension

The Task model has been extended with a `tree_flow_id` field that allows tasks to reference a tree flow:

```python
class Task(BaseModel):
    # ... existing fields ...
    tree_flow_id: Optional[str] = Field(default=None, description="ID of the task tree flow associated with this task")
```

This allows tasks to be associated with tree flows, enabling the task runner to execute the tree flow when the task is run.

## Task Runner Integration

The Task Runner has been updated to support tree flow execution. When a task with a `tree_flow_id` is executed, the runner will:

1. Initialize a TaskTreeFlowManager
2. Load the tree flow from the persistence model
3. Execute the tree flow with the appropriate context
4. Return the results

This integration allows tree flows to be executed through the standard task execution mechanisms.

## API Endpoints

The following API endpoints are available for associating tasks with tree flows:

### Associate a Task with a Tree Flow

```
POST /{tasksmanager_id}/task/{task_id}/associate_tree_flow/{tree_flow_id}
```

This endpoint associates a task with a tree flow, allowing the task to execute the tree flow when run.

### Disassociate a Task from a Tree Flow

```
POST /{tasksmanager_id}/task/{task_id}/disassociate_tree_flow
```

This endpoint removes the association between a task and its tree flow.

## Usage Examples

### Creating a Task Tree Flow and Associating it with a Task

```python
# Create a task tree flow
tree_flow_manager = TaskTreeFlowManager(task_manager, persistence_model)
tree_flow_id = tree_flow_manager.create_flow("My Tree Flow", "A complex flow of tasks")

# Add nodes to the tree flow
root_node_id = tree_flow_manager.create_node(
    tree_flow_id, 
    "Root Task", 
    "The root task of the flow",
    execution_config=ExecutionConfig(strategy=ExecutionStrategy.SEQUENTIAL)
)

child_node_id1 = tree_flow_manager.create_node(
    tree_flow_id,
    "Child Task 1",
    "First child task",
    parent_id=root_node_id
)

child_node_id2 = tree_flow_manager.create_node(
    tree_flow_id,
    "Child Task 2",
    "Second child task",
    parent_id=root_node_id
)

# Associate the tree flow with a task
task = task_manager.get_task("task-123")
task.tree_flow_id = tree_flow_id
task_manager.update_task(task)

# When the task is executed, it will run the tree flow
result = await task_runner.run_task(task)
```

### Using the API to Associate a Task with a Tree Flow

```python
import requests

# Associate a task with a tree flow
response = requests.post(
    "http://localhost:8000/api/tasksmanager/manager-123/task/task-123/associate_tree_flow/tree-flow-123"
)
print(response.json())

# Disassociate a task from a tree flow
response = requests.post(
    "http://localhost:8000/api/tasksmanager/manager-123/task/task-123/disassociate_tree_flow"
)
print(response.json())
```

## Best Practices

1. **Task Granularity**: Use tree flows for complex tasks that can be broken down into smaller, more manageable subtasks.

2. **Execution Strategies**: Choose the appropriate execution strategy based on the dependencies between tasks:
   - Use `SEQUENTIAL` for tasks that must be executed in order
   - Use `PARALLEL` for independent tasks that can be executed simultaneously
   - Use `PARALLEL_WITH_LIMIT` to control resource usage during parallel execution

3. **Error Handling**: Configure appropriate retry and timeout settings for critical tasks in the flow.

4. **Result Transformation**: Use transformers to modify task outputs before they are passed to child tasks.

5. **Result Aggregation**: Use aggregators to combine results from multiple child tasks into a single result.

## Troubleshooting

### Task Tree Flow Not Executing

If a task tree flow is not executing when the associated task is run, check the following:

1. Ensure the task has a valid `tree_flow_id` that corresponds to an existing tree flow
2. Verify that the tree flow has at least one root node
3. Check that the task runner has been properly initialized with the task manager

### Execution Errors

If errors occur during tree flow execution:

1. Check the logs for specific error messages
2. Verify that all tasks in the flow are properly configured
3. Ensure that any dependencies between tasks are correctly set up
4. Check for timeout or retry configuration issues

## Conclusion

The integration of Task Tree Flows with the existing Task Management system provides a powerful way to organize and execute complex task hierarchies. By associating tasks with tree flows, you can leverage the advanced execution strategies, transformers, and aggregators provided by the Task Tree Flow system while maintaining compatibility with the existing task execution mechanisms. 