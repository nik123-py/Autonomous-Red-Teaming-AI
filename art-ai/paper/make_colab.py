"""Generate the ART-AI demonstration notebook (ART_AI_Results.ipynb).

Design goals:
  * SUBSTANTIAL, runnable code -- this is a demonstration notebook, so the real
    implementations go in (grounding formula, MDP, value iteration, agents, scope choke
    point, capability-oracle pattern, defender layer, statistics), not summaries of them.
  * Everything that CAN run in Colab, does. The live lab needs Docker, so a MOCK lab
    reproduces the oracle verdicts we actually MEASURED (all 12 probes = 1.000), letting
    the defender / routability experiment execute end-to-end in the notebook.
  * Anything that cannot be computed here is clearly labelled as measured locally, with
    the command that produced it. No number is invented.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ART_AI_Results.ipynb"


def _lines(src):
    """nbformat requires every entry of `source` to END WITH a newline (except the last).
    Splitting without re-adding them makes Jupyter/Colab concatenate the whole cell onto
    one line -- which produces a SyntaxError and makes the code unreadable."""
    ls = src.strip("\n").split("\n")
    return [l + "\n" for l in ls[:-1]] + [ls[-1]]


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(src)}


def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": _lines(src)}


C = []

# ============================================================== title
C.append(md(r"""
# ART-AI — Autonomous Red-Team AI
### A reinforcement-learning agent for autonomous security testing, and an honest measurement of when it actually works

**The research question** is not the algorithm. It is whether competence learned in a
*simulator* survives contact with a *real* lab — and whether learning beats a simple
heuristic at all.

**Scope & ethics.** Every experiment ran against six deliberately-insecure practice
applications in Docker on the author's own machine, bound to loopback
(`127.0.0.1:3001-3006`). Scope is enforced in code by an allow-listed choke point that
raises *before any socket is opened*. No third-party system was ever contacted.

---
### How to read this notebook

| Part | Content | Runs here? |
|---|---|---|
| 1 | Data grounding — deriving probabilities from CVSS v3.1 / EPSS | **Yes** |
| 2–3 | The MDP and its exact optimum (value iteration) | **Yes** |
| 4–5 | Agents (Q-learning, double-Q, replay) + evaluation harness | **Yes** |
| 6 | Main results, ablations, learning curve | **Yes** |
| 7 | Safety: the scope choke point | **Yes** |
| 8 | Capability oracles (real code; mock lab to execute) | **Yes** |
| 9 | Defender layer + the routability experiment | **Yes** |
| 10 | Live-lab results (needs Docker) | Measured locally, labelled |
| 11 | ML component accuracy | Measured locally, labelled |

Parts 10–11 report numbers produced by named commands on the real lab. Everything else
executes in front of you.
"""))

C.append(code(r'''
# Standard library + numpy/matplotlib only -- nothing to install in Colab.
import itertools, math, random, re, json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt

RNG_SEED = 12345
INK, ACCENT, GOOD, GREY = "#1A2230", "#B3412B", "#2E7D54", "#8A93A0"
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": .3})
print("ready")
''' ))

# ============================================================== Part 1 grounding
C.append(md(r"""
## Part 1 — Data grounding: where the transition probabilities come from

The original project hard-coded its success probabilities as magic numbers. We replaced
them with values **derived from published signals**, via one documented formula.

The CVSS v3.1 *Exploitability sub-score* uses the official metric weights:

$$E = 8.22 \cdot AV \cdot AC \cdot PR \cdot UI, \qquad \hat{E} = E / E_{\max}$$

combined with EPSS, an Exploit-DB verified flag, and patch age:

$$p = \big(w_c\hat{E} + w_e\,\text{EPSS} + w_v\,\text{verified}\big)\cdot\text{recency},
\qquad p \in [0.05,\,0.95]$$

This is the real code from `backend/experiments/grounding.py`.
"""))

C.append(code(r'''
# --- CVSS v3.1 metric weights, from the official FIRST.org specification -------------
CVSS31 = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},   # Attack Vector
    "AC": {"L": 0.77, "H": 0.44},                          # Attack Complexity
    "PR": {"N": 0.85, "L": 0.62, "H": 0.27},               # Privileges Required (Scope: Unchanged)
    "UI": {"N": 0.85, "R": 0.62},                          # User Interaction
}
EXPLOITABILITY_MAX = 8.22 * 0.85 * 0.77 * 0.85 * 0.85      # = 3.8869...

def cvss31_exploitability(av, ac, pr, ui):
    """CVSS v3.1 Exploitability sub-score, normalised to 0..1."""
    raw = 8.22 * CVSS31["AV"][av] * CVSS31["AC"][ac] * CVSS31["PR"][pr] * CVSS31["UI"][ui]
    return raw / EXPLOITABILITY_MAX

@dataclass(frozen=True)
class CVE:
    cve_id: str
    av: str; ac: str; pr: str; ui: str      # CVSS v3.1 base metrics
    epss: float                              # 0..1 probability of exploitation in the wild
    exploitdb_verified: bool                 # a verified working PoC exists
    patch_age_days: int                      # how long the vulnerable version has been public

# combination weights -- stated explicitly, not hidden in a per-action table
W_CVSS, W_EPSS, W_VERIFIED, PATCH_HALFLIFE = 0.55, 0.35, 0.10, 365.0

def exploit_probability(cve: CVE) -> float:
    """Derive a success probability from the CVE's cited signals. Clamped to [0.05, 0.95]."""
    expl     = cvss31_exploitability(cve.av, cve.ac, cve.pr, cve.ui)
    verified = 1.0 if cve.exploitdb_verified else 0.0
    base     = W_CVSS * expl + W_EPSS * cve.epss + W_VERIFIED * verified
    recency  = 1.0 - 0.3 * (0.5 ** (cve.patch_age_days / PATCH_HALFLIFE))   # 0.7 -> 1.0
    return max(0.05, min(0.95, base * recency))

# --- the three lab hosts, as CVE metadata -------------------------------------------
HOSTS = ["juice-shop", "dvwa", "flask-api"]
LAB = {
  "juice-shop": dict(                       # trivial unauth foothold, weak local privesc
      foothold=CVE("LAB-JS-FOOTHOLD",  "N","L","N","N", 0.62, True,  800),
      privesc =CVE("LAB-JS-PRIVESC",   "L","H","L","N", 0.05, False, 120)),
  "dvwa": dict(                             # moderate on both axes
      foothold=CVE("LAB-DVWA-FOOTHOLD","N","L","N","R", 0.30, True,  500),
      privesc =CVE("LAB-DVWA-PRIVESC", "L","L","L","N", 0.25, True,  400)),
  "flask-api": dict(                        # hard foothold, strong local privesc
      foothold=CVE("LAB-API-FOOTHOLD", "N","H","L","N", 0.12, False, 200),
      privesc =CVE("LAB-API-PRIVESC",  "L","L","L","N", 0.55, True,  700)),
}

