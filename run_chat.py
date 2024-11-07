#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run Cerebrum Chat')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--port', type=int, default=8501, help='Streamlit port (default: 8501)')
    args = parser.parse_args()

    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Add project root to PYTHONPATH
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{project_root}:{env.get('PYTHONPATH', '')}"

    # Command to run Streamlit
    cmd = ['streamlit', 'run', 'src/chat.py']

    if args.debug:
        # Enable Python debugger
        env['PYTHONBREAKPOINT'] = '1'
        cmd = [
            'python', '-m', 'debugpy',
            '--listen', '5678',
            '--wait-for-client',
            '-m', 'streamlit', 'run', 'src/chat.py',
            '--server.port', str(args.port),
            '--server.headless', 'true'
        ]

    # Run the Streamlit app
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    main()