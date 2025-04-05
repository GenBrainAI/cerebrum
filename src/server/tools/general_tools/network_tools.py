"""
Network and security tools for Cerebrum.

This module provides tools for network diagnostics, DNS lookups, 
traceroute, ping tests, and other network-related functionality.
"""
import socket
import subprocess
import platform
import re
import ipaddress
import time
import requests
import json
from typing import Dict, List, Optional, Union, Tuple
import dns.resolver
import dns.reversename
import ssl
import OpenSSL
import datetime

class NetworkTools:
    """Tools for network diagnostics and security."""
    
    def ping_host(self, host: str, count: int = 4, timeout: int = 5) -> Dict:
        """
        Ping a host and return results.
        
        Args:
            host: Hostname or IP address to ping
            count: Number of ping packets to send
            timeout: Timeout in seconds
            
        Returns:
            Dictionary containing ping statistics
        """
        # Determine OS-specific ping command
        system = platform.system().lower()
        
        if system == "windows":
            cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
        else:  # Linux, Darwin (macOS), etc.
            cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
        
        try:
            # Run ping command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            output = result.stdout
            
            # Parse ping output
            stats = {"success": result.returncode == 0, "output": output}
            
            # Extract packet loss 
            if system == "windows":
                loss_match = re.search(r"(\d+)% loss", output)
            else:
                loss_match = re.search(r"(\d+)% packet loss", output)
                
            if loss_match:
                stats["packet_loss_percent"] = int(loss_match.group(1))
            
            # Extract round-trip times
            if system == "windows":
                time_match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output)
                if time_match:
                    stats["min_ms"] = int(time_match.group(1))
                    stats["max_ms"] = int(time_match.group(2))
                    stats["avg_ms"] = int(time_match.group(3))
            else:
                time_match = re.search(r"min/avg/max/.*?(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/", output)
                if time_match:
                    stats["min_ms"] = float(time_match.group(1))
                    stats["avg_ms"] = float(time_match.group(2))
                    stats["max_ms"] = float(time_match.group(3))
            
            return stats
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Ping command timed out",
                "packet_loss_percent": 100
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "packet_loss_percent": 100
            }
    
    def traceroute(self, host: str, max_hops: int = 30, timeout: int = 5) -> List[Dict]:
        """
        Perform a traceroute to a host.
        
        Args:
            host: Hostname or IP address to trace
            max_hops: Maximum number of hops
            timeout: Timeout in seconds
            
        Returns:
            List of dictionaries representing each hop in the traceroute
        """
        system = platform.system().lower()
        
        # Set command based on OS
        if system == "windows":
            cmd = ["tracert", "-d", "-h", str(max_hops), "-w", str(timeout * 1000), host]
        else:  # Linux, Darwin (macOS), etc.
            cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", str(timeout), host]
        
        try:
            # Run traceroute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_hops * timeout)
            output = result.stdout
            
            # Parse traceroute output
            hops = []
            
            # Different regex patterns for different OS outputs
            if system == "windows":
                hop_pattern = r"^\s*(\d+)\s+(?:(\d+)\s+ms|\*)\s+(?:(\d+)\s+ms|\*)\s+(?:(\d+)\s+ms|\*)\s+(?:(\d+\.\d+\.\d+\.\d+)|(?:\*))$"
            else:
                hop_pattern = r"^\s*(\d+)\s+(?:([\d.]+)\s+(\d+(?:\.\d+)?)?\s*ms|(?:\* \* \*))\s+(?:([\d.]+))?$"
            
            for line in output.split('\n'):
                if system == "windows":
                    match = re.search(hop_pattern, line)
                    if match:
                        hop_num = int(match.group(1))
                        times = [float(t) for t in match.groups()[1:4] if t]
                        ip = match.group(5) if match.group(5) else "*"
                        
                        if times:
                            avg_time = sum(times) / len(times)
                        else:
                            avg_time = None
                        
                        hops.append({
                            "hop": hop_num,
                            "ip": ip,
                            "avg_ms": avg_time,
                            "times_ms": times
                        })
                else:
                    # For Unix-like systems
                    if re.search(r"^\s*\d+", line):
                        parts = line.split()
                        hop_num = int(parts[0])
                        ip = "*"
                        times = []
                        
                        for part in parts[1:]:
                            if re.match(r"^\d+\.\d+\.\d+\.\d+$", part):
                                ip = part
                            elif re.match(r"^\d+\.\d+$", part):
                                times.append(float(part))
                        
                        avg_time = sum(times) / len(times) if times else None
                        
                        hops.append({
                            "hop": hop_num,
                            "ip": ip,
                            "avg_ms": avg_time,
                            "times_ms": times
                        })
            
            return hops
        
        except subprocess.TimeoutExpired:
            return [{"error": "Traceroute command timed out"}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_dns_records(self, domain: str, record_type: str = "A") -> List[Dict]:
        """
        Get DNS records for a domain.
        
        Args:
            domain: Domain name to query
            record_type: Type of DNS record (A, AAAA, MX, TXT, NS, etc.)
            
        Returns:
            List of dictionaries containing DNS records
        """
        try:
            # Validate record type
            valid_types = ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "SRV", "CAA", "PTR"]
            record_type = record_type.upper()
            
            if record_type not in valid_types:
                return [{"error": f"Invalid record type. Valid types are: {', '.join(valid_types)}"}]
            
            # Perform DNS query
            answers = dns.resolver.resolve(domain, record_type)
            
            records = []
            for rdata in answers:
                if record_type == "A" or record_type == "AAAA":
                    records.append({"type": record_type, "value": str(rdata.address)})
                elif record_type == "MX":
                    records.append({
                        "type": record_type,
                        "preference": rdata.preference,
                        "exchange": str(rdata.exchange)
                    })
                elif record_type == "NS":
                    records.append({"type": record_type, "value": str(rdata.target)})
                elif record_type == "TXT":
                    records.append({"type": record_type, "value": str(rdata).strip('"')})
                elif record_type == "SOA":
                    records.append({
                        "type": record_type,
                        "mname": str(rdata.mname),
                        "rname": str(rdata.rname),
                        "serial": rdata.serial,
                        "refresh": rdata.refresh,
                        "retry": rdata.retry,
                        "expire": rdata.expire,
                        "minimum": rdata.minimum
                    })
                elif record_type == "CNAME":
                    records.append({"type": record_type, "value": str(rdata.target)})
                elif record_type == "SRV":
                    records.append({
                        "type": record_type,
                        "priority": rdata.priority,
                        "weight": rdata.weight,
                        "port": rdata.port,
                        "target": str(rdata.target)
                    })
                else:
                    records.append({"type": record_type, "value": str(rdata)})
            
            return records
            
        except dns.resolver.NoAnswer:
            return [{"type": record_type, "no_records": True, "message": f"No {record_type} records found for {domain}"}]
        except dns.resolver.NXDOMAIN:
            return [{"error": f"Domain {domain} does not exist"}]
        except dns.resolver.Timeout:
            return [{"error": f"DNS query for {domain} timed out"}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def reverse_dns_lookup(self, ip: str) -> Dict:
        """
        Perform a reverse DNS lookup on an IP address.
        
        Args:
            ip: IP address to lookup
            
        Returns:
            Dictionary containing reverse DNS information
        """
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
            
            # Perform reverse lookup
            addr = dns.reversename.from_address(ip)
            answers = dns.resolver.resolve(addr, "PTR")
            
            hostnames = [str(rdata.target).rstrip('.') for rdata in answers]
            
            return {
                "ip": ip,
                "hostnames": hostnames,
                "success": True
            }
        except ValueError:
            return {"error": f"Invalid IP address: {ip}", "success": False}
        except dns.resolver.NoAnswer:
            return {"ip": ip, "hostnames": [], "message": "No PTR records found", "success": True}
        except dns.resolver.NXDOMAIN:
            return {"ip": ip, "hostnames": [], "message": "No reverse DNS entry exists", "success": True}
        except Exception as e:
            return {"ip": ip, "error": str(e), "success": False}
    
    def get_ip_info(self, ip: str) -> Dict:
        """
        Get information about an IP address using external IP geolocation API.
        
        Args:
            ip: IP address to lookup
            
        Returns:
            Dictionary containing IP information
        """
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
            
            # Make request to IP API
            response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "ip": ip,
                    "country": data.get("country_name"),
                    "country_code": data.get("country_code"),
                    "region": data.get("region"),
                    "city": data.get("city"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "isp": data.get("org"),
                    "asn": data.get("asn"),
                    "timezone": data.get("timezone"),
                    "success": True
                }
            else:
                return {"ip": ip, "error": f"API request failed with status code {response.status_code}", "success": False}
        
        except ValueError:
            return {"error": f"Invalid IP address: {ip}", "success": False}
        except requests.RequestException as e:
            return {"ip": ip, "error": f"Request failed: {str(e)}", "success": False}
        except json.JSONDecodeError:
            return {"ip": ip, "error": "Invalid response from API", "success": False}
        except Exception as e:
            return {"ip": ip, "error": str(e), "success": False}
    
    def get_my_ip(self) -> Dict:
        """
        Get the public IP address of the current system.
        
        Returns:
            Dictionary containing the public IP address
        """
        try:
            # Try multiple IP services in case one fails
            services = [
                "https://api.ipify.org?format=json",
                "https://ipinfo.io/json",
                "https://ifconfig.me/all.json"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        ip = data.get("ip", None)
                        if ip:
                            return {
                                "ip": ip,
                                "source": service,
                                "success": True
                            }
                except:
                    continue
            
            # If all services fail, try socket-based lookup
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            return {
                "ip": local_ip,
                "source": "local_socket",
                "is_local": True,
                "note": "This is a local IP, not a public IP",
                "success": True
            }
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def check_port(self, host: str, port: int, timeout: int = 5) -> Dict:
        """
        Check if a specific port is open on a host.
        
        Args:
            host: Hostname or IP address
            port: Port number to check
            timeout: Timeout in seconds
            
        Returns:
            Dictionary containing port status
        """
        try:
            # Create socket and attempt to connect
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_time = time.time()
            result = sock.connect_ex((host, port))
            response_time = time.time() - start_time
            
            sock.close()
            
            if result == 0:
                return {
                    "host": host,
                    "port": port,
                    "status": "open",
                    "response_time_ms": round(response_time * 1000, 2),
                    "success": True
                }
            else:
                return {
                    "host": host,
                    "port": port,
                    "status": "closed",
                    "error_code": result,
                    "success": False
                }
                
        except socket.timeout:
            return {
                "host": host,
                "port": port,
                "status": "timeout",
                "success": False
            }
        except socket.gaierror:
            return {
                "host": host,
                "port": port,
                "status": "error",
                "error": "Name resolution failed",
                "success": False
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "status": "error",
                "error": str(e),
                "success": False
            }
    
    def scan_common_ports(self, host: str, timeout: int = 2) -> List[Dict]:
        """
        Scan common ports on a host.
        
        Args:
            host: Hostname or IP address
            timeout: Timeout in seconds per port
            
        Returns:
            List of dictionaries containing port scan results
        """
        # Common ports and their services
        common_ports = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            465: "SMTPS",
            587: "SMTP (submission)",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            8080: "HTTP (alt)",
            8443: "HTTPS (alt)"
        }
        
        results = []
        
        for port, service in common_ports.items():
            result = self.check_port(host, port, timeout)
            result["service"] = service
            results.append(result)
            
            # Small delay to avoid overwhelming the target
            time.sleep(0.1)
        
        return results
    
    def check_ssl_certificate(self, host: str, port: int = 443) -> Dict:
        """
        Check SSL certificate information for a host.
        
        Args:
            host: Hostname or IP address
            port: Port number (default: 443)
            
        Returns:
            Dictionary containing SSL certificate information
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Connect to the server
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    # Get certificate
                    cert_binary = ssock.getpeercert(binary_form=True)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_binary)
                    
                    # Extract certificate information
                    cert_info = {
                        "subject": {},
                        "issuer": {},
                        "valid_from": None,
                        "valid_until": None,
                        "version": x509.get_version(),
                        "serial_number": hex(x509.get_serial_number()),
                        "signature_algorithm": x509.get_signature_algorithm().decode(),
                        "success": True
                    }
                    
                    # Extract subject
                    for item in x509.get_subject().get_components():
                        key = item[0].decode()
                        value = item[1].decode()
                        cert_info["subject"][key] = value
                    
                    # Extract issuer
                    for item in x509.get_issuer().get_components():
                        key = item[0].decode()
                        value = item[1].decode()
                        cert_info["issuer"][key] = value
                    
                    # Extract validity dates
                    not_before = x509.get_notBefore().decode()
                    not_after = x509.get_notAfter().decode()
                    
                    # Convert ASN1 time format to datetime
                    fmt = "%Y%m%d%H%M%SZ"
                    cert_info["valid_from"] = datetime.datetime.strptime(not_before, fmt).strftime("%Y-%m-%d %H:%M:%S")
                    cert_info["valid_until"] = datetime.datetime.strptime(not_after, fmt).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Calculate days until expiration
                    expiry_date = datetime.datetime.strptime(not_after, fmt)
                    now = datetime.datetime.utcnow()
                    cert_info["days_until_expiry"] = (expiry_date - now).days
                    cert_info["is_expired"] = now > expiry_date
                    
                    # Extract alternative names
                    san_extension = None
                    for i in range(x509.get_extension_count()):
                        ext = x509.get_extension(i)
                        if ext.get_short_name().decode() == "subjectAltName":
                            san_extension = ext
                            break
                    
                    if san_extension:
                        sans = str(san_extension).split(", ")
                        cert_info["subject_alternative_names"] = [san.split(":", 1)[1] for san in sans]
                    
                    return cert_info
                    
        except ssl.SSLError as e:
            return {"host": host, "port": port, "error": f"SSL error: {str(e)}", "success": False}
        except socket.timeout:
            return {"host": host, "port": port, "error": "Connection timed out", "success": False}
        except socket.gaierror:
            return {"host": host, "port": port, "error": "Name resolution failed", "success": False}
        except OpenSSL.crypto.Error as e:
            return {"host": host, "port": port, "error": f"Certificate error: {str(e)}", "success": False}
        except Exception as e:
            return {"host": host, "port": port, "error": str(e), "success": False}
    
    def check_domain_availability(self, domain: str) -> Dict:
        """
        Check if a domain is available for registration.
        
        Args:
            domain: Domain name to check
            
        Returns:
            Dictionary containing domain availability information
        """
        try:
            # Try to resolve the domain
            answers = dns.resolver.resolve(domain, "A")
            
            return {
                "domain": domain,
                "available": False,
                "message": "Domain exists and resolves to IP addresses",
                "ip_addresses": [str(rdata.address) for rdata in answers]
            }
        except dns.resolver.NoAnswer:
            # Domain exists but has no A records
            return {
                "domain": domain,
                "available": False,
                "message": "Domain exists but has no A records"
            }
        except dns.resolver.NXDOMAIN:
            # Domain does not exist (might be available)
            return {
                "domain": domain,
                "available": True,
                "message": "Domain does not exist and may be available for registration"
            }
        except dns.resolver.Timeout:
            return {
                "domain": domain,
                "error": "DNS query timed out",
                "available": None,
                "message": "Unable to determine domain availability due to timeout"
            }
        except Exception as e:
            return {
                "domain": domain,
                "error": str(e),
                "available": None,
                "message": "Unable to determine domain availability"
            }
            
    def run_dns_speed_test(self, dns_servers: List[str] = None) -> List[Dict]:
        """
        Test the response time of DNS servers.
        
        Args:
            dns_servers: List of DNS servers to test. If None, uses common public DNS servers.
            
        Returns:
            List of dictionaries containing DNS server response times
        """
        if dns_servers is None:
            # Default list of public DNS servers to test
            dns_servers = [
                "8.8.8.8",        # Google
                "8.8.4.4",        # Google
                "1.1.1.1",        # Cloudflare
                "1.0.0.1",        # Cloudflare
                "9.9.9.9",        # Quad9
                "149.112.112.112", # Quad9
                "208.67.222.222", # OpenDNS
                "208.67.220.220"  # OpenDNS
            ]
        
        results = []
        
        # Test domains
        test_domains = ["google.com", "amazon.com", "microsoft.com", "apple.com"]
        
        for server in dns_servers:
            result = {
                "server": server,
                "success": True,
                "avg_response_time_ms": 0,
                "responses": []
            }
            
            try:
                # Configure resolver to use this server
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [server]
                resolver.timeout = 3
                resolver.lifetime = 3
                
                times = []
                errors = 0
                
                # Query each test domain
                for domain in test_domains:
                    try:
                        start_time = time.time()
                        resolver.resolve(domain, "A")
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000  # Convert to ms
                        times.append(response_time)
                        
                        result["responses"].append({
                            "domain": domain,
                            "response_time_ms": round(response_time, 2),
                            "success": True
                        })
                    except Exception as e:
                        errors += 1
                        result["responses"].append({
                            "domain": domain,
                            "error": str(e),
                            "success": False
                        })
                
                # Calculate average response time
                if times:
                    result["avg_response_time_ms"] = round(sum(times) / len(times), 2)
                    result["min_response_time_ms"] = round(min(times), 2)
                    result["max_response_time_ms"] = round(max(times), 2)
                    result["success_rate"] = round((len(times) / len(test_domains)) * 100, 1)
                else:
                    result["success"] = False
                    result["error"] = "All queries failed"
                
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
            
            results.append(result)
        
        # Sort results by average response time
        return sorted(results, key=lambda x: x.get("avg_response_time_ms", float("inf")))


def register_network_tools(catalog = None) -> List[str]:
    """Register the network tools with the tools catalog.
    
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
    network_tools = NetworkTools()
    
    # Register tool and its methods
    registered_names = catalog.register_instance(
        network_tools, 
        "network_tools", 
        exclude_base_methods=True, 
        register_instance_itself=True
    )
    
    print(f"✅ Registered NetworkTools with {len(registered_names)} methods")
    return registered_names 