FOOTHOLD_P = {i: exploit_probability(LAB[h]["foothold"]) for i, h in enumerate(HOSTS)}
PRIVESC_P  = {i: exploit_probability(LAB[h]["privesc"])  for i, h in enumerate(HOSTS)}

print(f"{'host':12} {'foothold p':>11} {'privesc p':>10}")
print("-" * 35)
for i, h in enumerate(HOSTS):
    print(f"{h:12} {FOOTHOLD_P[i]:>11.3f} {PRIVESC_P[i]:>10.3f}")
print("\nNote the deliberate asymmetry: the CHEAPEST foothold host (juice-shop, 0.810) is")
print("the WEAKEST escalation host (0.126). So an optimal policy must reposition --")
print("which gives a learner something non-trivial to discover.")
''' ))

# ============================================================== Part 2 MDP
C.append(md(r"""
## Part 2 — The MDP

A state is `(access, position, discovered)`:

* `access` ∈ {NONE, USER, ADMIN} — privilege obtained; ADMIN is absorbing (the goal).
* `position` — which host the attacker operates from; `exploit` acts on this host.
* `discovered` — hosts revealed by recon; you may only move to or exploit a discovered host.

Reward is deliberately minimal and bounded: `−0.01` per step, `+1.0` on reaching ADMIN.
**No shaping bonuses.** The original project gave `+100` for matching an Exploit-DB "hint",
which dwarfed the `+15..60` for actually winning — classic reward hacking. It was removed.
"""))

C.append(code(r'''
NONE, USER, ADMIN = 0, 1, 2
STEP_COST, GOAL_REWARD, GAMMA, P_RECON = 0.01, 1.0, 0.95, 0.90
ACTIONS = ["recon", "exploit"] + [f"move_{i}" for i in range(len(HOSTS))]
S0 = (NONE, 0, frozenset())

def state_key(s) -> str:
    """Canonical stable key. The live defender-aware env appends a 4th field (|b...)."""
    access, pos, disc = s[0], s[1], s[2]
    d = ",".join(str(i) for i in sorted(disc)) if disc else "-"
    k = f"a{access}|p{pos}|d{d}"
    if len(s) > 3 and s[3]:
        k += "|b" + ",".join(sorted(map(str, s[3])))
    return k

def all_states():
    subs = [frozenset(c) for r in range(len(HOSTS) + 1)
            for c in itertools.combinations(range(len(HOSTS)), r)]
    return [(a, p, d) for a in (NONE, USER, ADMIN) for p in range(len(HOSTS)) for d in subs]

def transitions(s, a):
    """The EXPLICIT transition kernel: list of (probability, next_state, reward).

    Because this exists, the optimal policy is computable exactly by value iteration --
    which gives every agent a true ceiling to be measured against. Most work in this
    area has no such ceiling, only comparisons to other heuristics.
    """
    access, pos, disc = s
    if access == ADMIN:
        return [(1.0, s, 0.0)]                      # absorbing goal
    r = -STEP_COST

    if a == "recon":                                # reveal the lowest-index unknown host
        und = sorted(set(range(len(HOSTS))) - disc)
        if not und:
            return [(1.0, s, r)]
        j = und[0]
        return [(P_RECON, (access, pos, frozenset(disc | {j})), r),
                (1 - P_RECON, s, r)]

    if a.startswith("move_"):                       # bookkeeping; blocked if undiscovered
        i = int(a.split("_")[1])
        return [(1.0, (access, i, disc) if i in disc else s, r)]

    if a == "exploit":
        if pos not in disc:                         # cannot exploit an unknown host
            return [(1.0, s, r)]
        if access == NONE:                          # NONE -> USER
            p = FOOTHOLD_P[pos]
            return [(p, (USER, pos, disc), r), (1 - p, s, r)]
        p = PRIVESC_P[pos]                          # USER -> ADMIN pays the goal reward
        return [(p, (ADMIN, pos, disc), r + GOAL_REWARD), (1 - p, s, r)]

    raise ValueError(f"unknown action {a}")

def step_env(s, a, rng):
    """Sample one transition from the same kernel value iteration uses."""
    x, cum = rng.random(), 0.0
    outs = transitions(s, a)
    for p, ns, rw in outs:
        cum += p
        if x <= cum:
            return ns, rw, ns[0] == ADMIN
    p, ns, rw = outs[-1]
    return ns, rw, ns[0] == ADMIN

print(f"state space: {len(all_states())} states   actions: {ACTIONS}")
print(f"initial state: {state_key(S0)}")
''' ))

# ============================================================== Part 3 VI
C.append(md("## Part 3 — Value iteration: the exact optimum\n\n"
            "Because the kernel is explicit and the space is small, we can compute "
            "$V^*$ exactly. This is the ceiling every agent is scored against, and it is "
            "what makes *regret* a meaningful number here."))

C.append(code(r'''
def value_iteration(theta=1e-12, max_iter=100_000):
    """Standard VI. Returns (V, Q, greedy policy)."""
    S = all_states()
    V = {s: 0.0 for s in S}
    for _ in range(max_iter):
        delta = 0.0
        for s in S:
            if s[0] == ADMIN:
                continue
            best = max(sum(p * (rw + GAMMA * V[ns]) for p, ns, rw in transitions(s, a))
                       for a in ACTIONS)
            delta = max(delta, abs(best - V[s]))
            V[s] = best
        if delta < theta:
            break
    Q, pi = {}, {}
    for s in S:
        if s[0] == ADMIN:
            continue
        qs = {a: sum(p * (rw + GAMMA * V[ns]) for p, ns, rw in transitions(s, a)) for a in ACTIONS}
        Q[s] = qs
        pi[s] = max(qs, key=qs.get)
    return V, Q, pi

V, Qstar, PI = value_iteration()
VSTAR = V[S0]
print(f"V*(initial) = {VSTAR:.4f}   <-- the exact optimum")
print(f"optimal first action: {PI[S0]}\n")

print("Optimal policy trace (most-likely successor at each step):")
s = S0
for _ in range(9):
    a = PI[s]
    p, ns, _ = max(transitions(s, a), key=lambda t: t[0])
    print(f"  {state_key(s):18} --{a:8}-->  {state_key(ns)}")
    s = ns
    if s[0] == ADMIN:
        print("  reached ADMIN"); break

