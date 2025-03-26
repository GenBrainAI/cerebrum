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

# Import planning components
from src.server.planning.goal_decomposition import (
    GoalDecompositionEngine,
    GoalType,
    DecompositionStrategy,
    ResourceEstimate,
    SubGoal,
    DecomposedGoal
)

# Import planning engine components
from src.server.planning.planning_engine import (
    PlanningEngine,
    PlanType,
    IntegratedPlan,
    PlanningMetrics,
    PlanVersion
)
from src.server.planning.planning_config import (
    PlanningConfigManager,
    PlanningConfig,
    OptimizationGoal
)
from src.server.planning.planning_factory import PlanningEngineFactory
from src.server.planning.planning_workflow import PlanningWorkflow
from src.server.planning.planning_metrics import (
    PlanningMetricsCollector,
    MetricType,
    MetricSnapshot,
    MetricTrend
)
from src.server.planning.planning_visualization import (
    PlanningVisualization,
    VisualizationType,
    OutputFormat
)

# Import introspection components
from src.server.introspection.component_analysis.analyzer import ComponentAnalyzer
from src.server.introspection.component_analysis.code_parser import CodeParser
from src.server.introspection.component_analysis.complexity_analyzer import ComplexityAnalyzer
from src.server.introspection.component_analysis.dependency_mapper import DependencyMapper

from src.server.introspection.runtime_monitoring.behavior_monitor import BehaviorMonitor
from src.server.introspection.runtime_monitoring.telemetry_collector import TelemetryCollector
from src.server.introspection.runtime_monitoring.anomaly_detector import AnomalyDetector
from src.server.introspection.runtime_monitoring.performance_analyzer import PerformanceAnalyzer

