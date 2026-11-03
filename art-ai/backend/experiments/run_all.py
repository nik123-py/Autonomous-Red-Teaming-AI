"""Single entry point that regenerates every number and plot.

    python -m experiments.run_all            # uses experiments/config.yaml
    python -m experiments.run_all --quick    # small N for a fast smoke run

Outputs (under experiments/results/):
  * results.json / results.csv   — every metric with mean +/- 95% CI
  * learning_curves.png          — win-rate vs training episodes per configuration
  * run_meta.json                — seed, git commit, config, library versions

Nothing here contacts a network target; it is pure simulation over the tabular MDP.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List

import yaml

from .agents import GreedyBySignalAgent, RandomAgent, TabularQAgent
from .grounding import HOSTS, foothold_probs, privesc_probs
from .mdp import AttackMDP, initial_state
from .metrics import evaluate, mean_ci, train_and_track
from .value_iteration import value_iteration

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def derived_seeds(master: int, n: int) -> List[int]:
    rng = random.Random(master)
    return [rng.randrange(1, 2**31 - 1) for _ in range(n)]


def make_agent(rng: random.Random, cfg: Dict) -> TabularQAgent:
    a = dict(cfg["agent"])
    return TabularQAgent(rng=rng, **a)


def run_qlearning_config(cfg: Dict, overrides: Dict, seeds: List[int]):
    """Train+eval the Q-learner (with overrides) across all seeds. Returns per-run
    metrics plus averaged learning curve."""
    base = dict(cfg["agent"])
    base.update(overrides)
    local_cfg = dict(cfg)
    local_cfg["agent"] = base

    win_rates, steps, returns, regrets, eff, qsizes = [], [], [], [], [], []
    curves = []
    mdp = AttackMDP()
    v_star = value_iteration(mdp)[0][initial_state()]

    for seed in seeds:
        rng = random.Random(seed)
        agent = make_agent(rng, local_cfg)
        episodes, wrs, reached = train_and_track(
            mdp, agent, rng,
            n_train=cfg["n_train"], max_steps=cfg["max_steps"],
            eval_every=cfg["eval_every"], n_eval_snapshot=cfg["n_eval_snapshot"],
            win_threshold=cfg["win_threshold"],
        )
        curves.append((episodes, wrs))
        eff.append(reached)
        qsizes.append(agent.q_table_size())

        agent.freeze()
        m = evaluate(mdp, agent, rng, cfg["n_eval"], cfg["max_steps"])
        win_rates.append(m["win_rate"])
        steps.append(m["mean_steps_to_admin"])
        returns.append(m["mean_return"])
        regrets.append(v_star - m["mean_return"])

    # average the learning curve across seeds (episodes are identical per config)
    eps_axis = curves[0][0]
    avg_curve = [sum(c[1][i] for c in curves) / len(curves) for i in range(len(eps_axis))]
    return {
        "win_rate": win_rates, "steps": steps, "return": returns,
        "regret": regrets, "episodes_to_threshold": eff, "q_table_size": qsizes,
        "curve_episodes": eps_axis, "curve_win_rate": avg_curve,
    }


def run_baseline(agent_cls, cfg: Dict, seeds: List[int]):
    win_rates, steps, returns, regrets = [], [], [], []
    mdp = AttackMDP()
    v_star = value_iteration(mdp)[0][initial_state()]
    for seed in seeds:
        rng = random.Random(seed)
        agent = agent_cls(rng)
        m = evaluate(mdp, agent, rng, cfg["n_eval"], cfg["max_steps"])
        win_rates.append(m["win_rate"])
        steps.append(m["mean_steps_to_admin"])
        returns.append(m["mean_return"])
        regrets.append(v_star - m["mean_return"])
    return {"win_rate": win_rates, "steps": steps, "return": returns, "regret": regrets}


def summarize(name: str, raw: Dict) -> Dict:
    out = {"config": name}
    for metric in ("win_rate", "steps", "return", "regret", "episodes_to_threshold", "q_table_size"):
        if metric in raw:
            mean, ci = mean_ci(raw[metric])
            out[f"{metric}_mean"] = mean
            out[f"{metric}_ci95"] = ci
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(HERE, "config.yaml"))
    ap.add_argument("--quick", action="store_true", help="tiny N for a smoke run")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    if args.quick:
        cfg.update(n_runs=3, n_train=200, n_eval=100, eval_every=25, n_eval_snapshot=50)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    seeds = derived_seeds(cfg["seed"], cfg["n_runs"])

    mdp = AttackMDP()
    V, Q, pi = value_iteration(mdp)
    v_star = V[initial_state()]
    print(f"[*] Value-iteration optimum V*(initial) = {v_star:.4f}  (the ceiling)")
    print(f"[*] {cfg['n_runs']} runs x {cfg['n_train']} train episodes each\n")

    rows: List[Dict] = []
    curves: Dict[str, Dict] = {}

    print("[*] Baselines...")
    rows.append(summarize("random", run_baseline(RandomAgent, cfg, seeds)))
    rows.append(summarize("greedy_by_signal", run_baseline(GreedyBySignalAgent, cfg, seeds)))

    print("[*] Fixed Q-learning agent (default config)...")
    default_raw = run_qlearning_config(cfg, {}, seeds)
    rows.append(summarize("q_learning", default_raw))
    curves["q_learning"] = {"episodes": default_raw["curve_episodes"], "win_rate": default_raw["curve_win_rate"]}

    print("[*] Ablations...")
    for name, ov in cfg.get("ablations", {}).items():
        print(f"    - {name}: {ov}")
        raw = run_qlearning_config(cfg, ov, seeds)
        rows.append(summarize(name, raw))
        curves[name] = {"episodes": raw["curve_episodes"], "win_rate": raw["curve_win_rate"]}

    # value-iteration optimum as a reference row
    rows.append({"config": "value_iteration_optimum", "return_mean": v_star, "return_ci95": 0.0,
                 "regret_mean": 0.0, "regret_ci95": 0.0})

    # --- write artifacts --------------------------------------------------------
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump({"v_star": v_star, "rows": rows}, f, indent=2)

    fieldnames = sorted({k for r in rows for k in r})
    fieldnames = ["config"] + [k for k in fieldnames if k != "config"]
    with open(os.path.join(RESULTS_DIR, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "seed": cfg["seed"],
        "seeds": seeds,
        "config": cfg,
        "python": sys.version,
        "platform": platform.platform(),
        "grounded_foothold_probs": foothold_probs(),
        "grounded_privesc_probs": privesc_probs(),
        "hosts": [h.name for h in HOSTS],
    }
    with open(os.path.join(RESULTS_DIR, "run_meta.json"), "w") as f:
        json.dump(meta, f, indent=2, default=str)

    _plot_curves(curves)
    _print_table(rows, v_star)


def _plot_curves(curves: Dict[str, Dict]):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[!] matplotlib unavailable ({e}); skipping PNG")
        return
    plt.figure(figsize=(8, 5))
    for name, c in curves.items():
        plt.plot(c["episodes"], c["win_rate"], marker="o", markersize=3, label=name)
    plt.xlabel("training episodes")
    plt.ylabel("greedy win rate")
    plt.title("Learning curves (mean over runs)")
    plt.ylim(-0.02, 1.02)
    plt.legend()
    plt.grid(True, alpha=0.3)
    out = os.path.join(RESULTS_DIR, "learning_curves.png")
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    print(f"[*] wrote {out}")


def _fmt(v):
    return "  n/a " if v is None or (isinstance(v, float) and v != v) else f"{v:6.3f}"


def _print_table(rows: List[Dict], v_star: float):
    print("\n" + "=" * 92)
    print(f"{'config':24s} {'win_rate':>16s} {'steps_admin':>14s} {'return':>10s} {'regret':>10s}")
    print("-" * 92)
    for r in rows:
        wr = f"{_fmt(r.get('win_rate_mean'))}+-{_fmt(r.get('win_rate_ci95'))}"
        st = _fmt(r.get("steps_mean"))
        rt = _fmt(r.get("return_mean"))
        rg = _fmt(r.get("regret_mean"))
        print(f"{r['config']:24s} {wr:>16s} {st:>14s} {rt:>10s} {rg:>10s}")
    print("=" * 92)
    print(f"value-iteration optimum V* = {v_star:.4f}")


if __name__ == "__main__":
    main()
