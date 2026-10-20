# Amendment B2 to the v0.8 protocol: re-run mechanics and environment validity

Dated 20 October 2026. Committed **before any re-run or label exists**. One local validation was
made on environment e0457 (pytest on Windows, Python 3.11) in `--check-only` mode. That mode stops
after the environment check, and since the check deselects every candidate, **no candidate test was
run**. (A first, buggy local attempt ran the whole file including the candidate; its failure count
appeared in one log line. That attempt was on an unmatched local environment, not a label, and no
outcome from it is used.)

## Mechanics (`scripts/mdflaker_v08_rerun_job.py`, `.github/workflows/mdflaker-v08-rerun.yml`)

- **Grouping:** `scripts/mdflaker_v08_plan.py` groups candidates into re-run environments keyed by
  (repo, head_sha, merge_base, runner, Python spec, recipe variant). That gives 1,026 environments
  covering 1,641 candidates, in 6 batches of up to 200.
- **Runners:** the same OS family and generation as the original job (ubuntu-22.04/24.04,
  windows-2022/2025, macos-15/latest), with the original Python minor version. PyPy is used where
  the job ran PyPy, and free-threaded `t` builds where it ran those.
- **Recipes** follow each project's own CI tooling:
  - tox env from the log: DRF (the failing env), pytest, setuptools (`py`);
  - nox session from the log: urllib3;
  - `uv sync`: prefect;
  - requirements files: hypothesis, Cirq, conan.
- **Outcome parsing:** outcomes come only from pytest's final `short test summary info` section
  (`-rA`). Colour is disabled, and plugins are disabled with `-p no:randomly -p no:cacheprovider`.
  The checkout fetches tags, so tag-derived versions resolve.

## Exclusions (objective, recorded, never relabelled)

1. **Cygwin jobs** (18 setuptools candidates): their environment cannot be reproduced on standard
   runners.
2. **Invalid node IDs:** the test's file is absent from the tested tree. These are log-parsing
   artifacts, for example summary lines printed by nested pytest runs inside pytest's own tests.
3. **Setup failures:** checkout, merge or install fails, or the job times out (round limit
   15 minutes; job limit 4 hours).
4. **Environment check failure:** the candidates' test files are run once with every candidate
   `--deselect`ed. The environment is **valid** if at least 80% of the other tests that ran passed,
   were skipped or xfailed. With no other tests (single-test files) it is **unchecked**; such cases
   are kept and reported as a separate stratum.

## Labels

Rounds use only valid or unchecked environments. A candidate is **flaky** if any of the 30 rounds
reports PASSED (or XPASS), and **not flaky** if all 30 report FAILED or ERROR. Any other pattern
(MISSING or SKIPPED in any round) means **unlabelled**, reported with counts.

## Pilot

Before the full batches, `rerun/v0.8/pilot.json` (15 environments, 1–2 per project) is run in
**`check-only` mode** (checkout, install and environment check; no candidate test runs) to validate
the recipes. Recipe fixes after the pilot are allowed only if they are made **without looking at
candidate outcomes**: only setup and env-check logs may be inspected. Each fix is recorded here
with a date before the full run.

## Trigger (20 Oct 2026, before any run)

A manual `workflow_dispatch` only works when the workflow file is on the default branch. The
workflow therefore also runs when a `rerun/v0.8-*` branch is pushed; the batch and mode then come
from `rerun/v0.8/RUN.json`. This changes how runs start, not what they do.
