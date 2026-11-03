"""Data-grounded exploit-success probabilities for the local lab hosts.

The magic constants in ``AttackEngine.SUCCESS_PROBABILITIES`` are replaced here by
probabilities *derived* from published, citable signals for each host's CVE:

  1. CVSS v3.1 **Exploitability sub-score**. Per the CVSS v3.1 specification
     (FIRST.org, https://www.first.org/cvss/v3.1/specification-document, §7.1),
        Exploitability = 8.22 * AV * AC * PR * UI
     with the standard metric weights encoded in ``_CVSS31`` below. The maximum
     value of that product is 8.22 * 0.85 * 0.77 * 0.85 * 0.85 = 3.887, so we
     normalise by that maximum to get a 0..1 "how easy to exploit" factor.

  2. **EPSS** (Exploit Prediction Scoring System, https://www.first.org/epss/) — the
     probability a CVE is exploited in the wild in the next 30 days, already 0..1.

  3. **Exploit-DB verified** flag — whether a working PoC exists and was verified.

  4. **Patch age** — days since a fix was available. Older-unpatched => the exploit
     path is more likely to still work in a lab pinned to the vulnerable version.

These are combined by a single documented formula (``exploit_probability``). The
weights of that combination are the only tunable knobs, and they are stated
explicitly rather than hidden as per-action literals. The CVE metadata itself is
representative data for the *local* lab images (OWASP Juice Shop, DVWA, a local
Flask/VAmPI-style API); it never targets a third party.

Every probability is clamped to [0.05, 0.95] so no action is impossible or certain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# --- CVSS v3.1 metric weights (from the official specification) -------------------
# Attack Vector, Attack Complexity, Privileges Required, User Interaction.
_CVSS31 = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},
    "AC": {"L": 0.77, "H": 0.44},
    # PR depends on Scope; we use the "Unchanged" column (the common case here).
    "PR": {"N": 0.85, "L": 0.62, "H": 0.27},
    "UI": {"N": 0.85, "R": 0.62},
}
_EXPLOITABILITY_MAX = 8.22 * 0.85 * 0.77 * 0.85 * 0.85  # = 3.8869...


def cvss31_exploitability(av: str, ac: str, pr: str, ui: str) -> float:
    """CVSS v3.1 Exploitability sub-score, normalised to 0..1."""
    raw = 8.22 * _CVSS31["AV"][av] * _CVSS31["AC"][ac] * _CVSS31["PR"][pr] * _CVSS31["UI"][ui]
    return raw / _EXPLOITABILITY_MAX


@dataclass(frozen=True)
class CVE:
    """Representative CVE metadata for one local-lab host capability."""
    cve_id: str
    # CVSS v3.1 base metrics used for the exploitability sub-score:
    av: str  # Attack Vector: N/A/L/P
    ac: str  # Attack Complexity: L/H
    pr: str  # Privileges Required: N/L/H
    ui: str  # User Interaction: N/R
    epss: float          # 0..1, EPSS probability
    exploitdb_verified: bool
    patch_age_days: int  # days the vulnerable version has been public/unpatched


# Combination weights (documented, not hidden). They sum to 1.0 over the three
# score terms; patch age acts as a small multiplicative recency bonus.
_W_CVSS = 0.55   # weight on normalised CVSS exploitability
_W_EPSS = 0.35   # weight on EPSS
_W_VERIFIED = 0.10  # weight on the verified-PoC flag
_PATCH_AGE_HALFLIFE = 365.0  # days; older -> closer to full weight


def exploit_probability(cve: CVE) -> float:
    """Derive a success probability from the CVE's cited signals.

    p = (w_cvss * expl + w_epss * epss + w_verified * verified) * recency
    where ``recency`` grows from ~0.7 (fresh patch) toward 1.0 as the vulnerable
    version stays public. Result clamped to [0.05, 0.95].
    """
    expl = cvss31_exploitability(cve.av, cve.ac, cve.pr, cve.ui)
    verified = 1.0 if cve.exploitdb_verified else 0.0
    base = _W_CVSS * expl + _W_EPSS * cve.epss + _W_VERIFIED * verified
    # Recency: 0.7 at age 0, asymptotes to 1.0. Bounded, monotone in patch age.
    recency = 1.0 - 0.3 * (0.5 ** (cve.patch_age_days / _PATCH_AGE_HALFLIFE))
    p = base * recency
    return max(0.05, min(0.95, p))


# --- The local lab as three hosts -------------------------------------------------
# Host asymmetry is what makes the policy non-trivial: the cheapest foothold host
# is a poor escalation host, and vice-versa, so the optimal agent must recon, take
# a cheap foothold, then reposition to the best escalation host.

@dataclass(frozen=True)
class Host:
    name: str
    foothold: CVE   # NONE -> USER on this host
    privesc: CVE    # USER -> ADMIN on this host


HOSTS = [
    # Host 0 — OWASP Juice Shop: trivial remote foothold (unauth), weak local privesc.
    Host(
        name="juice-shop",
        foothold=CVE("LAB-JS-FOOTHOLD", av="N", ac="L", pr="N", ui="N",
                     epss=0.62, exploitdb_verified=True, patch_age_days=800),
        privesc=CVE("LAB-JS-PRIVESC", av="L", ac="H", pr="L", ui="N",
                    epss=0.05, exploitdb_verified=False, patch_age_days=120),
    ),
    # Host 1 — DVWA: moderate on both axes.
    Host(
        name="dvwa",
        foothold=CVE("LAB-DVWA-FOOTHOLD", av="N", ac="L", pr="N", ui="R",
                     epss=0.30, exploitdb_verified=True, patch_age_days=500),
        privesc=CVE("LAB-DVWA-PRIVESC", av="L", ac="L", pr="L", ui="N",
                    epss=0.25, exploitdb_verified=True, patch_age_days=400),
    ),
    # Host 2 — local Flask/VAmPI API: hard remote foothold, but strong local privesc.
    Host(
        name="flask-api",
        foothold=CVE("LAB-API-FOOTHOLD", av="N", ac="H", pr="L", ui="N",
                     epss=0.12, exploitdb_verified=False, patch_age_days=200),
        privesc=CVE("LAB-API-PRIVESC", av="L", ac="L", pr="L", ui="N",
                    epss=0.55, exploitdb_verified=True, patch_age_days=700),
    ),
]

N_HOSTS = len(HOSTS)


def foothold_probs() -> Dict[int, float]:
    return {i: exploit_probability(h.foothold) for i, h in enumerate(HOSTS)}


def privesc_probs() -> Dict[int, float]:
    return {i: exploit_probability(h.privesc) for i, h in enumerate(HOSTS)}


def recon_prob() -> float:
    # Discovery of an exposed local service is reliable but not certain.
    return 0.90


if __name__ == "__main__":
    print("Grounded per-host probabilities (derived from CVSS/EPSS/verified/patch-age):")
    fp, pp = foothold_probs(), privesc_probs()
    for i, h in enumerate(HOSTS):
        print(f"  [{i}] {h.name:12s} foothold p={fp[i]:.3f}  privesc p={pp[i]:.3f}")
    print(f"  recon p={recon_prob():.3f}")
