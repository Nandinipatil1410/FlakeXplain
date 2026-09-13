# FlakeXplain: Empirical Flaky Test Detection Report

**Methodology Adaptation**: iDFlakies (Lam et al., ICST 2019) detection protocol ported from JUnit/Maven to Pytest/Python.

> [!CAUTION]
> **Non-Flaky Label Caveat**: Tests categorized as `not observed flaky` were not observed flipping outcome in the executed $N$ rounds under the pinned environment. This is **not** mathematical proof of permanent non-flakiness.

## Summary Table

| Repository | Commit Hash | Total Tests Collected | Rounds (Orig / Rand / Rev) | Wall-Clock Time | Observed Flaky (Total) | OD | NOD | Unclassified | Not Observed Flaky (in N runs) | Observed Flaky Ratio | Baseline Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `click` | `6aabf099` | 2084 | 12 / 12 / 1 | 0.03s | **0** | 0 | 0 | 0 | 1975 | **0:1975** | `PASSED (Attempt 1, 11.44s)` |
| `flask` | `d318b683` | 494 | 12 / 12 / 1 | 0.03s | **0** | 0 | 0 | 0 | 494 | **0:494** | `PASSED (Attempt 1, 8.76s)` |
| `filelock` | `82f66d7b` | 1342 | 12 / 12 / 1 | 28594.31s | **2** | 2 | 0 | 0 | 1104 | **2:1104** | `PASSED (Attempt 1, 234.47s)` |
| `fsspec` | `13b0bce8` | 1779 | 12 / 12 / 1 | 1866.14s | **2** | 2 | 0 | 0 | 1492 | **2:1492** | `PASSED (Attempt 1, 61.74s)` |
| `httpx` | `b5addb64` | 0 | 0 / 0 / 0 | N/A | **0** | 0 | 0 | 0 | 0 | **DISCARDED** | `FAILED (Discarded)` |

## Per-Repository Breakdown & Empirical Logs

### Repository: `click`
- **Pinned Commit Hash**: `6aabf099bfdd4c1e75fe8d0e0d4241372b988ab1`
- **Execution Directory**: `G:\My Drive\Academics\Final Year Project\repos\click`
- **Baseline Gate Status**: `PASSED (Attempt 1, 11.44s)`
- **Total Collected Tests**: 2084
- **Unlabelled Tests** (skip-only or failure-only): 109
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 0.03 seconds
- **Observed Flaky Ratio**: `0:1975`

*No tests flipped outcomes across the executed reordering configurations under this pinned environment.*

---
### Repository: `flask`
- **Pinned Commit Hash**: `d318b683471101618febed18996405ad26462110`
- **Execution Directory**: `G:\My Drive\Academics\Final Year Project\repos\flask`
- **Baseline Gate Status**: `PASSED (Attempt 1, 8.76s)`
- **Total Collected Tests**: 494
- **Unlabelled Tests** (skip-only or failure-only): 0
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 0.03 seconds
- **Observed Flaky Ratio**: `0:494`

*No tests flipped outcomes across the executed reordering configurations under this pinned environment.*

---
### Repository: `filelock`
- **Pinned Commit Hash**: `82f66d7b0aaa83755f8d71d0b0da88408b58ec4a`
- **Execution Directory**: `C:\Users\Nandini\AppData\Local\FlakeXplain\5b4a364d\repos\filelock`
- **Baseline Gate Status**: `PASSED (Attempt 1, 234.47s)`
- **Total Collected Tests**: 1342
- **Unlabelled Tests** (skip-only or failure-only): 236
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 28594.31 seconds
- **Observed Flaky Ratio**: `2:1104`

#### Observed Flaky Test Details:

| Test Node ID | Classification | Category Reason | Outcomes Across Runs |
|---|---|---|---|
| `tests.test_read_write::test_timeout_behavior` | **OD** | Only fails under reordered/randomized configuration | `original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:FAIL, random-order:PASS, random-order:PASS, random-order:PASS, reverse-order:PASS` |
| `tests.test_strict_soft_stress::test_strict_soft_eight_process_contention_has_no_overlap` | **OD** | Only fails under reordered/randomized configuration | `original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, random-order:FAIL, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:PASS, random-order:FAIL, random-order:PASS, random-order:PASS, random-order:PASS, reverse-order:PASS` |

---
### Repository: `fsspec`
- **Pinned Commit Hash**: `13b0bce86a52b7c9a393753fc0381f3c5a955622`
- **Execution Directory**: `G:\My Drive\Academics\Final Year Project\repos\fsspec`
- **Baseline Gate Status**: `PASSED (Attempt 1, 61.74s)`
- **Total Collected Tests**: 1779
- **Unlabelled Tests** (skip-only or failure-only): 285
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 1866.14 seconds
- **Observed Flaky Ratio**: `2:1492`

#### Observed Flaky Test Details:

| Test Node ID | Classification | Category Reason | Outcomes Across Runs |
|---|---|---|---|
| `fsspec.tests.test_mapping::test_keys_view` | **OD** | Only fails under reordered/randomized configuration | `original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:PASS, random-order:PASS, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:PASS, random-order:FAIL, random-order:FAIL, reverse-order:FAIL` |
| `fsspec.tests.test_mapping::test_multi` | **OD** | Only fails under reordered/randomized configuration | `original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, original-order:PASS, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:PASS, random-order:FAIL, random-order:FAIL, random-order:PASS, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:FAIL, random-order:FAIL, reverse-order:FAIL` |

---
### Repository: `httpx`
- **Pinned Commit Hash**: `b5addb64f0161ff6bfe94c124ef76f6a1fba5254`
- **Execution Directory**: `C:\Users\Nandini\AppData\Local\FlakeXplain\5b4a364d\repos\httpx`
- **Baseline Gate Status**: `FAILED (Discarded)`
- **Total Collected Tests**: 0
- **Unlabelled Tests** (skip-only or failure-only): 0
- **Total Rounds Run**: 0 (0 original, 0 random, 0 reverse)
- **Total Wall-Clock Time**: 0.00 seconds
- **Observed Flaky Ratio**: `DISCARDED`

*No completed detection rounds; flaky labels have not been assigned.*

---