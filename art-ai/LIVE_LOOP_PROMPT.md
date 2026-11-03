# Prompt — Close the loop: wire the RL agent to the real lab (paste into Claude Code)

> Paste everything below the line into Claude Code, run from the `art-ai/` directory.
> Scope: **the local Docker lab on 127.0.0.1:3001-3006 only.** No external or third-party
> targets, ever. This is the successor to `RESEARCH_GRADE_PROMPT.md`, which fixed the
> simulation. This one makes the agent actually attack.

---

You are working on `art-ai/`, an academic RL project for autonomous security testing
against a **local, self-hosted vulnerable lab**. The previous round of work
(`RESEARCH_NOTES.md`, `RESULTS.md`, `backend/experiments/`) fixed the RL science: the
agent now reaches a 96% win rate and 93% of the value-iteration optimum on a grounded,
fully-specified tabular MDP. That work is correct and must not be regressed.

## The gap you are closing

The scanner is real: `backend/recon.py` opens actual TCP connections and grabs actual
banners. The **agent is not**. `experiments/mdp.py::AttackMDP.step` resolves every action
by `rng.random()` against a probability from `experiments/grounding.py`, which is derived
from CVE metadata — published signals, but still **priors, not observations**. No action
the agent takes produces a single HTTP request. `exploit` on `flask-api` is a coin flip,
not a POST to `127.0.0.1:3003`.

Your job: build a **live environment** that satisfies the same interface as `AttackMDP`,
where every action issues a real request against the lab and every reward is derived from
the actual response. Then measure the sim-to-real gap honestly.

## Non-negotiables

**Scope.** Exactly one chokepoint function performs every outbound request. It hard-fails
on anything that is not `127.0.0.1` (or `localhost`) on a port in `{3001,3002,3003,3004,
3005,3006}`. No env var, config key, or CLI flag may widen it — if a target is not in the
allowlist constant, the code raises. Write a test that asserts a request to a public host
raises before any socket is opened.

**No destructive actions.** Read, authenticate, inject to *observe*, escalate to *observe*.
No deletion of lab data beyond what an episode reset recreates, no fork bombs, no resource
exhaustion, no container escape attempts, no persistence. The lab is a measurement
instrument; keep it working.

**No fabricated success.** If an oracle cannot be made reliable for a host, drop that host
from the live action space and say so in writing. A success the agent did not actually
demonstrate is worse than a missing host. Never fall back to a probability roll when a
request fails — a failed request is a failed action, or an error the episode records.

**Do not touch the sim.** `experiments/mdp.py`, `grounding.py`, `value_iteration.py`,
`agents.py` keep working exactly as they do now; `python -m experiments.run_all` must
still reproduce the numbers in `RESULTS.md`. The live env is additive.

## Step 0 — Verify the gap, then write it down

Read `backend/experiments/{mdp.py,grounding.py,agents.py,run_all.py,config.yaml}`,
`backend/recon.py`, `backend/attack_engine.py`, `lab/docker-compose.yml`, and
`lab/vulnerable-api/app.py`. Confirm for yourself that no code path from an agent action
reaches a socket. Bring the lab up (`cd lab && docker compose up -d && docker compose ps`)
and confirm which services are actually healthy on this machine — record the real list,
because some of these images are large and one may not come up.

Write `LIVE_NOTES.md` **before changing code**: the exact call chain that proves the agent
is simulated, which lab services are live here, and for each service the concrete
endpoints you intend to use as capability probes. Do not skip this.

## Step 1 — The request layer (`backend/live/http_client.py`)

- `ALLOWED = {("127.0.0.1", p) for p in (3001, ..., 3006)}` as a module constant.
- `def request(method, url, **kw) -> Response` — the single chokepoint. Parses the URL,
  asserts host+port against `ALLOWED`, raises `ScopeViolation` otherwise.
- Per-request timeout (default 8s), bounded retries (2) with backoff, a global rate limit
  (configurable, default ~10 req/s) so a training loop cannot melt the containers.
- Every request returns a record: method, URL, request headers/body (redacted where
  sensible), status, response length, latency ms, and a truncated body snippet.
- Session/cookie handling per episode, because DVWA and Juice Shop are stateful.

## Step 2 — Capability probes with real oracles (`backend/live/capabilities.py`)

This is the heart of the work. For each host define two capabilities — **foothold**
(NONE→USER) and **privesc** (USER→ADMIN) — as named functions that issue real requests
and return `(bool success, str evidence)`. Each oracle needs a comment stating *what
evidence proves the capability*, and must be a deterministic predicate on the response,
not a heuristic guess.