from src.server.integration_optimization.interaction_analyzer import InteractionAnalyzer
from src.server.integration_optimization.resource_optimizer import ResourceOptimizer
from src.server.integration_optimization.workflow_optimizer import WorkflowOptimizer

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
    - Planning Layer (Goal Decomposition Engine)
    - Introspection Layer (Component Analysis, Runtime Monitoring)
    - Integration Optimization Layer (Interaction Analysis, Resource Optimization, Workflow Optimization)
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Self-Aware System.
        
        Args:
            storage_path: Path to store persistent data
        """
        self.storage_path = storage_path or "persistent_state/self_aware"
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize AI Parameter Manager
        self.parameter_manager = AIParameterManager(
            storage_path=os.path.join(self.storage_path, "parameters")
        )
        
        # Initialize Knowledge Integration System
        self.knowledge_system = KnowledgeIntegrationSystem(
            storage_path=os.path.join(self.storage_path, "knowledge")
        )
        
        # Initialize Cognitive Loop Orchestrator
        self.cognitive_orchestrator = CognitiveLoopOrchestrator(
            storage_path=os.path.join(self.storage_path, "cognitive_loop")
        )
        
        # Initialize Parallel Execution Controller
        self.parallel_controller = ParallelExecutionController(
            max_concurrent_tasks=10
        )
        
        # Initialize System Access Layer
        self.package_manager = PackageManager()
        self.git_manager = GitManager()
        self.test_runner = TestRunner()
        
        # Initialize Observability Layer
        self.supervision_hub = SupervisionHub(
            storage_path=os.path.join(self.storage_path, "supervision")
        )
        self.resource_monitor = ResourceMonitor()
        self.metrics_collector = MetricsCollector(
            storage_path=os.path.join(self.storage_path, "metrics")
        )
        
        # Initialize Self-Modification Engine
        self.code_generator = CodeGenerator()
        self.safety_validator = SafetyValidator()
        self.integration_manager = IntegrationManager(
            git_manager=self.git_manager,
            test_runner=self.test_runner
        )
        self.agentic_controller = AgenticDevelopmentController(
            code_generator=self.code_generator,
            safety_validator=self.safety_validator,
            integration_manager=self.integration_manager,
            knowledge_system=self.knowledge_system,
            cognitive_orchestrator=self.cognitive_orchestrator
        )
        
        # Initialize Planning Layer
        self.goal_decomposition_engine = GoalDecompositionEngine(
            knowledge_system=self.knowledge_system
        )
        
        # Initialize Phase 4 Introspection Layer
        self.component_analyzer = ComponentAnalyzer(
            knowledge_system=self.knowledge_system
        )
        self.telemetry_collector = TelemetryCollector()
        self.behavior_monitor = BehaviorMonitor(
            telemetry_system=self.telemetry_collector
        )
        
        # Initialize Phase 4 Integration Optimization Layer
        self.interaction_analyzer = InteractionAnalyzer(
            knowledge_system=self.knowledge_system,
            component_analyzer=self.component_analyzer
        )
        self.resource_optimizer = ResourceOptimizer(
            telemetry_system=self.telemetry_collector
        )
        self.workflow_optimizer = WorkflowOptimizer(
            knowledge_system=self.knowledge_system,
            goal_decomposition_engine=self.goal_decomposition_engine
        )
        
        # Initialize planning engine components
        self.planning_config_manager = PlanningConfigManager(
            config_path=os.path.join(self.storage_path, "planning/config")
        )
        
        # Will be initialized in initialize() method
        self.planning_engine = None
        self.planning_workflow = None
        self.planning_metrics_collector = None
        self.planning_visualization = None
        
        logger.info(f"Self-Aware System initialized with storage path: {self.storage_path}")

    async def initialize(self):
        """Initialize all components of the Self-Aware System."""
        logger.info("Initializing Self-Aware System components")
        
        # Initialize AI Parameter Manager
        await self.parameter_manager.initialize()
        
        # Initialize Knowledge Integration System
        await self.knowledge_system.initialize()
        
        # Initialize Cognitive Loop Orchestrator
        await self.cognitive_orchestrator.initialize()
        
        # Register specialized workers
        await self.register_specialized_workers()
        
        # Initialize Phase 4 Introspection Layer
        # These are asynchronous initializations to load any necessary data or models
        logger.info("Initializing Introspection Layer components")
        # No explicit initialization needed for ComponentAnalyzer as it relies on the knowledge system
        
        # Initialize telemetry collector and behavior monitor
        if hasattr(self.telemetry_collector, 'initialize'):
            await self.telemetry_collector.initialize()
        
        if hasattr(self.behavior_monitor, 'initialize'):
            await self.behavior_monitor.initialize()
        
        # Initialize Phase 4 Integration Optimization Layer
        logger.info("Initializing Integration Optimization Layer components")
        if hasattr(self.interaction_analyzer, 'initialize'):
            await self.interaction_analyzer.initialize()
            
        if hasattr(self.resource_optimizer, 'initialize'):
            await self.resource_optimizer.initialize()
            
        if hasattr(self.workflow_optimizer, 'initialize'):
            await self.workflow_optimizer.initialize()
        
        # Initialize planning engine components
        self.planning_engine = await PlanningEngineFactory.create_planning_engine(
            config_path=os.path.join(self.storage_path, "planning/config/default_config.json"),
            knowledge_system=self.knowledge_system,
            storage_path=self.storage_path
        )
        
        self.planning_workflow = PlanningWorkflow(self.planning_engine)
        
        self.planning_metrics_collector = PlanningMetricsCollector(
            storage_path=os.path.join(self.storage_path, "planning/metrics")
        )
        
        self.planning_visualization = PlanningVisualization(
            storage_path=os.path.join(self.storage_path, "planning/visualizations")
        )
        
        logger.info("Self-Aware System initialization completed")

    async def register_specialized_workers(self):
        """Register specialized workers with the cognitive orchestrator."""
        logger.info("Registering specialized workers")
        
        # Create and register Requirements Worker
        requirements_worker = RequirementsWorker(
            knowledge_system=self.knowledge_system,
            parameter_manager=self.parameter_manager
        )
        await self.cognitive_orchestrator.register_worker(
            worker_type=WorkerType.REQUIREMENTS,
            worker=requirements_worker
        )
        
        # Create and register Planning Worker
        planning_worker = PlanningWorker(
            knowledge_system=self.knowledge_system,
            parameter_manager=self.parameter_manager,
            goal_decomposition_engine=self.goal_decomposition_engine
        )
        await self.cognitive_orchestrator.register_worker(
            worker_type=WorkerType.PLANNING,
            worker=planning_worker
        )
        
        # Create and register Implementation Worker
        implementation_worker = ImplementationWorker(
            knowledge_system=self.knowledge_system,
            parameter_manager=self.parameter_manager,
            code_generator=self.code_generator,
            safety_validator=self.safety_validator
        )
        await self.cognitive_orchestrator.register_worker(
            worker_type=WorkerType.IMPLEMENTATION,
            worker=implementation_worker
        )
        
        # Create and register Evaluation Worker
        evaluation_worker = EvaluationWorker(
            knowledge_system=self.knowledge_system,
            parameter_manager=self.parameter_manager,
            test_runner=self.test_runner
        )
        await self.cognitive_orchestrator.register_worker(
            worker_type=WorkerType.EVALUATION,
            worker=evaluation_worker
        )
        
        logger.info("Specialized workers registered successfully")

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
    
    async def create_cognitive_task(self, title: str, description: str, phase: CognitivePhase, **kwargs):
        """Create a new cognitive task"""
        return await self.cognitive_orchestrator.create_task(title, description, phase, **kwargs)

    async def get_cognitive_task(self, task_id: str):
        """Get a cognitive task by ID"""
        return await self.cognitive_orchestrator.get_task(task_id)

    async def get_current_phase(self):
        """Get the current phase of the cognitive loop"""
        return await self.cognitive_orchestrator.get_current_phase()

    async def get_tasks_by_phase(self, phase: CognitivePhase, **kwargs):
        """Get tasks for a specific phase"""
        return await self.cognitive_orchestrator.get_tasks_by_phase(phase, **kwargs)

    async def update_development_context(self, key: str, value: Any):
        """Update a value in the development context"""
        await self.cognitive_orchestrator.update_development_context(key, value)

    async def get_development_context(self, key: Optional[str] = None):
        """Get a value from the development context"""
        return await self.cognitive_orchestrator.get_development_context(key)
    
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
        
        # Shutdown Phase 4 Introspection Layer
        logger.info("Shutting down Introspection Layer components")
        if hasattr(self.telemetry_collector, 'shutdown'):
            await self.telemetry_collector.shutdown()
        
        if hasattr(self.behavior_monitor, 'shutdown'):
            await self.behavior_monitor.shutdown()
        
        # Shutdown Phase 4 Integration Optimization Layer
        logger.info("Shutting down Integration Optimization Layer components")
        if hasattr(self.interaction_analyzer, 'shutdown'):
            await self.interaction_analyzer.shutdown()
            
        if hasattr(self.resource_optimizer, 'shutdown'):
            await self.resource_optimizer.shutdown()
            
        if hasattr(self.workflow_optimizer, 'shutdown'):
            await self.workflow_optimizer.shutdown()
        
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
        return await self.agentic_controller.initialize_development_cycle(requirements)
    
    async def get_development_cycle_status(self, cycle_id: str) -> Dict[str, Any]:
        """Get current status of a development cycle.
        
        Args:
            cycle_id: ID of the development cycle.
            
        Returns:
            Dictionary containing development cycle status.
        """
        logger.info(f"Getting status for development cycle: {cycle_id}")
        return await self.agentic_controller.get_cycle_status(cycle_id)
    
    # New methods for Goal Decomposition Engine
    
    async def decompose_goal(
        self, 
        goal: Dict[str, Any],
        strategy: str = "TOP_DOWN",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Decompose a high-level goal into manageable subgoals.
        
        Args:
            goal: Dictionary containing goal information (name, description, type, etc.)
            strategy: Decomposition strategy to use (TOP_DOWN, BOTTOM_UP, ITERATIVE, DOMAIN_SPECIFIC)
            context: Additional context for decomposition
            
        Returns:
            Dictionary representation of the decomposed goal
        """
        try:
            # Convert strategy string to enum
            decomposition_strategy = DecompositionStrategy.from_str(strategy)
            
            # Decompose the goal
            decomposed_goal = await self.goal_decomposition_engine.decompose_goal(
                goal=goal,
                strategy=decomposition_strategy,
                context=context
            )
            
            # Record in episodic memory
            self.knowledge_system.add_episodic_memory(
                title=f"Goal Decomposition: {goal.get('name', 'Unnamed Goal')}",
                description=f"Decomposed goal using {strategy} strategy",
                timestamp=datetime.now(),
                actors=["Self-Aware Cerebrum"],
                context={
                    "goal_id": decomposed_goal.id,
                    "strategy": strategy,
                    "subgoal_count": len(decomposed_goal.subgoals)
                },
                tags=["goal_decomposition", "planning", "system_activity"]
            )
            
            return decomposed_goal.to_dict()
            
        except Exception as e:
            logger.error(f"Error decomposing goal: {str(e)}")
            raise
    
    async def get_decomposed_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a decomposed goal by ID.
        
        Args:
            goal_id: ID of the decomposed goal
            
        Returns:
            Dictionary representation of the decomposed goal, or None if not found
        """
        decomposed_goal = await self.goal_decomposition_engine.get_decomposed_goal(goal_id)
        if decomposed_goal:
            return decomposed_goal.to_dict()
        return None
    
    async def prioritize_subgoals(self, goal_id: str) -> List[str]:
        """
        Prioritize subgoals within a decomposed goal.
        
        Args:
            goal_id: ID of the decomposed goal
            
        Returns:
            List of subgoal IDs in priority order
        """
        return await self.goal_decomposition_engine.prioritize_subgoals(goal_id)
    
    async def estimate_goal_resources(self, goal_id: str) -> Dict[str, Any]:
        """
        Estimate resources for a decomposed goal.
        
        Args:
            goal_id: ID of the decomposed goal
            
        Returns:
            Dictionary containing resource estimates
        """
        resource_estimate = await self.goal_decomposition_engine.estimate_resources(goal_id)
        return {
            "time_hours": resource_estimate.time_hours,
            "complexity": resource_estimate.complexity,
            "knowledge_requirements": resource_estimate.knowledge_requirements,
            "dependencies": resource_estimate.dependencies,
            "risk_level": resource_estimate.risk_level
        }
    
    async def validate_goal_decomposition(self, goal_id: str) -> Dict[str, Any]:
        """
        Validate a goal decomposition for completeness and consistency.
        
        Args:
            goal_id: ID of the decomposed goal
            
        Returns:
            Dictionary containing validation results
        """
        return await self.goal_decomposition_engine.validate_decomposition(goal_id)

    # New methods for Introspection Layer

    async def analyze_component(self, component_name: str) -> Dict[str, Any]:
        """Analyze a specific component"""
        return await self.component_analyzer.analyze_component(component_name)

    async def get_component_analysis(self, component_name: str) -> Dict[str, Any]:
        """Get analysis results for a specific component"""
        return await self.component_analyzer.get_analysis(component_name)

    async def get_telemetry_data(self, component_name: str) -> Dict[str, Any]:
        """Get telemetry data for a specific component"""
        return await self.telemetry_collector.get_telemetry(component_name)

    async def get_behavior_data(self, component_name: str) -> Dict[str, Any]:
        """Get behavior data for a specific component"""
        return await self.behavior_monitor.get_behavior_data(component_name)

    # New methods for Integration Optimization Layer

    async def analyze_interaction(self, component_name: str, other_component_name: str) -> Dict[str, Any]:
        """Analyze interaction between two components"""
        return await self.interaction_analyzer.analyze_interaction(component_name, other_component_name)

    async def optimize_resource(self, component_name: str, resource_type: str) -> Dict[str, Any]:
        """Optimize resource usage for a specific component"""
        return await self.resource_optimizer.optimize_resource(component_name, resource_type)

    async def optimize_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """Optimize a specific workflow"""
        return await self.workflow_optimizer.optimize_workflow(workflow_name)

    async def enable_introspective_cognitive_loop(self):
        """
        Enable advanced introspection capabilities in the cognitive loop.
        This allows the system to analyze its own components and behavior during the cognitive cycle.
        """
        logger.info("Enabling introspective cognitive loop")
        
        # Create a task to analyze system components in the understanding phase
        component_analysis_task_id = self.cognitive_orchestrator.create_task(
            title="System Component Analysis",
            description="Analyze the system's components to understand their structure and behavior.",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.MEDIUM,
            context={
                "introspection_type": "component_analysis",
                "target_components": ["self_aware_integration", "cognitive_loop", "knowledge_integration"]
            }
        )
        
        # Create a task to monitor runtime behavior in the understanding phase
        behavior_monitoring_task_id = self.cognitive_orchestrator.create_task(
            title="Runtime Behavior Monitoring",
            description="Monitor the runtime behavior of system components to identify patterns and anomalies.",
            phase=CognitivePhase.UNDERSTAND,
            worker_type=WorkerType.REQUIREMENTS,
            priority=TaskPriority.MEDIUM,
            context={
                "introspection_type": "behavior_monitoring",
                "monitoring_duration": 3600  # 1 hour
            }
        )
        
        # Create a task to analyze component interactions in the planning phase
        interaction_analysis_task_id = self.cognitive_orchestrator.create_task(
            title="Component Interaction Analysis",
            description="Analyze interactions between system components to identify optimization opportunities.",
            phase=CognitivePhase.PLAN,
            worker_type=WorkerType.PLANNING,
            priority=TaskPriority.MEDIUM,
            context={
                "optimization_type": "interaction_analysis",
                "target_components": ["self_aware_integration", "cognitive_loop", "knowledge_integration"]
            }
        )
        
        # Create a task to optimize workflows in the execution phase
        workflow_optimization_task_id = self.cognitive_orchestrator.create_task(
            title="Workflow Optimization",
            description="Optimize system workflows based on analysis results.",
            phase=CognitivePhase.EXECUTE,
            worker_type=WorkerType.IMPLEMENTATION,
            priority=TaskPriority.MEDIUM,
            context={
                "optimization_type": "workflow_optimization",
                "target_workflows": ["cognitive_cycle", "knowledge_retrieval"]
            }
        )
        
        # Create a task to evaluate optimizations in the reflection phase
        optimization_evaluation_task_id = self.cognitive_orchestrator.create_task(
            title="Optimization Evaluation",
            description="Evaluate the impact of implemented optimizations.",
            phase=CognitivePhase.REFLECT,
            worker_type=WorkerType.EVALUATION,
            priority=TaskPriority.MEDIUM,
            context={
                "evaluation_metrics": ["execution_time", "resource_usage", "success_rate"],
                "related_tasks": [
                    component_analysis_task_id,
                    behavior_monitoring_task_id,
                    interaction_analysis_task_id,
                    workflow_optimization_task_id
                ]
            }
        )
        
        # Update cognitive orchestrator development context
        self.cognitive_orchestrator.update_development_context(
            "introspection_enabled", True
        )
        
        # Store tasks in the context for reference
        self.cognitive_orchestrator.update_development_context(
            "introspection_tasks", {
                "component_analysis": component_analysis_task_id,
                "behavior_monitoring": behavior_monitoring_task_id,
                "interaction_analysis": interaction_analysis_task_id,
                "workflow_optimization": workflow_optimization_task_id,
                "optimization_evaluation": optimization_evaluation_task_id
            }
        )
        
        logger.info(f"Introspective cognitive loop enabled with initial tasks: {component_analysis_task_id}, {behavior_monitoring_task_id}")
        return {
            "component_analysis_task_id": component_analysis_task_id,
            "behavior_monitoring_task_id": behavior_monitoring_task_id,
            "interaction_analysis_task_id": interaction_analysis_task_id,
            "workflow_optimization_task_id": workflow_optimization_task_id,
            "optimization_evaluation_task_id": optimization_evaluation_task_id
        }

    # Planning Engine Integration Methods
    
    async def create_integrated_plan(
        self, 
        name: str,
        description: str,
        goal_requirements: Dict[str, Any],
        goal_type: str,
        strategy: str = "TOP_DOWN",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an integrated plan with all components.
        
        Args:
            name: Name of the integrated plan
            description: Description of the plan
            goal_requirements: Requirements for the goal
            goal_type: Type of goal (RESEARCH, DEVELOPMENT, ANALYSIS, etc.)
            strategy: Strategy for goal decomposition (TOP_DOWN, BOTTOM_UP, etc.)
            context: Additional context information
            
        Returns:
            Dictionary containing the integrated plan ID and summary
        """
        logger.info(f"Creating integrated plan: {name}")
        
        # Convert string parameters to enum values
        from src.server.planning.goal_decomposition import GoalType, DecompositionStrategy
        
        goal_type_enum = GoalType[goal_type]
        decomposition_strategy = DecompositionStrategy[strategy]
        
        # Create complete plan
        plan = await self.planning_engine.create_complete_plan(
            name=name,
            description=description,
            goal_requirements=goal_requirements,
            goal_type=goal_type_enum,
            decomposition_strategy=decomposition_strategy,
            context=context
        )
        
        # Collect metrics
        if plan.metrics and self.planning_metrics_collector:
            self.planning_metrics_collector.collect_metrics(
                plan_id=plan.id,
                metrics=plan.metrics,
                context={"creation_context": context}
            )
        
        # Convert to dictionary
        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "goal_decomposition_id": plan.goal_decomposition_id,
            "research_plan_ids": plan.research_plan_ids,
            "implementation_plan_id": plan.implementation_plan_id,
            "resource_allocation_id": plan.resource_allocation_id,
            "status": plan.status,
            "creation_time": plan.creation_time,
            "plan_type": plan.plan_type.value if plan.plan_type else None,
            "metrics": {
                "planning_time": plan.metrics.planning_time if plan.metrics else None,
                "complexity_score": plan.metrics.complexity_score if plan.metrics else None,
                "confidence_score": plan.metrics.confidence_score if plan.metrics else None,
                "resource_efficiency": plan.metrics.resource_efficiency if plan.metrics else None,
                "adaptability_score": plan.metrics.adaptability_score if plan.metrics else None
            } if plan.metrics else None,
            "metadata": plan.metadata
        }
    
    async def get_integrated_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an integrated plan by ID.
        
        Args:
            plan_id: ID of the plan
            
        Returns:
            Dictionary with plan details or None if not found
        """
        if not self.planning_engine:
            raise ValueError("Planning Engine not initialized")
        
        plan = self.planning_engine.integrated_plans.get(plan_id)
        if not plan:
            return None
        
        # Convert to dictionary
        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "goal_decomposition_id": plan.goal_decomposition_id,
            "research_plan_ids": plan.research_plan_ids,
            "implementation_plan_id": plan.implementation_plan_id,
            "resource_allocation_id": plan.resource_allocation_id,
            "status": plan.status,
            "creation_time": plan.creation_time,
            "plan_type": plan.plan_type.value if plan.plan_type else None,
            "version_history": [
                {
                    "id": v.version_id,
                    "timestamp": v.timestamp,
                    "changes": v.changes
                }
                for v in plan.version_history
            ] if plan.version_history else [],
            "metadata": plan.metadata
        }
    
    async def update_integrated_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any],
        change_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing integrated plan.
        
        Args:
            plan_id: ID of the plan to update
            updates: Updates to apply to the plan
            change_description: Description of the changes
            context: Additional context
            
        Returns:
            Dictionary with updated plan details
        """
        if not self.planning_engine:
            raise ValueError("Planning Engine not initialized")
            
        context = context or {}
        
        # Update the plan
        updated_plan = await self.planning_engine.update_plan(
            plan_id=plan_id,
            updates=updates,
            change_description=change_description,
            context=context
        )
        
        # Convert to dictionary
        return {
            "id": updated_plan.id,
            "name": updated_plan.name,
            "status": updated_plan.status,
            "latest_version": {
                "id": updated_plan.version_history[-1].version_id,
                "timestamp": updated_plan.version_history[-1].timestamp,
                "changes": updated_plan.version_history[-1].changes
            } if updated_plan.version_history else None,
            "version_count": len(updated_plan.version_history) if updated_plan.version_history else 0
        }
    
    async def list_integrated_plans(
        self,
        plan_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List integrated plans with optional filtering.
        
        Args:
            plan_type: Filter by plan type
            status: Filter by status
            
        Returns:
            List of plan summaries
        """
        if not self.planning_engine:
            raise ValueError("Planning Engine not initialized")
        
        results = []
        
        for plan in self.planning_engine.integrated_plans.values():
            # Apply filters if specified
            if plan_type and (not plan.plan_type or plan.plan_type.value != plan_type):
                continue
                
            if status and plan.status != status:
                continue
            
            # Add summary to results
            results.append({
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status,
                "creation_time": plan.creation_time,
                "plan_type": plan.plan_type.value if plan.plan_type else None
            })
        
        return results
    
    async def create_research_driven_workflow(
        self,
        name: str,
        description: str,
        initial_goal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a research-driven workflow that adapts based on research findings.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            initial_goal: Initial goal definition
            context: Additional context information
            
        Returns:
            Dictionary with workflow details
        """
        if not self.planning_workflow:
            raise ValueError("Planning Workflow not initialized")
            
        context = context or {}
        
        # Create workflow
        workflow_id = await self.planning_workflow.create_research_driven_workflow(
            name=name,
            description=description,
            initial_goal=initial_goal,
            context=context
        )
        
        # Get workflow status
        status = await self.planning_workflow.get_workflow_status(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "type": "research_driven",
            "status": status["status"],
            "steps": list(status["steps"].keys()),
            "step_order": status["step_order"]
        }
    
    async def create_implementation_focused_workflow(
        self,
        name: str,
        description: str,
        implementation_requirements: List[str],
        constraints: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an implementation-focused workflow that emphasizes solution design.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            implementation_requirements: Implementation requirements
            constraints: Implementation constraints
            context: Additional context information
            
        Returns:
            Dictionary with workflow details
        """
        if not self.planning_workflow:
            raise ValueError("Planning Workflow not initialized")
            
        context = context or {}
        
        # Create workflow
        workflow_id = await self.planning_workflow.create_implementation_focused_workflow(
            name=name,
            description=description,
            implementation_requirements=implementation_requirements,
            constraints=constraints,
            context=context
        )
        
        # Get workflow status
        status = await self.planning_workflow.get_workflow_status(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "type": "implementation_focused",
            "status": status["status"],
            "steps": list(status["steps"].keys()),
            "step_order": status["step_order"]
        }
    
    async def execute_planning_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a planning workflow by processing its steps in order.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Workflow execution result
        """
        if not self.planning_workflow:
            raise ValueError("Planning Workflow not initialized")
        
        # Execute workflow
        result = await self.planning_workflow.execute_workflow(workflow_id)
        
        return result
    
    async def get_planning_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the current status of a planning workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow status information
        """
        if not self.planning_workflow:
            raise ValueError("Planning Workflow not initialized")
        
        return await self.planning_workflow.get_workflow_status(workflow_id)
    
    async def visualize_integrated_plan(
        self,
        plan_id: str,
        visualization_type: str,
        output_format: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a visualization for an integrated plan.
        
        Args:
            plan_id: ID of the plan to visualize
            visualization_type: Type of visualization to generate
            output_format: Output format for the visualization
            context: Additional context for the visualization
            
        Returns:
            Visualization result with content and metadata
        """
        if not self.planning_visualization:
            raise ValueError("Planning Visualization not initialized")
            
        if not self.planning_engine:
            raise ValueError("Planning Engine not initialized")
            
        # Get the plan
        plan = self.planning_engine.integrated_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
            
        # Convert string types to enums
        vis_type = VisualizationType(visualization_type)
        out_format = OutputFormat(output_format)
        
        # Generate visualization
        result = self.planning_visualization.visualize_integrated_plan(
            plan=plan,
            visualization_type=vis_type,
            output_format=out_format,
            context=context
        )
        
        return {
            "visualization_id": result["id"],
            "plan_id": result["plan_id"],
            "type": result["type"],
            "format": result["format"],
            "content_type": result["content_type"],
            "content": result["content"]
        }
    
    async def get_plan_metrics(
        self,
        plan_id: str,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """
        Get metrics for a plan.
        
        Args:
            plan_id: ID of the plan
            include_trends: Whether to include trend analysis
            
        Returns:
            Dictionary with metrics data
        """
        if not self.planning_metrics_collector:
            raise ValueError("Planning Metrics Collector not initialized")
        
        # Generate metrics report
        report = self.planning_metrics_collector.generate_metrics_report(
            plan_id=plan_id,
            include_trends=include_trends
        )
        
        return report
    
    async def compare_plans(
        self,
        plan_ids: List[str],
        comparison_metrics: List[str],
        output_format: str
    ) -> Dict[str, Any]:
        """
        Compare multiple plans and visualize the comparison.
        
        Args:
            plan_ids: List of plan IDs to compare
            comparison_metrics: Metrics to use for comparison
            output_format: Output format for the visualization
            
        Returns:
            Comparison visualization result
        """
        if not self.planning_visualization:
            raise ValueError("Planning Visualization not initialized")
            
        if not self.planning_engine:
            raise ValueError("Planning Engine not initialized")
            
        # Get the plans
        plans = []
        for plan_id in plan_ids:
            plan = self.planning_engine.integrated_plans.get(plan_id)
            if plan:
                plans.append(plan)
        
        if not plans:
            raise ValueError("No valid plans found")
            
        # Convert output format string to enum
        out_format = OutputFormat(output_format)
        
        # Generate comparison
        result = self.planning_visualization.compare_plans(
            plans=plans,
            comparison_metrics=comparison_metrics,
            output_format=out_format
        )
        
        return {
            "visualization_id": result["id"],
            "type": result["type"],
            "format": result["format"],
            "content_type": result["content_type"],
            "content": result["content"],
            "plan_count": len(plans)
        } 