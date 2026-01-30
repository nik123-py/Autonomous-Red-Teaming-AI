"""
Reconnaissance engine for network and port scanning.
Simulates network discovery without actual network access.
"""

import socket
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
import subprocess
import platform


@dataclass
class PortInfo:
    """Information about an open port"""
    port: int
    service: str
    version: Optional[str] = None
    banner: Optional[str] = None


@dataclass
class ServiceInfo:
    """Information about a discovered service"""
    name: str
    port: int
    protocol: str
    version: Optional[str] = None
    vulnerabilities: List[str] = None


class ReconEngine:
    """
    Network reconnaissance engine.
    Performs port scanning and service discovery.
    """

    # Common ports and services
    COMMON_PORTS = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        445: "SMB",
        3306: "MySQL",
        5432: "PostgreSQL",
        8080: "HTTP-Proxy",
        8443: "HTTPS-Alt",
        9000: "SonarQube",
        27017: "MongoDB",
        6379: "Redis",
        9200: "Elasticsearch"
    }

    # Service banners (simulated)
    SERVICE_BANNERS = {
        "SSH": "SSH-2.0-OpenSSH_8.2",
        "HTTP": "Apache/2.4.41",
        "HTTPS": "nginx/1.18.0",
        "MySQL": "5.7.33-log",
        "PostgreSQL": "PostgreSQL 13.2",
        "FTP": "vsftpd 3.0.3",
        "SMTP": "Postfix smtpd"
    }

    def __init__(self):
        """Initialize reconnaissance engine"""
        self.scan_timeout = 1.0  # Timeout for port scans

    def scan_ports(
        self,
        target: str,
        ports: Optional[List[int]] = None,
        scan_type: str = "syn"  # syn, connect, full
    ) -> Dict:
        """
        Scan target for open ports.
        
        Args:
            target: Target hostname or IP
            ports: List of ports to scan (default: common ports)
            scan_type: Type of scan (syn, connect, full)
            
        Returns:
            Dictionary with open_ports and services
        """
        if ports is None:
            ports = list(self.COMMON_PORTS.keys())

        open_ports = []
        services = []

        # Simulate port scanning (in real scenario, would use nmap or socket)
        # For MVP, we simulate based on target characteristics
        discovered_ports = self._simulate_port_scan(target, ports)

        for port_info in discovered_ports:
            open_ports.append({
                "port": port_info.port,
                "service": port_info.service,
                "state": "open",
                "version": port_info.version,
                "banner": port_info.banner
            })

            services.append({
                "name": port_info.service,
                "port": port_info.port,
                "protocol": "tcp",
                "version": port_info.version,
                "vulnerabilities": []  # Will be populated by vulnerability scanner
            })

        return {
            "target": target,
            "scan_type": scan_type,
            "open_ports": open_ports,
            "services": services,
            "total_ports_scanned": len(ports),
            "open_ports_count": len(open_ports)
        }

    def _simulate_port_scan(self, target: str, ports: List[int]) -> List[PortInfo]:
        """
        Simulate port scanning.
        In production, this would use actual socket connections or nmap.
        For MVP, we simulate realistic results.
        """
        discovered = []

        # Simulate discovery based on target (deterministic for same target)
        # In real scenario, would actually connect to ports
        target_hash = hash(target) % 1000

        for port in ports:
            # Simulate port being open with some probability
            # Common ports more likely to be open
            probability = 0.3 if port in [80, 443, 22, 21] else 0.1
            
            # Make it deterministic based on target
            port_hash = hash(f"{target}:{port}") % 100
            is_open = port_hash < (probability * 100)

            if is_open:
                service = self.COMMON_PORTS.get(port, f"Unknown-{port}")
                banner = self.SERVICE_BANNERS.get(service)
                
                discovered.append(PortInfo(
                    port=port,
                    service=service,
                    version=banner,
                    banner=banner
                ))

        return discovered

    def scan_host(self, target: str) -> Dict:
        """
        Perform full host scan (ports + OS detection).
        
        Args:
            target: Target hostname or IP
            
        Returns:
            Complete host information
        """
        # Port scan
        port_scan = self.scan_ports(target)

        # OS detection (simulated)
        os_info = self._detect_os(target)

        return {
            **port_scan,
            "os": os_info,
            "hostname": target,
            "alive": True
        }

    def _detect_os(self, target: str) -> Dict:
        """Simulate OS detection"""
        # In real scenario, would use nmap -O or similar
        os_types = ["Linux", "Windows", "Unix"]
        target_hash = hash(target) % len(os_types)
        
        return {
            "type": os_types[target_hash],
            "version": "Unknown",
            "confidence": random.randint(70, 95)
        }

    def get_exposed_endpoints(self, target: str, service: str) -> List[str]:
        """
        Get exposed endpoints for a service.
        Simulates directory/file discovery.
        """
        # Common endpoints by service
        endpoints_by_service = {
            "HTTP": [
                "/",
                "/api",
                "/admin",
                "/login",
                "/dashboard",
                "/api/users",
                "/api/products"
            ],
            "HTTPS": [
                "/",
                "/api",
                "/admin",
                "/login"
            ],
            "FTP": [
                "/",
                "/pub",
                "/uploads"
            ]
        }

        endpoints = endpoints_by_service.get(service, ["/"])
        
        # Add some randomization
        discovered = random.sample(endpoints, min(len(endpoints), random.randint(2, 5)))
        
        return discovered

    def perform_network_scan(self, network: str) -> Dict:
        """
        Scan entire network range.
        
        Args:
            network: Network CIDR (e.g., "192.168.1.0/24")
            
        Returns:
            List of discovered hosts
        """
        # Simulate network scan
        # In real scenario, would use nmap or similar
        discovered_hosts = []

        # Simulate finding 2-5 hosts
        num_hosts = random.randint(2, 5)
        for i in range(num_hosts):
            host = f"192.168.1.{random.randint(1, 254)}"
            host_info = self.scan_host(host)
            discovered_hosts.append(host_info)

        return {
            "network": network,
            "discovered_hosts": discovered_hosts,
            "total_hosts": len(discovered_hosts)
        }

