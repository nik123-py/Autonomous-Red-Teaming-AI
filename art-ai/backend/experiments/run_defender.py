"""Headline experiment (research question 1): does a LEARNED policy beat the
non-adaptive greedy heuristic once the live lab has a real defender?

On the deterministic lab they were tied (both ~1.0). The hypothesis is that
defender-induced uncertainty -- lockout the agent can observe and route around -- is what
makes learning pay. The greedy baseline ignores the observed-blocked field by design; the
tabular agent is keyed on it, so it can learn to switch away from a locked host.

    python -m experiments.run_defender                 # strengths 2 and 3
    python -m experiments.run_defender --strengths 3   # just the strong defender
    python -m experiments.run_defender --dry-run       # tiny budget

Never fabricates: skips with a clear message if the lab is down.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from live.capabilities import SIM_EQUIVALENT
from live.defenses import STRENGTH_LABELS, policy_for_strength
from live.http_client import get_request_count, reset_request_count

from .agents import GreedyBySignalAgent, TabularQAgent
from .live_env import LiveAttackEnv, lab_health
from .metrics import run_episode
from .run_live import RESULTS, wilson_ci

HERE = Path(__file__).resolve().parent


def eval_agent(env, agent, n, max_steps, rng, learn=False):
    wins, steps = 0, []
    for _ in range(n):
        won, st, _ = run_episode(env, agent, rng, max_steps, learn=learn)
        if learn:
            agent.end_episode()
        if won:
            wins += 1
            steps.append(st)
    p, lo, hi = wilson_ci(wins, n)
    ms = sum(steps) / len(steps) if steps else float("nan")
    return {"n": n, "wins": wins, "win_rate": p, "lo": lo, "hi": hi, "mean_steps": ms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strengths", type=int, nargs="+", default=[2, 3])
    ap.add_argument("--train", type=int, default=80, help="live training episodes for the learner")
    ap.add_argument("--eval", type=int, default=20)
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        args.train, args.eval, args.strengths = 15, 8, [3]

    ok, msg = lab_health()
    print(f"[*] lab health: {msg}")
    if not ok:
        print("[!] SKIPPING: lab is down. Start it: cd lab && docker compose up -d")
        raise SystemExit(2)

    reset_request_count()
    t0 = time.monotonic()
    rows = []
    for lvl in args.strengths:
        label = STRENGTH_LABELS.get(lvl, str(lvl))
        print(f"\n=== defender strength {lvl} ({label}) ===")

        # --- greedy baseline (non-adaptive) ---
        rng = random.Random(args.seed + lvl)
        env = LiveAttackEnv(hosts=list(SIM_EQUIVALENT), defense=policy_for_strength(lvl, seed=lvl))
        g = eval_agent(env, GreedyBySignalAgent(rng), args.eval, args.max_steps, rng)
        print(f"    greedy      : win {g['win_rate']:.3f} [{g['lo']:.3f},{g['hi']:.3f}]  steps {g['mean_steps']:.2f}")

        # --- learned, defender-aware ---
        rng2 = random.Random(args.seed + 1000 + lvl)
        env2 = LiveAttackEnv(hosts=list(SIM_EQUIVALENT), defense=policy_for_strength(lvl, seed=lvl))
        agent = TabularQAgent(rng=rng2, epsilon=0.4, epsilon_decay=0.99, min_epsilon=0.05,
                              use_double_q=True, use_replay=True, use_boltzmann=False)
        print(f"    training learner live for {args.train} episodes...")
        eval_agent(env2, agent, args.train, args.max_steps, rng2, learn=True)
        agent.freeze()
        L = eval_agent(env2, agent, args.eval, args.max_steps, rng2)
        print(f"    learned     : win {L['win_rate']:.3f} [{L['lo']:.3f},{L['hi']:.3f}]  steps {L['mean_steps']:.2f}"
              f"   (q-states {agent.q_table_size()})")

        rows.append({"strength": lvl, "label": label, "greedy": g, "learned": L})

    wall = time.monotonic() - t0
    reqs = get_request_count()
    print("\n" + "=" * 72)
    print(f"{'strength':12} {'greedy win':>12} {'learned win':>13} {'delta':>8}")
    print("-" * 72)
    for r in rows:
        d = r["learned"]["win_rate"] - r["greedy"]["win_rate"]
        print(f"{r['label']:12} {r['greedy']['win_rate']:>12.3f} {r['learned']['win_rate']:>13.3f} {d:>+8.3f}")
    print("=" * 72)
    print(f"[*] cost: {reqs} real requests, {wall:.1f}s")

    RESULTS.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"defender-{run_id}.json"
    out.write_text(json.dumps({"run_id": run_id, "args": vars(args), "rows": rows,
                               "cost": {"requests": reqs, "wall_s": round(wall, 1)}}, indent=2))
    print(f"[*] wrote {out}")


if __name__ == "__main__":
    main()
