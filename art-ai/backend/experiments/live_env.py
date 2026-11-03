"""LiveAttackEnv -- the same interface as AttackMDP, but every action hits the real lab.

Interface compatibility is the point: every agent in ``agents.py`` runs against this
unchanged. Same State tuple, same ``state_key``, same action names, same bounded reward
contract (-STEP_COST per action, +GOAL_REWARD on the transition into ADMIN).

WHAT IS DIFFERENT FROM THE SIM
------------------------------
* ``exploit`` calls a real capability probe (live/capabilities.py) and escalates ONLY on a
  True oracle verdict backed by a logged response. No probability is consulted.
* ``recon`` performs a real port scan via backend/recon.py and discovers hosts that are
  actually open and HTTP-responsive. ``grounding.recon_prob`` (0.90) has no live meaning.
* There is NO ``transitions()``: a live environment has no enumerable kernel.
* ``rng`` is accepted for signature compatibility and used ONLY for tie-breaking. It never
  decides an outcome.

The simulation is untouched and still exists precisely because value iteration needs an
enumerable kernel that a live environment cannot provide.
"""

from __future__ import annotations

import random
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from live.capabilities import (FOOTHOLD, HOST_NAMES, HOST_PORTS, PRIVESC,  # noqa: E402
                               ProbeResult)
from live.http_client import (LabSession, LabUnreachable, get_request_count,  # noqa: E402
                              lab_is_up)

from .mdp import ADMIN, GOAL_REWARD, NONE, STEP_COST, USER, State, state_key  # noqa: E402

N_LIVE_HOSTS = len(HOST_NAMES)
ACTIONS: List[str] = ["recon", "exploit"] + [f"move_{i}" for i in range(N_LIVE_HOSTS)]


def initial_state() -> State:
    return (NONE, 0, frozenset())


def is_terminal(s: State) -> bool:
    return s[0] == ADMIN


