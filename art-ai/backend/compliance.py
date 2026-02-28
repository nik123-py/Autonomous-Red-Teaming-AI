"""
Compliance mapping system for security findings.
Maps vulnerabilities and attack results to compliance frameworks:
- PCI-DSS (Payment Card Industry Data Security Standard)
- HIPAA (Health Insurance Portability and Accountability Act)
- SOC2 (System and Organization Controls 2)
- ISO27001 (Information Security Management)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    PCI_DSS = "PCI-DSS"
    HIPAA = "HIPAA"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"


@dataclass
class ComplianceRequirement:
    """A specific requirement within a compliance framework"""
    framework: ComplianceFramework
    requirement_id: str  # e.g., "PCI-DSS 3.4", "HIPAA §164.312(a)(1)"
    title: str
    description: str
    category: str  # e.g., "Encryption", "Access Control"
    severity: str  # "Critical", "High", "Medium", "Low"


@dataclass
class ComplianceFinding:
    """A finding mapped to compliance requirements"""
    requirement: ComplianceRequirement
    vulnerability: str
    status: str  # "Compliant", "Non-Compliant", "Partially Compliant"
    evidence: str
    risk_score: float  # 0.0 to 1.0
    remediation: str


@dataclass
class ComplianceScore:
    """Compliance score for a framework"""
    framework: ComplianceFramework
    total_requirements: int
    compliant: int
    non_compliant: int
    partially_compliant: int
    score: float  # Percentage 0-100
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int


class ComplianceMapper:
    """
    Maps security findings to compliance framework requirements.
    Provides gap analysis and compliance scoring.
    """
    
    def __init__(self):
        self.requirements = self._load_requirements()
        self.vulnerability_mappings = self._load_vulnerability_mappings()
    
    def _load_requirements(self) -> Dict[ComplianceFramework, List[ComplianceRequirement]]:
        """Load compliance framework requirements"""
        requirements = {
            ComplianceFramework.PCI_DSS: [
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 3.4",
                    title="Render PAN unreadable",
                    description="Primary Account Numbers (PAN) must be rendered unreadable anywhere stored",
                    category="Data Protection",
                    severity="Critical"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 6.5",
                    title="Develop secure applications",
                    description="Develop applications based on secure coding guidelines",
                    category="Secure Development",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 6.5.1",
                    title="Injection flaws prevention",
                    description="Prevent injection flaws, particularly SQL injection",
                    category="Secure Development",
                    severity="Critical"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 6.5.7",
                    title="Cross-site scripting (XSS) prevention",
                    description="Prevent cross-site scripting vulnerabilities",
                    category="Secure Development",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 7.1",
                    title="Limit access to cardholder data",
                    description="Limit access to cardholder data to only those individuals whose job requires such access",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.PCI_DSS,
                    requirement_id="PCI-DSS 8.2",
                    title="Strong authentication",
                    description="Use strong authentication methods",
                    category="Access Control",
                    severity="High"
                ),
            ],
            ComplianceFramework.HIPAA: [
                ComplianceRequirement(
                    framework=ComplianceFramework.HIPAA,
                    requirement_id="HIPAA §164.312(a)(1)",
                    title="Access Control - Unique User Identification",
                    description="Assign a unique name and/or number for identifying and tracking user identity",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.HIPAA,
                    requirement_id="HIPAA §164.312(a)(2)(i)",
                    title="Access Control - Emergency Access Procedure",
                    description="Establish procedures for obtaining necessary electronic protected health information during an emergency",
                    category="Access Control",
                    severity="Medium"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.HIPAA,
                    requirement_id="HIPAA §164.312(e)(1)",
                    title="Transmission Security - Integrity Controls",
                    description="Implement security measures to ensure that electronically transmitted ePHI is not improperly modified",
                    category="Data Protection",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.HIPAA,
                    requirement_id="HIPAA §164.312(e)(2)(i)",
                    title="Transmission Security - Encryption",
                    description="Implement a mechanism to encrypt ePHI whenever deemed appropriate",
                    category="Data Protection",
                    severity="Critical"
                ),
            ],
            ComplianceFramework.SOC2: [
                ComplianceRequirement(
                    framework=ComplianceFramework.SOC2,
                    requirement_id="CC6.1",
                    title="Logical and Physical Access Controls",
                    description="The entity implements logical access security software, infrastructure, and architectures over protected information assets",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.SOC2,
                    requirement_id="CC6.2",
                    title="Prior to Issuing Credentials",
                    description="The entity discontinues or modifies logical access when access is no longer required",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.SOC2,
                    requirement_id="CC7.1",
                    title="System Boundaries",
                    description="The entity uses detection and monitoring procedures to identify vulnerabilities",
                    category="Monitoring",
                    severity="Medium"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.SOC2,
                    requirement_id="CC7.2",
                    title="Vulnerability Remediation",
                    description="The entity evaluates and responds to identified vulnerabilities",
                    category="Vulnerability Management",
                    severity="High"
                ),
            ],
            ComplianceFramework.ISO27001: [
                ComplianceRequirement(
                    framework=ComplianceFramework.ISO27001,
                    requirement_id="ISO27001 A.9.2.1",
                    title="User registration and de-registration",
                    description="A formal user registration and de-registration process shall be implemented",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.ISO27001,
                    requirement_id="ISO27001 A.9.4.2",
                    title="Secure log-on procedures",
                    description="Where required by the access control policy, access to systems and applications shall be controlled by a secure log-on procedure",
                    category="Access Control",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.ISO27001,
                    requirement_id="ISO27001 A.14.2.1",
                    title="Secure development policy",
                    description="Rules for the development of software and systems shall be established and applied",
                    category="Secure Development",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.ISO27001,
                    requirement_id="ISO27001 A.14.2.5",
                    title="Secure system engineering principles",
                    description="Principles for engineering secure systems shall be established, documented, maintained, and applied",
                    category="Secure Development",
                    severity="High"
                ),
                ComplianceRequirement(
                    framework=ComplianceFramework.ISO27001,
                    requirement_id="ISO27001 A.14.2.8",
                    title="System security testing",
                    description="Testing of security functionality shall be carried out during development",
                    category="Secure Development",
                    severity="Medium"
                ),
            ]
        }
        return requirements
    
    def _load_vulnerability_mappings(self) -> Dict[str, List[ComplianceRequirement]]:
        """Map vulnerabilities to compliance requirements"""
        mappings = {
            "SQL Injection": [
                self.requirements[ComplianceFramework.PCI_DSS][1],  # PCI-DSS 6.5.1
                self.requirements[ComplianceFramework.ISO27001][3],  # ISO27001 A.14.2.5
            ],
            "Cross-Site Scripting (XSS)": [
                self.requirements[ComplianceFramework.PCI_DSS][3],  # PCI-DSS 6.5.7
                self.requirements[ComplianceFramework.ISO27001][3],  # ISO27001 A.14.2.5
            ],
            "Path Traversal": [
                self.requirements[ComplianceFramework.ISO27001][3],  # ISO27001 A.14.2.5
            ],
            "Command Injection": [
                self.requirements[ComplianceFramework.PCI_DSS][1],  # PCI-DSS 6.5
                self.requirements[ComplianceFramework.ISO27001][3],  # ISO27001 A.14.2.5
            ],
            "Authentication Bypass": [
                self.requirements[ComplianceFramework.PCI_DSS][4],  # PCI-DSS 7.1
                self.requirements[ComplianceFramework.PCI_DSS][5],  # PCI-DSS 8.2
                self.requirements[ComplianceFramework.HIPAA][0],  # HIPAA §164.312(a)(1)
                self.requirements[ComplianceFramework.SOC2][0],  # SOC2 CC6.1
                self.requirements[ComplianceFramework.ISO27001][0],  # ISO27001 A.9.2.1
            ],
            "Session Hijack": [
                self.requirements[ComplianceFramework.PCI_DSS][4],  # PCI-DSS 7.1
                self.requirements[ComplianceFramework.HIPAA][0],  # HIPAA §164.312(a)(1)
                self.requirements[ComplianceFramework.SOC2][0],  # SOC2 CC6.1
            ],
            "Privilege Escalation": [
                self.requirements[ComplianceFramework.PCI_DSS][4],  # PCI-DSS 7.1
                self.requirements[ComplianceFramework.HIPAA][0],  # HIPAA §164.312(a)(1)
                self.requirements[ComplianceFramework.SOC2][0],  # SOC2 CC6.1
                self.requirements[ComplianceFramework.ISO27001][0],  # ISO27001 A.9.2.1
            ],
        }
        return mappings
    
    def map_findings(
        self,
        vulnerabilities: List[str],
        attack_path: List[Dict],
        frameworks: Optional[List[ComplianceFramework]] = None
    ) -> Dict[ComplianceFramework, List[ComplianceFinding]]:
        """
        Map security findings to compliance requirements.
        
        Args:
            vulnerabilities: List of discovered vulnerabilities
            attack_path: Attack path with actions and results
            frameworks: Optional list of frameworks to analyze (default: all)
        
        Returns:
            Dictionary mapping frameworks to compliance findings
        """
        if frameworks is None:
            frameworks = list(ComplianceFramework)
        
        findings = {framework: [] for framework in frameworks}
        
        # Map vulnerabilities
        for vuln in vulnerabilities:
            if vuln in self.vulnerability_mappings:
                for requirement in self.vulnerability_mappings[vuln]:
                    if requirement.framework in frameworks:
                        finding = ComplianceFinding(
                            requirement=requirement,
                            vulnerability=vuln,
                            status="Non-Compliant",
                            evidence=f"Vulnerability '{vuln}' discovered during security assessment",
                            risk_score=self._calculate_risk_score(requirement.severity),
                            remediation=self._get_remediation(vuln, requirement)
                        )
                        findings[requirement.framework].append(finding)
        
        # Map attack path actions to access control requirements
        for step in attack_path:
            if step.get("success") and step.get("access_level") in ["internal", "admin"]:
                # Unauthorized access detected
                access_requirements = [
                    req for req_list in self.requirements.values()
                    for req in req_list
                    if req.category == "Access Control"
                ]
                
                for requirement in access_requirements:
                    if requirement.framework in frameworks:
                        finding = ComplianceFinding(
                            requirement=requirement,
                            vulnerability="Unauthorized Access",
                            status="Non-Compliant",
                            evidence=f"Successfully escalated to {step.get('access_level')} access level via {step.get('action')}",
                            risk_score=0.9 if step.get("access_level") == "admin" else 0.7,
                            remediation="Implement strong access controls, multi-factor authentication, and least privilege principles"
                        )
                        # Avoid duplicates
                        if not any(f.requirement.requirement_id == requirement.requirement_id 
                                  for f in findings[requirement.framework]):
                            findings[requirement.framework].append(finding)
        
        return findings
    
    def calculate_compliance_scores(
        self,
        findings: Dict[ComplianceFramework, List[ComplianceFinding]]
    ) -> Dict[ComplianceFramework, ComplianceScore]:
        """Calculate compliance scores for each framework"""
        scores = {}
        
        for framework, framework_findings in findings.items():
            total_reqs = len(self.requirements[framework])
            compliant = total_reqs - len(framework_findings)
            non_compliant = len([f for f in framework_findings if f.status == "Non-Compliant"])
            partially_compliant = len([f for f in framework_findings if f.status == "Partially Compliant"])
            
            score = (compliant / total_reqs * 100) if total_reqs > 0 else 100.0
            
            critical = len([f for f in framework_findings if f.requirement.severity == "Critical"])
            high = len([f for f in framework_findings if f.requirement.severity == "High"])
            medium = len([f for f in framework_findings if f.requirement.severity == "Medium"])
            low = len([f for f in framework_findings if f.requirement.severity == "Low"])
            
            scores[framework] = ComplianceScore(
                framework=framework,
                total_requirements=total_reqs,
                compliant=compliant,
                non_compliant=non_compliant,
                partially_compliant=partially_compliant,
                score=score,
                critical_findings=critical,
                high_findings=high,
                medium_findings=medium,
                low_findings=low
            )
        
        return scores
    
    def _calculate_risk_score(self, severity: str) -> float:
        """Calculate risk score based on severity"""
        severity_map = {
            "Critical": 0.9,
            "High": 0.7,
            "Medium": 0.5,
            "Low": 0.3
        }
        return severity_map.get(severity, 0.5)
    
    def _get_remediation(self, vulnerability: str, requirement: ComplianceRequirement) -> str:
        """Get remediation recommendation"""
        remediations = {
            "SQL Injection": "Implement parameterized queries and input validation. Use prepared statements and stored procedures.",
            "Cross-Site Scripting (XSS)": "Implement output encoding, Content Security Policy (CSP), and input validation.",
            "Path Traversal": "Validate and sanitize file paths. Use whitelist-based access controls.",
            "Command Injection": "Avoid executing system commands with user input. Use safe APIs and input validation.",
            "Authentication Bypass": "Implement strong authentication mechanisms, multi-factor authentication, and session management.",
            "Session Hijack": "Use secure session tokens, implement session timeout, and use HTTPS for all communications.",
            "Privilege Escalation": "Implement least privilege access control, regular access reviews, and privilege separation.",
        }
        
        base_remediation = remediations.get(vulnerability, "Review and remediate the identified vulnerability following secure coding practices.")
        
        return f"{base_remediation} This addresses {requirement.framework.value} requirement {requirement.requirement_id}: {requirement.title}."
    
    def get_gap_analysis(
        self,
        vulnerabilities: List[str],
        attack_path: List[Dict],
        frameworks: Optional[List[ComplianceFramework]] = None
    ) -> Dict:
        """
        Perform gap analysis showing compliance gaps and remediation priorities.
        
        Args:
            vulnerabilities: List of discovered vulnerabilities
            attack_path: Attack path with actions and results
            frameworks: Optional list of frameworks to analyze
            
        Returns:
            Gap analysis with priority-ordered remediation recommendations
        """
        findings = self.map_findings(vulnerabilities, attack_path, frameworks)
        scores = self.calculate_compliance_scores(findings)
        
        # Build gap analysis
        gaps = []
        
        for framework, framework_findings in findings.items():
            for finding in framework_findings:
                gaps.append({
                    "framework": framework.value,
                    "requirement_id": finding.requirement.requirement_id,
                    "requirement_name": finding.requirement.title,
                    "category": finding.requirement.category,
                    "severity": finding.requirement.severity,
                    "status": finding.status,
                    "vulnerability": finding.vulnerability,
                    "risk_score": finding.risk_score,
                    "evidence": finding.evidence,
                    "remediation": finding.remediation
                })
        
        # Sort gaps by risk score (highest first)
        gaps.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Group by priority
        critical_gaps = [g for g in gaps if g["severity"] == "Critical"]
        high_gaps = [g for g in gaps if g["severity"] == "High"]
        medium_gaps = [g for g in gaps if g["severity"] == "Medium"]
        low_gaps = [g for g in gaps if g["severity"] == "Low"]
        
        # Generate summary
        summary = {
            "total_gaps": len(gaps),
            "critical_gaps": len(critical_gaps),
            "high_gaps": len(high_gaps),
            "medium_gaps": len(medium_gaps),
            "low_gaps": len(low_gaps),
            "frameworks_analyzed": len(findings),
            "overall_compliance_score": round(
                sum(s.score for s in scores.values()) / len(scores) if scores else 0, 1
            )
        }
        
        # Generate remediation roadmap
        roadmap = []
        
        # Phase 1: Critical items (Immediate - 1 week)
        if critical_gaps:
            roadmap.append({
                "phase": 1,
                "name": "Immediate Actions",
                "timeline": "1 week",
                "priority": "Critical",
                "items": critical_gaps[:5],  # Top 5 critical items
                "effort": "High"
            })
        
        # Phase 2: High items (Short-term - 2-4 weeks)
        if high_gaps:
            roadmap.append({
                "phase": 2,
                "name": "Short-term Remediation",
                "timeline": "2-4 weeks",
                "priority": "High",
                "items": high_gaps[:10],  # Top 10 high items
                "effort": "Medium-High"
            })
        
        # Phase 3: Medium items (Medium-term - 1-2 months)
        if medium_gaps:
            roadmap.append({
                "phase": 3,
                "name": "Medium-term Improvements",
                "timeline": "1-2 months",
                "priority": "Medium",
                "items": medium_gaps[:10],
                "effort": "Medium"
            })
        
        # Phase 4: Low items (Long-term - 3+ months)
        if low_gaps:
            roadmap.append({
                "phase": 4,
                "name": "Long-term Enhancements",
                "timeline": "3+ months",
                "priority": "Low",
                "items": low_gaps,
                "effort": "Low"
            })
        
        return {
            "summary": summary,
            "gaps": gaps,
            "roadmap": roadmap,
            "scores": {
                framework.value: {
                    "score": score.score,
                    "compliant": score.compliant,
                    "non_compliant": score.non_compliant,
                    "total": score.total_requirements
                }
                for framework, score in scores.items()
            }
        }
