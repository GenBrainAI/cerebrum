from typing import Dict, List, Optional, Any, Union
import os
import logging
import asyncio
from datetime import datetime
import uuid

from src.server.context.parameter_manager import AIParameterManager
from src.server.context.knowledge_integration import KnowledgeIntegrationSystem, MemoryType
from src.server.system.cognitive_loop import (
    CognitiveLoopOrchestrator, 
    WorkerType, 
    CognitivePhase,
    TaskPriority,
    RequirementsWorker,
    PlanningWorker,
    ImplementationWorker,
    EvaluationWorker
)

# Import new components
from src.server.execution.parallel_controller import ParallelExecutionController, Task
from src.server.system_access.package_manager import PackageManager
from src.server.system_access.git_manager import GitManager
from src.server.system_access.test_runner import TestRunner
from src.server.observability.supervision_hub import SupervisionHub
from src.server.observability.resource_monitor import ResourceMonitor
from src.server.observability.metrics_collector import MetricsCollector

# Import self-modification components
from src.server.self_modification.code_generator import CodeGenerator
from src.server.self_modification.safety_validator import SafetyValidator
from src.server.self_modification.integration_manager import IntegrationManager
from src.server.self_modification.agentic_framework import AgenticDevelopmentController

logger = logging.getLogger(__name__)