class LiveAttackEnv:
    """Live counterpart to AttackMDP. Every action is a real interaction with the lab."""

    def __init__(self, hosts: Optional[List[str]] = None, evidence_sink=None,
                 recon_reveals_all: bool = False, defense=None):
        """
        Args:
            hosts: subset of live hosts to expose (default: all). Used to restrict the
                live action space to the sim-equivalent host set for a fair comparison.
            evidence_sink: callable(dict) appending to the append-only evidence log.
            recon_reveals_all: False (default) => one recon reveals ONE host, matching the
                sim exactly, which is the defensible choice for sim-vs-live comparison.
        """
        self.hosts = hosts or list(HOST_NAMES)
        self.actions = ["recon", "exploit"] + [f"move_{i}" for i in range(len(self.hosts))]
        self.evidence_sink = evidence_sink
        self.recon_reveals_all = recon_reveals_all
        # Optional real defender (rate limit / lockout / probabilistic block). None =>
        # the deterministic lab, exactly as before; all existing results and the
        # rng-independence test are unaffected. See backend/live/defenses.py.
        self.defense = defense
        # Persistence-aware observation: a host is reported "locked-believed" only after
        # this many CONSECUTIVE blocks, so a single transient filter block does not make
        # the agent abandon a recoverable host. (COMPLEX_LAB_RESULTS.md explains why
        # occurrence-only observation made learning over-react under a strong defender.)
        self.persist_threshold = 2
        self._block_count: dict = {}
        self.session: Optional[LabSession] = None
        self.episode_tag = ""
        self.episode = 0
        self._step_idx = 0
        self._footheld: set = set()
        self._scan_cache: Optional[List[int]] = None

    # ------------------------------------------------------------------ interface
    def reset(self) -> State:
        """New episode. Reset strategy (see LIVE_RESULTS.md):

        * probes are idempotent (differentials and reads repeat cleanly), so no container
          restart is needed;
        * the one mutating probe (VAmPI registration) uses a per-episode unique username,
          so episodes never collide.
        Cost: a fresh cookie jar only -- effectively 0s.
        """
        self.session = LabSession()
        self.episode += 1
        self.episode_tag = f"ep{self.episode}-{uuid.uuid4().hex[:6]}"
        self._step_idx = 0
        self._footheld = set()
        self._block_count = {}
        if self.defense is not None:
            self.defense.reset()
        if self.defense is not None and self.defense.active:
            # defender-aware observation: carry an (initially empty) observed-blocked set
            return (NONE, 0, frozenset(), frozenset())
        return initial_state()

    def transitions(self, s: State, a: str):
        # A live environment has no enumerable transition kernel: outcomes are observed,
        # not enumerated. Value iteration therefore stays on the simulation -- which is
        # exactly why the simulation still exists.
        raise NotImplementedError(
            "LiveAttackEnv has no enumerable kernel; run value iteration on AttackMDP."
        )

    def step(self, s: State, a: str, rng: random.Random) -> Tuple[State, float, bool]:
        """Execute ``a`` for real. ``rng`` is accepted for signature compatibility and is
        used only for tie-breaking; it never decides an outcome."""
        if is_terminal(s):
            return s, 0.0, True
        if self.session is None:
            self.reset()

        self._step_idx += 1
        # The defender-aware observation carries a 4th element: the set of hosts the agent
        # has OBSERVED blocked. The core transition logic still operates on the 3-tuple, so
        # the handlers below are unchanged; the belief is updated and re-attached here.
        core = tuple(s[:3])
        access, position, discovered = core
        observe_defender = self.defense is not None and self.defense.active
        blocked = set(s[3]) if len(s) > 3 else set()
        reward = -STEP_COST
        ns = core
        verdict: Optional[bool] = None
        evidence = ""
        reqs: List[dict] = []
        host = None
        error = None

        t0 = time.monotonic()
        try:
            if a == "recon":
                ns, evidence, reqs = self._do_recon(core)
            elif a.startswith("move_"):
                i = int(a.split("_")[1])
                if i in discovered:
                    ns = (access, i, discovered)
                    evidence = f"moved to host {i} ({self.hosts[i]})"
                else:
                    evidence = f"host {i} not discovered; move refused"
            elif a == "exploit":
                ns, reward, verdict, evidence, reqs, host = self._do_exploit(core, reward)
            else:
                raise ValueError(f"unknown action {a}")
        except LabUnreachable as e:
            # A failed request is a failed action recorded as an error -- NEVER a
            # probability roll or a fabricated outcome.
            error = str(e)
            evidence = f"lab unreachable: {e}"

        # Update the agent's belief via a per-host CONSECUTIVE-block count: a block
        # increments it, any attempt that actually reached the oracle resets it. A host is
        # reported "locked-believed" (and so enters the observation) only once the count
        # crosses persist_threshold -- so a one-off transient filter block does not trigger
        # abandonment, but a genuine lockout (repeated blocks) does. This is the persistence
        # signal, not mere occurrence.
        if observe_defender and a == "exploit" and host is not None:
            if evidence.startswith("defender:"):
                self._block_count[host] = self._block_count.get(host, 0) + 1
            elif verdict is not None:
                self._block_count[host] = 0
        if observe_defender:
            locked = frozenset(h for h, c in self._block_count.items()
                               if c >= self.persist_threshold)
            ns = tuple(ns[:3]) + (locked,)

        done = is_terminal(ns)
        if self.evidence_sink:
            self.evidence_sink({
                "ts": time.time(),
                "episode": self.episode,
                "step": self._step_idx,
                "state": state_key(s),
                "action": a,
                "host": host,
                "oracle_verdict": verdict,
                "evidence": evidence,
                "requests": reqs,
                "next_state": state_key(ns),
                "reward": reward,
                "done": done,
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                "error": error,
            })
        return ns, reward, done

    # ------------------------------------------------------------------- internals
    def _do_recon(self, s: State):
        """Real port scan; discover hosts actually open AND HTTP-responsive.

        Parity with the sim: ONE recon reveals ONE host (the lowest-index undiscovered
        host that the scan confirms live). This keeps the live episode length comparable
        to the simulated one, which is what makes the sim-vs-live comparison meaningful.
        """
        access, position, discovered = s
        if self._scan_cache is None:
            from recon import ReconEngine
            eng = ReconEngine()
            ports = [HOST_PORTS[h] for h in self.hosts]
            scan = eng.scan_ports("127.0.0.1", ports=ports)
            self._scan_cache = [p["port"] for p in scan["open_ports"]]
        live_ports = self._scan_cache

        undiscovered = [i for i in range(len(self.hosts)) if i not in discovered]
        for i in undiscovered:
            if HOST_PORTS[self.hosts[i]] in live_ports:
                ns = (access, position, frozenset(discovered | {i}))
                return ns, f"recon confirmed {self.hosts[i]}:{HOST_PORTS[self.hosts[i]]} open", []
        return s, f"recon found no new live host (open={live_ports})", []

    def _do_exploit(self, s: State, reward: float):
        access, position, discovered = s
        host = self.hosts[position]
        if position not in discovered:
            return s, reward, None, f"{host} not discovered; exploit refused", [], host

        # Defender gate (only ever causes FAILURE; never fabricates success). Checked
        # before any oracle request so a blocked attempt sends no traffic.
        if self.defense is not None and self.defense.active:
            self.defense.record_attempt(host, self._step_idx)
            block = self.defense.check(host, self._step_idx)
            if block is not None:
                self.defense.record_result(host, False, self._step_idx)
                return s, reward, False, f"defender: {block}", [], host

        if access == NONE:
            try:
                res: ProbeResult = FOOTHOLD[host](self.session, self.episode_tag)
            except TypeError:
                res = FOOTHOLD[host](self.session)
            self._rec(host, res.success)
            if res.success:
                self._footheld.add(host)
                return (USER, position, discovered), reward, True, res.evidence, res.requests, host
            return s, reward, False, res.evidence, res.requests, host

        if access == USER:
            # ABSTRACTION MISMATCH, handled explicitly (see LIVE_RESULTS.md):
            # the simulation treats `access` as a GLOBAL privilege level, so its optimal
            # policy takes a cheap foothold on one host and escalates on a different one.
            # That is false in this lab: the five targets are independent web apps and
            # credentials do not transfer (a Juice Shop JWT is worthless on DVWA).
            # To escalate on a host you must first hold access ON THAT HOST, so we
            # establish this host's own foothold before attempting its privesc.
            if host not in self._footheld:
                try:
                    fres = FOOTHOLD[host](self.session, self.episode_tag)
                except TypeError:
                    fres = FOOTHOLD[host](self.session)
                reqs_pre = fres.requests
                if not fres.success:
                    self._rec(host, False)
                    return s, reward, False, f"privesc blocked: no foothold on {host} ({fres.evidence})", \
                           reqs_pre, host
                self._footheld.add(host)
            else:
                reqs_pre = []

            fn = PRIVESC[host]
            try:
                res = fn(self.session, self.episode_tag)  # vampi takes an episode tag
            except TypeError:
                res = fn(self.session)
            res.requests = reqs_pre + res.requests
            self._rec(host, res.success)
            if res.success:
                # goal reward paid on the transition into ADMIN
                return (ADMIN, position, discovered), reward + GOAL_REWARD, True, \
                       res.evidence, res.requests, host
            return s, reward, False, res.evidence, res.requests, host

        return s, reward, None, "already ADMIN", [], host

    def _rec(self, host: str, success: bool):
        """Record an oracle outcome with the defender (for lockout tracking)."""
        if self.defense is not None and self.defense.active:
            self.defense.record_result(host, success, self._step_idx)


def lab_health() -> Tuple[bool, str]:
    """Health gate for the harness: never fake results when the lab is down."""
    status = lab_is_up(tuple(HOST_PORTS[h] for h in HOST_NAMES))
    down = [p for p, ok in status.items() if not ok]
    if down:
        return False, f"lab ports not answering: {down}"
    return True, f"all lab ports up: {sorted(status)}"
