"""
Tests for the network tools.
"""
import os
import sys
import pytest
import socket
import subprocess
import requests
import dns.resolver
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.server.tools.general_tools.network_tools import NetworkTools


class TestNetworkTools:
    """Tests for the NetworkTools class."""
    
    @pytest.fixture
    def network_tools(self):
        """Create an instance of NetworkTools for testing."""
        return NetworkTools()
    
    # Tests that don't make external network requests
    def test_get_my_ip_mock(self, network_tools):
        """Test get_my_ip with mocked network requests."""
        # Setup mocks
        with patch('requests.get') as mock_get, patch('socket.socket') as mock_socket:
            # Mock the HTTP requests (all fail)
            mock_get.side_effect = Exception("Connection error")
            
            # Mock socket connection for local IP
            mock_socket_instance = MagicMock()
            mock_socket_instance.getsockname.return_value = ("192.168.1.100", 12345)
            mock_socket.return_value = mock_socket_instance
            
            # Execute
            result = network_tools.get_my_ip()
            
            # Verify
            assert result["ip"] == "192.168.1.100"
            assert result["source"] == "local_socket"
            assert result["is_local"] is True
            assert result["success"] is True
    
    @patch('socket.socket')
    def test_check_port_open(self, mock_socket, network_tools):
        """Test check_port for an open port."""
        # Setup socket mock
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.return_value = 0  # 0 means connection successful
        mock_socket.return_value = mock_socket_instance
        
        # Execute
        result = network_tools.check_port("example.com", 80)
        
        # Verify
        assert result["host"] == "example.com"
        assert result["port"] == 80
        assert result["status"] == "open"
        assert "response_time_ms" in result
        assert result["success"] is True
    
    @patch('socket.socket')
    def test_check_port_closed(self, mock_socket, network_tools):
        """Test check_port for a closed port."""
        # Setup socket mock
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.return_value = 111  # Connection refused
        mock_socket.return_value = mock_socket_instance
        
        # Execute
        result = network_tools.check_port("example.com", 80)
        
        # Verify
        assert result["host"] == "example.com"
        assert result["port"] == 80
        assert result["status"] == "closed"
        assert result["error_code"] == 111
        assert result["success"] is False
    
    @patch('socket.socket')
    def test_check_port_timeout(self, mock_socket, network_tools):
        """Test check_port with a connection timeout."""
        # Setup socket mock
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect_ex.side_effect = socket.timeout("Connection timed out")
        mock_socket.return_value = mock_socket_instance
        
        # Execute
        result = network_tools.check_port("example.com", 80)
        
        # Verify
        assert result["host"] == "example.com"
        assert result["port"] == 80
        assert result["status"] == "timeout"
        assert result["success"] is False


