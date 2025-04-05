"""
Test script for system monitoring tools.
"""
import os
import sys
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.server.tools.general_tools.system_monitor_tools import SystemMonitorTools

def main():
    """Run tests for the system monitoring tools."""
    print("Testing System Monitor Tools")
    print("===========================")
    
    # Initialize the tools
    monitor = SystemMonitorTools()
    
    # Test detailed OS info first
    print("\n🔍 Detailed OS Information:")
    os_info = monitor.get_detailed_os_info()
    print(json.dumps(os_info, indent=2))
    
    # Test CPU usage
    print("\n🖥️ CPU Usage:")
    cpu_info = monitor.get_cpu_usage()
    print(json.dumps(cpu_info, indent=2))
    
    # Test memory usage
    print("\n💾 Memory Usage:")
    memory_info = monitor.get_memory_usage()
    print(json.dumps(memory_info, indent=2))
    
    # Test disk usage
    print("\n💿 Disk Usage:")
    disk_info = monitor.get_disk_usage(os.getcwd())
    print(json.dumps(disk_info, indent=2))
    
    # Test system info
    print("\n🧩 System Info:")
    system_info = monitor.get_system_info()
    print(json.dumps(system_info, indent=2))
    
    # Test process list
    print("\n🔄 Top Processes:")
    processes = monitor.get_process_list(5)
    print(json.dumps(processes, indent=2, default=str))
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    main() 