Starting points verified in the source — **check each one against the live service, and
correct or replace anything that does not hold**:

- **`flask-api` (3003)** — `lab/vulnerable-api/app.py` is in-repo, so its behavior is
  fully known. `GET /api/users?id=1` interpolates the id straight into SQL, so
  `id=1 OR 1=1` returns *all* rows: a differential oracle (row count, plus the presence of
  the `admin` row) is exact. `POST /api/login` with `admin`/`admin123` returns
  `{"role":"admin"}` — that response is the privesc evidence. `GET /api/file?name=` reads
  `/tmp/<name>` with no validation. This host should be your first working end-to-end path.
- **`juice-shop` (3001)** — `POST /rest/user/login` with
  `{"email":"' OR 1=1--","password":"x"}` returns an `authentication.token` JWT on the SQLi
  bypass. Foothold oracle = a JWT is present and decodes. Privesc oracle = that token opens
  an admin-only route (e.g. `/rest/admin/application-configuration`, or a basket ID
  belonging to another user) — verify which route actually gates on role in the running
  image.
- **`vampi` (3005)** — started with `vulnerable=1`. `GET /users/v1/_debug` dumps all users
  including passwords; `POST /users/v1/register` accepts an `admin` field (mass
  assignment); `POST /users/v1/login` returns a JWT. Oracle = the token from a
  self-registered account reaches an admin-only endpoint.
- **`dvwa` (3002)** — needs a real login (`admin`/`password`), a `PHPSESSID` + `security`
  cookie, and a per-form `user_token` CSRF value scraped from the page. Expect setup work
  (the image may require a DB-init click-through on first boot). Its SQLi and command-exec
  pages are genuine capability probes once you are in.
- **`webgoat` (3004)** and **`bwapp` (3006)** — attempt these last. If authentication or
  lesson state makes a reliable oracle impractical, **drop them and document why** rather
  than shipping a flaky probe.

For each capability also record a **baseline response** (benign request) so success is a
measured difference, not an absolute guess.

## Step 3 — The live environment (`backend/experiments/live_env.py`)

`LiveAttackEnv` must be **interface-compatible** with `AttackMDP` so every existing agent
in `experiments/agents.py` runs against it unchanged:

- Same `State = (access, position, discovered)` tuple and the same `state_key()`.
- Same action set: `recon`, `exploit`, `move_i`.
- Same reward contract: `-STEP_COST` per action, `+GOAL_REWARD` on the transition into
  ADMIN. Bounded, unchanged, no new bonus terms.
- `reset() -> State`, `step(s, a, rng) -> (ns, r, done)`.
- **No `transitions()`.** A live env has no enumerable kernel; raise
  `NotImplementedError` with a comment saying value iteration stays on the sim, which is
  precisely why the sim still exists.
- `rng` is accepted for signature compatibility and used only for tie-breaking — it must
  not decide any outcome. Assert this in a test: two runs with different seeds over the
  same deterministic action sequence produce the same capability verdicts.
- `exploit` calls the foothold or privesc probe for the host at `position` depending on
  `access`, and escalates only on a `True` oracle verdict.
- `move_i` is local bookkeeping (no request) but must still be blocked to undiscovered
  hosts.

## Step 4 — Real recon replaces `p_recon`

`recon` must call `backend/recon.py::ReconEngine` against `127.0.0.1` over the lab port
range and add the hosts whose ports are **actually open and HTTP-responsive** to
`discovered`. The 0.90 constant in `grounding.py::recon_prob` disappears from the live
path: discovery is now an observation. Decide and document whether one `recon` action
reveals one host (parity with the sim) or the whole scan — parity is the defensible choice
for comparison, so prefer it and say so.

## Step 5 — Episode reset on stateful targets

This is the part that is easy to get wrong. Real targets accumulate state: registered
users, poisoned rows, session tokens. Design and document a reset strategy, in this order
of preference:

1. **Idempotent probes** — read-only or naturally repeatable actions, no reset needed.
2. **Per-episode unique identifiers** — e.g. register `art-ai-ep{n}-{uuid}` so episodes do
   not collide.
3. **Container restart** for hosts that genuinely cannot be reused
   (`docker compose restart <svc>` plus a health wait), with the cost measured and reported.

Report the per-episode wall-clock cost of your chosen strategy. If reset costs 20s, say
so — that number determines how many live episodes are affordable and belongs in the
results.