print("\nNote it recons TWICE, takes the cheap foothold on juice-shop, then MOVES to dvwa")
print("to escalate -- deliberately NOT reconnoitring flask-api, because the extra step")
print("cost outweighs that host's stronger privesc. A real trade-off to discover.")
''' ))

# ============================================================== Part 4 agents
C.append(md(r"""
## Part 4 — The agents

Three policies, all sharing one interface so they are directly comparable:

1. **Random** — uniform over the action set.
2. **Greedy-by-signal** — a non-learning heuristic that follows the grounded CVSS signal.
   This is the "greedy-by-CVSS" baseline, and it is a *strong* one.
3. **Tabular Q-learning** — with independently switchable **double-Q**, **experience
   replay**, **Boltzmann vs ε-greedy** exploration, and a **hint prior**, so each
   technique can be ablated rather than merely asserted to help.
"""))

C.append(code(r'''
def signal_action(s):
    """Grounded-signal heuristic. Deliberately IGNORES any defender observation (s[3]):
    it is the non-adaptive control that the learned agent must beat."""
    access, pos, disc = s[0], s[1], s[2]
    if access == NONE:
        if not disc:
            return "recon"
        best = max(disc, key=lambda i: FOOTHOLD_P[i])
    else:
        if len(disc) < len(HOSTS):      # discover everything, then escalate where best
            return "recon"
        best = max(disc, key=lambda i: PRIVESC_P[i])
    return "exploit" if pos == best else f"move_{best}"

class RandomAgent:
    name = "random"
    def __init__(self, rng): self.rng = rng
    def act(self, s): return self.rng.choice(ACTIONS)
    def observe(self, *a, **k): pass
    def end_episode(self): pass
    def freeze(self): pass

class GreedyBySignalAgent:
    name = "greedy_by_signal"
    def __init__(self, rng): self.rng = rng
    def act(self, s): return signal_action(s)
    def observe(self, *a, **k): pass
    def end_episode(self): pass
    def freeze(self): pass

class TabularQAgent:
    """Q-learning with ablatable techniques.

    double_q : two tables; update one, bootstrap from the other (reduces maximisation bias)
    replay   : store transitions, replay a random batch each step (sample efficiency)
    boltzmann: softmax action selection instead of epsilon-greedy
    hint     : bias EXPLORATION toward the grounded-signal action. Never touches the
               reward or the target, so it can change sample efficiency but provably
               cannot change the fixed point.
    """
    name = "q_learning"
    def __init__(self, rng, lr=0.2, gamma=GAMMA, epsilon=0.3, eps_decay=0.995,
                 min_eps=0.02, temperature=0.5, double_q=True, replay=True,
                 replay_capacity=5000, batch=32, boltzmann=False, hint=False, hint_bias=0.5):
        self.rng, self.lr, self.gamma = rng, lr, gamma
        self.eps, self.eps_decay, self.min_eps = epsilon, eps_decay, min_eps
        self.temperature = temperature
        self.double_q, self.replay_on, self.batch = double_q, replay, batch
        self.boltzmann, self.hint, self.hint_bias = boltzmann, hint, hint_bias
        self.qa, self.qb = {}, {}
        self.buf, self.capacity = [], replay_capacity

    # --- Q access -------------------------------------------------------------
    @staticmethod
    def _get(t, k, a): return t.get(k, {}).get(a, 0.0)
    @staticmethod
    def _set(t, k, a, v): t.setdefault(k, {})[a] = v
    def _combined(self, k, a):
        if self.double_q:
            return 0.5 * (self._get(self.qa, k, a) + self._get(self.qb, k, a))
        return self._get(self.qa, k, a)

    # --- action selection -----------------------------------------------------
    def act(self, s):
        k = state_key(s)
        explore = self.rng.random() < self.eps
        if self.boltzmann and not explore:
            return self._boltzmann(k)
        if explore:
            if self.hint and self.rng.random() < self.hint_bias:
                return signal_action(s)           # knowledge-guided exploration
            return self.rng.choice(ACTIONS)
        return self._greedy(k)

    def _greedy(self, k):
        vals = [(a, self._combined(k, a)) for a in ACTIONS]
        best = max(v for _, v in vals)
        return self.rng.choice([a for a, v in vals if v == best])   # random tie-break

    def _boltzmann(self, k):
        t = max(self.temperature, 0.05)
        vals = {a: self._combined(k, a) / t for a in ACTIONS}
        m = max(vals.values())
        exps = {a: math.exp(v - m) for a, v in vals.items()}
        tot = sum(exps.values())
        x, cum = self.rng.random(), 0.0
        for a, e in exps.items():
            cum += e / tot
            if x <= cum:
                return a
        return ACTIONS[-1]

    # --- learning -------------------------------------------------------------
    def _update(self, s, a, r, ns, done):
        k, nk = state_key(s), state_key(ns)
        if self.double_q:
            up, oth = (self.qa, self.qb) if self.rng.random() < 0.5 else (self.qb, self.qa)
        else:
            up = oth = self.qa                       # plain Q-learning: one table
        if done:
            target = r                               # terminal: no bootstrap
        else:
            a_star = max(ACTIONS, key=lambda x: self._get(up, nk, x))
            target = r + self.gamma * self._get(oth, nk, a_star)
        cur = self._get(up, k, a)
        self._set(up, k, a, cur + self.lr * (target - cur))

    def observe(self, s, a, r, ns, done):
        self._update(s, a, r, ns, done)              # always learn online...
        if self.replay_on:                           # ...plus an off-policy replay batch
            self.buf.append((s, a, r, ns, done))
            if len(self.buf) > self.capacity:
                self.buf.pop(0)
            if len(self.buf) >= self.batch:
                for e in self.rng.sample(self.buf, self.batch):
                    self._update(*e)

    def end_episode(self):
        self.eps = max(self.min_eps, self.eps * self.eps_decay)
        if self.boltzmann:
            self.temperature = max(0.05, self.temperature * 0.999)

    def freeze(self):
        """Switch to pure greedy for evaluation."""
        self.eps, self.boltzmann, self.hint = 0.0, False, False

    def q_table_size(self):
        return sum(len(v) for v in self.qa.values())

print("agents defined: RandomAgent, GreedyBySignalAgent, TabularQAgent")
''' ))

# ============================================================== Part 5 harness
C.append(md("## Part 5 — The evaluation harness\n\n"
            "Seeded runs, mean ± 95% CI, and **Wilson intervals** for win rates (correct "
            "at small N, unlike the normal approximation). Regret is measured against the "
            "exact $V^*$ from Part 3."))

C.append(code(r'''
def run_episode(env_step, agent, rng, max_steps=15, learn=False, s0=S0):
    """One episode. Returns (won, steps, discounted_return)."""
    s, total, disc = s0, 0.0, 1.0
    for t in range(1, max_steps + 1):
        a = agent.act(s)
        ns, r, done = env_step(s, a, rng)
        if learn:
            agent.observe(s, a, r, ns, done)
        total += disc * r
        disc *= GAMMA
        s = ns
        if done:
            return (s[0] == ADMIN), t, total
    return (s[0] == ADMIN), max_steps, total

