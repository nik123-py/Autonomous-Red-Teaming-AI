# LIVE_NOTES.md — the gap between the agent and the lab

Written **before** any live code, per Step 0. Everything below was verified by running it
against the lab on this machine on 2026-09-27. Scope: `127.0.0.1:3001-3006` only.

## 1. Proof that the agent is simulated

The scanner is real (`backend/recon.py` opens real TCP connections — confirmed earlier:
its output matches `netstat` exactly). The **agent** is not. The call chain:

```
experiments/run_all.py::run_qlearning_config
  -> metrics.py::run_episode
       -> agent.act(s)                      # picks "recon" | "exploit" | "move_i"
       -> AttackMDP.step(s, a, rng)         # experiments/mdp.py:153
            r = rng.random()                # <-- mdp.py:155  THE OUTCOME
            outcomes = self.transitions(s, a)
              -> foothold_p[position]       # grounding.py::exploit_probability
                 = f(CVSS exploitability, EPSS, verified flag, patch age)
```

`AttackMDP.transitions` returns `(probability, next_state, reward)` triples and `step`
picks one by comparing `rng.random()` against the cumulative probability. **The result of
`exploit` is decided entirely by a pseudo-random draw against a CVE-metadata prior.**

Mechanical confirmation:

```
$ grep -rnE "socket|requests\.|urllib|http\.client|aiohttp|httpx" backend/experiments/*.py
(no matches)
```

Zero network calls anywhere in `experiments/`. No agent action has ever produced an HTTP
request. The probabilities in `grounding.py` are **priors, not observations** — defensible
as priors, but never validated against the thing they claim to model.

## 2. Lab services actually live on this machine

All six containers report healthy (`docker compose ps`), and all six answer HTTP:

| port | service | container | health |
|---|---|---|---|
| 3001 | Juice Shop | art-ai-juice-shop | healthy |
| 3002 | DVWA | art-ai-dvwa | healthy |
| 3003 | vulnerable Flask API | art-ai-vulnerable-api | healthy |
| 3004 | WebGoat | art-ai-webgoat | healthy |
| 3005 | VAmPI | art-ai-vampi | healthy |
| 3006 | bWAPP | art-ai-bwapp | healthy |

Two required one-time initialisation steps, which the live harness must perform or assert:
- **VAmPI**: `GET /createdb` — without it every endpoint raises `sqlalchemy.OperationalError`.
- **DVWA**: `POST /setup.php` with `create_db` + CSRF token — without it login never sticks.
- **bWAPP**: `GET /install.php?install=yes` before `bee`/`bug` login works.

## 3. Capability probes — verified against the live services

Each capability is `(bool success, str evidence)` from a **deterministic predicate on a
real response**, with a benign baseline so success is a measured difference.

### flask-api (3003) — primary path, source is in-repo
- **foothold — SQLi differential.** Baseline `GET /api/users?id=1` returns **1 row**
  (`admin`). Injected `id=1 OR 1=1` returns **4 rows** (`admin,user,admin,user`).
  *Evidence that proves it:* returned row count strictly greater than the baseline count.
  Exact, because `app.py:51` interpolates `id` straight into the SQL string.
- **privesc — credential auth.** `POST /api/login` `admin`/`admin123` returns
  `{"success":true,"role":"admin","token":"fake_token_12345"}`; wrong password returns
  **HTTP 401**. *Evidence:* `role == "admin"` in a 200 response. Negative case confirmed.

### vampi (3005) — started with `vulnerable=1`
- **foothold — excessive data exposure.** `GET /users/v1/_debug` returns every user
  **including plaintext `password` fields**. *Evidence:* a `password` key present in the
  user objects. (Unauthenticated; no credentials needed.)
- **privesc — mass assignment.** `POST /users/v1/register` accepts an `admin` field;
  registering with `admin:true` and re-reading `_debug` shows `'admin': True` for that
  user. *Evidence:* the self-registered account's `admin` flag is true.
  **Non-destructive by design:** the `DELETE /users/v1/<name>` admin route also returns 200
  with that token, but it *deletes a lab user*, so it is **deliberately not used** as the
  oracle. The `admin:true` flag is sufficient proof without mutating lab data.

