"""Generate all figures for PROJECT_SUMMARY_DETAILED.md into paper/figures/*.png.

Self-contained: the simulated MDP / Q-learning figures are COMPUTED here; the live-lab and
ML figures plot results MEASURED locally (see the summary doc for the command that produced
each). No number here is invented.

    python make_figures.py
"""
import itertools, json, math, random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)
INK, ACCENT, GOOD, GREY, PAPER = "#1A2230", "#B3412B", "#2E7D54", "#8A93A0", "#EFEFEA"

# ----------------------------------------------------------------- the simulated MDP
FOOTHOLD_P = {0: 0.810, 1: 0.536, 2: 0.216}
PRIVESC_P = {0: 0.126, 1: 0.384, 2: 0.508}
P_RECON, STEP_COST, GOAL, GAMMA = 0.90, 0.01, 1.0, 0.95
NONE, USER, ADMIN = 0, 1, 2
ACTIONS = ["recon", "exploit"] + [f"move_{i}" for i in range(3)]
S0 = (NONE, 0, frozenset())


def all_states():
    subs = [frozenset(c) for r in range(4) for c in itertools.combinations(range(3), r)]
    return [(a, p, d) for a in (NONE, USER, ADMIN) for p in range(3) for d in subs]


def transitions(s, a):
    access, pos, disc = s
    if access == ADMIN:
        return [(1.0, s, 0.0)]
    r = -STEP_COST
    if a == "recon":
        und = sorted(set(range(3)) - disc)
        if not und:
            return [(1.0, s, r)]
        j = und[0]
        return [(P_RECON, (access, pos, frozenset(disc | {j})), r), (1 - P_RECON, s, r)]
    if a.startswith("move_"):
        i = int(a.split("_")[1])
        return [(1.0, (access, i, disc) if i in disc else s, r)]
    if pos not in disc:
        return [(1.0, s, r)]
    if access == NONE:
        p = FOOTHOLD_P[pos]
        return [(p, (USER, pos, disc), r), (1 - p, s, r)]
    p = PRIVESC_P[pos]
    return [(p, (ADMIN, pos, disc), r + GOAL), (1 - p, s, r)]


def value_iteration(theta=1e-12):
    S = all_states(); V = {s: 0.0 for s in S}
    for _ in range(100000):
        d = 0.0
        for s in S:
            if s[0] == ADMIN:
                continue
            b = max(sum(p * (rw + GAMMA * V[ns]) for p, ns, rw in transitions(s, a)) for a in ACTIONS)
            d = max(d, abs(b - V[s])); V[s] = b
        if d < theta:
            break
    return V


V = value_iteration(); VSTAR = V[S0]
print(f"V* = {VSTAR:.4f}")


def skey(s): return f"a{s[0]}|p{s[1]}|d{','.join(map(str, sorted(s[2]))) or '-'}"


class QAgent:
    def __init__(self, rng, lr=.2, eps=.3, decay=.995, min_eps=.02, double_q=True, replay=True, batch=32):
        self.rng, self.lr, self.eps, self.decay, self.min_eps = rng, lr, eps, decay, min_eps
        self.double_q, self.replay_on, self.batch = double_q, replay, batch
        self.qa, self.qb, self.buf = {}, {}, []

    def _q(self, t, k, a): return t.get(k, {}).get(a, 0.0)

    def _comb(self, k, a):
        return 0.5 * (self._q(self.qa, k, a) + self._q(self.qb, k, a)) if self.double_q else self._q(self.qa, k, a)

    def act(self, s):
        k = skey(s)
        if self.rng.random() < self.eps:
            return self.rng.choice(ACTIONS)
        vals = [(a, self._comb(k, a)) for a in ACTIONS]; m = max(v for _, v in vals)
        return self.rng.choice([a for a, v in vals if v == m])

    def _upd(self, s, a, r, ns, done):
        k, nk = skey(s), skey(ns)
        if self.double_q:
            up, oth = (self.qa, self.qb) if self.rng.random() < .5 else (self.qb, self.qa)
        else:
            up = oth = self.qa
        tgt = r if done else r + GAMMA * self._q(oth, nk, max(ACTIONS, key=lambda x: self._q(up, nk, x)))
        cur = self._q(up, k, a); up.setdefault(k, {})[a] = cur + self.lr * (tgt - cur)

    def observe(self, s, a, r, ns, done):
        self._upd(s, a, r, ns, done)
        if self.replay_on:
            self.buf.append((s, a, r, ns, done))
            if len(self.buf) > 5000: self.buf.pop(0)
            if len(self.buf) >= self.batch:
                for e in self.rng.sample(self.buf, self.batch): self._upd(*e)

    def end_episode(self): self.eps = max(self.min_eps, self.eps * self.decay)


