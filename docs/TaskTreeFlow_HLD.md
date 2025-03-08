# Task Tree Flow: High-Level Design Document

## 1. Executive Summary

This document outlines the design for enhancing the Task Tree framework with Flow capabilities, specifically focusing on integrating transformation capabilities between task nodes. The goal is to unify the two existing implementations (task_tree_controller.py and models/tasktree.py) into a single, coherent system that supports both hierarchical task execution and data transformation between tasks.

## 2. Current State Analysis

### 2.1 Existing Implementations

Currently, there are two separate implementations of task trees:

1. **Controller Implementation (task_tree_controller.py)**:
   - Robust aggregation system with multiple aggregator types
   - Comprehensive execution strategies (Sequential, Parallel, Parallel with limit)
   - Advanced state tracking and error handling
   - Retry mechanisms and timeout handling

2. **Model Implementation (models/tasktree.py)**:
   - Plugin-based architecture
   - Simpler node structure
   - Support for execution order determination
   - Less sophisticated aggregation capabilities

### 2.2 Task Flow Implementation

The Task Flow system (task_flow_manager.py) provides:
- Sequential execution of tasks
- Transformation of data between tasks using PromptTransformer and MessageTransformer
- Pre-execute and post-execute hooks
- Comprehensive state tracking

### 2.3 Gaps in Current Implementation

1. No transformation capabilities in task trees after aggregation
2. Duplicate implementations of task tree structures
3. No unified approach to handle both hierarchical execution and data transformation
4. Limited flexibility in how aggregated results are processed before being passed to parent nodes

## 3. Proposed Solution: Task Tree Flow

### 3.1 Core Concept

The Task Tree Flow will unify the existing implementations into a single, coherent system that supports:

1. Hierarchical task execution with multiple execution strategies
2. Rich aggregation capabilities for child task results
3. Transformation of aggregated results before passing to parent nodes
4. Comprehensive state tracking and error handling

### 3.2 Key Components

#### 3.2.1 Enhanced TaskNode

```python
class TaskNode:
    def __init__(
        self, 
        task: Task, 
        aggregator: TaskAggregator = AllAggregator(),
        transformer: Optional[PromptTransformer] = None,
        execution_config: Optional[ExecutionConfig] = None
    ):
        self.task = task
        self.aggregator = aggregator
        self.transformer = transformer
        self.children: List[TaskNode] = []
        self.dependencies: Set[TaskNode] = set()
        self.state = TaskNodeState(task_id=task.id, name=task.name)
        self.execution_config = execution_config or ExecutionConfig()
```

#### 3.2.2 Enhanced Run Method

```python
async def run(self, additional_info: Optional[Dict] = None) -> str:
    """Enhanced run method with transformation support"""
    try:
        if not self.can_execute():
            raise TaskExecutionError("Dependencies not satisfied")

        self.state.start_execution()
        context = additional_info or {}

        # Execute children based on strategy
        responses = await self._execute_children(context)

        # Aggregate child responses
        if responses:
            try:
                aggregated_response = self.aggregator.aggregate(responses)
                context["child_responses"] = responses
                context["aggregated_response"] = aggregated_response
                
                # Transform aggregated response if transformer exists
                if self.transformer:
                    transformed_response = self.transformer.transform(aggregated_response, self.task)
                    context["transformed_response"] = transformed_response
                    context["aggregated_response"] = transformed_response
            except Exception as e:
                raise TaskExecutionError(f"Aggregation/transformation failed: {str(e)}")

        # Execute this task with retry logic and timeout
        result = await self._execute_task_with_timeout(context)
        self.state.complete_execution(result)
        return result

    except Exception as e:
        self.state.fail_execution(str(e))
        raise TaskExecutionError(f"Task execution failed: {str(e)}")
```

#### 3.2.3 TaskTreeFlowManager

```python
class TaskTreeFlowManager:
    def __init__(self, persistence_model: 'PersistenceModelBase'):
        self.persistence_model = persistence_model
        self.nodes: Dict[str, TaskNode] = {}
        self.roots: Dict[str, TaskNode] = {}
        self.execution_groups: Dict[str, List[str]] = {}
        self.task_runner = None
        
    async def initialize(self):
        """Initialize the task tree flow manager"""
        from src.server.controllers.task_runner import TaskRunner
        
        if self.task_runner is None:
            self.task_runner = TaskRunner(self.persistence_model)
            await self.task_runner.initialize()
            
    def create_node(
        self, 
        task: Task, 
        aggregator: Optional[TaskAggregator] = None,
        transformer: Optional[PromptTransformer] = None,
        execution_config: Optional[ExecutionConfig] = None
    ) -> TaskNode:
        """Create a new task node with optional transformer"""
        node = TaskNode(
            task=task,
            aggregator=aggregator or AllAggregator(),
            transformer=transformer,
            execution_config=execution_config or ExecutionConfig()
        )
        self.nodes[task.id] = node
        return node
```