class SelfAwareSystem:
    """
    Integration of the Self-Aware Cerebrum components:
    - AI Parameter Manager
    - Knowledge Integration System
    - Development Cognitive Loop Orchestrator
    - Parallel Execution Controller
    - System Access Layer (Package Manager, Git Manager, Test Runner)
    - Observability Layer (Supervision Hub, Resource Monitor, Metrics Collector)
    - Self-Modification Engine (Code Generator, Safety Validator, Integration Manager, Agentic Development Controller)
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the Self-Aware System with its core components"""
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "self_aware")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize AI Parameter Manager
        param_path = os.path.join(self.storage_path, "parameters")
        self.parameter_manager = AIParameterManager(storage_path=param_path)
        
        # Initialize Knowledge Integration System
        knowledge_path = os.path.join(self.storage_path, "knowledge")
        self.knowledge_system = KnowledgeIntegrationSystem(storage_path=knowledge_path)
        
        # Initialize Development Cognitive Loop Orchestrator
        cognitive_path = os.path.join(self.storage_path, "cognitive_loop")
        self.cognitive_orchestrator = CognitiveLoopOrchestrator(storage_path=cognitive_path)
        
        # Initialize Parallel Execution Controller
        self.parallel_controller = ParallelExecutionController(
            max_concurrent_tasks=5,
            resource_limits={"cpu": 80.0, "memory": 4096.0}
        )
        
        # Initialize System Access Layer components
        self.package_manager = PackageManager()
        self.git_manager = GitManager()
        self.test_runner = TestRunner(project_root=os.getcwd())
        
        # Initialize Observability Layer components
        supervision_path = os.path.join(self.storage_path, "supervision")
        resource_path = os.path.join(self.storage_path, "resources")
        metrics_path = os.path.join(self.storage_path, "metrics")
        
        self.supervision_hub = SupervisionHub(storage_path=supervision_path)
        self.resource_monitor = ResourceMonitor()
        self.metrics_collector = MetricsCollector(storage_path=metrics_path)
        
        # Initialize self-modification components
        self.code_generator = CodeGenerator()
        self.safety_validator = SafetyValidator()
        self.integration_manager = IntegrationManager(
            self.git_manager, 
            self.test_runner
        )
        self.agentic_development_controller = AgenticDevelopmentController(
            self.code_generator,
            self.safety_validator,
            self.integration_manager,
            self.knowledge_system,
            self.cognitive_orchestrator
        )
        
        # Register specialized workers
        self._register_workers()
        
        # Initialize system with basic knowledge
        self._initialize_knowledge()
        
        # Don't start monitoring and metrics collection in __init__
        # This will be done explicitly in start_monitoring_and_metrics
    
    def _register_workers(self):
        """Register specialized workers with the cognitive loop orchestrator"""
        # Requirements Worker
        self.cognitive_orchestrator.register_worker(
            WorkerType.REQUIREMENTS,
            RequirementsWorker()
        )
        
        # Planning Worker
        self.cognitive_orchestrator.register_worker(
            WorkerType.PLANNING,
            PlanningWorker()
        )
        
        # Implementation Worker
        self.cognitive_orchestrator.register_worker(
            WorkerType.IMPLEMENTATION,
            ImplementationWorker()
        )
        
        # Evaluation Worker
        self.cognitive_orchestrator.register_worker(
            WorkerType.EVALUATION,
            EvaluationWorker()
        )
    
    def _initialize_knowledge(self):
        """Initialize the system with basic knowledge"""
        # Add semantic memory about the system itself
        if not self.knowledge_system.search_semantic_memory("Self-Aware Cerebrum"):
            self.knowledge_system.add_semantic_memory(
                concept="Self-Aware Cerebrum",
                definition="An AI framework that can modify and improve itself through a cognitive loop process.",
                related_concepts=["AI", "Self-Improvement", "Cognitive Loop"],
                tags=["system", "core", "architecture"]
            )
        
        # Add procedural memory about the cognitive loop process
        if not self.knowledge_system.search_procedural_memory("Run Cognitive Cycle"):
            self.knowledge_system.add_procedural_memory(
                task_name="Run Cognitive Cycle",
                description="Execute a complete cognitive cycle through all phases.",
                steps=[
                    "Start with the Understand phase to analyze requirements and context",
                    "Move to the Plan phase to create an implementation plan",
                    "Execute the plan in the Execute phase",
                    "Evaluate results and learn in the Reflect phase"
                ],
                expected_outcome="Completed development cycle with system improvements",
                tags=["cognitive_loop", "process", "core"]
            )
    
    async def start_cognitive_cycle(self):
        """Start a cognitive cycle"""
        # Create initial understanding task
        task_id = self.cognitive_orchestrator.create_task(
            title="Analyze System State",
            description="Analyze the current state of the system and identify improvement opportunities.",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.HIGH
        )
        
        # Run the cognitive cycle
        await self.cognitive_orchestrator.run_cognitive_cycle()
        
        # Record the experience in episodic memory
        self.knowledge_system.add_episodic_memory(
            title="Cognitive Cycle Execution",
            description=f"Executed a cognitive cycle starting with task {task_id}",
            timestamp=datetime.now(),
            actors=["Self-Aware Cerebrum"],
            context={
                "starting_task": task_id,
                "cycle_time": datetime.now().isoformat()
            },
            tags=["cognitive_cycle", "execution", "system_activity"]
        )
        
        return task_id
    
    async def start_continuous_operation(self, interval_seconds: float = 60.0):
        """Start continuous operation of the cognitive loop"""
        # Record the start in episodic memory
        self.knowledge_system.add_episodic_memory(
            title="Continuous Operation Started",
            description=f"Started continuous operation with interval {interval_seconds} seconds",
            timestamp=datetime.now(),
            actors=["Self-Aware Cerebrum"],
            tags=["continuous_operation", "system_activity"]
        )
        
        # Start continuous operation
        await self.cognitive_orchestrator.run_continuous(interval_seconds=interval_seconds)
    
    def get_optimal_parameters(self, task_type: str, model_name: str):
        """Get optimal parameters for a specific task type and model"""
        return self.parameter_manager.get_optimal_parameters(task_type, model_name)
    
    def record_task_performance(self, task_id: str, parameter_set_id: str, 
                               execution_time: float, token_count: int, 
                               success: bool, quality_score: Optional[float] = None):
        """Record performance metrics for a task execution"""
        self.parameter_manager.record_performance(
            task_id=task_id,
            parameter_set_id=parameter_set_id,
            execution_time=execution_time,
            token_count=token_count,
            success=success,
            quality_score=quality_score
        )
    
    def get_knowledge_context(self, query: str, max_items: int = 5):
        """Get relevant knowledge context for a query"""
        return self.knowledge_system.get_knowledge_context(query, max_items)
    
    def add_semantic_knowledge(self, concept: str, definition: str, **kwargs):
        """Add semantic knowledge to the system"""
        return self.knowledge_system.add_semantic_memory(concept, definition, **kwargs)
    
    def add_procedural_knowledge(self, task_name: str, description: str, steps: List[str], expected_outcome: str, **kwargs):
        """Add procedural knowledge to the system"""
        return self.knowledge_system.add_procedural_memory(task_name, description, steps, expected_outcome, **kwargs)
    
    def add_episodic_knowledge(self, title: str, description: str, **kwargs):
        """Add episodic knowledge to the system"""
        return self.knowledge_system.add_episodic_memory(title, description, **kwargs)
    
    def create_cognitive_task(self, title: str, description: str, phase: CognitivePhase, **kwargs):
        """Create a new cognitive task"""
        return self.cognitive_orchestrator.create_task(title, description, phase, **kwargs)
    
    def get_cognitive_task(self, task_id: str):
        """Get a cognitive task by ID"""
        return self.cognitive_orchestrator.get_task(task_id)
    
    def get_current_phase(self):
        """Get the current phase of the cognitive loop"""
        return self.cognitive_orchestrator.get_current_phase()
    
    def get_tasks_by_phase(self, phase: CognitivePhase, **kwargs):
        """Get tasks for a specific phase"""
        return self.cognitive_orchestrator.get_tasks_by_phase(phase, **kwargs)
    
    def update_development_context(self, key: str, value: Any):
        """Update a value in the development context"""
        self.cognitive_orchestrator.update_development_context(key, value)
    
    def get_development_context(self, key: Optional[str] = None):
        """Get a value from the development context"""
        return self.cognitive_orchestrator.get_development_context(key)
    
    # New methods for Parallel Execution Controller
    
    async def execute_tasks_in_parallel(self, tasks: List[Dict[str, Any]], strategy: str = "resource_aware") -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of task dictionaries with coroutine, resource_requirements, and dependencies
            strategy: Execution strategy ("resource_aware", "priority_based", "fifo")
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        # Convert task dictionaries to Task objects
        task_objects = []
        for task_dict in tasks:
            task = Task(
                task_id=task_dict.get("id", str(uuid.uuid4())),
                coroutine=task_dict["coroutine"],
                resource_requirements=task_dict.get("resource_requirements"),
                dependencies=task_dict.get("dependencies")
            )
            task_objects.append(task)
        
        # Execute tasks in parallel
        results = await self.parallel_controller.execute_tasks(task_objects, strategy)
        
        # Record metrics for each task
        for task_id, result in results.items():
            if result["status"] == "completed" and "execution_time" in result:
                await self.metrics_collector.record_task_metrics(
                    task_id=task_id,
                    execution_time=result.get("execution_time", 0),
                    memory_usage=result.get("resource_usage", {}).get("memory", 0),
                    success=True,
                    additional_metrics=result.get("resource_usage")
                )
            elif result["status"] == "failed":
                await self.metrics_collector.record_task_metrics(
                    task_id=task_id,
                    execution_time=result.get("execution_time", 0),
                    memory_usage=result.get("resource_usage", {}).get("memory", 0),
                    success=False,
                    additional_metrics=result.get("resource_usage")
                )
        
        return results
    
    async def add_parallel_task(self, coroutine: Any, resource_requirements: Optional[Dict[str, float]] = None,
                              dependencies: List[str] = None) -> str:
        """
        Add a task to the parallel execution queue.
        
        Args:
            coroutine: The coroutine to execute
            resource_requirements: Dictionary of resource requirements
            dependencies: List of task IDs that must complete before this task can start
            
        Returns:
            Task ID
        """
        task_id = await self.parallel_controller.add_task(
            coroutine=coroutine,
            resource_requirements=resource_requirements,
            dependencies=dependencies
        )
        
        # Record the task creation
        await self.metrics_collector.record_metric(
            metric_name="task_created",
            value=1.0,
            tags={"task_id": task_id}
        )
        
        return task_id
    
    async def wait_for_parallel_task(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for a parallel task to complete.
        
        Args:
            task_id: ID of the task to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Task result information
        """
        return await self.parallel_controller.wait_for_task(task_id, timeout)
    
    # New methods for Package Manager
    
    async def install_package(self, package_name: str, version: Optional[str] = None, 
                             upgrade: bool = False) -> Dict[str, Any]:
        """
        Install a Python package.
        
        Args:
            package_name: Name of the package to install
            version: Optional version specification
            upgrade: Whether to upgrade the package if already installed
            
        Returns:
            Installation result information
        """
        result = await self.package_manager.install_package(
            package_name=package_name,
            version=version,
            upgrade=upgrade,
            requires_approval=True
        )
        
        # If approval is required, create an approval request
        if not result["success"] and result.get("requires_approval"):
            request_id = await self.supervision_hub.create_approval_request(
                operation_type="package_install",
                details={
                    "package": result.get("package"),
                    "command": result.get("command")
                },
                required_role="admin"
            )
            
            # Update result with request ID
            result["approval_request_id"] = request_id
        
        return result
    
    async def uninstall_package(self, package_name: str) -> Dict[str, Any]:
        """
        Uninstall a Python package.
        
        Args:
            package_name: Name of the package to uninstall
            
        Returns:
            Uninstallation result information
        """
        result = await self.package_manager.uninstall_package(
            package_name=package_name,
            requires_approval=True
        )
        
        # If approval is required, create an approval request
        if not result["success"] and result.get("requires_approval"):
            request_id = await self.supervision_hub.create_approval_request(
                operation_type="package_uninstall",
                details={
                    "package": package_name,
                    "command": result.get("command")
                },
                required_role="admin"
            )
            
            # Update result with request ID
            result["approval_request_id"] = request_id
        
        return result
    
    async def list_installed_packages(self) -> List[Dict[str, str]]:
        """
        List all installed packages with versions.
        
        Returns:
            List of dictionaries with package information
        """
        return await self.package_manager.list_installed_packages()
    
    # New methods for Git Manager
    
    async def clone_repository(self, url: str, path: Optional[str] = None, 
                              branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Clone a Git repository.
        
        Args:
            url: Repository URL
            path: Local path to clone to
            branch: Branch to checkout
            
        Returns:
            Clone result information
        """
        result = await self.git_manager.clone_repository(
            url=url,
            path=path,
            branch=branch,
            requires_approval=True
        )
        
        # If approval is required, create an approval request
        if not result["success"] and result.get("requires_approval"):
            request_id = await self.supervision_hub.create_approval_request(
                operation_type="git_clone",
                details={
                    "url": url,
                    "path": path,
                    "branch": branch,
                    "command": result.get("command")
                },
                required_role="developer"
            )
            
            # Update result with request ID
            result["approval_request_id"] = request_id
        
        return result
    
    async def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            files: List of files to commit, or None for all changes
            
        Returns:
            Commit result information
        """
        result = await self.git_manager.commit_changes(
            message=message,
            files=files,
            requires_approval=True
        )
        
        # If approval is required, create an approval request
        if not result["success"] and result.get("requires_approval"):
            request_id = await self.supervision_hub.create_approval_request(
                operation_type="git_commit",
                details={
                    "message": message,
                    "files": files,
                    "stage_command": result.get("stage_command"),
                    "commit_command": result.get("commit_command")
                },
                required_role="developer"
            )
            
            # Update result with request ID
            result["approval_request_id"] = request_id
        
        return result
    
    async def get_repository_status(self) -> Dict[str, Any]:
        """
        Get the current status of the repository.
        
        Returns:
            Repository status information
        """
        return await self.git_manager.get_repository_status()
    
    # New methods for Test Runner
    
    async def discover_tests(self, path: Optional[str] = None, pattern: str = "test_*.py") -> List[Dict[str, Any]]:
        """
        Discover tests in the specified path.
        
        Args:
            path: Path to search for tests
            pattern: Pattern to match test files
            
        Returns:
            List of dictionaries with test information
        """
        return await self.test_runner.discover_tests(path, pattern)
    
    async def run_tests(self, test_path: Optional[str] = None, pattern: Optional[str] = None, 
                       verbosity: int = 2) -> Dict[str, Any]:
        """
        Run tests and return results.
        
        Args:
            test_path: Path to the tests to run
            pattern: Pattern to match test files
            verbosity: Verbosity level for test output
            
        Returns:
            Dictionary with test results
        """
        results = await self.test_runner.run_tests(test_path, pattern, verbosity)
        
        # Record metrics for test execution
        await self.metrics_collector.record_metric(
            metric_name="tests_run",
            value=results.get("total", 0),
            tags={"success": str(results.get("success", False))}
        )
        
        await self.metrics_collector.record_metric(
            metric_name="test_failures",
            value=results.get("failures", 0)
        )
        
        await self.metrics_collector.record_metric(
            metric_name="test_errors",
            value=results.get("errors", 0)
        )
        
        return results
    
    async def get_test_coverage(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get test coverage information.
        
        Args:
            test_path: Path to the tests to run for coverage
            
        Returns:
            Dictionary with coverage information
        """
        coverage_info = await self.test_runner.get_test_coverage(test_path)
        
        # Record metrics for test coverage
        await self.metrics_collector.record_metric(
            metric_name="test_coverage",
            value=coverage_info.get("total_coverage", 0)
        )
        
        return coverage_info
    
    # New methods for Supervision Hub
    
    async def register_supervisor(self, user_id: str, role: str, permissions: List[str]) -> Dict[str, Any]:
        """
        Register a new supervisor with role and permissions.
        
        Args:
            user_id: Unique identifier for the supervisor
            role: Role of the supervisor (e.g., "admin", "developer", "reviewer")
            permissions: List of permission strings
            
        Returns:
            Dictionary with registration result
        """
        return await self.supervision_hub.register_supervisor(user_id, role, permissions)
    
    async def approve_request(self, request_id: str, supervisor_id: str, 
                             comments: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request to approve
            supervisor_id: ID of the supervisor approving the request
            comments: Optional comments about the approval
            
        Returns:
            Dictionary with approval result
        """
        result = await self.supervision_hub.approve_request(request_id, supervisor_id, comments)
        
        # If approval was successful, execute the approved operation
        if result["success"]:
            request = result.get("details", {})
            operation_type = result.get("operation_type")
            
            if operation_type == "package_install":
                # Execute package installation
                package = request.get("package")
                if package:
                    if "==" in package:
                        package_name, version = package.split("==")
                        await self.package_manager.install_package(
                            package_name=package_name,
                            version=version,
                            requires_approval=False
                        )
                    else:
                        await self.package_manager.install_package(
                            package_name=package,
                            requires_approval=False
                        )
            
            elif operation_type == "git_clone":
                # Execute git clone
                await self.git_manager.clone_repository(
                    url=request.get("url"),
                    path=request.get("path"),
                    branch=request.get("branch"),
                    requires_approval=False
                )
            
            elif operation_type == "git_commit":
                # Execute git commit
                await self.git_manager.commit_changes(
                    message=request.get("message"),
                    files=request.get("files"),
                    requires_approval=False
                )
        
        return result
    
    async def get_pending_requests(self, supervisor_id: Optional[str] = None, 
                                  role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get pending approval requests, optionally filtered by supervisor or role.
        
        Args:
            supervisor_id: Optional supervisor ID to filter by
            role: Optional role to filter by
            
        Returns:
            List of pending requests
        """
        return await self.supervision_hub.get_pending_requests(supervisor_id, role)
    
    # New methods for Resource Monitor
    
    async def get_current_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage statistics.
        
        Returns:
            Dictionary with resource usage values
        """
        return await self.resource_monitor.get_current_usage()
    
    async def set_resource_budget(self, resource_type: str, limit: float, 
                                period: str = "daily") -> Dict[str, Any]:
        """
        Set a budget for a specific resource type.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk, api_calls, tokens)
            limit: Budget limit value
            period: Budget period (hourly, daily, weekly, monthly)
            
        Returns:
            Dictionary with budget information
        """
        return await self.resource_monitor.set_budget(resource_type, limit, period)
    
    async def check_resource_budget(self, resource_type: str) -> Dict[str, Any]:
        """
        Check current usage against budget for a resource type.
        
        Args:
            resource_type: Type of resource to check
            
        Returns:
            Dictionary with budget check results
        """
        return await self.resource_monitor.check_budget(resource_type)
    
    async def record_resource_usage(self, resource_type: str, amount: float, 
                                  operation_id: Optional[str] = None) -> None:
        """
        Record usage of a resource.
        
        Args:
            resource_type: Type of resource used
            amount: Amount of resource used
            operation_id: Optional operation identifier
        """
        await self.resource_monitor.record_usage(resource_type, amount, operation_id)
    
    # New methods for Metrics Collector
    
    async def record_metric(self, metric_name: str, value: float, 
                           tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a single metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        await self.metrics_collector.record_metric(metric_name, value, tags)
    
    async def get_metrics(self, metric_name: str, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None, 
                         aggregation: str = "avg") -> List[Dict[str, Any]]:
        """
        Get metrics for a specific metric name with optional time range and aggregation.
        
        Args:
            metric_name: Name of the metric
            start_time: Optional start time
            end_time: Optional end time
            aggregation: Aggregation method (avg, sum, min, max, count)
            
        Returns:
            List of metric records
        """
        return await self.metrics_collector.get_metrics(metric_name, start_time, end_time, aggregation)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            Dictionary with system health metrics
        """
        return await self.metrics_collector.get_system_health()
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        # Stop monitoring and metrics collection
        await self.resource_monitor.stop_monitoring()
        await self.metrics_collector.stop_collection()
        
        # Shutdown parallel controller
        await self.parallel_controller.shutdown()
        
        # Log shutdown
        logger.info("Self-Aware System shutdown complete")
    
    async def start_monitoring_and_metrics(self):
        """Start resource monitoring and metrics collection tasks"""
        # Start monitoring and metrics collection
        monitor_task = asyncio.create_task(self.resource_monitor.start_monitoring())
        metrics_task = asyncio.create_task(self.metrics_collector.start_collection())
        return monitor_task, metrics_task
    
    # Self-Modification Engine methods
    
    async def generate_code(self, specification: Dict[str, Any], 
                           context: Optional[Dict[str, Any]] = None,
                           existing_code: Optional[str] = None) -> Dict[str, Any]:
        """Generate code based on specification and context.
        
        Args:
            specification: Detailed specification for the code to be generated.
            context: Additional context information to guide generation.
            existing_code: Existing code to be modified or extended.
            
        Returns:
            Dictionary containing generated code and metadata.
        """
        logger.info(f"Generating code for specification: {specification.get('name', 'Unnamed')}")
        return await self.code_generator.generate_code(specification, context, existing_code)
    
    async def refactor_code(self, code: str, refactoring_type: str,
                           requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Refactor existing code according to requirements.
        
        Args:
            code: The code to be refactored.
            refactoring_type: Type of refactoring (e.g., "extract_method", "rename", "optimize").
            requirements: Specific requirements for the refactoring.
            
        Returns:
            Dictionary containing refactored code and metadata.
        """
        logger.info(f"Refactoring code with type: {refactoring_type}")
        return await self.code_generator.refactor_code(code, refactoring_type, requirements)
    
    async def optimize_code(self, code: str, optimization_goals: List[str]) -> Dict[str, Any]:
        """Optimize code for specified goals (performance, readability, etc.).
        
        Args:
            code: The code to be optimized.
            optimization_goals: List of optimization goals (e.g., ["performance", "memory_usage"]).
            
        Returns:
            Dictionary containing optimized code and metadata.
        """
        logger.info(f"Optimizing code for goals: {optimization_goals}")
        return await self.code_generator.optimize_code(code, optimization_goals)
    
    async def fix_bugs(self, code: str, bug_description: str,
                      test_cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Fix bugs in code based on description and test cases.
        
        Args:
            code: The code containing bugs.
            bug_description: Description of the bug(s) to fix.
            test_cases: Optional test cases that demonstrate the bug.
            
        Returns:
            Dictionary containing fixed code and metadata.
        """
        logger.info(f"Fixing bugs with description: {bug_description}")
        return await self.code_generator.fix_bugs(code, bug_description, test_cases)
    
    async def validate_code(self, code: str, file_path: str,
                           validation_level: str = "high") -> Dict[str, Any]:
        """Validate code against safety rules and quality standards.
        
        Args:
            code: The code to validate.
            file_path: The path where the code would be saved.
            validation_level: Level of validation (low, medium, high).
            
        Returns:
            Dictionary containing validation results.
        """
        logger.info(f"Validating code for file: {file_path}")
        return await self.safety_validator.validate_code(code, file_path, validation_level)
    
    async def integrate_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate changes into the system.
        
        Args:
            changes: Dictionary containing changes to be integrated.
                    Format: {"file_path": {"content": "...", "description": "..."}, ...}
            
        Returns:
            Dictionary containing integration plan details.
        """
        logger.info(f"Creating integration plan for {len(changes)} changes")
        return await self.integration_manager.create_integration_plan(changes)
    
    async def start_development_cycle(self, requirements: Dict[str, Any]) -> str:
        """Start a development cycle based on requirements.
        
        Args:
            requirements: Dictionary containing development requirements.
            
        Returns:
            ID of the created development cycle.
        """
        logger.info("Starting development cycle")
        return await self.agentic_development_controller.initialize_development_cycle(requirements)
    
    async def get_development_cycle_status(self, cycle_id: str) -> Dict[str, Any]:
        """Get current status of a development cycle.
        
        Args:
            cycle_id: ID of the development cycle.
            
        Returns:
            Dictionary containing development cycle status.
        """
        logger.info(f"Getting status for development cycle: {cycle_id}")
        return await self.agentic_development_controller.get_cycle_status(cycle_id) 