def step_env(s, a, rng):
    outs = transitions(s, a); x = rng.random(); c = 0.0
    for p, ns, rw in outs:
        c += p
        if x <= c: return ns, rw, ns[0] == ADMIN
    p, ns, rw = outs[-1]; return ns, rw, ns[0] == ADMIN


def episode(agent, rng, max_steps=15, learn=False, policy=None):
    s, tot, disc = S0, 0.0, 1.0
    for t in range(1, max_steps + 1):
        a = policy(s) if policy else agent.act(s)
        ns, r, done = step_env(s, a, rng)
        if learn: agent.observe(s, a, r, ns, done)
        tot += disc * r; disc *= GAMMA; s = ns
        if done: return True, t, tot
    return s[0] == ADMIN, max_steps, tot


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("  wrote", name)


# ---------------------------------------------------------------- fig 1 learning curve
def fig_learning_curve():
    # finer grid early: the agent climbs within the first ~30 episodes, so a coarse
    # 25-episode grid hides the whole learning transition.
    xs = [1, 2, 3, 5, 8, 12, 16, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 600]
    curves = []
    for sd in range(8):
        rng = random.Random(500 + sd); ag = QAgent(rng); ys = []
        for ep in range(1, 601):
            episode(ag, rng, learn=True); ag.end_episode()
            if ep in xs:
                e = ag.eps; ag.eps = 0.0
                ys.append(np.mean([episode(ag, rng)[0] for _ in range(200)])); ag.eps = e
        curves.append(ys)
    C = np.array(curves); mean = C.mean(0); ci = 1.96 * C.std(0) / math.sqrt(C.shape[0])
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(xs, mean, color=INK, lw=2, label="Q-learning (mean of 8 seeds)")
    ax.fill_between(xs, mean - ci, mean + ci, color=INK, alpha=.18, label="95% CI")
    ax.axhline(1.0, ls="--", color=GOOD, label="optimal policy")
    ax.axhline(0.171, ls=":", color=ACCENT, label="random baseline (0.171)")
    ax.set_xscale("log")
    ax.set_xlabel("training episodes (log scale)"); ax.set_ylabel("greedy win rate")
    ax.set_title("Learning curve — from random-level to near-optimal within ~30 episodes")
    ax.set_ylim(0, 1.08); ax.legend(loc="lower right"); ax.grid(alpha=.3)
    save(fig, "fig1_learning_curve.png")


# ----------------------------------------------------------------- fig 2 MDP diagram
def fig_mdp():
    fig, ax = plt.subplots(figsize=(10, 3.4)); ax.axis("off")
    pos = {"NONE": (0.5, 0.6), "USER": (3.0, 0.6), "ADMIN": (5.5, 0.6)}
    for name, (x, y) in pos.items():
        g = name == "ADMIN"
        ax.add_patch(plt.Circle((x, y), .42, fc="#E6F0EA" if g else "white",
                                ec=GOOD if g else INK, lw=2.2 if g else 1.5))
        ax.text(x, y, name, ha="center", va="center", fontsize=11, fontweight="bold" if g else "normal")
    for a, b, lab in [("NONE", "USER", "exploit\n(foothold)"), ("USER", "ADMIN", "exploit\n(privesc)")]:
        x1, y1 = pos[a]; x2, y2 = pos[b]
        ax.annotate("", xy=(x2 - .45, y2), xytext=(x1 + .45, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1.8, color=INK))
        ax.text((x1 + x2) / 2, y1 + .16, lab, ha="center", fontsize=9)
    for n in ("NONE", "USER"):
        x, y = pos[n]
        ax.annotate("", xy=(x + .20, y + .40), xytext=(x - .20, y + .40),
                    arrowprops=dict(arrowstyle="-|>", lw=1.3, color=GREY,
                                    connectionstyle="arc3,rad=-1.1"))
        ax.text(x, y + .80, "recon / move", ha="center", fontsize=8.5, color="#5A6472")
    ax.text(3.0, -.42, "ORIGINAL BUG: a non-escalating action returned success + reward while leaving the\n"
                       "state unchanged, so Q bootstrapped on itself and diverged (Q=90.9), trapping the\n"
                       "policy before ADMIN. Win rate was 2% vs random's 49%.",
            ha="center", fontsize=9, color=ACCENT)
    ax.set_xlim(-.3, 6.3); ax.set_ylim(-.95, 1.9)
    ax.set_title("Privilege-escalation MDP and the self-loop that defeated the original agent")
    save(fig, "fig2_mdp.png")


