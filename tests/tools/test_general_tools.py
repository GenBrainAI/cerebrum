"""
Unit tests for general tools including network and system monitoring tools.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest

from src.server.tools.general_tools.network_tools import NetworkTools
from src.server.tools.general_tools.system_monitor_tools import SystemMonitorTools


class TestNetworkTools(unittest.TestCase):
    """Test suite for NetworkTools functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.network = NetworkTools()

    @patch('src.server.tools.general_tools.network_tools.requests.get')
    def test_get_my_ip(self, mock_get):
        """Test getting public IP address."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ip": "203.0.113.1",
            "hostname": "example.com",
            "city": "New York",
            "region": "New York",
            "country": "US",
            "loc": "40.7128,-74.0060",
            "org": "AS12345 Example ISP",
            "postal": "10001",
            "timezone": "America/New_York"
        }
        mock_get.return_value = mock_response

        # Call the method
        result = self.network.get_my_ip()

        # Assertions
        self.assertEqual(result["ip"], "203.0.113.1")
        self.assertEqual(result["city"], "New York")
        self.assertEqual(result["country"], "US")
        mock_get.assert_called_once()

    @patch('src.server.tools.general_tools.network_tools.subprocess.run')
    def test_ping_host(self, mock_run):
        """Test pinging a host."""
        # Mock response
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "64 bytes from 8.8.8.8: icmp_seq=1 ttl=57 time=14.5 ms"
        mock_run.return_value = mock_process

        # Call the method
        result = self.network.ping_host("8.8.8.8")

        # Assertions
        self.assertTrue(result["reachable"])
        self.assertIn("time", result)
        mock_run.assert_called_once()

    @patch('src.server.tools.general_tools.network_tools.socket.socket')
    def test_check_port(self, mock_socket):
        """Test checking if a port is open."""
        # Mock socket
        mock_instance = MagicMock()
        mock_instance.connect_ex.return_value = 0  # 0 means success
        mock_socket.return_value.__enter__.return_value = mock_instance

        # Call the method
        result = self.network.check_port("google.com", 443)

        # Assertions
        self.assertTrue(result["open"])
        self.assertEqual(result["host"], "google.com")
        self.assertEqual(result["port"], 443)
        mock_instance.connect_ex.assert_called_once()

    @patch('src.server.tools.general_tools.network_tools.dns')
    def test_get_dns_records(self, mock_dns):
        """Test getting DNS records."""
        # Mock resolver
        mock_resolver = MagicMock()
        mock_record = MagicMock()
        mock_record.to_text.return_value = "203.0.113.1"
        mock_resolver.resolve.return_value = [mock_record]
        mock_dns.resolver.Resolver.return_value = mock_resolver

        # Call the method
        result = self.network.get_dns_records("example.com", "A")

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(result["record_type"], "A")
        self.assertIn("records", result)
        mock_resolver.resolve.assert_called_once_with("example.com", "A")

    @patch('src.server.tools.general_tools.network_tools.socket.gethostbyaddr')
    def test_reverse_dns_lookup(self, mock_gethostbyaddr):
        """Test reverse DNS lookup."""
        # Mock response
        mock_gethostbyaddr.return_value = ("dns.google", [], ["8.8.8.8"])

        # Call the method
        result = self.network.reverse_dns_lookup("8.8.8.8")

        # Assertions
        self.assertEqual(result["ip"], "8.8.8.8")
        self.assertEqual(result["hostname"], "dns.google")
        mock_gethostbyaddr.assert_called_once_with("8.8.8.8")

    @patch('src.server.tools.general_tools.network_tools.ssl')
    @patch('src.server.tools.general_tools.network_tools.socket.create_connection')
    def test_check_ssl_certificate(self, mock_create_connection, mock_ssl):
        """Test checking SSL certificate."""
        # Mock connection and certificate
        mock_socket = MagicMock()
        mock_create_connection.return_value = mock_socket
        
        mock_context = MagicMock()
        mock_ssl.create_default_context.return_value = mock_context
        
        mock_ssl_socket = MagicMock()
        mock_context.wrap_socket.return_value = mock_ssl_socket
        
        mock_cert = {
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("commonName", "Example CA"),),),
            "version": 3,
            "serialNumber": "01:23:45:67:89:ab:cd:ef",
            "notBefore": "Jan 01 00:00:00 2023 GMT",
            "notAfter": "Dec 31 23:59:59 2023 GMT"
        }
        mock_ssl_socket.getpeercert.return_value = mock_cert

        # Call the method
        result = self.network.check_ssl_certificate("example.com")

        # Assertions
        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(result["common_name"], "example.com")
        self.assertEqual(result["issuer"], "Example CA")
        self.assertEqual(result["valid_until"], "Dec 31 23:59:59 2023 GMT")
        mock_create_connection.assert_called_once()
        mock_ssl_socket.getpeercert.assert_called_once()


class TestSystemMonitorTools(unittest.TestCase):
    """Test suite for SystemMonitorTools functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.monitor = SystemMonitorTools()

    @patch('src.server.tools.general_tools.system_monitor_tools.platform')
    def test_get_system_info(self, mock_platform):
        """Test getting system information."""
        # Mock platform responses
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "20.6.0"
        mock_platform.version.return_value = "Darwin Kernel Version 20.6.0"
        mock_platform.architecture.return_value = ("64bit", "")
        mock_platform.machine.return_value = "x86_64"
        mock_platform.processor.return_value = "i386"
        mock_platform.node.return_value = "test-computer"

        # Call the method
        result = self.monitor.get_system_info()

        # Assertions
        self.assertEqual(result["system"], "Darwin")
        self.assertEqual(result["release"], "20.6.0")
        self.assertEqual(result["version"], "Darwin Kernel Version 20.6.0")
        self.assertEqual(result["architecture"], "64bit")
        self.assertEqual(result["machine"], "x86_64")
        self.assertEqual(result["processor"], "i386")
        self.assertEqual(result["hostname"], "test-computer")
        mock_platform.system.assert_called_once()

    @patch('src.server.tools.general_tools.system_monitor_tools.platform')
    @patch('src.server.tools.general_tools.system_monitor_tools.os')
    def test_get_detailed_os_info(self, mock_os, mock_platform):
        """Test getting detailed OS information."""
        # Mock responses
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "20.6.0"
        mock_platform.version.return_value = "Darwin Kernel Version 20.6.0"
        mock_platform.mac_ver.return_value = ("11.6", ("", "", ""), "x86_64")
        mock_os.uname.return_value = MagicMock(
            release="20.6.0",
            version="Darwin Kernel Version 20.6.0",
            machine="x86_64"
        )

        # Call the method
        result = self.monitor.get_detailed_os_info()

        # Assertions
        self.assertEqual(result["os_type"], "Darwin")
        self.assertEqual(result["release"], "20.6.0")
        mock_platform.system.assert_called_once()

    @patch('src.server.tools.general_tools.system_monitor_tools.psutil')
    def test_get_cpu_usage(self, mock_psutil):
        """Test getting CPU usage."""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.cpu_freq.return_value = MagicMock(
            current=2500,
            min=2000,
            max=3000
        )

        # Call the method
        result = self.monitor.get_cpu_usage()

        # Assertions
        self.assertEqual(result["percent"], 25.0)
        self.assertEqual(result["cores"], 8)
        self.assertEqual(result["frequency_mhz"], 2500)
        mock_psutil.cpu_percent.assert_called_once()

    @patch('src.server.tools.general_tools.system_monitor_tools.psutil')
    def test_get_memory_usage(self, mock_psutil):
        """Test getting memory usage."""
        # Mock psutil responses
        mock_mem = MagicMock()
        mock_mem.total = 16000000000  # 16GB
        mock_mem.available = 8000000000  # 8GB
        mock_mem.used = 8000000000  # 8GB
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        # Call the method
        result = self.monitor.get_memory_usage()

        # Assertions
        self.assertEqual(result["total_gb"], 14.9)  # 16GB -> 14.9GiB
        self.assertEqual(result["available_gb"], 7.45)  # 8GB -> 7.45GiB
        self.assertEqual(result["used_gb"], 7.45)  # 8GB -> 7.45GiB
        self.assertEqual(result["percent"], 50.0)
        mock_psutil.virtual_memory.assert_called_once()

    @patch('src.server.tools.general_tools.system_monitor_tools.psutil')
    @patch('src.server.tools.general_tools.system_monitor_tools.os.path')
    def test_get_disk_usage(self, mock_path, mock_psutil):
        """Test getting disk usage."""
        # Mock responses
        mock_path.abspath.return_value = "/test/path"
        mock_disk = MagicMock()
        mock_disk.total = 500000000000  # 500GB
        mock_disk.used = 250000000000  # 250GB
        mock_disk.free = 250000000000  # 250GB
        mock_disk.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_disk

        # Call the method
        result = self.monitor.get_disk_usage("/test/path")

        # Assertions
        self.assertEqual(result["path"], "/test/path")
        self.assertEqual(result["total_gb"], 465.66)  # 500GB -> 465.66GiB
        self.assertEqual(result["used_gb"], 232.83)  # 250GB -> 232.83GiB
        self.assertEqual(result["free_gb"], 232.83)  # 250GB -> 232.83GiB
        self.assertEqual(result["percent"], 50.0)
        mock_psutil.disk_usage.assert_called_once()

    @patch('src.server.tools.general_tools.system_monitor_tools.psutil')
    def test_get_process_list(self, mock_psutil):
        """Test getting process list."""
        # Mock processes
        mock_process1 = MagicMock()
        mock_process1.pid = 1
        mock_process1.name.return_value = "process1"
        mock_process1.status.return_value = "running"
        mock_process1.cpu_percent.return_value = 10.0
        mock_process1.memory_percent.return_value = 5.0
        
        mock_process2 = MagicMock()
        mock_process2.pid = 2
        mock_process2.name.return_value = "process2"
        mock_process2.status.return_value = "running"
        mock_process2.cpu_percent.return_value = 20.0
        mock_process2.memory_percent.return_value = 15.0
        
        mock_psutil.process_iter.return_value = [mock_process1, mock_process2]

        # Call the method
        result = self.monitor.get_process_list(2)

        # Assertions
        self.assertEqual(len(result["processes"]), 2)
        self.assertEqual(result["processes"][0]["pid"], 2)  # Highest CPU should be first
        self.assertEqual(result["processes"][0]["name"], "process2")
        self.assertEqual(result["processes"][0]["cpu_percent"], 20.0)
        self.assertEqual(result["processes"][1]["pid"], 1)
        self.assertEqual(result["processes"][1]["name"], "process1")
        self.assertEqual(result["processes"][1]["cpu_percent"], 10.0)
        mock_psutil.process_iter.assert_called_once()


if __name__ == "__main__":
    unittest.main() 