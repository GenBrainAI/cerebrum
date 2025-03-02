import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.server.self_aware_integration import SelfAwareSystem
from src.server.system.cognitive_loop import (
    CognitiveLoopOrchestrator, 
    WorkerType, 
    RequirementsWorker,
    PlanningWorker,
    ImplementationWorker,
    EvaluationWorker
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_components():
    """Create mock components for the SelfAwareSystem."""
    # Create mock components
    mock_parameter_manager = MagicMock()
    mock_parameter_manager.initialize = AsyncMock()
    
    mock_knowledge_system = MagicMock()
    mock_knowledge_system.initialize = AsyncMock()
    
    mock_cognitive_orchestrator = MagicMock()
    mock_cognitive_orchestrator.initialize = AsyncMock()
    mock_cognitive_orchestrator.register_worker = AsyncMock()
    
    mock_code_generator = MagicMock()
    mock_safety_validator = MagicMock()
    mock_test_runner = MagicMock()
    
    return {
        "parameter_manager": mock_parameter_manager,
        "knowledge_system": mock_knowledge_system,
        "cognitive_orchestrator": mock_cognitive_orchestrator,
        "code_generator": mock_code_generator,
        "safety_validator": mock_safety_validator,
        "test_runner": mock_test_runner
    }

@pytest.mark.asyncio
async def test_self_aware_system_initialization(temp_dir, mock_components):
    """Test initializing the SelfAwareSystem."""
    storage_path = os.path.join(temp_dir, "self_aware")
    
    # Patch the necessary components
    with patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_components["parameter_manager"]), \
         patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_components["knowledge_system"]), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_components["cognitive_orchestrator"]), \
         patch('src.server.self_aware_integration.CodeGenerator', return_value=mock_components["code_generator"]), \
         patch('src.server.self_aware_integration.SafetyValidator', return_value=mock_components["safety_validator"]), \
         patch('src.server.self_aware_integration.TestRunner', return_value=mock_components["test_runner"]), \
         patch('src.server.self_aware_integration.SelfAwareSystem.register_specialized_workers', new_callable=AsyncMock):
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Initialize the system
        await system.initialize()
        
        # Check that all components were initialized
        mock_components["parameter_manager"].initialize.assert_called_once()
        mock_components["knowledge_system"].initialize.assert_called_once()
        mock_components["cognitive_orchestrator"].initialize.assert_called_once()
        system.register_specialized_workers.assert_called_once()
        
        # Check that the storage path was created
        assert os.path.exists(storage_path)

@pytest.mark.asyncio
async def test_register_specialized_workers(temp_dir, mock_components):
    """Test registering specialized workers with the cognitive orchestrator."""
    storage_path = os.path.join(temp_dir, "self_aware")
    
    # Create mock worker instances
    mock_requirements_worker = MagicMock(spec=RequirementsWorker)
    mock_planning_worker = MagicMock(spec=PlanningWorker)
    mock_implementation_worker = MagicMock(spec=ImplementationWorker)
    mock_evaluation_worker = MagicMock(spec=EvaluationWorker)
    
    # Patch the worker classes to return our mock instances
    with patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_components["parameter_manager"]), \
         patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_components["knowledge_system"]), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_components["cognitive_orchestrator"]), \
         patch('src.server.self_aware_integration.CodeGenerator', return_value=mock_components["code_generator"]), \
         patch('src.server.self_aware_integration.SafetyValidator', return_value=mock_components["safety_validator"]), \
         patch('src.server.self_aware_integration.TestRunner', return_value=mock_components["test_runner"]), \
         patch('src.server.self_aware_integration.RequirementsWorker', return_value=mock_requirements_worker), \
         patch('src.server.self_aware_integration.PlanningWorker', return_value=mock_planning_worker), \
         patch('src.server.self_aware_integration.ImplementationWorker', return_value=mock_implementation_worker), \
         patch('src.server.self_aware_integration.EvaluationWorker', return_value=mock_evaluation_worker):
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Call register_specialized_workers directly
        await system.register_specialized_workers()
        
        # Check that all workers were registered with the cognitive orchestrator
        assert mock_components["cognitive_orchestrator"].register_worker.call_count == 4
        
        # Check that each worker type was registered
        mock_components["cognitive_orchestrator"].register_worker.assert_any_call(
            worker_type=WorkerType.REQUIREMENTS,
            worker=mock_requirements_worker
        )
        mock_components["cognitive_orchestrator"].register_worker.assert_any_call(
            worker_type=WorkerType.PLANNING,
            worker=mock_planning_worker
        )
        mock_components["cognitive_orchestrator"].register_worker.assert_any_call(
            worker_type=WorkerType.IMPLEMENTATION,
            worker=mock_implementation_worker
        )
        mock_components["cognitive_orchestrator"].register_worker.assert_any_call(
            worker_type=WorkerType.EVALUATION,
            worker=mock_evaluation_worker
        )