## 4. Detailed Design

### 4.1 Transformation Pipeline

The transformation pipeline in a task tree will work as follows:

1. Child tasks execute and produce results
2. Child results are collected based on execution strategy
3. Aggregator combines child results into a single aggregated response
4. Transformer (if present) transforms the aggregated response
5. Transformed response is added to context and passed to the parent task
6. Parent task executes with the transformed response in its context

### 4.2 Aggregator Types

We will maintain and enhance the existing aggregator types:

1. **AllAggregator**: Concatenates all responses with newlines
2. **CombineAggregator**: Combines responses into a single flow
3. **SummarizeAllAggregator**: Creates a summary of all responses
4. **FilterAggregator**: Filters responses based on a condition
5. **PrioritizeAggregator**: Prioritizes responses based on a scoring function
6. **ConsensusAggregator**: Requires consensus among responses

### 4.3 Transformer Types

We will support both existing transformer types:

1. **PromptTransformer**: Transforms content with instructions, prefix, suffix, or custom function
2. **MessageTransformer**: Provides advanced transformations for message structures

### 4.4 Execution Strategies

We will maintain the existing execution strategies:

1. **Sequential**: Execute tasks one after another
2. **Parallel**: Execute independent tasks in parallel
3. **Parallel with Limit**: Parallel execution with max concurrency

### 4.5 State Management

We will enhance the state management to track transformation details:

```python
class TaskNodeState(BaseModel):
    # Existing fields...
    transformation_applied: bool = False
    transformation_details: Optional[Dict[str, Any]] = None
    
    def record_transformation(self, original: str, transformed: str):
        """Record transformation details"""
        self.transformation_applied = True
        self.transformation_details = {
            "original": original,
            "transformed": transformed,
            "timestamp": datetime.now().isoformat()
        }
```

## 5. API Design

### 5.1 Creating a Task Tree with Transformers

```python
# Create a task tree flow manager
manager = TaskTreeFlowManager(persistence_model)
await manager.initialize()

# Create tasks
root_task = Task(id="root", name="Root Task")
child_task1 = Task(id="child1", name="Child Task 1")
child_task2 = Task(id="child2", name="Child Task 2")

# Create transformers
transformer = PromptTransformer(
    instructions="Analyze the following aggregated results"
)

# Create nodes with transformers
root_node = manager.create_node(root_task)
child_node1 = manager.create_node(child_task1)
child_node2 = manager.create_node(child_task2)

# Create a node with aggregator and transformer
aggregator = SummarizeAllAggregator()
root_node = manager.create_node(
    task=root_task,
    aggregator=aggregator,
    transformer=transformer
)

# Add child relationships
manager.add_child("root", "child1")
manager.add_child("root", "child2")

# Set execution configuration
manager.set_execution_config(
    "root",
    ExecutionConfig(
        strategy=ExecutionStrategy.PARALLEL,
        execute_children=True,
        propagate_context=True
    )
)

# Execute the tree
result = await manager.execute_node("root", context={})
```

### 5.2 REST API Endpoints

```
# Create a task node with transformer
POST /tasksmanager/{tasksmanager_id}/task/{task_id}/tree/node
{
    "aggregator_type": "summarize_all",
    "transformer": {
        "type": "prompt",
        "instructions": "Analyze the following aggregated results",
        "prefix": null,
        "suffix": null
    },
    "execution_config": {
        "strategy": "parallel",
        "execute_children": true,
        "propagate_context": true
    }
}

# Update a node's transformer
PUT /tasksmanager/{tasksmanager_id}/task/{task_id}/tree/transformer
{
    "type": "prompt",
    "instructions": "New instructions for transformation",
    "prefix": "PREFIX: ",
    "suffix": " :SUFFIX"
}

# Execute a tree with context
POST /tasksmanager/{tasksmanager_id}/task/{task_id}/tree/execute
{
    "context": {
        "input_data": "Data to process"
    },
    "session_id": "optional-session-id"
}
```

## 6. Implementation Strategy

### 6.1 Phase 1: Unification

