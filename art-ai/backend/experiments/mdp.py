"""A fully-specified, enumerable attack MDP grounding the local lab.

Because the state and action sets are finite and the transition kernel P(s'|s,a)
is written out explicitly, the optimal policy is computable exactly by value
iteration (see ``value_iteration.py``). That optimum is the ceiling every learning
agent is measured against.

STATE ENCODING (documented, Step 2 requirement)
------------------------------------------------
A state is the tuple ``(access, position, discovered)``:

  * ``access`` in {0:NONE, 1:USER, 2:ADMIN} — global privilege level obtained so far.
    ADMIN is the goal and is absorbing (terminal).
  * ``position`` in {0..N_HOSTS-1} — which host the attacker currently operates from.
    ``exploit`` always acts on the host at ``position``.
  * ``discovered`` — a frozenset of host indices that recon has revealed. You can
    only ``move`` to, or ``exploit``, a host you have discovered.

The canonical string key used by the tabular Q-table is::

    "a{access}|p{position}|d{sorted-comma-joined discovered}"

e.g. ``a1|p0|d0,1`` = USER access, positioned on host 0, hosts {0,1} discovered.
This encodes discovered services (which hosts/CVEs are known), per-host position,
and — via ``access`` — the escalation progress, i.e. the very fields the original
code tracked in ``EnvironmentState`` but never put into the state key.

ACTIONS
-------
  * ``recon``        — reveal the lowest-index undiscovered host (w.p. p_recon).
  * ``exploit``      — act on host at ``position``:
        access NONE -> USER  w.p. foothold_p[position]  (host must be discovered)
        access USER -> ADMIN w.p. privesc_p[position]   (host must be discovered)
  * ``move_i``       — reposition to host i (must be discovered), else no-op.

REWARD (bounded and justified, Step 2 requirement)
--------------------------------------------------
  * ``-STEP_COST`` on every action (encourages short paths; bounded).
  * ``+GOAL_REWARD`` on the transition that reaches ADMIN.
No hint bonus is part of the reward — the hint's value is measured only as an
ablation (see ``agents.py`` / ``run_all.py``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import chain, combinations
from typing import Dict, FrozenSet, List, Tuple

from .grounding import N_HOSTS, foothold_probs, privesc_probs, recon_prob

# Access levels
NONE, USER, ADMIN = 0, 1, 2

# Reward constants (bounded, documented).
STEP_COST = 0.01
GOAL_REWARD = 1.0
DISCOUNT = 0.95

State = Tuple[int, int, FrozenSet[int]]

# Action set
ACTIONS: List[str] = ["recon", "exploit"] + [f"move_{i}" for i in range(N_HOSTS)]


def state_key(s: State) -> str:
    """Canonical stable string key for a state (see module docstring).

    The simulator uses a 3-tuple (access, position, discovered). The live defender-aware
    environment appends a 4th element: the set of hosts the agent has OBSERVED as blocked
    (rate-limited / locked out). When present it is encoded as a `|b...` suffix, so the
    simulator's keys are byte-for-byte unchanged and value iteration is unaffected.
    """
    access, position, discovered = s[0], s[1], s[2]
    disc = ",".join(str(i) for i in sorted(discovered)) if discovered else "-"
    key = f"a{access}|p{position}|d{disc}"
    if len(s) > 3 and s[3]:
        key += "|b" + ",".join(str(i) for i in sorted(s[3]))
    return key


def initial_state() -> State:
    return (NONE, 0, frozenset())


def is_terminal(s: State) -> bool:
    return s[0] == ADMIN


def _powerset(items) -> List[FrozenSet[int]]:
    items = list(items)
    return [frozenset(c) for c in chain.from_iterable(combinations(items, r) for r in range(len(items) + 1))]


def all_states() -> List[State]:
    """Enumerate every reachable-or-not state (finite)."""
    states: List[State] = []
    for access in (NONE, USER, ADMIN):
        for position in range(N_HOSTS):
            for discovered in _powerset(range(N_HOSTS)):
                states.append((access, position, discovered))
    return states


class AttackMDP:
    """Explicit transition kernel + a sampling simulator over the same kernel."""

    def __init__(self):
        self.foothold = foothold_probs()
        self.privesc = privesc_probs()
        self.p_recon = recon_prob()
        self.actions = ACTIONS

    # --- explicit kernel used by value iteration --------------------------------
    def transitions(self, s: State, a: str) -> List[Tuple[float, State, float]]:
        """Return list of (probability, next_state, reward) for taking ``a`` in ``s``.

        Probabilities over next states sum to 1. Reward is the immediate reward for
        the transition (already includes step cost and any goal reward).
        """
        if is_terminal(s):
            return [(1.0, s, 0.0)]

        access, position, discovered = s
        base_r = -STEP_COST

        if a == "recon":
            undiscovered = sorted(set(range(N_HOSTS)) - discovered)
            if not undiscovered:
                return [(1.0, s, base_r)]
            j = undiscovered[0]
            found = (access, position, frozenset(discovered | {j}))
            return [(self.p_recon, found, base_r), (1.0 - self.p_recon, s, base_r)]

        if a.startswith("move_"):
            i = int(a.split("_")[1])
            if i in discovered:
                return [(1.0, (access, i, discovered), base_r)]
            return [(1.0, s, base_r)]  # can't move to an undiscovered host

        if a == "exploit":
            if position not in discovered:
                return [(1.0, s, base_r)]  # nothing to exploit here yet
            if access == NONE:
                p = self.foothold[position]
                succ = (USER, position, discovered)
                return [(p, succ, base_r), (1.0 - p, s, base_r)]
            if access == USER:
                p = self.privesc[position]
                succ = (ADMIN, position, discovered)
                # goal reward is paid on the transition into ADMIN
                return [(p, succ, base_r + GOAL_REWARD), (1.0 - p, s, base_r)]
            return [(1.0, s, base_r)]

        raise ValueError(f"unknown action {a}")

    # --- sampling simulator for the learning/eval loops -------------------------
    def reset(self) -> State:
        return initial_state()

    def step(self, s: State, a: str, rng: random.Random) -> Tuple[State, float, bool]:
        outcomes = self.transitions(s, a)
        r = rng.random()
        cum = 0.0
        for p, ns, rew in outcomes:
            cum += p
            if r <= cum:
                return ns, rew, is_terminal(ns)
        # numerical fallback
        p, ns, rew = outcomes[-1]
        return ns, rew, is_terminal(ns)


if __name__ == "__main__":
    mdp = AttackMDP()
    print(f"states={len(all_states())}  actions={ACTIONS}")
    print("initial:", state_key(initial_state()))
