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

### Hydra Black build prerequisite

Implemented: Hydra's bootstrap installs `setuptools-scm==5.0.2` before the
snapshot is installed with build isolation disabled. Black 20.8b1 uses
`use_scm_version` in setup.py; missing version-generation tooling can produce
the reported 0.0.0 metadata. Keep Black's original pin. Locally verified:
Black 20.8b1 builds with pip 23.3.2, setuptools 57.5.0, wheel 0.37.1 and
setuptools-scm 5.0.2 in a temporary Windows Python 3.11 environment, both
with and without toml. This does not verify Hydra's Ubuntu Python 3.8
setup or baseline. Rerun the current branch in CI; if metadata still fails,
inspect setup-bootstrap.log for the installed version-generation tooling.

### FlexGet six dependency correction

Implemented: override `six==1.16.0` with `six==1.15.0` in FlexGet's effective
requirements, preserving the original author snapshot. The supplied CI `pip check`
output verifies that the pinned FlexGet 3.1.134 requires exactly six 1.15.0.
Dependency checks and the strict baseline gate remain enabled. The corrected
FlexGet setup and baseline await CI verification.

### Electrum crypto test prerequisite

Implemented: add `pycryptodomex==3.10.1` to Electrum's effective requirements
and required setup distributions, preserving the original author snapshot.
The supplied CI log fails `test_pycryptodomex_is_available`; the pinned
`electrum/crypto.py` imports `Cryptodome` and requires version 3.7 or newer.
The snapshot includes `cryptography` but omits `pycryptodomex`. The selected pin
also occurs in the vendored Prefect snapshot; it is an explicit environment
correction, not a recovered Electrum author pin. Tests and the strict baseline
gate remain unchanged. The corrected Electrum baseline awaits CI verification.

### Conan CMake prerequisite

Implemented: add `cmake==3.15.3` to Conan's effective requirements, preserving the
original author snapshot. The pytest environment prepends the subject virtualenv
bin directory to PATH, so the pinned CMake takes precedence over system CMake
3.16.3. The supplied CI baseline log verifies that `test_default_cmake` expects
the 3.15 series and rejects 3.16.3. The test and strict gate remain unchanged;
the corrected Conan baseline awaits CI verification.

### Cirq dependency snapshot corrections

Implemented: explicit overrides set typing-extensions to 3.10.0.2 (codeowners
requires >=3.7,<4), typed-ast to 1.4.3 (mypy requires >=1.4,<1.5), and filelock
to 3.4.1 (virtualenv requires >=3.2,<4). The supplied CI log verifies the original
snapshot fails `pip check` on these three conflicts before baseline execution.
The author snapshot remains unchanged; effective requirements and the recipe are
packaged as evidence. These corrections await CI dependency and baseline
verification. Keep `pip check` enabled and rerun baseline-only.

The subsequent supplied Cirq baseline reaches 1,293 passing tests before
`test_plot_does_not_raise_error` fails: Matplotlib's `_check_1d` applies
`x[:, None]` to a pandas DataFrame and propagates `pandas.errors.InvalidIndexError`.
Implemented: override Matplotlib 3.5.1 with 3.5.2, whose upstream `_check_1d`
unpacks pandas input to NumPy before inspecting dimensions. This is an explicit
dependency correction, with no changes to Cirq source, tests, or labels. The
original snapshot remains preserved. The affected test and full baseline await
CI verification in the corrected environment.

### Airflow localhost SFTP prerequisite

Implemented: the shared executor starts a loopback-only OpenSSH server for Airflow,
with a temporary job-local RSA key for the unprivileged `cannier` test process to
authenticate as `root`, as required by the pinned SFTP tests. Password authentication
is disabled; the server host key is recorded in `cannier`'s known_hosts. SSH and
SFTP authentication are checked before the pipeline starts. Subject source and
baseline gate rules are unchanged. The supplied failed baseline logs show
`localhost:22` connection refusal; this service setup has not yet been verified
in a new GitHub Actions Airflow baseline. Rerun baseline-only before full mode.

