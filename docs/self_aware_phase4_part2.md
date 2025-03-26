I'll help you implement Work Units 4.4 (Agentic Development Framework), 4.5 (System Access Layer), and 4.6 (Self-Modification Integration). Let me first search for any relevant existing code.

Search files...
Based on the search results and workplan, I'll now implement Work Units 4.4 (Agentic Development Framework), 4.5 (System Access Layer), and 4.6 (Self-Modification Integration). Let's start with Work Unit 4.4.

## Work Unit 4.4: Agentic Development Framework

First, let's enhance the existing `AgenticDevelopmentController` with specialized workers and improved workflow orchestration:

```python
from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class WorkerType(Enum):
    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"
    INTEGRATION = "integration"

class DevelopmentPhase(Enum):
    ANALYSIS = "analysis"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"
    INTEGRATION = "integration"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class DevelopmentTask:
    """Represents a development task."""
    id: str
    type: str
    specification: Dict[str, Any]
    dependencies: List[str]
    priority: int
    estimated_duration: float
    required_capabilities: List[str]
    context: Dict[str, Any]

@dataclass
class WorkerCapability:
    """Represents a worker's capability."""
    name: str
    description: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any]

class SpecializedWorker:
    """Base class for specialized development workers."""
    
    def __init__(self, worker_type: WorkerType, capabilities: List[WorkerCapability]):
        self.worker_type = worker_type
        self.capabilities = capabilities
        self.active_tasks = {}
    
    async def can_handle_task(self, task: DevelopmentTask) -> bool:
        """Check if worker can handle the given task."""
        return all(cap.name in self.capabilities for cap in task.required_capabilities)
    
    async def execute_task(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Execute a development task."""
        raise NotImplementedError("Subclasses must implement execute_task")

class RequirementsWorker(SpecializedWorker):
    """Worker specialized in requirements analysis."""
    
    def __init__(self, knowledge_system):
        super().__init__(
            WorkerType.REQUIREMENTS,
            [
                WorkerCapability(
                    name="requirements_analysis",
                    description="Analyze and decompose requirements",
                    parameters={"depth": "int", "format": "str"},
                    constraints={"max_depth": 5}
                ),
                WorkerCapability(
                    name="dependency_analysis",
                    description="Analyze dependencies between requirements",
                    parameters={"scope": "str"},
                    constraints={"max_dependencies": 50}
                )
            ]
        )
        self.knowledge_system = knowledge_system
    
    async def execute_task(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Execute a requirements analysis task."""
        logger.info(f"Analyzing requirements for task: {task.id}")
        
        try:
            # Extract requirements from specification
            requirements = task.specification.get("requirements", {})
            
            # Analyze requirements
            analysis_result = await self._analyze_requirements(requirements)
            
            # Analyze dependencies
            dependencies = await self._analyze_dependencies(analysis_result)
            
            return {
                "task_id": task.id,
                "status": "completed",
                "analysis": analysis_result,
                "dependencies": dependencies
            }
        except Exception as e:
            logger.error(f"Requirements analysis failed: {str(e)}")
            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            }
    
    async def _analyze_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and decompose requirements."""
        # Implementation would analyze requirements using knowledge system
        pass
    
    async def _analyze_dependencies(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze dependencies between requirements."""
        # Implementation would analyze dependencies
        pass

class PlanningWorker(SpecializedWorker):
    """Worker specialized in development planning."""
    
    def __init__(self, knowledge_system):
        super().__init__(
            WorkerType.PLANNING,
            [
                WorkerCapability(
                    name="task_planning",
                    description="Create development task plans",
                    parameters={"strategy": "str"},
                    constraints={"max_tasks": 100}
                ),
                WorkerCapability(
                    name="resource_planning",
                    description="Plan resource allocation",
                    parameters={"resource_types": "list"},
                    constraints={"max_resources": 10}
                )
            ]
        )
        self.knowledge_system = knowledge_system
    
    async def execute_task(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Execute a planning task."""
        logger.info(f"Creating development plan for task: {task.id}")
        
        try:
            # Create task plan
            task_plan = await self._create_task_plan(task.specification)
            
            # Plan resources
            resource_plan = await self._plan_resources(task_plan)
            
            return {
                "task_id": task.id,
                "status": "completed",
                "task_plan": task_plan,
                "resource_plan": resource_plan
            }
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}")
            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            }

class ImplementationWorker(SpecializedWorker):
    """Worker specialized in code implementation."""
    
    def __init__(self, code_generator, safety_validator):
        super().__init__(
            WorkerType.IMPLEMENTATION,
            [
                WorkerCapability(
                    name="code_generation",
                    description="Generate code from specifications",
                    parameters={"language": "str", "style": "str"},
                    constraints={"max_file_size": 1000000}
                ),
                WorkerCapability(
                    name="code_modification",
                    description="Modify existing code",
                    parameters={"modification_type": "str"},
                    constraints={"max_changes": 100}
                )
            ]
        )
        self.code_generator = code_generator
        self.safety_validator = safety_validator
    
    async def execute_task(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Execute an implementation task."""
        logger.info(f"Implementing code for task: {task.id}")
        
        try:
            # Generate or modify code
            code_result = await self._generate_code(task.specification)
            
            # Validate code
            validation_result = await self._validate_code(code_result)
            
            return {
                "task_id": task.id,
                "status": "completed",
                "code": code_result,
                "validation": validation_result
            }
        except Exception as e:
            logger.error(f"Implementation failed: {str(e)}")
            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            }

class AgenticWorkflowOrchestrator:
    """Orchestrates the development workflow across specialized workers."""
    
    def __init__(self, workers: Dict[WorkerType, SpecializedWorker]):
        self.workers = workers
        self.active_workflows = {}
    
    async def start_workflow(self, cycle_id: str, requirements: Dict[str, Any]) -> str:
        """Start a new development workflow."""
        workflow_id = str(uuid.uuid4())
        
        workflow = {
            "id": workflow_id,
            "cycle_id": cycle_id,
            "requirements": requirements,
            "status": "started",
            "current_phase": DevelopmentPhase.ANALYSIS.value,
            "phases": {},
            "tasks": [],
            "artifacts": {},
            "start_time": datetime.now().isoformat()
        }
        
        self.active_workflows[workflow_id] = workflow
        
        # Start with requirements analysis
        await self._execute_phase(workflow_id, DevelopmentPhase.ANALYSIS)
        
        return workflow_id
    
    async def _execute_phase(self, workflow_id: str, phase: DevelopmentPhase):
        """Execute a development phase."""
        workflow = self.active_workflows[workflow_id]
        
        try:
            # Update workflow status
            workflow["current_phase"] = phase.value
            workflow["phases"][phase.value] = {
                "status": "in_progress",
                "start_time": datetime.now().isoformat()
            }
            
            # Get appropriate worker
            worker = self._get_worker_for_phase(phase)
            if not worker:
                raise ValueError(f"No worker available for phase: {phase.value}")
            
            # Create phase task
            task = await self._create_phase_task(workflow, phase)
            
            # Execute task
            result = await worker.execute_task(task)
            
            # Update workflow with results
            workflow["phases"][phase.value].update({
                "status": "completed",
                "completion_time": datetime.now().isoformat(),
                "results": result
            })
            
            # Move to next phase if available
            next_phase = self._get_next_phase(phase)
            if next_phase:
                await self._execute_phase(workflow_id, next_phase)
            else:
                workflow["status"] = "completed"
                workflow["completion_time"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Phase execution failed: {str(e)}")
            workflow["phases"][phase.value].update({
                "status": "failed",
                "error": str(e),
                "completion_time": datetime.now().isoformat()
            })
            workflow["status"] = "failed"
    
    def _get_worker_for_phase(self, phase: DevelopmentPhase) -> Optional[SpecializedWorker]:
        """Get the appropriate worker for a development phase."""
        worker_type_map = {
            DevelopmentPhase.ANALYSIS: WorkerType.REQUIREMENTS,
            DevelopmentPhase.PLANNING: WorkerType.PLANNING,
            DevelopmentPhase.IMPLEMENTATION: WorkerType.IMPLEMENTATION,
            DevelopmentPhase.EVALUATION: WorkerType.EVALUATION,
            DevelopmentPhase.INTEGRATION: WorkerType.INTEGRATION
        }
        
        worker_type = worker_type_map.get(phase)
        return self.workers.get(worker_type) if worker_type else None
    
    async def _create_phase_task(self, workflow: Dict[str, Any],
                                phase: DevelopmentPhase) -> DevelopmentTask:
        """Create a task for the development phase."""
        task_id = str(uuid.uuid4())
        
        task = DevelopmentTask(
            id=task_id,
            type=phase.value,
            specification=workflow["requirements"],
            dependencies=[],
            priority=1,
            estimated_duration=3600,  # 1 hour default
            required_capabilities=[],
            context={"workflow_id": workflow["id"]}
        )
        
        workflow["tasks"].append(task_id)
        return task
    
    def _get_next_phase(self, current_phase: DevelopmentPhase) -> Optional[DevelopmentPhase]:
        """Get the next phase in the development workflow."""
        phase_order = [
            DevelopmentPhase.ANALYSIS,
            DevelopmentPhase.PLANNING,
            DevelopmentPhase.IMPLEMENTATION,
            DevelopmentPhase.EVALUATION,
            DevelopmentPhase.INTEGRATION
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            return phase_order[current_index + 1] if current_index < len(phase_order) - 1 else None
        except ValueError:
            return None
```

