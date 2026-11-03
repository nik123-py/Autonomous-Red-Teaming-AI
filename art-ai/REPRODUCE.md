# REPRODUCE.md — regenerate every number and plot

All results are produced by a self-contained, deterministic simulation over the
tabular attack MDP in `backend/experiments/`. Nothing here contacts a network target.

## 1. Environment

```bash
cd art-ai/backend
python -m pip install -r experiments/requirements-freeze.txt
```

Generated with Python 3.14 on Windows 11. Only numpy/scipy/matplotlib/pyyaml are used
by the harness (pandas is optional). `scipy` is used for t-based confidence intervals;
if it is absent the harness falls back to a normal (1.96) approximation.

## 2. Inspect the grounded dynamics and the optimum

```bash
python -m experiments.grounding          # per-host probabilities derived from CVSS/EPSS/verified/patch-age
python -m experiments.value_iteration     # exact optimal value + policy trace (the ceiling)
```

## 3. Regenerate all results

```bash
python -m experiments.run_all            # full run: 20 seeds x 800 episodes (~3-4 min)
python -m experiments.run_all --quick    # fast smoke run (3 seeds x 200 episodes)
```

Outputs land in `backend/experiments/results/`:

| file                 | contents                                                        |
|----------------------|-----------------------------------------------------------------|
| `results.json`       | every metric, mean + 95% CI, per configuration                  |
| `results.csv`        | same, flat CSV                                                  |
| `learning_curves.png`| greedy win-rate vs training episodes, per configuration         |
| `run_meta.json`      | seed, derived seed list, git commit, config, versions, hosts    |

## 4. Determinism

Every run seed is derived from the master `seed` in `experiments/config.yaml`
(`derived_seeds`). Re-running with the same config reproduces the same numbers. The
seed, the resolved seed list, the git commit, and the full config are all written to
`run_meta.json` next to the results.

## 5. Legacy ground-truth check (the broken starting point)

```bash
python test_rl_learning.py               # the original test; RL agent loses to random
```

This is retained only to document the pre-fix state (see `RESEARCH_NOTES.md`). It is
NOT seeded and is not part of the research harness.

## 6. Live lab run (requires Docker; the sim numbers above do NOT)

**Everything in sections 1-5 reproduces without Docker** — it is pure simulation. The live
numbers in `LIVE_RESULTS.md` require the lab to be running, because every action issues a
real HTTP request to it.

### 6.1 Bring the lab up

```bash
cd art-ai/lab
docker compose config     # validate; all ports bind to 127.0.0.1
docker compose up -d
docker compose ps         # all six services should report (healthy)
```

One-time initialisation the harness performs automatically, but which you can do by hand:

```bash
curl http://127.0.0.1:3005/createdb              # VAmPI: populate its database
curl "http://127.0.0.1:3006/install.php?install=yes"   # bWAPP: install
# DVWA's database is created by the dvwa_foothold probe (POST /setup.php)
```

### 6.2 Health gate + dry run

```bash
cd art-ai/backend
python -m experiments.run_live --dry-run
```

`--dry-run` exercises every oracle and the whole loop on a tiny budget. If the lab is
down, the harness **exits with code 2 and a clear message** — it never fabricates results.

### 6.3 Full live run

```bash
python -m experiments.run_live --episodes 30 --measure-M 30 --finetune 25
```

Outputs to `backend/experiments/results/live/`:

| file | contents |
|---|---|
| `evidence-<run>.jsonl` | append-only, one record per step: state, action, host, every request (method/URL/status/latency/length), oracle verdict, evidence snippet |
| `run_meta-<run>.json` | git commit, config, image digests, resolved lab port map, excluded hosts |
| `report-<run>.json` | all metrics |
| `../measured_probs.json` | measured probe rates + Wilson CIs, with M and image digests |

### 6.4 Tests

```bash
python -m live.tests.test_live
```

Covers the scope chokepoint (rejects off-allowlist before any socket opens), a positive
and negative case per oracle, the shared AttackMDP/LiveAttackEnv interface contract, and
that the rng cannot influence a live verdict.

### 6.5 Scope

All live traffic is restricted to `127.0.0.1:3001-3006` by the `ALLOWED` constant in
`backend/live/http_client.py`. There is no flag, env var, or config key that widens it.
