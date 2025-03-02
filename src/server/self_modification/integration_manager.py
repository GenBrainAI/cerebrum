from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
import shutil
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

class IntegrationManager:
    """Manages the safe integration of new or modified code."""
    
    def __init__(self, git_manager, test_runner, security_config: Optional[Dict[str, Any]] = None):
        """Initialize with required components and security configuration.
        
        Args:
            git_manager: Git manager for version control operations.
            test_runner: Test runner for running tests.
            security_config: Configuration for security validation.
                            If None, default configuration will be used.
        """
        self.git_manager = git_manager
        self.test_runner = test_runner
        self.security_config = security_config or {
            "requires_approval": True,
            "auto_rollback": True,
            "backup_before_changes": True,
            "test_before_apply": True,
            "max_integration_time": 300  # seconds
        }
        self.integration_plans = {}
        self.integration_history = []
        
    async def create_integration_plan(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan for integrating changes.
        
        Args:
            changes: Dictionary containing changes to be integrated.
                    Format: {"file_path": {"content": "...", "description": "..."}, ...}
            
        Returns:
            Dictionary containing integration plan details.
        """
        plan_id = str(uuid.uuid4())
        logger.info(f"Creating integration plan with ID: {plan_id}")
        
        # Create integration plan
        plan = {
            "id": plan_id,
            "changes": changes,
            "status": "created",
            "creation_time": datetime.now().isoformat(),
            "stages": {
                "staging": {"status": "pending"},
                "testing": {"status": "pending"},
                "application": {"status": "pending"},
                "verification": {"status": "pending"}
            },
            "requires_approval": self.security_config["requires_approval"],
            "approved": False,
            "approver": None,
            "approval_time": None,
            "metrics": {}
        }
        
        self.integration_plans[plan_id] = plan
        
        # Record in history
        self.integration_history.append({
            "action": "create_plan",
            "plan_id": plan_id,
            "timestamp": datetime.now().isoformat(),
            "changes_count": len(changes)
        })
        
        return plan
    
    async def stage_changes(self, integration_plan_id: str) -> Dict[str, Any]:
        """Stage changes in a controlled environment for testing.
        
        Args:
            integration_plan_id: ID of the integration plan.
            
        Returns:
            Dictionary containing staging results.
        """
        if integration_plan_id not in self.integration_plans:
            return {"error": f"Integration plan {integration_plan_id} not found"}
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Staging changes for integration plan: {integration_plan_id}")
        
        # Update plan status
        plan["status"] = "staging"
        plan["stages"]["staging"]["status"] = "in_progress"
        plan["stages"]["staging"]["start_time"] = datetime.now().isoformat()
        
        try:
            # Create a staging directory
            staging_dir = tempfile.mkdtemp(prefix=f"cerebrum_staging_{integration_plan_id}_")
            plan["stages"]["staging"]["staging_dir"] = staging_dir
            
            # Get current repository state
            repo_status = await self.git_manager.get_repository_status()
            plan["stages"]["staging"]["repo_status"] = repo_status
            
            # Create a backup if configured
            if self.security_config["backup_before_changes"]:
                backup_result = await self._create_backup(integration_plan_id)
                plan["stages"]["staging"]["backup"] = backup_result
            
            # Apply changes to staging directory
            for file_path, change_info in plan["changes"].items():
                # Ensure directory exists
                full_path = os.path.join(staging_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Write file content
                with open(full_path, "w") as f:
                    f.write(change_info["content"])
            
            # Update plan status
            plan["stages"]["staging"]["status"] = "completed"
            plan["stages"]["staging"]["completion_time"] = datetime.now().isoformat()
            
            # Record in history
            self.integration_history.append({
                "action": "stage_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "completed",
                "staging_dir": staging_dir
            }
        except Exception as e:
            logger.error(f"Staging failed with error: {str(e)}")
            
            # Update plan status
            plan["stages"]["staging"]["status"] = "failed"
            plan["stages"]["staging"]["error"] = str(e)
            plan["stages"]["staging"]["completion_time"] = datetime.now().isoformat()
            
            # Record in history
            self.integration_history.append({
                "action": "stage_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def test_integration(self, integration_plan_id: str) -> Dict[str, Any]:
        """Test staged changes to ensure they work correctly.
        
        Args:
            integration_plan_id: ID of the integration plan.
            
        Returns:
            Dictionary containing test results.
        """
        if integration_plan_id not in self.integration_plans:
            return {"error": f"Integration plan {integration_plan_id} not found"}
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Testing integration for plan: {integration_plan_id}")
        
        # Check if staging is completed
        if plan["stages"]["staging"]["status"] != "completed":
            return {"error": "Staging must be completed before testing"}
        
        # Update plan status
        plan["status"] = "testing"
        plan["stages"]["testing"]["status"] = "in_progress"
        plan["stages"]["testing"]["start_time"] = datetime.now().isoformat()
        
        try:
            staging_dir = plan["stages"]["staging"]["staging_dir"]
            
            # Run tests on staged changes
            test_results = await self.test_runner.run_tests(test_path=staging_dir)
            plan["stages"]["testing"]["test_results"] = test_results
            
            # Determine if tests passed
            tests_passed = test_results.get("success", False)
            
            # Update plan status
            plan["stages"]["testing"]["status"] = "completed" if tests_passed else "failed"
            plan["stages"]["testing"]["completion_time"] = datetime.now().isoformat()
            
            # Record in history
            self.integration_history.append({
                "action": "test_integration",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if tests_passed else "failed",
                "tests_passed": tests_passed
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "completed" if tests_passed else "failed",
                "tests_passed": tests_passed,
                "test_results": test_results
            }
        except Exception as e:
            logger.error(f"Testing failed with error: {str(e)}")
            
            # Update plan status
            plan["stages"]["testing"]["status"] = "failed"
            plan["stages"]["testing"]["error"] = str(e)
            plan["stages"]["testing"]["completion_time"] = datetime.now().isoformat()
            
            # Record in history
            self.integration_history.append({
                "action": "test_integration",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def apply_changes(self, integration_plan_id: str, 
                          requires_approval: bool = True) -> Dict[str, Any]:
        """Apply changes to the running system.
        
        Args:
            integration_plan_id: ID of the integration plan.
            requires_approval: Whether approval is required before applying changes.
            
        Returns:
            Dictionary containing application results.
        """
        if integration_plan_id not in self.integration_plans:
            return {"error": f"Integration plan {integration_plan_id} not found"}
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Applying changes for integration plan: {integration_plan_id}")
        
        # Check if testing is completed (if required)
        if self.security_config["test_before_apply"] and plan["stages"]["testing"]["status"] != "completed":
            return {"error": "Testing must be completed successfully before applying changes"}
        
        # Check if approval is required and granted
        if requires_approval and not plan.get("approved", False):
            return {"error": "Approval is required before applying changes"}
        
        # Update plan status
        plan["status"] = "applying"
        plan["stages"]["application"]["status"] = "in_progress"
        plan["stages"]["application"]["start_time"] = datetime.now().isoformat()
        
        try:
            # Apply changes to the actual system
            for file_path, change_info in plan["changes"].items():
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write file content
                with open(file_path, "w") as f:
                    f.write(change_info["content"])
            
            # Commit changes if using git
            if hasattr(self.git_manager, "commit_changes"):
                commit_message = f"Integration of changes from plan {integration_plan_id}"
                commit_result = await self.git_manager.commit_changes(
                    message=commit_message,
                    files=list(plan["changes"].keys())
                )
                plan["stages"]["application"]["commit_result"] = commit_result
            
            # Update plan status
            plan["stages"]["application"]["status"] = "completed"
            plan["stages"]["application"]["completion_time"] = datetime.now().isoformat()
            
            # Record in history
            self.integration_history.append({
                "action": "apply_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "completed",
                "files_changed": list(plan["changes"].keys())
            }
        except Exception as e:
            logger.error(f"Applying changes failed with error: {str(e)}")
            
            # Update plan status
            plan["stages"]["application"]["status"] = "failed"
            plan["stages"]["application"]["error"] = str(e)
            plan["stages"]["application"]["completion_time"] = datetime.now().isoformat()
            
            # Auto-rollback if configured
            if self.security_config["auto_rollback"]:
                rollback_result = await self.rollback_changes(integration_plan_id)
                plan["stages"]["application"]["rollback_result"] = rollback_result
            
            # Record in history
            self.integration_history.append({
                "action": "apply_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
                "auto_rollback": self.security_config["auto_rollback"]
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "failed",
                "error": str(e),
                "auto_rollback": self.security_config["auto_rollback"]
            }
    
    async def rollback_changes(self, integration_plan_id: str) -> Dict[str, Any]:
        """Rollback changes if needed.
        
        Args:
            integration_plan_id: ID of the integration plan.
            
        Returns:
            Dictionary containing rollback results.
        """
        if integration_plan_id not in self.integration_plans:
            return {"error": f"Integration plan {integration_plan_id} not found"}
        
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Rolling back changes for integration plan: {integration_plan_id}")
        
        # Update plan status
        plan["status"] = "rolling_back"
        
        try:
            # Check if we have a backup
            if "backup" in plan["stages"]["staging"] and plan["stages"]["staging"]["backup"].get("success", False):
                backup_dir = plan["stages"]["staging"]["backup"]["backup_dir"]
                
                # Restore from backup
                for file_path in plan["changes"].keys():
                    backup_file_path = os.path.join(backup_dir, file_path)
                    
                    # Check if backup file exists
                    if os.path.exists(backup_file_path):
                        # Restore file
                        shutil.copy2(backup_file_path, file_path)
                    else:
                        # If no backup exists, the file was newly created, so remove it
                        if os.path.exists(file_path):
                            os.remove(file_path)
                
                # If using git, reset to previous state
                if hasattr(self.git_manager, "reset_to_commit"):
                    previous_commit = plan["stages"]["staging"]["repo_status"].get("commit_hash")
                    if previous_commit:
                        await self.git_manager.reset_to_commit(previous_commit)
            
            # Update plan status
            plan["status"] = "rolled_back"
            
            # Record in history
            self.integration_history.append({
                "action": "rollback_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "completed",
                "files_restored": list(plan["changes"].keys())
            }
        except Exception as e:
            logger.error(f"Rollback failed with error: {str(e)}")
            
            # Update plan status
            plan["status"] = "rollback_failed"
            
            # Record in history
            self.integration_history.append({
                "action": "rollback_changes",
                "plan_id": integration_plan_id,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return {
                "plan_id": integration_plan_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def get_integration_status(self, integration_plan_id: str) -> Dict[str, Any]:
        """Get current status of an integration plan.
        
        Args:
            integration_plan_id: ID of the integration plan.
            
        Returns:
            Dictionary containing integration plan status.
        """
        if integration_plan_id not in self.integration_plans:
            return {"error": f"Integration plan {integration_plan_id} not found"}
        
        return self.integration_plans[integration_plan_id]
    
    async def record_integration(self, integration_plan_id: str, 
                               success: bool, metrics: Dict[str, Any]) -> None:
        """Record integration attempt for learning and improvement.
        
        Args:
            integration_plan_id: ID of the integration plan.
            success: Whether the integration was successful.
            metrics: Metrics about the integration.
        """
        if integration_plan_id not in self.integration_plans:
            logger.error(f"Cannot record metrics for unknown integration plan: {integration_plan_id}")
            return
        
        plan = self.integration_plans[integration_plan_id]
        
        # Update plan metrics
        plan["metrics"].update(metrics)
        plan["metrics"]["success"] = success
        plan["metrics"]["record_time"] = datetime.now().isoformat()
        
        # Record in history
        self.integration_history.append({
            "action": "record_integration",
            "plan_id": integration_plan_id,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "metrics": metrics
        })
    
    async def _create_backup(self, integration_plan_id: str) -> Dict[str, Any]:
        """Create a backup of files before changes.
        
        Args:
            integration_plan_id: ID of the integration plan.
            
        Returns:
            Dictionary containing backup results.
        """
        plan = self.integration_plans[integration_plan_id]
        logger.info(f"Creating backup for integration plan: {integration_plan_id}")
        
        try:
            # Create backup directory
            backup_dir = tempfile.mkdtemp(prefix=f"cerebrum_backup_{integration_plan_id}_")
            
            # Backup existing files
            for file_path in plan["changes"].keys():
                if os.path.exists(file_path):
                    # Create directory structure in backup
                    backup_file_dir = os.path.dirname(os.path.join(backup_dir, file_path))
                    os.makedirs(backup_file_dir, exist_ok=True)
                    
                    # Copy file to backup
                    shutil.copy2(file_path, os.path.join(backup_dir, file_path))
            
            return {
                "success": True,
                "backup_dir": backup_dir,
                "files_backed_up": [f for f in plan["changes"].keys() if os.path.exists(f)],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Backup failed with error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 