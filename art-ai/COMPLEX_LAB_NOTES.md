# Complex-lab progress — Step A (stochastic defender) done; Step B next

This tracks the work from the gap analysis in `RESEARCH_GAP_ANALYSIS.md`: making the live
lab a genuine learning problem instead of a deterministic one.

## A — real defender layer: DONE

**Built:** `backend/live/defenses.py` — a stateful `DefensePolicy` with three mechanisms:
rate limiting (429 after N attempts/host), account lockout (after N consecutive failures),
and a probabilistic filter (403 with probability p). Wired into `LiveAttackEnv` behind a
`defense=` argument.

**Honesty invariants (verified):**
- The defender can only cause an attempt to **fail**; it never fabricates a success. A
  win still requires a real oracle verdict on a real response.
- Every block is logged as a defense event, so the induced uncertainty is **measured**,
  not assumed.
- The probabilistic filter uses a dedicated defender RNG, not the agent's. With the
  default policy (strength 0, all mechanisms off) the environment is exactly the old
  deterministic lab.

**Verification:**
- Unit tests (no lab needed): lockout trips after 3 failures and recovers; rate-limit
  trips after 4 attempts; the 0.45 filter measured 0.448 over 2000 draws and is
  reproducible under a fixed seed; strength 0 is inactive.
- **No regression:** the full live suite is `36 passed, 0 failed` with defenses off, and
  the simulator is untouched.

**What it demonstrates (lab up, 3 sim-equivalent hosts):**

| defender strength | greedy win rate | defender blocks (20 ep) |
|---|---|---|
| none (0) | 1.000 | 0 |
| mild (1) | 1.000 | 15 |
| medium (2) | 1.000 | 45 |
| strong (3) | **0.000** | 255 |

The deterministic lab (greedy always wins) becomes one where a naive, non-adaptive
policy **collapses under a strong defender**. Real failures are injected and logged.

## An honest limitation this surfaced (and why it motivates B)

The greedy curve is **binary** (1.0 until "strong", then 0.0), not graded. The reason is
real and worth stating: each capability oracle still succeeds **deterministically once the
defender lets the request through**, so a probabilistic filter alone does not grade the
difficulty — a greedy agent only needs one clear shot. What actually defeats greedy is
**lockout + rate-limit combined**, and it fails there specifically because **it cannot see
that a host is locked** and keeps hammering it until the step budget runs out.

That missing observation is the crux: the agent's state `(access, position, discovered)`
does not include defender state (which hosts are locked/rate-limited right now). This is
exactly the **partial observability** that the recent literature calls out as open
(dynamic networks where "paths become unavailable mid-episode"). It is the bridge to B.

## B — next steps (not yet done)

1. **Expose defender state in the observation** (which host is currently locked /
   rate-limited), turning this into a proper POMDP. Only then can a learned policy do
   what greedy cannot: back off before a lockout, and switch to an available host.
2. **Segmented topology** in docker-compose so lateral movement is real and a lockout
   makes a path temporarily unavailable.
3. **The headline experiment (RQ1):** learned policy vs greedy across defender strengths,
   with the extended observation. Hypothesis: with defender state observable, a learned
   agent that adapts (retry/backoff/switch) beats greedy at medium/strong, where the
   current greedy curve shows learning has something to win. Report the strengths where
   learning does **not** help, too.
4. **Re-ground the simulator** on the measured defender-induced probabilities and
   re-measure the sim-to-real transfer gap (RQ3).

Each step stays additive: defenses default off, simulator untouched, existing live
results reproducible.
