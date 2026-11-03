"""Agents for the attack MDP: baselines and a corrected tabular Q-learner.

Baselines
---------
* ``RandomAgent``          — uniform over the action set.
* ``GreedyBySignalAgent``  — non-learning heuristic that follows the grounded
  CVSS/EPSS signal (the "greedy-by-CVSS" baseline).

Learner
-------
* ``TabularQAgent`` — Q-learning with independently toggleable techniques so each
  can be ablated: ``use_double_q``, ``use_replay``, ``use_boltzmann`` (vs
  epsilon-greedy), and ``use_hint``. The hint is a *behaviour prior* that biases
  exploration toward the grounded-signal action; it is NEVER added to the reward,
  so it can change sample efficiency but not the fixed-point policy value.

Why this fixes the original degenerate loop
-------------------------------------------
1. The state now carries (access, position, discovered), so a no-op transition
   keeps ``next_state == state`` only when nothing actually changed, and the MDP
   makes non-progressing ``exploit``/``move`` cost a step with no positive reward
   — there is no positive self-loop to over-reinforce.
2. Rewards are bounded (step cost + terminal goal) with no hint bonus, so the
   objective is exactly "reach ADMIN quickly".
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from .grounding import N_HOSTS, foothold_probs, privesc_probs
from .mdp import ACTIONS, NONE, USER, State, state_key


# --------------------------------------------------------------------------------
def signal_action(s: State) -> str:
    """Grounded-signal heuristic action (shared by the greedy baseline & the hint).

    This deliberately ignores any defender-observation field (s[3]): the greedy baseline
    is the NON-ADAPTIVE control, so it keeps targeting the signal-best host even when the
    agent has observed that host is currently blocked. The learned agent, whose Q-table is
    keyed on the full state (including observed-blocked hosts), is what can adapt instead.
    """
    access, position, discovered = s[0], s[1], s[2]
    fp, pp = foothold_probs(), privesc_probs()
    if access == NONE:
        if not discovered:
            return "recon"
        best = max(discovered, key=lambda i: fp[i])
        return "exploit" if position == best else f"move_{best}"
    if access == USER:
        # discover all hosts, then escalate where privesc is strongest
        if len(discovered) < N_HOSTS:
            return "recon"
        best = max(discovered, key=lambda i: pp[i])
        return "exploit" if position == best else f"move_{best}"
    return "recon"


class RandomAgent:
    name = "random"

    def __init__(self, rng: random.Random):
        self.rng = rng

    def act(self, s: State) -> str:
        return self.rng.choice(ACTIONS)

    # no learning
    def observe(self, *args, **kwargs):
        pass

    def end_episode(self):
        pass


class GreedyBySignalAgent:
    name = "greedy_by_signal"

    def __init__(self, rng: random.Random):
        self.rng = rng

    def act(self, s: State) -> str:
        return signal_action(s)

    def observe(self, *args, **kwargs):
        pass

    def end_episode(self):
        pass


class TabularQAgent:
    name = "q_learning"

    def __init__(
        self,
        rng: random.Random,
        learning_rate: float = 0.2,
        discount: float = 0.95,
        epsilon: float = 0.3,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.02,
        temperature: float = 0.5,
        use_double_q: bool = True,
        use_replay: bool = True,
        replay_capacity: int = 5000,
        batch_size: int = 32,
        use_boltzmann: bool = False,
        use_hint: bool = False,
        hint_bias: float = 0.5,
    ):
        self.rng = rng
        self.lr = learning_rate
        self.gamma = discount
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.temperature = temperature
        self.use_double_q = use_double_q
        self.use_replay = use_replay
        self.batch_size = batch_size
        self.use_boltzmann = use_boltzmann
        self.use_hint = use_hint
        self.hint_bias = hint_bias

        self.qa: Dict[str, Dict[str, float]] = {}
        self.qb: Dict[str, Dict[str, float]] = {}  # second table for double-Q
        self.replay: Deque[Tuple[State, str, float, State, bool]] = deque(maxlen=replay_capacity)

    # --- Q access helpers -------------------------------------------------------
    @staticmethod
    def _get(table: Dict[str, Dict[str, float]], k: str, a: str) -> float:
        return table.get(k, {}).get(a, 0.0)

    @staticmethod
    def _set(table: Dict[str, Dict[str, float]], k: str, a: str, v: float):
        table.setdefault(k, {})[a] = v

    def _combined(self, k: str, a: str) -> float:
        if self.use_double_q:
            return 0.5 * (self._get(self.qa, k, a) + self._get(self.qb, k, a))
        return self._get(self.qa, k, a)

    # --- action selection -------------------------------------------------------
    def act(self, s: State) -> str:
        k = state_key(s)
        # hint: with prob hint_bias, when we would otherwise explore, steer toward
        # the grounded-signal action instead of a uniform random one.
        explore = self.rng.random() < self.epsilon
        if self.use_boltzmann and not explore:
            return self._boltzmann(k)
        if explore:
            if self.use_hint and self.rng.random() < self.hint_bias:
                return signal_action(s)
            return self.rng.choice(ACTIONS)
        return self._greedy(k)

    def _greedy(self, k: str) -> str:
        vals = [(a, self._combined(k, a)) for a in ACTIONS]
        best = max(v for _, v in vals)
        best_actions = [a for a, v in vals if v == best]
        return self.rng.choice(best_actions)

    def _boltzmann(self, k: str) -> str:
        t = max(self.temperature, 0.05)
        vals = {a: self._combined(k, a) / t for a in ACTIONS}
        m = max(vals.values())
        exps = {a: math.exp(v - m) for a, v in vals.items()}
        tot = sum(exps.values())
        r, cum = self.rng.random(), 0.0
        for a, e in exps.items():
            cum += e / tot
            if r <= cum:
                return a
        return ACTIONS[-1]

    # --- learning ---------------------------------------------------------------
    def observe(self, s: State, a: str, r: float, ns: State, done: bool):
        if self.use_replay:
            self.replay.append((s, a, r, ns, done))
            if len(self.replay) >= self.batch_size:
                for exp in self.rng.sample(self.replay, self.batch_size):
                    self._update(*exp)
        else:
            self._update(s, a, r, ns, done)

    def _update(self, s: State, a: str, r: float, ns: State, done: bool):
        k, nk = state_key(s), state_key(ns)
        if self.use_double_q:
            # randomly update one table using the other for the bootstrap value
            if self.rng.random() < 0.5:
                upd, oth = self.qa, self.qb
            else:
                upd, oth = self.qb, self.qa
            if done:
                target = r
            else:
                best_a = max(ACTIONS, key=lambda x: self._get(upd, nk, x))
                target = r + self.gamma * self._get(oth, nk, best_a)
            cur = self._get(upd, k, a)
            self._set(upd, k, a, cur + self.lr * (target - cur))
        else:
            if done:
                target = r
            else:
                target = r + self.gamma * max(self._get(self.qa, nk, x) for x in ACTIONS)
            cur = self._get(self.qa, k, a)
            self._set(self.qa, k, a, cur + self.lr * (target - cur))

    def end_episode(self):
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        if self.use_boltzmann:
            self.temperature = max(0.05, self.temperature * 0.999)

    def q_table_size(self) -> int:
        return sum(len(v) for v in self.qa.values())

    def freeze(self):
        """Switch to (near-)greedy for evaluation."""
        self.epsilon = 0.0
        self.use_boltzmann = False
        self.use_hint = False
