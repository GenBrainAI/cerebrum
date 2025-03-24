# Execution Engine Module

## Overview

The Execution Engine module provides a robust framework for task selection, execution, and context management. It enables intelligent task prioritization, dependency resolution, and efficient context handling across task execution.

## Components

### 1. Task Selector
Responsible for selecting the next task to execute based on priorities, dependencies, and available resources.

- **TaskSelector**: Selects tasks based on priority, dependencies, and resource availability
- **PriorityCalculator**: Calculates task priorities based on various factors
- **DependencyResolver**: Analyzes and resolves task dependencies

### 2. Context Manager
Manages execution context across tasks, including validation, propagation, and optimization.

- **ContextManager**: Core class for managing context entries
- **ContextValidator**: Validates context values against defined rules
- **ContextPropagator**: Propagates context between tasks based on defined rules
- **ContextOptimizer**: Optimizes context storage and management for efficient execution

### 3. Execution Engine
Integrates the Task Selector and Context Manager to coordinate task execution.

- **ExecutionEngine**: Main class that orchestrates task execution, context management, and tracks execution state

## Usage

See the `example.py` file for a complete usage example. Here's a basic overview:

```python
from src.server.execution_engine import ExecutionEngine, TaskPriority, ContextType

# Create the execution engine
engine = ExecutionEngine()

# Set up context validation rules
engine.context_validator.add_type_validator("project_name", str)

# Create a task
task_id = engine.create_task(
    name="Process Data",
    description="Process input data",
    priority=TaskPriority.MEDIUM,
    context_requirements=["input_data"]
)

# Set context
engine.context_manager.set_context("input_data", {"samples": 1000}, ContextType.TASK)

# Execute tasks
while True:
    task = engine.select_next_task()
    if not task:
        break
    result = engine.execute_task(task.id)
```

## Key Features

- **Intelligent Task Selection**: Select tasks based on priorities, dependencies, and available resources
- **Context Management**: Track, validate, and propagate context between tasks
- **Dependency Resolution**: Analyze and resolve task dependencies
- **Execution Tracking**: Monitor execution state and history
- **Resource Management**: Track resource usage and availability

## Design Principles

- **Modularity**: Components are designed to be modular and reusable
- **Type Safety**: Extensive use of type hints for code clarity and safety
- **Testability**: Classes are designed for easy testing
- **Extensibility**: Framework can be extended with custom rules and components 