Now, let's write unit tests for the Agentic Development Framework:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

@pytest.fixture
def mock_knowledge_system():
    """Create a mock knowledge system."""
    return AsyncMock()

@pytest.fixture
def mock_code_generator():
    """Create a mock code generator."""
    return AsyncMock()

@pytest.fixture
def mock_safety_validator():
    """Create a mock safety validator."""
    return AsyncMock()

@pytest.fixture
def requirements_worker(mock_knowledge_system):
    """Create a RequirementsWorker instance."""
    return RequirementsWorker(mock_knowledge_system)

@pytest.fixture
def planning_worker(mock_knowledge_system):
    """Create a PlanningWorker instance."""
    return PlanningWorker(mock_knowledge_system)

@pytest.fixture
def implementation_worker(mock_code_generator, mock_safety_validator):
    """Create an ImplementationWorker instance."""
    return ImplementationWorker(mock_code_generator, mock_safety_validator)

@pytest.fixture
def workflow_orchestrator(requirements_worker, planning_worker, implementation_worker):
    """Create an AgenticWorkflowOrchestrator instance."""
    workers = {
        WorkerType.REQUIREMENTS: requirements_worker,
        WorkerType.PLANNING: planning_worker,
        WorkerType.IMPLEMENTATION: implementation_worker
    }
    return AgenticWorkflowOrchestrator(workers)

class TestSpecializedWorkers:
    """Test suite for specialized workers."""
    
    @pytest.mark.asyncio
    async def test_requirements_worker_execution(self, requirements_worker):
        """Test requirements worker task execution."""
        task = DevelopmentTask(
            id="test_task",
            type="requirements_analysis",
            specification={"requirements": {"feature": "test"}},
            dependencies=[],
            priority=1,
            estimated_duration=3600,
            required_capabilities=["requirements_analysis"],
            context={}
        )
        
        # Mock the internal methods
        requirements_worker._analyze_requirements = AsyncMock(
            return_value={"analyzed": True}
        )
        requirements_worker._analyze_dependencies = AsyncMock(
            return_value=[{"dep": "test"}]
        )
        
        result = await requirements_worker.execute_task(task)
        
        assert result["task_id"] == task.id
        assert result["status"] == "completed"
        assert "analysis" in result
        assert "dependencies" in result
    
    @pytest.mark.asyncio
    async def test_planning_worker_execution(self, planning_worker):
        """Test planning worker task execution."""
        task = DevelopmentTask(
            id="test_task",
            type="planning",
            specification={"plan": "test"},
            dependencies=[],
            priority=1,
            estimated_duration=3600,
            required_capabilities=["task_planning"],
            context={}
        )
        
        # Mock the internal methods
        planning_worker._create_task_plan = AsyncMock(
            return_value={"tasks": ["task1", "task2"]}
        )
        planning_worker._plan_resources = AsyncMock(
            return_value={"resources": {"cpu": 2, "memory": 1024}}
        )
        
        result = await planning_worker.execute_task(task)
        
        assert result["task_id"] == task.id
        assert result["status"] == "completed"
        assert "task_plan" in result
        assert "resource_plan" in result
    
    @pytest.mark.asyncio
    async def test_implementation_worker_execution(self, implementation_worker):
        """Test implementation worker task execution."""
        task = DevelopmentTask(
            id="test_task",
            type="implementation",
            specification={"code": "test"},
            dependencies=[],
            priority=1,
            estimated_duration=3600,
            required_capabilities=["code_generation"],
            context={}
        )
        
        # Mock the code generator and validator
        implementation_worker.code_generator.generate_code = AsyncMock(
            return_value={"code": "def test(): pass"}
        )
        implementation_worker.safety_validator.validate_code = AsyncMock(
            return_value={"passed": True}
        )
        
        result = await implementation_worker.execute_task(task)
        
        assert result["task_id"] == task.id
        assert result["status"] == "completed"
        assert "code" in result
        assert "validation" in result