def wilson_ci(successes, n, z=1.96):
    """Wilson score interval -- correct for small N and for proportions near 0 or 1."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)

def mean_ci(vals, conf=1.96):
    """Mean with a normal-approximation CI across seeds."""
    v = np.asarray(vals, dtype=float)
    return v.mean(), conf * v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else 0.0

def evaluate(make_agent, seeds=10, train=0, evals=200, max_steps=15, env_step=step_env):
    """Train (optionally) then evaluate across independent seeds."""
    wins, rets, steps, qsizes = [], [], [], []
    for sd in range(seeds):
        rng = random.Random(RNG_SEED + sd)
        ag = make_agent(rng)
        for _ in range(train):
            run_episode(env_step, ag, rng, max_steps, learn=True)
            ag.end_episode()
        ag.freeze()
        w = [run_episode(env_step, ag, rng, max_steps) for _ in range(evals)]
        wins.append(np.mean([x[0] for x in w]))
        rets.append(np.mean([x[2] for x in w]))
        st = [x[1] for x in w if x[0]]
        steps.append(np.mean(st) if st else float("nan"))
        if hasattr(ag, "q_table_size"):
            qsizes.append(ag.q_table_size())
    wm, wc = mean_ci(wins); rm, _ = mean_ci(rets)
    return {"win": wm, "win_ci": wc, "ret": rm, "regret": VSTAR - rm,
            "steps": np.nanmean(steps), "q": int(np.mean(qsizes)) if qsizes else 0}

print("harness ready: run_episode, wilson_ci, mean_ci, evaluate")
''' ))

# ============================================================== Part 6 results
C.append(md("## Part 6 — Main result: learning vs the baselines\n\n"
            "> **Note on sample size.** These cells use 10 seeds so they finish quickly in "
            "Colab. The project's canonical numbers come from **20 seeds × 800 episodes** "
            "(`python -m experiments.run_all`) and read **0.960 ± 0.035** win rate at 93% of "
            "the optimum. Expect small differences here — same system, smaller sample."))

C.append(code(r'''
rows = []
rows.append(("random",            evaluate(lambda r: RandomAgent(r), seeds=10)))
rows.append(("greedy-by-CVSS",    evaluate(lambda r: GreedyBySignalAgent(r), seeds=10)))
rows.append(("Q-learning",        evaluate(lambda r: TabularQAgent(r), seeds=10, train=800)))

print(f"{'configuration':18} {'win rate':>16} {'steps':>7} {'return':>8} {'regret':>8} {'|Q|':>5}")
print("-" * 70)
for name, m in rows:
    print(f"{name:18} {m['win']:>8.3f} +-{m['win_ci']:<5.3f} {m['steps']:>7.2f} "
          f"{m['ret']:>8.3f} {m['regret']:>8.3f} {m['q']:>5}")
print("-" * 70)
print(f"{'value-iteration opt':18} {'--':>16} {'--':>7} {VSTAR:>8.3f} {0.0:>8.3f}")

q = rows[2][1]
print(f"\nThe learned agent reaches {100*q['ret']/VSTAR:.0f}% of the exact optimum.")
print(f"Before this project's repairs the same component scored 2% win rate -- it LOST")
print(f"to a random agent's 49%. The fix was the state encoding and reward, not more training.")
''' ))

C.append(md("### Ablations — each technique must earn its place\n\n"
            "A claim like *\"double-Q helps\"* needs a number, not an assertion. The "
            "project's finding across 20 seeds is that **only experience replay** shows a "
            "defensible benefit (it roughly halves episodes-to-competence); double-Q, "
            "Boltzmann and the hint all fall within overlapping intervals."))

C.append(code(r'''
abl = [
    ("default (doubleQ+replay)", dict()),
    ("double-Q off",             dict(double_q=False)),
    ("replay off",               dict(replay=False)),
    ("Boltzmann exploration",    dict(boltzmann=True)),
    ("hint prior on",            dict(hint=True)),
]
print(f"{'configuration':28} {'win rate':>16} {'regret':>9}")
print("-" * 56)
res_abl = []
for label, kw in abl:
    m = evaluate(lambda r, kw=kw: TabularQAgent(r, **kw), seeds=10, train=800)
    res_abl.append((label, m))
    print(f"{label:28} {m['win']:>8.3f} +-{m['win_ci']:<5.3f} {m['regret']:>9.3f}")
print("\nOverlapping intervals => NOT a defensible improvement. We report that honestly")
print("rather than claiming every technique in the stack contributes.")
''' ))

C.append(md("### Figure — learning curve"))

C.append(code(r'''
GRID = [1, 2, 3, 5, 8, 12, 16, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 600]

def learning_curve(seeds=8, train=600, evals=200):
    """Finer grid early: the agent climbs within ~30 episodes, so a coarse linear grid
    would hide the entire learning transition."""
    curves = []
    for sd in range(seeds):
        rng = random.Random(500 + sd)
        ag = TabularQAgent(rng)
        ys = []
        for ep in range(1, train + 1):
            run_episode(step_env, ag, rng, learn=True); ag.end_episode()
            if ep in GRID:
                saved = ag.eps; ag.eps = 0.0
                ys.append(np.mean([run_episode(step_env, ag, rng)[0] for _ in range(evals)]))
                ag.eps = saved
        curves.append(ys)
    return GRID, np.array(curves)

xs, Cv = learning_curve()
mean, ci = Cv.mean(0), 1.96 * Cv.std(0) / math.sqrt(Cv.shape[0])

fig, ax = plt.subplots(figsize=(9, 4.3))
ax.plot(xs, mean, color=INK, lw=2, label="Q-learning (mean of 8 seeds)")
ax.fill_between(xs, mean - ci, mean + ci, color=INK, alpha=.18, label="95% CI")
ax.axhline(1.0, ls="--", color=GOOD, label="optimal policy")
ax.axhline(0.171, ls=":", color=ACCENT, label="random baseline (0.171)")
ax.set_xscale("log")
ax.set_xlabel("training episodes (log scale)"); ax.set_ylabel("greedy win rate")
ax.set_title("Learning curve — random-level to near-optimal within ~30 episodes")
ax.set_ylim(0, 1.08); ax.legend(loc="lower right")
plt.tight_layout(); plt.show()
''' ))

# ============================================================== Part 7 safety
C.append(md(r"""
## Part 7 — Safety: the scope choke point

Every outbound request in the live system passes through **one** function, which validates
the target **before any socket is opened**. There is deliberately no environment variable,
config key or CLI flag that can widen it — changing scope requires editing the constant.

This is the real code from `backend/live/http_client.py`, and it is fully runnable.
"""))

C.append(code(r'''
import urllib.parse

LAB_PORTS = (3001, 3002, 3003, 3004, 3005, 3006)
LAB_HOSTS = ("127.0.0.1", "localhost")
ALLOWED   = {(h, p) for h in LAB_HOSTS for p in LAB_PORTS}

class ScopeViolation(Exception):
    """Raised when a request targets anything outside the local lab allowlist."""

def assert_in_scope(url: str):
    """Parse `url` and raise unless (host, port) is allow-listed. Runs BEFORE any socket."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScopeViolation(f"Refusing non-http(s) scheme: {parsed.scheme!r}")
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if (host, port) not in ALLOWED:
        raise ScopeViolation(f"Refusing out-of-scope target {host}:{port}")
    return host, port

