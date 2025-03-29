#!/usr/bin/env python

"""
Run Task Handover Demo

This script sets up the task handover demo state and launches the Streamlit app.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Set up the task handover demo and launch the Streamlit app."""
    print("🚀 Setting up Task Handover Demo")
    
    # Set up the demo state
    try:
        from src.state_setup.task_handover_demo import setup_task_handover_demo
        setup_task_handover_demo()
        print("✅ Task handover demo state created successfully")
    except Exception as e:
        print(f"❌ Error setting up task handover demo: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("Continuing with app startup...")
    
    # Launch the Streamlit app
    print("🚀 Launching Streamlit app")
    subprocess.run([
        "streamlit", "run", "src/chat.py",
        "--browser.gatherUsageStats", "false",
        "--server.headless", "true"
    ])

if __name__ == "__main__":
    main() 