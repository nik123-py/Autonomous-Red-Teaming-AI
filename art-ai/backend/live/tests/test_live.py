"""Tests for the live lab environment.

Run:  python -m live.tests.test_live      (from backend/)

Covers, per Step 8:
  * the scope chokepoint rejects off-allowlist hosts BEFORE any socket is opened
  * each oracle has a positive and a negative case
  * LiveAttackEnv satisfies the AttackMDP interface (one shared contract test)
  * rng does not influence live outcomes
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from experiments.live_env import LiveAttackEnv  # noqa: E402
from experiments.mdp import ACTIONS as SIM_ACTIONS  # noqa: E402
from experiments.mdp import AttackMDP, state_key  # noqa: E402
from live import http_client  # noqa: E402
from live.capabilities import FOOTHOLD, HOST_NAMES, PRIVESC  # noqa: E402
from live.http_client import LabSession, ScopeViolation, assert_in_scope  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


# ------------------------------------------------------------------ scope tests
def test_scope():
    print("\n[scope chokepoint]")
    for bad in ["http://8.8.8.8/", "http://example.com/", "https://evil.test/",
                "http://127.0.0.1:22/", "http://127.0.0.1:8003/", "http://169.254.169.254/",
                "file:///etc/passwd", "http://[::1]:3001/"]:
        try:
            assert_in_scope(bad)
            check(f"reject {bad}", False, "was ALLOWED")
        except ScopeViolation:
            check(f"reject {bad}", True)

    for good in ["http://127.0.0.1:3001/", "http://localhost:3003/api/users"]:
        try:
            assert_in_scope(good)
            check(f"allow {good}", True)
        except ScopeViolation as e:
            check(f"allow {good}", False, str(e))

    # the guard must fire before any socket work: monkeypatch the opener to explode
    fired = {"socket": False}
    orig = http_client.urllib.request.build_opener

    def boom(*a, **k):
        fired["socket"] = True
        return orig(*a, **k)

    http_client.urllib.request.build_opener = boom
    try:
        http_client.request("GET", "http://8.8.8.8/")
    except ScopeViolation:
        pass
    except Exception:
        pass
    finally:
        http_client.urllib.request.build_opener = orig
    check("no socket opened for out-of-scope target", not fired["socket"])


# ----------------------------------------------------------------- oracle tests
def test_oracles():
    print("\n[oracles: positive cases -- real requests]")
    for h in HOST_NAMES:
        s = LabSession()
        f = FOOTHOLD[h](s)
        check(f"{h} foothold positive", f.success, f.evidence[:60])
        try:
            p = PRIVESC[h](s, "test") if h == "vampi" else PRIVESC[h](s)
        except TypeError:
            p = PRIVESC[h](s)
        check(f"{h} privesc positive", p.success, p.evidence[:60])

    print("\n[oracles: negative cases -- the predicate must be able to say False]")
    from live.capabilities import _u, HOST_PORTS
    s = LabSession()
    # flask privesc with a wrong password must be refused (401, role != admin)
    r = s.post(_u(HOST_PORTS["flask-api"], "/api/login"),
               json_body={"username": "admin", "password": "definitely-wrong"})
    check("flask-api privesc negative (bad creds -> 401)", r.status == 401, f"status={r.status}")
    # juice-shop gate must 401 without a token
    r2 = s.get(_u(HOST_PORTS["juice-shop"], "/api/Users"))
    check("juice-shop gate negative (no token -> 401)", r2.status == 401, f"status={r2.status}")
    # flask SQLi differential must NOT fire on a benign id
    base = s.get(_u(HOST_PORTS["flask-api"], "/api/users?id=1"))
    check("flask-api baseline is 1 row (differential is meaningful)",
          len(base.json()) == 1, f"rows={len(base.json())}")

    # WebGoat: an over-long password silently fails registration, so login then fails.
    # This is the trap that made WebGoat look unusable; lock the behaviour in.
    import uuid as _uuid
    s2 = LabSession()
    bad_user = f"artaibad{_uuid.uuid4().hex[:4]}"
    s2.post(_u(HOST_PORTS["webgoat"], "/WebGoat/register.mvc"),
            data={"username": bad_user, "password": "Passw0rd123",      # 11 chars: invalid
                  "matchingPassword": "Passw0rd123", "agree": "agree"})
    lg = s2.post(_u(HOST_PORTS["webgoat"], "/WebGoat/login"),
                 data={"username": bad_user, "password": "Passw0rd123"})
    loc = lg.headers.get("Location", "")
    check("webgoat negative (11-char password -> registration rejected, login errors)",
          "error" in loc, f"login redirect={loc}")

    # WebGoat: the benign lesson-8 query on its own must NOT satisfy the oracle.
    s3 = LabSession()
    FOOTHOLD["webgoat"](s3, "negtest")
    benign = s3.post(_u(HOST_PORTS["webgoat"], "/WebGoat/SqlInjection/attack8"),
                     data={"name": "Smith", "auth_tan": "3SL99A"})
    import re as _re
    from live.capabilities import _wg_output
    n_b = len(_re.findall(r"<tr>", _wg_output(benign)))
    check("webgoat negative (benign query leaks only own record)", n_b == 2, f"rows={n_b}")


# --------------------------------------------------------------- contract test
def test_interface_contract():
    """One shared contract, run against BOTH the sim and the live env."""
    print("\n[interface contract: AttackMDP vs LiveAttackEnv]")
    sim = AttackMDP()
    live = LiveAttackEnv()
    for name, env in (("sim", sim), ("live", live)):
        check(f"{name}: has step", callable(getattr(env, "step", None)))
        check(f"{name}: action set shape", set(env.actions) >= {"recon", "exploit"},
              str(env.actions))
    check("live: reset returns initial state", state_key(live.reset()) == "a0|p0|d-")
    try:
        live.transitions((0, 0, frozenset()), "recon")
        check("live: transitions() raises NotImplementedError", False, "did not raise")
    except NotImplementedError:
        check("live: transitions() raises NotImplementedError", True)
    check("sim: transitions() works", len(sim.transitions((0, 0, frozenset()), "recon")) > 0)


# --------------------------------------------------------------- determinism
def test_rng_does_not_decide():
    """Different seeds over the same action sequence must give the same verdicts."""
    print("\n[rng must not decide live outcomes]")
    seq = ["recon", "exploit", "exploit"]
    verdicts = []
    for seed in (1, 999999):
        ev = []
        env = LiveAttackEnv(hosts=["flask-api"], evidence_sink=ev.append)
        s = env.reset()
        rng = random.Random(seed)
        for a in seq:
            s, _, done = env.step(s, a, rng)
            if done:
                break
        verdicts.append([e["oracle_verdict"] for e in ev])
    check("same verdicts across different seeds", verdicts[0] == verdicts[1],
          f"{verdicts[0]} vs {verdicts[1]}")


def test_defender():
    """The defender layer: off => unchanged; on => observable, and never fabricates."""
    print("\n[defender layer]")
    from live.defenses import DefensePolicy, policy_for_strength

    # strength 0 is inactive; the env stays a 3-tuple MDP
    env_off = LiveAttackEnv(hosts=["flask-api"], defense=policy_for_strength(0))
    s_off = env_off.reset()
    check("defender off -> 3-tuple state", len(s_off) == 3, str(s_off))
    check("defender off -> key unchanged", state_key(s_off) == "a0|p0|d-", state_key(s_off))

    # an always-blocking filter must make every exploit FAIL and never reach ADMIN
    # (this is the no-fabrication guarantee for the defender path)
    block_all = DefensePolicy(waf_block_p=1.0, seed=0)
    env_on = LiveAttackEnv(hosts=["flask-api"], defense=block_all)
    s = env_on.reset()
    check("defender on -> 4-tuple state", len(s) == 4, str(s))
    rng = random.Random(0)
    reached_admin = False
    saw_block = False
    s, _, _ = env_on.step(s, "recon", rng)
    for _ in range(6):
        s, _, done = env_on.step(s, "exploit", rng)
        if "|b" in state_key(s):
            saw_block = True
        if s[0] == 2:  # ADMIN
            reached_admin = True
        if done:
            break
    check("block-all defender never fabricates a win", not reached_admin)
    check("blocked host appears in observation", saw_block, state_key(s))

    # the probabilistic filter is reproducible under a fixed seed
    a = DefensePolicy(waf_block_p=0.5, seed=7)
    b = DefensePolicy(waf_block_p=0.5, seed=7)
    ra = [a.check("h", i * 10) for i in range(500)]
    rb = [b.check("h", i * 10) for i in range(500)]
    check("defender RNG reproducible under fixed seed", ra == rb)


if __name__ == "__main__":
    test_scope()
    test_interface_contract()
    test_rng_does_not_decide()
    test_defender()
    test_oracles()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
    sys.exit(1 if FAIL else 0)
