"""Sim-to-real protocol: evaluate agents against the REAL lab and measure the gap.

    python -m experiments.run_live --dry-run        # exercise every oracle, tiny budget
    python -m experiments.run_live                  # full live protocol
    python -m experiments.run_live --measure-only   # just re-measure probe probabilities

Protocol (20x800 is not affordable live):
  * zero-shot transfer: sim-trained frozen policy, evaluated live  <- headline number
  * live fine-tune:     continue learning live on a small budget
  * live baselines:     random and greedy-by-signal, same budget
  * measured probabilities: each probe run M times, Wilson 95% CI
  * measured-MDP optimum: value iteration re-run with the measured probabilities

Never fabricates: if the lab is down the harness SKIPS with a clear message.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from live.capabilities import (FOOTHOLD, HOST_NAMES, HOST_PORTS, PRIVESC,  # noqa: E402
                               SIM_EQUIVALENT)
from live.http_client import LabSession, get_request_count, reset_request_count  # noqa: E402

from .agents import GreedyBySignalAgent, RandomAgent, TabularQAgent  # noqa: E402
from .grounding import foothold_probs, privesc_probs  # noqa: E402
from .live_env import LiveAttackEnv, lab_health  # noqa: E402
from .mdp import ADMIN, DISCOUNT, AttackMDP, initial_state  # noqa: E402
from .metrics import run_episode as sim_run_episode  # noqa: E402
from .value_iteration import value_iteration  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "live"


# ------------------------------------------------------------------ statistics
def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    """Wilson score interval -- correct for small N, unlike the normal approximation."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(HERE),
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def image_digests() -> Dict[str, str]:
    lab = HERE.parent.parent / "lab"
    try:
        out = subprocess.check_output(["docker", "compose", "images", "--format", "json"],
                                      cwd=str(lab), stderr=subprocess.DEVNULL).decode()
        data = json.loads(out)
        return {d.get("Service", "?"): f"{d.get('Repository','?')}:{d.get('Tag','?')}@{str(d.get('ID',''))[:19]}"
                for d in (data if isinstance(data, list) else [data])}
    except Exception:
        return {}


# ------------------------------------------------------------- live evaluation
def eval_live(env: LiveAttackEnv, agent, n_episodes: int, max_steps: int,
              rng: random.Random, learn: bool = False) -> Dict:
    wins, steps_list, returns = 0, [], []
    for _ in range(n_episodes):
        s = env.reset()
        total, disc = 0.0, 1.0
        steps = 0
        for steps in range(1, max_steps + 1):
            a = agent.act(s)
            ns, r, done = env.step(s, a, rng)
            if learn:
                agent.observe(s, a, r, ns, done)
            total += disc * r
            disc *= DISCOUNT
            s = ns
            if done:
                break
        if learn:
            agent.end_episode()
        returns.append(total)
        if s[0] == ADMIN:
            wins += 1
            steps_list.append(steps)
    p, lo, hi = wilson_ci(wins, n_episodes)
    return {
        "n_episodes": n_episodes, "wins": wins,
        "win_rate": p, "win_lo": lo, "win_hi": hi,
        "mean_steps_to_admin": (sum(steps_list) / len(steps_list)) if steps_list else float("nan"),
        "mean_return": sum(returns) / len(returns),
    }


def train_sim_agent(seed: int, n_train: int, max_steps: int) -> TabularQAgent:
    """Train in the SIMULATION, then freeze -- this is the zero-shot transfer policy."""
    mdp = AttackMDP()
    rng = random.Random(seed)
    agent = TabularQAgent(rng=rng, use_double_q=True, use_replay=True)
    for _ in range(n_train):
        sim_run_episode(mdp, agent, rng, max_steps, learn=True)
        agent.end_episode()
    agent.freeze()
    return agent


