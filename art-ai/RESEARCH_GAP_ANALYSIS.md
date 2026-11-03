# Research gap analysis and proposed contribution

Purpose: locate a genuine, unoccupied niche by comparing the recent literature, then
define a contribution that filling it with the A-then-B lab would produce. Written so
the novelty claim is defensible and the related-work section is honest.

Date of literature review: 2026-10 (search results current as of this date).

---

## 1. The landscape, by what each line of work actually does

| Work | Environment | Stochastic? | Defender modelled? | Side | Live services? | Evidence per step? |
|---|---|---|---|---|---|---|
| NASim | simulated | invented probabilities | no | red | no | no |
| CyberBattleSim (Microsoft) | simulated | invented probabilities | partial | red | no | no |
| CybORG / CAGE-4 | simulated | yes (noisy monitoring, FP/FN) | yes | mostly **blue** | no | no |
| PenGym (Comp. & Security 2024) | **emulated/real actions** | **deliberately avoided** | no | red | yes (emulated hosts) | no |
| GAP / "Mind the Gap" (2024) | real VMs + synthetic sims | via domain randomization | no | red | yes | no |
| CRLF (ESORICS 2025) | Sim2Real IT/OT | partial | no | red | partial | no |
| POMDP-pentest (arXiv 2509.20008, 2025) | simulated | yes (partial observability) | no | red | no | no |
| **This project (ART-AI)** | **live Docker lab** | currently **no (p=1.0)** | **not yet** | **red** | **yes** | **yes (evidence log)** |

Sources: [PenGym](https://www.sciencedirect.com/science/article/pii/S0167404824004450),
[GAP](https://arxiv.org/abs/2412.04078),
[CRLF](https://link.springer.com/chapter/10.1007/978-3-032-16089-8_27),
[CybORG/CAGE hierarchical MARL](https://arxiv.org/pdf/2410.17351),
[robust POMDP pentest](https://arxiv.org/pdf/2509.20008),
[CAGE red-team framework](https://arxiv.org/html/2605.17075v1),
[Beyond Rewards in RL for Cyber Defence](https://arxiv.org/pdf/2602.04809).

## 2. What the papers explicitly leave open (quoted findings)

1. **PenGym avoids stochasticity rather than modelling it.** It runs real actions
   specifically to escape simulators' "predefined constants and probabilistic values,"
   and notes that as a system grows "these probabilistic factors may affect the learning
   process of the agents in unknown ways." So a *live* environment that **models
   defender-induced uncertainty on purpose** is not what PenGym does.
2. **Red-team RL collapses under sparse reward.** The 2026 CAGE red-team framework
   reports that "RL alone collapses to a degenerate policy and cannot find meaningful
   attack progression under sparse rewards," and that kill-chain reward shaping "helps
   training but risks reward hacking." This is *precisely* the failure mode this project
   already hit and fixed (the self-loop; the +100 hint bonus). It is a named open problem.
3. **Dynamic/stochastic environments are future work.** The robust-POMDP pentest paper
   lists dynamic networks — "hosts shutting down, firewall rules being updated, or paths
   becoming unavailable mid-episode" — as future work. No one does this with **live**
   services.
4. **CybORG is stochastic but simulated and mostly defensive.** Its red-team coverage is
   thin, and it is not a real target.
5. **No one grounds the stochasticity in measurement.** Simulators invent p; PenGym
   avoids p; nobody *measures* the real per-action success distribution under a defender
   and feeds it back into the model.

## 3. The gap, stated precisely

> **There is no penetration-testing RL environment that is simultaneously (a) live —
> real services, real requests; (b) stochastic because of a real, modelled defender
> (rate limiting, lockout, probabilistic blocking) rather than an invented constant;
> (c) partially observable — services, versions and credentials must be discovered;
> and (d) evidence-grounded — every reward is tied to a logged, verifiable observation.**

Each existing system has some of these. None has all four. The intersection is empty,
and it is exactly where the open problems in §2 live.

## 4. Proposed contribution

**An evidence-grounded, stochastic, partially-observable *live* red-team environment,
and a study of when learning actually beats a heuristic on it.**

Concretely, extend the current live lab along two axes:

- **A — a real defender layer** that injects *measurable* uncertainty: per-host rate
  limiting, account lockout after repeated failures, and a probabilistic block on
  injection attempts. The defender is a real stateful component; its block/lockout
  events are logged, so the stochasticity is **observed, not assumed**. Crucially it can
  only ever cause an action to *fail* — it never fabricates a success — so the project's
  "no fabricated success" rule is preserved. This converts the degenerate p=1.0 MDP into
  one where the agent must learn to retry, back off before lockout, and prefer currently
  reliable hosts/techniques.

- **B — a segmented topology** so lateral movement is real: internal hosts are reachable
  only after compromising a reachable one, and a lockout can make a path *temporarily
  unavailable mid-episode* — directly instantiating the "dynamic network" future work of
  the POMDP paper, but live.

The research questions this enables, none of which the current deterministic lab can ask:

1. On a live, stochastic, partially-observable red-team task, **does a learned policy
   beat a strong heuristic** — and by how much, as a function of defender strength? (On
   the deterministic lab they were tied; the hypothesis is that uncertainty is what makes
   learning pay.)
2. **Does the degenerate-collapse failure** reported for red-team RL under sparse reward
   reproduce here, and does evidence-grounded reward shaping mitigate it without the
   reward-hacking the CAGE paper warns about?
3. **How large is the sim-to-real gap** once the simulator must also model the defender —
   i.e., does grounding the simulator in *measured* defender-induced probabilities close
   the transfer gap that the current (deterministic) grounding leaves?

## 5. Why this is honest about novelty

- The headline "RL agent attacks a real lab with zero-shot transfer" is **not** claimed
  as new — GAP and PenGym did it first (see `WHAT_WE_DID_SIMPLE.md` and the deck's
  positioning slide).
- The novel element is the **combination** (live + modelled-defender stochasticity +
  partial observability + per-step evidence grounding) and the **study** it enables of
  the sparse-reward collapse that the 2026 CAGE red-team work names as open.
- It is a focused, student-scale contribution — a testbed and an empirical study — not a
  new algorithm. That framing is defensible; a grander claim would not be.

## 6. Build order

1. **A — defender layer** (`backend/live/defenses.py`), behind a flag so existing
   deterministic results in `LIVE_RESULTS.md` still reproduce unchanged.
2. Re-measure per-action success *under* the defender, with Wilson intervals, to confirm
   p is now < 1 and genuinely uncertain.
3. Re-run learned-vs-heuristic across defender strengths; report where learning starts to
   win (research question 1).
4. **B — segmented topology** in `docker-compose`, with a reachability map the live env
   enforces; add mid-episode path loss via lockout.
5. Ground the simulator in the measured defender probabilities and re-measure the
   transfer gap (research question 3).
6. Write `COMPLEX_LAB_RESULTS.md` honestly, including the configurations where learning
   did **not** help.

Each step is additive and reversible; none regresses the current simulator or the
existing live results.
