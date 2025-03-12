#!/usr/bin/env python3
"""
Script to install dependencies needed for the vector store.
"""

import subprocess
import sys

def install_dependencies():
    """Install dependencies needed for the vector store."""
    dependencies = [
        "backoff",
        "openai>=1.0.0",
        "PyPDF2>=3.0.0"
    ]
    
    print(f"Installing dependencies: {', '.join(dependencies)}")
    
    for dependency in dependencies:
        try:
            print(f"Installing {dependency}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dependency])
            print(f"Successfully installed {dependency}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing {dependency}: {e}")
            return False
    
    print("All dependencies installed successfully")
    return True

if __name__ == "__main__":
    install_dependencies() 