"""Rollouts, training loop, and statistics for the evaluation harness."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .mdp import ADMIN, DISCOUNT, AttackMDP, State, is_terminal


def run_episode(mdp: AttackMDP, agent, rng: random.Random, max_steps: int,
                learn: bool) -> Tuple[bool, int, float]:
    """Return (won, steps, discounted_return) for one episode."""
    s = mdp.reset()
    total, disc = 0.0, 1.0
    steps = 0
    for steps in range(1, max_steps + 1):
        a = agent.act(s)
        ns, r, done = mdp.step(s, a, rng)
        if learn:
            agent.observe(s, a, r, ns, done)
        total += disc * r
        disc *= DISCOUNT
        s = ns
        if done:
            return (s[0] == ADMIN), steps, total
    return (s[0] == ADMIN), steps, total


def evaluate(mdp: AttackMDP, agent, rng: random.Random, n_eval: int,
             max_steps: int) -> Dict[str, float]:
    wins, steps_to_admin, returns = 0, [], []
    for _ in range(n_eval):
        won, steps, ret = run_episode(mdp, agent, rng, max_steps, learn=False)
        returns.append(ret)
        if won:
            wins += 1
            steps_to_admin.append(steps)
    return {
        "win_rate": wins / n_eval,
        "mean_steps_to_admin": (sum(steps_to_admin) / len(steps_to_admin)) if steps_to_admin else float("nan"),
        "mean_return": sum(returns) / len(returns),
    }


def train_and_track(mdp: AttackMDP, agent, rng: random.Random, n_train: int,
                    max_steps: int, eval_every: int, n_eval_snapshot: int,
                    win_threshold: float) -> Tuple[List[int], List[float], float]:
    """Train, snapshotting greedy win-rate every ``eval_every`` episodes.

    Returns (episodes, win_rates, episodes_to_threshold). ``episodes_to_threshold``
    is the first snapshot episode whose greedy win-rate >= ``win_threshold``
    (NaN if never reached) — the sample-efficiency metric.
    """
    episodes, win_rates = [], []
    reached = float("nan")
    for ep in range(1, n_train + 1):
        run_episode(mdp, agent, rng, max_steps, learn=True)
        agent.end_episode()
        if ep % eval_every == 0:
            # snapshot with a temporary greedy view without disturbing training state
            saved_eps, saved_bolt, saved_hint = agent.epsilon, agent.use_boltzmann, agent.use_hint
            agent.epsilon, agent.use_boltzmann, agent.use_hint = 0.0, False, False
            wr = evaluate(mdp, agent, rng, n_eval_snapshot, max_steps)["win_rate"]
            agent.epsilon, agent.use_boltzmann, agent.use_hint = saved_eps, saved_bolt, saved_hint
            episodes.append(ep)
            win_rates.append(wr)
            if math.isnan(reached) and wr >= win_threshold:
                reached = ep
    return episodes, win_rates, reached


def mean_ci(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    """Return (mean, half-width of the confidence interval) using the t-distribution."""
    vals = [v for v in values if not math.isnan(v)]
    n = len(vals)
    if n == 0:
        return float("nan"), float("nan")
    mean = sum(vals) / n
    if n == 1:
        return mean, float("nan")
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    se = math.sqrt(var / n)
    try:
        from scipy import stats
        t = stats.t.ppf(0.5 + confidence / 2.0, df=n - 1)
    except Exception:
        t = 1.96  # normal approximation fallback
    return mean, t * se