class TestNetworkToolsMocked:
    """Additional mocked tests for NetworkTools."""
    
    @pytest.fixture
    def network_tools(self):
        """Create an instance of NetworkTools for testing."""
        return NetworkTools()
    
    @patch('subprocess.run')
    def test_ping_host_success(self, mock_run, network_tools):
        """Test ping_host with a successful ping."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """
        PING google.com (142.250.72.78): 56 data bytes
        64 bytes from 142.250.72.78: icmp_seq=0 ttl=116 time=24.125 ms
        64 bytes from 142.250.72.78: icmp_seq=1 ttl=116 time=21.998 ms
        64 bytes from 142.250.72.78: icmp_seq=2 ttl=116 time=32.063 ms
        64 bytes from 142.250.72.78: icmp_seq=3 ttl=116 time=29.879 ms
        
        --- google.com ping statistics ---
        4 packets transmitted, 4 packets received, 0% packet loss
        round-trip min/avg/max/stddev = 21.998/27.016/32.063/4.237 ms
        """
        mock_run.return_value = mock_process
        
        # Execute
        result = network_tools.ping_host("google.com")
        
        # Verify
        assert result["success"] is True
        assert result["packet_loss_percent"] == 0
        assert "min_ms" in result
        assert "avg_ms" in result
        assert "max_ms" in result
    
    @patch('subprocess.run')
    def test_ping_host_failure(self, mock_run, network_tools):
        """Test ping_host with a failed ping."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 2
        mock_process.stdout = """
        ping: cannot resolve nonexistentdomain.example: Unknown host
        """
        mock_run.return_value = mock_process
        
        # Execute
        result = network_tools.ping_host("nonexistentdomain.example")
        
        # Verify
        assert result["success"] is False
    
    @patch('subprocess.run')
    def test_traceroute_success(self, mock_run, network_tools):
        """Test traceroute with a successful trace."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """
        traceroute to google.com (142.250.72.78), 30 hops max, 60 byte packets
         1  router.local (192.168.1.1)  1.234 ms  0.987 ms  0.876 ms
         2  isp-gateway.net (10.0.0.1)  15.432 ms  14.321 ms  13.210 ms
         3  backbone.isp.net (66.77.88.99)  20.987 ms  21.876 ms  22.765 ms
         4  google-peer.backbone.net (123.123.123.123)  24.876 ms  25.765 ms  26.654 ms
         5  142.250.72.78 (142.250.72.78)  28.765 ms  27.654 ms  26.543 ms
        """
        mock_run.return_value = mock_process
        
        # Execute
        result = network_tools.traceroute("google.com")
        
        # Verify
        assert isinstance(result, list)
        assert len(result) > 0
        assert "hop" in result[0]
        assert "ip" in result[0]
    
    @patch('dns.resolver.resolve')
    def test_get_dns_records_a(self, mock_resolve, network_tools):
        """Test get_dns_records for A records."""
        # Setup mock
        class MockRecord:
            def __init__(self, address):
                self.address = address
        
        mock_resolve.return_value = [MockRecord("192.0.2.1"), MockRecord("192.0.2.2")]
        
        # Execute
        result = network_tools.get_dns_records("example.com", "A")
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "A"
        assert result[0]["value"] == "192.0.2.1"
        assert result[1]["type"] == "A"
        assert result[1]["value"] == "192.0.2.2"
    
    @patch('dns.resolver.resolve')
    def test_get_dns_records_mx(self, mock_resolve, network_tools):
        """Test get_dns_records for MX records."""
        # Setup mock
        class MockMXRecord:
            def __init__(self, preference, exchange):
                self.preference = preference
                self.exchange = exchange
        
        mock_resolve.return_value = [
            MockMXRecord(10, "mail1.example.com"), 
            MockMXRecord(20, "mail2.example.com")
        ]
        
        # Execute
        result = network_tools.get_dns_records("example.com", "MX")
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "MX"
        assert result[0]["preference"] == 10
        assert result[0]["exchange"] == "mail1.example.com"
        assert result[1]["type"] == "MX"
        assert result[1]["preference"] == 20
        assert result[1]["exchange"] == "mail2.example.com"
    
    @patch('dns.resolver.resolve')
    @patch('dns.reversename.from_address')
    def test_reverse_dns_lookup(self, mock_from_address, mock_resolve, network_tools):
        """Test reverse_dns_lookup."""
        # Setup mocks
        class MockPTRRecord:
            def __init__(self, target):
                self.target = target
        
        mock_from_address.return_value = "4.3.2.1.in-addr.arpa."
        mock_resolve.return_value = [MockPTRRecord("host.example.com.")]
        
        # Execute
        result = network_tools.reverse_dns_lookup("1.2.3.4")
        
        # Verify
        assert result["ip"] == "1.2.3.4"
        assert result["hostnames"] == ["host.example.com"]
        assert result["success"] is True
    
    @patch('requests.get')
    def test_get_ip_info(self, mock_get, network_tools):
        """Test get_ip_info."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ip": "1.2.3.4",
            "country_name": "United States",
            "country_code": "US",
            "region": "California",
            "city": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "org": "Example ISP",
            "asn": "AS12345",
            "timezone": "America/Los_Angeles"
        }
        mock_get.return_value = mock_response
        
        # Execute
        result = network_tools.get_ip_info("1.2.3.4")
        
        # Verify
        assert result["ip"] == "1.2.3.4"
        assert result["country"] == "United States"
        assert result["country_code"] == "US"
        assert result["region"] == "California"
        assert result["city"] == "San Francisco"
        assert result["latitude"] == 37.7749
        assert result["longitude"] == -122.4194
        assert result["isp"] == "Example ISP"
        assert result["asn"] == "AS12345"
        assert result["timezone"] == "America/Los_Angeles"
        assert result["success"] is True 