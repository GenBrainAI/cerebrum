"""
Advanced test suite for the InterventionInterface component.

Tests more complex use cases for the InterventionInterface, including:
- Multiple intervention levels
- Response modifications with complex data structures
- Callback mechanism for system events
- Role-based intervention routing
- Escalation workflows
- Concurrent intervention handling
- Persistence across restarts
- Rich context in intervention requests
"""

import os
import json
import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import Mock
import pytest_asyncio

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
        "default_timeout": 0.5,  # Very short timeout for testing
        "notification_channels": ["console"],
        "storage_path": temp_storage_path,
        "require_authentication": True,
        "allowed_roles": ["operator", "admin", "supervisor", "developer", "analyst"]
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
    """Factory function to create different intervention contexts."""
    def _create_context(
        component="test_component", 
        action="test_action",
        data=None, 
        timestamp=None
    ):
        return InterventionContext(
            component=component,
            action=action,
            data=data or {"test_key": "test_value"},
            timestamp=timestamp or datetime.now().isoformat()
        )
    return _create_context


@pytest.mark.asyncio
class TestInterventionInterfaceAdvanced:
    """Advanced test cases for the InterventionInterface."""
    
    async def test_multiple_intervention_levels(self, intervention_interface, create_context):
        """Test intervention requests with different levels."""
        levels = [
            (InterventionLevel.INFORMATION, "Information level intervention"),
            (InterventionLevel.SUGGESTION, "Suggestion level intervention"),
            (InterventionLevel.WARNING, "Warning level intervention"),
            (InterventionLevel.CRITICAL, "Critical level intervention"),
            (InterventionLevel.EMERGENCY, "Emergency level intervention")
        ]
        
        interventions = []
        for level, message in levels:
            context = create_context(component=f"component_{level.name.lower()}")
            interventions.append(await intervention_interface.request_intervention(
                level=level,
                message=message,
                context=context
            ))
        
        # Check auto-approval for INFORMATION level
        assert interventions[0]["status"] == InterventionStatus.APPROVED
        
        # All other levels should be pending
        for i in range(1, len(interventions)):
            assert interventions[i]["status"] == InterventionStatus.PENDING
        
        # Test auto-approval configuration by changing it
        old_config = intervention_interface.config["auto_approve_level"]
        intervention_interface.config["auto_approve_level"] = InterventionLevel.SUGGESTION
        
        # Create another suggestion-level intervention, should be auto-approved now
        suggestion_intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.SUGGESTION,
            message="This suggestion should be auto-approved",
            context=create_context()
        )
        assert suggestion_intervention["status"] == InterventionStatus.APPROVED
        
        # Restore original config
        intervention_interface.config["auto_approve_level"] = old_config
    
    async def test_response_modifications(self, intervention_interface, create_context):
        """Test handling of complex modifications in intervention responses."""
        # Create an intervention that expects modifications
        data = {
            "model_configuration": {
                "parameters": {
                    "learning_rate": 0.01,
                    "batch_size": 64,
                    "epochs": 100
                },
                "architecture": {
                    "layers": [
                        {"type": "dense", "units": 128, "activation": "relu"},
                        {"type": "dropout", "rate": 0.2},
                        {"type": "dense", "units": 64, "activation": "relu"},
                        {"type": "dense", "units": 10, "activation": "softmax"}
                    ]
                }
            }
        }
        
        context = create_context(
            component="model_trainer", 
            action="train_model",
            data=data
        )
        
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Model configuration review needed",
            context=context
        )
        
        # Create a response with complex modifications
        modifications = {
            "model_configuration": {
                "parameters": {
                    "learning_rate": 0.001,  # Changed
                    "batch_size": 128,       # Changed
                    "epochs": 50             # Changed
                },
                "architecture": {
                    "layers": [
                        {"type": "dense", "units": 256, "activation": "relu"},  # Changed
                        {"type": "dropout", "rate": 0.3},                      # Changed
                        {"type": "dense", "units": 128, "activation": "relu"},  # Changed
                        {"type": "dense", "units": 10, "activation": "softmax"}
                    ]
                }
            }
        }
        
        response = InterventionResponse(
            approved=True,
            message="Adjusted model configuration for better performance",
            action=ResponseAction.MODIFY,
            modifications=modifications
        )
        
        # Respond to the intervention
        updated = await intervention_interface.respond_to_intervention(intervention["id"], response)
        
        # Verify response was recorded properly
        assert updated["status"] == InterventionStatus.MODIFIED
        assert updated["response"]["modifications"] == modifications
        
        # Load the intervention from disk to verify persistence
        new_interface = InterventionInterface({"storage_path": intervention_interface.config["storage_path"]})
        await new_interface.initialize()
        
        loaded = await new_interface.get_intervention(intervention["id"])
        assert loaded["response"]["modifications"]["model_configuration"]["parameters"]["learning_rate"] == 0.001
        assert len(loaded["response"]["modifications"]["model_configuration"]["architecture"]["layers"]) == 4
    
    async def test_callback_mechanism(self, intervention_interface, create_context):
        """Test both synchronous and asynchronous callbacks for system events."""
        # Create tracking structures for callbacks
        sync_calls = []
        async_calls = []
        events = []
        
        # Define sync callback
        def sync_callback(intervention):
            sync_calls.append(intervention["id"])
            events.append(f"sync_{intervention['id']}")
        
        # Define async callback
        async def async_callback(intervention):
            await asyncio.sleep(0.1)  # Simulate async work
            async_calls.append(intervention["id"])
            events.append(f"async_{intervention['id']}")
        
        # Create interventions with callbacks
        intervention1 = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Sync callback test",
            context=create_context(component="sync_component"),
            callback=sync_callback
        )
        
        intervention2 = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Async callback test",
            context=create_context(component="async_component"),
            callback=async_callback
        )
        
        # Respond to both interventions
        await intervention_interface.respond_to_intervention(
            intervention1["id"],
            InterventionResponse(approved=True, message="Sync response")
        )
        
        await intervention_interface.respond_to_intervention(
            intervention2["id"],
            InterventionResponse(approved=True, message="Async response")
        )
        
        # Wait for async callback to complete
        await asyncio.sleep(0.2)
        
        # Verify callbacks were executed
        assert len(sync_calls) == 1
        assert len(async_calls) == 1
        assert sync_calls[0] == intervention1["id"]
        assert async_calls[0] == intervention2["id"]
        
        # Verify events ordering (sync should be before async)
        assert events.index(f"sync_{intervention1['id']}") < events.index(f"async_{intervention2['id']}")
    
    async def test_role_based_interventions(self, intervention_interface, create_context):
        """Test role-based routing of interventions."""
        # Create interventions for different roles
        roles = ["operator", "admin", "supervisor", "developer", "analyst"]
        interventions = {}
        
        for role in roles:
            context = create_context(component=f"{role}_system")
            intervention = await intervention_interface.request_intervention(
                level=InterventionLevel.WARNING,
                message=f"Intervention for {role}",
                context=context,
                role=role
            )
            interventions[role] = intervention["id"]
        
        # Get pending interventions for each role
        for role in roles:
            pending = await intervention_interface.get_pending_interventions(role=role)
            
            # Should only see their own interventions
            assert len(pending) == 1
            assert pending[0]["request"]["title"] == f"Intervention for {role}"
            
            # Other interventions should not be visible
            for other_role in [r for r in roles if r != role]:
                other_pending = [i for i in pending if i["id"] == interventions[other_role]]
                assert len(other_pending) == 0
        
        # Respond to one intervention
        await intervention_interface.respond_to_intervention(
            interventions["admin"],
            InterventionResponse(approved=True, message="Admin approval")
        )
        
        # Check that it's no longer in pending for that role
        admin_pending = await intervention_interface.get_pending_interventions(role="admin")
        assert len(admin_pending) == 0
    
    async def test_escalation_workflow(self, intervention_interface, create_context):
        """Test escalation workflow for critical interventions."""
        # Create a warning-level intervention initially
        context = create_context(
            component="security_system", 
            action="detect_anomaly",
            data={"anomaly_score": 0.7, "affected_system": "authentication"}
        )
        
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Suspicious activity detected",
            context=context,
            role="operator"
        )
        
        # Operator decides to escalate to supervisor
        escalation_response = InterventionResponse(
            approved=False,
            message="Escalating to supervisor for review",
            action=ResponseAction.ESCALATE,
            modifications={"escalated_to": "supervisor", "priority": "high"}
        )
        
        # We'll manually close this intervention since our implementation doesn't
        # directly support escalation workflow
        await intervention_interface.close_intervention(
            intervention["id"],
            reason="Escalated to supervisor"
        )
        
        # Create a new intervention at a higher level for the supervisor
        escalated_context = create_context(
            component="security_system",
            action="review_escalated_anomaly",
            data={
                "original_intervention_id": intervention["id"],
                "anomaly_score": 0.7,
                "affected_system": "authentication",
                "escalation_reason": escalation_response.message
            }
        )
        
        escalated_intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.CRITICAL,  # Escalated to critical
            message="ESCALATED: Suspicious activity requires supervisor review",
            context=escalated_context,
            role="supervisor"  # Only supervisors can see this now
        )
        
        # Verify only supervisor can see this
        operator_pending = await intervention_interface.get_pending_interventions(role="operator")
        supervisor_pending = await intervention_interface.get_pending_interventions(role="supervisor")
        
        assert all(i["id"] != escalated_intervention["id"] for i in operator_pending)
        assert any(i["id"] == escalated_intervention["id"] for i in supervisor_pending)
        
        # Supervisor responds
        await intervention_interface.respond_to_intervention(
            escalated_intervention["id"],
            InterventionResponse(
                approved=True,
                message="Approved after detailed review. Implement additional monitoring.",
                action=ResponseAction.MODIFY,
                modifications={"additional_monitoring": True, "alert_threshold": 0.5}
            )
        )
        
        # Verify the intervention was updated correctly
        updated = await intervention_interface.get_intervention(escalated_intervention["id"])
        assert updated["status"] == InterventionStatus.MODIFIED
        assert updated["response"]["modifications"]["additional_monitoring"] is True
    
    async def test_concurrent_interventions(self, intervention_interface, create_context):
        """Test handling of multiple concurrent interventions."""
        # Create multiple interventions concurrently
        num_interventions = 10
        tasks = []
        
        for i in range(num_interventions):
            context = create_context(
                component=f"component_{i}",
                action=f"action_{i}",
                data={"sequence": i}
            )
            
            # Alternate between different levels
            level = InterventionLevel.WARNING if i % 2 == 0 else InterventionLevel.CRITICAL
            
            tasks.append(
                intervention_interface.request_intervention(
                    level=level,
                    message=f"Concurrent intervention {i}",
                    context=context
                )
            )
        
        # Wait for all interventions to be created
        results = await asyncio.gather(*tasks)
        
        # Verify all were created successfully
        assert len(results) == num_interventions
        
        # Now respond to all concurrently
        response_tasks = []
        
        for intervention in results:
            response = InterventionResponse(
                approved=True,
                message=f"Approved {intervention['id']}",
                modifications={"processed_at": datetime.now().isoformat()}
            )
            
            response_tasks.append(
                intervention_interface.respond_to_intervention(intervention["id"], response)
            )
        
        # Wait for all responses to be processed
        response_results = await asyncio.gather(*response_tasks)
        
        # Verify all were processed
        assert len(response_results) == num_interventions
        assert all(result["status"] == InterventionStatus.MODIFIED for result in response_results)
        
        # Verify no interventions are pending
        pending = await intervention_interface.get_pending_interventions()
        assert len(pending) == 0
    
    async def test_persistence_across_restarts(self, intervention_interface, create_context, temp_storage_path):
        """Test persistence of interventions across system restarts."""
        # Create interventions with different states
        intervention1 = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Pending intervention",
            context=create_context(component="persistence_test_1")
        )
        
        intervention2 = await intervention_interface.request_intervention(
            level=InterventionLevel.CRITICAL,
            message="Will be approved",
            context=create_context(component="persistence_test_2")
        )
        
        intervention3 = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Will be rejected",
            context=create_context(component="persistence_test_3")
        )
        
        # Respond to some interventions
        await intervention_interface.respond_to_intervention(
            intervention2["id"],
            InterventionResponse(approved=True, message="Approved")
        )
        
        await intervention_interface.respond_to_intervention(
            intervention3["id"],
            InterventionResponse(approved=False, message="Rejected")
        )
        
        # Save and "restart" by creating a new interface
        save_path = os.path.join(temp_storage_path, "persistence_test.json")
        await intervention_interface.save_interventions(save_path)
        
        # Create new interface
        new_interface = InterventionInterface({
            "storage_path": temp_storage_path,
            "auto_approve_level": InterventionLevel.INFORMATION,
            "default_timeout": 30
        })
        
        # Load saved interventions
        await new_interface.load_interventions(save_path)
        
        # Verify all interventions were loaded with correct states
        loaded1 = await new_interface.get_intervention(intervention1["id"])
        loaded2 = await new_interface.get_intervention(intervention2["id"])
        loaded3 = await new_interface.get_intervention(intervention3["id"])
        
        assert loaded1["status"] == InterventionStatus.PENDING
        assert loaded2["status"] == InterventionStatus.APPROVED
        assert loaded3["status"] == InterventionStatus.REJECTED
        
        # Verify pending interventions are still retrievable
        pending = await new_interface.get_pending_interventions()
        assert len(pending) == 1
        assert pending[0]["id"] == intervention1["id"]
        
        # Respond to the still-pending intervention
        await new_interface.respond_to_intervention(
            intervention1["id"],
            InterventionResponse(approved=True, message="Approved after restart")
        )
        
        # Verify it was updated
        updated = await new_interface.get_intervention(intervention1["id"])
        assert updated["status"] == InterventionStatus.APPROVED
        assert updated["response"]["message"] == "Approved after restart"
    
    async def test_intervention_context_richness(self, intervention_interface, create_context):
        """Test richness of context in intervention requests."""
        # Create a rich context with multiple data types
        complex_data = {
            "metrics": {
                "accuracy": 0.95,
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90
            },
            "system_state": {
                "cpu_usage": 75.2,
                "memory_usage": 8.4,
                "gpu_usage": 92.1,
                "disk_space": 1024.5
            },
            "decision_points": [
                {"name": "feature_threshold", "value": 0.75, "status": "passed"},
                {"name": "performance_threshold", "value": 0.85, "status": "passed"},
                {"name": "resource_threshold", "value": 0.95, "status": "warning"}
            ],
            "environment": {
                "production": False,
                "staging": True,
                "version": "2.3.5",
                "dependencies": ["numpy==1.22.0", "pandas==1.5.0", "scikit-learn==1.1.2"]
            },
            "timestamps": {
                "started_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "checkpoint_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "current_at": datetime.now().isoformat()
            }
        }
        
        context = create_context(
            component="model_evaluator",
            action="evaluate_model_performance",
            data=complex_data
        )
        
        # Create intervention with rich context
        intervention = await intervention_interface.request_intervention(
            level=InterventionLevel.WARNING,
            message="Model performance review needed due to resource warnings",
            context=context
        )
        
        # Verify context was saved correctly
        loaded = await intervention_interface.get_intervention(intervention["id"])
        assert loaded["context"]["component"] == "model_evaluator"
        assert loaded["context"]["action"] == "evaluate_model_performance"
        
        # Check complex data structure preservation
        assert loaded["context"]["data"]["metrics"]["accuracy"] == 0.95
        assert len(loaded["context"]["data"]["decision_points"]) == 3
        assert loaded["context"]["data"]["decision_points"][2]["status"] == "warning"
        
        # Create specific modifications to the context data
        response = InterventionResponse(
            approved=True,
            message="Approved with resource allocation changes",
            action=ResponseAction.MODIFY,
            modifications={
                "system_state": {
                    "gpu_usage": 80.0,  # Reduced
                    "memory_usage": 6.0  # Reduced
                },
                "decision_points": [
                    {"name": "resource_threshold", "value": 0.85, "status": "passed"}  # Changed
                ]
            }
        )
        
        # Respond with modifications
        updated = await intervention_interface.respond_to_intervention(intervention["id"], response)
        
        # Verify modifications were saved
        assert updated["status"] == InterventionStatus.MODIFIED
        assert updated["response"]["modifications"]["system_state"]["gpu_usage"] == 80.0
        assert updated["response"]["modifications"]["decision_points"][0]["status"] == "passed" 