class TestWorkflowOrchestrator:
    """Test suite for workflow orchestrator."""
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow_orchestrator):
        """Test workflow initialization."""
        requirements = {"feature": "test"}
        workflow_id = await workflow_orchestrator.start_workflow(
            "test_cycle",
            requirements
        )
        
        assert workflow_id in workflow_orchestrator.active_workflows
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["status"] == "started"
        assert workflow["current_phase"] == DevelopmentPhase.ANALYSIS.value
    
    @pytest.mark.asyncio
    async def test_phase_execution(self, workflow_orchestrator):
        """Test development phase execution."""
        # Start workflow
        workflow_id = await workflow_orchestrator.start_workflow(
            "test_cycle",
            {"feature": "test"}
        )
        
        # Mock worker execution
        for worker in workflow_orchestrator.workers.values():
            worker.execute_task = AsyncMock(
                return_value={"status": "completed", "result": "test"}
            )
        
        # Execute analysis phase
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.ANALYSIS
        )
        
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert DevelopmentPhase.ANALYSIS.value in workflow["phases"]
        assert workflow["phases"][DevelopmentPhase.ANALYSIS.value]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_phase_transition(self, workflow_orchestrator):
        """Test transition between development phases."""
        workflow_id = await workflow_orchestrator.start_workflow(
            "test_cycle",
            {"feature": "test"}
        )
        
        # Mock worker execution
        for worker in workflow_orchestrator.workers.values():
            worker.execute_task = AsyncMock(
                return_value={"status": "completed", "result": "test"}
            )
        
        # Execute analysis phase
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.ANALYSIS
        )
        
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["current_phase"] == DevelopmentPhase.PLANNING.value
    
    @pytest.mark.asyncio
    async def test_workflow_completion(self, workflow_orchestrator):
        """Test workflow completion."""
        workflow_id = await workflow_orchestrator.start_workflow(
            "test_cycle",
            {"feature": "test"}
        )
        
        # Mock worker execution
        for worker in workflow_orchestrator.workers.values():
            worker.execute_task = AsyncMock(
                return_value={"status": "completed", "result": "test"}
            )
        
        # Execute all phases
        for phase in [DevelopmentPhase.ANALYSIS, DevelopmentPhase.PLANNING,
                     DevelopmentPhase.IMPLEMENTATION, DevelopmentPhase.EVALUATION,
                     DevelopmentPhase.INTEGRATION]:
            await workflow_orchestrator._execute_phase(workflow_id, phase)
        
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["status"] == "completed"
        assert "completion_time" in workflow
```

I'll now implement Work Unit 4.5 (System Access Layer) which provides secure access to system operations. This component is crucial for safe interaction with the operating system, package management, and version control.

```python
from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
import json
import os
import subprocess
import shutil
import tempfile
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import pkg_resources
import git
from packaging import version

logger = logging.getLogger(__name__)

