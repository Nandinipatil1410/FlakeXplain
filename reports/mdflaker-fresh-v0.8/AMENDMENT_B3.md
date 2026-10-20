# Amendment B3: collection check, and discarding the first full attempt

Dated 20 October 2026, before any label was computed.

## What happened

The first full attempt (runs 39386823153 = batch_00 and 39386840500 = batch_01, harness at commit
`23d714a`) was **stopped and is discarded completely**. None of its outcomes will be used or
analysed. While checking the mechanics, only round counts, round durations and the number of
MISSING outcomes were looked at; no PASS/FAIL value was inspected. First-round logs were opened
only for environments where *every* candidate was MISSING, which contain no outcome.

Two mechanics bugs were found:
1. **One bad argument aborts the whole round.** pytest stops the entire session when any argument
   cannot be collected. A garbled node ID from a CI log
   (`test_traceback_framesultiple_failures]`) therefore made every other candidate in that
   environment MISSING in every round.
2. **ID format mismatch.** pytest prints node IDs relative to its own rootdir, which can be a parent
   of the directory the candidate IDs are relative to (for example `hypothesis/tests/...` against
   `tests/...`).

## Changes (`scripts/mdflaker_v08_rerun_job.py`)

- **Collection check before any round:** the candidates are collected with `--collect-only`, never
  executed. Any candidate that cannot be collected is excluded as `not_collectable` (objective and
  label-blind); the rest run together. The check also runs in check-only mode.
- **ID matching** in the collection check, the environment check and the rounds accepts an exact
  match or a `/`-suffix match.

## Restart

The fix is verified with a check-only pilot (`rerun/v0.8/pilot_collect.json`: the original pilot
plus the five affected hypothesis environments). After that, **all six batches restart** on new
branches (`rerun/v0.8-r2-batchNN`), and only their results are used.

## Collection pilot 1 fix (20 Oct 2026; collection and env-check logs only)

Run 39389082524 (check-only) showed two problems with the first collection rule, which parsed node
IDs out of the collection output:
- A suffix match also hit pytest's own error lines ("ERROR: not found: .../<id>"), so a garbled ID
  counted as collectable.
- urllib3's nox session adds `-v`, so collection printed a tree rather than ID lines, and valid IDs
  were rejected.

The rule now uses only pytest's exit code, its "N collected" count (N must be at least the number of
IDs) and the absence of not-found or collection errors. It is applied first to all candidates
together and then to each one separately. Checked locally: e0003 keeps its 3 real tests and drops
the garbled ID; e0001 (needs `hypothesistooling`) is excluded.
