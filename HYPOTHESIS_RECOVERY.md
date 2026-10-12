# Hypothesis workflow recovery

## Verified evidence from run 38161059994

- The complete baseline passed on attempt 1: 4,554 collected test cases.
- All 12 original-order rounds completed with exit code 0.
- Eleven randomized rounds completed before the 330-minute limit interrupted
  random round 12; reverse execution had not started.
- Evidence is preserved at
  https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/38161059994/artifacts/11719070694
  and locally in `.tmp-hypothesis-evidence.zip`.

The randomized evidence from that run is **diagnostic, not a validated benchmark**.
Its logs show widespread failures in the upstream `pytest_runtest_call` PRNG-leak
check. `pytest-randomly` reset the global PRNG between that check's before/after
snapshots. Do not interpret those failures as order-dependent flaky labels without
accounting for this runner interference.

## Implemented correction; full verification pending

Hypothesis randomized rounds now pass `--randomly-dont-reset-seed`. The explicit
ordering seed and shuffling remain enabled. Test-time PRNG management belongs to
the unchanged upstream suite. Main-suite and entry-point example tests still run
on every invocation, with combined JUnit evidence. Child pytest processes retain
their required Hypothesis/xdist entry points without loading pytest-randomly.

The corrected option is part of the fingerprinted subject recipe, so previous
checkpoints cannot be reused as evidence for this changed experiment. A fresh
full baseline and 12 original, 12 random, and one reverse round are required.
If the full job reaches its time limit, rerun the same workflow commit in full
mode; reuse is permitted only after environment and complete-XML validation.

Local verification: the complete pipeline unit suite passes (one Linux-only
test is skipped on Windows). Three synthetic integration checks pass with pytest
6.2.4: child isolation and xdist support, explicit outer ordering seed, and disabled
per-test reseeding. These checks do not establish subject results or flaky labels.
