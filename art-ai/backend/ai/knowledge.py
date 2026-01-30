"""
Exploit Librarian - Knowledge-Augmented RL Component
Queries Exploit-DB (via searchsploit or mock database) to provide strategic hints.
"""

import subprocess
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import json
import os


class Action(str, Enum):
    """Attack actions that can be suggested as hints"""
    SQL_INJECTION = "sql_injection_attempt"
    XSS = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal_attempt"
    COMMAND_INJECTION = "command_injection_attempt"
    AUTHENTICATION_BYPASS = "authentication_bypass_attempt"
    PRIVILEGE_ESCALATION = "privilege_escalation_attempt"
    LATERAL_MOVEMENT = "lateral_movement_attempt"
    SSRF = "ssrf_attempt"
    XXE = "xxe_attempt"
    DESERIALIZATION = "deserialization_attempt"


@dataclass
class StrategicHint:
    """Represents a strategic hint from Exploit-DB"""
    action: Action
    service_name: str
    exploit_id: Optional[str] = None
    description: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    cve_id: Optional[str] = None
    exploit_path: Optional[str] = None


class ExploitLibrarian:
    """
    Knowledge-Augmented component that queries Exploit-DB for strategic hints.
    Provides attack vector suggestions based on discovered services.
    """

    def __init__(self, demo_mode: bool = True):
        """
        Initialize Exploit Librarian.
        
        Args:
            demo_mode: If True, uses hardcoded hints instead of real searchsploit
        """
        self.demo_mode = demo_mode
        self.searchsploit_available = self._check_searchsploit()
        self.hint_cache = {}  # Cache hints to avoid repeated queries
        
        # Mock Exploit-DB database (demo mode)
        self.mock_exploit_db = self._load_mock_exploit_db()

    def _check_searchsploit(self) -> bool:
        """Check if searchsploit is available on the system"""
        if self.demo_mode:
            return False
        
        try:
            result = subprocess.run(
                ["searchsploit", "--version"],
                capture_output=True,
                timeout=2,
                text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _load_mock_exploit_db(self) -> Dict[str, List[Dict]]:
        """
        Load mock Exploit-DB entries for demo mode.
        Based on real Exploit-DB patterns.
        """
        return {
            # Apache vulnerabilities
            "apache": [
                {
                    "exploit_id": "50437",
                    "cve": "CVE-2021-41773",
                    "description": "Apache 2.4.49 Path Traversal",
                    "action": Action.PATH_TRAVERSAL,
                    "confidence": 0.95,
                    "version_pattern": r"2\.4\.(49|50)"
                },
                {
                    "exploit_id": "50438",
                    "cve": "CVE-2021-42013",
                    "description": "Apache 2.4.50 Path Traversal RCE",
                    "action": Action.PATH_TRAVERSAL,
                    "confidence": 0.95,
                    "version_pattern": r"2\.4\.50"
                }
            ],
            # MySQL vulnerabilities
            "mysql": [
                {
                    "exploit_id": "23081",
                    "cve": "CVE-2012-2122",
                    "description": "MySQL Authentication Bypass",
                    "action": Action.AUTHENTICATION_BYPASS,
                    "confidence": 0.85,
                    "version_pattern": r"5\.(1|5|6|7)"
                },
                {
                    "exploit_id": "17491",
                    "cve": "CVE-2010-1850",
                    "description": "MySQL SQL Injection",
                    "action": Action.SQL_INJECTION,
                    "confidence": 0.80,
                    "version_pattern": r"5\.[0-5]"
                }
            ],
            # PostgreSQL vulnerabilities
            "postgresql": [
                {
                    "exploit_id": "45517",
                    "cve": "CVE-2019-9193",
                    "description": "PostgreSQL COPY Command RCE",
                    "action": Action.COMMAND_INJECTION,
                    "confidence": 0.90,
                    "version_pattern": r"9\.3|10\.[0-1]|11\.[0-1]"
                },
                {
                    "exploit_id": "28545",
                    "cve": "CVE-2007-6600",
                    "description": "PostgreSQL SQL Injection",
                    "action": Action.SQL_INJECTION,
                    "confidence": 0.75,
                    "version_pattern": r"8\.[0-2]"
                }
            ],
            # Nginx vulnerabilities
            "nginx": [
                {
                    "exploit_id": "37977",
                    "cve": "CVE-2013-2028",
                    "description": "Nginx Stack Buffer Overflow",
                    "action": Action.PRIVILEGE_ESCALATION,
                    "confidence": 0.70,
                    "version_pattern": r"1\.[0-3]\.[0-9]"
                }
            ],
            # PHP vulnerabilities
            "php": [
                {
                    "exploit_id": "49933",
                    "cve": "CVE-2021-21708",
                    "description": "PHP Deserialization RCE",
                    "action": Action.DESERIALIZATION,
                    "confidence": 0.85,
                    "version_pattern": r"7\.[0-3]|8\.[0-1]"
                },
                {
                    "exploit_id": "31192",
                    "cve": "CVE-2012-1823",
                    "description": "PHP CGI Argument Injection",
                    "action": Action.COMMAND_INJECTION,
                    "confidence": 0.80,
                    "version_pattern": r"5\.[3-4]"
                }
            ],
            # Redis vulnerabilities
            "redis": [
                {
                    "exploit_id": "47195",
                    "cve": "CVE-2022-0543",
                    "description": "Redis Lua Sandbox Escape RCE",
                    "action": Action.COMMAND_INJECTION,
                    "confidence": 0.90,
                    "version_pattern": r"5\.[0-9]|6\.[0-2]|7\.[0-1]"
                }
            ],
            # Elasticsearch vulnerabilities
            "elasticsearch": [
                {
                    "exploit_id": "36337",
                    "cve": "CVE-2014-3120",
                    "description": "Elasticsearch Remote Code Execution",
                    "action": Action.COMMAND_INJECTION,
                    "confidence": 0.95,
                    "version_pattern": r"1\.[0-1]\.[0-9]"
                }
            ],
            # SSH vulnerabilities
            "ssh": [
                {
                    "exploit_id": "45210",
                    "cve": "CVE-2018-15473",
                    "description": "OpenSSH Username Enumeration",
                    "action": Action.AUTHENTICATION_BYPASS,
                    "confidence": 0.60,
                    "version_pattern": r"7\.[0-7]"
                }
            ],
            # FTP vulnerabilities
            "ftp": [
                {
                    "exploit_id": "17491",
                    "cve": "CVE-2015-3306",
                    "description": "ProFTPD Mod_Copy Command Execution",
                    "action": Action.COMMAND_INJECTION,
                    "confidence": 0.75,
                    "version_pattern": r"1\.3\.[0-5]"
                }
            ],
            # Web application generic hints
            "http": [
                {
                    "exploit_id": "generic_001",
                    "cve": None,
                    "description": "Web applications commonly vulnerable to XSS",
                    "action": Action.XSS,
                    "confidence": 0.50,
                    "version_pattern": r".*"
                },
                {
                    "exploit_id": "generic_002",
                    "cve": None,
                    "description": "Web applications commonly vulnerable to SQL Injection",
                    "action": Action.SQL_INJECTION,
                    "confidence": 0.50,
                    "version_pattern": r".*"
                }
            ]
        }

    def get_strategic_hints(self, service_name: str, service_version: Optional[str] = None) -> List[StrategicHint]:
        """
        Query Exploit-DB for strategic hints based on service name.
        
        Args:
            service_name: Name of the discovered service (e.g., "Apache", "MySQL")
            service_version: Optional version string (e.g., "2.4.49")
            
        Returns:
            List of StrategicHint objects with suggested attack actions
        """
        # Check cache first
        cache_key = f"{service_name}:{service_version or 'unknown'}"
        if cache_key in self.hint_cache:
            return self.hint_cache[cache_key]

        hints = []

        if self.searchsploit_available and not self.demo_mode:
            # Use real searchsploit
            hints = self._query_searchsploit(service_name, service_version)
        else:
            # Use mock database (demo mode)
            hints = self._query_mock_db(service_name, service_version)

        # Cache results
        self.hint_cache[cache_key] = hints
        return hints

    def _query_searchsploit(self, service_name: str, version: Optional[str] = None) -> List[StrategicHint]:
        """
        Query real searchsploit for exploits.
        
        Args:
            service_name: Service name to search
            version: Optional version string
            
        Returns:
            List of StrategicHint objects
        """
        hints = []
        
        try:
            # Build search query
            query = service_name
            if version:
                query = f"{service_name} {version}"

            # Run searchsploit
            result = subprocess.run(
                ["searchsploit", "-j", query],
                capture_output=True,
                timeout=5,
                text=True
            )

            if result.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(result.stdout)
                    exploits = data.get("RESULTS_EXPLOIT", [])
                    
                    for exploit in exploits[:5]:  # Limit to top 5
                        hint = self._parse_exploit_result(exploit, service_name)
                        if hint:
                            hints.append(hint)
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to mock if searchsploit fails
            hints = self._query_mock_db(service_name, version)

        return hints

    def _parse_exploit_result(self, exploit_data: Dict, service_name: str) -> Optional[StrategicHint]:
        """Parse searchsploit result into StrategicHint"""
        try:
            title = exploit_data.get("Title", "").lower()
            exploit_id = exploit_data.get("EDB-ID", "")
            path = exploit_data.get("Path", "")

            # Map exploit title to action
            action = self._infer_action_from_title(title, service_name)
            
            if not action:
                return None

            # Extract CVE if present
            cve_match = re.search(r"CVE-\d{4}-\d+", title)
            cve_id = cve_match.group(0) if cve_match else None

            return StrategicHint(
                action=action,
                service_name=service_name,
                exploit_id=exploit_id,
                description=exploit_data.get("Title", ""),
                confidence=0.80,  # Default confidence for real exploits
                cve_id=cve_id,
                exploit_path=path
            )
        except Exception:
            return None

    def _query_mock_db(self, service_name: str, version: Optional[str] = None) -> List[StrategicHint]:
        """
        Query mock Exploit-DB for demo mode.
        
        Args:
            service_name: Service name to search
            version: Optional version string
            
        Returns:
            List of StrategicHint objects
        """
        hints = []
        service_lower = service_name.lower()

        # Search for matching service in mock DB
        for db_service, exploits in self.mock_exploit_db.items():
            if db_service in service_lower or service_lower in db_service:
                for exploit in exploits:
                    # Check version pattern if version provided
                    if version:
                        pattern = exploit.get("version_pattern", ".*")
                        if not re.search(pattern, version):
                            continue

                    hint = StrategicHint(
                        action=exploit["action"],
                        service_name=service_name,
                        exploit_id=exploit["exploit_id"],
                        description=exploit["description"],
                        confidence=exploit["confidence"],
                        cve_id=exploit.get("cve"),
                        exploit_path=f"exploits/{exploit['exploit_id']}"
                    )
                    hints.append(hint)

        # If no specific match, provide generic web app hints
        if not hints and any(web in service_lower for web in ["http", "https", "web", "www"]):
            for exploit in self.mock_exploit_db.get("http", []):
                hint = StrategicHint(
                    action=exploit["action"],
                    service_name=service_name,
                    exploit_id=exploit["exploit_id"],
                    description=exploit["description"],
                    confidence=exploit["confidence"],
                    cve_id=exploit.get("cve")
                )
                hints.append(hint)

        return hints

    def _infer_action_from_title(self, title: str, service_name: str) -> Optional[Action]:
        """
        Infer attack action from exploit title.
        
        Args:
            title: Exploit title/description
            service_name: Service name
            
        Returns:
            Action enum or None
        """
        title_lower = title.lower()
        service_lower = service_name.lower()

        # SQL Injection
        if any(term in title_lower for term in ["sql injection", "sqli", "sql injection"]):
            return Action.SQL_INJECTION

        # Path Traversal
        if any(term in title_lower for term in ["path traversal", "directory traversal", "lfi", "local file inclusion"]):
            return Action.PATH_TRAVERSAL

        # Command Injection
        if any(term in title_lower for term in ["command injection", "rce", "remote code execution", "code execution"]):
            return Action.COMMAND_INJECTION

        # Authentication Bypass
        if any(term in title_lower for term in ["authentication bypass", "auth bypass", "login bypass"]):
            return Action.AUTHENTICATION_BYPASS

        # XSS
        if any(term in title_lower for term in ["xss", "cross-site scripting"]):
            return Action.XSS

        # Privilege Escalation
        if any(term in title_lower for term in ["privilege escalation", "privilege", "escalation"]):
            return Action.PRIVILEGE_ESCALATION

        # SSRF
        if any(term in title_lower for term in ["ssrf", "server-side request forgery"]):
            return Action.SSRF

        # XXE
        if any(term in title_lower for term in ["xxe", "xml external entity"]):
            return Action.XXE

        # Deserialization
        if any(term in title_lower for term in ["deserialization", "unserialize"]):
            return Action.DESERIALIZATION

        # Default based on service type
        if "mysql" in service_lower or "postgresql" in service_lower or "sql" in service_lower:
            return Action.SQL_INJECTION

        if "apache" in service_lower or "nginx" in service_lower or "web" in service_lower:
            return Action.PATH_TRAVERSAL

        return None

    def get_best_hint(self, service_name: str, version: Optional[str] = None) -> Optional[StrategicHint]:
        """
        Get the best (highest confidence) hint for a service.
        
        Args:
            service_name: Service name
            version: Optional version string
            
        Returns:
            Best StrategicHint or None
        """
        hints = self.get_strategic_hints(service_name, version)
        if not hints:
            return None

        # Return hint with highest confidence
        return max(hints, key=lambda h: h.confidence)

    def clear_cache(self):
        """Clear the hint cache"""
        self.hint_cache.clear()

