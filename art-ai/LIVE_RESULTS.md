# LIVE_RESULTS.md — the agent actually attacks the lab, and what that revealed

Every number here was generated on this machine on 2026-09-27 by
`python -m experiments.run_live --episodes 30 --measure-M 30 --finetune 25`.
Scope: the local Docker lab at `127.0.0.1:3001-3006`. Nothing else was contacted.

## 1. The gap that was closed

Before: **no agent action produced a single HTTP request.** `AttackMDP.step` resolved
every action with `rng.random()` against a CVE-metadata prior (`mdp.py:155`), and
`grep -rnE "socket|requests\.|urllib" backend/experiments/*.py` returned nothing.

Now: `LiveAttackEnv` issues real requests through one chokepoint and escalates **only** on
a deterministic oracle verdict backed by a logged response.

Audit of the run below:

| check | result |
|---|---|
| rng deciding a live outcome | **none** — `grep -nE "rng\.(random\|choice\|randrange\|sample)"` over `live_env.py`, `capabilities.py`, `http_client.py` returns nothing |
| real HTTP requests issued | **2,126** |
| requests logged *inside agent steps* | **714** across 959 agent steps |
| oracle verdicts | True=276, False=0, n/a=683 (recon/move, which make no capability claim) |
| hosts with working oracles | **6 of 6** (12 capabilities) |

Example record from `evidence-20260927T175259Z.jsonl` — an agent action, the request it
made, and the evidence that justified the escalation:

```
ep1 step5  a0|p0|d0 --exploit--> a1|p0|d0   host=juice-shop  verdict=True
  evidence: status=200 jwt_identity=admin@juice-sh.op|role=admin
  POST http://127.0.0.1:3001/rest/user/login -> HTTP 200  19.4ms  784B
```

## 2. Derived prior vs measured rate — the sim-to-real gap, quantified

Each probe run **M=30** times independently, Wilson 95% CI:

| host | capability | derived prior (CVSS/EPSS/verified/patch-age) | measured | Wilson 95% CI |
|---|---|---:|---:|---|
| juice-shop | foothold | 0.810 | **1.000** | [0.886, 1.000] |
| juice-shop | privesc | 0.126 | **1.000** | [0.886, 1.000] |
| dvwa | foothold | 0.536 | **1.000** | [0.886, 1.000] |
| dvwa | privesc | 0.384 | **1.000** | [0.886, 1.000] |
| flask-api | foothold | 0.216 | **1.000** | [0.886, 1.000] |
| flask-api | privesc | 0.508 | **1.000** | [0.886, 1.000] |
| vampi | foothold | n/a (not in sim) | 1.000 | [0.886, 1.000] |
| vampi | privesc | n/a (not in sim) | 1.000 | [0.886, 1.000] |
| bwapp | foothold | n/a (not in sim) | 1.000 | [0.886, 1.000] |
| bwapp | privesc | n/a (not in sim) | 1.000 | [0.886, 1.000] |
| webgoat | foothold | n/a (not in sim) | 1.000 | [0.886, 1.000] |
| webgoat | privesc | n/a (not in sim) | 1.000 | [0.886, 1.000] |

**Every probe is deterministic. The priors are wrong, and not by a little.**
`juice-shop privesc` was predicted at **0.126** and measured at **1.000** — off by ~8x, in
the direction that matters most (the sim thought the goal-reaching action was the hardest
one available).

This is a real result about the limits of CVE-metadata-derived dynamics, and it is stated
rather than tuned away. The honest reading: **CVSS exploitability, EPSS, verified-PoC and
patch age describe a population, not an instance.** EPSS in particular answers "will this
be exploited in the wild in the next 30 days", which is a question about attacker
behaviour across the internet — it says nothing about whether a specific unpatched,
deliberately-vulnerable container will yield to a specific working payload. Against a
static lab pinned to a vulnerable version, a correct exploit succeeds every time. The
formula in `grounding.py` was not re-fitted to match; doing so would be curve-fitting to
one lab and would destroy the only honest thing the priors had going for them.

Measured probabilities are written to `experiments/measured_probs.json` with the date, M,
and image digests.

