Phase 1 Completion Plan: Detailed Instructions for Next Development Session
Overview
To complete Phase 1 of the Self-Aware Cerebrum implementation, we need to focus on three key areas:
Parallel Execution Controller
System Access Layer (Package Management, Version Control, Test Runner)
Observability Foundations (Multi-Human Supervision Hub, Budget & Resource Monitor, Metrics Collection)
Below are detailed instructions for implementing these components in your next development session.
1. Parallel Execution Controller Implementation
File Path: src/server/execution/parallel_controller.py
Key Classes and Methods:
class ParallelExecutionController:
    """Manages parallel execution of tasks with resource-aware scheduling."""
    
    def __init__(self, max_concurrent_tasks: int = 5, resource_limits: Optional[Dict[str, float]] = None):
        """Initialize the controller with resource limits."""
        # Implementation details
        
    async def execute_tasks(self, tasks: List[Task], strategy: str = "resource_aware") -> Dict[str, Any]:
        """Execute multiple tasks in parallel using the specified strategy."""
        # Implementation details
        
    async def add_task(self, task: Task, dependencies: List[str] = None) -> str:
        """Add a task to the execution queue with optional dependencies."""
        # Implementation details
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task."""
        # Implementation details
        
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the current status of a task."""
        # Implementation details
        
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for a task to complete and return its result."""
        # Implementation detailsImplementation Notes:
Use asyncio for managing concurrent task execution
Implement resource tracking for CPU, memory, and API call limits
Create dependency resolution to ensure tasks execute in the correct order
Develop result aggregation for combining outputs from parallel tasks
Implement timeout and cancellation mechanisms
2. System Access Layer Implementation
2.1 Package Management
File Path: src/server/system_access/package_manager.py
Key Classes and Methods:
class PackageManager:
    """Manages Python package installation and dependencies."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with security configuration."""
        # Implementation details
        
    async def install_package(self, package_name: str, version: Optional[str] = None, 
                             upgrade: bool = False, requires_approval: bool = True) -> Dict[str, Any]:
        """Install a Python package with optional version specification."""
        # Implementation details
        
    async def uninstall_package(self, package_name: str, requires_approval: bool = True) -> Dict[str, Any]:
        """Uninstall a Python package."""
        # Implementation details
        
    async def list_installed_packages(self) -> List[Dict[str, str]]:
        """List all installed packages with versions."""
        # Implementation details
        
    async def check_package_security(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Check package security against known vulnerabilities."""
        # Implementation details
        
    async def create_requirements_file(self, path: str = "requirements.txt") -> str:
        """Generate a requirements.txt file from installed packages."""
        # Implementation details
2.2 Version Control Integration
File Path: src/server/system_access/git_manager.py
Key Classes and Methods:
class GitManager:
    """Manages Git repository operations."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with security configuration."""
        # Implementation details
        
    async def clone_repository(self, url: str, path: Optional[str] = None, 
                              branch: Optional[str] = None, requires_approval: bool = True) -> Dict[str, Any]:
        """Clone a Git repository."""
        # Implementation details
        
    async def commit_changes(self, message: str, files: Optional[List[str]] = None, 
                            requires_approval: bool = True) -> Dict[str, Any]:
        """Commit changes to the repository."""
        # Implementation details
        
    async def push_changes(self, remote: str = "origin", branch: Optional[str] = None, 
                          requires_approval: bool = True) -> Dict[str, Any]:
        """Push committed changes to a remote repository."""
        # Implementation details
        
    async def pull_changes(self, remote: str = "origin", branch: Optional[str] = None) -> Dict[str, Any]:
        """Pull changes from a remote repository."""
        # Implementation details
        
    async def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> Dict[str, Any]:
        """Create a new branch."""
        # Implementation details
        
    async def get_repository_status(self) -> Dict[str, Any]:
        """Get the current status of the repository."""
        # Implementation details
2.3 Test Runner Integration
File Path: src/server/system_access/test_runner.py
Key Classes and Methods:
class TestRunner:
    """Manages test discovery, execution, and analysis."""
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize with project root directory."""
        # Implementation details
        
    async def discover_tests(self, path: Optional[str] = None, pattern: str = "test_*.py") -> List[Dict[str, Any]]:
        """Discover tests in the specified path."""
        # Implementation details
        
    async def run_tests(self, test_path: Optional[str] = None, pattern: Optional[str] = None, 
                       verbosity: int = 2) -> Dict[str, Any]:
        """Run tests and return results."""
        # Implementation details
        
    async def run_specific_test(self, test_id: str) -> Dict[str, Any]:
        """Run a specific test by ID."""
        # Implementation details
        
    async def analyze_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results for patterns and issues."""
        # Implementation details
        
    async def get_test_coverage(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """Get test coverage information."""
        # Implementation details
        
    async def generate_test(self, source_file: str, output_file: Optional[str] = None) -> str:
        """Generate a test file for the given source file."""
        # Implementation details
3. Observability Foundations Implementation
3.1 Multi-Human Supervision Hub
File Path: src/server/observability/supervision_hub.py
Key Classes and Methods:
class SupervisionHub:
    """Manages supervision by multiple humans with different roles."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize with storage path for supervision data."""
        # Implementation details
        
    async def register_supervisor(self, user_id: str, role: str, permissions: List[str]) -> Dict[str, Any]:
        """Register a new supervisor with role and permissions."""
        # Implementation details
        
    async def create_approval_request(self, operation_type: str, details: Dict[str, Any], 
                                     required_role: str) -> str:
        """Create a request for approval of an operation."""
        # Implementation details
        
    async def approve_request(self, request_id: str, supervisor_id: str, 
                             comments: Optional[str] = None) -> Dict[str, Any]:
        """Approve a pending request."""
        # Implementation details
        
    async def reject_request(self, request_id: str, supervisor_id: str, 
                            reason: str) -> Dict[str, Any]:
        """Reject a pending request."""
        # Implementation details
        
    async def get_pending_requests(self, supervisor_id: Optional[str] = None, 
                                  role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending approval requests, optionally filtered by supervisor or role."""
        # Implementation details
        
    async def create_notification(self, supervisor_ids: List[str], message: str, 
                                 level: str = "info", context: Optional[Dict[str, Any]] = None) -> str:
        """Create a notification for supervisors."""
        # Implementation details
3.2 Budget & Resource Monitor
File Path: src/server/observability/resource_monitor.py
Key Classes and Methods:
class ResourceMonitor:
    """Monitors and manages resource usage and budgets."""
    
    def __init__(self, budget_config: Optional[Dict[str, Any]] = None):
        """Initialize with budget configuration."""
        # Implementation details
        
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        # Implementation details
        
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        # Implementation details
        
    async def get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage statistics."""
        # Implementation details
        
    async def set_budget(self, resource_type: str, limit: float, 
                        period: str = "daily") -> Dict[str, Any]:
        """Set a budget for a specific resource type."""
        # Implementation details
        
    async def check_budget(self, resource_type: str) -> Dict[str, Any]:
        """Check current usage against budget for a resource type."""
        # Implementation details
        
    async def record_usage(self, resource_type: str, amount: float, 
                          operation_id: Optional[str] = None) -> None:
        """Record usage of a resource."""
        # Implementation details
        
    async def get_usage_history(self, resource_type: str, 
                               period: str = "daily") -> List[Dict[str, Any]]:
        """Get historical usage for a resource type."""
        # Implementation details
        
    async def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for budget thresholds that have been crossed."""
        # Implementation details
3.3 Metrics Collection
File Path: src/server/observability/metrics_collector.py
Key Classes and Methods:
class MetricsCollector:
    """Collects, stores, and analyzes system metrics."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize with storage path for metrics data."""
        # Implementation details
        
    async def start_collection(self, interval_seconds: float = 60.0) -> None:
        """Start metrics collection at the specified interval."""
        # Implementation details
        
    async def stop_collection(self) -> None:
        """Stop metrics collection."""
        # Implementation details
        
    async def record_metric(self, metric_name: str, value: float, 
                           tags: Optional[Dict[str, str]] = None) -> None:
        """Record a single metric value."""
        # Implementation details
        
    async def record_task_metrics(self, task_id: str, execution_time: float, 
                                 memory_usage: float, success: bool, 
                                 additional_metrics: Optional[Dict[str, float]] = None) -> None:
        """Record metrics for a task execution."""
        # Implementation details
        
    async def get_metrics(self, metric_name: str, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None, 
                         aggregation: str = "avg") -> List[Dict[str, Any]]:
        """Get metrics for a specific metric name with optional time range and aggregation."""
        # Implementation details
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        # Implementation details
        
    async def export_metrics(self, format: str = "json", 
                            path: Optional[str] = None) -> str:
        """Export metrics in the specified format."""
        # Implementation details
4. Integration with Self-Aware System
After implementing the above components, integrate them with the existing Self-Aware System:
File Path: src/server/self_aware_integration.py
Add the following imports and update the SelfAwareSystem class:
from src.server.execution.parallel_controller import ParallelExecutionController
from src.server.system_access.package_manager import PackageManager
from src.server.system_access.git_manager import GitManager
from src.server.system_access.test_runner import TestRunner
from src.server.observability.supervision_hub import SupervisionHub
from src.server.observability.resource_monitor import ResourceMonitor
from src.server.observability.metrics_collector import MetricsCollector

# Update the SelfAwareSystem class to include the new components
class SelfAwareSystem:
    """
    Integration of the Self-Aware Cerebrum components
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        # Existing initialization code...
        
        # Initialize new components
        self.parallel_controller = ParallelExecutionController()
        self.package_manager = PackageManager()
        self.git_manager = GitManager()
        self.test_runner = TestRunner()
        self.supervision_hub = SupervisionHub(os.path.join(self.storage_path, "supervision"))
        self.resource_monitor = ResourceMonitor()
        self.metrics_collector = MetricsCollector(os.path.join(self.storage_path, "metrics"))
        
        # Start monitoring and metrics collection
        asyncio.create_task(self.resource_monitor.start_monitoring())
        asyncio.create_task(self.metrics_collector.start_collection())
    
    # Add methods to expose the new components' functionality
    async def execute_tasks_in_parallel(self, tasks: List[Dict[str, Any]], strategy: str = "resource_aware") -> Dict[str, Any]:
        """Execute multiple tasks in parallel."""
        # Convert task dictionaries to Task objects and execute
        # Implementation details...
        
    async def install_package(self, package_name: str, version: Optional[str] = None, upgrade: bool = False) -> Dict[str, Any]:
        """Install a Python package."""
        return await self.package_manager.install_package(package_name, version, upgrade)
    
    # Add more methods for other components...

5. Update CLI and Streamlit UI
Update the CLI and Streamlit UI to expose the new functionality:
5.1 CLI Updates
Add new commands to src/server/cli.py for the new components:
# Add new command handlers to SelfAwareCLI class
def install_package(self, package_name: str, version: Optional[str] = None, upgrade: bool = False):
    """Install a Python package"""
    result = run_async(self.system.install_package(package_name, version, upgrade))
    return result

# Add more methods for other components...

# Update parse_args() to add new commands
def parse_args():
    # Existing code...
    
    # Add package management commands
    package_parser = subparsers.add_parser("package", help="Package management")
    package_subparsers = package_parser.add_subparsers(dest="package_command", help="Package command")
    
    install_parser = package_subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument("--name", required=True, help="Package name")
    install_parser.add_argument("--version", help="Package version")
    install_parser.add_argument("--upgrade", action="store_true", help="Upgrade package")
    
    # Add more commands for other components...
5.2 Streamlit UI Updates
Add new pages or sections to src/server/streamlit_app.py for the new components:
# Add new pages to the sidebar
page = st.sidebar.radio("Select Page", [
    "Dashboard", 
    "Cognitive Tasks", 
    "Knowledge Management", 
    "Development Context",
    "System Access",  # New page
    "Observability"   # New page
])

# Add new pages
elif page == "System Access":
    st.header("System Access")
    
    # Package Management
    st.subheader("Package Management")
    col1, col2, col3 = st.columns(3)
    with col1:
        package_name = st.text_input("Package Name")
    with col2:
        package_version = st.text_input("Version (optional)")
    with col3:
        upgrade = st.checkbox("Upgrade")
    
    if st.button("Install Package"):
        result = run_async(st.session_state.system.install_package(package_name, package_version, upgrade))
        st.json(result)
    
    # Add more UI elements for other components...

elif page == "Observability":
    st.header("Observability")
    
    # Resource Monitoring
    st.subheader("Resource Monitoring")
    if st.button("Get Current Usage"):
        usage = run_async(st.session_state.system.resource_monitor.get_current_usage())
        st.json(usage)
    
    # Add more UI elements for other components...
6. Testing Plan
Create tests for each new component:
6.1 Test Files
tests/server/execution/test_parallel_controller.py
tests/server/system_access/test_package_manager.py
tests/server/system_access/test_git_manager.py
tests/server/system_access/test_test_runner.py
tests/server/observability/test_supervision_hub.py
tests/server/observability/test_resource_monitor.py
tests/server/observability/test_metrics_collector.py
6.2 Test Cases
For each component, create tests that cover:
Basic functionality
Error handling
Edge cases
Integration with other components
7. Documentation Updates
Update the documentation to reflect the new components:
Update README.md with information about the new components
Create detailed documentation for each component in the docs directory
Update the high-level design document to reflect the completed Phase 1
Implementation Timeline
Here's a suggested timeline for implementing these components:
Week 1: Implement Parallel Execution Controller and System Access Layer
Week 2: Implement Observability Foundations
Week 3: Integration, testing, and documentation
Conclusion
This plan provides detailed instructions for completing Phase 1 of the Self-Aware Cerebrum implementation. By following these instructions, you'll implement the remaining components needed to establish a solid foundation for the subsequent phases.
After completing Phase 1, you'll be ready to move on to Phase 2 (Self-Modification Engine), which will enable the system to modify its own code with appropriate safety checks.
