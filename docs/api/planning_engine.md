# Planning Engine API Documentation

## Overview

The Planning Engine API provides a comprehensive set of methods for creating, managing, and visualizing plans within the Self-Aware System. This document describes the available API methods, their parameters, return values, and usage examples.

## Core Planning Engine API

### create_integrated_plan

Creates a comprehensive integrated plan that combines goal decomposition, research planning, implementation planning, and resource allocation.

**Method Signature:**
```python
async def create_integrated_plan(
    self,
    name: str,
    description: str,
    goal: Dict[str, Any],
    strategy: str = "TOP_DOWN",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `name` (str): Name of the integrated plan
- `description` (str): Description of the integrated plan
- `goal` (Dict[str, Any]): Goal dictionary containing name, description, goal_type, requirements, and other goal-specific fields
- `strategy` (str, optional): Strategy for goal decomposition ("TOP_DOWN", "BOTTOM_UP", or "HYBRID"). Default: "TOP_DOWN"
- `metadata` (Dict[str, Any], optional): Additional metadata for the plan

**Returns:**
- Dictionary containing the created plan details including:
  - `id`: Unique identifier for the plan
  - `name`: Plan name
  - `description`: Plan description
  - `goal_decomposition_id`: ID of the associated goal decomposition
  - `research_plan_id`: ID of the associated research plan (if applicable)
  - `implementation_plan_id`: ID of the associated implementation plan (if applicable)
  - `resource_allocation_id`: ID of the associated resource allocation plan (if applicable)
  - `creation_time`: Timestamp of plan creation
  - `status`: Current status of the plan
  - `metrics`: Planning metrics
  - `version_history`: List of version information
  - `metadata`: Additional plan metadata

**Example:**
```python
plan_result = await self_aware_system.create_integrated_plan(
    name="New Feature Planning",
    description="Comprehensive plan for implementing Feature X",
    goal={
        "name": "Implement Feature X",
        "description": "Add Feature X to the product",
        "goal_type": "IMPLEMENTATION",
        "requirements": ["Must support API Y", "Must be scalable"],
        "success_criteria": ["Passes all tests", "Meets performance requirements"]
    },
    strategy="TOP_DOWN",
    metadata={"priority": "high", "requested_by": "product_team"}
)
```

### get_integrated_plan

Retrieves an integrated plan by its ID.

**Method Signature:**
```python
async def get_integrated_plan(
    self,
    plan_id: str
) -> Dict[str, Any]
```

**Parameters:**
- `plan_id` (str): ID of the integrated plan to retrieve

**Returns:**
- Dictionary containing the plan details (same structure as the return value of `create_integrated_plan`)

**Example:**
```python
plan = await self_aware_system.get_integrated_plan("plan-123")
```

### update_integrated_plan

Updates an existing integrated plan and creates a new version based on the provided updates.

**Method Signature:**
```python
async def update_integrated_plan(
    self,
    plan_id: str,
    updates: Dict[str, Any],
    change_description: str
) -> Dict[str, Any]
```

**Parameters:**
- `plan_id` (str): ID of the integrated plan to update
- `updates` (Dict[str, Any]): Dictionary containing fields to update
- `change_description` (str): Description of the changes being made

**Returns:**
- Dictionary containing the updated plan details

**Example:**
```python
updated_plan = await self_aware_system.update_integrated_plan(
    plan_id="plan-123",
    updates={
        "name": "Updated Feature Plan",
        "description": "Revised plan for Feature X implementation",
        "metadata": {"priority": "critical"}
    },
    change_description="Updated priority and refined description"
)
```

### list_integrated_plans

Lists all integrated plans, optionally filtered by type, status, or creation time range.

**Method Signature:**
```python
async def list_integrated_plans(
    self,
    plan_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]
