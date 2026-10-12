# Prefect historical workflow recovery

## Implemented

The pinned Prefect checkout is `6b59d989dec33aad8c62ea2476fee519c32f5c63` (2021).
Its `tests/cli/test_auth.py::test_create_key` cases contain fixed expiration
strings in June and December 2025. The CLI intentionally rejects past dates,
so running these cases with the current wall clock causes a deterministic
baseline failure.

`scripts/run_prefect_tests.py` supplies Pendulum's supported test clock,
2021-07-01 UTC, during the call phase of these six cases only. The context
manager restores the prior Pendulum clock even when a case fails. Collection,
fixtures, all assertions, system time, monotonic time, and all other cases
retain their normal behavior. No upstream files are modified.

The pipeline uses this same entry point for the strict baseline and all
12 original-order, 12 random-order, and one reverse-order rounds. The
fingerprinted subject recipe records the scope, clock value, and rationale.
The workflow defaults to `full`; every recovery dispatch uses `mode=full`.
A 180-second faulthandler diagnostic prints thread stacks without converting
failures to passes or dropping tests.

## Empirically verified

The original full workflow run 37968218406 failed on the first expired-date
case. A subsequent baseline attempt was terminated with exit code -9.
The 57 local pipeline unit checks passed after the runtime entry point change.

The first recovery full run (38139721214) passed the expiry cases, then failed
at `test_jupyter_html_output`: PyZMQ had cached a MagicMock JSON backend.
Prefect documentation collection wraps optional imports with an exception-to-
MagicMock hook. PyZMQ's optional simplejson lookup can therefore select a mock.
One baseline attempt also observed an asynchronous cancellation log in a shell
logging assertion; the other two reached the notebook failure.

The launcher now imports and validates `zmq.utils.jsonapi` before collection,
letting its normal import fallback choose the real installed JSON backend.
A local reproduction using the exact PyZMQ 22.1.0 source verified both the
failure under the documentation import hook and the successful byte roundtrip
when initialized before that hook. The launcher hash is included in Prefect's
environment fingerprint. The 57 local pipeline checks passed again.

Second full recovery run uses commit `7e9e33ed547a791bc999d8897e7f1e2a590e5d3b`.


The recovery workflow is still in progress. No successful full-run result or
flaky-test statistics are claimed until its evidence has been checked.

## 2026-10-12 follow-up

Empirically verified: run 38160921362 passed the strict baseline on its first
attempt with 7,076 JUnit test cases (7,045 passed, 29 skipped, 2 xpassed).
Original-order rounds 1, 2, and 3 completed with the same test counts.
Original-order round 4 was killed with exit -9 and was not checkpointed.
No random or reverse rounds were completed by that run.

The diagnostic dump showed six heartbeat threads inside Agent's infinite
heartbeat loop, most repeatedly calling mocked time.sleep. The main thread
was formatting an exception and performing inspect.findsource/getmodule
filesystem work. Resource exhaustion is consistent with this evidence;
the artifact does not contain a kernel OOM report proving the kill reason.

Implemented mitigation: Prefect's recipe now selects --tb=line, avoiding
source introspection for traceback formatting, and the launcher logs each
exception's node ID and phase before reporting. Assertions, fixtures,
collection, ordering, and outcome recording are unchanged. No upstream source
is patched. The launcher hash and recipe continue to bind environment IDs.
The 57 local pipeline checks passed after this change.

Published commit: 524f2a1760e6cf436ff63cacb7372d3a833cb0a8.
Another mode=full run was dispatched. Its outcome remains unverified.

## Retry-plugin evidence correction

Run 38166749563 passed the baseline and original-order round 1. Round 2
finished, but its XML had 7,077 testcase elements for 7,076 collected cases.
The duplicate was TestDaskExecutor's
`test_exit_early_with_external_or_inproc_cluster_waits_for_pending_futures[inproc]`:
the upstream flaky plugin retried it inside the round. The existing strict
count validation correctly refused to checkpoint that XML. The distinct
backend start-time test also recorded a genuine assertion failure after
background heartbeat threads called its mocked sleep 1,373 times.

Implemented: disable the internal flaky retry plugin for Prefect via
`-p no:flaky`, identically for baseline and every round. Each planned round
now observes one execution per test; failures are retained instead of being
masked by retries. No test assertions, source, or count validation is changed.
The full baseline remains mandatory; 12 original, 12 random, and one reverse
round remain mandatory. Fresh evidence is required for the changed recipe.
Local pipeline checks: 60 tests run, OK with one existing skip.

Published retry-policy commit: `018f2334f533789a89a55cb78b59b23e1dec3ba6`.
Full run: https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/38213537194