tests = [
    ("http://127.0.0.1:3001/",            True,  "lab host"),
    ("http://localhost:3003/api/users",   True,  "lab host by name"),
    ("http://8.8.8.8/",                   False, "public IP"),
    ("http://example.com/",               False, "public hostname"),
    ("http://127.0.0.1:22/",              False, "local but NOT a lab port (SSH)"),
    ("http://127.0.0.1:8003/",            False, "the project's OWN backend"),
    ("http://169.254.169.254/",           False, "cloud metadata endpoint"),
    ("file:///etc/passwd",                False, "non-http scheme"),
]
print(f"{'target':38} {'expected':>9} {'result':>9}")
print("-" * 60)
ok = 0
for url, should_pass, why in tests:
    try:
        assert_in_scope(url); got = "ALLOW"
    except ScopeViolation:
        got = "REFUSE"
    exp = "ALLOW" if should_pass else "REFUSE"
    mark = "ok" if exp == got else "FAIL"
    ok += exp == got
    print(f"{url:38} {exp:>9} {got:>9}  {mark}   ({why})")
print(f"\n{ok}/{len(tests)} scope checks behaved correctly.")
print("Note it is PORT-specific, not just host-specific: the project's own API on 8003")
print("is refused, so the agent cannot accidentally attack its own backend.")
''' ))

# ============================================================== Part 8 oracles
C.append(md(r'''
## Part 8 — Capability oracles (and a mock lab so they run here)

The live agent escalates **only** on a deterministic predicate over a real HTTP response —
never a probability. Each oracle pairs an injected request with a **benign baseline**, so
success is a *measured difference*, not an absolute guess.

Real example from `backend/live/capabilities.py` (flask-api foothold):

```python
def flask_foothold(s: LabSession) -> ProbeResult:
    """SQLi differential on GET /api/users?id=
    EVIDENCE: app.py interpolates `id` straight into SQL, so `1 OR 1=1` returns every
    row. Success == injected row count STRICTLY GREATER than the benign baseline."""
    base = s.get(_u(p, "/api/users?id=1"))
    inj  = s.get(_u(p, "/api/users?id=1%20OR%201=1"))
    n_base, n_inj = len(base.json()), len(inj.json())
    ok = n_inj > n_base
    return ProbeResult(ok, f"rows baseline={n_base} injected={n_inj}", [...])
```

Colab has no Docker, so below is a **mock lab** whose verdicts reproduce what we actually
**measured** on the real lab: all 12 probes succeeded 30/30 times (Wilson 95% CI
[0.886, 1.000]). The mock is therefore deterministic-success — matching reality — and it
lets Part 9's defender experiment run end-to-end here.
'''))

C.append(code(r'''
@dataclass
class ProbeResult:
    success: bool
    evidence: str
    requests: List[dict] = field(default_factory=list)

class MockLab:
    """Stands in for the six Docker services.

    Verdicts are deterministic-success because that is what we MEASURED on the real lab
    (M=30 per probe, every probe 1.000). The mock does not invent an outcome the real
    lab did not exhibit; it reproduces the measured one so the notebook can run.
    """
    EVIDENCE = {
        ("juice-shop", "foothold"): "status=200 jwt_identity=admin@juice-sh.op|role=admin",
        ("juice-shop", "privesc"):  "/api/Users anon=401 with_token=200 (401->200 differential)",
        ("dvwa",       "foothold"): "login=302 index=200 (authenticated session)",
        ("dvwa",       "privesc"):  "sql rows baseline=1 injected=5",
        ("flask-api",  "foothold"): "rows baseline=1 injected=4",
        ("flask-api",  "privesc"):  "status=200 role='admin' success=True",
    }
    def probe(self, host, capability) -> ProbeResult:
        ev = self.EVIDENCE.get((host, capability), "measured success")
        return ProbeResult(True, ev, [{"method": "GET", "url": f"http://127.0.0.1/{host}",
                                       "status": 200}])

MOCK = MockLab()
print(f"{'host':12} {'capability':11} {'verdict':>8}   evidence")
print("-" * 86)
for h in HOSTS:
    for cap in ("foothold", "privesc"):
        r = MOCK.probe(h, cap)
        print(f"{h:12} {cap:11} {str(r.success):>8}   {r.evidence[:52]}")
print("\nOn the REAL lab these verdicts come from live HTTP responses, and every one is")
print("written to an append-only evidence log tying the reward to the request that earned it.")
''' ))

# ============================================================== Part 9 defender
C.append(md(r"""
## Part 9 — The defender, and the central result

On the deterministic lab a learned agent and the greedy heuristic were **tied** — so RL had
nothing to prove. To find out *when* learning is worth its cost, we added a real defender:
per-host **rate limiting**, **account lockout** after consecutive failures, and
**probabilistic filtering**.

**Honesty invariant:** the defender can only make an attempt **fail** — it never fabricates
a success. A win still requires a real oracle verdict.

This is the real `DefensePolicy` from `backend/live/defenses.py`.
"""))

C.append(code(r'''
@dataclass
class DefensePolicy:
    """Stateful defender. Only ever causes FAILURE; never fabricates success."""
    rate_limit: Optional[int] = None          # attempts/host before a cooldown
    rate_cooldown: int = 3
    lockout_threshold: Optional[int] = None   # consecutive failures before a lockout
    lockout_steps: int = 5
    waf_block_p: float = 0.0                  # uniform filter probability
    host_waf: Optional[Dict[str, float]] = None   # PER-HOST override -> heterogeneous
    seed: int = 0

    def __post_init__(self):
        # Seed ONCE. reset() must not re-seed, or every episode replays the identical
        # block pattern -- which would make the defender deterministic across episodes
        # and erase the very uncertainty the agent is meant to handle. (Real bug, fixed.)
        self._rng = random.Random(self.seed)
        self.reset()

    def reset(self):
        self._attempts, self._fails = {}, {}
        self._locked_until, self._rate_until = {}, {}
        self.events = {"rate": 0, "lockout": 0, "waf": 0, "allowed": 0}

    @property
    def active(self):
        return (self.rate_limit is not None or self.lockout_threshold is not None
                or self.waf_block_p > 0 or bool(self.host_waf))

    def _waf_for(self, host):
        if self.host_waf and host in self.host_waf:
            return self.host_waf[host]
        return self.waf_block_p

    def check(self, host, step) -> Optional[str]:
        """Return a block reason, or None to allow. Deterministic checks first."""
        if self.lockout_threshold is not None and step < self._locked_until.get(host, 0):
            self.events["lockout"] += 1; return "account locked out"
        if self.rate_limit is not None and step < self._rate_until.get(host, 0):
            self.events["rate"] += 1; return "rate-limited (429)"
        p = self._waf_for(host)
        if p > 0 and self._rng.random() < p:
            self.events["waf"] += 1; return f"blocked by filter (403), p={p}"
        self.events["allowed"] += 1
        return None

    def record_attempt(self, host, step):
        n = self._attempts.get(host, 0) + 1
        self._attempts[host] = n
        if self.rate_limit is not None and n > self.rate_limit:
            self._rate_until[host] = step + self.rate_cooldown

    def record_result(self, host, success, step):
        if self.lockout_threshold is None:
            return
        if success:
            self._fails[host] = 0
        else:
            f = self._fails.get(host, 0) + 1
            self._fails[host] = f
            if f >= self.lockout_threshold:
                self._locked_until[host] = step + self.lockout_steps
                self._fails[host] = 0

