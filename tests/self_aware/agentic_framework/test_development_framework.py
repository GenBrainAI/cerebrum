"""
Unit tests for the Agentic Development Framework.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
from datetime import datetime
from src.server.self_aware.agentic_framework.controller import (
    WorkerType,
    DevelopmentPhase,
    DevelopmentTask,
    WorkerCapability,
    SpecializedWorker,
    RequirementsWorker,
    PlanningWorker,
    ImplementationWorker,
    AgenticWorkflowOrchestrator
)

# Test Utilities and Fixtures
@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return MagicMock(
        generate_response=AsyncMock(return_value="Test response"),
        analyze_code=AsyncMock(return_value={"quality": 0.8, "issues": []})
    )

class TestAgenticDevelopmentFramework:
    """Test suite for the Agentic Development Framework."""
    
    @pytest.fixture
    def mock_workers(self):
        """Create mock specialized workers."""
        return {
            WorkerType.REQUIREMENTS: MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            WorkerType.PLANNING: MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            WorkerType.IMPLEMENTATION: MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            WorkerType.EVALUATION: MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            ),
            WorkerType.INTEGRATION: MagicMock(
                execute_task=AsyncMock(return_value={"status": "success"})
            )
        }
    
    @pytest.fixture
    def workflow_orchestrator(self, mock_workers, mock_llm):
        """Create AgenticWorkflowOrchestrator instance."""
        return AgenticWorkflowOrchestrator(mock_workers)
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow_orchestrator):
        """Test workflow initialization."""
        requirements = {
            "task": "Implement new feature",
            "description": "Add user authentication",
            "constraints": ["Must use JWT", "RESTful API"]
        }
        
        # Mock the _execute_phase method before starting the workflow
        async def mock_execute_phase(workflow_id: str, phase: DevelopmentPhase):
            # Do nothing to prevent phase execution during initialization test
            pass
            
        with patch.object(workflow_orchestrator, '_execute_phase', new=mock_execute_phase):
            workflow_id = await workflow_orchestrator.start_workflow(
                "test_cycle",
                requirements
            )
            
            # Verify workflow initialization
            workflow = workflow_orchestrator.active_workflows[workflow_id]
            assert workflow["id"] == workflow_id
            assert workflow["cycle_id"] == "test_cycle"
            assert workflow["requirements"] == requirements
            assert workflow["status"] == "started"
            assert workflow["current_phase"] == DevelopmentPhase.ANALYSIS.value
            assert "phases" in workflow
            assert "tasks" in workflow
            assert "artifacts" in workflow
            assert "start_time" in workflow
    
    @pytest.mark.asyncio
    async def test_requirements_phase(self, workflow_orchestrator, mock_workers):
        """Test requirements analysis phase."""
        workflow_id = "test_workflow"
        workflow_orchestrator.active_workflows[workflow_id] = {
            "id": workflow_id,
            "requirements": {"test": "requirement"},
            "phases": {},
            "tasks": []
        }
        
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.ANALYSIS
        )
        
        mock_workers[WorkerType.REQUIREMENTS].execute_task.assert_called_once()
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["phases"][DevelopmentPhase.ANALYSIS.value]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_planning_phase(self, workflow_orchestrator, mock_workers):
        """Test development planning phase."""
        workflow_id = "test_workflow"
        requirements = {
            "feature": "user_auth",
            "requirements": ["JWT support", "API endpoints"]
        }
        workflow_orchestrator.active_workflows[workflow_id] = {
            "id": workflow_id,
            "requirements": requirements,
            "phases": {},
            "tasks": []
        }
        
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.PLANNING
        )
        
        mock_workers[WorkerType.PLANNING].execute_task.assert_called_once()
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["phases"][DevelopmentPhase.PLANNING.value]["status"] == "completed"
    
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
        workflow_orchestrator.active_workflows[workflow_id] = {
            "id": workflow_id,
            "requirements": {"plan": plan},
            "phases": {},
            "tasks": []
        }
        
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.IMPLEMENTATION
        )
        
        mock_workers[WorkerType.IMPLEMENTATION].execute_task.assert_called_once()
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["phases"][DevelopmentPhase.IMPLEMENTATION.value]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_phase_transition(self, workflow_orchestrator, mock_workers):
        """Test phase transitions in workflow."""
        workflow_id = "test_workflow"
        
        # Mock _execute_phase to prevent cascading phase execution
        original_execute_phase = workflow_orchestrator._execute_phase
        
        async def controlled_execute_phase(wf_id: str, phase: DevelopmentPhase):
            """Mock that only updates phase status without triggering next phase."""
            workflow = workflow_orchestrator.active_workflows[wf_id]
            workflow["current_phase"] = phase.value
            workflow["phases"][phase.value] = {
                "status": "in_progress",
                "start_time": datetime.now().isoformat()
            }
            
            # Execute task with appropriate worker
            worker = workflow_orchestrator._get_worker_for_phase(phase)
            task = await workflow_orchestrator._create_phase_task(workflow, phase)
            result = await worker.execute_task(task)
            
            workflow["phases"][phase.value].update({
                "status": "completed",
                "completion_time": datetime.now().isoformat(),
                "results": result
            })
            
            # Don't trigger next phase automatically
        
        with patch.object(workflow_orchestrator, '_execute_phase', new=controlled_execute_phase):
            # Start workflow with controlled execution
            workflow_id = await workflow_orchestrator.start_workflow(
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
                await workflow_orchestrator._execute_phase(
                    workflow_id,
                    phase
                )
                workflow = workflow_orchestrator.active_workflows[workflow_id]
                assert workflow["phases"][phase.value]["status"] == "completed"
                assert workflow["current_phase"] == phase.value
            
            # Verify final state
            workflow = workflow_orchestrator.active_workflows[workflow_id]
            assert workflow["current_phase"] == DevelopmentPhase.EVALUATION.value
            assert all(workflow["phases"][phase.value]["status"] == "completed" for phase in phases)
    
    @pytest.mark.asyncio
    async def test_worker_error_handling(self, workflow_orchestrator, mock_workers):
        """Test error handling in worker execution."""
        workflow_id = "test_workflow"
        mock_workers[WorkerType.REQUIREMENTS].execute_task.side_effect = \
            Exception("Worker failed")
        
        workflow_orchestrator.active_workflows[workflow_id] = {
            "id": workflow_id,
            "requirements": {},
            "phases": {},
            "tasks": []
        }
        
        await workflow_orchestrator._execute_phase(
            workflow_id,
            DevelopmentPhase.ANALYSIS
        )
        
        workflow = workflow_orchestrator.active_workflows[workflow_id]
        assert workflow["phases"][DevelopmentPhase.ANALYSIS.value]["status"] == "failed"
        assert workflow["status"] == "failed" 