# --------------------------------------------------- Step 7: measure the probes
def measure_probabilities(M: int, sink=None) -> Dict:
    """Run each capability probe M times independently; empirical rate + Wilson CI."""
    out = {}
    for host in HOST_NAMES:
        out[host] = {}
        for cap, registry in (("foothold", FOOTHOLD), ("privesc", PRIVESC)):
            succ = 0
            for i in range(M):
                s = LabSession()
                try:
                    if cap == "privesc":
                        # foothold first where the probe needs a session/token
                        FOOTHOLD[host](s)
                        fn = registry[host]
                        try:
                            res = fn(s, f"measure-{i}-{random.randrange(10**6)}")
                        except TypeError:
                            res = fn(s)
                    else:
                        res = registry[host](s)
                    if res.success:
                        succ += 1
                    if sink:
                        sink({"measure": True, "host": host, "cap": cap, "trial": i,
                              "success": res.success, "evidence": res.evidence})
                except Exception as e:
                    if sink:
                        sink({"measure": True, "host": host, "cap": cap, "trial": i,
                              "success": False, "error": repr(e)})
            p, lo, hi = wilson_ci(succ, M)
            out[host][cap] = {"M": M, "successes": succ, "rate": p, "ci95": [lo, hi]}
    return out


def measured_mdp_optimum(measured: Dict) -> float:
    """Re-run value iteration with MEASURED probabilities to get the real ceiling."""
    mdp = AttackMDP()
    hosts = SIM_EQUIVALENT  # the 3 sim-equivalent hosts, in sim host order
    for i, h in enumerate(hosts):
        if h in measured:
            mdp.foothold[i] = max(0.001, measured[h]["foothold"]["rate"])
            mdp.privesc[i] = max(0.001, measured[h]["privesc"]["rate"])
    mdp.p_recon = 1.0  # recon is an observation live, not a coin flip
    V, _, _ = value_iteration(mdp)
    return V[initial_state()]


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tiny budget; exercise everything")
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--episodes", type=int, default=30, help="live episodes per configuration")
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--sim-train", type=int, default=800)
    ap.add_argument("--finetune", type=int, default=30)
    ap.add_argument("--measure-M", type=int, default=30)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    if args.dry_run:
        args.episodes, args.sim_train, args.finetune, args.measure_M = 3, 100, 3, 3

    ok, msg = lab_health()
    print(f"[*] lab health: {msg}")
    if not ok:
        print("[!] SKIPPING live run: the lab is not up. Start it with:")
        print("      cd lab && docker compose up -d")
        print("    No results were produced (this harness never fabricates numbers).")
        sys.exit(2)

    RESULTS.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev_path = RESULTS / f"evidence-{run_id}.jsonl"
    ev_file = open(ev_path, "a", encoding="utf-8")

    def sink(rec):
        ev_file.write(json.dumps(rec, default=str) + "\n")
        ev_file.flush()

    reset_request_count()
    t_start = time.monotonic()
    report: Dict = {"run_id": run_id, "args": vars(args)}

    # -------------------------------------------------- Step 7: measured probabilities
    print(f"[*] measuring capability probabilities (M={args.measure_M} per probe)...")
    measured = measure_probabilities(args.measure_M, sink=sink)
    report["measured"] = measured
    derived_f, derived_p = foothold_probs(), privesc_probs()
    sim_hosts = SIM_EQUIVALENT
    print(f"\n  {'host':12} {'cap':9} {'derived prior':>14} {'measured':>10} {'Wilson 95% CI':>20}")
    print("  " + "-" * 70)
    for host in HOST_NAMES:
        for cap in ("foothold", "privesc"):
            m = measured[host][cap]
            if host in sim_hosts:
                idx = sim_hosts.index(host)
                prior = (derived_f if cap == "foothold" else derived_p)[idx]
                ps = f"{prior:.3f}"
            else:
                ps = "n/a (not in sim)"
            print(f"  {host:12} {cap:9} {ps:>14} {m['rate']:>10.3f}"
                  f"   [{m['ci95'][0]:.3f}, {m['ci95'][1]:.3f}]")

    if not args.measure_only:
        # ------------------------------------------------ Step 6: sim-to-real protocol
        # Restrict the live action space to the sim-equivalent hosts for a fair
        # like-for-like transfer comparison.
        env = LiveAttackEnv(hosts=list(SIM_EQUIVALENT), evidence_sink=sink)
        rng = random.Random(args.seed)

        print(f"\n[*] training sim agent ({args.sim_train} episodes) then freezing...")
        zero_shot = train_sim_agent(args.seed, args.sim_train, args.max_steps)

        rows = []
        print(f"[*] live evaluation, {args.episodes} episodes per configuration...")

        print("    - random baseline")
        rows.append(("random", eval_live(env, RandomAgent(rng), args.episodes, args.max_steps, rng)))

        print("    - greedy-by-signal baseline")
        rows.append(("greedy_by_signal",
                     eval_live(env, GreedyBySignalAgent(rng), args.episodes, args.max_steps, rng)))

        print("    - zero-shot transfer (sim-trained, frozen)")
        rows.append(("zero_shot_transfer",
                     eval_live(env, zero_shot, args.episodes, args.max_steps, rng)))

        print(f"    - live fine-tune ({args.finetune} episodes) then evaluate")
        ft = train_sim_agent(args.seed, args.sim_train, args.max_steps)
        ft.epsilon, ft.use_boltzmann, ft.use_hint = 0.2, False, False
        eval_live(env, ft, args.finetune, args.max_steps, rng, learn=True)
        ft.freeze()
        rows.append(("live_finetuned",
                     eval_live(env, ft, args.episodes, args.max_steps, rng)))

        report["live_rows"] = [{"config": c, **m} for c, m in rows]

        # measured-MDP optimum + sim optimum
        sim_opt = value_iteration(AttackMDP())[0][initial_state()]
        meas_opt = measured_mdp_optimum(measured)
        report["sim_optimum"] = sim_opt
        report["measured_optimum"] = meas_opt

        print("\n" + "=" * 92)
        print(f"{'config':22} {'win rate':>10} {'Wilson 95% CI':>20} {'steps':>8} {'return':>9} {'regret*':>9}")
        print("-" * 92)
        for c, m in rows:
            st = "n/a" if m["mean_steps_to_admin"] != m["mean_steps_to_admin"] else f"{m['mean_steps_to_admin']:.2f}"
            print(f"{c:22} {m['win_rate']:>10.3f}  [{m['win_lo']:.3f}, {m['win_hi']:.3f}]"
                  f"  {st:>8} {m['mean_return']:>9.3f} {meas_opt - m['mean_return']:>9.3f}")
        print("=" * 92)
        print(f"sim optimum V*={sim_opt:.4f}   measured-MDP optimum V*={meas_opt:.4f}   (*regret vs measured)")

    wall = time.monotonic() - t_start
    reqs = get_request_count()
    n_ep = args.episodes * 4 + args.finetune if not args.measure_only else 0
    report["cost"] = {
        "wall_clock_s": round(wall, 1),
        "total_requests": reqs,
        "live_episodes": n_ep,
        "requests_per_episode": round(reqs / n_ep, 1) if n_ep else None,
    }
    print(f"\n[*] cost: {reqs} real requests, {wall:.1f}s wall-clock"
          + (f", {n_ep} live episodes ({reqs/n_ep:.1f} req/episode)" if n_ep else ""))

    meta = {
        "run_id": run_id, "git_commit": git_commit(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "image_digests": image_digests(),
        "lab_port_map": {h: HOST_PORTS[h] for h in HOST_NAMES},
        "excluded_hosts": {},  # all six lab services have working oracles
        "config": vars(args),
    }
    (RESULTS / f"run_meta-{run_id}.json").write_text(json.dumps(meta, indent=2, default=str))
    (RESULTS / f"report-{run_id}.json").write_text(json.dumps(report, indent=2, default=str))
    (HERE / "measured_probs.json").write_text(json.dumps(
        {"date": meta["timestamp_utc"], "M": args.measure_M,
         "image_digests": meta["image_digests"], "measured": measured}, indent=2, default=str))
    ev_file.close()
    print(f"[*] evidence log : {ev_path}")
    print(f"[*] measured probs: {HERE / 'measured_probs.json'}")


if __name__ == "__main__":
    main()
