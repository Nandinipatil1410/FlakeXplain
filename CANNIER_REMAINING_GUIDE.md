# Remaining CANNIER subjects: execution and research plan

## Implemented and verified scope

Implemented: 20 individual manual launchers, one batch launcher, a shared executor,
setup/runner/parser registration, pinned author dependency snapshots, and an
allowlisted evidence packager with checksums. Local pipeline tests and workflow
syntax/embedded-script checks pass. No new subject baseline, detection count,
fixture feature, trained model, or prediction improvement is empirically verified.

Source manifest and snapshots are vendored from CANNIER replication revision
b96d6ed02e98d514eb6a92ca264a082234cb9728, with its license and README.
See cannier-replication/inventory.json for all 30 subjects and configured status.
Existing IPython, Loguru, FontTools, Graphene, Pyramid, Kombu, PyGithub,
Django REST framework and urllib3 are excluded from the new batch. Tornado remains
a discarded historical candidate with its earlier workflow; it is not retried.
The existing urllib3 experiment uses a different commit from the CANNIER subject
manifest. Project overlap does not establish exact replication.

| Pipeline key | Repository | Pinned commit |
|---|---|---|
| airflow | https://github.com/apache/airflow | `c743b95a` |
| celery | https://github.com/celery/celery | `552e067b` |
| cirq | https://github.com/quantumlib/Cirq | `782c14e0` |
| conan | https://github.com/conan-io/conan | `d5240749` |
| dask | https://github.com/dask/dask | `d5bbad0b` |
| electrum | https://github.com/spesmilo/electrum | `d8d2c180` |
| flexget | https://github.com/Flexget/Flexget | `4fb25084` |
| hydra | https://github.com/facebookresearch/hydra | `69d31ebf` |
| hypothesis | https://github.com/HypothesisWorks/hypothesis | `ccac4364` |
| libcloud | https://github.com/apache/libcloud | `449b315e` |
| mitmproxy | https://github.com/mitmproxy/mitmproxy | `4511ea7c` |
| pillow | https://github.com/python-pillow/Pillow | `92933b86` |
| prefect | https://github.com/PrefectHQ/prefect | `6b59d989` |
| requests | https://github.com/psf/requests | `a1a6a549` |
| salt | https://github.com/saltstack/salt | `bac2d1e6` |
| scikit_image | https://github.com/scikit-image/scikit-image | `8fbbb516` |
| seaborn | https://github.com/mwaskom/seaborn | `703259f2` |
| setuptools | https://github.com/pypa/setuptools | `4d64156d` |
| sunpy | https://github.com/sunpy/sunpy | `7c6e51e8` |
| xonsh | https://github.com/xonsh/xonsh | `e9b12c8b` |

## Push and run

Commit only the new workflow/pipeline files listed in the final instructions; keep
unrelated local report/AGENTS edits separate. Push to the default branch so GitHub
shows manual dispatch controls.

1. Actions > FlakeXplain CANNIER remaining subjects.
2. Select subject=all, mode=baseline-only. At most two subject jobs run at once;
   one failed job does not cancel another. Individual launchers are also available.
3. Inspect setup and baseline logs. Successful setup includes pip check; a passing
   baseline must execute the collected suite successfully, not merely collect it.
4. Dispatch full for each passing subject. Full runs rebuild in a fresh job and
   recheck the baseline, then run 12 original / 12 random / 1 reverse rounds.
   All/full is possible, but still stops each failing subject at its gate.
5. Download full-run evidence before the 90-day requested retention expires (the
   repository/organization may enforce a shorter limit).

Each job has a six-hour limit and the pipeline step a five-hour limit. Large suites
and native builds may exceed them; partial output is retained when packaging can
run. Timeouts, collection failures, dependency conflicts and missing external
services are incomplete experiments, not non-flaky labels. Historical dependencies
may no longer build even with recorded pins. Diagnose the preserved logs; do not
silently upgrade, skip failing tests, or merge environments to obtain a pass.

