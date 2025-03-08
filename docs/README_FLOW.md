# Task Flow Framework

## Overview

The Task Flow Framework is a powerful system for creating and executing sequences of tasks with transformations between them. It allows you to build complex workflows by chaining multiple AI tasks together, with each task's output serving as input for the next task after appropriate transformation.

## Key Components

### TaskFlow

A container for a sequence of tasks with transformations between them. Each flow has:
- A unique ID
- A name and description
- A reference to a TasksManager
- A list of TaskFlowSteps
- A session ID for tracking execution

### TaskFlowStep

An individual step in a flow, containing:
- A task ID
- An optional name and description
- An optional transformer for modifying the output before passing to the next step
- Optional pre-execute and post-execute hooks
- Status tracking (pending, started, completed, failed)
- Result storage

### TaskFlowManager

Manages the creation and execution of task flows:
- Creates and stores flows
- Executes entire flows or individual steps
- Tracks flow execution status and results
- Handles error conditions

### Transformers

Two types of transformers are available:

1. **PromptTransformer**: Transforms the output of one task into a prompt for the next task.
   - Can add instructions, prefixes, or suffixes to content
   - Can use custom transformation functions
   - Creates properly formatted Message objects

2. **MessageTransformer**: Provides more advanced transformations for message structures.
   - Can include system messages from the target task
   - Can include message history from the source task
   - Can apply custom transformations to the entire message structure

## Creating a Task Flow

Here's how to create a flow with multiple tasks:

```python
# Create a task flow manager
flow_manager = TaskFlowManager(persistence_model)
await flow_manager.initialize()

# Create a new flow
flow = flow_manager.create_flow(
    name="Multi-Task Flow",
    description="A flow with multiple tasks",
    tasksmanager_id=manager.id
)

# Add multiple tasks to the flow
flow.add_task(task1.id, name="Task 1")
flow.add_task(task2.id, name="Task 2", transformer=transformer1)
flow.add_task(task3.id, name="Task 3", transformer=transformer2)
flow.add_task(task4.id, name="Task 4", transformer=transformer3)
```

## Executing a Task Flow

Flows are executed sequentially, with each step's output being transformed and passed to the next step:

```python
# Execute the entire flow
result = await flow_manager.execute_flow(
    flow_id=flow.id,
    initial_context={"input_data": input_data}
)

# Or execute a single step
step_result = await flow_manager.execute_flow_step(
    flow_id=flow.id,
    step_index=1,
    context=context
)
```

## Creating Transformers

### PromptTransformer

```python
# Create a transformer with instructions
transformer = PromptTransformer(
    instructions="Please analyze this text"
)

# Or with prefix and suffix
transformer = PromptTransformer(
    prefix="ANALYZE: ",
    suffix=" END OF ANALYSIS REQUEST"
)

# Or with a custom transformation function
def custom_transform(content, target_task):
    return f"Custom transformation: {content}"

transformer = PromptTransformer(
    transform_func=custom_transform
)
```

### MessageTransformer

```python
# Create a message transformer that includes history
transformer = MessageTransformer(
    include_system_messages=True,
    include_history=True,
    max_history=5
)

# Or with a custom transformation function
def custom_message_transform(messages, source_task, target_task):
    # Custom transformation logic
    return messages

transformer = MessageTransformer(
    transform_func=custom_message_transform
)
```

## Using Pre-execute and Post-execute Hooks

Hooks allow for custom processing before or after a step executes:

```python
def pre_execute_hook(context, previous_result, task):
    """Modify context before task execution"""
    context["additional_data"] = "Some additional data"
    return context

def post_execute_hook(result, context, task):
    """Modify result after task execution"""
    result["additional_info"] = "Some additional info"
    return result

# Add hooks to a step
step = flow.steps[0]
step.pre_execute_hook = pre_execute_hook
step.post_execute_hook = post_execute_hook
```

## Example: Three-Task Flow

Here's an example of creating a flow with three tasks:

```python
# Create three tasks
task1 = Task(name="Data Extraction", ...)  # Extracts data
task2 = Task(name="Analysis", ...)         # Analyzes the data
task3 = Task(name="Report Generation", ...) # Generates a report

# Create transformers
extraction_to_analysis = PromptTransformer(
    instructions="Analyze the following extracted data"
)
analysis_to_report = PromptTransformer(
    instructions="Generate a report based on this analysis"
)

# Create the flow
flow = flow_manager.create_flow(
    name="Data Processing Flow",
    description="Extract, analyze, and report on data",
    tasksmanager_id=manager.id
)

# Add tasks with transformers
flow.add_task(task1.id, name="Extract")
flow.add_task(task2.id, name="Analyze", transformer=extraction_to_analysis)
flow.add_task(task3.id, name="Report", transformer=analysis_to_report)

# Execute the flow
result = await flow_manager.execute_flow(
    flow_id=flow.id,
    initial_context={"input_data": input_data}
)
```

## Transforming First Input and Last Output

### Using Hooks

```python
def first_step_pre_hook(context, previous_result, task):
    """Transform the initial input before the first task runs"""
    if 'messages' in context and isinstance(context['messages'], list):
        # Get the user message
        for i, msg in enumerate(context['messages']):
            if msg.role == 'user':
                # Transform the user message
                transformed_content = f"Enhanced input: {msg.content}"
                context['messages'][i] = Message(role='user', content=transformed_content)
    return context

def last_step_post_hook(result, context, task):
    """Transform the final output after the last task runs"""
    if isinstance(result, dict) and 'response' in result:
        # Transform the response
        result['response'] = f"Final enhanced output: {result['response']}"
    return result

# Add hooks to first and last steps
flow.steps[0].pre_execute_hook = first_step_pre_hook
flow.steps[-1].post_execute_hook = last_step_post_hook
```

### Using Dedicated Transformer Tasks

```python
# Create a flow with transformer tasks at beginning and end
flow = flow_manager.create_flow(
    name="Flow with Input/Output Transformers",
    description="A flow with dedicated transformer tasks",
    tasksmanager_id=manager.id
)

# Add an input transformer task
flow.add_task(input_transformer_task.id, name="Input Transformer")

# Add your main processing tasks
flow.add_task(main_task1.id, name="Process 1", transformer=transformer1)
flow.add_task(main_task2.id, name="Process 2", transformer=transformer2)

# Add an output transformer task
flow.add_task(output_transformer_task.id, name="Output Transformer")
```

## Best Practices

1. **Task Design**: Design tasks to be modular and focused on a single responsibility.
2. **Transformer Selection**: Choose the appropriate transformer type based on your needs:
   - Use PromptTransformer for simple content transformations
   - Use MessageTransformer for complex message structure transformations
3. **Context Management**: Use the context to pass data between steps effectively.
4. **Error Handling**: Implement proper error handling in pre/post-execute hooks.
5. **Testing**: Test each task individually before combining them in a flow.
6. **Message Validation**: Ensure all messages are properly formatted Message objects.
7. **Flow Organization**: Keep flows organized with clear naming and descriptions.

## Debugging

The task flow framework includes extensive debugging output that can be enabled to troubleshoot issues:

- Transformer operations are logged with detailed information
- Message validation is performed at multiple points
- Step execution status is tracked and reported
- Errors are captured and included in the flow results

## Advanced Features

- **Session Management**: Each flow has a session ID for tracking execution
- **Status Tracking**: Each step's status, result, and execution time are tracked
- **Error Handling**: If a step fails, the flow execution stops and the error is captured
- **Context Propagation**: Context is passed between steps and can be modified by hooks
- **Result Aggregation**: Results from all steps are collected and returned 