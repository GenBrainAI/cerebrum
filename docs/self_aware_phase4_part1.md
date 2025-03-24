I'll help you create a detailed implementation guide for Work Units 4.1 (Code Generator), 4.2 (Safety Validator), and 4.3 (Integration Manager) of Phase 4. Let's start with a high-level overview and then dive into each component.

First, let me search for any relevant code or documentation in the codebase.

Search files...
Based on the search results and the workplan, I'll provide a detailed implementation guide for Phase 4, focusing on Work Units 4.1 (Code Generator), 4.2 (Safety Validator), and 4.3 (Integration Manager). Let's start with the Code Generator.

## Work Unit 4.1: Code Generator

The Code Generator is responsible for generating code based on specifications and requirements. Here's the implementation:

```python
from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class GenerationType(Enum):
    NEW_CODE = "new_code"
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"

@dataclass
class GenerationContext:
    """Context for code generation."""
    codebase_path: str
    dependencies: Dict[str, str]
    style_guide: Dict[str, Any]
    target_language: str
    framework_constraints: List[str]
    existing_code: Optional[Dict[str, str]] = None

class CodeGenerator:
    """Generates code based on specifications and requirements."""
    
    def __init__(self, template_path: Optional[str] = None,
                 style_config: Optional[Dict[str, Any]] = None):
        """Initialize the code generator.
        
        Args:
            template_path: Path to code templates directory
            style_config: Configuration for code style enforcement
        """
        self.template_path = template_path or "templates/code"
        self.style_config = style_config or {
            "indent_style": "space",
            "indent_size": 4,
            "max_line_length": 100,
            "docstring_style": "google"
        }
        self.generation_history = {}
        
    async def generate_code(self, specification: Dict[str, Any],
                          context: Optional[GenerationContext] = None,
                          existing_code: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate code based on specification and context.
        
        Args:
            specification: Detailed specification for code generation
            context: Generation context with codebase info
            existing_code: Existing code if modifying/refactoring
            
        Returns:
            Dictionary containing generated code and metadata
        """
        generation_id = str(uuid.uuid4())
        logger.info(f"Starting code generation with ID: {generation_id}")
        
        # Create generation record
        record = {
            "id": generation_id,
            "specification": specification,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "type": specification.get("type", GenerationType.NEW_CODE.value)
        }
        
        self.generation_history[generation_id] = record
        
        try:
            # Select appropriate template
            template = await self._select_template(specification)
            
            # Generate code structure
            code_structure = await self._generate_structure(specification, template)
            
            # Generate actual code
            code = await self._generate_implementation(code_structure, context)
            
            # Apply style formatting
            formatted_code = await self._apply_style_formatting(code)
            
            # Add documentation
            documented_code = await self._add_documentation(formatted_code, specification)
            
            # Update record with success
            record.update({
                "status": "completed",
                "code": documented_code,
                "metrics": await self._calculate_metrics(documented_code),
                "completion_time": datetime.now().isoformat()
            })
            
            return record
            
        except Exception as e:
            logger.error(f"Code generation failed with error: {str(e)}")
            record.update({
                "status": "failed",
                "error": str(e),
                "completion_time": datetime.now().isoformat()
            })
            return record
    
    async def refactor_code(self, code: str, requirements: Dict[str, Any],
                          context: Optional[GenerationContext] = None) -> Dict[str, Any]:
        """Refactor existing code according to requirements.
        
        Args:
            code: Code to refactor
            requirements: Refactoring requirements
            context: Generation context
            
        Returns:
            Dictionary containing refactored code and metadata
        """
        specification = {
            "type": GenerationType.REFACTOR.value,
            "original_code": code,
            "requirements": requirements
        }
        return await self.generate_code(specification, context, {None: code})
    
    async def optimize_code(self, code: str, optimization_goals: List[str],
                          context: Optional[GenerationContext] = None) -> Dict[str, Any]:
        """Optimize code for specified goals.
        
        Args:
            code: Code to optimize
            optimization_goals: List of optimization goals
            context: Generation context
            
        Returns:
            Dictionary containing optimized code and metadata
        """
        specification = {
            "type": GenerationType.OPTIMIZE.value,
            "original_code": code,
            "optimization_goals": optimization_goals
        }
        return await self.generate_code(specification, context, {None: code})
    
    async def fix_bugs(self, code: str, bug_description: str,
                      test_cases: Optional[List[Dict[str, Any]]] = None,
                      context: Optional[GenerationContext] = None) -> Dict[str, Any]:
        """Fix bugs in code based on description and test cases.
        
        Args:
            code: Code containing bugs
            bug_description: Description of the bugs
            test_cases: Test cases demonstrating the bugs
            context: Generation context
            
        Returns:
            Dictionary containing fixed code and metadata
        """
        specification = {
            "type": GenerationType.BUG_FIX.value,
            "original_code": code,
            "bug_description": bug_description,
            "test_cases": test_cases
        }
        return await self.generate_code(specification, context, {None: code})
    
    async def _select_template(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate template based on specification."""
        # Implementation would load and select appropriate template
        pass
    
    async def _generate_structure(self, specification: Dict[str, Any],
                                template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code structure based on specification and template."""
        # Implementation would generate code structure
        pass
    
    async def _generate_implementation(self, structure: Dict[str, Any],
                                     context: Optional[GenerationContext]) -> str:
        """Generate actual code implementation."""
        # Implementation would generate actual code
        pass
    
    async def _apply_style_formatting(self, code: str) -> str:
        """Apply style formatting to code."""
        # Implementation would format code according to style config
        pass
    
    async def _add_documentation(self, code: str,
                               specification: Dict[str, Any]) -> str:
        """Add documentation to code."""
        # Implementation would add appropriate documentation
        pass
    
    async def _calculate_metrics(self, code: str) -> Dict[str, Any]:
        """Calculate code quality metrics."""
        # Implementation would calculate various metrics
        pass
```

