"""
Test suite for the InterventionInterface component.

Tests the basic functionality of the intervention interface, including:
- Creating intervention requests
- Auto-approving information-level interventions
- Responding to interventions
- Handling timeouts
- Retrieving pending interventions
- Closing interventions
"""

import os
import json
import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.server.observability.intervention_interface import (
    InterventionInterface, 
    InterventionLevel,
    InterventionStatus, 
    ResponseAction,
    InterventionContext,
    InterventionRequest,
    InterventionResponse
)


@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    shutil.rmtree(temp_dir)


@pytest_asyncio.fixture
async def intervention_interface(temp_storage_path):
    """Create an InterventionInterface instance for testing."""
    config = {
        "auto_approve_level": InterventionLevel.INFORMATION,
        "default_timeout": 1,  # Short timeout for testing
        "notification_channels": ["console"],
        "storage_path": temp_storage_path,
        "require_authentication": False,
        "allowed_roles": ["operator", "admin", "supervisor"]
    }
    
    interface = InterventionInterface(config)
    await interface.initialize()
    try:
        yield interface
    finally:
        # Cleanup if needed
        if hasattr(interface, "cleanup") and callable(interface.cleanup):
            await interface.cleanup()


@pytest.fixture
def create_context():
    """Create an InterventionContext for testing."""
    def _create_context(component="test_component", action="test_action", 
                       data=None, timestamp=None):
        return InterventionContext(
            component=component,
            action=action,
            data=data or {"test_key": "test_value"},
            timestamp=timestamp or datetime.now().isoformat()
        )
    return _create_context


