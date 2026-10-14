# FlakeXplain dataset v0.1 — guide and pilot dataset card

**Status: implemented and automatically validated pilot dataset. No model has been trained in this preparation step.**

## Verified size and scope

- 35 projects: all 30 CANNIER subjects (SunPy and urllib3 at changed revisions), plus filelock, freezegun, pytest, reframe, rich.
- Audited evidence candidates: 99,861; uniquely source-mapped model cases: **96,118** (96.25% coverage).
- **693 observed-flaky** and **95,425 not-observed-flaky** cases; natural positive rate **0.7210%**. No synthetic balancing or duplication.
- 51,370 defining source-function families; 631 positive source families across 29 positive projects. Parameter cases and inherited collections share family identifiers; they are not independent causal examples.
- Effective detection observations per case: {'25': 93216, '27': 2902}. Baseline observations are not counted in N.
- 3,743 candidate cases, including 22 observed positives, lack the required unique Python function join. They remain in source_exclusions.csv.gz and the evidence corpus. Rules are applied without selecting on the label.
- Excluded positives: 13 generated Airflow cases, one SunPy documentation case and eight Xonsh-language cases. Non-Python tests and generated functions are outside this extractor version. This selection can affect prevalence and difficulty.

## Target and evidence

The target is outcome instability observed under the recorded protocol: at least one PASS and one FAIL/ERROR. The negative class means all-pass after its recorded N observations, with no skip, missing or duplicate rounds. It does not establish permanent non-flakiness. Legacy click/flask/fsspec, baseline-failed httpx and ambiguous identities remain outside the primary evidence cohort.

All 1,168 frozen evidence files were rehashed successfully. Source archives are pinned to the recorded full commits; every extracted Python file was checked against its archive. Selected test and context source hashes are validated again in the exported artifact. Derived source node IDs are provided; original collection/execution order is not reconstructed.

pytest-randomly changes runtime seeds as well as order. These data support observed-instability prediction; OD/NOD patterns are provisional and are not classifier inputs. Fresh execution labels are not interchangeable with the authors’ released CANNIER labels.

## Tables and safe model inputs

| File | Purpose |
|---|---|
| labels.csv.gz | Binary target, effective N, outcome evidence and configuration-specific counts. Never a predictor table. |
| metadata.csv.gz | Project, revision, environment, original JUnit identity, parameter suffix, source identity/location/hash, family and context joins. Never a predictor table. |
| features_body.csv.gz | 22 numeric AST features from the test body. example_id is a join key, not an input. |
| features_context.csv.gz | 33 added static features: fixture/helper/lifecycle counts, scope/autouse/dependency structure and aggregated context AST features. |
| contexts.jsonl.gz | Source-linked context nodes, edges, bounds and unresolved-reference audit. Never a predictor table. |
| splits_outer.csv / splits_inner.csv | Fixed project groups for five outer folds and four inner folds within each outer training cohort. |
| source_exclusions.csv.gz / source_parse_errors.csv | Explicit source joins and parser limitations excluded from the model subset. |
| source_manifest.json / manifest.json / schema.json / validation.json | Source provenance, checksums, predictor allowlists and validation result. |
| manual_review_queue.csv | Deterministic broader review queue; pending rows do not imply human validation. |

Both planned Extra Trees ablations use exactly the same examples and outer/inner splits: body features versus body plus context (55 predictors). Outcome counts, patterns, seed values, JUnit durations, provenance and identifiers are prohibited as inputs. Fit preprocessing, tuning and thresholds only inside the corresponding training folds. No scaling, feature selection, imputation, vocabulary or model fitting was performed here.

## Context coverage and limitations

77,712 cases have at least one resolved context node. 28,992 cases have unresolved candidate fixture references; 21,856 reach a context bound. These counts are audit metadata, excluded from predictors.

Implemented: nearest ancestor conftest/module/class fixture precedence, imported repository fixtures, literal usefixtures/parametrize, applicable autouse fixture names, fixture dependencies, selected named helpers and xunit/unittest lifecycle methods. Limits: fixture depth 4, helper depth 2 and 32 unique context functions. This is potential static context, not a runtime trace.

Third-party fixtures and pytest_plugins registries are not expanded. Overridden fixtures depending on their own name are flagged rather than guessed. Hypothesis/mocking decorator-injected arguments can appear among unresolved candidate fixtures. Dynamic collection/dispatch, local/nested generated definitions, re-export chains, class/module initialization state, runtime conftest loading restrictions, stringified subprocess code and complete object call graphs are not resolved. Zero unresolved names does not prove complete context. Lexical call-category features are heuristics; they do not identify failure causes.

AI-assisted static spot review covers 16 cases (12 positives, four negatives) across 12 projects; see reports/dataset-preparation/static_review.json. It checks named source joins and selected context, not causal labels or complete runtime fixture graphs. The broader review queue and human cause annotation remain pending.

## Evaluation split freeze

| Outer fold | Projects | Cases | Observed flaky |
|---|---:|---:|---:|
| 0 | 6 | 21,584 | 310 |
| 1 | 7 | 19,609 | 146 |
| 2 | 7 | 19,583 | 78 |
| 3 | 7 | 17,807 | 80 |
| 4 | 8 | 17,535 | 79 |

Deterministic greedy project-group allocation minimizing incremental normalized squared imbalance of positive counts, case counts and group counts (weights 1,1,0.25); five outer and four inner folds. No fitted predictors used.

Substantive exact AST body families shared across projects: 0; any detected groups are kept together. Common bodies below three statements/20 AST nodes are not used to connect projects. Near-duplicate and fork genealogy audits remain incomplete; no claim of full benchmark independence is made.

Additional projects influenced preparation. Evaluate them with the same project-disjoint procedure; describe a later CANNIER-only training/additional-project evaluation as a secondary analysis, not untouched external validation. Airflow contributes many positives; report project-level and source-family-sensitive metrics rather than treating cases as independent.

## Reproduction

From the repository root, with Python 3.11 and standard-library dependencies:

```powershell
python scripts/fetch_dataset_sources.py
python scripts/verify_frozen_evidence.py --repos-dir 'G:\My Drive\Academics\Final Year Project\repos'
python scripts/prepare_dataset.py
python scripts/validate_dataset.py
python scripts/report_dataset.py
```

Raw workflow evidence and pinned third-party sources remain in local storage and are not embedded in the feature export. Network access is required to recreate source caches. Retain the evidence recovery reports and original archives. Verify upstream licences before releasing source snippets or third-party artifacts. Numerical tables and source references here do not grant upstream redistribution rights.

## Ready now and remaining work

Automated dataset validation passed 23 checks. Repository unit tests passed (one platform-specific check skipped on Windows). Dataset preparation is ready for a bounded pilot using the declared limitations. Model results, performance improvements, CANNIER-compatible reproduction, causal annotation, broad human review and submission readiness are not established.
