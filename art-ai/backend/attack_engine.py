"""
Attack simulation engine.
Defines abstract attack actions and simulates their execution.
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import random
from env import AccessLevel, EnvironmentState


class AttackAction(str, Enum):
    """Predefined abstract attack actions"""
    PUBLIC_ACCESS_ATTEMPT = "public_access_attempt"
    TOKEN_REUSE_ATTEMPT = "token_reuse_attempt"
    PRIVILEGE_ESCALATION_ATTEMPT = "privilege_escalation_attempt"
    LATERAL_MOVEMENT_ATTEMPT = "lateral_movement_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    COMMAND_INJECTION_ATTEMPT = "command_injection_attempt"
    AUTHENTICATION_BYPASS_ATTEMPT = "authentication_bypass_attempt"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"


@dataclass
class AttackResult:
    """Result of an attack action execution"""
    success: bool
    new_access_level: AccessLevel
    message: str
    discovered_component: Optional[str] = None
    vulnerability_found: Optional[str] = None
    blocked: bool = False


class AttackEngine:
    """
    Simulates attack actions in a sandboxed environment.
    Uses probability-based success rates that depend on current access level.
    """

    # Success probabilities based on current access level
    SUCCESS_PROBABILITIES = {
        AccessLevel.NONE: {
            AttackAction.PUBLIC_ACCESS_ATTEMPT: 0.3,
            AttackAction.AUTHENTICATION_BYPASS_ATTEMPT: 0.1,
            AttackAction.SQL_INJECTION_ATTEMPT: 0.15,
        },
        AccessLevel.PUBLIC: {
            AttackAction.TOKEN_REUSE_ATTEMPT: 0.25,
            AttackAction.SESSION_HIJACK_ATTEMPT: 0.2,
            AttackAction.XSS_ATTEMPT: 0.3,
            AttackAction.PATH_TRAVERSAL_ATTEMPT: 0.2,
        },
        AccessLevel.INTERNAL: {
            AttackAction.PRIVILEGE_ESCALATION_ATTEMPT: 0.2,
            AttackAction.LATERAL_MOVEMENT_ATTEMPT: 0.3,
            AttackAction.COMMAND_INJECTION_ATTEMPT: 0.15,
        },
        AccessLevel.ADMIN: {
            # Admin level - most actions succeed but some are blocked
            AttackAction.LATERAL_MOVEMENT_ATTEMPT: 0.8,
        }
    }

    # Access level escalations for successful attacks
    ACCESS_ESCALATIONS = {
        AttackAction.PUBLIC_ACCESS_ATTEMPT: AccessLevel.PUBLIC,
        AttackAction.AUTHENTICATION_BYPASS_ATTEMPT: AccessLevel.PUBLIC,
        AttackAction.TOKEN_REUSE_ATTEMPT: AccessLevel.INTERNAL,
        AttackAction.SESSION_HIJACK_ATTEMPT: AccessLevel.INTERNAL,
        AttackAction.PRIVILEGE_ESCALATION_ATTEMPT: AccessLevel.ADMIN,
        AttackAction.LATERAL_MOVEMENT_ATTEMPT: AccessLevel.INTERNAL,
    }

    # Vulnerability types that can be discovered
    VULNERABILITIES = {
        AttackAction.SQL_INJECTION_ATTEMPT: "SQL Injection",
        AttackAction.XSS_ATTEMPT: "Cross-Site Scripting (XSS)",
        AttackAction.PATH_TRAVERSAL_ATTEMPT: "Path Traversal",
        AttackAction.COMMAND_INJECTION_ATTEMPT: "Command Injection",
    }

    def __init__(self):
        self.block_probability = 0.05  # 5% chance of being blocked

    def execute_attack(
        self,
        action: AttackAction,
        state: EnvironmentState
    ) -> AttackResult:
        """
        Execute an attack action and return the result.
        
        Args:
            action: The attack action to execute
            state: Current environment state
            
        Returns:
            AttackResult with success status and new access level
        """
        # Check if IP is blocked
        if state.is_blocked("attacker_ip"):
            return AttackResult(
                success=False,
                new_access_level=state.current_access_level,
                message="IP address is blocked",
                blocked=True
            )

        # Check if action is applicable to current access level
        if not self._is_action_applicable(action, state.current_access_level):
            return AttackResult(
                success=False,
                new_access_level=state.current_access_level,
                message=f"Action {action.value} not applicable at {state.current_access_level.value} level"
            )

        # Check for blocking (intrusion detection)
        if random.random() < self.block_probability:
            state.block_ip("attacker_ip")
            return AttackResult(
                success=False,
                new_access_level=state.current_access_level,
                message="Attack detected and blocked by IDS",
                blocked=True
            )

        # Calculate success probability
        success_prob = self._get_success_probability(action, state.current_access_level)
        
        # Execute attack
        success = random.random() < success_prob

        if success:
            # Determine new access level
            new_level = self._calculate_new_access_level(action, state.current_access_level)
            
            # Check if escalation occurred
            escalated = state.escalate_access(new_level)
            
            # Discover component
            component = f"service_{random.randint(1, 10)}"
            state.add_visited_component(component)
            
            # Discover vulnerability if applicable
            vulnerability = self.VULNERABILITIES.get(action)
            if vulnerability:
                state.discovered_vulnerabilities.append(vulnerability)
            
            return AttackResult(
                success=True,
                new_access_level=state.current_access_level,
                message=f"Successfully executed {action.value}",
                discovered_component=component,
                vulnerability_found=vulnerability
            )
        else:
            return AttackResult(
                success=False,
                new_access_level=state.current_access_level,
                message=f"Failed to execute {action.value}"
            )

    def _is_action_applicable(self, action: AttackAction, current_level: AccessLevel) -> bool:
        """Check if action can be executed at current access level"""
        level_actions = self.SUCCESS_PROBABILITIES.get(current_level, {})
        return action in level_actions or action in self.ACCESS_ESCALATIONS

    def _get_success_probability(
        self,
        action: AttackAction,
        current_level: AccessLevel
    ) -> float:
        """Get success probability for action at current level"""
        level_probs = self.SUCCESS_PROBABILITIES.get(current_level, {})
        base_prob = level_probs.get(action, 0.1)  # Default 10% if not specified
        
        # Adjust based on iteration count (learning curve)
        return min(base_prob * 1.1, 0.95)  # Cap at 95%

    def _calculate_new_access_level(
        self,
        action: AttackAction,
        current_level: AccessLevel
    ) -> AccessLevel:
        """Calculate new access level after successful attack"""
        escalation = self.ACCESS_ESCALATIONS.get(action)
        if escalation and current_level < escalation:
            return escalation
        return current_level

    def get_available_actions(self, current_level: AccessLevel) -> list[AttackAction]:
        """Get list of available actions for current access level"""
        available = []
        
        # Actions available at all levels
        base_actions = [
            AttackAction.PUBLIC_ACCESS_ATTEMPT,
            AttackAction.SQL_INJECTION_ATTEMPT,
        ]
        
        # Level-specific actions
        if current_level >= AccessLevel.PUBLIC:
            available.extend([
                AttackAction.TOKEN_REUSE_ATTEMPT,
                AttackAction.XSS_ATTEMPT,
                AttackAction.PATH_TRAVERSAL_ATTEMPT,
            ])
        
        if current_level >= AccessLevel.INTERNAL:
            available.extend([
                AttackAction.PRIVILEGE_ESCALATION_ATTEMPT,
                AttackAction.LATERAL_MOVEMENT_ATTEMPT,
                AttackAction.COMMAND_INJECTION_ATTEMPT,
            ])
        
        return list(set(available + base_actions))