The subsequent supplied CI log empirically verifies that the SFTP tests pass,
but stops at `SSHHookTest.test_ssh_connection` with public-key authentication
failure. The pinned SSHHook uses `getpass.getuser()` when `ssh_default` has no
login, so the executor now authorizes the job key for `cannier` as well as `root`
and preflights both logins. This additional correction is implemented but awaits
CI verification; the complete Airflow baseline has not passed.

The later supplied CI log reaches 1,924 passing tests, including the SSH tests,
then fails `ConfTest.test_broker_transport_options` with missing
`visibility_timeout`. Implemented: the subject recipe now supplies the four
broker fixture values from the pinned upstream
`scripts/in_container/airflow_ci.cfg` through pytest environment variables:
visibility_timeout=21600, _test_only_bool=True, _test_only_float=12.0, and
_test_only_string="this is a test". The shared environment builder applies these
only to Airflow baseline and detection subprocesses. The recipe is included in
the environment fingerprint and evidence. This restores upstream CI fixture
settings without changing subject tests or bypassing the gate; the corrected
configuration test and complete baseline await CI verification.

The latest supplied Airflow retry fails `TestLocalClient.test_trigger_dag`:
`example_bash_operator` loads from source but is absent from DagModel. The pinned
session fixture skips resetting the database when `~/.airflow_db_initialised`
exists, so failed attempts can leave database changes for later processes.
Implemented: pass the upstream `--with-db-init` option on each baseline attempt
and detection round. This requests the existing upstream reset procedure before
each complete suite; it does not reset state between individual tests, so
within-suite order dependence remains observable. The missing record is verified
by the supplied traceback; attribution to retained database state and resolution
by this correction await CI verification. Retain all earlier attempt logs.

### Conan version-selected CMake tools

Implemented: the shared executor also installs official Kitware CMake releases
3.15.7, 3.16.9, 3.17.5, and 3.19.7 into the exact `/usr/share/cmake-<version>/bin`
locations in the pinned `conans/test/conftest.py`. Downloads are checked against
the release SHA-256 manifests, and each executable is checked as `cannier` before
baseline execution. Conan's fixture prepends these locations for tests marked
with the respective CMake series. This supplies all four versions requested by
`tools_versions_test.py`; the earlier virtualenv-only 3.15.3 addition did not
provision the explicit 3.16/3.17/3.19 locations. CI execution remains unverified.

The subsequent supplied Conan CI log fails `AutoToolsConfigureTest.test_pkg_config_paths`
because GitHub's Python setup exports `PKG_CONFIG_PATH` pointing to its Python
installation. Implemented: Conan's recipe explicitly removes this inherited
variable from baseline and detection subprocesses. The test expects no
PKG_CONFIG_PATH when no package configuration paths were provided. The parent
environment and other subjects are unaffected; the removal is recorded in the
fingerprinted recipe. This correction awaits a new Conan CI baseline.

The latest supplied Conan log fails
`test_editable_cmake_linux[Ninja]` because CMake cannot find the Ninja build
program. Implemented: the Conan setup step installs Ubuntu's `ninja-build`
package and checks `ninja --version` as `cannier` before either baseline-only
or full execution. The shared prerequisites already install `build-essential`.
This supplies the requested generator without changing the upstream tests or
baseline gate. Resolution of the failure and the complete baseline await CI
verification; retain the earlier failed-attempt logs.

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

### Dask scheduler import failure: upstream blocker

The supplied 2026-10-09 baseline log fails at
`dask/tests/test_layers.py::test_scheduler_highlevel_graph_unpack_import[True-_dataframe_shuffle-pandas.]`:
pandas submodules appear in the scheduler after its initial module snapshot.
This matches upstream issue https://github.com/dask/dask/issues/8480.
An upstream comment links the import behavior to Distributed's shuffle extension:
https://github.com/dask/distributed/pull/5695#issuecomment-1035371765.
Upstream's temporary response was to mark the test as expected to fail:
https://github.com/dask/dask/pull/8724.

