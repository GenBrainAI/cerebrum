import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Patch all required modules before importing SelfAwareSystem
import sys
from unittest import mock

# Mock Component Analyzer
class MockComponentAnalyzer:
    def __init__(self, knowledge_system=None):
        self.knowledge_system = knowledge_system
        
    async def analyze_component(self, component_path):
        return {"mock": "analysis"}

# Mock ResourceOptimizer
class MockResourceOptimizer:
    def __init__(self, knowledge_system=None, resource_monitor=None, telemetry_system=None):
        self.knowledge_system = knowledge_system
        self.resource_monitor = resource_monitor
        self.telemetry_system = telemetry_system
        self.resource_usage_stats = {}
        self.resource_allocations = {}
        self.optimization_history = []
        
    async def optimize_resource(self, component, resource_type):
        return {"optimization": "result"}

# Mock InteractionAnalyzer
class MockInteractionAnalyzer:
    def __init__(self, knowledge_system=None, component_analyzer=None):
        self.knowledge_system = knowledge_system
        self.component_analyzer = component_analyzer
        
    async def analyze_interaction(self, component_a, component_b):
        return {"interaction": "analysis"}

# Mock WorkflowOptimizer
class MockWorkflowOptimizer:
    def __init__(self, knowledge_system=None, goal_decomposition_engine=None):
        self.knowledge_system = knowledge_system
        self.goal_decomposition_engine = goal_decomposition_engine
        
    async def optimize_workflow(self, workflow_name):
        return {"workflow": "optimized"}

# Mock CodeParser
class MockCodeParser:
    def __init__(self):
        pass
        
    async def parse_file(self, file_path):
        return {"ast": "mock_ast", "imports": [], "functions": [], "classes": []}

# Mock ComplexityAnalyzer
class MockComplexityAnalyzer:
    def __init__(self):
        pass
        
    async def analyze_file(self, file_path):
        return {"cyclomatic_complexity": 5, "cognitive_complexity": 3}

# Mock DependencyMapper
class MockDependencyMapper:
    def __init__(self, code_parser=None):
        self.code_parser = code_parser
        
    async def map_dependencies(self, component_path):
        return {"dependencies": {}, "reverse_dependencies": {}}

# Mock BehaviorMonitor
class MockBehaviorMonitor:
    def __init__(self, telemetry_system=None):
        self.telemetry_system = telemetry_system
        
    async def start_monitoring(self, components=None):
        return "mock_session_id"

# Mock AnomalyDetector
class MockAnomalyDetector:
    def __init__(self, telemetry_collector=None):
        self.telemetry_collector = telemetry_collector
        
    async def detect_anomalies(self, time_period=None):
        return {"anomalies": []}

# Mock PerformanceAnalyzer
class MockPerformanceAnalyzer:
    def __init__(self, telemetry_collector=None):
        self.telemetry_collector = telemetry_collector
        
    async def analyze_performance(self, component=None, time_period=None):
        return {"performance_metrics": {}, "bottlenecks": []}

# Mock TelemetryCollector
class MockTelemetryCollector:
    def __init__(self):
        pass
        
    async def collect_telemetry(self, component=None, metric_type=None):
        return {"telemetry": "data"}

# Apply all patches
sys.modules['src.server.introspection.component_analysis.analyzer'] = mock.MagicMock()
sys.modules['src.server.introspection.component_analysis.analyzer'].ComponentAnalyzer = MockComponentAnalyzer

sys.modules['src.server.integration_optimization.resource_optimizer'] = mock.MagicMock()
sys.modules['src.server.integration_optimization.resource_optimizer'].ResourceOptimizer = MockResourceOptimizer

sys.modules['src.server.integration_optimization.interaction_analyzer'] = mock.MagicMock()
sys.modules['src.server.integration_optimization.interaction_analyzer'].InteractionAnalyzer = MockInteractionAnalyzer

sys.modules['src.server.integration_optimization.workflow_optimizer'] = mock.MagicMock()
sys.modules['src.server.integration_optimization.workflow_optimizer'].WorkflowOptimizer = MockWorkflowOptimizer

sys.modules['src.server.introspection.component_analysis.code_parser'] = mock.MagicMock()
sys.modules['src.server.introspection.component_analysis.code_parser'].CodeParser = MockCodeParser

sys.modules['src.server.introspection.component_analysis.complexity_analyzer'] = mock.MagicMock()
sys.modules['src.server.introspection.component_analysis.complexity_analyzer'].ComplexityAnalyzer = MockComplexityAnalyzer

sys.modules['src.server.introspection.component_analysis.dependency_mapper'] = mock.MagicMock()
sys.modules['src.server.introspection.component_analysis.dependency_mapper'].DependencyMapper = MockDependencyMapper

sys.modules['src.server.introspection.runtime_monitoring.behavior_monitor'] = mock.MagicMock()
sys.modules['src.server.introspection.runtime_monitoring.behavior_monitor'].BehaviorMonitor = MockBehaviorMonitor

sys.modules['src.server.introspection.runtime_monitoring.anomaly_detector'] = mock.MagicMock()
sys.modules['src.server.introspection.runtime_monitoring.anomaly_detector'].AnomalyDetector = MockAnomalyDetector

sys.modules['src.server.introspection.runtime_monitoring.performance_analyzer'] = mock.MagicMock()
sys.modules['src.server.introspection.runtime_monitoring.performance_analyzer'].PerformanceAnalyzer = MockPerformanceAnalyzer

sys.modules['src.server.introspection.runtime_monitoring.telemetry_collector'] = mock.MagicMock()
sys.modules['src.server.introspection.runtime_monitoring.telemetry_collector'].TelemetryCollector = MockTelemetryCollector

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
    mock_goal_decomposition_engine = MagicMock()
    
    return {
        "parameter_manager": mock_parameter_manager,
        "knowledge_system": mock_knowledge_system,
        "cognitive_orchestrator": mock_cognitive_orchestrator,
        "code_generator": mock_code_generator,
        "safety_validator": mock_safety_validator,
        "test_runner": mock_test_runner,
        "goal_decomposition_engine": mock_goal_decomposition_engine
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
         patch('src.server.self_aware_integration.GoalDecompositionEngine', return_value=mock_components["goal_decomposition_engine"]), \
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
         patch('src.server.self_aware_integration.GoalDecompositionEngine', return_value=mock_components["goal_decomposition_engine"]), \
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
         patch('src.server.self_aware_integration.GoalDecompositionEngine', return_value=mock_components["goal_decomposition_engine"]), \
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
            parameter_manager=mock_components["parameter_manager"],
            goal_decomposition_engine=mock_components["goal_decomposition_engine"]
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
         patch('src.server.self_aware_integration.CodeGenerator', return_value=mock_components["code_generator"]), \
         patch('src.server.self_aware_integration.SafetyValidator', return_value=mock_components["safety_validator"]), \
         patch('src.server.self_aware_integration.TestRunner', return_value=mock_components["test_runner"]), \
         patch('src.server.self_aware_integration.GoalDecompositionEngine', return_value=mock_components["goal_decomposition_engine"]), \
         patch('src.server.self_aware_integration.SelfAwareSystem.register_specialized_workers', new_callable=AsyncMock):
        
        # Create a SelfAwareSystem instance
        system = SelfAwareSystem(storage_path=storage_path)
        
        # Initialize the system
        await system.initialize()
        
        # Check initialization order
        assert init_order == ["parameter_manager", "knowledge_system", "cognitive_orchestrator"]
        
        # Check that register_specialized_workers was called after all components were initialized
        system.register_specialized_workers.assert_called_once() 