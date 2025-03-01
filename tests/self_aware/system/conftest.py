"""
Fixtures for system-related tests.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path

from src.server.system.terminal_command_executor import SecurityConfig
from src.server.system.codebase_vector_store import VectorStoreConfig

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for command logs."""
    log_dir = tmp_path / "test_command_logs"
    log_dir.mkdir(exist_ok=True)
    yield log_dir
    # Cleanup
    shutil.rmtree(log_dir)

@pytest.fixture
def security_config(temp_log_dir):
    """Create a test security configuration."""
    return SecurityConfig(
        allowed_commands=["ls", "echo", "cat", "pwd"],
        blocked_commands=["rm", "sudo", "chmod"],
        allowed_patterns=[],
        blocked_patterns=[r"rm\s+-rf", r"sudo"],
        max_execution_time=5,
        max_output_size=1024,
        sandbox_type="subprocess",
        log_commands=True,
        log_output=True,
        log_directory=str(temp_log_dir),
        require_approval_for_risk_level="medium"
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
    
    def subtract(self, a, b):
        \"\"\"Subtract b from a.\"\"\"
        return a - b
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
    
    subtract(a, b) {
        // Subtract b from a
        return a - b;
    }
}
""")
        
        # Create a directory with a file to test exclusion
        excluded_dir = os.path.join(temp_dir, "node_modules")
        os.makedirs(excluded_dir, exist_ok=True)
        with open(os.path.join(excluded_dir, "excluded.js"), 'w') as f:
            f.write("// This file should be excluded")
        
        yield temp_dir

@pytest.fixture
def temp_store_dir():
    """Create a temporary directory for the vector store."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def vector_store_config(temp_codebase_dir, temp_store_dir):
    """Create a test vector store configuration."""
    return VectorStoreConfig(
        root_dir=temp_codebase_dir,
        store_dir=temp_store_dir,
        embedding_dimension=10,  # Small dimension for testing
        similarity_threshold=0.5
    ) 