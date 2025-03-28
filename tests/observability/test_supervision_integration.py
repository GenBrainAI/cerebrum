import pytest
import os
import json
import asyncio
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.server.observability.supervision_hub import SupervisionHub
from src.server.observability.intervention_interface import (
    InterventionInterface,
    InterventionLevel,
    InterventionStatus,
    ResponseAction
)

class TestSupervisionIntegration:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def supervision_hub(self, temp_dir):
        """Create a SupervisionHub instance with temporary storage."""
        return SupervisionHub(storage_path=os.path.join(temp_dir, "supervision"))
    
    @pytest.fixture
    def intervention_interface(self, temp_dir):
        """Create an InterventionInterface with temporary storage."""
        storage_path = os.path.join(temp_dir, "interventions")
        os.makedirs(storage_path, exist_ok=True)
        return InterventionInterface(config={
            "storage_path": storage_path
        })
    
    @pytest.mark.asyncio
    async def test_full_intervention_workflow(self, supervision_hub, intervention_interface):
        """Test the full workflow of intervention, supervision, and response."""
        # Connect the components
        await supervision_hub.set_intervention_interface(intervention_interface)
        intervention_interface.set_supervision_hub(supervision_hub)
        
        # Register a supervisor
        admin = await supervision_hub.register_supervisor(
            username="admin_user",
            name="Admin User",
            email="admin@example.com",
            password="secure_admin_pass",
            roles=["admin", "supervisor"]
        )
        
        # Create an approval policy
        policy = await supervision_hub.create_approval_policy(
            name="Critical Intervention Policy",
            description="Policy for handling critical interventions",
            required_roles={"supervisor": 1},
            threshold_percentage=50,
            rejection_blocks=True
        )
        
        # Create an intervention request
        intervention_id = await intervention_interface.create_intervention(
            level=InterventionLevel.CRITICAL,
            title="Critical System Issue",
            description="The system has encountered a critical error that requires human review.",
            context={
                "error_code": "ERR-1234",
                "component": "database_connection",
                "timestamp": datetime.now().isoformat()
            },
            suggested_actions=[
                {"action": "restart_service", "description": "Restart the database service"},
                {"action": "check_logs", "description": "Review database logs for errors"}
            ]
        )
        
        # Check that the intervention was created
        interventions = await intervention_interface.get_interventions(status=InterventionStatus.PENDING)
        assert len(interventions) >= 1
        intervention = next((i for i in interventions if i["id"] == intervention_id), None)
        assert intervention is not None
        assert intervention["level"] == InterventionLevel.CRITICAL.value
        
        # Check that a workflow was created in the supervision hub
        workflows = await supervision_hub.get_workflows(supervisor_id=admin["supervisor_id"])
        assert len(workflows) >= 1
        
        # Find the workflow related to our intervention
        workflow = next((w for w in workflows if w["metadata"].get("intervention_id") == intervention_id), None)
        assert workflow is not None
        
        # Approve the workflow as admin
        approve_result = await supervision_hub.approve_workflow(
            workflow_id=workflow["id"],
            supervisor_id=admin["supervisor_id"],
            comments="Issue identified and resolved."
        )
        
        assert approve_result["success"] is True
        
        # Check that the intervention was updated
        updated_interventions = await intervention_interface.get_interventions(status=InterventionStatus.RESOLVED)
        assert len(updated_interventions) >= 1
        updated_intervention = next((i for i in updated_interventions if i["id"] == intervention_id), None)
        assert updated_intervention is not None
        assert updated_intervention["status"] == InterventionStatus.RESOLVED.value
        
        # Check the response in the intervention
        assert updated_intervention["response"]["approved"] is True
        assert updated_intervention["response"]["supervisor_id"] == admin["supervisor_id"]
    
    @pytest.mark.asyncio
    async def test_intervention_rejection(self, supervision_hub, intervention_interface):
        """Test rejecting an intervention."""
        # Connect the components
        await supervision_hub.set_intervention_interface(intervention_interface)
        intervention_interface.set_supervision_hub(supervision_hub)

        # Register supervisors
        admin = await supervision_hub.register_supervisor(
            username="expert_user",
            name="Expert User",
            email="expert@example.com",
            password="secure_expert_pass",
            roles=["admin", "expert", "supervisor"]
        )
        
        # Create an approval policy
        policy = await supervision_hub.create_approval_policy(
            name="Expert Intervention Policy",
            description="Policy for expert interventions",
            required_roles={"supervisor": 1, "expert": 1},
            threshold_percentage=50,
            rejection_blocks=True
        )
        
        # Create an intervention request
        intervention_id = await intervention_interface.create_intervention(
            level=InterventionLevel.WARNING,
            title="Unusual Access Pattern",
            description="The system has detected an unusual access pattern that requires review.",
            context={
                "ip_address": "192.168.1.100",
                "access_count": 150,
                "timeframe_minutes": 5
            }
        )
        
        # Check that the intervention was created
        interventions = await intervention_interface.get_interventions(status=InterventionStatus.PENDING)
        assert len(interventions) >= 1
        
        # Get request IDs
        requests = await supervision_hub.get_pending_requests(supervisor_id=admin["supervisor_id"])
        assert len(requests) >= 1
        
        # Find request related to our intervention
        request = next((r for r in requests if r["details"].get("intervention_id") == intervention_id), None)
        assert request is not None
        
        # Reject the request
        reject_result = await supervision_hub.reject_request(
            request_id=request["id"],
            supervisor_id=admin["supervisor_id"],
            reason="This is a known pattern from a scheduled task. Not a security issue."
        )
        
        assert reject_result["success"] is True
        
        # Check that the intervention was updated
        updated_interventions = await intervention_interface.get_interventions(status=InterventionStatus.DISMISSED)
        assert len(updated_interventions) >= 1
        updated_intervention = next((i for i in updated_interventions if i["id"] == intervention_id), None)
        assert updated_intervention is not None
        assert updated_intervention["status"] == InterventionStatus.DISMISSED.value
        
        # Check the response in the intervention
        assert updated_intervention["response"]["approved"] is False
        assert "known pattern" in updated_intervention["response"]["message"]
    
    @pytest.mark.asyncio
    async def test_resource_alert_to_intervention(self, supervision_hub, intervention_interface, monkeypatch):
        """Test resource monitor alerts creating interventions."""
        # Mock ResourceMonitor for testing
        class MockResourceMonitor:
            def __init__(self):
                self.supervision_hub = None
            
            async def set_supervision_hub(self, hub):
                self.supervision_hub = hub
            
            async def simulate_alert(self, resource_type, component, usage, limit):
                """Simulate an alert being triggered."""
                if not self.supervision_hub:
                    return False
                
                result = await self.supervision_hub.handle_intervention_request(
                    intervention_id=f"resource_alert_{resource_type}_{component}",
                    level=InterventionLevel.WARNING,
                    title=f"High {resource_type.upper()} usage for {component}",
                    description=f"Component {component} is using {usage} of {limit} {resource_type} allocation.",
                    context={
                        "resource_type": resource_type,
                        "component": component,
                        "current_usage": usage,
                        "limit": limit,
                        "percentage": round(usage/limit * 100, 2)
                    }
                )
                return result
        
        # Connect the components
        await supervision_hub.set_intervention_interface(intervention_interface)
        intervention_interface.set_supervision_hub(supervision_hub)
        
        # Create resource monitor mock
        resource_monitor = MockResourceMonitor()
        await resource_monitor.set_supervision_hub(supervision_hub)
        
        # Register a supervisor
        operator = await supervision_hub.register_supervisor(
            username="system_operator",
            name="System Operator",
            email="operator@example.com",
            password="secure_operator_pass",
            roles=["operator"]
        )
        
        # Simulate a resource alert
        alert_result = await resource_monitor.simulate_alert(
            resource_type="memory",
            component="inference_service",
            usage=750,
            limit=1000
        )
        
        assert alert_result["success"] is True
        intervention_id = f"resource_alert_memory_inference_service"
        
        # Get pending requests
        requests = await supervision_hub.get_pending_requests(supervisor_id=operator["supervisor_id"])
        assert len(requests) >= 1
        
        # Find our request
        request = next((r for r in requests if r["details"].get("intervention_id") == intervention_id), None)
        assert request is not None
        
        # Approve the request
        approve_result = await supervision_hub.approve_request(
            request_id=request["id"],
            supervisor_id=operator["supervisor_id"],
            comments="Will monitor the situation. No action needed at this time."
        )
        
        assert approve_result["success"] is True
        
        # Check that the intervention was updated
        interventions = await intervention_interface.get_interventions()
        intervention = next((i for i in interventions if i["id"] == intervention_id), None)
        assert intervention is not None
        assert intervention["status"] == InterventionStatus.RESOLVED.value
        assert intervention["response"]["approved"] is True 