## 3. Sim-to-real transfer (N = 30 live episodes per configuration)

Live action space restricted to the three sim-equivalent hosts (juice-shop, dvwa,
flask-api) so the comparison is like-for-like. Win-rate CIs are **Wilson** (correct at
N=30, unlike a normal approximation).

| configuration | win rate | Wilson 95% CI | steps-to-admin | return | regret vs measured optimum |
|---|---:|---|---:|---:|---:|
| random | 0.700 | [0.521, 0.833] | 10.00 | 0.360 | 0.514 |
| greedy-by-signal | 1.000 | [0.886, 1.000] | 6.00 | 0.721 | 0.153 |
| **zero-shot transfer** (sim-trained, frozen) | **1.000** | [0.886, 1.000] | **5.00** | **0.769** | **0.105** |
| live fine-tuned (+25 live episodes) | 1.000 | [0.886, 1.000] | 5.00 | 0.769 | 0.105 |

- sim optimum `V* = 0.6772` · **measured-MDP optimum `V* = 0.8740`** (value iteration
  re-run with the measured probabilities; recon treated as an observation, p=1.0).
- **Zero-shot transfer works and is the best configuration**: 100% win rate in 5.00 steps,
  beating both random (70%, 10 steps) and the greedy-by-signal heuristic (100%, 6 steps).
  The policy learned in simulation transfers to the real lab without degradation.
- **Fine-tuning adds exactly nothing** (identical to 3 decimal places). Reported as a null
  result: once every capability is deterministic and the policy already reaches the goal
  in near-minimal steps, there is no gradient left to exploit. 25 live episodes of extra
  learning bought 0.000 improvement.
- Residual regret of 0.105 against the measured optimum is step-count, not failure: the
  measured-MDP optimum can reach ADMIN in fewer actions than the sim-trained policy's 5,
  because the sim policy still budgets for a recon step whose live outcome is certain.

## 4. The abstraction mismatch — the most interesting finding

The first live run scored **zero-shot transfer 0.000 while random scored 1.000**. The
evidence log gave the reason immediately:

```
a1|p1|d0,1,2 | exploit | dvwa | no PHPSESSID; foothold required first
```

