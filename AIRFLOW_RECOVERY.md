# Airflow execution and recovery

Runtime prerequisite correction (implemented, complete CI result pending):
Airflow now uses Python 3.8.7, before the Python 3.8.8 query-separator change
that breaks this pinned suite's semicolon URL assertion. Ubuntu's Python 2.7
is installed for the operator tests that explicitly request python2/python2.7.
The Airflow container runs with Docker's init process so orphaned children can
be reaped after process-group termination.

The disposable base Python's site-packages contains an explicit .pth bridge to
Airflow's dependency environment. This recreates globally installed dependency
visibility for upstream --system-site-packages child virtualenvs while isolated
child virtualenvs cannot see those packages. Both modes are checked using real
virtualenvs before execution; the bridge, checksum, Python 2 version and PID 1
are recorded in logs/airflow-runtime-fixtures.json. The seven previous failure
areas are checked first as diagnostic prerequisites with INFO logs, then the
complete strict baseline still runs. Diagnostic tests never supply labels or
replace a complete baseline. This is a new environment; previous failed-run
evidence remains separate.

Implemented: Airflow's outer pytest launcher prioritizes standard-library and
installed SDK imports in its own sys.path. PYTHONPATH retains tasks/tests/src/root
without exporting outer site-packages into isolated child virtual environments.
This addresses the isolation failure in test_no_system_site_packages seen in
workflow run 37943045493. Full historical execution requires CI verification.

The Airflow baseline executes the full suite to reveal all failures. Before
repeating a failed baseline, pytest's last-failed cache checks only its failures.
If they still fail, execution stops without repeating the passing tests. A focused
pass is diagnostic only: a complete passing original-order baseline is required
before detection. Baseline and diagnostic XML/logs are kept separately.

Airflow jobs restore/save execution storage using GitHub Actions cache, including
after failure. Use the Airflow workflow with mode `full`; another dispatch or
rerun of the same recipe can reuse the passing baseline and completed detection
rounds. Actual test failures (pytest exit 1) within complete detection rounds are
valid evidence and do not abort the 25-round experiment. An interrupted round is
rerun as a whole to preserve order-dependent behavior.

Cache scope hashes the executor workflow, pipeline code and replication recipes.
CI fingerprints use that scope in place of the ephemeral host/kernel identity,
and retain Python, installed Python/system packages, OS release, source revision,
source changes, recipe, execution UID/GID and repository path. Changed recipes
start fresh; results from different environments are never silently combined.
Cache eviction or a hard cancellation before save can require fresh execution.
The cache is recovery storage; the 90-day evidence artifact is the result archive.

Full mode packages the generated report together with XML, execution manifest,
environment information, diagnostics and checksums. A report from a failed or
interrupted job remains partial; only a passing baseline and 12 original,
12 random and 1 reverse completed rounds establish complete detection evidence.