@pytest.mark.asyncio
async def test_worker_initialization(temp_dir, mock_components):
    """Test that workers are initialized with the correct dependencies."""
    storage_path = os.path.join(temp_dir, "self_aware")
    
    # Patch the worker classes to check their initialization
    with patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_components["parameter_manager"]), \
         patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_components["knowledge_system"]), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_components["cognitive_orchestrator"]), \
         patch('src.server.self_aware_integration.CodeGenerator', return_value=mock_components["code_generator"]), \
         patch('src.server.self_aware_integration.SafetyValidator', return_value=mock_components["safety_validator"]), \
         patch('src.server.self_aware_integration.TestRunner', return_value=mock_components["test_runner"]), \
         patch('src.server.self_aware_integration.RequirementsWorker') as mock_requirements_worker_class, \
         patch('src.server.self_aware_integration.PlanningWorker') as mock_planning_worker_class, \
         patch('src.server.self_aware_integration.ImplementationWorker') as mock_implementation_worker_class, \
         patch('src.server.self_aware_integration.EvaluationWorker') as mock_evaluation_worker_class:
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Call register_specialized_workers directly
        await system.register_specialized_workers()
        
        # Check that each worker was initialized with the correct dependencies
        mock_requirements_worker_class.assert_called_once_with(
            knowledge_system=mock_components["knowledge_system"],
            parameter_manager=mock_components["parameter_manager"]
        )
        
        mock_planning_worker_class.assert_called_once_with(
            knowledge_system=mock_components["knowledge_system"],
            parameter_manager=mock_components["parameter_manager"]
        )
        
        mock_implementation_worker_class.assert_called_once_with(
            knowledge_system=mock_components["knowledge_system"],
            parameter_manager=mock_components["parameter_manager"],
            code_generator=mock_components["code_generator"],
            safety_validator=mock_components["safety_validator"]
        )
        
        mock_evaluation_worker_class.assert_called_once_with(
            knowledge_system=mock_components["knowledge_system"],
            parameter_manager=mock_components["parameter_manager"],
            test_runner=mock_components["test_runner"]
        )

@pytest.mark.asyncio
async def test_initialization_error_handling(temp_dir):
    """Test error handling during initialization."""
    storage_path = os.path.join(temp_dir, "self_aware")
    
    # Create a mock parameter manager that raises an exception during initialization
    mock_parameter_manager = MagicMock()
    mock_parameter_manager.initialize = AsyncMock(side_effect=Exception("Test error"))
    
    # Patch the necessary components
    with patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_parameter_manager), \
         pytest.raises(Exception) as excinfo:
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Initialize the system
        await system.initialize()
    
    # Check that the exception was raised
    assert "Test error" in str(excinfo.value)
    
    # Check that the storage path was still created
    assert os.path.exists(storage_path)

@pytest.mark.asyncio
async def test_component_dependencies(temp_dir, mock_components):
    """Test that components are initialized in the correct order with proper dependencies."""
    storage_path = os.path.join(temp_dir, "self_aware")
    
    # Track initialization order
    init_order = []
    
    # Override the initialize methods to track order
    async def parameter_manager_init():
        init_order.append("parameter_manager")
    
    async def knowledge_system_init():
        init_order.append("knowledge_system")
    
    async def cognitive_orchestrator_init():
        init_order.append("cognitive_orchestrator")
    
    mock_components["parameter_manager"].initialize.side_effect = parameter_manager_init
    mock_components["knowledge_system"].initialize.side_effect = knowledge_system_init
    mock_components["cognitive_orchestrator"].initialize.side_effect = cognitive_orchestrator_init
    
    # Patch the necessary components
    with patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_components["parameter_manager"]), \
         patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_components["knowledge_system"]), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_components["cognitive_orchestrator"]), \
         patch('src.server.self_aware_integration.SelfAwareSystem.register_specialized_workers', new_callable=AsyncMock):
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Initialize the system
        await system.initialize()
        
        # Check initialization order
        assert init_order == ["parameter_manager", "knowledge_system", "cognitive_orchestrator"]
        
        # Check that register_specialized_workers was called after all components were initialized
        system.register_specialized_workers.assert_called_once() 