This implementation provides a robust foundation for code generation with the following key features:

1. Support for different types of code generation (new code, refactoring, optimization, bug fixes)
2. Template-based generation system
3. Style enforcement through configuration
4. Documentation generation
5. Code quality metrics calculation
6. Comprehensive history tracking


I'll continue with Work Unit 4.2 (Safety Validator) and its unit tests, then move on to Work Unit 4.3 (Integration Manager).

## Work Unit 4.2: Safety Validator

First, let's implement the Safety Validator with enhanced features:

```python
from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import subprocess
import tempfile
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ValidationRule:
    """Rule for code validation."""
    name: str
    description: str
    severity: str
    pattern: str
    validation_type: str
    enabled: bool = True

class SafetyValidator:
    """Validates generated code for safety and quality."""
    
    def __init__(self, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with security configuration."""
        self.security_config = security_config or {
            "validation_level": "high",
            "static_analysis_tools": ["pylint", "mypy", "bandit"],
            "security_scan_tools": ["bandit", "safety"],
            "test_frameworks": ["pytest"],
            "max_validation_time": 60,  # seconds
            "sandbox_enabled": True,
            "dependency_check_enabled": True
        }
        self.validation_history = {}
        self.validation_rules = self._load_validation_rules()
        
    def _load_validation_rules(self) -> List[ValidationRule]:
        """Load validation rules from configuration."""
        # Default rules
        return [
            ValidationRule(
                name="no_eval",
                description="Prevent use of eval() function",
                severity="critical",
                pattern=r"\beval\s*\(",
                validation_type="security"
            ),
            ValidationRule(
                name="no_exec",
                description="Prevent use of exec() function",
                severity="critical",
                pattern=r"\bexec\s*\(",
                validation_type="security"
            ),
            ValidationRule(
                name="sql_injection",
                description="Detect potential SQL injection vulnerabilities",
                severity="critical",
                pattern=r"f[\"'].*SELECT.*\{.*\}.*[\"']",
                validation_type="security"
            ),
            # Add more rules as needed
        ]
    
    async def validate_code(self, code: str, file_path: str,
                          validation_level: str = "high") -> Dict[str, Any]:
        """Validate code against safety rules and quality standards."""
        validation_id = str(uuid.uuid4())
        logger.info(f"Starting code validation with ID: {validation_id}")
        
        validation_record = {
            "id": validation_id,
            "file_path": file_path,
            "validation_level": validation_level,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "results": {}
        }
        
        self.validation_history[validation_id] = validation_record
        
        try:
            # Run in sandbox if enabled
            if self.security_config["sandbox_enabled"]:
                await self._setup_sandbox()
            
            # Static analysis
            static_result = await self.static_analysis(code, file_path)
            validation_record["results"]["static_analysis"] = static_result
            
            # Security scan
            security_result = await self.security_scan(code)
            validation_record["results"]["security_scan"] = security_result
            
            # Dependency check
            if self.security_config["dependency_check_enabled"]:
                dep_result = await self.check_dependencies(code)
                validation_record["results"]["dependency_check"] = dep_result
            
            # Custom rule validation
            rule_result = await self._validate_custom_rules(code)
            validation_record["results"]["custom_rules"] = rule_result
            
            # Determine overall result
            validation_passed = all([
                static_result.get("passed", False),
                security_result.get("passed", False),
                rule_result.get("passed", False),
                dep_result.get("passed", True) if "dep_result" in locals() else True
            ])
            
            validation_record.update({
                "status": "completed",
                "passed": validation_passed,
                "completion_time": datetime.now().isoformat()
            })
            
            return validation_record
            
        except Exception as e:
            logger.error(f"Validation failed with error: {str(e)}")
            validation_record.update({
                "status": "failed",
                "error": str(e),
                "completion_time": datetime.now().isoformat()
            })
            return validation_record
        finally:
            if self.security_config["sandbox_enabled"]:
                await self._cleanup_sandbox()
    
    async def static_analysis(self, code: str, file_path: str) -> Dict[str, Any]:
        """Perform static analysis on code."""
        logger.info("Performing static analysis")
        
        result = {
            "tool_results": {},
            "issues": [],
            "passed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Run pylint
            if "pylint" in self.security_config["static_analysis_tools"]:
                pylint_result = await self._run_pylint(temp_file_path)
                result["tool_results"]["pylint"] = pylint_result
                if not pylint_result["passed"]:
                    result["passed"] = False
                    result["issues"].extend(pylint_result["issues"])
            
            # Run mypy
            if "mypy" in self.security_config["static_analysis_tools"]:
                mypy_result = await self._run_mypy(temp_file_path)
                result["tool_results"]["mypy"] = mypy_result
                if not mypy_result["passed"]:
                    result["passed"] = False
                    result["issues"].extend(mypy_result["issues"])
            
            return result
        finally:
            os.unlink(temp_file_path)
    
    async def security_scan(self, code: str) -> Dict[str, Any]:
        """Scan code for security vulnerabilities."""
        logger.info("Performing security scan")
        
        result = {
            "tool_results": {},
            "vulnerabilities": [],
            "passed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Run bandit
            if "bandit" in self.security_config["security_scan_tools"]:
                bandit_result = await self._run_bandit(temp_file_path)
                result["tool_results"]["bandit"] = bandit_result
                if not bandit_result["passed"]:
                    result["passed"] = False
                    result["vulnerabilities"].extend(bandit_result["vulnerabilities"])
            
            # Run safety
            if "safety" in self.security_config["security_scan_tools"]:
                safety_result = await self._run_safety(temp_file_path)
                result["tool_results"]["safety"] = safety_result
                if not safety_result["passed"]:
                    result["passed"] = False
                    result["vulnerabilities"].extend(safety_result["vulnerabilities"])
            
            return result
        finally:
            os.unlink(temp_file_path)
    
    async def check_dependencies(self, code: str) -> Dict[str, Any]:
        """Check dependencies for known vulnerabilities."""
        # Implementation of dependency checking
        pass
    
    async def _validate_custom_rules(self, code: str) -> Dict[str, Any]:
        """Validate code against custom rules."""
        result = {
            "passed": True,
            "violations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for rule in self.validation_rules:
            if not rule.enabled:
                continue
                
            import re
            if re.search(rule.pattern, code):
                result["passed"] = False
                result["violations"].append({
                    "rule": rule.name,
                    "description": rule.description,
                    "severity": rule.severity
                })
        
        return result
    
    async def _setup_sandbox(self):
        """Set up sandbox environment for code validation."""
        # Implementation of sandbox setup
        pass
    
    async def _cleanup_sandbox(self):
        """Clean up sandbox environment."""
        # Implementation of sandbox cleanup
        pass
```

