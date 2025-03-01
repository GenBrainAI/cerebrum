"""
Fixtures for context-related tests.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.server.context.adaptive_context_manager import ContextConfig
from src.server.context.unified_context_manager import UnifiedContextManager
from src.server.system.terminal_command_executor import SecurityConfig
from src.server.system.codebase_vector_store import VectorStoreConfig

@pytest.fixture
def context_config():
    """Create a test context configuration."""
    return ContextConfig(
        max_tokens=1000,  # Smaller for testing
        default_model="gpt-4",
        enable_history=True
    )

@pytest.fixture
def temp_codebase_dir():
    """Create a temporary directory with sample code files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample Python file
        py_file_path = os.path.join(temp_dir, "sample.py")
        with open(py_file_path, 'w') as f:
            f.write("""
def hello_world():
    \"\"\"Print a greeting message.\"\"\"
    print("Hello, World!")

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self):
        self.result = 0
    
    def add(self, a, b):
        \"\"\"Add two numbers.\"\"\"
        return a + b
""")
        
        # Create sample JavaScript file
        js_file_path = os.path.join(temp_dir, "sample.js")
        with open(js_file_path, 'w') as f:
            f.write("""
function helloWorld() {
    // Print a greeting message
    console.log("Hello, World!");
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(a, b) {
        // Add two numbers
        return a + b;
    }
}
""")
        
        yield temp_dir

@pytest.fixture
def unified_context_manager_config(temp_dir, temp_codebase_dir):
    """Create configurations for the unified context manager."""
    store_dir = os.path.join(temp_dir, "vector_store")
    os.makedirs(store_dir, exist_ok=True)
    
    context_config = ContextConfig(
        max_tokens=1000  # Smaller for testing
    )
    
    security_config = SecurityConfig(
        max_execution_time=5,
        require_approval_for_risk_level="medium"
    )
    
    vector_store_config = VectorStoreConfig(
        root_dir=temp_codebase_dir,
        store_dir=store_dir,
        embedding_dimension=10  # Small dimension for testing
    )
    
    return {
        "base_path": temp_dir,
        "codebase_root": temp_codebase_dir,
        "context_config": context_config,
        "security_config": security_config,
        "vector_store_config": vector_store_config
    } 