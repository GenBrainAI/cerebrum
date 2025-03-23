# Planning Engine Integration

## Overview

The Planning Engine integration enhances the Self-Aware System with advanced planning capabilities, enabling it to decompose complex goals, develop research strategies, create implementation plans, and allocate resources effectively. This document outlines the Planning Engine architecture, its key components, and how they integrate with the broader Self-Aware System.

## Architecture

The Planning Engine consists of six main components:

1. **Planning Engine Core** - The central orchestrator that integrates all planning components
2. **Planning Engine Configuration Manager** - Manages configuration for all planning components
3. **Planning Engine Factory** - Creates Planning Engine instances with various configurations
4. **Planning Engine Workflow Manager** - Orchestrates cross-component planning workflows
5. **Planning Engine Metrics Collector** - Collects and analyzes planning-related metrics
6. **Planning Engine Visualization** - Visualizes planning components and outputs

These components work together to provide comprehensive planning capabilities while maintaining separation of concerns and modularity.

## Component Details

### Planning Engine Core

The Planning Engine Core orchestrates the entire planning process, integrating goal decomposition, research planning, implementation planning, and resource allocation. It maintains integrated plans and their version history, allowing for plan updates and tracking of planning metrics.

**Key Features:**
- Creation of complete integrated plans
- Plan versioning and update management
- Planning metrics calculation and tracking
- Component coordination and integration

### Planning Engine Configuration Manager

The Configuration Manager provides a centralized system for managing planning engine settings across all components. It supports loading and saving configurations, component-specific settings, and optimization goal settings.

**Key Features:**
- Default configuration management
- Configuration loading and saving
- Component-specific configuration retrieval
- Optimization goal settings

### Planning Engine Factory

The Factory creates Planning Engine instances with various component combinations and configurations. It simplifies the initialization process and ensures proper dependency injection and component creation.

**Key Features:**
- Flexible component inclusion/exclusion
- Configuration integration
- Knowledge system integration
- Component initialization

### Planning Engine Workflow Manager

The Workflow Manager orchestrates cross-component workflows for different planning scenarios. It provides predefined workflow templates and manages workflow execution, tracking status and handling dependencies.

**Key Features:**
- Research-driven workflow management
- Implementation-focused workflow management
- Workflow execution and status tracking
- Step dependency resolution

### Planning Engine Metrics Collector

The Metrics Collector gathers, analyzes, and reports metrics related to planning activities. It tracks metrics over time, calculates trends, and provides reporting capabilities for performance analysis.

**Key Features:**
- Metric collection and storage
- Trend analysis
- Report generation
- Plan comparison

### Planning Engine Visualization

The Visualization component provides visual representations of planning components and outputs. It supports various visualization types and output formats, enhancing the interpretability of planning results.

**Key Features:**
- Integrated plan visualization
- Metrics trend visualization
- Plan comparison visualization
- Multiple output format support

## Integration with Self-Aware System

The Planning Engine is integrated with the Self-Aware System via the `self_aware_integration.py` module. The integration provides the following capabilities:

1. **Initialization** - Planning Engine components are initialized during Self-Aware System startup
2. **Plan Management** - Creation, retrieval, updating, and listing of integrated plans
3. **Workflow Execution** - Creation and execution of planning workflows
4. **Visualization** - Access to visualization capabilities for plans and metrics
5. **Metrics Analysis** - Tracking and analysis of planning metrics

## Usage Examples

### Creating an Integrated Plan

```python
plan_result = await self_aware_system.create_integrated_plan(
    name="New Project Plan",
    description="Planning for the new product feature",
    goal={
        "name": "Implement Feature X",
        "description": "Add new capability to the product",
        "goal_type": "IMPLEMENTATION",
        "requirements": ["Requirement 1", "Requirement 2"],
        "success_criteria": ["Criteria 1", "Criteria 2"]
    },
    strategy="TOP_DOWN"
)
```

### Creating and Executing a Research-Driven Workflow

```python
workflow_result = await self_aware_system.create_research_driven_workflow(
    name="Research Workflow",
    description="Research workflow for new technology",
    initial_goal={
        "name": "Research Technology Y",
        "description": "Investigate potential applications of Technology Y",
        "goal_type": "RESEARCH",
        "knowledge_gaps": ["Gap 1", "Gap 2"]
    }
)

workflow_id = workflow_result["workflow_id"]
execution_result = await self_aware_system.execute_planning_workflow(workflow_id)
```