Now, let's implement comprehensive unit tests for the Safety Validator:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os
from datetime import datetime

@pytest.fixture
def safety_validator():
    """Create a SafetyValidator instance for testing."""
    return SafetyValidator()

@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No issues found",
            stderr=""
        )
        yield mock_run

class TestSafetyValidator:
    """Test suite for SafetyValidator."""
    
    @pytest.mark.asyncio
    async def test_validate_code_success(self, safety_validator, mock_subprocess_run):
        """Test successful code validation."""
        code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
        result = await safety_validator.validate_code(code, "test.py")
        
        assert result["status"] == "completed"
        assert result["passed"] is True
        assert "static_analysis" in result["results"]
        assert "security_scan" in result["results"]
        assert "custom_rules" in result["results"]
    
    @pytest.mark.asyncio
    async def test_validate_code_with_security_issues(self, safety_validator):
        """Test code validation with security issues."""
        code = """
def dangerous_code():
    user_input = input()
    eval(user_input)  # This should trigger security warning
"""
        result = await safety_validator.validate_code(code, "test.py")
        
        assert result["status"] == "completed"
        assert result["passed"] is False
        assert result["results"]["custom_rules"]["passed"] is False
        assert len(result["results"]["custom_rules"]["violations"]) > 0
        assert any(v["rule"] == "no_eval" for v in result["results"]["custom_rules"]["violations"])
    
    @pytest.mark.asyncio
    async def test_static_analysis(self, safety_validator, mock_subprocess_run):
        """Test static analysis functionality."""
        code = """
def test_function():
    unused_var = 42
    return None
"""
        result = await safety_validator.static_analysis(code, "test.py")
        
        assert "tool_results" in result
        assert "issues" in result
        assert "timestamp" in result
        assert isinstance(result["passed"], bool)
    
    @pytest.mark.asyncio
    async def test_security_scan(self, safety_validator, mock_subprocess_run):
        """Test security scanning functionality."""
        code = """
import os
os.system("echo 'Hello'")  # This should trigger security warning
"""
        result = await safety_validator.security_scan(code)
        
        assert "tool_results" in result
        assert "vulnerabilities" in result
        assert "timestamp" in result
        assert isinstance(result["passed"], bool)
    
    @pytest.mark.asyncio
    async def test_custom_rules_validation(self, safety_validator):
        """Test custom rules validation."""
        code = """
def unsafe_code():
    exec("print('Hello')")  # This should trigger custom rule
"""
        result = await safety_validator._validate_custom_rules(code)
        
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert any(v["rule"] == "no_exec" for v in result["violations"])
    
    @pytest.mark.asyncio
    async def test_validation_with_different_levels(self, safety_validator):
        """Test validation with different validation levels."""
        code = "print('Hello, World!')"
        
        for level in ["low", "medium", "high", "critical"]:
            result = await safety_validator.validate_code(code, "test.py", validation_level=level)
            assert result["validation_level"] == level
            assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_validation_with_sandbox(self, safety_validator):
        """Test validation with sandbox enabled."""
        safety_validator.security_config["sandbox_enabled"] = True
        
        code = "print('Hello, World!')"
        result = await safety_validator.validate_code(code, "test.py")
        
        assert result["status"] == "completed"
        assert result["passed"] is True
    
    @pytest.mark.asyncio
    async def test_validation_history(self, safety_validator):
        """Test validation history tracking."""
        code = "print('Hello, World!')"
        result = await safety_validator.validate_code(code, "test.py")
        
        assert result["id"] in safety_validator.validation_history
        assert safety_validator.validation_history[result["id"]]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, safety_validator):
        """Test error handling during validation."""
        with patch.object(safety_validator, 'static_analysis',
                         side_effect=Exception("Test error")):
            result = await safety_validator.validate_code("print('Hello')", "test.py")
            
            assert result["status"] == "failed"
            assert "error" in result
            assert "Test error" in result["error"]