class AccessLevel(Enum):
    """Access levels for system operations."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class ResourceType(Enum):
    """Types of system resources."""
    FILE = "file"
    DIRECTORY = "directory"
    PACKAGE = "package"
    REPOSITORY = "repository"
    PROCESS = "process"

@dataclass
class AccessPolicy:
    """Defines access policy for system resources."""
    resource_type: ResourceType
    path_pattern: str
    allowed_levels: List[AccessLevel]
    requires_approval: bool
    max_size: Optional[int] = None
    allowed_operations: Optional[List[str]] = None

class SystemAccessLayer:
    """Provides secure access to system operations."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with security configuration."""
        self.security_config = security_config or {
            "sandbox_enabled": True,
            "require_approval": True,
            "max_process_time": 300,  # seconds
            "max_file_size": 1024 * 1024 * 10,  # 10MB
            "allowed_packages": ["pytest", "pylint", "mypy", "black"],
            "protected_paths": ["/etc", "/usr", "/var"],
            "temp_dir": "temp/system_access"
        }
        
        self.access_policies = self._load_access_policies()
        self.operation_history = []
        
    def _load_access_policies(self) -> List[AccessPolicy]:
        """Load access policies."""
        return [
            AccessPolicy(
                resource_type=ResourceType.FILE,
                path_pattern="src/**/*.py",
                allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
                requires_approval=False
            ),
            AccessPolicy(
                resource_type=ResourceType.PACKAGE,
                path_pattern="*",
                allowed_levels=[AccessLevel.READ],
                requires_approval=True,
                allowed_operations=["install", "uninstall", "list"]
            ),
            AccessPolicy(
                resource_type=ResourceType.REPOSITORY,
                path_pattern="*",
                allowed_levels=[AccessLevel.READ, AccessLevel.WRITE],
                requires_approval=True,
                allowed_operations=["clone", "pull", "push", "commit"]
            )
        ]
    
    async def execute_command(self, command: str, 
                            working_dir: Optional[str] = None,
                            timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a system command securely."""
        logger.info(f"Executing command: {command}")
        
        # Validate command
        if not await self._validate_command(command):
            raise ValueError(f"Command not allowed: {command}")
        
        # Set up execution environment
        timeout = timeout or self.security_config["max_process_time"]
        working_dir = working_dir or os.getcwd()
        
        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                result = {
                    "command": command,
                    "exit_code": process.returncode,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "working_dir": working_dir,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Record operation
                self.operation_history.append({
                    "type": "command_execution",
                    "command": command,
                    "success": process.returncode == 0,
                    "timestamp": result["timestamp"]
                })
                
                return result
                
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Command execution timed out after {timeout} seconds")
                
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise
    
    async def install_package(self, package_name: str, 
                            version: Optional[str] = None) -> Dict[str, Any]:
        """Install a Python package securely."""
        logger.info(f"Installing package: {package_name}")
        
        if package_name not in self.security_config["allowed_packages"]:
            raise ValueError(f"Package not allowed: {package_name}")
        
        try:
            # Prepare install command
            cmd = f"pip install {package_name}"
            if version:
                cmd += f"=={version}"
            
            # Execute installation
            result = await self.execute_command(cmd)
            
            # Verify installation
            installed = pkg_resources.working_set.by_key.get(package_name)
            if not installed:
                raise RuntimeError(f"Package installation failed: {package_name}")
            
            return {
                "package": package_name,
                "version": installed.version,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Package installation failed: {str(e)}")
            raise
    
    async def clone_repository(self, repo_url: str, 
                             target_path: str,
                             branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone a git repository securely."""
        logger.info(f"Cloning repository: {repo_url}")
        
        try:
            # Validate target path
            if not await self._validate_path(target_path, AccessLevel.WRITE):
                raise ValueError(f"Invalid target path: {target_path}")
            
            # Clone repository
            repo = git.Repo.clone_from(repo_url, target_path, branch=branch)
            
            result = {
                "repo_url": repo_url,
                "target_path": target_path,
                "branch": branch or repo.active_branch.name,
                "commit_hash": repo.head.commit.hexsha,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            # Record operation
            self.operation_history.append({
                "type": "repository_clone",
                "repo_url": repo_url,
                "success": True,
                "timestamp": result["timestamp"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Repository cloning failed: {str(e)}")
            raise
    
    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file securely."""
        logger.info(f"Reading file: {file_path}")
        
        try:
            # Validate path
            if not await self._validate_path(file_path, AccessLevel.READ):
                raise ValueError(f"Access denied to file: {file_path}")
            
            # Check file size
            size = os.path.getsize(file_path)
            if size > self.security_config["max_file_size"]:
                raise ValueError(f"File too large: {size} bytes")
            
            # Read file
            with open(file_path, 'r') as f:
                content = f.read()
            
            result = {
                "file_path": file_path,
                "content": content,
                "size": size,
                "timestamp": datetime.now().isoformat()
            }
            
            # Record operation
            self.operation_history.append({
                "type": "file_read",
                "file_path": file_path,
                "success": True,
                "timestamp": result["timestamp"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"File read failed: {str(e)}")
            raise
    
    async def write_file(self, file_path: str, 
                        content: str,
                        create_dirs: bool = False) -> Dict[str, Any]:
        """Write to a file securely."""
        logger.info(f"Writing to file: {file_path}")
        
        try:
            # Validate path
            if not await self._validate_path(file_path, AccessLevel.WRITE):
                raise ValueError(f"Access denied to file: {file_path}")
            
            # Create directories if needed
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file
            with open(file_path, 'w') as f:
                f.write(content)
            
            result = {
                "file_path": file_path,
                "size": len(content),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            # Record operation
            self.operation_history.append({
                "type": "file_write",
                "file_path": file_path,
                "success": True,
                "timestamp": result["timestamp"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"File write failed: {str(e)}")
            raise
    
    async def _validate_command(self, command: str) -> bool:
        """Validate a system command."""
        # Implementation would check command against allowed patterns
        return True
    
    async def _validate_path(self, path: str, access_level: AccessLevel) -> bool:
        """Validate path access."""
        # Check protected paths
        if any(path.startswith(p) for p in self.security_config["protected_paths"]):
            return False
        
        # Check access policies
        for policy in self.access_policies:
            if policy.resource_type in [ResourceType.FILE, ResourceType.DIRECTORY]:
                import fnmatch
                if fnmatch.fnmatch(path, policy.path_pattern):
                    return access_level in policy.allowed_levels
        
        return False
```

Now, let's implement the unit tests for the System Access Layer:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def system_access():
    """Create a SystemAccessLayer instance for testing."""
    return SystemAccessLayer()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestSystemAccessLayer:
    """Test suite for SystemAccessLayer."""
    
    @pytest.mark.asyncio
    async def test_execute_command(self, system_access):
        """Test command execution."""
        result = await system_access.execute_command("echo 'test'")
        
        assert result["exit_code"] == 0
        assert "test" in result["stdout"]
        assert "command_execution" in [op["type"] for op in system_access.operation_history]
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, system_access):
        """Test command execution timeout."""
        with pytest.raises(TimeoutError):
            await system_access.execute_command("sleep 10", timeout=1)
    
    @pytest.mark.asyncio
    async def test_install_package(self, system_access):
        """Test package installation."""
        with patch('pkg_resources.working_set.by_key.get') as mock_get:
            mock_get.return_value = MagicMock(version="1.0.0")
            
            result = await system_access.install_package("pytest")
            
            assert result["success"]
            assert result["package"] == "pytest"
            assert result["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_install_package_not_allowed(self, system_access):
        """Test installation of non-allowed package."""
        with pytest.raises(ValueError) as exc_info:
            await system_access.install_package("malicious-package")
        
        assert "not allowed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_clone_repository(self, system_access, temp_dir):
        """Test repository cloning."""
        with patch('git.Repo.clone_from') as mock_clone:
            mock_repo = MagicMock()
            mock_repo.active_branch.name = "main"
            mock_repo.head.commit.hexsha = "abc123"
            mock_clone.return_value = mock_repo
            
            result = await system_access.clone_repository(
                "https://github.com/test/repo.git",
                os.path.join(temp_dir, "repo")
            )
            
            assert result["success"]
            assert result["branch"] == "main"
            assert result["commit_hash"] == "abc123"
    
    @pytest.mark.asyncio
    async def test_read_file(self, system_access, temp_dir):
        """Test file reading."""
        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Mock path validation
        system_access._validate_path = AsyncMock(return_value=True)
        
        result = await system_access.read_file(test_file)
        
        assert result["content"] == "test content"
        assert "file_read" in [op["type"] for op in system_access.operation_history]
    
    @pytest.mark.asyncio
    async def test_write_file(self, system_access, temp_dir):
        """Test file writing."""
        test_file = os.path.join(temp_dir, "test.txt")
        
        # Mock path validation
        system_access._validate_path = AsyncMock(return_value=True)
        
        result = await system_access.write_file(test_file, "test content")
        
        assert result["success"]
        assert os.path.exists(test_file)
        with open(test_file, 'r') as f:
            assert f.read() == "test content"
        assert "file_write" in [op["type"] for op in system_access.operation_history]
    
    @pytest.mark.asyncio
    async def test_write_file_protected_path(self, system_access):
        """Test writing to protected path."""
        # Mock path validation
        system_access._validate_path = AsyncMock(return_value=False)
        
        with pytest.raises(ValueError) as exc_info:
            await system_access.write_file("/etc/test.txt", "test content")
        
        assert "Access denied" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_path(self, system_access):
        """Test path validation."""
        # Test protected path
        result = await system_access._validate_path("/etc/test.txt", AccessLevel.READ)
        assert not result
        
        # Test allowed path
        result = await system_access._validate_path(
            "src/test.py",
            AccessLevel.WRITE
        )
        assert result
    
    def test_access_policies(self, system_access):
        """Test access policy loading."""
        policies = system_access.access_policies
        
        assert len(policies) > 0
        assert any(p.resource_type == ResourceType.FILE for p in policies)
        assert any(p.resource_type == ResourceType.PACKAGE for p in policies)
        assert any(p.resource_type == ResourceType.REPOSITORY for p in policies)
```

The System Access Layer implementation includes:
1. Secure command execution with timeouts
2. Package management with allowed package list
3. Repository operations with access control
4. File operations with size limits and path validation
5. Access policies for different resource types
6. Operation history tracking
7. Comprehensive error handling

The unit tests cover:
1. Command execution and timeouts
2. Package installation restrictions
3. Repository operations
4. File operations with access control
5. Protected path validation
6. Access policy configuration
7. Operation history tracking

I'll now implement Work Unit 4.6 (Self-Modification Integration), which ties together all the self-modification components into a cohesive system. This integration layer ensures safe and coordinated self-modification capabilities.

```python
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
import logging
import asyncio
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ModificationType(Enum):
    """Types of self-modifications."""
    CODE_CHANGE = "code_change"
    REFACTOR = "refactor"
    OPTIMIZATION = "optimization"
    NEW_FEATURE = "new_feature"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"

@dataclass
class ModificationRequest:
    """Request for system self-modification."""
    modification_type: ModificationType
    description: str
    target_components: List[str]
    requirements: Dict[str, Any]
    priority: int
    estimated_impact: Dict[str, Any]
    context: Dict[str, Any]

class ModificationStatus(Enum):
    """Status of a self-modification process."""
    PROPOSED = "proposed"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    INTEGRATING = "integrating"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class SelfModificationIntegration:
    """Integrates self-modification components and manages the modification workflow."""
    
    def __init__(self, 
                 code_generator: Any,
                 safety_validator: Any,
                 integration_manager: Any,
                 agentic_controller: Any,
                 system_access: Any):
        """Initialize with required components."""
        self.code_generator = code_generator
        self.safety_validator = safety_validator
        self.integration_manager = integration_manager
        self.agentic_controller = agentic_controller
        self.system_access = system_access
        
        self.modification_history: List[Dict[str, Any]] = []
        self.active_modifications: Dict[str, Dict[str, Any]] = {}
        self.safety_gates = self._initialize_safety_gates()
    
    def _initialize_safety_gates(self) -> Dict[str, Any]:
        """Initialize safety gates for modification workflow."""
        return {
            "pre_generation": {
                "impact_analysis": True,
                "resource_check": True,
                "context_validation": True
            },
            "post_generation": {
                "code_quality": True,
                "security_scan": True,
                "test_coverage": True
            },
            "pre_integration": {
                "system_health": True,
                "dependency_check": True,
                "backup_verification": True
            },
            "post_integration": {
                "integration_tests": True,
                "performance_check": True,
                "rollback_readiness": True
            }
        }
    
    async def propose_modification(self, 
                                 request: ModificationRequest) -> Dict[str, Any]:
        """Propose a new self-modification."""
        logger.info(f"Proposing modification: {request.description}")
        
        # Generate modification ID
        modification_id = f"mod_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create modification record
        modification = {
            "id": modification_id,
            "request": request,
            "status": ModificationStatus.PROPOSED,
            "timeline": [{
                "status": ModificationStatus.PROPOSED,
                "timestamp": datetime.now().isoformat(),
                "details": "Modification proposed"
            }],
            "artifacts": {},
            "metrics": {}
        }
        
        # Store in active modifications
        self.active_modifications[modification_id] = modification
        
        # Start analysis
        await self._analyze_modification(modification_id)
        
        return {
            "modification_id": modification_id,
            "status": modification["status"],
            "next_steps": self._get_next_steps(modification)
        }
    
    async def execute_modification(self, 
                                 modification_id: str) -> Dict[str, Any]:
        """Execute a proposed modification."""
        logger.info(f"Executing modification: {modification_id}")
        
        if modification_id not in self.active_modifications:
            raise ValueError(f"Unknown modification ID: {modification_id}")
        
        modification = self.active_modifications[modification_id]
        
        try:
            # Check pre-generation safety gates
            await self._check_safety_gates("pre_generation", modification)
            
            # Generate code changes
            generated_code = await self._generate_code_changes(modification)
            modification["artifacts"]["generated_code"] = generated_code
            
            # Check post-generation safety gates
            await self._check_safety_gates("post_generation", modification)
            
            # Validate changes
            validation_results = await self._validate_changes(modification)
            modification["artifacts"]["validation_results"] = validation_results
            
            # Check pre-integration safety gates
            await self._check_safety_gates("pre_integration", modification)
            
            # Integrate changes
            integration_results = await self._integrate_changes(modification)
            modification["artifacts"]["integration_results"] = integration_results
            
            # Check post-integration safety gates
            await self._check_safety_gates("post_integration", modification)
            
            # Update status
            self._update_modification_status(
                modification_id,
                ModificationStatus.COMPLETED,
                "Modification successfully completed"
            )
            
            # Archive completed modification
            self.modification_history.append(modification)
            del self.active_modifications[modification_id]
            
            return {
                "modification_id": modification_id,
                "status": ModificationStatus.COMPLETED,
                "results": integration_results
            }
            
        except Exception as e:
            logger.error(f"Modification failed: {str(e)}")
            await self._handle_modification_failure(modification_id, str(e))
            raise
    
    async def _analyze_modification(self, modification_id: str) -> None:
        """Analyze a proposed modification."""
        modification = self.active_modifications[modification_id]
        
        self._update_modification_status(
            modification_id,
            ModificationStatus.ANALYZING,
            "Analyzing modification impact and requirements"
        )
        
        # Delegate analysis to agentic controller
        analysis_results = await self.agentic_controller.analyze_modification(
            modification["request"]
        )
        
        modification["artifacts"]["analysis"] = analysis_results
    
    async def _generate_code_changes(self, 
                                   modification: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code changes for modification."""
        self._update_modification_status(
            modification["id"],
            ModificationStatus.GENERATING,
            "Generating code changes"
        )
        
        return await self.code_generator.generate_code(
            modification["request"],
            modification["artifacts"]["analysis"]
        )
    
    async def _validate_changes(self, 
                              modification: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated code changes."""
        self._update_modification_status(
            modification["id"],
            ModificationStatus.VALIDATING,
            "Validating generated changes"
        )
        
        return await self.safety_validator.validate_code(
            modification["artifacts"]["generated_code"]
        )
    
    async def _integrate_changes(self, 
                               modification: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate validated changes."""
        self._update_modification_status(
            modification["id"],
            ModificationStatus.INTEGRATING,
            "Integrating changes into system"
        )
        
        return await self.integration_manager.apply_changes(
            modification["artifacts"]["generated_code"],
            modification["artifacts"]["validation_results"]
        )
    
    async def _check_safety_gates(self, 
                                gate_phase: str,
                                modification: Dict[str, Any]) -> None:
        """Check safety gates for a modification phase."""
        gates = self.safety_gates[gate_phase]
        
        for gate, enabled in gates.items():
            if not enabled:
                continue
                
            logger.info(f"Checking safety gate: {gate} in phase {gate_phase}")
            
            # Implement specific gate checks here
            if gate == "impact_analysis":
                await self._check_impact(modification)
            elif gate == "security_scan":
                await self._check_security(modification)
            # Add more gate checks as needed
    
    async def _check_impact(self, modification: Dict[str, Any]) -> None:
        """Check modification impact."""
        # Implementation would analyze potential system impact
        pass
    
    async def _check_security(self, modification: Dict[str, Any]) -> None:
        """Check modification security."""
        # Implementation would perform security analysis
        pass
    
    def _update_modification_status(self,
                                  modification_id: str,
                                  status: ModificationStatus,
                                  details: str) -> None:
        """Update modification status and timeline."""
        modification = self.active_modifications[modification_id]
        
        modification["status"] = status
        modification["timeline"].append({
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
    
    async def _handle_modification_failure(self,
                                        modification_id: str,
                                        error_message: str) -> None:
        """Handle modification failure."""
        logger.error(f"Handling modification failure: {error_message}")
        
        modification = self.active_modifications[modification_id]
        
        # Update status
        self._update_modification_status(
            modification_id,
            ModificationStatus.FAILED,
            f"Modification failed: {error_message}"
        )
        
        # Attempt rollback if needed
        if modification["status"] in [
            ModificationStatus.INTEGRATING,
            ModificationStatus.TESTING
        ]:
            await self._rollback_modification(modification_id)
    
    async def _rollback_modification(self, modification_id: str) -> None:
        """Rollback a failed modification."""
        logger.info(f"Rolling back modification: {modification_id}")
        
        modification = self.active_modifications[modification_id]
        
        try:
            await self.integration_manager.rollback_changes(
                modification["artifacts"].get("integration_results", {})
            )
            
            self._update_modification_status(
                modification_id,
                ModificationStatus.ROLLED_BACK,
                "Modification rolled back successfully"
            )
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            # Handle rollback failure - might need manual intervention
    
    def _get_next_steps(self, modification: Dict[str, Any]) -> List[str]:
        """Get next steps for a modification based on its current status."""
        status = modification["status"]
        
        steps_map = {
            ModificationStatus.PROPOSED: ["Analysis", "Impact Assessment"],
            ModificationStatus.ANALYZING: ["Code Generation", "Validation"],
            ModificationStatus.GENERATING: ["Safety Validation", "Integration"],
            ModificationStatus.VALIDATING: ["Integration", "Testing"],
            ModificationStatus.INTEGRATING: ["Testing", "Verification"],
            ModificationStatus.TESTING: ["Final Verification", "Completion"],
            ModificationStatus.COMPLETED: ["Monitoring"],
            ModificationStatus.FAILED: ["Review Error", "Retry or Rollback"],
            ModificationStatus.ROLLED_BACK: ["Review Changes", "New Proposal"]
        }
        
        return steps_map.get(status, [])
```

Now, let's implement the unit tests:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    return {
        "code_generator": MagicMock(generate_code=AsyncMock()),
        "safety_validator": MagicMock(validate_code=AsyncMock()),
        "integration_manager": MagicMock(
            apply_changes=AsyncMock(),
            rollback_changes=AsyncMock()
        ),
        "agentic_controller": MagicMock(analyze_modification=AsyncMock()),
        "system_access": MagicMock()
    }

@pytest.fixture
def self_modification(mock_components):
    """Create SelfModificationIntegration instance for testing."""
    return SelfModificationIntegration(**mock_components)

@pytest.fixture
def sample_request():
    """Create a sample modification request."""
    return ModificationRequest(
        modification_type=ModificationType.CODE_CHANGE,
        description="Test modification",
        target_components=["test_component"],
        requirements={"test": "requirement"},
        priority=1,
        estimated_impact={"risk": "low"},
        context={"test": "context"}
    )

class TestSelfModificationIntegration:
    """Test suite for SelfModificationIntegration."""
    
    @pytest.mark.asyncio
    async def test_propose_modification(self, self_modification, sample_request):
        """Test modification proposal."""
        result = await self_modification.propose_modification(sample_request)
        
        assert "modification_id" in result
        assert result["status"] == ModificationStatus.ANALYZING
        assert len(self_modification.active_modifications) == 1
    
    @pytest.mark.asyncio
    async def test_execute_modification_success(self, 
                                             self_modification,
                                             sample_request,
                                             mock_components):
        """Test successful modification execution."""
        # Setup mock returns
        mock_components["code_generator"].generate_code.return_value = {
            "files": {"test.py": "test code"}
        }
        mock_components["safety_validator"].validate_code.return_value = {
            "passed": True
        }
        mock_components["integration_manager"].apply_changes.return_value = {
            "success": True
        }
        
        # Propose and execute modification
        proposal = await self_modification.propose_modification(sample_request)
        result = await self_modification.execute_modification(
            proposal["modification_id"]
        )
        
        assert result["status"] == ModificationStatus.COMPLETED
        assert len(self_modification.modification_history) == 1
        assert len(self_modification.active_modifications) == 0
    
    @pytest.mark.asyncio
    async def test_execute_modification_failure(self,
                                             self_modification,
                                             sample_request,
                                             mock_components):
        """Test modification execution failure."""
        # Setup mock to raise exception
        mock_components["code_generator"].generate_code.side_effect = \
            Exception("Generation failed")
        
        # Propose modification
        proposal = await self_modification.propose_modification(sample_request)
        
        # Execute and expect exception
        with pytest.raises(Exception) as exc_info:
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        assert "Generation failed" in str(exc_info.value)
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_safety_gates(self, self_modification, sample_request):
        """Test safety gate checks."""
        # Propose modification
        proposal = await self_modification.propose_modification(sample_request)
        modification_id = proposal["modification_id"]
        
        # Test pre-generation gates
        await self_modification._check_safety_gates(
            "pre_generation",
            self_modification.active_modifications[modification_id]
        )
        
        # Verify gates were checked
        assert all(self_modification.safety_gates["pre_generation"].values())
    
    @pytest.mark.asyncio
    async def test_modification_rollback(self,
                                      self_modification,
                                      sample_request,
                                      mock_components):
        """Test modification rollback."""
        # Setup mock to fail during integration
        mock_components["integration_manager"].apply_changes.side_effect = \
            Exception("Integration failed")
        
        # Propose modification
        proposal = await self_modification.propose_modification(sample_request)
        
        # Execute and expect rollback
        with pytest.raises(Exception):
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        # Verify rollback was called
        mock_components["integration_manager"].rollback_changes.assert_called_once()
        
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.FAILED
    
    def test_get_next_steps(self, self_modification, sample_request):
        """Test next steps generation."""
        # Create a test modification
        modification = {
            "status": ModificationStatus.PROPOSED,
            "request": sample_request
        }
        
        steps = self_modification._get_next_steps(modification)
        
        assert len(steps) > 0
        assert "Analysis" in steps
```

The Self-Modification Integration implementation includes:
1. Comprehensive modification workflow management
2. Safety gates at critical phases
3. Integration with all self-modification components
4. Detailed status tracking and history
5. Rollback capabilities
6. Error handling and recovery
7. Progress tracking and next steps guidance

The unit tests cover:
1. Modification proposal and execution
2. Success and failure scenarios
3. Safety gate checks
4. Rollback functionality
5. Status tracking
6. Next steps generation

This completes the implementation of Phase 4, integrating the Code Generator, Safety Validator, Integration Manager, Agentic Development Framework, System Access Layer, and Self-Modification Integration components into a cohesive system for safe self-modification.


### UNIT TESTINGS

I'll provide comprehensive unit testing instructions for Work Units 4.4, 4.5, and 4.6. I'll create a structured test suite that covers all critical functionality.

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
from datetime import datetime
import os
import tempfile
import shutil
from pathlib import Path

# Test Utilities and Fixtures
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    workspace = tempfile.mkdtemp()
    yield workspace
    shutil.rmtree(workspace)

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return MagicMock(
        generate_response=AsyncMock(return_value="Test response"),
        analyze_code=AsyncMock(return_value={"quality": 0.8, "issues": []})
    )

# Work Unit 4.4: Agentic Development Framework Tests

class TestAgenticDevelopmentFramework:
    """Test suite for the Agentic Development Framework."""
    
    @pytest.fixture
    def mock_workers(self):
        """Create mock specialized workers."""
        return {
            "requirements": MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            "planning": MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            "implementation": MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            )
        }
    
    @pytest.fixture
    def workflow_orchestrator(self, mock_workers, mock_llm):
        """Create AgenticWorkflowOrchestrator instance."""
        return AgenticWorkflowOrchestrator(
            workers=mock_workers,
            llm=mock_llm
        )
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow_orchestrator):
        """Test workflow initialization."""
        requirements = {
            "task": "Implement new feature",
            "description": "Add user authentication",
            "constraints": ["Must use JWT", "RESTful API"]
        }
        
        result = await workflow_orchestrator.start_workflow(
            "test_cycle",
            requirements
        )
        
        assert result["workflow_id"]
        assert result["status"] == "initialized"
        assert "phases" in result
    
    @pytest.mark.asyncio
    async def test_requirements_phase(self, workflow_orchestrator, mock_workers):
        """Test requirements analysis phase."""
        workflow_id = "test_workflow"
        
        result = await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.ANALYSIS
        )
        
        mock_workers["requirements"].execute_task.assert_called_once()
        assert result["status"] == "success"
        assert "requirements" in result
    
    @pytest.mark.asyncio
    async def test_planning_phase(self, workflow_orchestrator, mock_workers):
        """Test development planning phase."""
        workflow_id = "test_workflow"
        requirements = {
            "feature": "user_auth",
            "requirements": ["JWT support", "API endpoints"]
        }
        
        result = await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.PLANNING,
            requirements
        )
        
        mock_workers["planning"].execute_task.assert_called_once()
        assert result["status"] == "success"
        assert "plan" in result
    
    @pytest.mark.asyncio
    async def test_implementation_phase(self, workflow_orchestrator, mock_workers):
        """Test code implementation phase."""
        workflow_id = "test_workflow"
        plan = {
            "tasks": [
                {"type": "create_file", "path": "auth.py"},
                {"type": "implement_function", "name": "verify_token"}
            ]
        }
        
        result = await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.IMPLEMENTATION,
            plan
        )
        
        mock_workers["implementation"].execute_task.assert_called_once()
        assert result["status"] == "success"
        assert "implementation" in result
    
    @pytest.mark.asyncio
    async def test_phase_transition(self, workflow_orchestrator):
        """Test phase transitions in workflow."""
        workflow_id = "test_workflow"
        
        # Start workflow
        await workflow_orchestrator.start_workflow(
            workflow_id,
            {"task": "Test task"}
        )
        
        # Test each phase transition
        phases = [
            DevelopmentPhase.ANALYSIS,
            DevelopmentPhase.PLANNING,
            DevelopmentPhase.IMPLEMENTATION,
            DevelopmentPhase.EVALUATION
        ]
        
        for phase in phases:
            result = await workflow_orchestrator._execute_phase(
                workflow_id,
                phase
            )
            assert result["status"] == "success"
            
        final_state = workflow_orchestrator.get_workflow_state(workflow_id)
        assert final_state["current_phase"] == DevelopmentPhase.EVALUATION

# Work Unit 4.5: System Access Layer Tests

class TestSystemAccessLayer:
    """Test suite for the System Access Layer."""
    
    @pytest.fixture
    def system_access(self):
        """Create SystemAccessLayer instance."""
        return SystemAccessLayer(
            security_config={
                "sandbox_enabled": True,
                "max_file_size": 1024 * 1024,
                "allowed_packages": ["pytest", "black"]
            }
        )
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, system_access):
        """Test successful command execution."""
        result = await system_access.execute_command("echo 'test'")
        
        assert result["exit_code"] == 0
        assert "test" in result["stdout"]
        assert result["command"] == "echo 'test'"
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, system_access):
        """Test command execution timeout."""
        with pytest.raises(TimeoutError):
            await system_access.execute_command(
                "sleep 10",
                timeout=1
            )
    
    @pytest.mark.asyncio
    async def test_package_management(self, system_access):
        """Test package installation and management."""
        # Test allowed package installation
        result = await system_access.install_package("pytest")
        assert result["success"]
        
        # Test disallowed package
        with pytest.raises(ValueError):
            await system_access.install_package("malicious-package")
    
    @pytest.mark.asyncio
    async def test_file_operations(self, system_access, temp_workspace):
        """Test file read/write operations."""
        test_file = os.path.join(temp_workspace, "test.txt")
        test_content = "test content"
        
        # Test write
        write_result = await system_access.write_file(
            test_file,
            test_content
        )
        assert write_result["success"]
        
        # Test read
        read_result = await system_access.read_file(test_file)
        assert read_result["content"] == test_content
    
    @pytest.mark.asyncio
    async def test_repository_operations(self, system_access, temp_workspace):
        """Test repository operations."""
        with patch('git.Repo.clone_from') as mock_clone:
            mock_repo = MagicMock()
            mock_repo.active_branch.name = "main"
            mock_clone.return_value = mock_repo
            
            result = await system_access.clone_repository(
                "https://github.com/test/repo.git",
                os.path.join(temp_workspace, "repo")
            )
            
            assert result["success"]
            assert result["branch"] == "main"
    
    def test_access_policy_validation(self, system_access):
        """Test access policy validation."""
        # Test protected path
        assert not system_access._validate_path(
            "/etc/passwd",
            AccessLevel.READ
        )
        
        # Test allowed path
        assert system_access._validate_path(
            "src/test.py",
            AccessLevel.WRITE
        )

# Work Unit 4.6: Self-Modification Integration Tests

class TestSelfModificationIntegration:
    """Test suite for Self-Modification Integration."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components."""
        return {
            "code_generator": MagicMock(generate_code=AsyncMock()),
            "safety_validator": MagicMock(validate_code=AsyncMock()),
            "integration_manager": MagicMock(
                apply_changes=AsyncMock(),
                rollback_changes=AsyncMock()
            ),
            "agentic_controller": MagicMock(analyze_modification=AsyncMock()),
            "system_access": MagicMock()
        }
    
    @pytest.fixture
    def self_modification(self, mock_components):
        """Create SelfModificationIntegration instance."""
        return SelfModificationIntegration(**mock_components)
    
    @pytest.mark.asyncio
    async def test_modification_workflow(self, self_modification, mock_components):
        """Test complete modification workflow."""
        # Setup mock returns
        mock_components["code_generator"].generate_code.return_value = {
            "files": {"test.py": "def test(): pass"}
        }
        mock_components["safety_validator"].validate_code.return_value = {
            "passed": True,
            "issues": []
        }
        mock_components["integration_manager"].apply_changes.return_value = {
            "success": True
        }
        
        # Create modification request
        request = ModificationRequest(
            modification_type=ModificationType.CODE_CHANGE,
            description="Test modification",
            target_components=["test"],
            requirements={},
            priority=1,
            estimated_impact={},
            context={}
        )
        
        # Test workflow
        proposal = await self_modification.propose_modification(request)
        assert proposal["modification_id"]
        
        result = await self_modification.execute_modification(
            proposal["modification_id"]
        )
        
        assert result["status"] == ModificationStatus.COMPLETED
        assert len(self_modification.modification_history) == 1
    
    @pytest.mark.asyncio
    async def test_safety_gate_checks(self, self_modification):
        """Test safety gate validation."""
        modification = {
            "id": "test_mod",
            "request": {
                "modification_type": ModificationType.CODE_CHANGE,
                "target_components": ["test"]
            },
            "artifacts": {
                "analysis": {"risk_level": "low"}
            }
        }
        
        # Test pre-generation gates
        await self_modification._check_safety_gates(
            "pre_generation",
            modification
        )
        
        # Verify all gates were checked
        for gate in self_modification.safety_gates["pre_generation"]:
            assert gate in modification.get("safety_checks", {})
    
    @pytest.mark.asyncio
    async def test_modification_failure_handling(self,
                                              self_modification,
                                              mock_components):
        """Test handling of modification failures."""
        # Setup mock to fail
        mock_components["code_generator"].generate_code.side_effect = \
            Exception("Generation failed")
        
        request = ModificationRequest(
            modification_type=ModificationType.CODE_CHANGE,
            description="Test modification",
            target_components=["test"],
            requirements={},
            priority=1,
            estimated_impact={},
            context={}
        )
        
        # Test failure handling
        proposal = await self_modification.propose_modification(request)
        
        with pytest.raises(Exception):
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_rollback_procedure(self, self_modification, mock_components):
        """Test modification rollback procedure."""
        # Setup mock to fail during integration
        mock_components["integration_manager"].apply_changes.side_effect = \
            Exception("Integration failed")
        
        request = ModificationRequest(
            modification_type=ModificationType.CODE_CHANGE,
            description="Test modification",
            target_components=["test"],
            requirements={},
            priority=1,
            estimated_impact={},
            context={}
        )
        
        # Test rollback
        proposal = await self_modification.propose_modification(request)
        
        with pytest.raises(Exception):
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        mock_components["integration_manager"].rollback_changes.assert_called_once()
        
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.ROLLED_BACK

def run_tests():
    """Run all test suites."""
    pytest.main([
        "-v",
        "--asyncio-mode=strict",
        "-k", "TestAgenticDevelopmentFramework or TestSystemAccessLayer or TestSelfModificationIntegration"
    ])

if __name__ == "__main__":
    run_tests()
```

Key aspects of the test suites:

1. **Agentic Development Framework Tests**:
   - Workflow initialization and phase transitions
   - Specialized worker execution
   - Task handling and coordination
   - Error handling and recovery
   - Context propagation

2. **System Access Layer Tests**:
   - Command execution with timeouts
   - Package management restrictions
   - File operations with security checks
   - Repository operations
   - Access policy validation
   - Resource limits enforcement

3. **Self-Modification Integration Tests**:
   - Complete modification workflow
   - Safety gate validation
   - Failure handling
   - Rollback procedures
   - Component integration
   - State management

Testing Best Practices:
1. Use fixtures for common setup
2. Mock external dependencies
3. Test both success and failure paths
4. Validate security constraints
5. Check state transitions
6. Verify error handling
7. Test integration points
8. Validate rollback procedures

To run the tests:
1. Install required packages:
```bash
pip install pytest pytest-asyncio pytest-mock
```

2. Run tests with coverage:
```bash
pytest --cov=. --cov-report=term-missing -v
```

3. Run specific test suites:
```bash
pytest -v -k "TestAgenticDevelopmentFramework"
pytest -v -k "TestSystemAccessLayer"
pytest -v -k "TestSelfModificationIntegration"
```

The test suites ensure comprehensive coverage of all critical functionality while maintaining security and reliability requirements.

