#!/usr/bin/env python3
"""
Cleanup script to remove unnecessary test files and organize tests properly.
This script identifies and removes ad-hoc test files that have been converted to proper unittest format.
"""

import os
import shutil

# Files to delete (ad-hoc tests that have been converted to proper unit tests)
FILES_TO_DELETE = [
    "test_concert_planner.py",
    "test_crewai_fix.py",
    "test_crewai_sanitization.py",
    "test_delegation_fix.py",
    "test_task_runner_init.py",
    "fix_concert_planner.py"
]

def main():
    """Main cleanup function."""
    print("Starting test file cleanup...")
    
    # Get current working directory
    cwd = os.getcwd()
    
    # Count of deleted files
    deleted_count = 0
    
    # Delete each file in the list if it exists
    for filename in FILES_TO_DELETE:
        file_path = os.path.join(cwd, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Deleted: {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"✗ Error deleting {filename}: {str(e)}")
        else:
            print(f"⚠ File not found: {filename}")
    
    print(f"\nCleanup complete. Deleted {deleted_count} files.")
    print("\nThe following proper test files are now available:")
    print("  - tests/controllers/test_crewai_runner.py")
    print("  - tests/controllers/test_crewai_task.py")
    print("  - tests/controllers/test_delegation_tool.py")
    print("  - tests/tools/test_general_tools.py")
    print("  - tests/tasktree/test_crewai_tasktree.py")

if __name__ == "__main__":
    main() 