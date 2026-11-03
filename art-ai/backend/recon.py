"""
Reconnaissance engine for network and port scanning.

This performs REAL TCP connect scanning and banner grabbing. It previously returned
randomized fake results; every function here now reflects the actual state of the
target.

SCOPE GUARD: scanning is restricted to loopback and RFC1918/private addresses (the
local vulnerable lab). Any attempt to scan a public/third-party address raises
``UnauthorizedTargetError``. This keeps the tool inside the authorized sandbox.
"""

import ipaddress
import platform
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional


class UnauthorizedTargetError(ValueError):
    """Raised when a scan target is outside the authorized local lab scope."""


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
    Performs real port scanning and service discovery against local lab targets.
    """

    # Port -> default service label. Includes the local ART-AI lab ports.
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
        # --- local ART-AI vulnerable lab ---
        3001: "HTTP",   # Juice Shop
        3002: "HTTP",   # DVWA
        3003: "HTTP",   # vulnerable Flask API
        3004: "HTTP",   # WebGoat
        3005: "HTTP",   # VAmPI
        3006: "HTTP",   # bWAPP
        3306: "MySQL",
        5000: "HTTP",
        5432: "PostgreSQL",
        8000: "HTTP",
        8003: "HTTP",   # ART-AI backend
        8080: "HTTP-Proxy",
        8443: "HTTPS-Alt",
        9000: "SonarQube",
        27017: "MongoDB",
        6379: "Redis",
        9200: "Elasticsearch",
        11434: "Ollama",
    }

    # Ports we should speak HTTP to when grabbing a banner.
    HTTP_PORTS = {80, 443, 3001, 3002, 3003, 3004, 3005, 3006,
                  5000, 8000, 8003, 8080, 8443, 9200, 9000, 11434}

    def __init__(self, scan_timeout: float = 0.6, max_workers: int = 100):
        """Initialize reconnaissance engine."""
        self.scan_timeout = scan_timeout
        self.max_workers = max_workers

    # ------------------------------------------------------------------ scope
    @staticmethod
    def resolve_and_authorize(target: str) -> str:
        """Resolve ``target`` and confirm it is a local/private address.

        Returns the resolved IP string. Raises UnauthorizedTargetError otherwise.
        """
        host = target.strip()
        # strip scheme/path if a URL was passed
        host = re.sub(r"^[a-zA-Z]+://", "", host).split("/")[0]
        # strip :port
        if host.count(":") == 1:
            host = host.split(":")[0]
        try:
            ip_str = socket.gethostbyname(host)
        except OSError as e:
            raise UnauthorizedTargetError(f"Cannot resolve target '{target}': {e}")

        ip = ipaddress.ip_address(ip_str)
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            raise UnauthorizedTargetError(
                f"Target '{target}' resolves to {ip_str}, which is outside the "
                f"authorized local-lab scope. Only loopback/private addresses may "
                f"be scanned."
            )
        return ip_str

    # ------------------------------------------------------------- port scan
    def _probe_port(self, ip: str, port: int) -> Optional[PortInfo]:
        """Real TCP connect to (ip, port). Returns PortInfo if open, else None."""
        try:
            with socket.create_connection((ip, port), timeout=self.scan_timeout) as sock:
                banner = self._grab_banner(sock, port)
        except (OSError, socket.timeout):
            return None

        service, version = self._identify(port, banner)
        return PortInfo(port=port, service=service, version=version, banner=banner)

    def _grab_banner(self, sock: socket.socket, port: int) -> Optional[str]:
        """Read a real banner from an open socket."""
        sock.settimeout(self.scan_timeout)
        try:
            if port in self.HTTP_PORTS:
                sock.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
            data = sock.recv(512)
            if not data:
                return None
            return data.decode("utf-8", errors="replace").strip() or None
        except (OSError, socket.timeout):
            return None

    @staticmethod
    def _identify(port: int, banner: Optional[str]) -> tuple:
        """Derive (service, version) from the real banner where possible."""
        service = ReconEngine.COMMON_PORTS.get(port, f"Unknown-{port}")
        version = None
        if not banner:
            return service, None

        first = banner.splitlines()[0] if banner else ""
        # HTTP: prefer the Server header, fall back to the status line
        if banner.startswith("HTTP/"):
            service = "HTTP"
            m = re.search(r"^Server:\s*(.+)$", banner, re.IGNORECASE | re.MULTILINE)
            if m:
                version = m.group(1).strip()
            else:
                m = re.search(r"^X-Powered-By:\s*(.+)$", banner, re.IGNORECASE | re.MULTILINE)
                version = m.group(1).strip() if m else first.strip()
        elif first.startswith("SSH-"):
            service, version = "SSH", first.strip()
        elif first.startswith("220") and "smtp" in banner.lower():
            service, version = "SMTP", first.strip()
        elif first.startswith("220"):
            service, version = "FTP", first.strip()
        else:
            version = first.strip()[:120] or None
        return service, version

    def scan_ports(
        self,
        target: str,
        ports: Optional[List[int]] = None,
        scan_type: str = "connect"
    ) -> Dict:
        """
        Scan target for open ports using real TCP connects (concurrent).

        Args:
            target: Target hostname or IP (must be loopback/private)
            ports: Ports to scan (default: COMMON_PORTS)
            scan_type: Recorded in the result; only TCP connect is implemented.

        Returns:
            Dictionary with open_ports and services (actual findings only)
        """
        ip = self.resolve_and_authorize(target)
        if ports is None:
            ports = sorted(self.COMMON_PORTS.keys())

        discovered: List[PortInfo] = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(len(ports), 1))) as pool:
            futures = {pool.submit(self._probe_port, ip, p): p for p in ports}
            for fut in as_completed(futures):
                info = fut.result()
                if info is not None:
                    discovered.append(info)

        discovered.sort(key=lambda p: p.port)

        open_ports = [{
            "port": p.port,
            "service": p.service,
            "state": "open",
            "version": p.version,
            "banner": p.banner,
        } for p in discovered]

        services = [{
            "name": p.service,
            "port": p.port,
            "protocol": "tcp",
            "version": p.version,
            "vulnerabilities": [],  # populated by the vulnerability scanner
        } for p in discovered]

        return {
            "target": target,
            "resolved_ip": ip,
            "scan_type": scan_type,
            "open_ports": open_ports,
            "services": services,
            "total_ports_scanned": len(ports),
            "open_ports_count": len(open_ports),
        }

    # ------------------------------------------------------------- host scan
    def scan_host(self, target: str) -> Dict:
        """Perform a real host scan (ports + best-effort OS info)."""
        port_scan = self.scan_ports(target)
        os_info = self._detect_os(port_scan["resolved_ip"], port_scan["open_ports"])
        return {
            **port_scan,
            "os": os_info,
            "hostname": target,
            "alive": port_scan["open_ports_count"] > 0,
        }

    @staticmethod
    def _detect_os(ip: str, open_ports: List[Dict]) -> Dict:
        """Best-effort OS info. Reports 'undetermined' rather than guessing."""
        try:
            is_local = ipaddress.ip_address(ip).is_loopback
        except ValueError:
            is_local = False

        if is_local:
            return {
                "type": platform.system(),
                "version": platform.release(),
                "confidence": 100,
                "method": "local platform inspection",
            }

        # Weak signal only: infer from observed service banners, else undetermined.
        banners = " ".join((p.get("version") or "") for p in open_ports).lower()
        if "win" in banners or "iis" in banners:
            return {"type": "Windows", "version": "Unknown", "confidence": 40,
                    "method": "banner heuristic"}
        if any(k in banners for k in ("ubuntu", "debian", "centos", "nginx", "apache")):
            return {"type": "Linux", "version": "Unknown", "confidence": 40,
                    "method": "banner heuristic"}
        return {"type": "undetermined", "version": "Unknown", "confidence": 0,
                "method": "no OS fingerprinting performed"}

    # --------------------------------------------------------- HTTP endpoints
    def get_exposed_endpoints(self, target: str, service: str, port: Optional[int] = None) -> List[str]:
        """Probe a real HTTP service for which candidate endpoints actually exist."""
        ip = self.resolve_and_authorize(target)
        if port is None:
            port = 443 if service.upper() in ("HTTPS", "HTTPS-ALT") else 80

        candidates = [
            "/", "/api", "/admin", "/login", "/dashboard",
            "/api/users", "/api/products", "/robots.txt", "/.env", "/health",
        ]

        found: List[str] = []

        def check(path: str) -> Optional[str]:
            try:
                with socket.create_connection((ip, port), timeout=self.scan_timeout) as s:
                    s.settimeout(self.scan_timeout)
                    req = (f"GET {path} HTTP/1.0\r\nHost: {ip}\r\n"
                           f"User-Agent: ART-AI-recon\r\n\r\n").encode()
                    s.sendall(req)
                    resp = s.recv(256).decode("utf-8", errors="replace")
                m = re.match(r"HTTP/[\d.]+\s+(\d{3})", resp)
                if not m:
                    return None
                code = int(m.group(1))
                # Treat anything that is not 404/410 as present (incl. 401/403 redirects)
                return path if code not in (404, 410) else None
            except (OSError, socket.timeout):
                return None

        with ThreadPoolExecutor(max_workers=min(20, len(candidates))) as pool:
            for res in pool.map(check, candidates):
                if res:
                    found.append(res)
        return found

    # -------------------------------------------------------- network sweep
    def perform_network_scan(self, network: str, max_hosts: int = 256) -> Dict:
        """
        Sweep a private network range for live hosts (real TCP connects).

        Only private/loopback ranges are permitted, and the range is capped at
        ``max_hosts`` addresses to keep the sweep bounded.
        """
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            raise UnauthorizedTargetError(f"Invalid network '{network}': {e}")

        if not (net.is_private or net.is_loopback):
            raise UnauthorizedTargetError(
                f"Network '{network}' is outside the authorized local-lab scope."
            )
        hosts = list(net.hosts())[:max_hosts] or [net.network_address]

        # Liveness = any of a few common ports accepting a connection.
        probe_ports = [80, 443, 22, 3389, 3001, 3002, 3003, 8003]

        def alive(ip_obj) -> Optional[str]:
            ip = str(ip_obj)
            for p in probe_ports:
                try:
                    with socket.create_connection((ip, p), timeout=0.3):
                        return ip
                except (OSError, socket.timeout):
                    continue
            return None

        live: List[str] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for res in pool.map(alive, hosts):
                if res:
                    live.append(res)

        discovered_hosts = [self.scan_host(ip) for ip in live]
        return {
            "network": network,
            "addresses_probed": len(hosts),
            "discovered_hosts": discovered_hosts,
            "total_hosts": len(discovered_hosts),
        }