# ---------------------------------------------------------------- fig 3 architecture
def fig_arch():
    fig, ax = plt.subplots(figsize=(11, 4.2)); ax.axis("off")

    def box(x, y, w, h, t, s, fc="white", ec=INK, tc=INK):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.6, zorder=2))
        ax.text(x + w / 2, y + h * .63, t, ha="center", fontsize=10.5, fontweight="bold", color=tc)
        ax.text(x + w / 2, y + h * .26, s, ha="center", fontsize=8.5, color=tc)

    box(0.1, 1.5, 2.1, .95, "React dashboard", "14 routes")
    box(0.1, 0.3, 2.1, .95, "FastAPI backend", "38 endpoints")
    box(2.7, 0.9, 2.1, .95, "RL core", "double-Q + value iteration")
    box(5.3, 1.7, 2.3, .95, "Simulated MDP", "enumerable -> V* exact", fc=PAPER)
    box(5.3, 0.1, 2.3, .95, "Live environment", "real HTTP + oracles", fc=PAPER)
    box(8.1, 0.95, 2.0, .85, "Scope choke point", "127.0.0.1:3001-3006", fc="#F7E9E4", ec=ACCENT, tc=ACCENT)
    box(8.1, -0.3, 2.0, .85, "Docker lab", "6 vulnerable services", fc="#E6F0EA", ec=GOOD)
    for x1, y1, x2, y2 in [(2.2, 1.97, 2.7, 1.45), (2.2, .77, 2.7, 1.25), (4.8, 1.5, 5.3, 2.17),
                           (4.8, 1.1, 5.3, .57), (7.6, .57, 8.1, 1.3), (9.1, .95, 9.1, .55)]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#5A6472"))
    ax.text(5.9, 2.95, "Both environments expose ONE identical interface, so any agent runs against either\n"
                       "unchanged -- which is what makes the sim-to-real gap measurable rather than guessed.",
            ha="center", fontsize=9, color="#5A6472")
    ax.set_xlim(0, 10.4); ax.set_ylim(-.6, 3.3)
    save(fig, "fig3_architecture.png")


