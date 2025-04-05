"""
System monitoring tools for Cerebrum.

This module provides tools for monitoring system resources like CPU, memory, and disk usage.
"""
from typing import Dict, List, Tuple, Optional
import psutil
import os
import platform
import datetime
import socket
import subprocess
import sys

class SystemMonitorTools:
    """Tools for monitoring system resources."""
    
    def get_cpu_usage(self) -> Dict[str, float]:
        """
        Get current CPU usage information.
        
        Returns:
            Dictionary containing CPU usage percentages (overall and per-core)
        """
        # Get overall CPU usage
        overall_cpu = psutil.cpu_percent(interval=0.5)
        
        # Get per-core CPU usage
        per_core_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
        
        return {
            "overall_percent": overall_cpu,
            "per_core_percent": per_core_cpu,
            "core_count": psutil.cpu_count(logical=True),
            "physical_core_count": psutil.cpu_count(logical=False)
        }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage information.
        
        Returns:
            Dictionary containing memory usage stats in GB and percentages
        """
        memory = psutil.virtual_memory()
        
        # Convert bytes to GB
        def to_gb(bytes_value):
            return round(bytes_value / (1024 ** 3), 2)
        
        return {
            "total_gb": to_gb(memory.total),
            "available_gb": to_gb(memory.available),
            "used_gb": to_gb(memory.used),
            "percent_used": memory.percent,
            "percent_available": 100 - memory.percent
        }
    
    def get_disk_usage(self, path: Optional[str] = None) -> Dict[str, float]:
        """
        Get disk usage information for a specific path or all mounted disks.
        
        Args:
            path: Path to check disk usage for. If None, returns info for all mounted disks.
            
        Returns:
            Dictionary containing disk usage information in GB and percentages
        """
        # Convert bytes to GB
        def to_gb(bytes_value):
            return round(bytes_value / (1024 ** 3), 2)
        
        if path:
            # Get disk usage for specific path
            disk = psutil.disk_usage(path)
            return {
                "path": path,
                "total_gb": to_gb(disk.total),
                "used_gb": to_gb(disk.used),
                "free_gb": to_gb(disk.free),
                "percent_used": disk.percent,
                "percent_free": 100 - disk.percent
            }
        else:
            # Get disk usage for all mounted disks
            result = {}
            for partition in psutil.disk_partitions(all=False):
                if os.name == 'nt' or not partition.mountpoint.startswith('/dev'):
                    try:
                        disk = psutil.disk_usage(partition.mountpoint)
                        result[partition.mountpoint] = {
                            "device": partition.device,
                            "total_gb": to_gb(disk.total),
                            "used_gb": to_gb(disk.used),
                            "free_gb": to_gb(disk.free),
                            "percent_used": disk.percent,
                            "percent_free": 100 - disk.percent
                        }
                    except (PermissionError, FileNotFoundError):
                        # Skip if permission denied or path not found
                        continue
            return result
    
    def get_network_stats(self) -> Dict[str, Dict]:
        """
        Get network interface statistics.
        
        Returns:
            Dictionary containing network interface statistics
        """
        net_io = psutil.net_io_counters(pernic=True)
        result = {}
        
        for interface, stats in net_io.items():
            # Convert bytes to MB
            def to_mb(bytes_value):
                return round(bytes_value / (1024 ** 2), 2)
            
            result[interface] = {
                "bytes_sent_mb": to_mb(stats.bytes_sent),
                "bytes_recv_mb": to_mb(stats.bytes_recv),
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin,
                "errout": stats.errout,
                "dropin": stats.dropin,
                "dropout": stats.dropout
            }
        
        return result
    
    def get_system_info(self) -> Dict[str, str]:
        """
        Get general system information.
        
        Returns:
            Dictionary containing system information
        """
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_days": uptime.days,
            "uptime_hours": uptime.seconds // 3600,
            "uptime_minutes": (uptime.seconds % 3600) // 60,
            "python_version": platform.python_version()
        }
    
    def get_detailed_os_info(self) -> Dict[str, str]:
        """
        Get detailed operating system information.
        
        Returns:
            Dictionary containing detailed OS information
        """
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "platform": platform.platform(True),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_compiler": platform.python_compiler(),
            "hostname": socket.gethostname()
        }
        
        # Add Mac-specific information
        if platform.system() == 'Darwin':
            try:
                # Get macOS version
                mac_ver = platform.mac_ver()
                os_info.update({
                    "mac_version": mac_ver[0],
                    "mac_machine": mac_ver[2]
                })
                
                # Get additional macOS info using system_profiler
                if sys.platform == 'darwin':
                    try:
                        result = subprocess.run(
                            ['system_profiler', 'SPSoftwareDataType', '-detailLevel', 'mini'],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            output = result.stdout
                            # Extract key information from system_profiler output
                            for line in output.splitlines():
                                line = line.strip()
                                if ":" in line:
                                    key, value = line.split(":", 1)
                                    key = key.strip().lower().replace(" ", "_")
                                    value = value.strip()
                                    if key and value:
                                        os_info[f"macos_{key}"] = value
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                        pass
            except Exception:
                pass
        
        # Add Linux-specific information
        elif platform.system() == 'Linux':
            try:
                # Try to get Linux distribution information
                import distro
                linux_info = distro.info()
                os_info.update({
                    "linux_distro": linux_info.get('id', ''),
                    "linux_version": linux_info.get('version', ''),
                    "linux_codename": linux_info.get('codename', '')
                })
            except ImportError:
                # Fallback for older Python versions or if distro is not installed
                try:
                    with open('/etc/os-release', 'r') as f:
                        for line in f:
                            if '=' in line:
                                key, value = line.rstrip().split('=', 1)
                                value = value.strip('"')
                                if key == 'NAME':
                                    os_info['linux_distro'] = value
                                elif key == 'VERSION':
                                    os_info['linux_version'] = value
                                elif key == 'ID':
                                    os_info['linux_id'] = value
                except (IOError, FileNotFoundError):
                    pass
        
        # Add Windows-specific information
        elif platform.system() == 'Windows':
            try:
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                try:
                    key = winreg.OpenKey(registry, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion')
                    for i in range(30):
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if name in ['ProductName', 'CurrentBuildNumber', 'ReleaseId']:
                                os_info[f'windows_{name.lower()}'] = value
                        except OSError:
                            break
                except OSError:
                    pass
            except ImportError:
                pass
        
        return os_info
    
    def get_process_list(self, top_n: int = 10) -> List[Dict]:
        """
        Get list of top processes sorted by memory usage.
        
        Args:
            top_n: Number of top processes to return
            
        Returns:
            List of dictionaries containing process information
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                # Get process info
                proc_info = proc.info
                # Get CPU percentage
                proc_info['cpu_percent'] = proc.cpu_percent(interval=0.1)
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by memory usage and get top N
        sorted_processes = sorted(processes, key=lambda p: p['memory_percent'], reverse=True)
        return sorted_processes[:top_n]
    
    def get_all_system_stats(self) -> Dict:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dictionary containing all system statistics
        """
        return {
            "cpu": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "system_info": self.get_system_info(),
            "os_info": self.get_detailed_os_info(),
            "top_processes": self.get_process_list(5)
        }


def register_system_monitor_tools(catalog = None) -> List[str]:
    """Register the system monitoring tools with the tools catalog.
    
    Args:
        catalog: Optional tools catalog instance. If not provided, the global instance will be used.
        
    Returns:
        List of registered tool names
    """
    # Get catalog instance if not provided
    if catalog is None:
        from src.server.tools.tools_catalog import tools_catalog
        catalog = tools_catalog
    
    # Create tool instance
    system_monitor = SystemMonitorTools()
    
    # Register tool and its methods
    registered_names = catalog.register_instance(
        system_monitor, 
        "system_monitor", 
        exclude_base_methods=True, 
        register_instance_itself=True
    )
    
    print(f"✅ Registered SystemMonitorTools with {len(registered_names)} methods")
    return registered_names 