# FlakeXplain execution

## Verified cause of the filelock baseline failure

The original Windows checkout runs on Google Drive (G:). A diagnostic using the
unmodified filelock code reproduced WinError 87 for invalid filenames there.
The same calls on the local C: filesystem returned WinError 123, which the upstream
test expects. The colon case also differed: permission denied on G:, invalid
argument/syntax error on C:. Do not patch assertions or skip these tests.

On Windows the runner now defaults to:
`%LOCALAPPDATA%\FlakeXplain\<project-path-hash>\repos\<repository>`.

The original Drive checkout supplies the exact commit for a fresh local checkout.
Tracked modifications cause migration to stop for review. Virtual environments
are recreated locally, not copied. Original XML, reports, and source checkouts
remain in place. The local run is a separate recorded environment.

## Commands

Run from the project directory:

```powershell
python run_all.py filelock --baseline-only
python run_all.py filelock
# HTTPX remains discarded on Windows; urllib3 runs in GitHub Actions.
```

The second command reuses the verified environment and passing baseline, then runs
12 original + 12 random + 1 reverse round. Repeating a command resumes completed
rounds after checking environment identity, round/seed metadata and complete XML.

To choose a different local disk:

```powershell
python run_all.py filelock --work-dir C:\FlakeXplain
```

To deliberately repeat the baseline: `--force-baseline`.
To reinstall dependencies before any detection evidence exists: `--refresh-setup`.
Use a new work directory for a changed environment that already has detection
results. Baseline failure returns a nonzero status and prevents detection.

## Implemented runtime improvements

- Local checkouts and virtual environments avoid Drive filesystem incompatibility.
- Setup installs test dependencies in one pip transaction, reusing pip's cache.
  HTTPX's documentation, lint and publishing tools are not installed.
- Successful setup is reused only while the source and environment fingerprint match.
- Failed baseline attempts stop on the first failure; a passing attempt executes
  the entire suite. Up to three attempts remain permitted.
- No separate collection-only subprocess: successful baseline XML records the count.
- Commands stream complete output to terminal and logs, with a 30-second quiet-period
  heartbeat. Pytest capture remains enabled to preserve test behavior.
- Slowest 15 test durations are printed.
- Each completed detection round saves its manifest immediately. Invalid/incomplete
  rounds are not resumed or used as labels. Baseline XML lives outside results/.
- Tests within each round remain serial; no xdist, fewer rounds, or synthetic labels.
- A per-repository OS lock prevents duplicate orchestrators in the same work directory.

## Evidence and reporting

In each execution checkout:
- `env_snapshot.txt`, `environment.json`, `setup_state.json`: dependencies/provenance.
- `baseline_state.json`, `logs/baseline-*/`: gate state and complete attempt logs/XML.
- `results/execution_manifest.json`, `results/*_run_*.xml`: detection evidence.
- `logs/*_run_*.log`: round stdout/stderr.

The report records the execution directory. Repositories without a local checkout
retain their separate legacy evidence from the original project directory. Results
from two environments of the same repository are never merged.

On this laptop, closing the lid must not put Windows to sleep if running locally.
For laptop-independent execution, use GitHub-hosted Actions (workflow included) or
an always-on server. Cloud results constitute another environment and require their
own baseline. GitHub-hosted jobs have a six-hour limit; artifacts are uploaded even
when a job fails. A cloud workflow cannot be launched until these files are in a
GitHub repository with Actions enabled.

## Verification on 2026-09-08

Filelock at 82f66d7b, Python 3.11.9, local C: checkout: the complete baseline
passed on attempt 1 with 1,106 passed and 236 upstream skips in 234.47 seconds
(subprocess wall time). The user-provided failed G: attempt took 584.74 seconds.
That is approximately 60% less time in these two observations, not a controlled
benchmark or a guarantee for every round. Re-running the baseline-only command
verified that setup and the passing baseline are reused.

The two Windows test dependency snapshots in environment-locks/ are used as pip
constraints for new environments, including the cloud workflow. Sources remain
pinned separately. Cloud validation has not been performed.

## GitHub Actions: urllib3

The workflow follows the official [setup-python](https://github.com/actions/setup-python)
and [upload-artifact](https://github.com/actions/upload-artifact) interfaces. It
runs only urllib3 on Ubuntu 24.04 with Python 3.11.9. The source is pinned at
`a5d70ebfd6a30ceba0e9cc322089a6497dcd643e`.

The dependency setup mirrors urllib3's own CI: `uv==0.11.7`, the repository's
committed `uv.lock`, its `dev` dependency group, and its socks, Brotli, Zstandard,
and HTTP/2 extras. FlakeXplain adds only `pytest-randomly==5.0.0`. Every pytest
invocation uses urllib3's upstream strict-marker and socket restrictions; public
network access is disabled while localhost and Unix sockets remain available.

Before pushing, ensure `.gitignore` excludes `repos/`, virtual environments,
Python caches, logs, and the temporary inspection checkout. The project root is
not currently a Git repository.

After pushing the project files to a GitHub repository:

1. Open the repository's **Actions** tab.
2. Select **FlakeXplain urllib3 detection**.
3. Choose **Run workflow**, then **Run workflow** again.
4. The laptop can be shut down after GitHub shows the job as queued or running.
5. When the run finishes, download the `flakexplain-urllib3-...` artifact from
   the run summary.

The artifact contains environment provenance, baseline evidence, per-round logs,
25 JUnit XML files and the generated report. It is uploaded even after a failed
stage. GitHub-hosted jobs have a six-hour limit, so the experiment step has a
330-minute limit that leaves time for artifact upload. A rerun starts on a fresh
host; completed rounds are not automatically restored from a prior workflow run.

HTTPX was empirically discarded on Windows after three baseline attempts. The
first two reached 1,342 passing tests before the same multipart test failed due
to Windows `TemporaryFile` wrapper behavior. Its upstream source and tests were
not changed or skipped.