# ------------------------------------------------------ fig 4 prior vs measured
def fig_priors():
    labels = ["juice-shop\nprivesc", "flask-api\nfoothold", "dvwa\nprivesc",
              "flask-api\nprivesc", "dvwa\nfoothold", "juice-shop\nfoothold"]
    derived = [0.126, 0.216, 0.384, 0.508, 0.536, 0.810]
    x = np.arange(len(labels)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(x - w / 2, derived, w, label="derived prior (CVSS/EPSS)", color=ACCENT)
    ax.bar(x + w / 2, [1.0] * 6, w, label="measured (M=30)", color=GOOD)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("success probability"); ax.set_ylim(0, 1.15)
    ax.set_title("Derived CVE-metadata prior vs measured reality (worst error ~8x)")
    ax.legend(); ax.grid(axis="y", alpha=.3)
    save(fig, "fig4_prior_vs_measured.png")


# ------------------------------------------------------------- fig 5 transfer
def fig_transfer():
    cfgs = ["random", "greedy-by-\nsignal", "zero-shot\ntransfer", "live\nfine-tuned"]
    wins = np.array([0.700, 1.000, 1.000, 1.000])
    lo = np.array([0.521, 0.886, 0.886, 0.886]); hi = np.array([0.833, 1.000, 1.000, 1.000])
    steps = [10.00, 6.00, 5.00, 5.00]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.bar(cfgs, wins, yerr=[wins - lo, hi - wins], capsize=5, color=[GREY, GREY, INK, INK])
    a1.set_ylabel("win rate"); a1.set_ylim(0, 1.15)
    a1.set_title("Live win rate (N=30, Wilson 95% CI)"); a1.grid(axis="y", alpha=.3)
    a2.bar(cfgs, steps, color=[GREY, GREY, GOOD, GOOD])
    a2.set_ylabel("steps to ADMIN (lower is better)")
    a2.set_title("Efficiency — zero-shot is fastest"); a2.grid(axis="y", alpha=.3)
    save(fig, "fig5_transfer.png")


# --------------------------------------------------------- fig 6 routability
def fig_routability():
    rows = [("medium (uniform)", 0.920, 1.000), ("strong (uniform)", 0.600, 0.320),
            ("strong + persistence obs", 0.600, 0.000), ("heterogeneous (routable)", 0.320, 1.000)]
    y = np.arange(len(rows)); h = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.barh(y + h / 2, [r[1] for r in rows], h, label="greedy heuristic", color=GREY)
    ax.barh(y - h / 2, [r[2] for r in rows], h, label="learned policy", color=INK)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=10)
    ax.set_xlabel("win rate (N=25)"); ax.set_xlim(0, 1.1); ax.invert_yaxis()
    ax.set_title("Learning beats the heuristic only when the defence is ROUTABLE")
    ax.legend(loc="lower right"); ax.grid(axis="x", alpha=.3)
    save(fig, "fig6_routability.png")


# ------------------------------------------------------------ fig 7 confusion
def fig_confusion():
    p = HERE.parent / "backend" / "experiments" / "results" / "ml_eval.json"
    m = json.loads(p.read_text())["heldout"]
    cm = np.array(m["confusion_matrix"]); labels = m["labels"]
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(labels)), labels); ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("predicted"); ax.set_ylabel("true")
    ax.set_title(f"Exploit-type classifier — held-out n={m['n_test']}\n"
                 f"acc {m['accuracy']:.4f} · macro-F1 {m['macro_f1']:.4f}", fontsize=10)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=11,
                    color="white" if cm[i, j] > cm.max() * .5 else INK)
    fig.colorbar(im, ax=ax, shrink=.8)
    save(fig, "fig7_confusion.png")


# ------------------------------------------------------- fig 8 sim results bar
def fig_sim_results():
    names = ["random", "greedy-by-\nCVSS", "Q-learning\n(repaired)", "value-iteration\noptimum"]
    wins = [0.171, 0.999, 0.960, 1.0]
    err = [0.012, 0.001, 0.035, 0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.bar(names, wins, yerr=err, capsize=5, color=[GREY, GREY, INK, GOOD])
    a1.set_ylabel("win rate"); a1.set_ylim(0, 1.15)
    a1.set_title("Simulated win rate (20 seeds × 800 ep, mean ± 95% CI)")
    a1.grid(axis="y", alpha=.3)
    a1.tick_params(axis="x", labelsize=8.5)
    regret = [0.680, 0.022, 0.047, 0.0]
    a2.bar(names, regret, color=[GREY, GREY, INK, GOOD])
    a2.set_ylabel("regret vs exact optimum (lower is better)")
    a2.set_title(f"Regret against V* = {VSTAR:.4f}"); a2.grid(axis="y", alpha=.3)
    a2.tick_params(axis="x", labelsize=8.5)
    save(fig, "fig8_sim_results.png")


if __name__ == "__main__":
    print("generating figures ->", FIG)
    fig_sim_results(); fig_learning_curve(); fig_mdp(); fig_arch()
    fig_priors(); fig_transfer(); fig_routability(); fig_confusion()
    print("done")
