# Prompt — Convert ART-AI from demo to research-grade (paste into Claude Code)

> Paste everything below the line into Claude Code, run from the `art-ai/` directory.
> It is scoped to the **local simulated MDP + local vulnerable lab + evaluation rigor** only.
> It does **not** ask for anything that targets systems you don't own.

---

You are working on `art-ai/`, an academic reinforcement-learning project for autonomous
security testing against a **local, self-hosted vulnerable lab** (OWASP Juice Shop, DVWA,
and a local Flask app) and an **abstract simulated attack MDP**. All work stays inside this
sandbox — no external or third-party targets, ever. Treat this as a research-reproducibility
and RL-correctness task, not a demo-polish task.

## Ground truth you must start from (verify it yourself)
Run `backend/test_rl_learning.py`. The current "optimized" agent **loses to a random agent**
(≈5% win rate vs ≈38% random) and its Q-table has only ~10 entries. That is the real starting
point. The project is currently a template with a broken RL core, not research-grade. Your job
is to fix the science, not to make the numbers look nice.

## Step 0 — Analyze and write findings first
Read `backend/ai_agent.py`, `ai_agent_optimized.py`, `attack_engine.py`, `env.py`,
`decision_maker.py`, `exploit_ml_models.py`, `test_rl_learning.py`. Write a short
`RESEARCH_NOTES.md` listing every reason the current setup is not research-grade before
changing code. Do not skip this.

## Step 1 — Create purpose-built subagents
Define these subagents (in `.claude/agents/`) and use them for the matching work:
1. **rl-engineer** — RL algorithm correctness, environment/MDP design, reward design.
2. **eval-scientist** — experiment harness, seeds, baselines, statistics, plots, ablations.
3. **lab-infra** — Docker vulnerable labs, health checks, grounding the MDP in real lab/CVE data.
4. **data-grounding** — replace hardcoded probabilities with data-derived ones (CVSS/EPSS/Exploit-DB).
5. **reproducibility** — config files, logged metrics, deterministic runs, a `make reproduce` path.
Give each a tight system prompt and only the tools it needs.

## Step 2 — Fix the RL science (this is the core deliverable)
The accuracy problem is **not** solved by "more training." The environment and reward are the
problem. Do all of these:

- **State space:** the state is currently just the access-level string (4 states). Expand it to
  include discovered services, discovered vulnerabilities, visited components, and per-host
  position, so the policy has something real to learn. Document the state encoding.
- **Data-grounded dynamics:** replace the magic numbers in `AttackEngine.SUCCESS_PROBABILITIES`
  with probabilities derived from real signals (CVSS exploitability sub-score, EPSS where
  available, Exploit-DB verified flag, patch age). No hand-tuned constants without a cited basis.
- **Reward hacking:** the `+100/+120` hint bonus dominates the signal. Remove it from the base
  reward and instead measure the hint's value as an **ablation** (agent with vs without the
  Exploit-DB "librarian" hint). Keep rewards bounded and justified.
- **Fix the degenerate policy:** the optimized agent learns to loop `lateral_movement_attempt`
  and never reaches ADMIN. Diagnose why (experience replay over-reinforcement, applicability
  check letting non-escalating actions fire, Boltzmann/adaptive-LR instability) and fix it so
  the trained agent **provably beats random and approaches the value-iteration optimum**.

## Step 3 — Build a real evaluation harness
Create `backend/experiments/`:
- Fixed seeds; **N ≥ 20 independent runs** per configuration; report **mean ± 95% CI**.
- Baselines to compare against: (a) random, (b) greedy-by-CVSS, (c) **value-iteration optimal
  policy** for the tabular MDP (this is the ceiling — report the gap to it).
- Metrics: win rate, steps-to-admin, sample efficiency (episodes to threshold), regret.
- Learning curves saved as PNG + raw metrics saved as CSV/JSON.
- **Ablations:** double-Q on/off, experience replay on/off, Boltzmann vs ε-greedy, hint on/off.
  A claim like "double-Q helps" must be backed by an ablation number, not an assertion.
- A single `python -m experiments.run_all` that regenerates every number and plot.

## Step 4 — More labs, and connect them to the MDP
Extend `lab/docker-compose.yml` with more authorized local targets (e.g. WebGoat, VAmPI,
bWAPP, Juice Shop already present). Add health checks. Then **close the loop**: have `lab-infra`
+ `data-grounding` derive the MDP's transition probabilities from what the labs actually expose,
so the simulation is grounded in the real lab rather than invented constants. Keep everything
bound to localhost.

## Step 5 — Reproducibility
- One config file per experiment (YAML/JSON) with every hyperparameter.
- Log the seed, git commit, and config with each result.
- Add a `requirements` freeze and a `REPRODUCE.md` with exact commands.

## Step 6 — Run it and report honestly
Run the full harness. Produce `RESULTS.md` with a before/after table: random vs old "optimized"
agent vs fixed agent vs value-iteration optimum, with CIs. If a technique doesn't help, say so.
Do not report a number you did not generate. End with the exact commands you ran.

Constraints: stay inside the local lab and simulation; no third-party targets; no
detection-evasion or real-world weaponization; this is reproducible academic RL research.
