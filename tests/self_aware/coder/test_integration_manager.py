import pytest
import asyncio
from typing import Dict, Any
import tempfile
import os
from pathlib import Path
from src.server.code_management.integration_manager import IntegrationManager, IntegrationStatus, IntegrationMetrics

class MockGitManager:
    """Mock Git operations manager for testing."""
    
    async def clone(self, path: str):
        os.makedirs(path, exist_ok=True)
    
    async def create_backup(self, path: str):
        os.makedirs(path, exist_ok=True)
        
    async def restore_backup(self, path: str):
        pass
        
    async def stage_file(self, path: str):
        pass
        
    async def commit(self, message: str):
        pass

class MockTestRunner:
    """Mock test runner for testing."""
    
    async def run_tests(self, path: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "tests_passed": 10,
            "tests_failed": 0,
            "coverage": 0.85,
            "pass_rate": 100.0,
            "completion_time": "2024-03-20T12:00:00",
            "requirements_met": True  # Add this to explicitly indicate requirements are met
        }

@pytest.fixture
def integration_manager():
    """Fixture to create an IntegrationManager instance."""
    security_config = {
        "requires_approval": True,
        "auto_rollback": True,
        "backup_before_changes": True,
        "test_before_apply": True,
        "max_integration_time": 60,
        "required_test_coverage": 0.8,
        "max_file_size": 1024 * 1024,
        "protected_paths": ["config/", "core/", "security/"]
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_path = os.path.join(temp_dir, "backups")
        os.makedirs(backup_path, exist_ok=True)
        
        manager = IntegrationManager(
            git_manager=MockGitManager(),
            test_runner=MockTestRunner(),
            security_config=security_config
        )
        manager.backup_path = backup_path
        yield manager

@pytest.mark.asyncio
async def test_create_integration_plan(integration_manager):
    """Test creating an integration plan."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    
    assert plan["id"] is not None
    assert plan["status"] == IntegrationStatus.PENDING.value
    assert plan["changes"] == changes
    assert "description" in plan
    assert plan["description"] == "Add new helper function"

@pytest.mark.asyncio
async def test_stage_changes(integration_manager):
    """Test staging changes."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    result = await integration_manager.stage_changes(plan["id"])
    
    assert result["status"] == IntegrationStatus.STAGED.value
    assert "staging_path" in result

@pytest.mark.asyncio
async def test_test_integration(integration_manager):
    """Test running integration tests."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    await integration_manager.stage_changes(plan["id"])
    result = await integration_manager.test_integration(plan["id"])
    
    assert result["status"] == IntegrationStatus.TESTING.value
    assert "test_results" in result
    assert result["test_results"]["tests_passed"] > 0

@pytest.mark.asyncio
async def test_approve_integration(integration_manager):
    """Test approving an integration plan."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    await integration_manager.stage_changes(plan["id"])
    await integration_manager.test_integration(plan["id"])
    
    result = await integration_manager.approve_integration(plan["id"], "test_approver")
    
    assert result["status"] == IntegrationStatus.APPROVED.value
    assert result["approver"] == "test_approver"

@pytest.mark.asyncio
async def test_apply_changes(integration_manager):
    """Test applying changes."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    await integration_manager.stage_changes(plan["id"])
    await integration_manager.test_integration(plan["id"])
    await integration_manager.approve_integration(plan["id"], "test_approver")
    
    result = await integration_manager.apply_changes(plan["id"])
    
    assert result["status"] == IntegrationStatus.APPLIED.value
    assert "verification" in result

@pytest.mark.asyncio
async def test_rollback_changes(integration_manager):
    """Test rolling back changes."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    await integration_manager.stage_changes(plan["id"])
    await integration_manager.test_integration(plan["id"])
    await integration_manager.approve_integration(plan["id"], "test_approver")
    await integration_manager.apply_changes(plan["id"])
    
    result = await integration_manager.rollback_changes(plan["id"])
    
    assert result["status"] == IntegrationStatus.ROLLED_BACK.value

@pytest.mark.asyncio
async def test_protected_paths(integration_manager):
    """Test handling of protected paths."""
    changes = {
        "config/settings.py": {  # Protected path
            "content": "SETTING = 'value'",
            "description": "Update settings"
        }
    }
    
    with pytest.raises(ValueError, match="protected path"):
        await integration_manager.create_integration_plan(
            changes=changes,
            description="Update configuration settings"
        )

@pytest.mark.asyncio
async def test_file_size_limit(integration_manager):
    """Test file size limit enforcement."""
    large_content = "x" * (integration_manager.security_config["max_file_size"] + 1)
    changes = {
        "src/large_file.py": {
            "content": large_content,
            "description": "Large file"
        }
    }
    
    with pytest.raises(ValueError, match="exceeds maximum size"):
        await integration_manager.create_integration_plan(
            changes=changes,
            description="Add large file"
        )

@pytest.mark.asyncio
async def test_integration_metrics(integration_manager):
    """Test integration metrics calculation."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper():\n    return True",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    await integration_manager.stage_changes(plan["id"])
    result = await integration_manager.test_integration(plan["id"])
    
    assert "metrics" in result
    assert isinstance(result["metrics"], IntegrationMetrics)
    assert result["metrics"].test_coverage >= 0.0
    assert result["metrics"].test_pass_rate >= 0.0

@pytest.mark.asyncio
async def test_integration_history(integration_manager):
    """Test integration history tracking."""
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    
    assert len(integration_manager.integration_history) > 0
    latest_entry = integration_manager.integration_history[-1]
    assert latest_entry["action"] == "created"
    assert latest_entry["plan_id"] == plan["id"]

@pytest.mark.asyncio
async def test_error_handling(integration_manager):
    """Test error handling."""
    # Test with non-existent plan ID
    with pytest.raises(ValueError, match="not found"):
        await integration_manager.stage_changes("non_existent_id")
    
    # Test applying changes without approval
    changes = {
        "src/utils/helper.py": {
            "content": "def helper(): pass",
            "description": "Add helper function"
        }
    }
    
    plan = await integration_manager.create_integration_plan(
        changes=changes,
        description="Add new helper function"
    )
    
    with pytest.raises(ValueError, match="not approved"):
        await integration_manager.apply_changes(plan["id"]) 