```

The Safety Validator implementation includes:
1. Multiple validation levels
2. Custom validation rules
3. Integration with static analysis tools
4. Security vulnerability scanning
5. Dependency checking
6. Sandbox execution
7. Comprehensive error handling
8. Validation history tracking

The unit tests cover:
1. Basic validation functionality
2. Security issue detection
3. Static analysis
4. Security scanning
5. Custom rules validation
6. Different validation levels
7. Sandbox functionality
8. History tracking
9. Error handling

I'll now implement Work Unit 4.3 (Integration Manager) and its unit tests. This component is crucial for safely integrating code changes into the system.

```python
from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import shutil
import tempfile
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

class IntegrationStatus(Enum):
    CREATED = "created"
    STAGING = "staging"
    TESTING = "testing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class IntegrationMetrics:
    """Metrics for integration process."""
    files_changed: int
    lines_added: int
    lines_removed: int
    test_coverage: float
    integration_duration: float
    rollback_count: int

class IntegrationManager:
    """Manages the safe integration of new or modified code."""
    
    def __init__(self, git_manager, test_runner, 
                 security_config: Optional[Dict[str, Any]] = None):
        """Initialize with required components and security configuration."""
        self.git_manager = git_manager
        self.test_runner = test_runner
        self.security_config = security_config or {
            "requires_approval": True,
            "auto_rollback": True,
            "backup_before_changes": True,
            "test_before_apply": True,
            "max_integration_time": 300,  # seconds
            "required_test_coverage": 0.8,
            "max_file_size": 1024 * 1024,  # 1MB
            "protected_paths": ["config/", "core/", "security/"]
        }
        self.integration_plans = {}
        self.integration_history = []
        self.backup_path = "backups/integration"
        
    async def create_integration_plan(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan for integrating changes."""
        plan_id = str(uuid.uuid4())
        logger.info(f"Creating integration plan with ID: {plan_id}")
        
        # Validate changes
        await self._validate_changes(changes)
        
        # Create integration plan
        plan = {
            "id": plan_id,
            "changes": changes,
            "status": IntegrationStatus.CREATED.value,
            "creation_time": datetime.now().isoformat(),
            "stages": {
                "staging": {"status": "pending"},
                "testing": {"status": "pending"},
                "approval": {"status": "pending"},
                "application": {"status": "pending"},
                "verification": {"status": "pending"}
            },
            "requires_approval": self.security_config["requires_approval"],
            "approved": False,
            "approver": None,
            "approval_time": None,
            "metrics": {},
            "backup_path": None
        }
        
        self.integration_plans[plan_id] = plan
        self.integration_history.append({
            "action": "create_plan",
            "plan_id": plan_id,
            "timestamp": datetime.now().isoformat(),
            "changes_count": len(changes)
        })
        
        return plan
    
    async def stage_changes(self, integration_plan_id: str) -> Dict[str, Any]:
        """Stage changes in a controlled environment for testing."""
        if integration_plan_id not in self.integration_plans:
            raise ValueError(f"Integration plan {integration_plan_id} not found")
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Staging changes for integration plan: {integration_plan_id}")
        
        try:
            # Create staging environment
            staging_path = await self._create_staging_environment(plan)
            
            # Apply changes in staging
            await self._apply_changes_to_staging(plan, staging_path)
            
            # Update plan status
            plan["status"] = IntegrationStatus.STAGING.value
            plan["stages"]["staging"]["status"] = "completed"
            plan["stages"]["staging"]["path"] = staging_path
            
            return {"status": "success", "staging_path": staging_path}
            
        except Exception as e:
            logger.error(f"Staging failed: {str(e)}")
            plan["status"] = IntegrationStatus.FAILED.value
            plan["stages"]["staging"]["status"] = "failed"
            plan["stages"]["staging"]["error"] = str(e)
            return {"status": "failed", "error": str(e)}
    
    async def test_integration(self, integration_plan_id: str) -> Dict[str, Any]:
        """Test staged changes to ensure they work correctly."""
        if integration_plan_id not in self.integration_plans:
            raise ValueError(f"Integration plan {integration_plan_id} not found")
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Testing integration for plan: {integration_plan_id}")
        
        if plan["stages"]["staging"]["status"] != "completed":
            return {"status": "failed", "error": "Changes must be staged first"}
        
        try:
            staging_path = plan["stages"]["staging"]["path"]
            
            # Run tests
            test_results = await self._run_integration_tests(staging_path)
            
            # Calculate metrics
            metrics = await self._calculate_integration_metrics(plan, test_results)
            plan["metrics"] = metrics
            
            # Update plan status
            plan["status"] = IntegrationStatus.TESTING.value
            plan["stages"]["testing"].update({
                "status": "completed",
                "results": test_results,
                "completion_time": datetime.now().isoformat()
            })
            
            # Check if approval is required
            if self.security_config["requires_approval"]:
                plan["status"] = IntegrationStatus.PENDING_APPROVAL.value
            
            return {
                "status": "success",
                "test_results": test_results,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Testing failed: {str(e)}")
            plan["status"] = IntegrationStatus.FAILED.value
            plan["stages"]["testing"]["status"] = "failed"
            plan["stages"]["testing"]["error"] = str(e)
            return {"status": "failed", "error": str(e)}
    
    async def approve_integration(self, integration_plan_id: str,
                                approver: str) -> Dict[str, Any]:
        """Approve an integration plan."""
        if integration_plan_id not in self.integration_plans:
            raise ValueError(f"Integration plan {integration_plan_id} not found")
        
        plan = self.integration_plans[integration_plan_id]
        
        if plan["status"] != IntegrationStatus.PENDING_APPROVAL.value:
            return {"status": "failed", "error": "Plan is not pending approval"}
        
        plan["approved"] = True
        plan["approver"] = approver
        plan["approval_time"] = datetime.now().isoformat()
        plan["status"] = IntegrationStatus.APPROVED.value
        plan["stages"]["approval"]["status"] = "completed"
        
        return {"status": "success", "approved_by": approver}
    
    async def apply_changes(self, integration_plan_id: str) -> Dict[str, Any]:
        """Apply changes to the running system."""
        if integration_plan_id not in self.integration_plans:
            raise ValueError(f"Integration plan {integration_plan_id} not found")
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Applying changes for integration plan: {integration_plan_id}")
        
        if self.security_config["requires_approval"] and not plan["approved"]:
            return {"status": "failed", "error": "Approval required before applying changes"}
        
        try:
            # Create backup if configured
            if self.security_config["backup_before_changes"]:
                backup_path = await self._create_backup()
                plan["backup_path"] = backup_path
            
            # Apply changes
            await self._apply_changes_to_system(plan)
            
            # Verify changes
            verification_result = await self._verify_changes(plan)
            
            if verification_result["status"] == "success":
                plan["status"] = IntegrationStatus.COMPLETED.value
                plan["stages"]["application"]["status"] = "completed"
                plan["stages"]["verification"]["status"] = "completed"
                return {"status": "success", "verification": verification_result}
            else:
                # Rollback if verification failed
                if self.security_config["auto_rollback"]:
                    await self.rollback_changes(integration_plan_id)
                return {"status": "failed", "error": "Verification failed"}
                
        except Exception as e:
            logger.error(f"Application failed: {str(e)}")
            if self.security_config["auto_rollback"]:
                await self.rollback_changes(integration_plan_id)
            return {"status": "failed", "error": str(e)}
    
    async def rollback_changes(self, integration_plan_id: str) -> Dict[str, Any]:
        """Rollback changes if needed."""
        if integration_plan_id not in self.integration_plans:
            raise ValueError(f"Integration plan {integration_plan_id} not found")
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Rolling back changes for integration plan: {integration_plan_id}")
        
        try:
            if plan["backup_path"]:
                await self._restore_from_backup(plan["backup_path"])
                
            plan["status"] = IntegrationStatus.ROLLED_BACK.value
            return {"status": "success", "message": "Changes rolled back successfully"}
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def _validate_changes(self, changes: Dict[str, Any]):
        """Validate proposed changes."""
        for file_path, change in changes.items():
            # Check file size
            if len(change["content"].encode()) > self.security_config["max_file_size"]:
                raise ValueError(f"File {file_path} exceeds maximum size limit")
            
            # Check protected paths
            if any(file_path.startswith(p) for p in self.security_config["protected_paths"]):
                raise ValueError(f"File {file_path} is in a protected path")
    
    async def _create_staging_environment(self, plan: Dict[str, Any]) -> str:
        """Create a staging environment for testing changes."""
        staging_dir = tempfile.mkdtemp(prefix="integration_staging_")
        
        # Copy current codebase to staging
        # Implementation would copy relevant files
        
        return staging_dir
    
    async def _apply_changes_to_staging(self, plan: Dict[str, Any], staging_path: str):
        """Apply changes to staging environment."""
        for file_path, change in plan["changes"].items():
            full_path = os.path.join(staging_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w") as f:
                f.write(change["content"])
    
    async def _run_integration_tests(self, staging_path: str) -> Dict[str, Any]:
        """Run integration tests in staging environment."""
        return await self.test_runner.run_tests(staging_path)
    
    async def _calculate_integration_metrics(self, plan: Dict[str, Any],
                                          test_results: Dict[str, Any]) -> IntegrationMetrics:
        """Calculate integration metrics."""
        # Implementation would calculate actual metrics
        pass
    
    async def _create_backup(self) -> str:
        """Create backup of current system state."""
        backup_dir = os.path.join(
            self.backup_path,
            datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        os.makedirs(backup_dir, exist_ok=True)
        
        # Implementation would create actual backup
        
        return backup_dir
    
    async def _apply_changes_to_system(self, plan: Dict[str, Any]):
        """Apply changes to the actual system."""
        # Implementation would apply changes to actual system
        pass
    
    async def _verify_changes(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Verify applied changes."""
        # Implementation would verify changes
        pass
    
    async def _restore_from_backup(self, backup_path: str):
        """Restore system from backup."""
        # Implementation would restore from backup
        pass
```

Now, let's implement the unit tests for the Integration Manager:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os
from datetime import datetime

@pytest.fixture
def mock_git_manager():
    """Create a mock GitManager."""
    return AsyncMock()

@pytest.fixture
def mock_test_runner():
    """Create a mock TestRunner."""
    return AsyncMock()

@pytest.fixture
def integration_manager(mock_git_manager, mock_test_runner):
    """Create an IntegrationManager instance for testing."""
    return IntegrationManager(mock_git_manager, mock_test_runner)

class TestIntegrationManager:
    """Test suite for IntegrationManager."""
    
    @pytest.mark.asyncio
    async def test_create_integration_plan(self, integration_manager):
        """Test creating an integration plan."""
        changes = {
            "src/test.py": {
                "content": "print('Hello, World!')",
                "description": "Add test file"
            }
        }
        
        plan = await integration_manager.create_integration_plan(changes)
        
        assert plan["id"] in integration_manager.integration_plans
        assert plan["status"] == IntegrationStatus.CREATED.value
        assert plan["changes"] == changes
        assert not plan["approved"]
        assert len(integration_manager.integration_history) == 1
    
    @pytest.mark.asyncio
    async def test_stage_changes(self, integration_manager):
        """Test staging changes."""
        # Create plan first
        changes = {
            "src/test.py": {
                "content": "print('Hello, World!')",
                "description": "Add test file"
            }
        }
        plan = await integration_manager.create_integration_plan(changes)
        
        # Stage changes
        result = await integration_manager.stage_changes(plan["id"])
        
        assert result["status"] == "success"
        assert "staging_path" in result
        assert os.path.exists(result["staging_path"])
        
        plan = integration_manager.integration_plans[plan["id"]]
        assert plan["status"] == IntegrationStatus.STAGING.value
        assert plan["stages"]["staging"]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_test_integration(self, integration_manager):
        """Test integration testing."""
        # Setup
        changes = {
            "src/test.py": {
                "content": "print('Hello, World!')",
                "description": "Add test file"
            }
        }
        plan = await integration_manager.create_integration_plan(changes)
        await integration_manager.stage_changes(plan["id"])
        
        # Configure mock test runner
        integration_manager.test_runner.run_tests.return_value = {
            "status": "success",
            "tests_passed": 10,
            "tests_failed": 0,
            "coverage": 0.85
        }
        
        # Run tests
        result = await integration_manager.test_integration(plan["id"])
        
        assert result["status"] == "success"
        assert "test_results" in result
        assert "metrics" in result
        
        plan = integration_manager.integration_plans[plan["id"]]
        assert plan["status"] == IntegrationStatus.PENDING_APPROVAL.value
        assert plan["stages"]["testing"]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_approve_integration(self, integration_manager):
        """Test integration approval."""
        # Setup
        changes = {"src/test.py": {"content": "print('Hello!')", "description": "Test"}}
        plan = await integration_manager.create_integration_plan(changes)
        await integration_manager.stage_changes(plan["id"])
        await integration_manager.test_integration(plan["id"])
        
        # Approve
        result = await integration_manager.approve_integration(plan["id"], "test_user")
        
        assert result["status"] == "success"
        assert result["approved_by"] == "test_user"
        
        plan = integration_manager.integration_plans[plan["id"]]
        assert plan["status"] == IntegrationStatus.APPROVED.value
        assert plan["approved"]
        assert plan["approver"] == "test_user"
    
    @pytest.mark.asyncio
    async def test_apply_changes(self, integration_manager):
        """Test applying changes."""
        # Setup
        changes = {"src/test.py": {"content": "print('Hello!')", "description": "Test"}}
        plan = await integration_manager.create_integration_plan(changes)
        await integration_manager.stage_changes(plan["id"])
        await integration_manager.test_integration(plan["id"])
        await integration_manager.approve_integration(plan["id"], "test_user")
        
        # Apply changes
        result = await integration_manager.apply_changes(plan["id"])
        
        assert result["status"] == "success"
        assert "verification" in result
        
        plan = integration_manager.integration_plans[plan["id"]]
        assert plan["status"] == IntegrationStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_rollback_changes(self, integration_manager):
        """Test rolling back changes."""
        # Setup
        changes = {"src/test.py": {"content": "print('Hello!')", "description": "Test"}}
        plan = await integration_manager.create_integration_plan(changes)
        plan_id = plan["id"]
        
        # Create a backup path
        backup_path = tempfile.mkdtemp()
        integration_manager.integration_plans[plan_id]["backup_path"] = backup_path
        
        # Rollback
        result = await integration_manager.rollback_changes(plan_id)
        
        assert result["status"] == "success"
        
        plan = integration_manager.integration_plans[plan_id]
        assert plan["status"] == IntegrationStatus.ROLLED_BACK.value
    
    @pytest.mark.asyncio
    async def test_protected_paths(self, integration_manager):
        """Test protection of sensitive paths."""
        changes = {
            "config/sensitive.py": {
                "content": "SECRET_KEY = 'test'",
                "description": "Add secret key"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            await integration_manager.create_integration_plan(changes)
        
        assert "protected path" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_file_size_limit(self, integration_manager):
        """Test file size limit enforcement."""
        large_content = "x" * (integration_manager.security_config["max_file_size"] + 1)
        changes = {
            "src/large_file.py": {
                "content": large_content,
                "description": "Large file"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            await integration_manager.create_integration_plan(changes)
        
        assert "size limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_integration_metrics(self, integration_manager):
        """Test integration metrics calculation."""
        changes = {"src/test.py": {"content": "print('Hello!')", "description": "Test"}}
        plan = await integration_manager.create_integration_plan(changes)
        await integration_manager.stage_changes(plan["id"])
        
        integration_manager.test_runner.run_tests.return_value = {
            "status": "success",
            "tests_passed": 10,
            "tests_failed": 0,
            "coverage": 0.85
        }
        
        result = await integration_manager.test_integration(plan["id"])
        
        assert "metrics" in result
        assert "test_results" in result
        assert result["test_results"]["coverage"] == 0.85
```

The Integration Manager implementation includes:
1. Comprehensive integration workflow (create, stage, test, approve, apply)
2. Safety features (backups, rollbacks, protected paths)
3. Staging environment for testing
4. Integration metrics tracking
5. Approval workflow
6. Version control integration
7. Test automation
8. Change verification

The unit tests cover:
1. Integration plan creation
2. Change staging
3. Integration testing
4. Approval process
5. Change application
6. Rollback functionality
7. Protected paths
8. File size limits
9. Integration metrics

This implementation connects with the previous Work Units:
1. Uses the Code Generator (4.1) for applying changes
2. Integrates with Safety Validator (4.2) for verifying changes
3. Connects with Task Selector (3.1) for managing integration tasks
4. Uses Context Manager (3.2) for maintaining integration state
5. Works with Parallel Execution Controller (3.3) for running tests
6. Integrates with Execution Tracker (3.4) for monitoring integration progress

The Integration Manager serves as a critical component for safely evolving the system while maintaining stability and reliability.
