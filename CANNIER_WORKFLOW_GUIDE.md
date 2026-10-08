# CANNIER five-subject execution and consolidation

Implemented: one manually dispatched workflow with five independent jobs for IPython,
Loguru, FontTools, Graphene, and Pyramid. Commits match the CANNIER subjects.json.
IPython and Loguru reuse existing setup configurations and environment locks.
FontTools, Graphene, and Pyramid use upstream test extras and pinned pytest tools;
their complete dependency resolutions and clean baselines are not yet empirically verified.
Python 3.8.18 is a historical-subject environment, not the main project's Python requirement.

Sources:
- https://github.com/flake-it/cannier-experiment/blob/main/subjects.json
- https://link.springer.com/article/10.1007/s10664-023-10307-w

## Run on GitHub

1. Commit and push the new workflow, this guide, and changes to scripts/setup_repos.py,
   scripts/runtime.py, and scripts/parse_results.py to your default branch.
2. Open Actions > FlakeXplain CANNIER five subjects > Run workflow.
3. Choose subject=all and mode=baseline-only. Inspect each project's setup and baseline logs.
4. For each passing project, dispatch subject=<project>, mode=full. Full mode prepares a
   fresh environment and checks the baseline again before running 12 original-order,
   12 seeded random-order, and 1 reverse-order rounds in serial within each project.
   You can also dispatch all/full; projects with failed baselines stop automatically.
5. Download each full-run artifact before its 30-day retention expires. Unzip it to find
   cannier-<subject>-evidence.tar.gz. Keep the original download with its run ID/attempt.

A failed baseline is a discarded candidate, not a non-flaky project. Setup errors and
job timeouts are incomplete experiments. Inspect their preserved logs before retrying;
do not patch tests, ignore failures, or merge rounds across separate environments.
These 25 rounds are the FlakeXplain protocol, not a reproduction of CANNIER's run budget.

## Add evidence to the consolidated report (PowerShell)

The tarball contains repos/<subject>/ with results, execution_manifest.json inside
results, baseline logs/state, environment metadata, setup log, and source.tar.gz.
The nested source archive preserves the exact source for later fixture/helper analysis.

1. Extract each downloaded tarball into a separate staging directory, for example:

```powershell
New-Item -ItemType Directory -Force .\imports\ipython-run123
 tar -xzf 'C:\path\to\cannier-ipython-evidence.tar.gz' -C .\imports\ipython-run123
```

2. Inspect repos/<subject>/baseline_state.json: status must be PASSED. For a complete
   full experiment, results/execution_manifest.json must contain 12 original_rounds,
   12 random_rounds and 1 reverse_rounds record, with existing complete XML files and
   matching environment IDs. Baseline-only downloads contain no detection labels.
   Keep failed/incomplete artifacts in imports for diagnostics; do not call them completed.
3. Copy the staged project directory into the project's repos directory. Example:

```powershell
# Run only if repos/ipython does not already exist.
Copy-Item -LiteralPath .\imports\ipython-run123\repos\ipython -Destination .\repos\ipython -Recurse
```

   Repeat for the other subjects. If a destination already exists, archive that entire
   directory first and deliberately choose one complete attempt. Never overlay XML
   from different commits, environments, run IDs or attempts. Preserve provenance.json
   with each archived download. Keep all previous projects' evidence directories.
4. Explicitly point the parser to the workspace evidence to avoid Windows AppData
   execution directories taking precedence:

```powershell
$env:FLAKEXPLAIN_REPOS_DIR = (Resolve-Path .\repos).Path
python scripts/parse_results.py
Remove-Item Env:FLAKEXPLAIN_REPOS_DIR
```

5. Review FlakeXplain_Flaky_Report.md. Verify the five subjects' commits and round counts,
   then check Combined Completed-Run Totals. The parser recalculates totals from raw
   evidence for every registered project; do not paste workflow summary rows manually.
   Back up the existing report before regeneration. Existing evidence must be present
   under workspace repos for it to remain in this consolidated report.

## Research interpretation

No new test outcomes or model improvements have been empirically verified by this change.
Repeated-run outcomes, seeds and flip counts remain label evidence only. The fixture/helper
feature hypothesis needs a separate static extraction implementation and controlled ablation
against the base features on fixed project-disjoint splits. The existing OD/NOD classification
is observational; confirm suspected dependencies with targeted reruns before cause claims.
Label passing tests as not observed flaky after N runs. New observed outcomes need not match
CANNIER because dependency versions, operating systems and execution budgets differ.


## Two additional subjects: Kombu and Tornado

Implemented separate workflows:
- Actions > FlakeXplain CANNIER Kombu
- Actions > FlakeXplain CANNIER Tornado

Each has mode=baseline-only (default) and mode=full. Run baseline-only first,
then full after a clean pass. Each full run checks its baseline afresh and
runs 12 original, 12 random, and 1 reverse round. Download the tarball artifact
and follow the same staging/import instructions above using kombu or tornado.
Both subjects are registered with the consolidated parser.

Pinned CANNIER commits:
- celery/kombu: 2aeb73248b4a0bf8ad3de81a0f40733e7cd42255
- tornadoweb/tornado: 2047e7ae3c825bf52dad10cc8402d09e11091bc1

Kombu preserves upstream setup.cfg collection of t/unit and the historical
pytest<=5.3.5 requirement, using pytest-randomly 3.5.0. It does not claim to
cover broker-dependent integration suites. Tornado uses its basic dependency
profile; upstream tests requiring optional pycurl, Twisted or pycares may skip.
Skips remain unlabelled unless the same test has sufficient pass/fail evidence.
Neither baseline nor detection results have been empirically verified yet.
Keep snapshots and report this dependency/collection scope in the paper.

These two additions bring the newly configured subjects to five: FontTools,
Graphene, Pyramid, Kombu and Tornado. IPython and Loguru are existing subjects.
