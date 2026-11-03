"""The single outbound-request chokepoint for the live lab environment.

EVERY request the live agent makes goes through ``request()``. It hard-fails on any
host/port outside ``ALLOWED``. There is deliberately no environment variable, config key
or CLI flag that can widen the allowlist -- to target anything else you would have to edit
this constant, which is the point.

Scope: the local Docker lab on 127.0.0.1, ports 3001-3006. Nothing else, ever.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import Any, Dict, Optional

# --- the allowlist. Editing this constant is the ONLY way to change scope. ----------
LAB_PORTS = (3001, 3002, 3003, 3004, 3005, 3006)
LAB_HOSTS = ("127.0.0.1", "localhost")
ALLOWED = {(h, p) for h in LAB_HOSTS for p in LAB_PORTS}

DEFAULT_TIMEOUT = 8.0
DEFAULT_RETRIES = 2
DEFAULT_RATE_LIMIT = 10.0  # requests/second, global


class ScopeViolation(Exception):
    """Raised when a request targets anything outside the local lab allowlist."""


@dataclass
class RequestRecord:
    """Auditable record of one real request/response."""
    method: str
    url: str
    status: Optional[int]
    latency_ms: float
    resp_len: int
    snippet: str = ""
    req_body: Optional[str] = None
    error: Optional[str] = None
    headers_sent: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method, "url": self.url, "status": self.status,
            "latency_ms": round(self.latency_ms, 1), "resp_len": self.resp_len,
            "snippet": self.snippet, "req_body": self.req_body,
            "error": self.error, "headers_sent": self.headers_sent,
        }


@dataclass
class Response:
    status: int
    body: str
    headers: Dict[str, str]
    record: RequestRecord

    def json(self) -> Any:
        return json.loads(self.body)


class _RateLimiter:
    """Global token-bucket-ish limiter so a training loop cannot melt the containers."""

    def __init__(self, rps: float):
        self.min_interval = 1.0 / rps if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()


_limiter = _RateLimiter(DEFAULT_RATE_LIMIT)

# Counters for cost reporting
REQUEST_COUNT = 0
_count_lock = threading.Lock()


def reset_request_count():
    global REQUEST_COUNT
    with _count_lock:
        REQUEST_COUNT = 0


def get_request_count() -> int:
    return REQUEST_COUNT


def assert_in_scope(url: str) -> tuple:
    """Parse ``url`` and raise ScopeViolation unless (host, port) is allowlisted.

    This runs BEFORE any socket is opened. Returns (host, port).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScopeViolation(f"Refusing non-http(s) scheme: {parsed.scheme!r} in {url!r}")
    host = parsed.hostname
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if (host, port) not in ALLOWED:
        raise ScopeViolation(
            f"Refusing out-of-scope target {host}:{port}. "
            f"The live lab allowlist is {sorted(ALLOWED)}."
        )
    return host, port


class LabSession:
    """Per-episode session: cookies persist here (DVWA / bWAPP / Juice Shop are stateful)."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES):
        self.timeout = timeout
        self.retries = retries
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            _NoRedirect(),
        )
        self.records: list[RequestRecord] = []

    def request(self, method: str, url: str, *, data: Any = None,
                headers: Optional[Dict[str, str]] = None,
                json_body: Any = None, follow_redirects: bool = False) -> Response:
        return request(method, url, data=data, headers=headers, json_body=json_body,
                       session=self, follow_redirects=follow_redirects)

    def get(self, url, **kw) -> Response:
        return self.request("GET", url, **kw)

    def post(self, url, **kw) -> Response:
        return self.request("POST", url, **kw)

    def cookies(self) -> Dict[str, str]:
        return {c.name: c.value for c in self.cookie_jar}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not auto-follow redirects: a 302 is itself evidence for several oracles."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(method: str, url: str, *, data: Any = None,
            headers: Optional[Dict[str, str]] = None,
            json_body: Any = None,
            session: Optional[LabSession] = None,
            follow_redirects: bool = False,
            timeout: float = DEFAULT_TIMEOUT,
            retries: int = DEFAULT_RETRIES) -> Response:
    """THE chokepoint. Performs one real HTTP request against the local lab.

    Raises ScopeViolation (before opening any socket) for out-of-scope targets.
    """
    # --- scope check happens first, before any socket work -------------------------
    assert_in_scope(url)

    global REQUEST_COUNT

    hdrs = {"User-Agent": "ART-AI-live/1.0 (local lab research)"}
    if headers:
        hdrs.update(headers)

    body: Optional[bytes] = None
    req_body_repr: Optional[str] = None
    if json_body is not None:
        body = json.dumps(json_body).encode()
        hdrs.setdefault("Content-Type", "application/json")
        req_body_repr = json.dumps(json_body)[:300]
    elif data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
            req_body_repr = urllib.parse.urlencode(_redact(data))[:300]
        elif isinstance(data, str):
            body = data.encode()
            req_body_repr = data[:300]
        else:
            body = data
            req_body_repr = "<bytes>"

    opener = session.opener if session is not None else urllib.request.build_opener(_NoRedirect())
    last_err = None

    for attempt in range(retries + 1):
        _limiter.wait()
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method.upper())
        t0 = time.monotonic()
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                text = raw.decode("utf-8", errors="replace")
                latency = (time.monotonic() - t0) * 1000
                rec = RequestRecord(method.upper(), url, resp.status, latency,
                                    len(raw), text[:300], req_body_repr, None, _redact(hdrs))
                with _count_lock:
                    REQUEST_COUNT += 1
                if session is not None:
                    session.records.append(rec)
                return Response(resp.status, text, dict(resp.headers), rec)
        except urllib.error.HTTPError as e:
            # A 4xx/5xx is a real, meaningful response for our oracles -- not an error.
            raw = e.read()
            text = raw.decode("utf-8", errors="replace")
            latency = (time.monotonic() - t0) * 1000
            rec = RequestRecord(method.upper(), url, e.code, latency, len(raw),
                                text[:300], req_body_repr, None, _redact(hdrs))
            with _count_lock:
                REQUEST_COUNT += 1
            if session is not None:
                session.records.append(rec)
            return Response(e.code, text, dict(e.headers or {}), rec)
        except Exception as e:  # connection refused, timeout, etc.
            last_err = e
            if attempt < retries:
                time.sleep(0.25 * (2 ** attempt))  # bounded backoff
                continue
            latency = (time.monotonic() - t0) * 1000
            rec = RequestRecord(method.upper(), url, None, latency, 0, "",
                                req_body_repr, repr(e), _redact(hdrs))
            with _count_lock:
                REQUEST_COUNT += 1
            if session is not None:
                session.records.append(rec)
            raise LabUnreachable(f"{method} {url} failed after {retries + 1} attempts: {e!r}") from e

    raise LabUnreachable(str(last_err))


class LabUnreachable(Exception):
    """The lab did not answer. This is an episode error, never a fabricated outcome."""


def _redact(d: Dict[str, Any]) -> Dict[str, str]:
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in ("auth", "cookie", "token", "password")):
            out[k] = "<redacted>"
        else:
            out[k] = str(v)[:120]
    return out


def lab_is_up(ports=LAB_PORTS) -> Dict[int, bool]:
    """Health gate: which lab ports answer right now."""
    import socket
    status = {}
    for p in ports:
        try:
            with socket.create_connection(("127.0.0.1", p), timeout=1.5):
                status[p] = True
        except OSError:
            status[p] = False
    return status
