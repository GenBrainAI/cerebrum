#!/usr/bin/env python3
"""
Run the CrewAI configuration serialization tests.
"""

import unittest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parents[2])
sys.path.append(project_root)

# Import the test module
from tests.crewai_config.test_crewai_config_serialization import TestCrewAIConfigSerialization

if __name__ == "__main__":
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add all tests from the TestCrewAIConfigSerialization class
    suite.addTest(unittest.makeSuite(TestCrewAIConfigSerialization))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful()) 