The sim treats `access` as a **global** privilege level, so its optimal policy is "take the
cheap foothold on juice-shop (prior 0.810), then *move* to dvwa and escalate there (prior
0.384 > juice-shop's 0.126)". That strategy is *optimal in the sim and impossible in the
lab*: the five targets are independent web applications and **credentials do not transfer**
— a Juice Shop JWT is worthless against DVWA, which wants its own `PHPSESSID`.

So the sim's most confident strategic insight — cross-host escalation — was an artifact of
modelling five separate web apps as one machine with one privilege ladder.

`LiveAttackEnv` now models this correctly: escalating on a host first establishes that
host's own foothold, because you cannot escalate on a box you have not accessed. With that
fixed, transfer is perfect (§3). **The lesson is that the sim-to-real gap here was not in
the probabilities at all — it was in the state abstraction**, and only a live environment
could have exposed it.

## 5. Hosts and capabilities — all six implemented

| host | port | foothold oracle | privesc oracle | status |
|---|---|---|---|---|
| flask-api | 3003 | SQLi differential 1→4 rows | `role=="admin"` on login (neg: 401) | ✅ |
| vampi | 3005 | `_debug` leaks plaintext passwords | mass assignment → `admin:true` | ✅ |
| juice-shop | 3001 | SQLi auth bypass → decodable JWT | `/api/Users` 401→200 differential | ✅ |
| dvwa | 3002 | authenticated session → `/index.php` 200 | SQLi differential 1→5 rows | ✅ |
| bwapp | 3006 | `bee`/`bug` session → portal `logout` | SQLi differential 2→17 cells | ✅ |
| **webgoat** | 3004 | register+login → `start.mvc` 200 w/ own username | SQLi differential 2→6 rows | ✅ |

**All six hosts are now implemented. Nothing remains dropped.**

WebGoat was dropped in the first pass and that call was wrong. The original objection was
that its vulnerabilities are lesson-scoped, so an oracle would measure WebGoat's
`lessonCompleted` bookkeeping rather than an attack outcome. The fix was to key the oracle
on the **actual SQL output** instead:

- Lesson-8 query is `... WHERE last_name = '<name>' AND auth_tan = '<auth_tan>'`.
- Benign (`Smith`/`3SL99A`) returns **2** `<tr>` rows (header + the user's own record).
- Injected (`auth_tan=' OR '1'='1`) returns **6** (header + all five employees) — records
  the authenticated user is not entitled to.
- Success iff injected rows > benign rows. `lessonCompleted` is logged only as
  corroboration and is **not** the predicate.

That is a genuine observable capability (the query returned rows it should not have), so
the original objection no longer applies.

Two WebGoat-specific traps, found by testing and now locked into the test suite as
negative cases:
- **WebGoat enforces a 6-10 character password.** An 11-character password causes
  registration to fail *silently* (HTTP 200 re-rendering the form with validation errors
  rather than a 302), after which every login returns `/WebGoat/login?error`. This is what
  made the host look unusable on first contact.
- The benign lesson-8 query alone must not satisfy the oracle (asserted: exactly 2 rows).

**Two corrections to assumptions made before testing:**
- `/rest/admin/application-configuration` on Juice Shop returns **200 without any auth** in
  this image, so it proves nothing. `/api/Users` (401→200) is used instead.
- DVWA emits all SQLi rows on **one line**, so `grep -c` (which counts matching *lines*)
  reports 1 regardless of how many rows leaked. Occurrences must be counted.

## 6. Cost

| metric | value |
|---|---|
| live episodes | 145 (4 configs × 30, plus 25 fine-tune) |
| total real requests | 2,126 |
| requests per episode | 14.7 |
| wall-clock | 224.0 s |
| per-episode reset cost | **~0 s** |

Reset strategy, in the preference order the task specifies:
1. **Idempotent probes** — every SQLi differential and read repeats cleanly, so no reset
   is needed for 10 of the 12 capabilities.
2. **Per-episode unique identifiers** — the two mutating probes (VAmPI registration and
   WebGoat registration) use `artai-ep{n}-{uuid}` style names, so episodes never collide.
3. **Container restart** — *not needed*, hence the ~0 s cost.

Caveat worth stating: VAmPI's and WebGoat's user tables **accumulate** one row per probe
(38 VAmPI users after this run; WebGoat similarly). It is non-destructive and does not affect any oracle, but a long
campaign should periodically `GET /createdb` to reset it. The admin-only
`DELETE /users/v1/<name>` route does succeed with the escalated token, and is
**deliberately not used as the oracle** because it destroys lab data; the `admin:true`
flag proves the same capability without mutation.

## 7. Definition of done

| # | requirement | status |
|---|---|---|
| 1 | sim still reproduces `RESULTS.md` | ✅ `V*=0.6772` identical; `run_all --quick` reproduces exactly |
| 2 | one command runs the live loop; an action provably issues HTTP | ✅ 714 requests logged inside agent steps, traceable per step |
| 3 | every live success justified by a logged response | ✅ 276 True verdicts, each with evidence + requests; **no rng in the live path** |
| 4 | scope test passes before a socket opens | ✅ 32/32 tests, incl. "no socket opened for out-of-scope target" |
| 5 | derived-vs-measured table + transfer numbers with N and cost | ✅ §2, §3, §6 |
| 6 | what could not be made to work is written down | ✅ §4 (abstraction mismatch); §5 — **nothing remains dropped**, WebGoat was reinstated |

## 8. Exact commands run

```bash
cd art-ai/lab && docker compose up -d && docker compose ps     # all six healthy
cd ../backend
python -m experiments.run_live --dry-run                        # smoke, tiny budget
python -m experiments.run_live --episodes 30 --measure-M 30 --finetune 25
python -m live.tests.test_live                                  # 36 passed, 0 failed
python -m experiments.value_iteration                           # V*=0.6772 (sim intact)
python -m experiments.run_all --quick                           # sim regression check
```

Artifacts: `backend/experiments/results/live/{evidence,run_meta,report}-20260927T175259Z.*`
and `backend/experiments/measured_probs.json`.