@pytest.mark.asyncio
class TestInterventionInterface:
    """Test cases for the InterventionInterface."""
    
    async def test_request_intervention(self, intervention_interface, create_context):
        """Test requesting an intervention."""
        context = create_context()
        
        # Create a request
        request = InterventionRequest(
            title="Test Intervention",
            description="This is a test intervention",
            level=InterventionLevel.WARNING,
            options=["approve", "reject", "modify"],
            context=context,
            require_response=True
        )
        
        # Request intervention
        intervention = await intervention_interface.request_intervention(request=request)
        
        # Check intervention details
        assert "id" in intervention
        assert intervention["status"] == InterventionStatus.PENDING
        assert intervention["request"]["title"] == "Test Intervention"
        assert intervention["request"]["description"] == "This is a test intervention"
        assert intervention["context"]["component"] == "test_component"
        assert intervention["context"]["action"] == "test_action"
        assert intervention["require_response"] is True
        
        # Check that it was saved to storage
        file_path = os.path.join(intervention_interface.config["storage_path"], f"{intervention['id']}.json")
        assert os.path.exists(file_path)
    
    async def test_auto_approve_intervention(self, intervention_interface, create_context):
        """Test auto-approval of information-level interventions."""
        context = create_context()
        
        # Create an information-level request
        request = InterventionRequest(
            title="Info Intervention",
            description="This should be auto-approved",
            level=InterventionLevel.INFORMATION,
            context=context
        )
        
        # Request intervention
        intervention = await intervention_interface.request_intervention(request=request)
        
        # Check auto-approval
        assert intervention["status"] == InterventionStatus.APPROVED
        assert "response" in intervention
        assert intervention["response"]["approved"] is True
        assert "Auto-approved" in intervention["response"]["message"]
    
    async def test_respond_to_intervention(self, intervention_interface, create_context):
        """Test responding to an intervention."""
        context = create_context()
        
        # Create a request
        request = InterventionRequest(
            title="Test Intervention",
            description="This is a test intervention",
            level=InterventionLevel.WARNING,
            context=context
        )
        
        # Request intervention
        intervention = await intervention_interface.request_intervention(request=request)
        intervention_id = intervention["id"]
        
        # Respond to intervention
        response = InterventionResponse(
            approved=True,
            message="Test approved",
            action=ResponseAction.CONTINUE,
            modifications={"key": "modified_value"}
        )
        
        updated = await intervention_interface.respond_to_intervention(intervention_id, response)
        
        # Check response details
        assert updated["status"] == InterventionStatus.MODIFIED  # Modified because we provided modifications
        assert updated["response"]["approved"] is True
        assert updated["response"]["message"] == "Test approved"
        assert updated["response"]["action"] == ResponseAction.CONTINUE.value
        assert updated["response"]["modifications"] == {"key": "modified_value"}
    
    async def test_intervention_timeout(self, intervention_interface, create_context):
        """Test intervention timeout."""
        context = create_context()
        
        # Create a request with a short timeout
        request = InterventionRequest(
            title="Timeout Test",
            description="This should time out",
            level=InterventionLevel.WARNING,
            context=context
        )
        
        # Request intervention with a 0.1 second timeout
        intervention = await intervention_interface.request_intervention(
            request=request,
            timeout=0.1
        )
        intervention_id = intervention["id"]
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Get intervention and check status
        updated = await intervention_interface.get_intervention(intervention_id)
        assert updated["status"] == InterventionStatus.TIMEOUT
        assert "timeout_at" in updated
    
    async def test_get_pending_interventions(self, intervention_interface, create_context):
        """Test retrieving pending interventions."""
        # Create multiple interventions with different roles
        interventions = []
        
        # Create pending intervention for operator
        context = create_context(component="component1")
        interventions.append(await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Operator intervention",
            context=context,
            role="operator"
        ))
        
        # Create pending intervention for admin
        context = create_context(component="component2")
        interventions.append(await intervention_interface.request_intervention(
            level=InterventionLevel.CRITICAL,
            message="Admin intervention",
            context=context,
            role="admin"
        ))
        
        # Create auto-approved intervention (should not be pending)
        context = create_context(component="component3")
        interventions.append(await intervention_interface.request_intervention(
            level=InterventionLevel.INFORMATION,
            message="Info intervention",
            context=context
        ))
        
        # Get all pending interventions
        all_pending = await intervention_interface.get_pending_interventions()
        assert len(all_pending) == 2
        
        # Get operator-specific pending interventions
        operator_pending = await intervention_interface.get_pending_interventions(role="operator")
        assert len(operator_pending) == 1
        assert operator_pending[0]["request"]["title"] == "Operator intervention"
        
        # Get admin-specific pending interventions
        admin_pending = await intervention_interface.get_pending_interventions(role="admin")
        assert len(admin_pending) == 1
        assert admin_pending[0]["request"]["title"] == "Admin intervention"
        
        # Verify that critical intervention comes first in the full list (sorted by priority)
        assert all_pending[0]["level"] == InterventionLevel.CRITICAL
    
    async def test_close_intervention(self, intervention_interface, create_context):
        """Test closing an intervention without a response."""
        context = create_context()
        
        # Create a request
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Test Close",
            context=context
        )
        intervention_id = intervention["id"]
        
        # Close intervention
        updated = await intervention_interface.close_intervention(
            intervention_id, 
            reason="No longer needed"
        )
        
        # Check status
        assert updated["status"] == InterventionStatus.CLOSED
        assert updated["closure_reason"] == "No longer needed"
        assert "closed_at" in updated
    
    async def test_save_and_load_interventions(self, intervention_interface, create_context, temp_storage_path):
        """Test saving and loading all interventions."""
        # Create multiple interventions
        context1 = create_context(component="component1")
        await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Intervention 1",
            context=context1
        )
        
        context2 = create_context(component="component2")
        await intervention_interface.request_intervention(
            level=InterventionLevel.CRITICAL,
            message="Intervention 2",
            context=context2
        )
        
        # Save all interventions to a file
        save_path = os.path.join(temp_storage_path, "all_interventions.json")
        await intervention_interface.save_interventions(save_path)
        
        # Create a new interface and load interventions
        new_interface = InterventionInterface({
            "storage_path": temp_storage_path
        })
        await new_interface.load_interventions(save_path)
        
        # Verify that interventions were loaded
        assert len(new_interface.interventions) == 2
        
        # Check that we can retrieve them
        pending = await new_interface.get_pending_interventions()
        assert len(pending) == 2  # Both WARNING and CRITICAL interventions should be pending
        # Verify they are sorted by level (CRITICAL should come first)
        assert pending[0]["level"] == InterventionLevel.CRITICAL
    
    async def test_callback_execution(self, intervention_interface, create_context):
        """Test that callbacks are executed when interventions are responded to."""
        callback_results = {"called": False, "intervention_id": None}
        
        # Define callback
        def test_callback(intervention):
            callback_results["called"] = True
            callback_results["intervention_id"] = intervention["id"]
        
        # Create intervention with callback
        context = create_context()
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Callback Test",
            context=context,
            callback=test_callback
        )
        intervention_id = intervention["id"]
        
        # Respond to intervention
        response = InterventionResponse(approved=True, message="Approved for callback test")
        await intervention_interface.respond_to_intervention(intervention_id, response)
        
        # Check that callback was executed
        assert callback_results["called"] is True
        assert callback_results["intervention_id"] == intervention_id
    
    async def test_async_callback_execution(self, intervention_interface, create_context):
        """Test that async callbacks are executed when interventions are responded to."""
        callback_results = {"called": False, "intervention_id": None}
        
        # Define async callback
        async def test_async_callback(intervention):
            callback_results["called"] = True
            callback_results["intervention_id"] = intervention["id"]
        
        # Create intervention with async callback
        context = create_context()
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Async Callback Test",
            context=context,
            callback=test_async_callback
        )
        intervention_id = intervention["id"]
        
        # Respond to intervention
        response = InterventionResponse(approved=True, message="Approved for async callback test")
        await intervention_interface.respond_to_intervention(intervention_id, response)
        
        # Wait for async callback to complete
        await asyncio.sleep(0.1)
        
        # Check that callback was executed
        assert callback_results["called"] is True
        assert callback_results["intervention_id"] == intervention_id 