1. Merge the two existing implementations into a single TaskTreeController
2. Ensure backward compatibility with existing code
3. Add comprehensive tests for the unified implementation

### 6.2 Phase 2: Transformation Integration

1. Add transformer support to TaskNode
2. Enhance the run method to apply transformations
3. Update the TaskTreeManager to support transformer creation and configuration
4. Add tests for transformation capabilities

### 6.3 Phase 3: API Enhancement

1. Update REST API to support transformer configuration
2. Add endpoints for managing transformers
3. Update documentation and examples

### 6.4 Phase 4: Advanced Features

1. Add support for conditional transformations
2. Implement transformation caching for performance
3. Add visualization tools for transformation pipelines

## 7. Migration Plan

### 7.1 Code Migration

1. Create a new unified implementation in src/server/controllers/task_tree_flow.py
2. Deprecate but maintain the old implementations temporarily
3. Update references to use the new implementation
4. Remove old implementations after migration period

### 7.2 Data Migration

1. Create a migration script to convert existing task trees to the new format
2. Add transformer fields with null values to existing nodes
3. Test migration with production data
4. Deploy migration script before code changes

## 8. Testing Strategy

### 8.1 Unit Tests

1. Test each aggregator type
2. Test each transformer type
3. Test execution strategies
4. Test error handling and retry mechanisms

### 8.2 Integration Tests

1. Test complete task trees with transformations
2. Test API endpoints
3. Test migration from old to new format

### 8.3 Performance Tests

1. Test with large task trees
2. Test parallel execution performance
3. Test transformation performance with large datasets

## 9. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing functionality | High | Medium | Comprehensive testing, phased rollout |
| Performance degradation | Medium | Low | Performance testing, optimization |
| Complex migration | Medium | Medium | Detailed migration plan, rollback capability |
| Increased complexity | Low | High | Clear documentation, examples, abstraction |

## 10. Timeline and Milestones

| Phase | Milestone | Timeline |
|-------|-----------|----------|
| Phase 1 | Unified implementation | Week 1-2 |
| Phase 2 | Transformation integration | Week 3-4 |
| Phase 3 | API enhancement | Week 5 |
| Phase 4 | Advanced features | Week 6-8 |

## 11. Conclusion

The Task Tree Flow enhancement will unify the existing task tree implementations and add powerful transformation capabilities, creating a more flexible and powerful framework for complex task orchestration. By combining the hierarchical execution capabilities of task trees with the transformation capabilities of task flows, we will enable more sophisticated AI workflows while maintaining a clean, consistent API. 






Based on the High-Level Design document for the Task Tree Flow feature, here's a list of files that will need to be created or modified for implementation:
New Files to Create
src/server/controllers/task_tree_flow.py - The unified implementation combining both task tree approaches with transformation capabilities
src/server/models/task_tree_flow.py - Models for the new task tree flow system
src/server/api/routes/task_tree_flow.py - API endpoints for the task tree flow functionality
src/server/schemas/task_tree_flow.py - Pydantic schemas for API requests and responses
tests/task_tree_flow/test_task_tree_flow.py - Unit tests for the task tree flow implementation
tests/task_tree_flow/test_task_tree_flow_api.py - API tests for the task tree flow endpoints
tests/task_tree_flow/test_transformers.py - Tests for transformation capabilities
scripts/migrate_task_trees.py - Migration script for existing task trees
docs/task_tree_flow.md - Documentation for the task tree flow feature
Existing Files to Modify
src/server/controllers/task_tree_controller.py - Add deprecation notices and compatibility layer
src/server/models/tasktree.py - Add deprecation notices and compatibility layer
src/server/controllers/prompt_transformer.py - Enhance for task tree integration
src/server/controllers/task_runner.py - Update to support task tree flow execution
src/server/api/routes/task.py - Update to include task tree flow endpoints
src/server/api/routes/tasksmanager.py - Update to include task tree flow endpoints
src/server/main.py - Register new API routes
src/server/persistence/persistence_model.py - Add support for task tree flow persistence
src/server/persistence/crud_handlers.py - Add CRUD handlers for task tree flow objects
README.md - Update documentation to include task tree flow feature
Key Dependencies
src/server/models/task.py - Task model used by task nodes
src/server/models/tasks_manager.py - TasksManager model used by task tree flow
src/server/controllers/task_flow_manager.py - Reference for transformation implementation
src/server/persistence/persistence_model_base.py - Base persistence model
Configuration Files
pyproject.toml or requirements.txt - Update dependencies if needed
.github/workflows/test.yml - Update test workflow to include task tree flow tests