```

**Parameters:**
- `plan_type` (str, optional): Filter by plan type
- `status` (str, optional): Filter by plan status
- `start_time` (str, optional): Filter by creation time (start of range, ISO format)
- `end_time` (str, optional): Filter by creation time (end of range, ISO format)
- `limit` (int, optional): Maximum number of plans to return. Default: 100

**Returns:**
- List of dictionaries containing plan summary information

**Example:**
```python
research_plans = await self_aware_system.list_integrated_plans(
    plan_type="RESEARCH",
    status="COMPLETED",
    start_time="2023-01-01T00:00:00Z",
    limit=50
)
```

## Planning Workflow API

### create_research_driven_workflow

Creates a research-driven planning workflow that focuses on knowledge gathering and analysis before implementation planning.

**Method Signature:**
```python
async def create_research_driven_workflow(
    self,
    name: str,
    description: str,
    initial_goal: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `name` (str): Name of the workflow
- `description` (str): Description of the workflow
- `initial_goal` (Dict[str, Any]): Initial goal dictionary that includes research requirements
- `context` (Dict[str, Any], optional): Additional context information for the workflow

**Returns:**
- Dictionary containing workflow information including:
  - `workflow_id`: Unique identifier for the workflow
  - `name`: Workflow name
  - `description`: Workflow description
  - `type`: Workflow type ("research_driven")
  - `creation_time`: Timestamp of workflow creation
  - `steps`: Dictionary of workflow steps

**Example:**
```python
workflow = await self_aware_system.create_research_driven_workflow(
    name="AI Technology Research",
    description="Research workflow for exploring new AI techniques",
    initial_goal={
        "name": "Research LLM Applications",
        "description": "Explore potential applications of LLMs in our product",
        "goal_type": "RESEARCH",
        "knowledge_gaps": ["Performance characteristics", "Integration challenges"],
        "requirements": ["Must be production-ready", "Must meet security standards"]
    },
    context={"existing_knowledge": "basic_llm_concepts", "priority": "high"}
)
```

### create_implementation_focused_workflow

Creates an implementation-focused planning workflow that emphasizes solution design and resource allocation.

**Method Signature:**
```python
async def create_implementation_focused_workflow(
    self,
    name: str,
    description: str,
    implementation_requirements: List[str],
    constraints: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `name` (str): Name of the workflow
- `description` (str): Description of the workflow
- `implementation_requirements` (List[str]): List of implementation requirements
- `constraints` (List[str], optional): List of implementation constraints
- `context` (Dict[str, Any], optional): Additional context information for the workflow

**Returns:**
- Dictionary containing workflow information (similar to `create_research_driven_workflow`)

**Example:**
```python
workflow = await self_aware_system.create_implementation_focused_workflow(
    name="Feature X Implementation",
    description="Implementation workflow for Feature X",
    implementation_requirements=[
        "Must support 1000 concurrent users",
        "Must integrate with existing API",
        "Must maintain backward compatibility"
    ],
    constraints=[
        "Must be completed within 2 weeks",
        "Must use existing database structure",
        "Must not require additional infrastructure"
    ],
    context={"priority": "high", "existing_codebase": "v2.5.1"}
)
```

### execute_planning_workflow

Executes a planning workflow, processing all workflow steps in order based on their dependencies.

**Method Signature:**
```python
async def execute_planning_workflow(
    self,
    workflow_id: str
) -> Dict[str, Any]
```

**Parameters:**
- `workflow_id` (str): ID of the workflow to execute

**Returns:**
- Dictionary containing execution results including:
  - `workflow_id`: ID of the executed workflow
  - `status`: Final status of the workflow
  - `result`: Result details including created plan IDs
  - `completed_steps`: List of completed workflow steps

**Example:**
```python
execution_result = await self_aware_system.execute_planning_workflow("workflow-123")
```

### get_planning_workflow_status

Retrieves the current status of a planning workflow.

**Method Signature:**
```python
async def get_planning_workflow_status(
    self,
    workflow_id: str
) -> Dict[str, Any]
```

**Parameters:**
- `workflow_id` (str): ID of the workflow to check

**Returns:**
- Dictionary containing workflow status information including:
  - `workflow_id`: ID of the workflow
  - `status`: Current status of the workflow
  - `steps`: Dictionary of step statuses
  - `completion_percentage`: Percentage of workflow completion

**Example:**
```python
status = await self_aware_system.get_planning_workflow_status("workflow-123")
print(f"Workflow is {status['completion_percentage']}% complete")
```

## Visualization API

### visualize_integrated_plan

Creates a visualization of an integrated plan.

**Method Signature:**
```python
async def visualize_integrated_plan(
    self,
    plan_id: str,
    visualization_type: str,
    output_format: str = "json",
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `plan_id` (str): ID of the plan to visualize
- `visualization_type` (str): Type of visualization to create ("goal_hierarchy", "dependency_graph", "resource_allocation", or "timeline")
- `output_format` (str, optional): Output format for the visualization ("json", "html", "mermaid", "d3", or "plotly"). Default: "json"
- `context` (Dict[str, Any], optional): Additional context for visualization

**Returns:**
- Dictionary containing visualization information including:
  - `id`: Unique identifier for the visualization
  - `plan_id`: ID of the visualized plan
  - `type`: Visualization type
  - `format`: Output format
  - `content_type`: MIME type of the content
  - `content`: Visualization content

**Example:**
```python
visualization = await self_aware_system.visualize_integrated_plan(
    plan_id="plan-123",
    visualization_type="goal_hierarchy",
    output_format="html"
)
```

## Metrics API

### get_plan_metrics

Retrieves metrics for a specific plan, optionally including trend analysis.

**Method Signature:**
```python
async def get_plan_metrics(
    self,
    plan_id: str,
    include_trends: bool = True
) -> Dict[str, Any]
```

**Parameters:**
- `plan_id` (str): ID of the plan to retrieve metrics for
- `include_trends` (bool, optional): Whether to include trend analysis. Default: True

**Returns:**
- Dictionary containing metrics information including:
  - `plan_id`: ID of the plan
  - `report_time`: Timestamp of the report generation
  - `metrics`: Dictionary of the latest metric values
  - `trends`: Dictionary of trend analysis (if requested)

**Example:**
```python
metrics = await self_aware_system.get_plan_metrics("plan-123")
print(f"Planning time: {metrics['metrics']['time']['latest_value']}")
print(f"Time trend: {metrics['trends']['time']['trend_direction']}")
```

### compare_plans

Compares metrics across multiple plans, generating a visualization of the comparison.

**Method Signature:**
```python
async def compare_plans(
    self,
    plan_ids: List[str],
    comparison_metrics: Optional[List[str]] = None,
    output_format: str = "json"
) -> Dict[str, Any]
```

**Parameters:**
- `plan_ids` (List[str]): List of plan IDs to compare
- `comparison_metrics` (List[str], optional): List of specific metrics to compare
- `output_format` (str, optional): Output format for the comparison ("json", "html", or "plotly"). Default: "json"

**Returns:**
- Dictionary containing comparison information including:
  - `id`: Unique identifier for the comparison
  - `type`: Visualization type ("comparison")
  - `format`: Output format
  - `content_type`: MIME type of the content
  - `content`: Comparison content
  - `plan_count`: Number of plans compared
  - `metric_count`: Number of metrics compared

**Example:**
```python
comparison = await self_aware_system.compare_plans(
    plan_ids=["plan-123", "plan-456", "plan-789"],
    comparison_metrics=["planning_time", "complexity_score", "confidence_score"],
    output_format="html"
)
```

## Error Handling

All API methods follow consistent error handling patterns:

1. **ValidationError**: Raised when input parameters fail validation
2. **NotFoundError**: Raised when requested resources don't exist
3. **StateError**: Raised when operation cannot be performed in current state
4. **StorageError**: Raised when storage operations fail
5. **ComponentError**: Raised when planning component operations fail

Example error handling:

```python
try:
    plan = await self_aware_system.get_integrated_plan("non-existent-id")
except NotFoundError as e:
    print(f"Plan not found: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

## Asynchronous Operation

All API methods are asynchronous (using `async/await`) and should be called accordingly. This allows for non-blocking operation and efficient resource usage, especially for long-running planning operations.

## API Versioning

The Planning Engine API follows semantic versioning. Breaking changes will only be introduced in major version updates. The current API version can be obtained via:

```python
version_info = self_aware_system.get_component_version("planning_engine")
``` 