# RESEARCH_NOTES.md — Why the current ART-AI RL core is not research-grade

Scope: local simulated attack MDP + local vulnerable lab only. No external targets.
This document is written **before** changing code, per Step 0. Every claim below was
verified by reading the source and running `python test_rl_learning.py`.

## 0. Verified ground truth (the real starting point)

Running the shipped `backend/test_rl_learning.py` (seeded only by the wall clock):

```
Random Agent Win Rate: 49%
RL Agent Win Rate:      2%     <- trained agent loses badly to random
Q-table size:           9 entries (never grows past ep. 50)
```

The learned policy printed by the test:

```
State: internal
    lateral_movement_attempt: Q=90.89   <- chosen greedily, but it is a NO-OP here
    public_access_attempt:    Q=81.86
    sql_injection_attempt:    Q=79.26
State: none
    public_access_attempt:    Q=73.65
State: public
    token_reuse_attempt:      Q=64.00
```

So the "optimized" agent is worse than random and its Q-table has ~9 entries. This
matches the prompt's premise (it is even a bit worse than the ~5% quoted). The problem
is the **environment, state representation, and reward** — not the amount of training.

## 1. The state is the access level, so there is nothing to learn

`test_rl_learning.py` builds the state as `state = f"{env.current_access_level.value}"`.
That is 4 possible states: `none | public | internal | admin`. `admin` is terminal, so
the agent effectively has **3 non-terminal states**. `EnvironmentState` already tracks
`discovered_services`, `discovered_vulnerabilities`, `visited_components`, and hint
fields (`env.py:37-52`) but **none of them enter the state key**. A tabular policy over
3 states cannot express a strategy; the "9-entry Q-table" is the direct symptom.

**Consequence for bootstrapping:** because state = access level, a `lateral_movement`
that "succeeds" while already at `internal` produces `next_state == state == "internal"`.
The Q-learning target then bootstraps off `max_a Q(internal, a)`, which includes the very
action being updated. This is a positive self-loop and Q(internal, lateral_movement)
diverges upward (90.89 above) — a textbook over-estimation from a self-transition with
positive reward.

## 2. The applicability check lets non-escalating actions fire everywhere

`AttackEngine._is_action_applicable` (`attack_engine.py:167-170`):

```python
level_actions = self.SUCCESS_PROBABILITIES.get(current_level, {})
return action in level_actions or action in self.ACCESS_ESCALATIONS
```

`LATERAL_MOVEMENT_ATTEMPT` is a key in `ACCESS_ESCALATIONS`, so the `or` branch makes it
"applicable" at **every** access level, including `internal` where its escalation target
is also `internal`. It therefore returns `success=True` as a no-op, is rewarded, and
never advances access. `get_available_actions` also only ever offers escalation actions
from PUBLIC upward, but the applicability short-circuit is what enables the degenerate
loop. The single action that reaches ADMIN — `PRIVILEGE_ESCALATION_ATTEMPT` (0.2 success
at `internal`) — is dominated by the higher-frequency, higher-reward `lateral_movement`
no-op, so the greedy policy never escalates to ADMIN.

## 3. Reward hacking: the hint bonus dwarfs the task reward

`OptimizedQLearningAgent.calculate_reward` (`ai_agent_optimized.py:356-362`) and the
non-optimized `ai_agent.py:205-209` add **+96..+120** (optimized) / **+100** (base) when
the action matches the Exploit-DB hint. Reaching ADMIN — the actual objective — is worth
only `15 * 2^level_gain` ≈ 15–60. So "match the hint string" is worth ~2–8x more than
winning the episode. Any agent that can trigger the hint will prefer hint-matching over
task completion. This is reward hacking by construction and makes the reward signal
scientifically meaningless.

