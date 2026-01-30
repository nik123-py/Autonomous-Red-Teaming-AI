"""
Environment state model for attacker simulation.
Tracks current access level and visited components.
Knowledge-Augmented RL: Includes strategic hints from Exploit-DB.
"""

from enum import Enum
from typing import List, Set, Optional
from dataclasses import dataclass, field


class AccessLevel(str, Enum):
    """Access levels in order of privilege escalation"""
    NONE = "none"
    PUBLIC = "public"
    INTERNAL = "internal"
    ADMIN = "admin"

    def __lt__(self, other):
        """Compare access levels for privilege escalation"""
        order = {
            AccessLevel.NONE: 0,
            AccessLevel.PUBLIC: 1,
            AccessLevel.INTERNAL: 2,
            AccessLevel.ADMIN: 3
        }
        return order[self] < order[other]

    def __le__(self, other):
        return self == other or self < other

    def can_escalate_to(self, target):
        """Check if escalation to target level is possible"""
        return self < target


@dataclass
class EnvironmentState:
    """Represents the current state of the vulnerable environment"""
    current_access_level: AccessLevel = AccessLevel.NONE
    visited_components: Set[str] = field(default_factory=set)
    blocked_ips: Set[str] = field(default_factory=set)
    discovered_services: List[str] = field(default_factory=list)
    discovered_vulnerabilities: List[str] = field(default_factory=list)
    iteration_count: int = 0
    # Knowledge-Augmented RL: Strategic hints from Exploit-DB
    strategic_hint: Optional[str] = None  # Suggested action from Exploit-DB
    hint_available: int = 0  # 0 or 1 for observation space
    hint_service: Optional[str] = None  # Service that generated the hint
    hint_confidence: float = 0.0  # Confidence level of hint
    hint_followed: bool = False  # Whether agent followed the hint
    hint_success: bool = False  # Whether following hint was successful

    def reset(self, target_service: Optional[str] = None, librarian=None):
        """
        Reset environment to initial state.
        
        Args:
            target_service: Optional service name to query for hints
            librarian: Optional ExploitLibrarian instance for knowledge augmentation
        """
        self.current_access_level = AccessLevel.NONE
        self.visited_components.clear()
        self.blocked_ips.clear()
        self.discovered_services.clear()
        self.discovered_vulnerabilities.clear()
        self.iteration_count = 0
        
        # Reset hint state
        self.strategic_hint = None
        self.hint_available = 0
        self.hint_service = None
        self.hint_confidence = 0.0
        self.hint_followed = False
        self.hint_success = False
        
        # Query Exploit-DB for strategic hints if librarian provided
        if librarian and target_service:
            self._query_strategic_hints(target_service, librarian)
    
    def _query_strategic_hints(self, service_name: str, librarian):
        """Query Exploit-DB for strategic hints"""
        try:
            # Get best hint from librarian
            hint = librarian.get_best_hint(service_name)
            if hint:
                self.strategic_hint = hint.action.value
                self.hint_available = 1
                self.hint_service = service_name
                self.hint_confidence = hint.confidence
                print(f"[+] Librarian suggests: {hint.action.value} for {service_name} (confidence: {hint.confidence:.2f}, CVE: {hint.cve_id or 'N/A'})")
        except Exception as e:
            print(f"[!] Failed to query strategic hints: {e}")
            self.hint_available = 0
    
    def check_hint_match(self, action: str) -> bool:
        """Check if action matches the strategic hint"""
        if not self.strategic_hint:
            return False
        return action == self.strategic_hint
    
    def mark_hint_followed(self, success: bool):
        """Mark that the hint was followed and whether it was successful"""
        self.hint_followed = True
        self.hint_success = success

    def escalate_access(self, new_level: AccessLevel):
        """Attempt to escalate access level"""
        if self.current_access_level < new_level:
            self.current_access_level = new_level
            return True
        return False

    def add_visited_component(self, component: str):
        """Mark a component as visited"""
        self.visited_components.add(component)

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.blocked_ips

    def block_ip(self, ip: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)

    def to_dict(self):
        """Convert state to dictionary for API responses"""
        return {
            "current_access_level": self.current_access_level.value,
            "visited_components": list(self.visited_components),
            "blocked_ips": list(self.blocked_ips),
            "discovered_services": self.discovered_services,
            "discovered_vulnerabilities": self.discovered_vulnerabilities,
            "iteration_count": self.iteration_count,
            "strategic_hint": self.strategic_hint,
            "hint_available": self.hint_available,
            "hint_service": self.hint_service,
            "hint_confidence": self.hint_confidence,
            "hint_followed": self.hint_followed,
            "hint_success": self.hint_success
        }

