#!/usr/bin/env python
import sys
print("Python path:", sys.path)

try:
    import src.server.observability
    print("Successfully imported src.server.observability")
except ImportError as e:
    print(f"ImportError for src.server.observability: {e}")

try:
    import src.server
    print("Successfully imported src.server")
except ImportError as e:
    print(f"ImportError for src.server: {e}")

try:
    import src
    print("Successfully imported src")
except ImportError as e:
    print(f"ImportError for src: {e}")

# Check if our test files exist
import os
test_files = [
    "tests/server/observability/test_intervention_interface.py",
    "tests/server/observability/test_intervention_interface_advanced.py",
    "tests/server/observability/test_observability_integration.py",
    "src/server/observability/intervention_interface.py"
]

for file in test_files:
    if os.path.exists(file):
        print(f"File exists: {file}")
    else:
        print(f"File does not exist: {file}") 