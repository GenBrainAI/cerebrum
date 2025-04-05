"""
Test script for network tools.
"""
import os
import sys
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.server.tools.general_tools.network_tools import NetworkTools

def main():
    """Run tests for the network tools."""
    print("Testing Network Tools")
    print("====================")
    
    # Initialize the tools
    network = NetworkTools()
    
    # Test getting public IP
    print("\n🌐 Public IP Address:")
    ip_info = network.get_my_ip()
    print(json.dumps(ip_info, indent=2))
    
    # Test ping to a reliable host
    print("\n📡 Ping to Google DNS (8.8.8.8):")
    ping_result = network.ping_host("8.8.8.8")
    print(json.dumps(ping_result, indent=2))
    
    # Test DNS lookup
    print("\n🔍 DNS Lookup for google.com (A records):")
    dns_records = network.get_dns_records("google.com", "A")
    print(json.dumps(dns_records, indent=2))
    
    # Test checking a common port
    print("\n🔌 Port Check for google.com:443 (HTTPS):")
    port_check = network.check_port("google.com", 443)
    print(json.dumps(port_check, indent=2))
    
    # Test reverse DNS lookup on Google's DNS
    print("\n🔄 Reverse DNS Lookup for 8.8.8.8:")
    reverse_dns = network.reverse_dns_lookup("8.8.8.8")
    print(json.dumps(reverse_dns, indent=2))
    
    # Test get IP info
    print("\n📊 IP Information for 8.8.8.8:")
    ip_details = network.get_ip_info("8.8.8.8")
    print(json.dumps(ip_details, indent=2))
    
    # Test checking SSL certificate
    print("\n🔒 SSL Certificate for google.com:")
    ssl_info = network.check_ssl_certificate("google.com")
    print(json.dumps(ssl_info, indent=2, default=str))
    
    # Test DNS speed test (using smaller set of servers)
    print("\n⏱️ DNS Speed Test (limited servers):")
    dns_speed = network.run_dns_speed_test(["8.8.8.8", "1.1.1.1"])
    print(json.dumps(dns_speed, indent=2))
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    main() 