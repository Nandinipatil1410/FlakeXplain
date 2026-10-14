# Consolidated workflow evidence report

Generated 2026-10-14T10:11:35.568879+05:30. Evidence snapshot only; no subjects were rerun.

Inspected **3 imported project folders**. **3 pass the local protocol checks** below. Expected but absent folders: Cirq, Flexget, Pillow, PyGithub, airflow, celery, conan, dask, django-rest-framework, electrum, fonttools, graphene, hydra, hypothesis, ipython, kombu, libcloud, loguru, mitmproxy, prefect, pyramid, requests, salt, scikit-image, seaborn, setuptools, sunpy, tornado, urllib3, xonsh.

Across locally protocol-complete projects: **2,621 distinct JUnit test identities**, **0 observed flaky**, **2,610 passed every detection round**, and **11 excluded from the strict binary denominator**. Observed-flaky percentage: **0.0000%**; positive:negative ratio **0:2,610**.

These projects contribute **75 detection rounds** and **0.14 recorded detection process-hours**, excluding baseline, setup, and scheduling overhead. Projects with three reverse rounds retain all 27 rounds.

Across all parsed folders, including unverified/ambiguous evidence: **2,621 JUnit identities in the per-project union**, **0 observed outcome-flip identities**, **2,610 all-pass identities**, **0 pass+skip/missing**, **11 skip-only**, **0 duplicate identities**. These are exploratory counts, not a frozen dataset size. Changing parameter IDs inflate the union for some projects; module-collection skips also appear as JUnit records.

Audit categories: 3 locally protocol-complete without identity exclusions; 0 complete with documented identity exclusions; 0 identity/other issues; 0 legacy unverified; 0 without detection evidence. Configured folders absent from this import: click, flask, filelock, fsspec, httpx, urllib3, rich, pytest, ipython, reframe, loguru, freezegun, fonttools, graphene, pyramid, kombu, tornado, pygithub, djangorestframework.

## Imported-folder evidence and remaining gaps

Copying the entire artifact `repos/<project>/` folder is the right core import: retain results/execution_manifest.json, all original/random/reverse JUnit XML, logs (including baseline XML), environment.json, baseline_state.json, setup_state.json, env_snapshot.txt, setup_log.md, and any dependency snapshot/setup recipe. The packager does not include full upstream source; source must later be retrieved at the recorded commit for static features.

Also preserve the original downloaded ZIP and its sibling/top-level provenance.json, checksums.json, and system_packages.txt, ideally in a separate directory per workflow run ID and attempt. Copying only the nested project folder omits these archive-level records. Their recovery normally requires re-extracting the download, not rerunning tests. Do not merge attempts or overwrite differing environments.

Current project-specific recovery decisions are recorded in `reports/evidence-recovery/EVIDENCE_RECOVERY_REPORT.md`. Any `protocol_complete_with_exclusions` row retains only identities outside the commit-bound, source-hash-verified resolution rules. Original XML and original identifiers are preserved, with exclusions exported per identity. No changing parameter values are silently merged.

## Scope and interpretation

- Protocol-complete means a matching passing baseline XML, standalone/embedded environment identity, complete expected checkpoint records, valid XML, consistent retained JUnit identities, and expected ordering seeds. Source-verified exclusions are explicit where needed. It is a local structural audit, not a claim of fully verified archive provenance or causal validity.
- Primary descriptive target: at least one PASS and one FAIL/ERROR in parsed detection rounds. Strict negatives pass every recorded detection round. PASS+SKIP/missing, skip-only, failure-only, and ambiguous duplicate identities are separated. Project-level acceptance is required before considering these labels for a primary dataset.
- Baseline observations are gate evidence, excluded from detection outcome counts. Tests include parameterized JUnit cases; these are not independent source functions. File + classname + name are preserved to avoid class collisions, but canonical pytest/source mapping remains pending.
- Reordered-only failures are configuration patterns, not confirmed OD. pytest-randomly may affect runtime seeds as well as order. Mixed original outcomes also do not establish a causal NOD subtype.
- CANNIER membership/revision is compared against the vendored authors' inventory. Same revision does not mean identical environment, labels, execution budget, features, or full replication.
- Duration is the sum of checkpointed detection process durations, excluding setup/baseline. It is neither summed testcase time nor a measurement of hybrid-detection savings. Legacy durations are withheld.
- General archive provenance remains outside this folder audit. Graphene was separately recovered with a downloaded ZIP digest matching GitHub artifact metadata and retained workflow provenance; see the recovery report. Newly computed hashes for other imported files freeze the current snapshot rather than retrospectively verifying downloads. No workflow success badge or run URL is inferred for other projects.

Strict flaky percentage = `100 × flaky / (flaky + all-pass)`. F:N is the same unrebalanced positive:negative count ratio. `project_summary.csv` also gives an active-outcome percentage including pass+skip/missing records; this broader denominator is not the primary binary dataset.

## Locally protocol-complete cohort by repository group