Note: in `test_rl_learning.py` the `ExploitLibrarian` is never wired into `env.reset()`,
so `hint_available` stays 0 and the bonus does **not** fire in that specific test. The
degenerate loop observed there is caused solely by §1–§2. The hint hacking is a latent
defect that dominates the **main application** path (`main.py`), where the librarian is
active. Both must be fixed for the reward to be trustworthy either way.

## 4. The hint "confidence" and success probabilities are hardcoded magic numbers

- `ai/knowledge.py` runs in `demo_mode` with hint confidences hardcoded as literals
  (0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50 — `knowledge.py:90-229`). These feed
  directly into the reward scaling. No CVSS/EPSS/Exploit-DB basis.
- `AttackEngine.SUCCESS_PROBABILITIES` (`attack_engine.py:45-66`) are hand-picked
  constants (0.3, 0.1, 0.15, ...). `_get_success_probability` then multiplies by a flat
  `1.1` "learning curve" fudge (`attack_engine.py:182`) with no justification. There is
  no link to any real signal (CVSS exploitability sub-score, EPSS, Exploit-DB verified
  flag, patch age).

## 5. Double-Q / replay / Boltzmann / adaptive-LR are enabled but unvalidated (and partly harmful)

`ai_agent_optimized.py` layers on experience replay, double-Q, N-step buffer, Boltzmann
exploration, and adaptive LR — none of which is measured against an ablation. Several
actively hurt here:

- **Experience replay over a 3-state MDP** repeatedly re-samples the same self-loop
  transition, amplifying the §1 over-estimation.
- **Adaptive LR** raises LR to 0.3 whenever recent reward > 0 (`ai_agent_optimized.py:428-435`).
  Because the self-loop keeps reward positive, LR is pinned high, accelerating divergence.
- **Double-Q target network** is copied as a hard overwrite every 10 updates
  (`_update_target_network`), which does not decorrelate anything meaningfully at this
  scale.
- **Boltzmann temperature** starts at 1.0 with Q-values in the tens/hundreds, so softmax
  is effectively greedy from early on — it locks in the bad self-loop.

None of this is wrong to *have*, but claiming it "helps" without an ablation is not
research-grade.

## 6. No experimental rigor

- **No seeding.** `random` is never seeded, so no run is reproducible.
- **No baselines beyond random.** No greedy-by-signal baseline, and critically **no
  value-iteration optimal policy** to bound the achievable return (the MDP is tiny and
  fully specified, so the optimum is computable exactly — that is the ceiling to report a
  gap against).
- **N = 1.** A single train/test run with no independent repeats, no confidence intervals.
- **Win-rate defined loosely.** The test counts a "win" only if ADMIN is reached before
  `max_steps` or a block; steps-to-admin, regret, and sample efficiency are not measured.
- **No logged artifacts.** No CSV/JSON metrics, no learning curves, no config/seed/commit
  record. Nothing can be regenerated or audited.

## 7. Summary of what must change (drives Steps 2–5)

1. **State encoding**: include access level + sorted discovered services/vulns + visited
   components + host position, documented and hashed into a stable key.
2. **Dynamics**: replace `SUCCESS_PROBABILITIES` and the hint confidences with values
   derived from cited signals (CVSS exploitability sub-score / EPSS / Exploit-DB verified
   / patch age), or clearly label any residual constant with its basis.
3. **Reward**: remove the hint bonus from the base reward; keep rewards bounded and
   justified; measure the hint's value only as an ablation.
4. **Fix the degenerate policy**: make non-escalating actions non-applicable where they
   cannot progress (or make self-loops non-positive), and confirm the trained agent
   provably beats random and approaches the value-iteration optimum.
5. **Harness**: seeds, N >= 20 runs, mean +- 95% CI, baselines (random, greedy-by-signal,
   value-iteration optimum), metrics (win rate, steps-to-admin, sample efficiency,
   regret), PNG curves + CSV/JSON, and ablations (double-Q, replay, Boltzmann vs
   epsilon-greedy, hint on/off), all behind one `python -m experiments.run_all`.
