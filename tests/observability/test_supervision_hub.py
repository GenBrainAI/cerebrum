import pytest
import os
import json
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.server.observability.supervision_hub import (
    SupervisionHub,
    SupervisorRole,
    ApprovalPolicy,
    ApprovalWorkflow,
    ApprovalStatus
)
from src.server.observability.intervention_interface import InterventionLevel

class TestSupervisionHub:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def hub(self, temp_dir):
        """Create a SupervisionHub instance with temporary storage."""
        hub = SupervisionHub(storage_path=temp_dir)
        yield hub
    
    @pytest.mark.asyncio
    async def test_register_supervisor(self, hub):
        """Test supervisor registration."""
        # Register a supervisor
        result = await hub.register_supervisor(
            username="test_user",
            name="Test User",
            email="test@example.com",
            password="test_password123",
            roles=["supervisor", "operator"]
        )
        
        assert result["success"] is True
        assert "supervisor_id" in result
        assert "token" in result
        assert "roles" in result
        
        # Check that the supervisor was saved
        supervisor_id = result["supervisor_id"]
        assert supervisor_id in hub.supervisors
        
        # Try to register with the same username
        duplicate_result = await hub.register_supervisor(
            username="test_user",
            name="Another User",
            email="another@example.com",
            password="another_password",
            roles=["observer"]
        )
        
        assert duplicate_result["success"] is False
        assert "already exists" in duplicate_result["message"]
    
    @pytest.mark.asyncio
    async def test_authenticate_supervisor(self, hub):
        """Test supervisor authentication."""
        # Register a supervisor
        register_result = await hub.register_supervisor(
            username="auth_test",
            name="Auth Test",
            email="auth@example.com",
            password="auth_password123",
            roles=["supervisor"]
        )
        
        # Authenticate with correct credentials
        auth_result = await hub.authenticate_supervisor(
            username="auth_test",
            password="auth_password123"
        )
        
        assert auth_result["success"] is True
        assert auth_result["supervisor_id"] == register_result["supervisor_id"]
        assert "token" in auth_result
        
        # Try to authenticate with incorrect password
        wrong_pass_result = await hub.authenticate_supervisor(
            username="auth_test",
            password="wrong_password"
        )
        
        assert wrong_pass_result["success"] is False
        assert "Invalid username or password" in wrong_pass_result["message"]
        
        # Try to authenticate with non-existent username
        wrong_user_result = await hub.authenticate_supervisor(
            username="nonexistent",
            password="auth_password123"
        )
        
        assert wrong_user_result["success"] is False
        assert "Invalid username or password" in wrong_user_result["message"]
    
    @pytest.mark.asyncio
    async def test_approval_policy_management(self, hub):
        """Test creating and retrieving approval policies."""
        # Create a policy
        policy_result = await hub.create_approval_policy(
            name="Test Policy",
            description="A test policy",
            required_roles={"supervisor": 1, "expert": 2},
            threshold_percentage=80,
            expiration_hours=48,
            consecutive_order=True,
            enable_override=False,
            rejection_blocks=True
        )
        
        assert policy_result["success"] is True
        assert "policy_id" in policy_result
        
        # Get all policies
        policies = await hub.get_approval_policies()
        
        # Should have at least the default policy and our new one
        assert len(policies) >= 2
        
        # Find our policy
        policy = next((p for p in policies if p["name"] == "Test Policy"), None)
        assert policy is not None
        assert policy["required_roles"] == {"supervisor": 1, "expert": 2}
        assert policy["threshold_percentage"] == 80
        assert policy["expiration_hours"] == 48
        assert policy["consecutive_order"] is True
        assert policy["enable_override"] is False
        assert policy["rejection_blocks"] is True
    
    @pytest.mark.asyncio
    async def test_approval_workflow(self, hub):
        """Test the approval workflow lifecycle."""
        # Register supervisors
        supervisor1 = await hub.register_supervisor(
            username="supervisor1",
            name="Supervisor One",
            email="sup1@example.com",
            password="password123",
            roles=["supervisor"]
        )
        
        expert1 = await hub.register_supervisor(
            username="expert1",
            name="Expert One",
            email="expert1@example.com",
            password="password123",
            roles=["expert"]
        )
        
        expert2 = await hub.register_supervisor(
            username="expert2",
            name="Expert Two",
            email="expert2@example.com",
            password="password123",
            roles=["expert"]
        )
        
        # Create a policy
        policy_result = await hub.create_approval_policy(
            name="Test Workflow Policy",
            description="A test workflow policy",
            required_roles={"supervisor": 1, "expert": 2},
            supervisor_id=supervisor1["supervisor_id"]
        )
        
        # Create a workflow
        workflow_result = await hub.create_approval_workflow(
            title="Test Workflow",
            description="A test workflow",
            policy_id=policy_result["policy_id"],
            supervisor_id=supervisor1["supervisor_id"],
            metadata={"test_key": "test_value"}
        )
        
        assert workflow_result["success"] is True
        assert "workflow_id" in workflow_result
        
        # Get workflows for the supervisor
        workflows = await hub.get_workflows(
            supervisor_id=supervisor1["supervisor_id"]
        )
        
        assert len(workflows) >= 1
        workflow = next((w for w in workflows if w["id"] == workflow_result["workflow_id"]), None)
        assert workflow is not None
        assert workflow["status"] == "waiting"
        
        # Approve from the supervisor
        approve_result = await hub.approve_workflow(
            workflow_id=workflow_result["workflow_id"],
            supervisor_id=supervisor1["supervisor_id"],
            comments="Looks good!"
        )
        
        assert approve_result["success"] is True
        
        # Approve from the first expert
        expert1_approve = await hub.approve_workflow(
            workflow_id=workflow_result["workflow_id"],
            supervisor_id=expert1["supervisor_id"],
            comments="Approved as expert"
        )
        
        assert expert1_approve["success"] is True
        
        # Check workflow status - should be partial until all required approvals
        workflows = await hub.get_workflows(
            supervisor_id=supervisor1["supervisor_id"]
        )
        workflow = next((w for w in workflows if w["id"] == workflow_result["workflow_id"]), None)
        assert workflow is not None
        assert workflow["status"] == "partial"
        
        # Approve from the second expert
        expert2_approve = await hub.approve_workflow(
            workflow_id=workflow_result["workflow_id"],
            supervisor_id=expert2["supervisor_id"],
            comments="Also approved as expert"
        )
        
        assert expert2_approve["success"] is True
        
        # Check workflow status - should now be approved
        workflows = await hub.get_workflows(
            supervisor_id=supervisor1["supervisor_id"]
        )
        workflow = next((w for w in workflows if w["id"] == workflow_result["workflow_id"]), None)
        assert workflow is not None
        assert workflow["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_workflow_rejection(self, hub):
        """Test workflow rejection."""
        # Register supervisors
        supervisor = await hub.register_supervisor(
            username="reject_sup",
            name="Rejection Supervisor",
            email="reject_sup@example.com",
            password="password123",
            roles=["supervisor"]
        )
        
        # Create a policy with rejection_blocks=True
        policy_result = await hub.create_approval_policy(
            name="Rejection Policy",
            description="A policy that can be rejected",
            required_roles={"supervisor": 1},
            rejection_blocks=True,
            supervisor_id=supervisor["supervisor_id"]
        )
        
        # Create a workflow
        workflow_result = await hub.create_approval_workflow(
            title="Rejection Test",
            description="A workflow to test rejection",
            policy_id=policy_result["policy_id"],
            supervisor_id=supervisor["supervisor_id"]
        )
        
        # Reject the workflow
        reject_result = await hub.reject_workflow(
            workflow_id=workflow_result["workflow_id"],
            supervisor_id=supervisor["supervisor_id"],
            reason="Not approved for testing reasons"
        )
        
        assert reject_result["success"] is True
        
        # Check workflow status - should be rejected
        workflows = await hub.get_workflows(
            supervisor_id=supervisor["supervisor_id"]
        )
        workflow = next((w for w in workflows if w["id"] == workflow_result["workflow_id"]), None)
        assert workflow is not None
        assert workflow["status"] == "rejected"
    
    @pytest.mark.asyncio
    async def test_notification_management(self, hub):
        """Test notification creation and management."""
        # Register a supervisor
        supervisor = await hub.register_supervisor(
            username="notif_test",
            name="Notification Test",
            email="notif@example.com",
            password="password123",
            roles=["supervisor"]
        )
        
        # Create a notification
        notification_id = await hub.create_notification(
            supervisor_ids=[supervisor["supervisor_id"]],
            message="Test notification",
            level="info",
            context={"test": True}
        )
        
        assert notification_id is not None
        
        # Get notifications
        notifications = await hub.get_supervisor_notifications(
            supervisor_id=supervisor["supervisor_id"]
        )
        
        assert len(notifications) >= 1
        notification = next((n for n in notifications if n["id"] == notification_id), None)
        assert notification is not None
        assert notification["message"] == "Test notification"
        assert notification["level"] == "info"
        assert notification["context"] == {"test": True}
        
        # Mark as read
        mark_result = await hub.mark_notification_read(
            notification_id=notification_id,
            supervisor_id=supervisor["supervisor_id"]
        )
        
        assert mark_result["success"] is True
        
        # Should not appear in unread notifications
        unread = await hub.get_supervisor_notifications(
            supervisor_id=supervisor["supervisor_id"],
            include_read=False
        )
        
        assert not any(n["id"] == notification_id for n in unread)
        
        # Should appear in all notifications
        all_notifications = await hub.get_supervisor_notifications(
            supervisor_id=supervisor["supervisor_id"],
            include_read=True
        )
        
        assert any(n["id"] == notification_id for n in all_notifications)
    
    @pytest.mark.asyncio
    async def test_integration_with_intervention_interface(self, hub):
        """Test integration with the intervention interface."""
        # Create a mock intervention interface
        mock_interface = MagicMock()
        mock_interface.respond_to_intervention = AsyncMock()
        mock_interface.respond_to_intervention.return_value = {"success": True}
        mock_interface._save_intervention = AsyncMock()
        mock_interface._save_intervention.return_value = {"success": True}
        mock_interface.interventions = {}
        
        # Set the interface
        await hub.set_intervention_interface(mock_interface)
        
        # Register an admin
        admin = await hub.register_supervisor(
            username="admin_test",
            name="Admin Test",
            email="admin@example.com",
            password="password123",
            roles=["admin", "supervisor"]
        )
        
        # Handle an intervention request (critical level)
        intervention_id = "test_intervention_123"
        intervention_result = await hub.handle_intervention_request(
            intervention_id=intervention_id,
            level=InterventionLevel.CRITICAL,
            title="Critical Test",
            description="A critical test intervention",
            context={"test": True}
        )
        
        assert intervention_result["success"] is True
        assert "workflow_id" in intervention_result
        
        # Get workflows for admin to confirm it was created
        workflows = await hub.get_workflows(supervisor_id=admin["supervisor_id"])
        workflow = next((w for w in workflows if w["metadata"].get("intervention_id") == intervention_id), None)
        assert workflow is not None
        
        # Approve the workflow
        approve_result = await hub.approve_workflow(
            workflow_id=intervention_result["workflow_id"],
            supervisor_id=admin["supervisor_id"],
            comments="Approved for testing"
        )
        
        assert approve_result["success"] is True
        
        # Give time for the async processing to complete
        await asyncio.sleep(0.1)
        
        # Check that the intervention interface was called
        assert mock_interface.respond_to_intervention.called
        call_args = mock_interface.respond_to_intervention.call_args
        assert call_args is not None
        kwargs = call_args[1]
        assert kwargs["intervention_id"] == intervention_id
        assert "response" in kwargs
        assert kwargs["response"].get("approved") is True

# Helper for async mock
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
    
    # Override normal methods for the async behavior
    async def __await__(self):
        return self().__await__()

    def assert_called_once(self):
        if not self.call_count == 1:
            msg = (f"Expected '{self._mock_name or 'mock'}' to have been called once. "
                   f"Called {self.call_count} times.")
            raise AssertionError(msg)
        return super(AsyncMock, self).assert_called_once() 