The current recipe pins Dask `d5bbad0b` and Distributed `2022.2.0`.
No verified environment-only repair has been established for these pins.
The missing `jupyter-server-proxy` message is informational, not the failed assertion.
Keep the baseline discarded if all three permitted attempts fail. Do not apply
the upstream xfail, exclude the test, change dependencies speculatively, or count
this failure as a flaky label without both passing and failing execution evidence.
A patched or differently pinned experiment would need separate configuration,
provenance and evidence; it would not repair the untouched historical experiment.

### Implemented setup corrections

- Libcloud: the supplied setup log cannot install `codecov==2.1.10` from the
  package index. The pinned upstream `tox.ini` invokes this coverage uploader
  only after coverage execution; FlakeXplain invokes pytest directly.
  Explicitly exclude `codecov` from the effective snapshot, preserving all
  other pins and the original author snapshot. The exclusion and reason are
  recorded in `snapshot_exclusions` in the fingerprinted setup recipe, and
  effective requirements are archived. This is a tooling-corrected environment;
  successful installation and a complete passing baseline await fresh CI
  verification. No upstream tests or baseline criteria are changed.
- FlexGet: the 2026-10-09 baseline failed at
  `flexget/tests/test_urlrewriting.py::TestURLRewriters::test_rutracker`
  because `api.t-ru.org` did not resolve and its cassette is absent at the pinned
  commit. Restore the authentic recording from upstream commit
  `dabf5803ff8863b6be0f387d4ed54629230cd24a` (November 2022).
  The bundled bytes are checksum-verified before installation; the recording and
  provenance are archived in experiment logs. Existing differing recordings are
  rejected. This supplements the historical fixture set and must be disclosed
  as a fixture-corrected experiment, not an untouched-checkout replication.
  No test code or expected result is changed. Full baseline validation still
  requires a fresh GitHub Actions job; this fix does not establish a passing suite.
- Hypothesis: install `hypothesis-python/examples/example_hypothesis_entrypoint`
  as an editable test package, with dependency resolution and build isolation
  disabled. Its setuptools entry point registers the non-negative strategy used
  by `test_registered_from_entrypoint`; installing only `hypothesis-python`
  leaves that hook undiscoverable. The installation is logged and included in
  the recipe/environment fingerprint. No upstream tests are changed or excluded.
  Full baseline validation requires a fresh GitHub Actions job.
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


### Experiment user correction

The initial shared container ran the pipeline as root. Celery's mocked privilege
change test still sees real root UID/GID and fails its security check. The authors'
Dockerfile uses a non-root user. Shared jobs now create a cannier user, grant it
ownership of the checked-out workspace and isolated execution root, and run setup,
baseline and detection as that user with its own HOME. System package installation
and artifact packaging stay in the workflow's administrative context. New-subject
environment identities include execution UID/GID. No source test is patched or
skipped. Retry failed baselines in fresh jobs; never mix root/non-root evidence.

Airflow also adds argparse==1.4.0 to satisfy snakebite-py3 3.0.5 metadata.
Its original snapshot is preserved and its effective requirements are archived
with the artifact. Retry baseline-only in a fresh job; the baseline remains unverified.

Airflow import precedence: its `tests/kubernetes` package shadows the installed Kubernetes SDK when `tests` leads `PYTHONPATH`. The Airflow recipe now puts its virtual environment site-packages first, retaining tasks/tests/src/root paths. This applies consistently to baseline and reordered execution and is recorded in the recipe fingerprint. No tests are excluded. A subprocess regression check reproduces the collision and verifies SDK resolution; full Airflow execution still requires GitHub Actions validation.

Airflow follow-up: dependency path priority now preserves standard-library paths (including extension modules) before site-packages, followed by required source paths. This prevents the legacy argparse distribution required by snakebite-py3 from overriding Python 3.8 argparse and breaking pytest allow_abbrev. The subprocess regression verifies both Kubernetes SDK and standard-library argparse imports.