Jobs use an Ubuntu 20.04 container on a hosted runner and Python 3.8.18. System
prerequisites follow the original Dockerfile, with additional build/image tools.
Dependency snapshots are restored without dependency resolution, then the pinned
subject is installed editable without dependencies, followed by pytest-randomly
3.5.0. pip check rejects inconsistencies. Bootstrap pip/setuptools/wheel/Cython,
Python patch version, runner resources and order plugin differ from the paper;
this is a FlakeXplain execution using author subject recipes, not exact replication.
Snapshots contain broad author environment packages (including developer tools),
which are retained to avoid guessing or silently omitting dependencies.

The source commit, installed package versions, recipe and snapshot digest are bound
to each new environment identity. Libcloud receives the authors' placeholder
secrets.py-dist -> secrets.py copy. No real cloud credentials are supplied.
Cirq and Hypothesis use the authors' package subdirectories. Salt uses the
specified unit subtree. Scikit-image retains the authors' pre-existing
not-test_reproducibility selection. Airflow's continue-on-collection-errors and
Dask's mock-flaky flags are deliberately omitted to keep collection errors fatal
and avoid enabling modified flaky behavior. These are documented protocol
changes, not claims of matching the paper's labels.

## Artifact import

New artifacts are regular GitHub ZIP downloads containing repos/<pipeline-key>,
provenance.json, system_packages.txt and checksums.json. There is no nested source
archive. The packager includes only XML/JSON/Markdown/text/log evidence and metadata;
it excludes Python files, binaries, virtual environments and source archives.
This may help download accessibility, but does not guarantee browser acceptance.

Extract to a staging directory. Verify checksums before import:

```powershell
python -c "import hashlib,json,pathlib; p=pathlib.Path(r'imports/EXTRACTED_ARTIFACT'); h=json.loads((p/'checksums.json').read_text()); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==v for n,v in h.items()); print('Checksums match')"
```

Inspect baseline_state.json for PASSED and results/execution_manifest.json for
12 original_rounds / 12 random_rounds / 1 reverse_rounds, matching environment IDs,
and complete XML. Preserve original artifacts and provenance. Copy the contained
repos/<key> directly into the workspace repos directory only after confirming the
destination does not already contain another attempt. Archive existing attempts
as whole folders; never overlay their XML. Retain earlier projects' evidence.

Then regenerate, backing up the old report under a unique filename:

```powershell
$stamp = Get-Date -Format yyyyMMdd-HHmmss
Copy-Item FlakeXplain_Flaky_Report.md "FlakeXplain_Flaky_Report.$stamp.backup.md"
$env:FLAKEXPLAIN_REPOS_DIR = (Resolve-Path .\repos).Path
python scripts/parse_results.py
Remove-Item Env:FLAKEXPLAIN_REPOS_DIR
```

## What the base paper did

The published experiment uses 30 Python projects (26 from previous work plus four
more) and tests from that subject set for model training and evaluation. Its main
pipeline uses stratified 10-fold cross-validation over pooled test cases: it is
not a project-held-out evaluation. It studies Random Forest and Extra Trees,
synthetic balancing variants, 18 features and several classification tasks.
For its corpus, it used 2,500 original-order runs, 2,500 shuffled runs and 30
feature-measurement runs, plus victim/polluter analysis. See Sections 4.2 and 5:
https://link.springer.com/article/10.1007/s10664-023-10307-w

Our 25-round evidence and observational OD/NOD categories cannot be treated as
identical ground truth or directly compared numerically to the paper's metrics.
The original replication output.zip is a separate potential evidence source;
validate identities and label semantics before any secondary analysis.

## Proposed experiment to test fixtures and helpers

Research question: Do fixture and helper context features improve prediction of
order-dependent victims on unseen projects, under a fixed detection protocol?
This is narrower than claiming improved overall CANNIER rerunning performance.

