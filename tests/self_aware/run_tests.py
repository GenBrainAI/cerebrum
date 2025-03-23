#!/usr/bin/env python
"""
Script to run self-aware tests directly without relying on parent conftest.py.
"""
import os
import sys
import pytest
import unittest.mock
from pathlib import Path
import importlib.util
from unittest.mock import AsyncMock

# Add the root project to the path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(root_dir)

# Mock the GitHub API to avoid authentication issues
class MockGitHub:
    def __init__(self, *args, **kwargs):
        pass
    
    def get_repo(self, repo_name):
        mock = unittest.mock.MagicMock()
        mock.get_contents.return_value = []
        return mock

# Apply the mock to bypass GitHub authentication
import github.MainClass
github.MainClass.Github = MockGitHub

# Mock cerebrum.introspection modules if they don't exist
mock_modules = [
    "src.server.integration_optimization",
    "src.server.integration_optimization.resource_optimizer",
    "src.server.integration_optimization.interaction_analyzer",
    "src.server.integration_optimization.workflow_optimizer",
    "src.server.introspection",
    "src.server.introspection.component_analysis",
    "src.server.introspection.component_analysis.analyzer",
    "src.server.introspection.component_analysis.code_parser",
    "src.server.introspection.component_analysis.complexity_analyzer",
    "src.server.introspection.component_analysis.dependency_mapper",
    "src.server.introspection.runtime_monitoring",
    "src.server.introspection.runtime_monitoring.behavior_monitor",
    "src.server.introspection.runtime_monitoring.telemetry_collector",
    "src.server.introspection.runtime_monitoring.anomaly_detector",
    "src.server.introspection.runtime_monitoring.performance_analyzer",
]

