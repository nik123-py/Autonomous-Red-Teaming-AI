# Smoke-test artifacts — NOT results

Runs in this folder were produced with `--dry-run` (tiny N, no real lab traffic) purely to
check that `run_defender.py` wires up. They are kept for provenance and are **not** cited
anywhere.

- `defender-20261013T164519Z.json` — `dry_run: true`, eval N=8, strength 3 only, 0 requests.

The three real runs stay one level up in `results/live/` and *are* cited in
`COMPLEX_LAB_RESULTS.md`:

| file | `dry_run` | eval N | what it measures |
|---|---|---|---|
| `defender-20261013T164833Z.json` | false | 25 | strengths 2,3 — medium +0.08, strong uniform −0.28 |
| `defender-20261013T165219Z.json` | false | 25 | strengths 2,3 with persistence observation — strong 0.00 (−0.60) |
| `defender-20261013T165452Z.json` | false | 25 | strength 4, heterogeneous — the routability result (+0.68) |
