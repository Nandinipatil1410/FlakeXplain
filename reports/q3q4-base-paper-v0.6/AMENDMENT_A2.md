# Amendment A2 to the v0.6 protocol: study population without Superset

Dated 19 October 2026. Decided by the project team (Nandini Patil) and committed **before gate G1
was evaluated**. At that point no label had been read in stage 1 and no model had been fitted.
`PROTOCOL.md`, `protocol.json` and Amendment A1 remain in force, except where this amendment changes
them.

## What triggered it

The stage 1 source join found that the exact recorded build commits can be retrieved for:

| Project | Build commits | Retrievable | Rows covered |
|---|---:|---:|---:|
| spaCy | 65 | 65 | 1,080 / 1,080 |
| django-rest-framework | 62 | 62 | 536 / 536 |
| incubator-superset (now apache/superset) | 84 | **3** | 8 / 535 |

The 81 missing Superset commits are not reachable from any branch or from `refs/pull/<n>/head` (all
32 pull requests were fetched). `git fetch <sha>` returns "not our ref", the GitHub commits API
returns 422, and codeload archives return 404. They were almost certainly Travis pull-request merge
commits, which GitHub has since discarded. They cannot be recovered, so on the full data
G1 (at least 85% mapped) was certain to fail, whatever the labels: at most (1,616 + 8) / 2,151 ≈ 75%.

## Changes

**A2.1: primary population.** All stage 3 analyses, comparator selection and gate G1 use only the
spaCy and django-rest-framework rows (1,616 rows). Superset is excluded **as a whole project**
because its source is unavailable. Its 8 retrievable rows are excluded too, so that no rows are
selected individually. The exclusion depends only on source availability, never on labels.

**A2.2: G1** is evaluated on the 1,616 rows. The thresholds are unchanged: at least 85% mapped, and a
label gap of at most 10 percentage points.

**A2.3: B\* selection** (A1.1) uses the primary population.

**A2.4: project criteria.** Rule 4 (no degradation) applies to both remaining projects. The "robust
across projects" qualifier now requires ET-BC to beat B\* on MCC in **both** projects. It replaces
the original "at least 2 of 3".

**A2.5: S2** (leave-one-project-out) becomes 2 folds: train on spaCy and test on DRF, and the reverse.

**A2.6: S7, new and baseline-only, reported but outside the rule.** The four comparator candidates
and ET-B (the authors' features only) are also run on all 2,151 rows from all 3 projects, so the
Superset loss can be judged on the base paper's full data. G2a and G2b are reported on all rows and
on the primary population.

**A2.7: wording.** Every claim says it holds "on MDFlaker's released data for the two of its three
projects whose source is still retrievable (spaCy, django-rest-framework; 1,616 failed executions)".

Nothing else changes: features, models, grouping, seeds, thresholds and the C1/C2 values all stay
as frozen.
