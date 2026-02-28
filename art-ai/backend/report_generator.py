"""
Professional Security Report Generator for ART-AI.
Generates PDF/HTML security assessment reports with:
- Executive summary
- Technical findings
- Risk scoring
- Remediation recommendations
- Compliance mapping (PCI-DSS, SOC2, ISO27001, HIPAA)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from compliance import ComplianceMapper, ComplianceFramework, ComplianceFinding, ComplianceScore
import json
import base64


@dataclass
class ReportSection:
    """A section in the security report"""
    title: str
    content: str
    severity: Optional[str] = None
    
    
class SecurityReportGenerator:
    """
    Generates professional security assessment reports.
    Supports HTML output with embedded styling.
    """
    
    def __init__(self):
        self.compliance_mapper = ComplianceMapper()
    
    def generate_report(
        self,
        simulation_result: Dict,
        attack_path: List[Dict],
        vulnerabilities: List[str],
        target: str = "Target System",
        include_compliance: bool = True,
        frameworks: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a complete security assessment report.
        
        Args:
            simulation_result: Results from the simulation
            attack_path: List of attack steps
            vulnerabilities: List of discovered vulnerabilities
            target: Target system name
            include_compliance: Whether to include compliance mapping
            frameworks: List of compliance frameworks to include
            
        Returns:
            Dictionary with report data and HTML content
        """
        # Parse frameworks
        compliance_frameworks = None
        if frameworks:
            compliance_frameworks = [
                ComplianceFramework(f) for f in frameworks 
                if f in [cf.value for cf in ComplianceFramework]
            ]
        
        # Generate compliance data
        compliance_findings = {}
        compliance_scores = {}
        if include_compliance:
            compliance_findings = self.compliance_mapper.map_findings(
                vulnerabilities, attack_path, compliance_frameworks
            )
            compliance_scores = self.compliance_mapper.calculate_compliance_scores(
                compliance_findings
            )
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(
            simulation_result, attack_path, vulnerabilities
        )
        
        # Generate report sections
        executive_summary = self._generate_executive_summary(
            simulation_result, vulnerabilities, risk_metrics, target
        )
        
        technical_findings = self._generate_technical_findings(
            attack_path, vulnerabilities
        )
        
        remediation_section = self._generate_remediation_section(
            vulnerabilities, compliance_findings
        )
        
        # Generate HTML report
        html_report = self._generate_html_report(
            target=target,
            executive_summary=executive_summary,
            risk_metrics=risk_metrics,
            technical_findings=technical_findings,
            remediation_section=remediation_section,
            compliance_scores=compliance_scores,
            compliance_findings=compliance_findings,
            simulation_result=simulation_result,
            attack_path=attack_path
        )
        
        return {
            "report_id": f"ART-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "target": target,
            "risk_metrics": risk_metrics,
            "executive_summary": executive_summary,
            "technical_findings": technical_findings,
            "remediation": remediation_section,
            "compliance_scores": {
                framework.value: {
                    "score": score.score,
                    "total_requirements": score.total_requirements,
                    "compliant": score.compliant,
                    "non_compliant": score.non_compliant,
                    "critical_findings": score.critical_findings,
                    "high_findings": score.high_findings
                }
                for framework, score in compliance_scores.items()
            } if compliance_scores else {},
            "html_report": html_report
        }
    
    def _calculate_risk_metrics(
        self,
        simulation_result: Dict,
        attack_path: List[Dict],
        vulnerabilities: List[str]
    ) -> Dict:
        """Calculate overall risk metrics"""
        # Calculate risk score (0-100)
        base_score = 0
        
        # Access level achieved
        access_scores = {"none": 0, "public": 25, "internal": 60, "admin": 100}
        final_access = simulation_result.get("final_access_level", "none")
        base_score = access_scores.get(final_access, 0)
        
        # Vulnerability severity
        critical_vulns = ["SQL Injection", "Command Injection", "Authentication Bypass"]
        high_vulns = ["Cross-Site Scripting (XSS)", "Session Hijack", "Privilege Escalation"]
        
        critical_count = len([v for v in vulnerabilities if v in critical_vulns])
        high_count = len([v for v in vulnerabilities if v in high_vulns])
        
        vuln_score = min(critical_count * 15 + high_count * 10, 50)
        
        # Success rate impact
        total = simulation_result.get("successful_attacks", 0) + simulation_result.get("failed_attacks", 0)
        success_rate = simulation_result.get("successful_attacks", 0) / max(total, 1)
        
        overall_risk = min(base_score + vuln_score, 100)
        
        # Determine risk level
        if overall_risk >= 80:
            risk_level = "Critical"
        elif overall_risk >= 60:
            risk_level = "High"
        elif overall_risk >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return {
            "overall_risk_score": overall_risk,
            "risk_level": risk_level,
            "access_level_achieved": final_access,
            "vulnerability_count": len(vulnerabilities),
            "critical_vulnerabilities": critical_count,
            "high_vulnerabilities": high_count,
            "success_rate": round(success_rate * 100, 1),
            "total_attack_steps": len(attack_path)
        }
    
    def _generate_executive_summary(
        self,
        simulation_result: Dict,
        vulnerabilities: List[str],
        risk_metrics: Dict,
        target: str
    ) -> str:
        """Generate executive summary"""
        risk_level = risk_metrics["risk_level"]
        risk_score = risk_metrics["overall_risk_score"]
        access_level = risk_metrics["access_level_achieved"]
        vuln_count = len(vulnerabilities)
        
        summary = f"""
Security Assessment Executive Summary for {target}

Overall Risk Level: {risk_level} ({risk_score}/100)

The autonomous security assessment of {target} has been completed. 
The AI-driven penetration testing agent successfully {'achieved ' + access_level.upper() + ' level access' if access_level != 'none' else 'tested the system'} 
and discovered {vuln_count} {'vulnerability' if vuln_count == 1 else 'vulnerabilities'}.

Key Findings:
- Final Access Level: {access_level.upper()}
- Vulnerabilities Discovered: {vuln_count}
- Critical Issues: {risk_metrics['critical_vulnerabilities']}
- High Severity Issues: {risk_metrics['high_vulnerabilities']}
- Attack Success Rate: {risk_metrics['success_rate']}%

{'IMMEDIATE ACTION REQUIRED: Critical vulnerabilities were discovered that could lead to complete system compromise.' if risk_level == 'Critical' else ''}
{'ACTION RECOMMENDED: High-risk vulnerabilities require prompt remediation.' if risk_level == 'High' else ''}
        """.strip()
        
        return summary
    
    def _generate_technical_findings(
        self,
        attack_path: List[Dict],
        vulnerabilities: List[str]
    ) -> List[Dict]:
        """Generate detailed technical findings"""
        findings = []
        
        # Vulnerability findings
        vuln_details = {
            "SQL Injection": {
                "severity": "Critical",
                "description": "SQL injection vulnerability allows attackers to execute arbitrary SQL commands",
                "impact": "Data breach, unauthorized access, data manipulation",
                "cvss": 9.8
            },
            "Cross-Site Scripting (XSS)": {
                "severity": "High",
                "description": "XSS vulnerability allows injection of malicious scripts",
                "impact": "Session hijacking, credential theft, defacement",
                "cvss": 7.5
            },
            "Path Traversal": {
                "severity": "High",
                "description": "Path traversal allows access to files outside intended directory",
                "impact": "Information disclosure, configuration file access",
                "cvss": 7.2
            },
            "Command Injection": {
                "severity": "Critical",
                "description": "Command injection allows execution of arbitrary system commands",
                "impact": "Remote code execution, full system compromise",
                "cvss": 9.8
            },
            "Authentication Bypass": {
                "severity": "Critical",
                "description": "Authentication mechanism can be bypassed",
                "impact": "Unauthorized access, privilege escalation",
                "cvss": 9.1
            },
            "Session Hijack": {
                "severity": "High",
                "description": "Session tokens can be intercepted or predicted",
                "impact": "Account takeover, unauthorized actions",
                "cvss": 8.0
            }
        }
        
        for vuln in vulnerabilities:
            details = vuln_details.get(vuln, {
                "severity": "Medium",
                "description": f"Vulnerability: {vuln}",
                "impact": "Potential security impact",
                "cvss": 5.0
            })
            
            findings.append({
                "title": vuln,
                "severity": details["severity"],
                "description": details["description"],
                "impact": details["impact"],
                "cvss_score": details["cvss"],
                "evidence": f"Discovered during automated security assessment"
            })
        
        # Add access escalation findings
        escalation_steps = [s for s in attack_path if s.get("success") and s.get("access_level") in ["internal", "admin"]]
        for step in escalation_steps:
            findings.append({
                "title": f"Access Escalation: {step.get('action', 'Unknown').replace('_', ' ').title()}",
                "severity": "Critical" if step.get("access_level") == "admin" else "High",
                "description": f"Successfully escalated to {step.get('access_level')} access level",
                "impact": "Unauthorized access to protected resources",
                "cvss_score": 9.0 if step.get("access_level") == "admin" else 7.5,
                "evidence": step.get("message", "N/A")
            })
        
        return findings
    
    def _generate_remediation_section(
        self,
        vulnerabilities: List[str],
        compliance_findings: Dict
    ) -> List[Dict]:
        """Generate remediation recommendations"""
        remediations = {
            "SQL Injection": {
                "priority": 1,
                "recommendation": "Implement parameterized queries",
                "details": "Use prepared statements, stored procedures, and input validation. Never concatenate user input into SQL queries.",
                "effort": "Medium",
                "timeline": "Immediate"
            },
            "Cross-Site Scripting (XSS)": {
                "priority": 2,
                "recommendation": "Implement output encoding and CSP",
                "details": "Encode all output, implement Content Security Policy headers, and validate/sanitize input.",
                "effort": "Medium",
                "timeline": "1-2 weeks"
            },
            "Path Traversal": {
                "priority": 2,
                "recommendation": "Implement path validation",
                "details": "Use allowlists for file paths, canonicalize paths, and restrict file system access.",
                "effort": "Low",
                "timeline": "1 week"
            },
            "Command Injection": {
                "priority": 1,
                "recommendation": "Avoid system command execution",
                "details": "Use safe APIs instead of system commands. If unavoidable, use strict input validation and allowlists.",
                "effort": "High",
                "timeline": "Immediate"
            },
            "Authentication Bypass": {
                "priority": 1,
                "recommendation": "Strengthen authentication",
                "details": "Implement multi-factor authentication, secure session management, and proper access controls.",
                "effort": "High",
                "timeline": "Immediate"
            },
            "Session Hijack": {
                "priority": 2,
                "recommendation": "Secure session management",
                "details": "Use secure, HttpOnly cookies, implement session timeout, regenerate session IDs, use HTTPS.",
                "effort": "Medium",
                "timeline": "1-2 weeks"
            }
        }
        
        recommendations = []
        for vuln in vulnerabilities:
            if vuln in remediations:
                rec = remediations[vuln]
                recommendations.append({
                    "vulnerability": vuln,
                    "priority": rec["priority"],
                    "recommendation": rec["recommendation"],
                    "details": rec["details"],
                    "effort": rec["effort"],
                    "timeline": rec["timeline"]
                })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"])
        
        return recommendations
    
    def _generate_html_report(
        self,
        target: str,
        executive_summary: str,
        risk_metrics: Dict,
        technical_findings: List[Dict],
        remediation_section: List[Dict],
        compliance_scores: Dict,
        compliance_findings: Dict,
        simulation_result: Dict,
        attack_path: List[Dict]
    ) -> str:
        """Generate complete HTML report"""
        
        # Risk level colors
        risk_colors = {
            "Critical": "#ff4444",
            "High": "#ff8800",
            "Medium": "#ffaa00",
            "Low": "#00ff88"
        }
        risk_color = risk_colors.get(risk_metrics["risk_level"], "#00d4ff")
        
        # Generate findings HTML
        findings_html = ""
        for finding in technical_findings:
            severity_color = risk_colors.get(finding["severity"], "#00d4ff")
            findings_html += f"""
            <div class="finding-card">
                <div class="finding-header">
                    <h3>{finding['title']}</h3>
                    <span class="severity-badge" style="background: {severity_color}20; color: {severity_color}; border: 1px solid {severity_color}40;">
                        {finding['severity']} (CVSS: {finding['cvss_score']})
                    </span>
                </div>
                <p><strong>Description:</strong> {finding['description']}</p>
                <p><strong>Impact:</strong> {finding['impact']}</p>
                <p><strong>Evidence:</strong> {finding['evidence']}</p>
            </div>
            """
        
        # Generate remediation HTML
        remediation_html = ""
        for rec in remediation_section:
            remediation_html += f"""
            <div class="remediation-card">
                <div class="remediation-header">
                    <h3>P{rec['priority']}: {rec['vulnerability']}</h3>
                    <span class="timeline-badge">{rec['timeline']}</span>
                </div>
                <p><strong>Recommendation:</strong> {rec['recommendation']}</p>
                <p><strong>Details:</strong> {rec['details']}</p>
                <p><strong>Estimated Effort:</strong> {rec['effort']}</p>
            </div>
            """
        
        # Generate compliance HTML
        compliance_html = ""
        if compliance_scores:
            for framework, score in compliance_scores.items():
                score_color = "#00ff88" if score.score >= 80 else "#ffaa00" if score.score >= 60 else "#ff4444"
                compliance_html += f"""
                <div class="compliance-card">
                    <h3>{framework.value}</h3>
                    <div class="compliance-score" style="color: {score_color}">
                        {score.score:.1f}%
                    </div>
                    <div class="compliance-stats">
                        <span>Compliant: {score.compliant}/{score.total_requirements}</span>
                        <span>Non-Compliant: {score.non_compliant}</span>
                        <span>Critical: {score.critical_findings}</span>
                    </div>
                </div>
                """
        
        # Generate attack path HTML
        attack_path_html = ""
        for i, step in enumerate(attack_path[:20]):  # Limit to 20 steps
            step_color = "#00ff88" if step.get("success") else "#ff4444"
            attack_path_html += f"""
            <div class="attack-step" style="border-left-color: {step_color}">
                <div class="step-number">{i + 1}</div>
                <div class="step-content">
                    <strong>{step.get('action', 'Unknown').replace('_', ' ').title()}</strong>
                    <span class="step-result" style="color: {step_color}">
                        {'Success' if step.get('success') else 'Failed'}
                    </span>
                    <div class="step-details">
                        Access Level: {step.get('access_level', 'N/A').upper()} | 
                        Reward: {step.get('reward', 0):.2f}
                    </div>
                </div>
            </div>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ART-AI Security Assessment Report - {target}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            color: #00d4ff;
            margin-bottom: 0.5rem;
        }}
        
        .header .subtitle {{
            color: #9ca3af;
            font-size: 1.1rem;
        }}
        
        .header .report-meta {{
            margin-top: 1rem;
            font-size: 0.9rem;
            color: #6b7280;
        }}
        
        .section {{
            background: rgba(20, 25, 50, 0.85);
            border: 1px solid rgba(0, 212, 255, 0.15);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
        }}
        
        .section h2 {{
            color: #00d4ff;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
        }}
        
        .risk-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .risk-card {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .risk-card .value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        
        .risk-card .label {{
            color: #9ca3af;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .executive-summary {{
            white-space: pre-wrap;
            line-height: 1.8;
            color: #e0e0e0;
        }}
        
        .finding-card, .remediation-card, .compliance-card {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .finding-header, .remediation-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        
        .finding-header h3, .remediation-header h3 {{
            color: #fff;
            font-size: 1.1rem;
        }}
        
        .severity-badge, .timeline-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        
        .timeline-badge {{
            background: rgba(0, 212, 255, 0.15);
            color: #00d4ff;
            border: 1px solid rgba(0, 212, 255, 0.4);
        }}
        
        .finding-card p, .remediation-card p {{
            margin-bottom: 0.5rem;
            color: #9ca3af;
        }}
        
        .finding-card strong, .remediation-card strong {{
            color: #e0e0e0;
        }}
        
        .compliance-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }}
        
        .compliance-card h3 {{
            color: #fff;
            margin-bottom: 1rem;
        }}
        
        .compliance-score {{
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        
        .compliance-stats {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            font-size: 0.85rem;
            color: #9ca3af;
        }}
        
        .attack-path {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        
        .attack-step {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 3px solid;
        }}
        
        .step-number {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: rgba(0, 212, 255, 0.2);
            color: #00d4ff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.85rem;
        }}
        
        .step-content {{
            flex: 1;
        }}
        
        .step-content strong {{
            color: #fff;
        }}
        
        .step-result {{
            margin-left: 1rem;
            font-size: 0.85rem;
        }}
        
        .step-details {{
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 0.25rem;
        }}
        
        .footer {{
            text-align: center;
            padding-top: 2rem;
            margin-top: 2rem;
            border-top: 1px solid rgba(0, 212, 255, 0.2);
            color: #6b7280;
            font-size: 0.85rem;
        }}
        
        @media print {{
            body {{
                background: #fff;
                color: #000;
            }}
            .section {{
                background: #f5f5f5;
                border-color: #ddd;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ART-AI Security Assessment Report</h1>
            <p class="subtitle">Autonomous Red Team - AI-Powered Penetration Testing</p>
            <div class="report-meta">
                <strong>Target:</strong> {target} | 
                <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                <strong>Report ID:</strong> ART-{datetime.now().strftime('%Y%m%d%H%M%S')}
            </div>
        </div>
        
        <div class="section">
            <h2>Risk Overview</h2>
            <div class="risk-overview">
                <div class="risk-card">
                    <div class="value" style="color: {risk_color}">{risk_metrics['overall_risk_score']}</div>
                    <div class="label">Risk Score</div>
                </div>
                <div class="risk-card">
                    <div class="value" style="color: {risk_color}">{risk_metrics['risk_level']}</div>
                    <div class="label">Risk Level</div>
                </div>
                <div class="risk-card">
                    <div class="value" style="color: {'#00ff88' if risk_metrics['access_level_achieved'] == 'none' else '#ff4444'}">{risk_metrics['access_level_achieved'].upper()}</div>
                    <div class="label">Access Achieved</div>
                </div>
                <div class="risk-card">
                    <div class="value" style="color: #ff4444">{risk_metrics['vulnerability_count']}</div>
                    <div class="label">Vulnerabilities</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="executive-summary">{executive_summary}</div>
        </div>
        
        <div class="section">
            <h2>Technical Findings</h2>
            {findings_html if findings_html else '<p style="color: #6b7280">No vulnerabilities discovered.</p>'}
        </div>
        
        <div class="section">
            <h2>Remediation Recommendations</h2>
            {remediation_html if remediation_html else '<p style="color: #6b7280">No remediation required.</p>'}
        </div>
        
        {f'''
        <div class="section">
            <h2>Compliance Mapping</h2>
            <div class="compliance-grid">
                {compliance_html}
            </div>
        </div>
        ''' if compliance_html else ''}
        
        <div class="section">
            <h2>Attack Path Analysis</h2>
            <div class="attack-path">
                {attack_path_html if attack_path_html else '<p style="color: #6b7280">No attack path recorded.</p>'}
            </div>
            {f'<p style="margin-top: 1rem; color: #6b7280; font-size: 0.85rem;">Showing first 20 of {len(attack_path)} steps.</p>' if len(attack_path) > 20 else ''}
        </div>
        
        <div class="footer">
            <p>Generated by ART-AI - Autonomous Red Team AI</p>
            <p>This report is confidential and intended for authorized personnel only.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
