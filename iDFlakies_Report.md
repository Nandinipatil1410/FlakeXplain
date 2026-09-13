# FlakeXplain: iDFlakies Empirical Flaky Test Report

**Methodology Adaptation**: iDFlakies (Lam et al., ICST 2019) ported from JUnit/Maven to Pytest/Python.

> [!CAUTION]
> **Non-Flaky Label Caveat**: Tests categorized as `not observed flaky` were not observed flipping outcome in the executed $N$ rounds under the pinned environment. This is **not** mathematical proof of permanent non-flakiness.

## Summary Table

| Repository | Commit Hash | Total Tests Collected | Rounds (Orig / Rand / Rev) | Wall-Clock Time | Observed Flaky (Total) | OD | NOD | Unclassified | Not Observed Flaky (in N runs) | Observed Flaky Ratio | Baseline Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `click` | `6aabf099` | 2084 | 12 / 12 / 1 | 13.70s | **0** | 0 | 0 | 0 | 2084 | **0:2084** | `PASSED (Attempt 1, 13.95s)` |
| `flask` | `d318b683` | 494 | 12 / 12 / 1 | 240.30s | **0** | 0 | 0 | 0 | 494 | **0:494** | `PASSED (Attempt 1, 9.98s)` |

## Per-Repository Breakdown & Empirical Logs

### Repository: `click`
- **Pinned Commit Hash**: `6aabf099bfdd4c1e75fe8d0e0d4241372b988ab1`
- **Baseline Gate Status**: `PASSED (Attempt 1, 13.95s)`
- **Total Collected Tests**: 2084
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 13.70 seconds
- **Observed Flaky Ratio**: `0:2084`

*No tests flipped outcomes across the executed reordering configurations under this pinned environment.*

---
### Repository: `flask`
- **Pinned Commit Hash**: `d318b683471101618febed18996405ad26462110`
- **Baseline Gate Status**: `PASSED (Attempt 1, 9.98s)`
- **Total Collected Tests**: 494
- **Total Rounds Run**: 25 (12 original, 12 random, 1 reverse)
- **Total Wall-Clock Time**: 240.30 seconds
- **Observed Flaky Ratio**: `0:494`

*No tests flipped outcomes across the executed reordering configurations under this pinned environment.*

---