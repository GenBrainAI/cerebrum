# Development Instructions: Dynamic Tools Generation Verification and Metrics

## Context
We have stabilized the tools catalog infrastructure and have passing unit tests for `test_create_tools_dynamicaly.py`. However, we haven't yet verified that tools are being properly generated and executed. This is a critical step before moving forward with the UI development.

## Current State
- Tools catalog singleton pattern is implemented and stable
- Basic unit tests are passing
- Dynamic tools generation infrastructure exists but needs verification
- No execution metrics or logging in place

## Relevant Files

### Core Implementation Files
1. `src/server/tools/tools_catalog.py`
   - Main singleton catalog implementation
   - Tool registration and management
   - Will contain new metrics and logging functionality

2. `src/server/models/tools_descriptors.py`
   - Contains tool type definitions and metadata models
   - Defines the structure for tool information

3. `src/state_setup/dynamic_tools.py`
   - Handles dynamic tool state initialization
   - Sets up the initial tools configuration
   - Contains `setup_dynamic_tools_state` function

### Test Files
1. `tests/specialized/test_create_tools_dynamicaly.py`
   - Main test file for dynamic tools functionality
   - Contains test fixtures and state setup
   - Will include new execution verification tests

2. `tests/conftest.py`
   - Global test configuration
   - Will contain logging setup
   - Shared test fixtures

### Supporting Files
1. `src/server/persistence/persistence_model_factory.py`
   - Manages persistence model creation
   - Used in test setup and state management

2. `src/server/controllers/task_runner.py`
   - Handles task execution
   - Will interact with tool execution tracking

3. `src/server/context/unified_context.py`
   - Manages context state
   - Important for tool execution context

### Files to be Modified
1. `src/server/tools/tools_catalog.py`:
   - Add ToolExecutionMetrics class
   - Enhance register_tool method
   - Add execution tracking
   - Add metrics API

2. `tests/specialized/test_create_tools_dynamicaly.py`:
   - Add test_dynamic_tool_execution
   - Enhance existing tests with metrics verification

3. `tests/conftest.py`:
   - Add logging configuration
   - Add any needed test fixtures

## Development Goals
1. Verify dynamic tools generation is working
2. Add execution verification and logging
3. Implement basic tool performance metrics

## Step-by-Step Development Plan

### 1. Add Logging Infrastructure

```python
# Add to src/server/tools/tools_catalog.py
import logging
from typing import Optional, Dict, Any
from datetime import datetime

class ToolExecutionMetrics:
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.success: bool = False
        self.error: Optional[str] = None
        self.input_params: Dict[str, Any] = {}
        self.output: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            "success": self.success,
            "error": self.error,
            "input_params": self.input_params,
            "output": str(self.output) if self.output is not None else None
        }

class ToolsCatalog:
    def __init__(self):
        # Add to existing initialization
        self._execution_metrics: Dict[str, List[ToolExecutionMetrics]] = {}
        self._logger = logging.getLogger(__name__)
```

### 2. Enhance Tool Registration

```python
# Modify register_tool method in ToolsCatalog
def register_tool(self, tool: Any, name: Optional[str] = None) -> str:
    """Register a tool with enhanced logging and validation."""
    tool_name = name or getattr(tool, '__name__', str(tool))
    
    try:
        self._logger.info(f"Registering tool: {tool_name}")
        self._logger.debug(f"Tool type: {type(tool)}")
        
        # Existing registration logic...
        
        # Add validation
        if not self._validate_tool(tool):
            raise ValueError(f"Tool {tool_name} failed validation")
            
        self._logger.info(f"Successfully registered tool: {tool_name}")
        return tool_name
        
    except Exception as e:
        self._logger.error(f"Failed to register tool {tool_name}: {str(e)}")
        raise

def _validate_tool(self, tool: Any) -> bool:
    """Validate tool meets minimum requirements."""
    # Implement validation logic based on tool type
    return True  # Placeholder
```

### 3. Add Execution Tracking

```python
# Add to ToolsCatalog
async def execute_tool(self, tool_name: str, **kwargs) -> Any:
    """Execute a tool with metrics tracking."""
    if tool_name not in self._tools:
        raise KeyError(f"Tool {tool_name} not found")
        
    metrics = ToolExecutionMetrics()
    metrics.start_time = datetime.now()
    metrics.input_params = kwargs
    
    try:
        tool = self._tools[tool_name]
        self._logger.info(f"Executing tool: {tool_name}")
        self._logger.debug(f"Input parameters: {kwargs}")
        
        result = await tool.execute(**kwargs)
        
        metrics.success = True
        metrics.output = result
        self._logger.info(f"Tool {tool_name} executed successfully")
        return result
        
    except Exception as e:
        metrics.success = False
        metrics.error = str(e)
        self._logger.error(f"Tool {tool_name} execution failed: {str(e)}")
        raise
        
    finally:
        metrics.end_time = datetime.now()
        if tool_name not in self._execution_metrics:
            self._execution_metrics[tool_name] = []
        self._execution_metrics[tool_name].append(metrics)
```

### 4. Add Test Cases