### juice-shop (3001)
- **foothold — SQLi auth bypass.** `POST /rest/user/login` with
  `{"email":"' OR 1=1--","password":"x"}` returns `authentication.token`. The JWT decodes
  to `email=admin@juice-sh.op, id=1, role=admin`. *Evidence:* a token is present and its
  payload decodes to a valid identity.
- **privesc — auth-gated route differential.** **Correction to the assumed probe:**
  `/rest/admin/application-configuration` returns **200 without any auth** in this image,
  so it proves nothing and must not be used. `GET /api/Users` is a genuine gate:
  **401 unauthenticated, 200 with the token**. *Evidence:* that 401→200 differential.
  (`/rest/user/authentication-details` behaves the same and is a backup.)

### dvwa (3002)
- **foothold — real authenticated session.** Scrape `user_token` from `login.php`, POST
  `admin`/`password`, then `GET /index.php` returns **200** (unauthenticated it redirects).
  Requires the DB-create step above. *Evidence:* 200 on an authenticated-only page.
- **privesc — SQLi differential at security=low.** With `PHPSESSID` + `security=low`,
  `?id=1` yields **1** `First name:` row; `?id=1' or '1'='1` yields **5**
  (`admin,Gordon,Hack,Pablo,Bob`). *Evidence:* row count > baseline.
  *(Note: count occurrences, not matching lines — DVWA emits all rows on one line.)*

### bwapp (3006)
- **foothold — authenticated session.** After `GET /install.php?install=yes`,
  `POST /login.php` `bee`/`bug` returns 302 and `portal.php` returns 200 containing
  `logout`. *Evidence:* `logout` present on the portal page.
- **privesc — SQLi differential.** `GET /sqli_1.php?title=Iron&action=search` yields **2**
  table cells; `title=' or 1=1#` yields **17**, leaking other rows
  (`Cobra Commander`, `Tony Stark`, `Man of Steel`). *Evidence:* cell count > baseline.

### webgoat (3004) — initially dropped, then **IMPLEMENTED**
*First pass (superseded):* dropped on the grounds that WebGoat's vulnerabilities are
lesson-scoped, so an oracle would measure its `lessonCompleted` bookkeeping rather than an
attack outcome.

*Resolution:* that objection is answered by keying the oracle on the **actual SQL output**
rather than on the lesson tracker, so the host is now in the live action space.
- **foothold — authenticated session.** `POST /WebGoat/register.mvc` (per-episode unique
  username) then `POST /WebGoat/login`; `GET /WebGoat/start.mvc` returns **200** and the
  page contains that account's own username plus a Logout control (unauthenticated it
  302-redirects to `/WebGoat/login`). *Evidence:* own username present on an
  authenticated-only page.
  **Trap:** WebGoat enforces a **6-10 character password**. An 11-character password makes
  registration fail *silently* (HTTP 200 re-rendering the form with validation errors, not
  a 302), and every later login then returns `/WebGoat/login?error`. This is what made the
  host look unusable on first contact.
- **privesc — SQLi differential on lesson 8.** The query is
  `... WHERE last_name = '<name>' AND auth_tan = '<auth_tan>'`. Benign
  (`Smith`/`3SL99A`) returns **2** `<tr>` rows (header + own record); injecting
  `auth_tan=' OR '1'='1` returns **6** (header + all five employees). *Evidence:* injected
  row count > benign row count — records the user is not entitled to. `lessonCompleted` is
  logged as corroboration only and is **not** the predicate.

All six lab services therefore have working oracles; nothing is dropped.

## 4. Consequences for the live design

- The live action space has **6 hosts**, the sim has 3. For a like-for-like sim-vs-live
  comparison the live env must be restricted to a comparable host set, or the comparison
  must state the difference. I will keep the full 6 and report per-host results, and use
  the 3 sim-equivalent hosts for the headline transfer number.
- **Several probes look deterministic** (SQLi differentials either work or they do not).
  If that holds under repetition, the measured probabilities will be ~1.0 where
  `grounding.py` predicted 0.216–0.810. That is the sim-to-real gap this work must
  quantify and report plainly — not retune away.
- `recon_prob = 0.90` has no live meaning: discovery becomes an observation from
  `ReconEngine`.
- Reset strategy is mostly **idempotent probes** (all SQLi differentials and reads are
  repeatable) plus **per-episode unique identifiers** for the one mutating probe (VAmPI
  registration uses a unique username per episode). No container restarts needed, so
  per-episode reset cost should be ~0s. To be measured and reported.
