"""A real, stateful defender that injects *measurable* uncertainty into the live lab.

Why this exists (see RESEARCH_GAP_ANALYSIS.md): the live lab is deterministic -- every
capability succeeds with probability 1.0 -- which makes it a degenerate MDP where a fixed
heuristic matches a learned policy. Real targets are not deterministic: they rate-limit,
lock accounts, and sit behind filters that block a fraction of attempts. This module adds
those three mechanisms as a configurable, stateful policy the live environment consults
before each exploit attempt.

HONESTY INVARIANTS (these are load-bearing):
  * The defender can ONLY cause an attempt to FAIL (rate-limited / locked out / blocked).
    It never turns a real failure into a success. The "no fabricated success" rule of the
    live environment is therefore preserved: a success still requires a real oracle
    verdict on a real response.
  * Every block is recorded as a defense event in the evidence log, so the induced
    stochasticity is OBSERVED, not assumed.
  * The probabilistic block uses a DEDICATED defender RNG owned by the environment, never
    the agent's tie-break rng. With the default policy (all mechanisms off) the
    environment stays exactly deterministic, so existing results and the
    rng-independence test are unaffected.

Rate limiting and lockout are deterministic functions of the attempt sequence; only the
probabilistic WAF consults the defender RNG.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DefensePolicy:
    """Per-episode defender state.

    rate_limit: max attempts per host per episode before a cooldown kicks in (None = off).
    rate_cooldown: steps a host stays rate-limited once the limit is hit.
    lockout_threshold: consecutive FAILED attempts on a host before it locks (None = off).
    lockout_steps: steps a host stays locked.
    waf_block_p: probability an attempt is blocked by a filter (0.0 = off).
    seed: seeds the dedicated defender RNG (reproducible stochasticity).
    """
    rate_limit: Optional[int] = None
    rate_cooldown: int = 3
    lockout_threshold: Optional[int] = None
    lockout_steps: int = 5
    waf_block_p: float = 0.0
    # Optional PER-HOST block probabilities that override waf_block_p for named hosts.
    # A heterogeneous posture (some hosts defended far more than others) is the regime
    # where routing -- a learned skill -- can beat a heuristic that fixates on the
    # CVSS-best host. A uniform (global) filter is NOT routable, so learning cannot help
    # there; see COMPLEX_LAB_RESULTS.md.
    host_waf: Optional[Dict[str, float]] = None
    seed: int = 0

    # runtime state (per episode)
    _attempts: Dict[str, int] = field(default_factory=dict)
    _fails: Dict[str, int] = field(default_factory=dict)
    _locked_until: Dict[str, int] = field(default_factory=dict)
    _rate_until: Dict[str, int] = field(default_factory=dict)
    _rng: random.Random = field(default_factory=lambda: random.Random(0))
    # counters for measurement / reporting
    events: Dict[str, int] = field(default_factory=lambda: {"rate": 0, "lockout": 0, "waf": 0, "allowed": 0})

    def __post_init__(self):
        # Seed the defender RNG ONCE. reset() must not re-seed it, or every episode would
        # replay the identical block pattern (making the defender deterministic across
        # episodes and erasing the uncertainty the agent is meant to learn to handle).
        self._rng = random.Random(self.seed)

    def reset(self):
        # Per-episode state only; the RNG stream deliberately flows across episodes so each
        # episode sees a different (but, for a fixed seed, reproducible) sequence of blocks.
        self._attempts.clear()
        self._fails.clear()
        self._locked_until.clear()
        self._rate_until.clear()
        self.events = {"rate": 0, "lockout": 0, "waf": 0, "allowed": 0}

    @property
    def active(self) -> bool:
        return (self.rate_limit is not None or self.lockout_threshold is not None
                or self.waf_block_p > 0.0 or bool(self.host_waf))

    def _waf_for(self, host: str) -> float:
        if self.host_waf and host in self.host_waf:
            return self.host_waf[host]
        return self.waf_block_p

    def check(self, host: str, step_idx: int) -> Optional[str]:
        """Return a block-reason string if this attempt is denied, else None.

        Deterministic checks (lockout, rate) first; the probabilistic block last so a
        locked host is reported as locked rather than consuming a random draw.
        """
        if self.lockout_threshold is not None and step_idx < self._locked_until.get(host, 0):
            self.events["lockout"] += 1
            return f"account locked out until step {self._locked_until[host]}"
        if self.rate_limit is not None and step_idx < self._rate_until.get(host, 0):
            self.events["rate"] += 1
            return f"rate-limited (429) until step {self._rate_until[host]}"
        p = self._waf_for(host)
        if p > 0.0 and self._rng.random() < p:
            self.events["waf"] += 1
            return f"blocked by filter (403), p={p}"
        self.events["allowed"] += 1
        return None

    def record_attempt(self, host: str, step_idx: int):
        """Count an attempt; trip the rate limiter when the per-host budget is exceeded."""
        n = self._attempts.get(host, 0) + 1
        self._attempts[host] = n
        if self.rate_limit is not None and n > self.rate_limit:
            self._rate_until[host] = step_idx + self.rate_cooldown

    def record_result(self, host: str, success: bool, step_idx: int):
        """Track consecutive failures; lock the host when the threshold is crossed."""
        if self.lockout_threshold is None:
            return
        if success:
            self._fails[host] = 0
        else:
            f = self._fails.get(host, 0) + 1
            self._fails[host] = f
            if f >= self.lockout_threshold:
                self._locked_until[host] = step_idx + self.lockout_steps
                self._fails[host] = 0  # reset after locking


# --- named strengths for the defender-strength sweep (research question 1) ----------
def policy_for_strength(level: int, seed: int = 0) -> DefensePolicy:
    """level 0 = no defender (deterministic, the current lab); 1..3 increasing."""
    presets = {
        0: dict(),
        1: dict(waf_block_p=0.25, lockout_threshold=6, lockout_steps=4),
        2: dict(waf_block_p=0.45, lockout_threshold=4, lockout_steps=5, rate_limit=8, rate_cooldown=3),
        3: dict(waf_block_p=0.65, lockout_threshold=3, lockout_steps=6, rate_limit=5, rate_cooldown=4),
        # 4 = HETEROGENEOUS / routable: the host the CVSS-greedy baseline fixates on
        # (juice-shop, highest foothold prior) is heavily defended, while flask-api is
        # left soft. A learner that observes the blocks can route to the soft target; the
        # greedy baseline cannot, because it chooses by prior, not by observed defence.
        4: dict(host_waf={"juice-shop": 0.85, "dvwa": 0.50, "flask-api": 0.05},
                lockout_threshold=3, lockout_steps=5),
    }
    return DefensePolicy(seed=seed, **presets.get(level, {}))


STRENGTH_LABELS = {0: "none", 1: "mild", 2: "medium", 3: "strong", 4: "heterogeneous"}