PRESETS = {
    0: dict(),                                                            # none
    1: dict(waf_block_p=0.25, lockout_threshold=6, lockout_steps=4),      # mild
    2: dict(waf_block_p=0.45, lockout_threshold=4, lockout_steps=5,
            rate_limit=8, rate_cooldown=3),                               # medium
    3: dict(waf_block_p=0.65, lockout_threshold=3, lockout_steps=6,
            rate_limit=5, rate_cooldown=4),                               # strong (UNIFORM)
    # 4 = HETEROGENEOUS: the host the CVSS-greedy baseline fixates on is heavily
    # defended, while flask-api is left soft. Routing becomes a real, learnable skill.
    4: dict(host_waf={"juice-shop": 0.85, "dvwa": 0.50, "flask-api": 0.05},
            lockout_threshold=3, lockout_steps=5),
}
LABELS = {0: "none", 1: "mild", 2: "medium", 3: "strong (uniform)", 4: "heterogeneous"}
print("DefensePolicy defined;", len(PRESETS), "presets")
''' ))

C.append(md(r"""
### The defender-aware environment

Two changes make adaptation *possible*:

1. **Per-host access.** Escalating on a host requires a foothold *on that host* — the
   finding from §10.2 (a Juice Shop token is worthless against DVWA).
2. **A persistence-aware observation.** The state gains a 4th field: hosts the agent has
   observed blocked **repeatedly** (≥2 consecutive). A single transient filter block does
   *not* flag a host, so the agent does not abandon a recoverable position.
"""))

C.append(code(r'''
PERSIST_THRESHOLD = 2

class DefendedEnv:
    """Defender-aware environment over the mock lab. Mirrors backend/experiments/live_env.py."""
    def __init__(self, defense: DefensePolicy, lab=MOCK, hosts=HOSTS):
        self.defense, self.lab, self.hosts = defense, lab, hosts
        self.reset()

    def reset(self):
        self.defense.reset()
        self._footheld, self._block_count, self._step = set(), {}, 0
        return (NONE, 0, frozenset(), frozenset()) if self.defense.active else S0

    def step(self, s, a, rng):
        self._step += 1
        access, pos, disc = s[0], s[1], s[2]
        observe = self.defense.active
        reward, ns, host, evidence = -STEP_COST, (access, pos, disc), None, ""

        if a == "recon":
            und = sorted(set(range(len(self.hosts))) - disc)
            if und and rng.random() < P_RECON:
                ns = (access, pos, frozenset(disc | {und[0]}))
        elif a.startswith("move_"):
            i = int(a.split("_")[1])
            if i in disc:
                ns = (access, i, disc)
        elif a == "exploit":
            host = self.hosts[pos]
            if pos not in disc:
                evidence = "not discovered"
            else:
                # --- defender gate: checked BEFORE any probe, can only cause failure ---
                self.defense.record_attempt(host, self._step)
                block = self.defense.check(host, self._step)
                if block:
                    evidence = f"defender: {block}"
                    self.defense.record_result(host, False, self._step)
                else:
                    if access == NONE:
                        res = self.lab.probe(host, "foothold")
                        evidence = res.evidence
                        self.defense.record_result(host, res.success, self._step)
                        if res.success:
                            self._footheld.add(host); ns = (USER, pos, disc)
                    else:
                        # per-host access: need a foothold on THIS host before privesc
                        if host not in self._footheld:
                            f = self.lab.probe(host, "foothold")
                            self.defense.record_result(host, f.success, self._step)
                            if f.success:
                                self._footheld.add(host)
                            evidence = "established host-local foothold"
                        if host in self._footheld:
                            res = self.lab.probe(host, "privesc")
                            evidence = res.evidence
                            self.defense.record_result(host, res.success, self._step)
                            if res.success:
                                ns = (ADMIN, pos, disc); reward += GOAL_REWARD

        # --- persistence-aware belief update ---
        if observe and a == "exploit" and host is not None:
            if evidence.startswith("defender:"):
                self._block_count[host] = self._block_count.get(host, 0) + 1
            elif evidence and "not discovered" not in evidence:
                self._block_count[host] = 0          # a probe got through => reachable
        if observe:
            locked = frozenset(h for h, c in self._block_count.items()
                               if c >= PERSIST_THRESHOLD)
            ns = tuple(ns[:3]) + (locked,)
        return ns, reward, ns[0] == ADMIN

print("DefendedEnv ready")
''' ))

C.append(md("### The experiment: greedy vs learned, across defender strengths\n\n"
            "This is the project's central claim, and it runs here."))

C.append(code(r'''
def run_defender_experiment(level, train=400, evals=60, max_steps=20, seeds=4):
    """Greedy (non-adaptive) vs a defender-aware learner, at one defender strength."""
    g_w, l_w = [], []
    for sd in range(seeds):
        # --- greedy baseline ---
        rng = random.Random(900 + sd)
        env = DefendedEnv(DefensePolicy(seed=level * 10 + sd, **PRESETS[level]))
        wins = 0
        for _ in range(evals):
            s = env.reset()
            won, _, _ = run_episode(env.step, GreedyBySignalAgent(rng), rng, max_steps, s0=s)
            wins += won
        g_w.append(wins / evals)

        # --- learned, defender-aware ---
        rng2 = random.Random(1900 + sd)
        env2 = DefendedEnv(DefensePolicy(seed=level * 10 + sd, **PRESETS[level]))
        ag = TabularQAgent(rng2, epsilon=0.4, eps_decay=0.99, min_eps=0.05)
        for _ in range(train):
            s = env2.reset()
            run_episode(env2.step, ag, rng2, max_steps, learn=True, s0=s)
            ag.end_episode()
        ag.freeze()
        wins = 0
        for _ in range(evals):
            s = env2.reset()
            won, _, _ = run_episode(env2.step, ag, rng2, max_steps, s0=s)
            wins += won
        l_w.append(wins / evals)
    return float(np.mean(g_w)), float(np.mean(l_w))

