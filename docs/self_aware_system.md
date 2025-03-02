# Self-Aware System

The Self-Aware System is a core component of Cerebrum that integrates various subsystems to create a cohesive, self-improving AI framework. This system can monitor its own performance, manage resources, execute tasks in parallel, and continuously improve through a cognitive loop process.

## Architecture

The Self-Aware System integrates the following components:

### Core Components

1. **AI Parameter Manager**: Optimizes and manages AI model parameters for different tasks.
2. **Knowledge Integration System**: Manages different types of knowledge (semantic, procedural, episodic).
3. **Development Cognitive Loop Orchestrator**: Coordinates the cognitive development cycle.

### Execution Layer

4. **Parallel Execution Controller**: Manages parallel execution of tasks with resource awareness.

### System Access Layer

5. **Package Manager**: Manages Python package installation and dependencies.
6. **Git Manager**: Provides Git operations for version control.
7. **Test Runner**: Discovers and runs tests, collects coverage information.

### Observability Layer

8. **Supervision Hub**: Manages approval workflows for sensitive operations.
9. **Resource Monitor**: Tracks and manages system resource usage.
10. **Metrics Collector**: Collects and analyzes system performance metrics.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Self-Aware System                           │
├─────────────┬─────────────┬────────────────┬────────────────────────┤
│  Knowledge  │ Parameter   │  Cognitive     │                        │
│ Integration │ Manager     │  Loop          │                        │
│   System    │             │ Orchestrator   │                        │
├─────────────┴─────────────┴────────────────┤     Parallel          │
│              Execution Layer                │     Execution         │
│                                             │     Controller        │
├─────────────┬─────────────┬────────────────┤                        │
│  Package    │    Git      │    Test        │                        │
│  Manager    │   Manager   │    Runner      │                        │
├─────────────┴─────────────┴────────────────┼────────────────────────┤
│             Observability Layer             │                        │
├─────────────┬─────────────┬────────────────┤                        │
│ Supervision │  Resource   │    Metrics     │                        │
│    Hub      │   Monitor   │   Collector    │                        │
└─────────────┴─────────────┴────────────────┴────────────────────────┘
```

## Key Features

- **Self-Improvement**: The system can analyze its own performance and make improvements.
- **Resource Awareness**: Monitors and manages system resources efficiently.
- **Parallel Execution**: Executes tasks in parallel with dependency management.
- **Approval Workflows**: Sensitive operations require explicit approval.
- **Knowledge Management**: Maintains different types of knowledge for better decision-making.
- **Metrics Collection**: Tracks performance metrics for analysis and optimization.
- **System Access**: Safely interacts with external systems (packages, Git, tests).

## Usage

### Initialization

```python
from src.server.self_aware_integration import SelfAwareSystem

# Initialize the system
system = SelfAwareSystem()

# Custom storage path
# system = SelfAwareSystem(storage_path="/path/to/storage")
```

### Cognitive Loop

```python
# Start a cognitive cycle
task_id = await system.start_cognitive_cycle()

# Start continuous operation
await system.start_continuous_operation(interval_seconds=60.0)
```

### Parallel Execution

```python
# Define tasks
tasks = [
    {
        "coroutine": some_async_function(),
        "resource_requirements": {"cpu": 0.5, "memory": 200},
        "dependencies": []
    },
    {
        "coroutine": another_async_function(),
        "resource_requirements": {"cpu": 0.3, "memory": 100},
        "dependencies": []
    }
]

# Execute tasks in parallel
results = await system.execute_tasks_in_parallel(tasks, strategy="resource_aware")

# Add a single task
task_id = await system.add_parallel_task(
    coroutine=some_async_function(),
    resource_requirements={"cpu": 0.5, "memory": 200}
)

# Wait for a task to complete
result = await system.wait_for_parallel_task(task_id)
```

### Package Management

```python
# List installed packages
packages = await system.list_installed_packages()

# Install a package
result = await system.install_package("requests", version="2.28.1")

# Uninstall a package
result = await system.uninstall_package("requests")
```

### Git Operations

```python
# Get repository status
status = await system.get_repository_status()

# Clone a repository
result = await system.clone_repository(
    url="https://github.com/username/repo.git",
    path="./repos/my_repo",
    branch="main"
)

# Commit changes
result = await system.commit_changes(
    message="Update documentation",
    files=["README.md", "docs/usage.md"]
)
```

### Test Operations

```python
# Discover tests
tests = await system.discover_tests(path="./tests", pattern="test_*.py")

# Run tests
results = await system.run_tests(test_path="./tests")

# Get test coverage
coverage = await system.get_test_coverage()
```

### Resource Monitoring

```python
# Get current resource usage
usage = await system.get_current_resource_usage()

# Set a resource budget
budget = await system.set_resource_budget("cpu", 90.0, period="hourly")

# Check a resource budget
check = await system.check_resource_budget("cpu")

# Record resource usage
await system.record_resource_usage("api_calls", 10, operation_id="example_op")
```

### Metrics Collection

```python
# Record a metric
await system.record_metric("response_time", 0.25, tags={"endpoint": "/api/data"})

# Get metrics
metrics = await system.get_metrics(
    metric_name="response_time",
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now(),
    aggregation="avg"
)

# Get system health
health = await system.get_system_health()
```

### Knowledge Management

```python
# Add semantic knowledge
system.add_semantic_knowledge(
    concept="Self-Aware System",
    definition="A system that can monitor and improve itself.",
    related_concepts=["AI", "Self-Improvement"],
    tags=["system", "core"]
)

# Add procedural knowledge
system.add_procedural_knowledge(
    task_name="Initialize System",
    description="How to initialize the Self-Aware System.",
    steps=["Import the class", "Create an instance", "Start operations"],
    expected_outcome="A running Self-Aware System instance",
    tags=["initialization", "usage"]
)

# Add episodic knowledge
system.add_episodic_knowledge(
    title="System Initialization",
    description="The system was initialized successfully.",
    timestamp=datetime.now(),
    actors=["User"],
    tags=["initialization", "event"]
)

# Get knowledge context
context = system.get_knowledge_context("self-aware system")
```

### Supervision

```python
# Register a supervisor
result = await system.register_supervisor(
    user_id="admin_user",
    role="admin",
    permissions=["approve_packages", "approve_git_operations"]
)

# Get pending requests
requests = await system.get_pending_requests(role="admin")

# Approve a request
result = await system.approve_request(
    request_id="request_123",
    supervisor_id="admin_user",
    comments="Approved after code review"
)
``` 