| Group | Projects | JUnit identities | Observed flaky | All-pass | Excluded | Flaky % strict |
|---|---:|---:|---:|---:|---:|---:|
| CANNIER same revision | 0 | 0 | 0 | 0 | 0 | N/A |
| CANNIER changed/unknown revision | 0 | 0 | 0 | 0 | 0 | N/A |
| additional | 3 | 2,621 | 0 | 2,610 | 11 | 0.0000 |

## Per-project results

Counts below describe all parsed identities, including exclusions and legacy evidence. Headline totals use only retained identities in the two protocol-complete categories. The eligibility table specifies the primary cohort.

| Project | Audit status | CANNIER relation | Commit | JUnit identities (union) | O/R/Rev | Flaky | All-pass | Pass+skip/missing | Skip-only | Fail-only | Duplicate | Flaky % strict | F:N |
|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| attrs | protocol_complete_local_checks | additional | `ee66e727` | 1,412 | 12/12/1 | 0 | 1,401 | 0 | 11 | 0 | 0 | 0.0000 | 0:1401 |
| tenacity | protocol_complete_local_checks | additional | `32ac68f0` | 185 | 12/12/1 | 0 | 185 | 0 | 0 | 0 | 0 | 0.0000 | 0:185 |
| werkzeug | protocol_complete_local_checks | additional | `f97c3056` | 1,024 | 12/12/1 | 0 | 1,024 | 0 | 0 | 0 | 0 | 0.0000 | 0:1024 |

## Retained identities and primary cohort eligibility

| Project | Retained identities | Excluded identities | Eligible flaky | Eligible all-pass | Flaky % strict | Primary project eligible |
|---|---:|---:|---:|---:|---:|---|
| attrs | 1,412 | 0 | 0 | 1,401 | 0.0000 | yes |
| tenacity | 185 | 0 | 0 | 185 | 0.0000 | yes |
| werkzeug | 1,024 | 0 | 0 | 1,024 | 0.0000 | yes |

## Raw detection observations and timing

These are repeated testcase rows, not distinct tests. Repeated identities are retained in these raw totals but quarantined from labels.

| Project | Baseline | Recorded baseline count | PASS rows | FAIL rows | ERROR rows | SKIP rows | Rounds with FAIL/ERROR O/R/Rev | Detection hours |
|---|---|---:|---:|---:|---:|---:|---|---:|
| attrs | PASSED | 1412 | 35,025 | 0 | 0 | 275 | 0/0/0 | 0.054 |
| tenacity | PASSED | 185 | 4,625 | 0 | 0 | 0 | 0/0/0 | 0.017 |
| werkzeug | PASSED | 1024 | 25,600 | 0 | 0 | 0 | 0/0/0 | 0.064 |

## Configuration patterns among observed flaky tests

| Project | Mixed original outcomes | Failure only under reordering | Original failure/pass elsewhere | Other |
|---|---:|---:|---:|---:|
| attrs | 0 | 0 | 0 | 0 |
| tenacity | 0 | 0 | 0 | 0 |
| werkzeug | 0 | 0 | 0 | 0 |

## Project audit details and effective observation budgets

### attrs

- Commit: `ee66e7274852438cc23d4240a1a9cd632fda8b52`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `d5cb658c174fec62de038029d09a6025e32c2c8bf6961bbcb94f1d38d8a11b62`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{0: 11, 25: 1401}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### tenacity

- Commit: `32ac68f0941319c0d2f4fb927f96e4ee29bb46c6`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `6eee45249fd179ea15aeafc70f6df75618a76cb7703014ab9f04287fd3ae9946`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{25: 185}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### werkzeug

- Commit: `f97c305673ba121a1dae6764c37e8be48907a1d1`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `65142da7d27a8cefa63cd9ae35577c298a11e75c2b16572ac3762b41b77fa295`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{25: 1024}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

## Deliverables and reproduction

- `project_summary.csv` and `audit.json`: project counts, statuses, membership, exclusions, and issues.
- `rounds.csv`: each checkpoint/file, ordering seed, exit code, raw outcomes, timing, and validation issues.
- `test_details.csv.gz`: every original test identity, descriptive label, effective N, outcomes, exclusion reason, project audit status, and primary eligibility. Only primary_eligible=True rows qualify for the binary cohort; eligible_identity alone does not override a legacy/failed project status. Decompress with any gzip tool or Python gzip.open. P=PASS, F=FAIL, E=ERROR, S=SKIP, D=duplicate identity, M=missing; character positions follow each project's round_order in audit.json.
- `evidence_hashes.csv`: SHA-256 of parsed baseline/detection XML and supporting project metadata. Raw files remain unchanged.
- `observed_flaky_tests.csv`: a convenient uncompressed subset of the test export; project audit status must accompany its interpretation.

Reproduce with `python scripts/consolidate_workflow_evidence.py --repos-dir <imported-repos> --output reports/workflow-audit --resolution-rules reports/evidence-recovery/identity_resolution_rules.json --source-root <pinned-source-root>`. Omit resolution arguments for the conservative audit without source-verified exclusions.

This report supersedes historical aggregate counts for this imported snapshot. It does not yet constitute a source-resolved training dataset or model-training result.
