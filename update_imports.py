#!/usr/bin/env python
"""
Script to update import paths in files moved from cerebrum to src/server
"""
import os
import re
from pathlib import Path

def update_file_imports(file_path):
    """Update imports in a file from cerebrum.* to src.server.*"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace imports
    updated_content = re.sub(
        r'from cerebrum\.', 
        'from src.server.', 
        content
    )
    updated_content = re.sub(
        r'import cerebrum\.', 
        'import src.server.', 
        updated_content
    )
    
    # Write back to file if changes were made
    if content != updated_content:
        with open(file_path, 'w') as f:
            f.write(updated_content)
        return True
    return False

def process_directory(directory):
    """Process all Python files in a directory recursively"""
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if update_file_imports(file_path):
                    count += 1
                    print(f"Updated imports in: {file_path}")
    
    return count

if __name__ == "__main__":
    server_dir = Path("src/server")
    count = process_directory(server_dir)
    print(f"\nUpdated imports in {count} files.") 