```python
# Add to tests/specialized/test_create_tools_dynamicaly.py
@pytest.mark.asyncio
async def test_dynamic_tool_execution():
    """Test that dynamically generated tools can be executed."""
    # Setup
    persistence_model = PersistenceModelFactory.persistence_model()
    state = await setup_dynamic_tools_state(persistence_model)
    
    # Get the dynamic tools task
    tasks = persistence_model.tasks.list()
    dynamic_tools_task = next(
        (task for task in tasks if task.name == "Generate Dynamic Langchain Tool"),
        None
    )
    assert dynamic_tools_task is not None
    
    # Execute the task
    result = await task_runner.execute_task(dynamic_tools_task.id)
    assert result is not None
    
    # Verify tool was generated
    generated_tool_name = result.get("generated_tool_name")
    assert generated_tool_name is not None
    
    # Verify tool exists in catalog
    assert generated_tool_name in tools_catalog.list_tools()
    
    # Execute the generated tool
    tool_result = await tools_catalog.execute_tool(generated_tool_name, input_param="test")
    assert tool_result is not None
    
    # Check metrics
    metrics = tools_catalog._execution_metrics.get(generated_tool_name, [])
    assert len(metrics) > 0
    assert metrics[-1].success
```

### 5. Add Metrics API

```python
# Add to ToolsCatalog
def get_tool_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Get execution metrics for one or all tools."""
    if tool_name:
        if tool_name not in self._execution_metrics:
            return {}
        return {
            "total_executions": len(self._execution_metrics[tool_name]),
            "successful_executions": sum(1 for m in self._execution_metrics[tool_name] if m.success),
            "average_duration": sum((m.end_time - m.start_time).total_seconds() 
                                 for m in self._execution_metrics[tool_name] 
                                 if m.start_time and m.end_time) / len(self._execution_metrics[tool_name])
                                 if self._execution_metrics[tool_name] else 0,
            "last_execution": self._execution_metrics[tool_name][-1].to_dict() 
                            if self._execution_metrics[tool_name] else None
        }
    
    return {name: self.get_tool_metrics(name) for name in self._tools.keys()}
```

## Testing Instructions

1. Run the existing tests to ensure baseline functionality:
   ```bash
   python -m pytest tests/specialized/test_create_tools_dynamicaly.py -v
   ```

2. Add logging configuration:
   ```python
   # Add to tests/conftest.py
   import logging
   
   @pytest.fixture(autouse=True)
   def setup_logging():
       logging.basicConfig(level=logging.DEBUG)
   ```

3. Run the new execution test:
   ```bash
   python -m pytest tests/specialized/test_create_tools_dynamicaly.py::test_dynamic_tool_execution -v
   ```

4. Check the logs for:
   - Tool registration events
   - Execution tracking
   - Performance metrics

## Expected Outcomes

1. All tests should pass
2. Logs should show:
   - Tool registration process
   - Dynamic tool generation
   - Tool execution with metrics
3. Metrics should be available for:
   - Execution success/failure
   - Duration
   - Input/output tracking

## Next Steps After Completion

1. Review the metrics data to ensure tools are being generated and executed properly
2. Use this information to implement the UI monitoring dashboard
3. Begin implementing the task tree enhancement features

## Notes
- Keep the logging level at DEBUG during development
- Monitor memory usage with the metrics storage
- Consider adding metric persistence for long-term analysis
- Document any patterns in tool generation failures

## Bibliography

### Implementation Files
```plaintext
src/
├── server/
│   ├── tools/
│   │   ├── tools_catalog.py             # Main implementation file
│   │   ├── internal_file_tools.py       # Internal tools implementation
│   │   ├── internal_testing_tools.py    # Testing tools implementation
│   │   └── internal_proxy_tools.py      # Proxy tools implementation
│   ├── models/
│   │   └── tools_descriptors.py         # Tool type definitions and models
│   ├── persistence/
│   │   └── persistence_model_factory.py # Persistence management
│   ├── controllers/
│   │   └── task_runner.py              # Task execution handling
│   └── context/
│       └── unified_context.py           # Context state management
└── state_setup/
    └── dynamic_tools.py                 # Dynamic tools state initialization
```

### Test Files
```plaintext
tests/
├── specialized/
│   └── test_create_tools_dynamicaly.py  # Dynamic tools tests
└── conftest.py                          # Global test configuration
```

### File Purposes Summary
1. **Core Files**
   - `tools_catalog.py`: Singleton catalog implementation, tool management
   - `tools_descriptors.py`: Tool metadata and type definitions
   - `dynamic_tools.py`: Dynamic tool state setup and initialization

2. **Support Files**
   - `internal_file_tools.py`: File operation tools
   - `internal_testing_tools.py`: Testing utilities
   - `internal_proxy_tools.py`: Tool proxying functionality
   - `persistence_model_factory.py`: State persistence
   - `task_runner.py`: Task execution
   - `unified_context.py`: Context management

3. **Test Files**
   - `test_create_tools_dynamicaly.py`: Main test suite
   - `conftest.py`: Test configuration and fixtures

### Required for Development Session
To set up the development session in Cursor IDE, ensure these files are loaded into the context:
1. `src/server/tools/tools_catalog.py`
2. `src/server/models/tools_descriptors.py`
3. `src/state_setup/dynamic_tools.py`
4. `tests/specialized/test_create_tools_dynamicaly.py`
5. `tests/conftest.py`
