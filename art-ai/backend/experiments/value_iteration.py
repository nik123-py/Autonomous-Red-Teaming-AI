"""Exact value iteration for the tabular attack MDP.

Since ``AttackMDP.transitions`` gives the full kernel, this computes the optimal
state-value V*, action-value Q*, and greedy policy pi* exactly. V*(initial_state)
is the best achievable expected discounted return — the ceiling every learning
agent is compared to, and the quantity used to compute *regret*.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .mdp import ACTIONS, DISCOUNT, AttackMDP, State, all_states, is_terminal, state_key


def value_iteration(mdp: AttackMDP, theta: float = 1e-10, max_iter: int = 100_000):
    """Return (V, Q, policy) keyed by state tuple / (state, action)."""
    states = all_states()
    V: Dict[State, float] = {s: 0.0 for s in states}

    for _ in range(max_iter):
        delta = 0.0
        for s in states:
            if is_terminal(s):
                continue
            best = float("-inf")
            for a in ACTIONS:
                q = sum(p * (r + DISCOUNT * V[ns]) for p, ns, r in mdp.transitions(s, a))
                if q > best:
                    best = q
            delta = max(delta, abs(best - V[s]))
            V[s] = best
        if delta < theta:
            break

    Q: Dict[Tuple[State, str], float] = {}
    policy: Dict[State, str] = {}
    for s in states:
        if is_terminal(s):
            continue
        best_a, best_q = None, float("-inf")
        for a in ACTIONS:
            q = sum(p * (r + DISCOUNT * V[ns]) for p, ns, r in mdp.transitions(s, a))
            Q[(s, a)] = q
            if q > best_q:
                best_q, best_a = q, a
        policy[s] = best_a
    return V, Q, policy


if __name__ == "__main__":
    from .mdp import initial_state

    mdp = AttackMDP()
    V, Q, pi = value_iteration(mdp)
    s0 = initial_state()
    print(f"V*(initial) = {V[s0]:.4f}")
    print("Optimal action from the initial state:", pi[s0])
    print("\nOptimal policy trace from the initial state (greedy, most-likely outcome):")
    s = s0
    for _ in range(12):
        a = pi[s]
        # take the most probable successor for display
        outs = max(mdp.transitions(s, a), key=lambda t: t[0])
        print(f"  {state_key(s):20s} -> {a:8s} -> {state_key(outs[1])}")
        s = outs[1]
        if is_terminal(s):
            print("  reached ADMIN")
            break
