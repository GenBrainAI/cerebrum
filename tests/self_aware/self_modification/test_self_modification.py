"""
Unit tests for Self-Modification Integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
from datetime import datetime
from src.server.self_modification.integration.self_modification import (
    ModificationType,
    ModificationRequest,
    ModificationStatus,
    SelfModificationIntegration
)

class TestSelfModificationIntegration:
    """Test suite for Self-Modification Integration."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components."""
        return {
            "code_generator": MagicMock(
                generate_code=AsyncMock(return_value={
                    "files": {"test.py": "def test(): pass"}
                })
            ),
            "safety_validator": MagicMock(
                validate_code=AsyncMock(return_value={
                    "passed": True,
                    "issues": []
                })
            ),
            "integration_manager": MagicMock(
                apply_changes=AsyncMock(return_value={"success": True}),
                rollback_changes=AsyncMock(return_value={"success": True})
            ),
            "agentic_controller": MagicMock(
                analyze_modification=AsyncMock(return_value={
                    "risk_level": "low",
                    "impact_areas": []
                })
            ),
            "system_access": MagicMock()
        }
    
    @pytest.fixture
    def self_modification(self, mock_components):
        """Create SelfModificationIntegration instance."""
        return SelfModificationIntegration(**mock_components)
    
    @pytest.fixture
    def test_request(self):
        """Create a test modification request."""
        return ModificationRequest(
            modification_type=ModificationType.CODE_CHANGE,
            description="Test modification",
            target_components=["test"],
            requirements={},
            priority=1,
            estimated_impact={},
            context={}
        )
    
    @pytest.mark.asyncio
    async def test_modification_workflow(self, self_modification,
                                      mock_components, test_request):
        """Test complete modification workflow."""
        # Propose modification
        proposal = await self_modification.propose_modification(test_request)
        assert proposal["modification_id"]
        assert "next_steps" in proposal
        
        # Execute modification
        result = await self_modification.execute_modification(
            proposal["modification_id"]
        )
        
        # Verify component calls
        mock_components["agentic_controller"].analyze_modification.assert_called_once()
        mock_components["code_generator"].generate_code.assert_called_once()
        mock_components["safety_validator"].validate_code.assert_called_once()
        mock_components["integration_manager"].apply_changes.assert_called_once()
        
        # Verify result
        assert result["status"] == ModificationStatus.COMPLETED
        assert len(self_modification.modification_history) == 1
    
    @pytest.mark.asyncio
    async def test_safety_gate_checks(self, self_modification, test_request):
        """Test safety gate validation."""
        # Propose modification
        proposal = await self_modification.propose_modification(test_request)
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        
        # Test pre-generation gates
        await self_modification._check_safety_gates(
            "pre_generation",
            modification
        )
        
        # Test post-generation gates
        await self_modification._check_safety_gates(
            "post_generation",
            modification
        )
        
        # Test pre-integration gates
        await self_modification._check_safety_gates(
            "pre_integration",
            modification
        )
        
        # Test post-integration gates
        await self_modification._check_safety_gates(
            "post_integration",
            modification
        )
    
    @pytest.mark.asyncio
    async def test_modification_failure_handling(self, self_modification,
                                              mock_components, test_request):
        """Test handling of modification failures."""
        # Setup mock to fail
        mock_components["code_generator"].generate_code.side_effect = \
            Exception("Generation failed")
        
        # Propose modification
        proposal = await self_modification.propose_modification(test_request)
        
        # Execute and expect failure
        with pytest.raises(Exception):
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        # Verify failure handling
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.FAILED
        
        # Verify timeline
        timeline = modification["timeline"]
        assert any(t["status"] == ModificationStatus.FAILED for t in timeline)
    
    @pytest.mark.asyncio
    async def test_rollback_procedure(self, self_modification,
                                    mock_components, test_request):
        """Test modification rollback procedure."""
        # Setup mock to fail during integration
        mock_components["integration_manager"].apply_changes.side_effect = \
            Exception("Integration failed")
        
        # Propose modification
        proposal = await self_modification.propose_modification(test_request)
        
        # Execute and expect failure
        with pytest.raises(Exception):
            await self_modification.execute_modification(
                proposal["modification_id"]
            )
        
        # Verify rollback
        mock_components["integration_manager"].rollback_changes.assert_called_once()
        
        modification = self_modification.active_modifications[
            proposal["modification_id"]
        ]
        assert modification["status"] == ModificationStatus.ROLLED_BACK
        
        # Verify timeline
        timeline = modification["timeline"]
        assert any(t["status"] == ModificationStatus.ROLLED_BACK for t in timeline)
    
    @pytest.mark.asyncio
    async def test_modification_status_transitions(self, self_modification,
                                                test_request):
        """Test modification status transitions."""
        # Propose modification
        proposal = await self_modification.propose_modification(test_request)
        modification_id = proposal["modification_id"]
        
        # Get initial status
        modification = self_modification.active_modifications[modification_id]
        timeline = modification["timeline"]
        
        # Verify status transitions
        status_sequence = [
            ModificationStatus.PROPOSED,
            ModificationStatus.ANALYZING,
            ModificationStatus.GENERATING,
            ModificationStatus.VALIDATING,
            ModificationStatus.INTEGRATING,
            ModificationStatus.COMPLETED
        ]
        
        # Execute modification
        await self_modification.execute_modification(modification_id)
        
        # Verify timeline contains all status transitions
        timeline_statuses = [t["status"] for t in timeline]
        for status in status_sequence:
            assert status in timeline_statuses
    
    def test_safety_gates_initialization(self, self_modification):
        """Test safety gates initialization."""
        gates = self_modification.safety_gates
        
        # Verify all gate phases exist
        assert "pre_generation" in gates
        assert "post_generation" in gates
        assert "pre_integration" in gates
        assert "post_integration" in gates
        
        # Verify gate types
        for phase in gates.values():
            assert isinstance(phase, dict)
            assert all(isinstance(enabled, bool) for enabled in phase.values())
    
    @pytest.mark.asyncio
    async def test_concurrent_modifications(self, self_modification, test_request):
        """Test handling of concurrent modifications."""
        # Create multiple modification requests
        requests = [
            test_request,
            ModificationRequest(
                modification_type=ModificationType.REFACTOR,
                description="Concurrent modification",
                target_components=["other"],
                requirements={},
                priority=2,
                estimated_impact={},
                context={}
            )
        ]
        
        # Execute modifications concurrently
        proposals = await asyncio.gather(*[
            self_modification.propose_modification(req)
            for req in requests
        ])
        
        # Verify each modification has unique ID
        modification_ids = [p["modification_id"] for p in proposals]
        assert len(set(modification_ids)) == len(requests)
        
        # Execute modifications
        results = await asyncio.gather(*[
            self_modification.execute_modification(mod_id)
            for mod_id in modification_ids
        ])
        
        # Verify all completed successfully
        assert all(r["status"] == ModificationStatus.COMPLETED for r in results)
        
        # Verify history contains all modifications
        assert len(self_modification.modification_history) == len(requests) 