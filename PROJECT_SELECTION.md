# Step 5 project selection and provenance

Status: **implemented selection/configuration; no new FlakeXplain execution results yet**.

This document records how historical datasets were used to choose candidate projects.
Their outcomes are provenance and prioritization signals only. They are not copied into
FlakeXplain labels, classifier features, or the authoritative consolidated report.

## Selection rules

- Prefer projects with historical flaky tests from FlaPy, FLAKE16, iPFlakies, or
  Python IDoFT, especially agreement across sources.
- Pin the studied historical commit when available and use its compatible Python era.
- Execute the complete upstream pytest suite after a clean baseline gate; do not run
  only historically named tests.
- Preserve the suite's natural class imbalance. Because projects are deliberately
  enriched for historical yield, this corpus must not be presented as a prevalence
  estimate for Python projects.
- Treat historical rows as records, not independent root causes. Parameterized tests,
  victim/polluter pairs, and shared failures must later be clustered.

## First execution batch

| Priority | Project | Pinned commit | Historical selection evidence | FlakeXplain status |
|---:|---|---|---|---|
| 1 | IPython | `95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d` | FLAKE16 reports a suite of 846 tests with 6 NOD and 304 OD records. | Two baseline runs rejected for deterministic setup incompatibilities (`matplotlib` absent, then incompatible Jedi API); dependency configuration corrected and rerun pending. No detection result. |
| 2 | ReFrame | `576eb3f1dcc015d1e6d7a10602c748d4f810da68` | FlaPy contains 189 OD records; iPFlakies yields 136 unique flaky-test IDs after filtering non-flaky statuses and deduplication; Python IDoFT contains 137 records. | Candidate workflow configured; no baseline or detection result yet. |
| 3 | Loguru | `f31e97142adc1156693a26ecaf47208d3765a6e3` | FLAKE16 reports a suite of 1,255 tests with 4 NOD and 21 OD records. | Candidate workflow configured; no baseline or detection result yet. |
| 4 | Freezegun | `b46da782a7a051081fd51577749cfc0074db0cc6` | At this commit, FlaPy contains 17 OD records and iPFlakies yields 15 unique victim tests. Python IDoFT contains 16 records at this commit plus 1 at another commit. | Candidate workflow configured; no baseline or detection result yet. |

The historical counts above retain each source's own unit and terminology. They are
not expected FlakeXplain positives and must not be added to the current total of 50.

The first IPython baseline attempt on 2026-09-14 was rejected after all three gate
attempts stopped at collection with `ModuleNotFoundError: matplotlib`. This is a setup
dependency failure, not flaky-test evidence. The pinned source imports matplotlib
unconditionally in `IPython/core/tests/test_pylabtools.py`; the corrected configuration
adds the `matplotlib==3.4.2` version recorded by FLAKE16 before a clean rerun.

The second baseline run reached the tests but all three gate attempts stopped at
`TestCompleter.test_abspath_file_completions`: a newer Jedi rejected IPython's
`line` and `column` arguments. This is also deterministic environment incompatibility,
not flaky-test evidence. The corrected environment pins FLAKE16's recorded
`jedi==0.17.0` and `parso==0.8.2` pair.

## Reserves and deferred projects

| Status | Project | Historical signal | Reason |
|---|---|---|---|
| Reserve | Requests | FLAKE16: 537 tests, 5 NOD, 0 OD records. | Useful NOD-focused fallback, but the historical checkout has a much older dependency stack. |
| Reserve | Kombu | FLAKE16: 1,025 tests, 2 NOD, 23 OD records. | Promising yield, but optional transports create broader setup risk. |
| Deferred | Airflow | FLAKE16: 3,458 tests, 66 NOD, 293 OD records. | High yield but a large dependency and service surface raises baseline and six-hour job risk. |
| Deferred | Libcloud | FLAKE16: 9,840 tests, 3 NOD, 133 OD records. | Twenty-seven full-suite rounds are at high risk of exceeding the job limit. |

## Source provenance

- FlaPy repository: <https://github.com/se2p/FlaPy>
- FlaPy dataset record: <https://zenodo.org/records/4450435>
- FLAKE16 framework and subject pins: <https://github.com/flake-it/flake16-framework>
- FLAKE16 archived artifact: <https://zenodo.org/records/17250074>
- iPFlakies artifact: <https://github.com/ailen-wrx/ipflakies_artifact>
- iPFlakies dataset record: <https://zenodo.org/records/6176417>
- Python IDoFT data: <https://github.com/TestingResearchIllinois/idoft/blob/main/py-data.csv>

## GitHub Actions protocol

Each candidate has an isolated manual workflow. Run `baseline-only` first. A nonzero
baseline result rejects that environment and prevents detection. Only after reviewing
a passing baseline should `full` be selected; it runs 12 original, 12 seeded random,
and 3 reverse rounds. Every workflow uploads setup, environment, baseline, logs, and
any completed XML evidence even on failure.