## Step 6 — Sim-to-real protocol (`backend/experiments/run_live.py`)

20 seeds x 800 episodes is not affordable live. Build this protocol instead, and report
exactly what you ran:

- **Zero-shot transfer:** take the agent trained in the sim (frozen policy, via
  `TabularQAgent.freeze()`), evaluate it live for N episodes. This is the headline number.
- **Live fine-tune:** continue learning on the live env for a small episode budget and
  report whether it improves on zero-shot.
- **Live baselines:** random and greedy-by-signal, same live env, same episode budget —
  without them the agent's live number means nothing.
- Report **N live episodes, total requests issued, wall-clock, and requests per episode**
  alongside every metric. Confidence intervals over the episodes you actually ran; if N is
  small, use the appropriate interval (Wilson for win rate) and state N in the table.
- `--dry-run` must exercise the whole loop against the oracles without a full training
  budget, and the harness must **skip with a clear message** (not fake results) when the
  lab is down.

## Step 7 — Re-ground the MDP with measured probabilities

Now close the loop in the strong sense. Run each capability probe M times independently
(M ≥ 30 where the probe is cheap and repeatable) and compute the **empirical success rate
with a Wilson 95% CI**. Write these to `experiments/measured_probs.json` with the date,
image digests, and M.

Then:

- Produce a table comparing `grounding.py`'s **derived prior** against the **measured
  rate**, per host per capability. This is the sim-to-real gap, quantified.
- Re-run value iteration with the measured probabilities to get a **measured-MDP optimum**,
  and report the live agent's regret against it.
- If the priors are badly wrong (likely: several of these probes are deterministic, i.e.
  p≈1.0, where the CVSS/EPSS formula predicted 0.2–0.8), **say so plainly**. That finding
  is a legitimate research result about the limits of CVE-metadata-derived dynamics — it is
  not a failure to hide, and not a reason to retune the formula until it matches.

## Step 8 — Evidence log, reproducibility, and honest reporting

- **Evidence log:** append-only JSONL at `experiments/results/live/evidence-<run>.jsonl`,
  one record per step: timestamp, episode, step, state key, action, host, every request
  made (method/URL/status/latency/length), oracle verdict, and the evidence snippet that
  justified it. This log is what makes "the agent really attacked" auditable rather than
  asserted. Also write `run_meta.json` with git commit, config, image digests
  (`docker compose images`), and the resolved lab port map.
- **`LIVE_RESULTS.md`:** sim vs live table (win rate, steps-to-admin, regret vs sim optimum
  and vs measured optimum, for random / greedy / zero-shot / fine-tuned), the
  derived-vs-measured probability table, which hosts and capabilities work and which you
  dropped with reasons, the cost numbers (requests, wall-clock, reset overhead), and the
  exact commands you ran. If zero-shot transfer degrades, report the degradation — that is
  the interesting result.
- **Update `REPRODUCE.md`** with a live section: lab bring-up, health gate, `--dry-run`,
  full live run, and a clear statement that the sim numbers reproduce without Docker while
  the live numbers require it.
- **Tests** (`backend/live/tests/` or alongside): scope chokepoint rejects off-allowlist
  hosts; each oracle has a positive and a negative case; the live env satisfies the
  `AttackMDP` interface (one shared contract test run against both); rng does not influence
  live outcomes.

## Subagents

`.claude/agents/` already has `rl-engineer`, `eval-scientist`, `lab-infra`,
`data-grounding`, and `reproducibility` — use them for the matching work. Add one:
**`oracle-engineer`** — owns the capability probes and success oracles, with a system
prompt that makes the scope allowlist and the "no fabricated success" rule its first
responsibility, and only the tools it needs.

## Definition of done

1. `python -m experiments.run_all` still reproduces `RESULTS.md`. Nothing in the sim
   regressed.
2. A single command runs the live loop, and an agent action provably issues an HTTP request
   to the lab — traceable in the evidence log, request by request.
3. Every live success is justified by a logged response, not a random draw. `grep` the live
   path: no `rng.random()` decides an outcome.
4. Scope test passes: an off-allowlist request raises before a socket opens.
5. `LIVE_RESULTS.md` contains the derived-vs-measured probability table and the sim-to-real
   transfer numbers, with N and cost stated.
6. Everything you could not make work is written down as such.

Constraints, restated: local lab only, `127.0.0.1:3001-3006`; no third-party targets; no
detection evasion, no weaponization, no persistence, nothing destructive; report what you
measured, including the parts that came out badly.