### Visualizing an Integrated Plan

```python
visualization = await self_aware_system.visualize_integrated_plan(
    plan_id="plan-123",
    visualization_type="goal_hierarchy",
    output_format="html"
)
```

### Comparing Multiple Plans

```python
comparison = await self_aware_system.compare_plans(
    plan_ids=["plan-123", "plan-456"],
    comparison_metrics=["planning_time", "complexity_score", "confidence_score"],
    output_format="html"
)
```

## Data Model

### Integrated Plan

An Integrated Plan represents a comprehensive plan that combines multiple planning components:

```
{
    "id": string,
    "name": string,
    "description": string,
    "goal_decomposition_id": string,
    "research_plan_id": string,
    "implementation_plan_id": string,
    "resource_allocation_id": string,
    "creation_time": timestamp,
    "status": string,
    "metrics": {
        "planning_time": number,
        "complexity_score": number,
        "confidence_score": number,
        "resource_efficiency": number,
        "adaptability_score": number
    },
    "version_history": [
        {
            "version_id": string,
            "timestamp": timestamp,
            "changes": string,
            "metadata": object
        }
    ],
    "metadata": object
}
```

### Planning Workflow

A Planning Workflow represents a series of planning steps with dependencies:

```
{
    "workflow_id": string,
    "name": string,
    "description": string,
    "type": string,
    "creation_time": timestamp,
    "status": string,
    "steps": {
        "step_id": {
            "name": string,
            "status": string,
            "dependencies": [string],
            "result": object
        }
    },
    "metadata": object
}
```

### Planning Metrics

Planning Metrics represent various measurements of planning performance:

```
{
    "plan_id": string,
    "metrics": {
        "planning_time": {
            "latest_value": number,
            "snapshot_count": number
        },
        "complexity_score": {
            "latest_value": number,
            "snapshot_count": number
        }
    },
    "trends": {
        "planning_time": {
            "mean": number,
            "median": number,
            "min": number,
            "max": number,
            "std_dev": number,
            "trend_direction": string,
            "rate_of_change": number
        }
    }
}
```

## Configuration

The Planning Engine configuration is managed through JSON files with the following structure:

```json
{
    "general": {
        "default_strategy": "TOP_DOWN",
        "optimization_goal": "BALANCED"
    },
    "goal_decomposition": {
        "max_goal_depth": 5,
        "min_goal_confidence": 0.7
    },
    "research_planning": {
        "knowledge_source_count": 3,
        "knowledge_gap_threshold": 0.6
    },
    "implementation_planning": {
        "task_granularity": "MEDIUM",
        "dependency_detection_threshold": 0.8
    },
    "resource_allocation": {
        "resource_buffer_percentage": 20,
        "allocation_strategy": "BALANCED"
    }
}
```

## Error Handling

The Planning Engine implements comprehensive error handling:

1. **Input Validation** - All inputs are validated before processing
2. **Component Failures** - Failures in individual components are isolated and reported
3. **Workflow Errors** - Workflow execution errors are tracked and reported
4. **Configuration Issues** - Configuration loading failures are handled gracefully
5. **Storage Problems** - Storage-related errors are caught and reported

## Testing

The Planning Engine integration includes comprehensive tests in `tests/self_aware/planning/test_planning_integration.py`. The tests cover:

1. **Initialization** - Verifying proper component initialization
2. **Plan Creation** - Testing integrated plan creation and retrieval
3. **Plan Updates** - Testing plan update functionality
4. **Workflow Execution** - Testing workflow creation and execution
5. **Visualization** - Testing visualization capabilities
6. **Metrics** - Testing metrics collection and reporting

## Future Enhancements

Planned future enhancements for the Planning Engine integration:

1. **Advanced Dependency Analysis** - Enhanced detection of dependencies between plan components
2. **Collaborative Planning** - Support for multiple agents contributing to plan development
3. **Plan Evaluation** - Automated evaluation of plan quality and feasibility
4. **Learning from Execution** - Improving planning based on execution results
5. **Dynamic Workflow Adaptation** - Adapting workflows based on intermediate results 