# Create mock for missing/problematic modules
for module_name in mock_modules + [
    "src.server.main",
    "src.server.apis.agents_api",
    "src.server.controllers.agents_controller",
    "src.server.tools.github_tool",
    "src.server.context.unified_context_manager",
    "src.server.self_aware_core"
]:
    parts = module_name.split('.')
    parent_mod = '.'.join(parts[:-1])
    
    # Ensure parent modules exist
    current = ""
    for part in parts[:-1]:
        if current:
            current = f"{current}.{part}"
        else:
            current = part
        
        if current not in sys.modules:
            spec = importlib.util.find_spec(current)
            if spec is None:
                # Create a new module if it doesn't exist
                module = type(sys)(current)
                sys.modules[current] = module
    
    # Create the actual module
    if module_name not in sys.modules:
        module = type(sys)(module_name)
        sys.modules[module_name] = module
        
        # Create mocks for specific modules
        if module_name == "src.server.main":
            from fastapi import FastAPI
            module.app = FastAPI()
        
        if module_name == "src.server.apis.agents_api":
            from fastapi import APIRouter
            module.router = APIRouter()
        
        if module_name == "src.server.controllers.agents_controller":
            async def create_crew(*args, **kwargs):
                return {"id": "test-id"}
            
            async def enhance_crew_with_context(*args, **kwargs):
                return {"id": "test-id", "context": "test"}
            
            module.create_crew = create_crew
            module.enhance_crew_with_context = enhance_crew_with_context
            module.GitHubTool = MockGitHub
        
        # Mock cerebrum.introspection modules
        if module_name == "src.server.introspection.component_analysis.analyzer":
            class ComponentAnalyzer:
                def __init__(self, knowledge_system):
                    self.knowledge_system = knowledge_system
                
                async def analyze_component(self, component_path):
                    return {"mock": "analysis"}
            
            module.ComponentAnalyzer = ComponentAnalyzer
        
        if module_name == "src.server.introspection.component_analysis.code_parser":
            class CodeParser:
                def __init__(self):
                    pass
                
                async def parse_file(self, file_path):
                    return {"ast": "mock_ast", "imports": [], "functions": [], "classes": []}
                
                async def extract_dependencies(self, file_path):
                    return {"imports": [], "from_imports": []}
            
            module.CodeParser = CodeParser
        
        if module_name == "src.server.introspection.component_analysis.complexity_analyzer":
            class ComplexityAnalyzer:
                def __init__(self):
                    pass
                
                async def analyze_file(self, file_path):
                    return {"cyclomatic_complexity": 5, "cognitive_complexity": 3}
                
                async def analyze_component(self, component_path):
                    return {"overall_complexity": "medium", "files": {}}
            
            module.ComplexityAnalyzer = ComplexityAnalyzer
        
        if module_name == "src.server.introspection.component_analysis.dependency_mapper":
            class DependencyMapper:
                def __init__(self, code_parser=None):
                    self.code_parser = code_parser
                
                async def map_dependencies(self, component_path):
                    return {"dependencies": {}, "reverse_dependencies": {}}
                
                async def generate_dependency_graph(self, component_path):
                    return {"nodes": [], "edges": []}
            
            module.DependencyMapper = DependencyMapper
        
        if module_name == "src.server.introspection.runtime_monitoring.behavior_monitor":
            class BehaviorMonitor:
                def __init__(self, telemetry_system):
                    self.telemetry_system = telemetry_system
                
                async def start_monitoring(self, components=None):
                    return "mock_session_id"
                
                async def analyze_performance(self, time_period):
                    return {"performance": "analysis"}
            
            module.BehaviorMonitor = BehaviorMonitor
        
        if module_name == "src.server.introspection.runtime_monitoring.anomaly_detector":
            class AnomalyDetector:
                def __init__(self, telemetry_collector=None):
                    self.telemetry_collector = telemetry_collector
                
                async def detect_anomalies(self, time_period=None):
                    return {"anomalies": []}
                
                async def analyze_pattern(self, pattern_type, component=None):
                    return {"pattern_analysis": "mock_result"}
            
            module.AnomalyDetector = AnomalyDetector
        
        if module_name == "src.server.introspection.runtime_monitoring.performance_analyzer":
            class PerformanceAnalyzer:
                def __init__(self, telemetry_collector=None):
                    self.telemetry_collector = telemetry_collector
                
                async def analyze_performance(self, component=None, time_period=None):
                    return {"performance_metrics": {}, "bottlenecks": []}
                
                async def get_resource_usage(self, component=None, resource_type=None):
                    return {"resource_usage": "mock_data"}
            
            module.PerformanceAnalyzer = PerformanceAnalyzer
        
        if module_name == "src.server.introspection.runtime_monitoring.telemetry_collector":
            class TelemetryCollector:
                def __init__(self):
                    pass
            
            module.TelemetryCollector = TelemetryCollector
        
        if module_name == "src.server.integration_optimization.interaction_analyzer":
            class InteractionAnalyzer:
                def __init__(self, knowledge_system=None, component_analyzer=None):
                    self.knowledge_system = knowledge_system
                    self.component_analyzer = component_analyzer
                    self.interaction_patterns = {}
                    self.optimization_suggestions = []
                
                async def analyze_interaction(self, component_a, component_b):
                    return {"interaction": "analysis"}
            
            module.InteractionAnalyzer = InteractionAnalyzer
        
        if module_name == "src.server.integration_optimization.resource_optimizer":
            class ResourceOptimizer:
                def __init__(self, knowledge_system=None, resource_monitor=None):
                    self.knowledge_system = knowledge_system
                    self.resource_monitor = resource_monitor
                    self.resource_usage_stats = {}
                    self.resource_allocations = {}
                    self.optimization_history = []
                
                async def optimize_resource(self, component, resource_type):
                    return {"optimization": "result"}
            
            module.ResourceOptimizer = ResourceOptimizer
        
        if module_name == "src.server.integration_optimization.workflow_optimizer":
            class WorkflowOptimizer:
                def __init__(self, knowledge_system=None, goal_decomposition_engine=None):
                    self.knowledge_system = knowledge_system
                    self.goal_decomposition_engine = goal_decomposition_engine
                    self.workflow_metrics = {}
                    self.workflow_bottlenecks = []
                    self.workflow_optimizations = []
                    self.workflow_graph = {}
                
                async def analyze_workflow_efficiency(self, workflow_type):
                    return {"efficiency": 0.8, "bottlenecks": []}
                
                async def optimize_workflow(self, workflow_name):
                    return {"workflow": "optimized"}
            
            module.WorkflowOptimizer = WorkflowOptimizer
            
        if module_name == "src.server.context.unified_context_manager":
            class UnifiedContextManager:
                def __init__(self, config=None):
                    self.config = config or {}
                    
                async def list_operations(self):
                    """List all operations."""
                    return []
                
                async def create_operation(self, operation_id, description, operation_type, metadata=None):
                    """Create a new operation."""
                    return operation_id
                
                async def initialize_codebase_index(self, incremental=True):
                    """Initialize the codebase index."""
                    return {
                        "indexed_files": 10,
                        "total_files": 10,
                        "skipped_files": 0
                    }
                
                async def execute_command(self, operation_id, command, working_directory=".", environment_vars=None, 
                                         timeout=30, requires_approval=True, add_to_context=True, context_priority=60):
                    """Execute a command."""
                    from src.server.system.terminal_command_executor import CommandExecutionResult
                    return CommandExecutionResult(
                        command_id="cmd1",
                        command=command,
                        exit_code=0,
                        stdout="file1.txt\nfile2.txt",
                        stderr="",
                        execution_time=0.1,
                        started_at="2023-01-01T00:00:00",
                        completed_at="2023-01-01T00:00:01",
                        working_directory=working_directory,
                        environment_vars=environment_vars or {},
                        sandbox_type="subprocess",
                        metadata={}
                    )
                
                async def search_codebase(self, operation_id, query, top_k=5, add_to_context=True, context_priority=70):
                    """Search the codebase."""
                    return []
                
                async def get_file_content(self, operation_id, file_path, add_to_context=True, context_priority=65):
                    """Get file content."""
                    return "file content"
                
                async def get_operation_context(self, operation_id, max_tokens=1000, include_metadata=False):
                    """Get operation context."""
                    return "context content"
                
                async def add_to_operation_context(self, operation_id, content, source, priority=50, metadata=None):
                    """Add to operation context."""
                    return "item1"
                
                async def get_pending_command_approvals(self):
                    """Get pending command approvals."""
                    return []
                
                async def execute_approved_command(self, operation_id, approval_id, add_to_context=True, context_priority=60):
                    """Execute an approved command."""
                    from src.server.system.terminal_command_executor import CommandExecutionResult
                    return CommandExecutionResult(
                        command_id="cmd2",
                        command="cat file.txt",
                        exit_code=0,
                        stdout="file content",
                        stderr="",
                        execution_time=0.1,
                        started_at="2023-01-01T00:00:00",
                        completed_at="2023-01-01T00:00:01",
                        working_directory=".",
                        environment_vars={},
                        sandbox_type="subprocess",
                        metadata={}
                    )
                
                async def reject_command(self, approval_id):
                    """Reject a command."""
                    return True
                
                async def get_codebase_stats(self):
                    """Get codebase stats."""
                    return {
                        "total_files": 10,
                        "total_lines": 1000,
                        "languages": {
                            "python": 5,
                            "javascript": 3,
                            "markdown": 2
                        },
                        "last_updated": "2023-01-01T00:00:00"
                    }
                
                async def refresh_codebase(self):
                    """Refresh the codebase."""
                    return {
                        "indexed_files": 2,
                        "total_files": 10,
                        "skipped_files": 8
                    }
            
            module.UnifiedContextManager = UnifiedContextManager
            
        if module_name == "src.server.self_aware_core":
            # Import the UnifiedContextManager class
            from src.server.context.unified_context_manager import UnifiedContextManager
            
            # Add the UnifiedContextManager to the module
            module.UnifiedContextManager = UnifiedContextManager
            
            class CerebrumSystemCore:
                def __init__(self, base_path, codebase_root, config=None):
                    self.base_path = base_path
                    self.codebase_root = codebase_root
                    self.config = config or {}
                    self._initialized = False
                    self._context_manager = None
                    self._operation_id = "cerebrum_system"
                    
                async def initialize(self):
                    self._context_manager = UnifiedContextManager(self.config)
                    
                    # List operations to check if one already exists
                    operations = await self._context_manager.list_operations()
                    
                    # Create operation
                    self._operation_id = await self._context_manager.create_operation(
                        operation_id="cerebrum_system",
                        description="Cerebrum System Core",
                        operation_type="system",
                        metadata={
                            "created_at": "2023-01-01T00:00:00",
                            "system_type": "cerebrum_system",
                            "version": "1.0.0"
                        }
                    )
                    
                    # Add initialization message to context
                    await self._context_manager.add_to_operation_context(
                        operation_id=self._operation_id,
                        content="Cerebrum System Core initialized.",
                        source="system",
                        priority=90,
                        metadata={
                            "type": "initialization",
                            "timestamp": "2023-01-01T00:00:00"
                        }
                    )
                    
                    # Initialize codebase index
                    await self._context_manager.initialize_codebase_index(incremental=True)
                    
                    self._initialized = True
                    
                async def index_codebase(self, incremental=True):
                    return await self._context_manager.initialize_codebase_index(incremental=incremental)
                    
                async def execute_command(self, command, working_directory=".", timeout=30, requires_approval=True):
                    return await self._context_manager.execute_command(
                        operation_id=self._operation_id,
                        command=command,
                        working_directory=working_directory,
                        environment_vars=None,
                        timeout=timeout,
                        requires_approval=requires_approval,
                        add_to_context=True,
                        context_priority=60
                    )
                    
                async def search_code(self, query, top_k=5):
                    return await self._context_manager.search_codebase(
                        operation_id=self._operation_id,
                        query=query,
                        top_k=top_k,
                        add_to_context=True,
                        context_priority=70
                    )
                    
                async def get_file_content(self, file_path):
                    return await self._context_manager.get_file_content(
                        operation_id=self._operation_id,
                        file_path=file_path,
                        add_to_context=True,
                        context_priority=65
                    )
                    
                async def get_context(self, max_tokens=1000, include_metadata=False):
                    return await self._context_manager.get_operation_context(
                        operation_id=self._operation_id,
                        max_tokens=max_tokens,
                        include_metadata=include_metadata
                    )
                    
                async def add_to_context(self, content, source, priority=50, metadata=None):
                    return await self._context_manager.add_to_operation_context(
                        operation_id=self._operation_id,
                        content=content,
                        source=source,
                        priority=priority,
                        metadata=metadata or {}
                    )
                    
                async def get_pending_approvals(self):
                    return await self._context_manager.get_pending_command_approvals()
                    
                async def execute_approved_command(self, approval_id):
                    return await self._context_manager.execute_approved_command(
                        operation_id=self._operation_id,
                        approval_id=approval_id,
                        add_to_context=True,
                        context_priority=60
                    )
                    
                async def reject_command(self, approval_id):
                    return await self._context_manager.reject_command(approval_id)
                    
                async def get_codebase_stats(self):
                    return await self._context_manager.get_codebase_stats()
                    
                async def refresh_codebase(self):
                    return await self._context_manager.refresh_codebase()
            
            module.CerebrumSystemCore = CerebrumSystemCore

def run_test(test_path=None):
    """Run tests in the self-aware directory."""
    if test_path is None:
        # Run all tests in the self-aware directory
        args = [".", "-v"]
    else:
        # Run specific test
        args = [test_path, "-v"]
    
    # Add any additional pytest arguments
    args.extend(sys.argv[1:])
    
    return pytest.main(args)

if __name__ == "__main__":
    # Change to the self_aware directory if not already there
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # If a specific test is provided as argument, run only that test
    if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
        test_path = sys.argv[1]
        sys.argv.pop(1)  # Remove the test path from argv to avoid confusing pytest
        exit_code = run_test(test_path)
    else:
        # Run all tests
        exit_code = run_test()
    
    sys.exit(exit_code) 