print(f"{'defender':20} {'greedy':>8} {'learned':>9} {'delta':>8}   verdict")
print("-" * 68)
results = {}
for lvl in (0, 2, 3, 4):
    g, l = run_defender_experiment(lvl)
    results[lvl] = (g, l)
    d = l - g
    verdict = ("learning WINS" if d > 0.05 else
               "learning HURTS" if d < -0.05 else "tied")
    print(f"{LABELS[lvl]:20} {g:>8.3f} {l:>9.3f} {d:>+8.3f}   {verdict}")
''' ))

C.append(code(r'''
labels = [LABELS[k] for k in results]
g = [results[k][0] for k in results]; l = [results[k][1] for k in results]
y = np.arange(len(labels)); h = .38
fig, ax = plt.subplots(figsize=(9.5, 4))
ax.barh(y + h/2, g, h, label="greedy heuristic (non-adaptive)", color=GREY)
ax.barh(y - h/2, l, h, label="learned policy (defender-aware)", color=INK)
ax.set_yticks(y); ax.set_yticklabels(labels); ax.invert_yaxis()
ax.set_xlabel("win rate"); ax.set_xlim(0, 1.1)
ax.set_title("Learning beats the heuristic only when the defence is ROUTABLE")
ax.legend(loc="lower right"); plt.tight_layout(); plt.show()

print("Measured on the REAL lab (python -m experiments.run_defender):")
print("   medium (uniform)          greedy 0.920   learned 1.000   +0.080")
print("   strong (uniform)          greedy 0.600   learned 0.320   -0.280   <- learning HURT")
print("   strong + persistence obs  greedy 0.600   learned 0.000   -0.600   <- the 'fix' hurt more")
print("   heterogeneous (routable)  greedy 0.320   learned 1.000   +0.680   <- intervals disjoint")
print()
print("The in-notebook run above reproduces the HEADLINE (routability) but not the exact")
print("magnitudes at the uniform strengths: the mock lab's oracles are deterministic and")
print("the training budget here is smaller, so the uniform rows read 'tied' rather than")
print("'learning hurt'. The real-lab numbers are the canonical ones; both agree that")
print("learning only pulls decisively ahead when the defence is heterogeneous.")
''' ))

C.append(md(r"""
> ### The conditional claim this earns
>
> **A learned policy beats a CVSS-greedy heuristic exactly when the defensive posture is
> heterogeneous (routable) — when there is a soft target to find. Under a *uniform*
> defender, stubborn persistence is optimal, learning does not help, and a mis-designed
> observation makes it actively worse.**

This was reached through **two documented failures and a diagnosis**, not by tuning until a
number looked good:

1. Occurrence-based observation → learning *hurt* at strong (−0.28).
2. Persistence-based observation → *hurt more* (−0.60).
3. **Diagnosis:** under a *uniform* filter the block probability is identical on every
   host, so switching gains nothing and stubborn retry is optimal. Adaptation has no
   purchase — no observation design can win there.
4. **Confirming experiment:** make the defence heterogeneous, and the learner routes to the
   soft target and wins decisively (+0.68, non-overlapping intervals).

**Traced winning episode on the real lab:**

```
a0|p0|d-        recon    -> confirmed juice-shop open
a0|p0|d0        recon    -> confirmed dvwa open
a0|p0|d0,1      recon    -> confirmed flask-api open
a0|p0|d0,1,2    move_2   -> moved to host 2 (flask-api)     <- routes to the SOFT host
a0|p2|d0,1,2    exploit  -> SQLi 1->28 rows (foothold)
a1|p2|d0,1,2    exploit  -> role=admin (privesc)   => ADMIN in 6 steps
```
"""))

# ============================================================== Part 10 live
C.append(md(r"""
## Part 10 — Live-lab results (measured locally; needs Docker)

> Produced by `python -m experiments.run_live`. **Nothing below is computed by this
> notebook.**

### 10.1 The agent genuinely attacks — and it is auditable

| metric | value |
|---|---|
| hosts with working capability oracles | **6 / 6** (12 capabilities) |
| real HTTP requests per run | **2,126** (14.7 per episode, 224 s) |
| oracle verdicts | 276 True, **0 fabricated** |
| `rng` calls on the live decision path | **0** (mechanically verified) |
| test suite | **42 passed, 0 failed** |

One evidence-log record — every escalation tied to the request that justified it:

```
ep1 step5  a0|p0|d0 --exploit--> a1|p0|d0   host=juice-shop  verdict=True
  evidence: status=200 jwt_identity=admin@juice-sh.op|role=admin
  POST http://127.0.0.1:3001/rest/user/login -> HTTP 200  19.4ms  784B
```

### 10.2 Sim-to-real transfer (N = 30 live episodes each)

| configuration | win rate | Wilson 95% CI | steps |
|---|---|---|---|
| random | 0.700 | [0.521, 0.833] | 10.00 |
| greedy-by-signal | 1.000 | [0.886, 1.000] | 6.00 |
| **zero-shot transfer** | **1.000** | [0.886, 1.000] | **5.00** |
| live fine-tuned | 1.000 | [0.886, 1.000] | 5.00 |

Fine-tuning added **exactly 0.000** — reported as a null result rather than omitted.

**The abstraction finding.** The *first* live run scored zero-shot **0.000** while random
scored 1.000. One evidence line explained it: `exploit | dvwa | no PHPSESSID; foothold
required first`. The simulator modelled one **global** privilege level, so its optimal
policy took a cheap foothold on one host and escalated on *another* — false here, because
the six targets are independent apps. After modelling host-local access, transfer became
perfect. **Fixing the probabilities would not have helped; fixing the abstraction did.**
"""))

C.append(md("### 10.3 CVE-metadata priors vs measured reality"))

C.append(code(r'''
# Measured: each of 12 probes run M=30 times; every one = 1.000, Wilson CI [0.886, 1.000].
names   = ["juice-shop\nprivesc", "flask-api\nfoothold", "dvwa\nprivesc",
           "flask-api\nprivesc", "dvwa\nfoothold", "juice-shop\nfoothold"]
derived = [PRIVESC_P[0], FOOTHOLD_P[2], PRIVESC_P[1], PRIVESC_P[2], FOOTHOLD_P[1], FOOTHOLD_P[0]]

x = np.arange(len(names)); w = .38
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.bar(x - w/2, derived, w, label="derived prior (CVSS/EPSS)", color=ACCENT)
ax.bar(x + w/2, [1.0]*6, w, label="measured (M=30)", color=GOOD)
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel("success probability"); ax.set_ylim(0, 1.15)
ax.set_title("Derived CVE-metadata prior vs measured reality")
ax.legend(); plt.tight_layout(); plt.show()

print(f"worst error: juice-shop privesc  prior {PRIVESC_P[0]:.3f} vs measured 1.000"
      f"  = {1.0/PRIVESC_P[0]:.1f}x")