1. Audit the corpus first: restore missing Filelock evidence, investigate suspect
   Click/Flask timing, preserve collection/skip counts and explain exclusions.
   Validate suspected OD cases through replay of failing reordered prefixes and
   passing original prefixes, with polluter analysis when feasible. The current
   parser's pattern labels are provisional evidence, not proven causal categories.
2. Freeze per-test identities and source context (including parametrization and
   inherited tests), commits, environments, raw rounds, seeds, order and confidence.
   Retain natural imbalance. Not observed flaky after N runs is an uncertainty-aware
   negative; skips/failure-only tests are not negative training examples.
3. Define the target as observed/validated OD victim versus eligible passing controls.
   Keep NOD and uncertain cases separate for this target. They can form a separate
   general-flakiness experiment; do not casually pool incompatible labels.
4. Implement matched features: base-only; base+fixtures; base+helpers;
   base+fixtures+helpers. Resolve explicit and autouse fixtures, transitive fixture
   dependencies, scopes, parametrization, yield/finalizers and conftest visibility.
   Resolve helpers conservatively, with bounded call depth and explicit unknowns.
   Feature examples include scope counts, shared setup, mutable/global operations,
   filesystem/network/process usage and cleanup structure. These are candidates,
   not established causes of flakiness.
5. Reimplement/validate the paper's 18 features for a faithful base-feature arm.
   If using only a subset or proxy static features, name it an adapted baseline.
   Single-run dynamic measurements must be collected independently of detection
   evidence. Seeds, failure/flip counts, reordered outcomes and rerun timing are
   label evidence only, never classifier inputs. Extract code context for all
   tests, without selecting feature content based on outcomes.
6. Freeze outer project-disjoint folds before model selection. Use grouped inner
   validation only on training projects for feature selection, tuning, class
   weights and probability thresholds. Keep each project's tests/parameters and
   fixture context within the same fold. Use identical folds, samples, algorithms,
   tuning budgets and random seeds for all feature ablations. Random Forest and
   Extra Trees connect to the base paper; an interpretable model is a useful arm.
7. Report PR-AUC/average precision with its exact definition, precision, recall,
   F1, MCC, confusion matrices and per-project results. Accuracy alone rewards
   predicting the majority class. Report undefined metrics for folds lacking
   positives honestly. Use paired project-level uncertainty estimates, not an
   assumption that related test cases are independent samples. No SMOTE or
   duplicated test cases in the primary experiment under our project policy.
8. Assess extraction cost and robustness, then explain feature contributions and
   manually inspect examples. If claiming improved CANNIER cost/recall tradeoffs,
   additionally evaluate the guided rerunning policy at matched budgets/recall.
   Better classifier metrics alone do not prove cheaper flaky-test detection.

You do not need all 30 projects to start validating extraction and experimental
plumbing. Develop using designated training projects while remaining baselines run;
keep evaluation projects unseen. More eligible, diverse projects improve the test
of generalization, but running every candidate does not guarantee usable labels or
publication. Improvements must be demonstrated by controlled experiments.


## Explicit setup corrections after the first historical runs

- Celery: add argparse==1.4.0 to satisfy unittest2's declared dependency.
- Conan: replace six==1.16.0 with six==1.15.0 to satisfy the pinned Conan release.
- Subjects whose snapshots include Black: bootstrap setuptools-scm==5.0.2,
  required by Black's version metadata generation when build isolation is disabled.
  Keep the original Black version. This addresses a missing build prerequisite;
  verification on the GitHub runner is still required.

Original author snapshots remain unchanged. Runtime corrections are explicit in
remaining-configs.json, and effective requirements are recorded under each
corrected project's logs/effective-cannier-requirements.txt and copied into its
artifact. Recipes/snapshot digest remain bound to the environment identity.
The strict pip check and baseline gate remain in force. Retry the failed subjects
with baseline-only in new jobs after pushing these changes. Do not mix attempts.
