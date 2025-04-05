"""
Tests for the system monitoring tools.
"""
import os
import sys
import pytest
import psutil
from unittest.mock import patch, MagicMock, PropertyMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.server.tools.general_tools.system_monitor_tools import SystemMonitorTools


class TestSystemMonitorTools:
    """Tests for the SystemMonitorTools class."""
    
    @pytest.fixture
    def system_monitor(self):
        """Create an instance of SystemMonitorTools for testing."""
        return SystemMonitorTools()
    
    def test_get_cpu_usage(self, system_monitor):
        """Test get_cpu_usage returns the expected data structure."""
        # Execute
        result = system_monitor.get_cpu_usage()
        
        # Verify
        assert isinstance(result, dict)
        assert "overall_percent" in result
        assert "per_core_percent" in result
        assert "core_count" in result
        assert "physical_core_count" in result
        
        # Check types
        assert isinstance(result["overall_percent"], float)
        assert isinstance(result["per_core_percent"], list)
        assert isinstance(result["core_count"], int)
        assert isinstance(result["physical_core_count"], int)
    
    def test_get_memory_usage(self, system_monitor):
        """Test get_memory_usage returns the expected data structure."""
        # Execute
        result = system_monitor.get_memory_usage()
        
        # Verify
        assert isinstance(result, dict)
        assert "total_gb" in result
        assert "available_gb" in result
        assert "used_gb" in result
        assert "percent_used" in result
        assert "percent_available" in result
        
        # Check types
        assert isinstance(result["total_gb"], float)
        assert isinstance(result["available_gb"], float)
        assert isinstance(result["used_gb"], float)
        assert isinstance(result["percent_used"], float)
        assert isinstance(result["percent_available"], float)
        
        # Verify the percent values add up to 100
        assert abs(result["percent_used"] + result["percent_available"] - 100) < 0.01
    
    def test_get_disk_usage_with_path(self, system_monitor):
        """Test get_disk_usage with a specific path returns the expected data structure."""
        # Execute
        result = system_monitor.get_disk_usage(os.getcwd())
        
        # Verify
        assert isinstance(result, dict)
        assert "path" in result
        assert "total_gb" in result
        assert "used_gb" in result
        assert "free_gb" in result
        assert "percent_used" in result
        assert "percent_free" in result
        
        # Check types
        assert isinstance(result["path"], str)
        assert isinstance(result["total_gb"], float)
        assert isinstance(result["used_gb"], float)
        assert isinstance(result["free_gb"], float)
        assert isinstance(result["percent_used"], float)
        assert isinstance(result["percent_free"], float)
        
        # Verify the percent values add up to 100
        assert abs(result["percent_used"] + result["percent_free"] - 100) < 0.01
    
    def test_get_disk_usage_without_path(self, system_monitor):
        """Test get_disk_usage without a path returns data for all disks."""
        # Execute
        result = system_monitor.get_disk_usage()
        
        # Verify
        assert isinstance(result, dict)
        # At least one disk should be returned
        assert len(result) > 0
        
        # Check the first disk
        first_disk = next(iter(result.values()))
        assert "total_gb" in first_disk
        assert "used_gb" in first_disk
        assert "free_gb" in first_disk
        assert "percent_used" in first_disk
        assert "percent_free" in first_disk
    
    def test_get_system_info(self, system_monitor):
        """Test get_system_info returns the expected data structure."""
        # Execute
        result = system_monitor.get_system_info()
        
        # Verify
        assert isinstance(result, dict)
        assert "system" in result
        assert "node" in result
        assert "release" in result
        assert "version" in result
        assert "machine" in result
        assert "processor" in result
        assert "boot_time" in result
        assert "uptime_days" in result
        assert "uptime_hours" in result
        assert "uptime_minutes" in result
        assert "python_version" in result
    
    def test_get_detailed_os_info(self, system_monitor):
        """Test get_detailed_os_info returns the expected data structure."""
        # Execute
        result = system_monitor.get_detailed_os_info()
        
        # Verify
        assert isinstance(result, dict)
        assert "system" in result
        assert "release" in result
        assert "version" in result
        assert "machine" in result
        assert "processor" in result
        assert "architecture" in result
        assert "platform" in result
        assert "python_version" in result
        assert "python_implementation" in result
        assert "python_compiler" in result
        assert "hostname" in result
    
    def test_get_process_list(self, system_monitor):
        """Test get_process_list returns the expected data structure."""
        # Execute
        result = system_monitor.get_process_list(5)
        
        # Verify
        assert isinstance(result, list)
        assert len(result) <= 5  # It should return at most 5 processes
        
        if result:  # If any processes were returned
            assert "pid" in result[0]
            assert "name" in result[0]
            assert "username" in result[0]
            assert "memory_percent" in result[0]
            assert "cpu_percent" in result[0]
    
    def test_get_all_system_stats(self, system_monitor):
        """Test get_all_system_stats returns the expected data structure."""
        # Execute
        result = system_monitor.get_all_system_stats()
        
        # Verify
        assert isinstance(result, dict)
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "system_info" in result
        assert "os_info" in result
        assert "top_processes" in result


# Mock tests for some functions to avoid environment dependencies
class TestSystemMonitorToolsMocked:
    """Mocked tests for SystemMonitorTools to avoid environment dependencies."""
    
    @pytest.fixture
    def system_monitor(self):
        """Create an instance of SystemMonitorTools for testing."""
        return SystemMonitorTools()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_get_cpu_usage_mocked(self, mock_cpu_count, mock_cpu_percent, system_monitor):
        """Test get_cpu_usage with mocked psutil functions."""
        # Mock return values
        mock_cpu_percent.side_effect = [25.5, [10.0, 15.0, 20.0, 25.0]]
        mock_cpu_count.side_effect = [4, 2]  # logical, physical
        
        # Execute
        result = system_monitor.get_cpu_usage()
        
        # Verify
        assert result["overall_percent"] == 25.5
        assert result["per_core_percent"] == [10.0, 15.0, 20.0, 25.0]
        assert result["core_count"] == 4
        assert result["physical_core_count"] == 2
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage_mocked(self, mock_virtual_memory, system_monitor):
        """Test get_memory_usage with mocked psutil functions."""
        # Create a mock for virtual_memory result
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3  # 16 GB
        mock_memory.available = 8 * 1024**3  # 8 GB
        mock_memory.used = 8 * 1024**3  # 8 GB
        mock_memory.percent = 50.0
        
        mock_virtual_memory.return_value = mock_memory
        
        # Execute
        result = system_monitor.get_memory_usage()
        
        # Verify
        assert result["total_gb"] == 16.0
        assert result["available_gb"] == 8.0
        assert result["used_gb"] == 8.0
        assert result["percent_used"] == 50.0
        assert result["percent_available"] == 50.0 