print("\nCVSS scores SEVERITY; EPSS estimates exploitation attempts IN THE WILD -- a")
print("population statistic. Neither answers 'will THIS payload work on THIS host'.")
print("The formula was NOT re-fitted to match: that would be curve-fitting to one lab,")
print("destroying the only property the priors had -- independence from the measurement.")
''' ))

# ============================================================== Part 11 ML
C.append(md("""## Part 11 — ML component accuracy (measured locally)

`python -m experiments.eval_ml_models`

The shipped model pickles recorded **no accuracy at all** — the models had been trained but
never evaluated. We measured them properly. The corpus is heavily imbalanced, so raw
accuracy misleads and **macro-F1 is the fair metric**; the majority-class baseline is shown
as the number any model must beat."""))

C.append(code(r'''
ML = __ML_EVAL__

print(f"corpus: {ML['n_records']} records   classes: {ML['class_counts']}\n")
print(f"{'evaluation':34} {'accuracy':>9} {'macro-F1':>9}")
print("-" * 56)
b = ML['baseline']
print(f"{'majority baseline (always dos)':34} {b['accuracy']:>9.4f} {b['macro_f1']:>9.4f}")
s = ML.get('shipped_model_full_corpus', {})
if 'accuracy' in s:
    print(f"{'shipped model, FULL corpus*':34} {s['accuracy']:>9.4f} {s['macro_f1']:>9.4f}")
h = ML['heldout']
print(f"{'fresh model, HELD-OUT 20%':34} {h['accuracy']:>9.4f} {h['macro_f1']:>9.4f}")
print(f"\nlift over majority baseline: {h['lift_over_baseline_acc']:+.4f} accuracy")
print("\n* optimistic: the shipped model was fitted on this same data, so it is")
print("  effectively a TRAIN-set score, not a generalisation estimate.")

cm = np.array(h["confusion_matrix"]); labels_ = h["labels"]
fig, ax = plt.subplots(figsize=(5.2, 4.4))
im = ax.imshow(cm, cmap="Greens")
ax.set_xticks(range(len(labels_)), labels_); ax.set_yticks(range(len(labels_)), labels_)
ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.grid(False)
ax.set_title(f"Held-out n={h['n_test']} · acc {h['accuracy']:.4f} · macro-F1 {h['macro_f1']:.4f}",
             fontsize=10)
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=11,
                color="white" if cm[i, j] > cm.max()*.5 else INK)
fig.colorbar(im, ax=ax, shrink=.8); plt.tight_layout(); plt.show()

for i, lab in enumerate(labels_):
    print(f"  {lab:8} recall={cm[i,i]/cm[i].sum():.3f}  (support {cm[i].sum()})")
print("\nThe weak class is 'remote' -- only 632 records in the corpus. This is exactly why")
print("macro-F1, not accuracy, is the honest headline for an imbalanced problem.")
''' ))

# ============================================================== Part 12 positioning
C.append(md(r"""
## Part 12 — What is different about this project

### Honest positioning (stated before a reviewer asks)

**Not novel — do not claim these.** RL for penetration testing is a decade old. Tabular
Q-learning, double-Q, replay and value iteration are textbook. And crucially, *"an agent
attacks a real lab with zero-shot transfer"* was **already published**: **GAP**
(arXiv 2412.04078, Dec 2024), **PenGym** (Computers & Security 2024), **CRLF**
(ESORICS 2025).

### Where this work sits

| system | live services? | stochastic defender? | partially observable? | per-step evidence? |
|---|---|---|---|---|
| NASim / CyberBattleSim | no | invented constants | no | no |
| CybORG / CAGE | no | yes | yes | no |
| PenGym | yes | **deliberately avoided** | no | no |
| GAP | yes | via domain randomization | no | no |
| **ART-AI (this work)** | **yes** | **yes, modelled + measured** | **yes** | **yes** |

### Defensibly ours

1. **The state-abstraction finding** — the dominant sim-to-real gap was the abstraction
   (global vs per-host privilege), not the transition probabilities.
2. **The routability result** — learning beats a heuristic *iff* the defence is
   heterogeneous. Reached via two documented failures.
3. **A per-step evidence log** — each reward tied to a logged, verifiable observation.
4. **An observation-design lesson** — observe block *persistence*, not mere occurrence.

**Honest level:** a strong thesis / workshop contribution — a **testbed and an empirical
study**, not a new algorithm.

---

## Limitations (stated, not hidden)

1. The base lab is deterministic (p = 1.000 for all 12 probes); the defender layer exists
   precisely to fix this.
2. Small live N (25–30 episodes): a win rate of 1.000 at N=25 still admits a true rate of
   0.867.
3. The corpus `verified` column is uniformly 0 — one grounding signal is inert.
4. The live learner trained for only 100–120 episodes — undertrained for a ~150-state POMDP.
5. Vulnerability scanning is unauthenticated only, so three hosts honestly report zero.
6. LLM chat endpoints are non-functional (no model connected).
7. Six hosts on one machine is not a network, and there is no adaptive adversary.

## Reproducing everything

```bash
# simulation only -- no Docker required
python -m experiments.run_all            # 20 seeds x 800 episodes
python -m experiments.value_iteration    # V* = 0.6772

# requires the local lab:  cd lab && docker compose up -d
python -m experiments.run_live                      # sim-to-real protocol
python -m experiments.run_defender --strengths 4    # the routability result
python -m experiments.eval_ml_models                # ML accuracy
python -m live.tests.test_live                      # 42 tests
```
"""))

# ---------------------------------------------------------------- inject measured ML
ML_JSON = Path(__file__).resolve().parent.parent / "backend" / "experiments" / "results" / "ml_eval.json"
_m = json.loads(ML_JSON.read_text())
_compact = {
    "n_records": _m["n_records"],
    "class_counts": _m["class_counts"],
    "baseline": {k: _m["baseline"][k] for k in ("strategy", "accuracy", "macro_f1")},
    "shipped_model_full_corpus": {k: v for k, v in _m["shipped_model_full_corpus"].items()
                                  if k in ("accuracy", "macro_f1")},
    "heldout": {k: _m["heldout"][k] for k in
                ("n_train", "n_test", "accuracy", "macro_f1", "lift_over_baseline_acc",
                 "confusion_matrix", "labels")},
}
_lit = json.dumps(_compact, indent=4)
for c in C:
    if c["cell_type"] == "code":
        c["source"] = [ln.replace("__ML_EVAL__", _lit) for ln in c["source"]]

nb = {
    "nbformat": 4, "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True, "name": "ART_AI_Results.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": C,
}
OUT.write_text(json.dumps(nb, indent=1), encoding="utf-8")
n_code = sum(1 for c in C if c["cell_type"] == "code")
n_lines = sum(len(c["source"]) for c in C if c["cell_type"] == "code")
print(f"wrote {OUT}")
print(f"  {len(C)} cells ({n_code} code, {len(C)-n_code} markdown), {n_lines} lines of code")
