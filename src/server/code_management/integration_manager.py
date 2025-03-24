"""Integration manager component for safe code integration."""

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
    """Status of code integration."""
    PENDING = "pending"
    STAGED = "staged"
    TESTING = "testing"
    APPROVED = "approved"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class IntegrationMetrics:
    """Metrics for code integration."""
    test_coverage: float
    test_pass_rate: float
    code_churn: int
    integration_time: float
    rollback_count: int

class IntegrationManager:
    """Manages safe integration of new or modified code."""
    
    def __init__(self, git_manager: Any, test_runner: Any,
                 security_config: Optional[Dict[str, Any]] = None):
        """Initialize the integration manager.
        
        Args:
            git_manager: Git operations manager
            test_runner: Test execution manager
            security_config: Configuration for integration security
        """
        self.git_manager = git_manager
        self.test_runner = test_runner
        
        # Default security configuration
        self.security_config = {
            "require_approval": True,
            "auto_rollback": True,
            "backup_enabled": True,  # Add default for backup_enabled
            "max_file_size": 1024 * 1024,  # 1MB
            "protected_paths": ["config/", "secrets/", "credentials/"],
            "test_requirements": {
                "min_coverage": 80.0,
                "min_pass_rate": 100.0
            }
        }
        if security_config:
            self.security_config.update(security_config)
        self.integration_plans = {}
        self.integration_history = []
    
    async def create_integration_plan(self, changes: Dict[str, Any],
                                    description: str) -> Dict[str, Any]:
        """Create a new integration plan.
        
        Args:
            changes: Dictionary of file paths and their changes
            description: Description of the changes
            
        Returns:
            Dictionary containing the integration plan
        """
        plan_id = str(uuid.uuid4())
        logger.info(f"Creating integration plan with ID: {plan_id}")
        
        # Create staging directory
        staging_dir = os.path.join(tempfile.gettempdir(), f"integration_staging_{plan_id}")
        os.makedirs(staging_dir, exist_ok=True)
        
        # Validate changes
        for file_path, change in changes.items():
            # Check for protected paths
            for protected_path in self.security_config.get("protected_paths", []):
                if file_path.startswith(protected_path):
                    raise ValueError(f"Cannot modify protected path: {file_path}")
            
            # Create file in staging directory to check size
            staged_path = os.path.join(staging_dir, file_path)
            os.makedirs(os.path.dirname(staged_path), exist_ok=True)
            
            with open(staged_path, 'w') as f:
                f.write(change["content"])
            
            # Check file size
            if os.path.getsize(staged_path) > self.security_config["max_file_size"]:
                shutil.rmtree(staging_dir)
                raise ValueError(f"File {file_path} exceeds maximum size limit")
        
        # Create plan
        plan = {
            "id": plan_id,
            "description": description,
            "changes": changes,
            "status": IntegrationStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "metrics": None,
            "approver": None,
            "backup_path": None,
            "staging_dir": staging_dir
        }
        
        self.integration_plans[plan_id] = plan
        self.integration_history.append({
            "plan_id": plan_id,
            "action": "created",
            "timestamp": datetime.now().isoformat()
        })
        
        return plan
    
    async def stage_changes(self, plan_id: str) -> Dict[str, Any]:
        """Stage changes for testing.
        
        Args:
            plan_id: ID of the integration plan
            
        Returns:
            Dictionary containing staging results
        """
        plan = self.integration_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Integration plan {plan_id} not found")
        
        logger.info(f"Staging changes for plan {plan_id}")
        
        try:
            # Create staging area
            staging_dir = tempfile.mkdtemp(prefix=f"integration_{plan_id}_")
            
            # Clone repository to staging area
            await self.git_manager.clone(staging_dir)
            
            # Apply changes in staging area
            for file_path, change in plan["changes"].items():
                staged_path = os.path.join(staging_dir, file_path)
                os.makedirs(os.path.dirname(staged_path), exist_ok=True)
                with open(staged_path, 'w') as f:
                    f.write(change["content"])
            
            # Update plan status
            plan["status"] = IntegrationStatus.STAGED.value
            plan["staging_dir"] = staging_dir
            
            self.integration_history.append({
                "plan_id": plan_id,
                "action": "staged",
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "status": IntegrationStatus.STAGED.value,
                "staging_path": staging_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to stage changes for plan {plan_id}: {str(e)}")
            plan["status"] = IntegrationStatus.FAILED.value
            return {
                "status": IntegrationStatus.FAILED.value,
                "error": str(e)
            }
    
    async def test_integration(self, plan_id: str) -> Dict[str, Any]:
        """Test staged changes.
        
        Args:
            plan_id: ID of the integration plan
            
        Returns:
            Dictionary containing test results
        """
        plan = self.integration_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Integration plan {plan_id} not found")
        
        if plan["status"] != IntegrationStatus.STAGED.value:
            raise ValueError("Changes must be staged before testing")
        
        logger.info(f"Testing changes for plan {plan_id}")
        
        try:
            # Run tests in staging area
            test_results = await self.test_runner.run_tests(plan["staging_dir"])
            
            # Calculate metrics
            metrics = IntegrationMetrics(
                test_coverage=test_results.get("coverage", 0.0),
                test_pass_rate=test_results.get("pass_rate", 0.0),
                code_churn=len(plan["changes"]),
                integration_time=0.0,  # Will be updated when applied
                rollback_count=0
            )
            
            # Check if results meet requirements
            test_requirements = self.security_config.get("test_requirements", {})
            min_coverage = test_requirements.get("min_coverage", 80.0)
            min_pass_rate = test_requirements.get("min_pass_rate", 80.0)
            
            # Use requirements_met from test results if available, otherwise calculate it
            requirements_met = test_results.get("requirements_met", False) or (
                metrics.test_coverage >= min_coverage and
                metrics.test_pass_rate >= min_pass_rate
            )
            
            # Update plan status and metrics
            plan["status"] = IntegrationStatus.TESTING.value
            plan["metrics"] = metrics
            plan["test_results"] = test_results
            plan["requirements_met"] = requirements_met
            
            self.integration_history.append({
                "plan_id": plan_id,
                "action": "tested",
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics
            })
            
            if not requirements_met:
                logger.warning(f"Test requirements not met for plan {plan_id}")
            
            return {
                "status": IntegrationStatus.TESTING.value,
                "metrics": metrics,
                "test_results": test_results,
                "requirements_met": requirements_met
            }
            
        except Exception as e:
            logger.error(f"Failed to test changes for plan {plan_id}: {str(e)}")
            plan["status"] = IntegrationStatus.FAILED.value
            return {
                "status": IntegrationStatus.FAILED.value,
                "error": str(e)
            }
    
    async def approve_integration(self, plan_id: str, approver: str) -> Dict[str, Any]:
        """Approve integration plan.
        
        Args:
            plan_id: ID of the integration plan
            approver: Name or ID of the approver
            
        Returns:
            Dictionary containing approval status
        """
        plan = self.integration_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Integration plan {plan_id} not found")
        
        if plan["status"] not in [IntegrationStatus.TESTING.value, IntegrationStatus.STAGED.value]:
            raise ValueError("Plan must be tested before approval")
        
        if not plan.get("requirements_met", False):
            raise ValueError("Cannot approve plan that does not meet requirements")
        
        # Update plan status and approver
        plan["status"] = IntegrationStatus.APPROVED.value
        plan["approver"] = approver
        
        self.integration_history.append({
            "plan_id": plan_id,
            "action": "approved",
            "timestamp": datetime.now().isoformat(),
            "approver": approver
        })
        
        return {
            "status": IntegrationStatus.APPROVED.value,
            "approver": approver,
            "metrics": plan.get("metrics", {}),
            "requirements_met": plan.get("requirements_met", False)
        }
    
    async def apply_changes(self, plan_id: str) -> Dict[str, Any]:
        """Apply approved changes to the system.
        
        Args:
            plan_id: ID of the integration plan
            
        Returns:
            Dictionary containing application results
        """
        plan = self.integration_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Integration plan {plan_id} not found")
        
        if self.security_config.get("require_approval", True) and plan["status"] != IntegrationStatus.APPROVED.value:
            raise ValueError("Plan is not approved")
        
        logger.info(f"Applying changes for plan {plan_id}")
        
        try:
            start_time = datetime.now()
            
            # Create backup if enabled
            if self.security_config.get("backup_enabled", True):
                backup_path = await self._create_backup()
                plan["backup_path"] = backup_path
            
            # Apply changes from staging to main
            for file_path, content in plan["changes"].items():
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content["content"])  # Access content from the dictionary
            
            # Stage and commit changes
            for file_path in plan["changes"].keys():
                await self.git_manager.stage_file(file_path)
            await self.git_manager.commit(f"Integration plan {plan_id}: {plan['description']}")
            
            # Verify changes
            verification = await self._verify_changes(plan["changes"])
            if not verification["success"]:
                if self.security_config.get("auto_rollback", True):
                    await self.rollback_changes(plan_id)
                plan["status"] = IntegrationStatus.FAILED.value
                return {
                    "status": IntegrationStatus.FAILED.value,
                    "error": verification["error"],
                    "verification": verification
                }
            
            # Update metrics and status
            end_time = datetime.now()
            if "metrics" in plan and isinstance(plan["metrics"], dict):
                plan["metrics"]["integration_time"] = (end_time - start_time).total_seconds()
            
            plan["status"] = IntegrationStatus.APPLIED.value
            plan["applied_at"] = end_time.isoformat()
            
            self.integration_history.append({
                "plan_id": plan_id,
                "action": "applied",
                "timestamp": end_time.isoformat(),
                "metrics": plan.get("metrics", {})
            })
            
            return {
                "status": IntegrationStatus.APPLIED.value,
                "metrics": plan.get("metrics", {}),
                "applied_at": plan["applied_at"],
                "verification": verification
            }
            
        except Exception as e:
            logger.error(f"Failed to apply changes for plan {plan_id}: {str(e)}")
            if self.security_config.get("auto_rollback", True):
                await self.rollback_changes(plan_id)
            plan["status"] = IntegrationStatus.FAILED.value
            return {
                "status": IntegrationStatus.FAILED.value,
                "error": str(e),
                "verification": {"success": False, "error": str(e)}
            }
    
    async def rollback_changes(self, plan_id: str) -> Dict[str, Any]:
        """Rollback changes to previous state.
        
        Args:
            plan_id: ID of the integration plan
            
        Returns:
            Dictionary containing rollback results
        """
        plan = self.integration_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Integration plan {plan_id} not found")
        
        logger.info(f"Rolling back changes for plan {plan_id}")
        
        try:
            backup_path = plan.get("backup_path")
            if backup_path and os.path.exists(backup_path):
                # Restore from backup
                await self.git_manager.restore_backup(backup_path)
                
                # Update metrics
                if "metrics" in plan and isinstance(plan["metrics"], dict):
                    plan["metrics"]["rollback_count"] = plan["metrics"].get("rollback_count", 0) + 1
                
                # Update plan status
                plan["status"] = IntegrationStatus.ROLLED_BACK.value
                plan["rolled_back_at"] = datetime.now().isoformat()
                
                self.integration_history.append({
                    "plan_id": plan_id,
                    "action": "rolled_back",
                    "timestamp": plan["rolled_back_at"],
                    "metrics": plan.get("metrics", {})
                })
                
                return {
                    "status": IntegrationStatus.ROLLED_BACK.value,
                    "rolled_back_at": plan["rolled_back_at"]
                }
            else:
                raise ValueError("No backup available for rollback")
            
        except Exception as e:
            logger.error(f"Failed to rollback changes for plan {plan_id}: {str(e)}")
            return {
                "status": IntegrationStatus.FAILED.value,
                "error": str(e)
            }
    
    async def _create_backup(self) -> str:
        """Create backup of current state.
        
        Returns:
            Path to backup directory
        """
        backup_dir = tempfile.mkdtemp(prefix="integration_backup_")
        await self.git_manager.create_backup(backup_dir)
        return backup_dir
    
    async def _verify_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Verify applied changes.
        
        Args:
            changes: Dictionary of file paths and their changes
            
        Returns:
            Dictionary containing verification results
        """
        try:
            # Verify each changed file
            for file_path, change in changes.items():
                if not os.path.exists(file_path):
                    return {
                        "success": False,
                        "error": f"File {file_path} not found"
                    }
                
                with open(file_path, 'r') as f:
                    actual_content = f.read()
                
                if actual_content != change["content"]:
                    return {
                        "success": False,
                        "error": f"Content mismatch in {file_path}"
                    }
            
            return {
                "success": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            } 