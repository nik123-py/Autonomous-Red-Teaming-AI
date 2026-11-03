"""Evidence-backed vulnerability detection against the local lab.

Replaces the `SERVICE_VULNERABILITIES` template lookup in vulnerability_scanner.py,
which emitted the same three findings -- with placeholder CVE ids CVE-2023-XXXXX /
YYYYY / ZZZZZ -- for every port whose service string was "HTTP", without ever sending a
request. That produced false positives against ports that have none (including ART-AI's
own backend on 8003).

Rules here:
  * A finding is returned ONLY if a real request confirmed it, and it carries the
    evidence that confirmed it.
  * **No fabricated CVE ids.** We report a CWE (a weakness class, which is an accurate
    classification of what we observed) and leave `cve` as None unless a specific CVE is
    genuinely known for that component. Inventing a CVE number is worse than omitting it.
  * All traffic goes through the scope-checked chokepoint in http_client.py
    (127.0.0.1:3001-3006 only).
  * Non-destructive: reads and observes, never deletes or persists.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .http_client import ALLOWED, LabSession, LabUnreachable, ScopeViolation


@dataclass
class Finding:
    name: str
    severity: str                  # critical | high | medium | low
    cwe: str                       # accurate weakness classification
    description: str
    evidence: str                  # what actually proved it
    port: int
    service: str = "HTTP"
    cve: Optional[str] = None      # only when genuinely known; never fabricated
    confirmed: bool = True
    exploit_available: bool = False
    remediation: str = ""
    requests: List[dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "severity": self.severity, "cwe": self.cwe,
            "cve": self.cve, "description": self.description,
            "evidence": self.evidence, "confirmed": self.confirmed,
            "port": self.port, "service": self.service,
            "exploit_available": self.exploit_available,
            "remediation": self.remediation,
            "verified_by": [f"{r['method']} {r['url']} -> {r['status']}" for r in self.requests],
        }


def _base(port: int) -> str:
    return f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------- detectors
def detect_sql_injection(s: LabSession, port: int) -> Optional[Finding]:
    """Differential SQLi: an injected query must return strictly more data than a
    benign one, or surface a database error the benign request does not."""
    candidates = [
        ("/api/users?id=1", "/api/users?id=1%20OR%201=1"),          # flask-api
        ("/sqli_1.php?title=Iron&action=search",
         "/sqli_1.php?title=%27+or+1%3D1%23&action=search"),        # bwapp
        ("/rest/products/search?q=apple",
         "/rest/products/search?q=apple%27"),                       # juice-shop
    ]
    for benign_path, inj_path in candidates:
        try:
            b = s.get(_base(port) + benign_path)
            i = s.get(_base(port) + inj_path)
        except LabUnreachable:
            continue
        if b.status >= 400 and i.status >= 400:
            continue

        # (a) database error surfaced only by the injected request
        db_err = re.search(r"SQLITE_ERROR|SQL syntax|sqlalchemy|near \"|unrecognized token|"
                           r"You have an error in your SQL", i.body, re.I)
        if db_err and not re.search(r"SQLITE_ERROR|SQL syntax|sqlalchemy", b.body, re.I):
            return Finding(
                "SQL Injection", "high", "CWE-89",
                "User input is interpolated into a SQL query",
                f"injected request surfaced a database error the benign request did not: "
                f"{db_err.group(0)!r}",
                port, exploit_available=True,
                remediation="Use parameterised queries / prepared statements",
                requests=[b.record.to_dict(), i.record.to_dict()])

        # (b) strictly more rows returned
        n_b, n_i = _row_count(b.body), _row_count(i.body)
        if n_i > n_b and n_b >= 1:
            return Finding(
                "SQL Injection", "high", "CWE-89",
                "User input is interpolated into a SQL query",
                f"benign query returned {n_b} record(s); injected query returned {n_i}",
                port, exploit_available=True,
                remediation="Use parameterised queries / prepared statements",
                requests=[b.record.to_dict(), i.record.to_dict()])
    return None


def detect_path_traversal(s: LabSession, port: int) -> Optional[Finding]:
    """Confirmed only if the response actually contains OS file content."""
    payloads = ["/api/file?name=../../etc/passwd", "/api/file?name=../../../etc/passwd"]
    for p in payloads:
        try:
            r = s.get(_base(port) + p)
        except LabUnreachable:
            continue
        if r.status == 200 and re.search(r"root:x:0:0:", r.body):
            return Finding(
                "Path Traversal", "high", "CWE-22",
                "File path parameter is not validated, allowing access outside the intended directory",
                "response contained /etc/passwd content (matched 'root:x:0:0:')",
                port, exploit_available=True,
                remediation="Canonicalise the path and confirm it stays within an allow-listed base directory",
                requests=[r.record.to_dict()])
    return None


def detect_reflected_xss(s: LabSession, port: int) -> Optional[Finding]:
    """Confirmed only if our marker comes back with HTML metacharacters unencoded."""
    marker = f"artai{uuid.uuid4().hex[:6]}"
    payload = f"<b>{marker}</b>"
    for path in ["/api/search?q=", "/search?q=", "/?q="]:
        try:
            r = s.get(_base(port) + path + payload.replace("<", "%3C").replace(">", "%3E"))
        except LabUnreachable:
            continue
        if r.status == 200 and f"<b>{marker}</b>" in r.body:
            return Finding(
                "Reflected Cross-Site Scripting", "medium", "CWE-79",
                "User input is reflected into the response without output encoding",
                f"payload <b>{marker}</b> was reflected with tags intact (not HTML-encoded)",
                port, exploit_available=True,
                remediation="HTML-encode all user input on output; set a restrictive Content-Security-Policy",
                requests=[r.record.to_dict()])
    return None


def detect_sensitive_data_exposure(s: LabSession, port: int) -> Optional[Finding]:
    """Confirmed only if an unauthenticated response actually contains credentials."""
    for path in ["/users/v1/_debug", "/api/users", "/debug"]:
        try:
            r = s.get(_base(port) + path)
        except LabUnreachable:
            continue
        if r.status == 200 and re.search(r'"password"\s*:', r.body):
            n = len(re.findall(r'"password"\s*:', r.body))
            return Finding(
                "Sensitive Data Exposure", "critical", "CWE-200",
                "An unauthenticated endpoint returns user credentials",
                f"GET {path} returned {n} plaintext password field(s) without authentication",
                port, exploit_available=True,
                remediation="Remove debug endpoints from production; never return credentials",
                requests=[r.record.to_dict()])
    return None


def detect_weak_credentials(s: LabSession, port: int) -> Optional[Finding]:
    """Confirmed only if a well-known default credential actually authenticates."""
    attempts = [
        ("/api/login", {"username": "admin", "password": "admin123"}, True),
        ("/api/login", {"username": "admin", "password": "admin"}, True),
    ]
    for path, body, as_json in attempts:
        try:
            r = s.post(_base(port) + path, json_body=body) if as_json else \
                s.post(_base(port) + path, data=body)
        except LabUnreachable:
            continue
        if r.status == 200 and re.search(r'"success"\s*:\s*true|"token"\s*:', r.body, re.I):
            role = re.search(r'"role"\s*:\s*"([^"]+)"', r.body)
            return Finding(
                "Use of Default/Weak Credentials", "critical", "CWE-1392",
                "A default account authenticates with a guessable password",
                f"{body['username']}/{body['password']} authenticated successfully"
                + (f" with role={role.group(1)}" if role else ""),
                port, exploit_available=True,
                remediation="Force a password change on first login; block known-weak passwords",
                requests=[r.record.to_dict()])
    return None


def detect_auth_bypass(s: LabSession, port: int) -> Optional[Finding]:
    """SQLi authentication bypass: confirmed only if a token is actually issued."""
    try:
        r = s.post(_base(port) + "/rest/user/login",
                   json_body={"email": "' OR 1=1--", "password": "x"})
    except LabUnreachable:
        return None
    if r.status == 200 and '"token"' in r.body:
        return Finding(
            "Authentication Bypass via SQL Injection", "critical", "CWE-89",
            "The login query is built by string concatenation, so authentication can be bypassed",
            "a session token was issued for the payload \"' OR 1=1--\" with no valid password",
            port, exploit_available=True,
            remediation="Use parameterised queries for authentication lookups",
            requests=[r.record.to_dict()])
    return None


DETECTORS = [
    detect_sql_injection,
    detect_path_traversal,
    detect_reflected_xss,
    detect_sensitive_data_exposure,
    detect_weak_credentials,
    detect_auth_bypass,
]


def _row_count(body: str) -> int:
    """Best-effort record count for a differential comparison."""
    if not body:
        return 0
    n = len(re.findall(r"<tr[ >]", body))
    if n:
        return n
    n = len(re.findall(r'"(?:id|username|name|email)"\s*:', body))
    if n:
        return n
    return len(re.findall(r"First name:", body))


def scan_port(port: int, session: Optional[LabSession] = None) -> List[Dict]:
    """Run every detector against one in-scope port. Returns only CONFIRMED findings."""
    if ("127.0.0.1", port) not in ALLOWED:
        raise ScopeViolation(
            f"Port {port} is outside the local lab allowlist; refusing to scan it.")
    s = session or LabSession()
    findings: List[Finding] = []
    for det in DETECTORS:
        try:
            f = det(s, port)
        except (LabUnreachable, ScopeViolation):
            continue
        except Exception:
            continue
        if f is not None:
            findings.append(f)
    return [f.to_dict() for f in findings]


def scan_ports(ports: List[int]) -> Dict[int, List[Dict]]:
    out: Dict[int, List[Dict]] = {}
    for p in ports:
        if ("127.0.0.1", p) not in ALLOWED:
            continue  # silently skip out-of-scope ports rather than inventing findings
        out[p] = scan_port(p)
    return out
