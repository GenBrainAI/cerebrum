#!/usr/bin/env python

"""
Run Task Handover Tests

This script runs the unit tests for the task handover feature.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the task handover tests."""
    print("🧪 Running Task Handover Tests")
    
    # Get the path to the tests directory
    tests_dir = Path(__file__).parent / "tests" / "handover"
    
    # Run pytest on the handover test directory
    result = subprocess.run([
        "python", "-m", "pytest", 
        str(tests_dir),
        "-v",  # Verbose output
        "--no-header",  # Hide pytest header
    ])
    
    # Return the exit code from pytest
    return result.returncode

if __name__ == "__main__":
    sys.exit(main()) 