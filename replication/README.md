# Replication package: FlakeXplain v0.8 (MDFlaker on fresh GitHub Actions failures)

Status: **Implemented; data release pending guide approval.** The code below is in this repository.
The derived data are exported locally to `replication/data/`, which is git-ignored. Nothing has been
published yet.

The study collected failed pytest executions from recent GitHub Actions runs. It froze **1,659
candidate failures** from 8 Python projects and re-ran each one 30 times in a matching environment.
That labelled **1,292** of them: 409 flaky (≥ 1 pass in 30) and 883 not flaky (30/30 fail).
It then compared MDFlaker's reimplemented classifier with ours (ET-BF) under a frozen rule.
- Protocol: `reports/mdflaker-fresh-v0.8/PROTOCOL.md`, with amendments `AMENDMENT_B1.md`–`AMENDMENT_B3.md`.
- Results: `reports/mdflaker-fresh-v0.8/RESULTS.md`.

## Two ways to replicate

1. **Re-analysis (recommended).** Start from the exported derived data: candidates, features, labels
   and rerun outcome summaries. You can rerun the frozen analysis and the post-hoc diagnostics
   offline, without a GitHub token, in minutes (steps 5–6).
2. **Full re-collection (steps 1–4).** This re-executes collection, reruns and feature extraction.
   It cannot reproduce *the same* candidates. GitHub deletes Actions job logs after 90 days, and the
   probe window is always "the last 89 days". A re-collection is a new sample under the same procedure.

## Environment

- **Analysis:** Python 3.11.9 in the local virtual environment `.venv-pilot`, with:

  | Package | Version |
  |---|---|
  | scikit-learn | 1.7.2 |
  | shap | 0.51.0 |
  | numpy | 2.2.6 |
  | scipy | 1.15.3 |
  | pandas | 3.0.6 |

  Recreate it with:

  ```bash
  python -m venv .venv-pilot
  ```
  ```bash
  .venv-pilot/Scripts/python -m pip install scikit-learn==1.7.2 shap==0.51.0 numpy==2.2.6 scipy==1.15.3
  ```

  On Linux or macOS, use `.venv-pilot/bin/python`.
- **Collection, planning, labelling and features:** standard library only, plus `git` on `PATH`.
  Step 4 also uses the repository's `scripts/dataset_static.py` and `scripts/confirmation_features.py`.
- **Reruns:** GitHub-hosted runners (Ubuntu, Windows, macOS). The workflow sets up Python with
  `actions/setup-python@v5` and installs `uv` with `astral-sh/setup-uv@v6`. The harness itself
  (`mdflaker_v08_rerun_job.py`) uses the standard library only.
- **GitHub token:** needed only for collection. That means steps 1, 3 (artifact download) and 4
  (when the API caches are missing).
  - Pass it as the `GH_TOKEN` environment variable. It needs public-repository read access, plus
    Actions read access on the repository that runs the reruns.
  - The scripts never write the token to disk.
  - `mdflaker_v08_probe.py` reads `GH_TOKEN` when imported. Scripts that import it (`candidates`,
    `plan`, `collect`, `features`, `robustness`, `posthoc_extra`) need the variable to be *set*.
    For offline steps, any placeholder works: `GH_TOKEN=unused`.

All paths below are relative to the repository root. `local-evidence/` is git-ignored: it holds raw
CI logs, git clones and rerun artifacts, which are not redistributed.

## Pipeline

### Step 1: candidate collection

**1a. `scripts/mdflaker_v08_probe.py`: download failed CI job logs** *(token needed)*
- **Inputs:**
  - The GitHub Actions API.
  - The repository preference list `REPOS` in the script.
  - Environment variables:

    | Variable | Default | Controls |
    |---|---|---|
    | `PROBE_MAX_RUNS` | 40 | Failed runs per repo |
    | `PROBE_MAX_LOGS` | 40 | Logs per repo |
    | `PROBE_MAX_PAGES` | 5 | API pages per repo |
    | `PROBE_REPOS` | (the `REPOS` list) | Comma-separated repos to probe |
    | `PROBE_PARTIAL` | `probe_partial.json` | Resumable progress file |
    | `PROBE_SUMMARY` | `probe_summary.json` | Summary file name |

- **Filtering:**
  - Only failed runs in the last 89 days are kept.
  - Lint, docs, typing and release jobs or workflows are skipped, as are scheduled and
    `pull_request_target` events.
- **Outputs:**
  - `local-evidence/mdflaker-fresh-v0.8/logs/<owner>__<repo>/<job_id>.txt`, plus a `<job_id>.json`
    with run and job metadata. The logs were gzip-compressed to `.txt.gz` afterwards; `read_log`
    accepts both forms.
  - The progress file `local-evidence/…/<PROBE_PARTIAL>`.
  - **In reports:**
    - `reports/mdflaker-fresh-v0.8/probe_summary.json`: the first small probe, 40 runs and 40 logs
      per repo.
    - `full_summary_1.json`–`full_summary_4.json`: the full collection.
- **How the full collection was run:** four repository shards, each with `PROBE_MAX_RUNS=400`,
  `PROBE_MAX_LOGS=400` and window start 2026-07-23. Each shard set `PROBE_REPOS`, plus
  `PROBE_PARTIAL=full_partial_N.json` and `PROBE_SUMMARY=full_summary_N.json`.
- **Project selection:** `reports/mdflaker-fresh-v0.8/projects_proposed.json` lists the 8 projects
  chosen from these counts. The rule is the preference order, at least 20 parseable failed
  executions, and at most 8 projects. It is a committed input to step 1b, not written by a script.

**1b. `scripts/mdflaker_v08_candidates.py`: freeze the candidate list** *(label-blind)*
- **Inputs:** the saved logs and their `.json` metadata, and `projects_proposed.json`.
- **Selection rule:**
  - Every failure in a job with ≤ 5 failed tests is kept.
  - A job with more failures is a mass-failure job; one test is drawn from it with seed `20261020`.
- **Environment fields:** runner image, platform, Python version, pytest rootdir and PR merge
  checkout are all parsed from the log.
- **Outputs:**
  - **In reports:** `reports/mdflaker-fresh-v0.8/candidates.csv`, 1,659 rows. The row index is the
    `candidate` ID used everywhere else.
  - `local-evidence/…/job_envs.json`, not used downstream.
  - It prints per-project counts and the SHA-256 of `candidates.csv`.

### Step 2: rerun planning

**`scripts/mdflaker_v08_plan.py`** *(label-blind; set `GH_TOKEN` to any placeholder)*
- **Inputs:** `candidates.csv` and the original job logs. The logs supply the tox, nox or uv
  environment each project's CI used.
- **What it does:**
  - Groups candidates into rerun environments by
    (repo, head SHA, merge base, runner, Python, variant).
  - Attaches each project's setup and test recipe.
  - Excludes Cygwin and unknown-runner candidates, recording them.
- **Outputs** (committed, but in `rerun/v0.8/`, not `reports/`):
  - `rerun/v0.8/plan.json`: environments, the excluded list, and per-repo and per-runner counts.
  - `rerun/v0.8/batch_00.json`–`batch_05.json`: at most 200 environments each.
  - `pilot.json` and `pilot_collect.json` were used for the check-only pilot that fixed the recipes
    (amendment B2).

### Step 3: reruns and labelling

**3a. `.github/workflows/mdflaker-v08-rerun.yml` + `scripts/mdflaker_v08_rerun_job.py`** *(GitHub Actions)*
- **How to start a batch:** either way works.
  - Run the workflow manually (`workflow_dispatch`) with inputs `batch` (for example
    `batch_00.json`) and `mode` (`check-only` or `full`).
  - Or push a branch named `rerun/v0.8-*`. It then runs the batch and mode named in
    `rerun/v0.8/RUN.json`.
- **Matrix:** one job per environment, at most 20 in parallel, on the planned runner and Python.
- **What each job runs** (`mdflaker_v08_rerun_job.py --batch … --env … --out results [--check-only]`):
  1. Rebuild the tested tree. For pushes this is `head_sha`. For PRs it is
     `merge_base` + `git merge head_sha` (B1).
  2. Run the setup command.
  3. Run an environment check on the *other* tests in the candidates' files (B2).
  4. Run a collect-only check on the candidates; uncollectable ones are excluded (B3).
  5. Run the candidates 30 times with `-rA -p no:randomly -p no:cacheprovider`.
- **Outputs:** an artifact `rerun-<env_id>` (kept 90 days) with:
  - `<env_id>.json`: status, environment check, invalid or uncollectable node IDs, and per-round
    outcomes.
  - Setup, environment-check, collect and round-0 logs.
- **Local dry check:** `--check-only` stops after the collection check. It records no candidate
  outcome.
- **Runs used for labels:** 39391984769, 39392001716 and 39400858694 (batches 00–02), and
  39416723189, 39432208752 and 39432222851 (batches 03–05). They are listed in
  `labels_summary.json`.
- Workflow runs are tied to the repository `Nandinipatil1410/FlakeXplain`, which is hard-coded as
  `REPO` in `collect.py`. A fork must edit `REPO` and run the workflow there.

**3b. `scripts/mdflaker_v08_collect.py <run_id>`** *(token needed)*
- **Inputs:** a workflow run ID.
- **What it does:** downloads every artifact of that run into
  `local-evidence/mdflaker-fresh-v0.8/runs/<run_id>/rerun-<env_id>/`. It prints one setup and
  environment-check line per environment; the valid threshold is ≥ 80% of the other tests passing.
- It prints no candidate outcomes. The `--outcomes` flag in its docstring is not implemented.
- **Outputs:** local artifacts only. Run it once per run ID above.

**3c. `scripts/mdflaker_v08_label.py <run_id> …`** *(offline)*
- **Inputs:** the downloaded artifacts of the given runs, `candidates.csv`, and
  `rerun/v0.8/plan.json` with its batches.
- **Frozen label rule (B2):** environments must be valid or unchecked, with all 30 rounds present.
  - Flaky (1): any `PASSED` or `XPASS`.
  - Not flaky (0): all `FAILED` or `ERROR`.
  - Otherwise unlabelled, with a reason.
  - Candidates with no artifact, and planner exclusions, are also listed as unlabelled.
- **Outputs:**
  - `local-evidence/mdflaker-fresh-v0.8/labels.csv`, with columns
    `candidate, repo, label, status`. SHA-256 `3d856bde…b4c2`, recorded in `RESULTS.md`.
  - **In reports:** `reports/mdflaker-fresh-v0.8/labels_summary.json`.
- **Exact command:**

  ```bash
  python scripts/mdflaker_v08_label.py 39391984769 39392001716 39400858694 39416723189 39432208752 39432222851
  ```

### Step 4: features

**`scripts/mdflaker_v08_features.py`** *(label-blind; reads no rerun outcome or label)*
- **Inputs:**
  - `candidates.csv` and the saved CI logs.
  - Bare partial git clones in `local-evidence/mdflaker-fresh-v0.8/clones/<name>.git`. The
    existing clones are bare, with partial-clone filter `blob:limit=1048576`, for example
    `git clone --bare --filter=blob:limit=1m https://github.com/urllib3/urllib3.git urllib3.git`.
    Missing commits and blobs are fetched on demand from public GitHub.
  - The schema `dataset/development-v0.2/schema.json`.
  - The helper modules `scripts/mdflaker_v08_smells.py`, `scripts/dataset_static.py` and
    `scripts/confirmation_features.py`.
  - The GitHub API, only if `local-evidence/…/previous_states.json` or `job_durations.json` is
    missing. Both caches are in the exported data; copy them in to run without a token.
- **Scratch space:** each tested tree's `.py` files are exported to `MDF_SRC` (default `~/mdfsrc`).
  The short root avoids Windows MAX_PATH. Only one tree is kept on disk at a time.
- **Outputs:**
  - `local-evidence/mdflaker-fresh-v0.8/features.csv.gz`, one row per candidate:
    - B: MDFlaker's 5 factors.
    - F: 17 failure-evidence features.
    - C: 66 static context features, plus `context_available`.
  - **In reports:** `reports/mdflaker-fresh-v0.8/features_summary.json`, with row counts, coverage,
    the features file SHA-256 and the script SHA-256.

### Step 5: frozen analysis

**`scripts/mdflaker_v08_analyze.py`** *(offline)*
- **Inputs:** `local-evidence/mdflaker-fresh-v0.8/features.csv.gz` and `labels.csv`.
- **Evaluations:**
  - E1: time-ordered, 60/40 per project.
  - E2: leave-one-project-out.
  - Each has 7 arms. Inference uses a project bootstrap with 2,000 resamples and seed `20261020`.
  - E3 (secondary transfer) also needs MDFlaker's released data and the v0.6/v0.7 features:
    `local-evidence/mdflaker-v0.6/upstream/simpac/F_Detector/dataset.csv`,
    `local-evidence/mdflaker-v0.6/stage1/features_context.csv.gz` and
    `local-evidence/failure-evidence-v0.7/features_failure.csv.gz`. These are **not in this package**.
    The first is third-party (MDFlaker's repository). If they are missing, `results.json` records an
    `E3.error` and E1/E2 are unaffected.
- **Outputs:** **In reports:** `reports/mdflaker-fresh-v0.8/results.json`, with the frozen-rule
  verdicts.

### Step 6: post-hoc analyses (outside the frozen rule)

| Script | Inputs | Output (in `reports/mdflaker-fresh-v0.8/`) |
|---|---|---|
| `mdflaker_v08_diagnostics.py` | features, labels | `diagnostics.json`: project prior, within-project MCC, traceback proxy, permutation importance, unseen tests |
| `mdflaker_v08_robustness.py` | features, labels, `candidates.csv`, **saved CI logs** | `robustness.json`: strict-history `flaky_frequency` (R1), SHAP on ET-BF (R2, shap 0.51.0) |
| `mdflaker_v08_posthoc_extra.py` | features, labels, `candidates.csv`, **saved CI logs** | `posthoc_extra.json`: extra intervals, per-project unseen-test MCC, sensitivity without hypothesis |

- `robustness` and `posthoc_extra` rebuild the per-test failure history from the raw logs. That is
  how they compute `flaky_frequency_strict`. Raw logs are not redistributed, so the package ships
  the parsed history as `failure_history.csv.gz` instead (see below).
- With only the package, `diagnostics` reproduces fully. Reproducing `robustness` or
  `posthoc_extra` needs the logs, or an adapter that reads `failure_history.csv.gz`. Such an
  adapter is **proposed**, not implemented.

### Re-analysis from the exported data

```bash
mkdir -p local-evidence/mdflaker-fresh-v0.8
```
```bash
cp replication/data/features.csv.gz replication/data/labels.csv local-evidence/mdflaker-fresh-v0.8/
```
```bash
.venv-pilot/Scripts/python scripts/mdflaker_v08_analyze.py
```
```bash
.venv-pilot/Scripts/python scripts/mdflaker_v08_diagnostics.py
```

These overwrite `results.json` and `diagnostics.json` in `reports/mdflaker-fresh-v0.8/`. Compare
them with the committed versions using `git diff`. Do this in a scratch clone so the committed
evidence is not disturbed.

## Exported data (`replication/data/`, not committed)

`python replication/export_derived_data.py` (add `--dry-run` to only check) writes:

| File | Source | Content |
|---|---|---|
| `candidates.csv` | `reports/…/candidates.csv` | 1,659 frozen candidates |
| `features.csv.gz` | `local-evidence/…/features.csv.gz` | label-blind features |
| `labels.csv` | `local-evidence/…/labels.csv` | frozen labels; the script aborts unless the SHA-256 is `3d856bde…b4c2` |
| `previous_states.json`, `job_durations.json` | `local-evidence/…/` | cached API metadata used by step 4 |
| `rerun_outcomes.csv` | the `e*.json` records of the six label runs | one row per candidate and run: environment, check counts, invalid or uncollectable flags, and outcome counts over the 30 rounds |
| `failure_history.csv.gz` | parsed from the saved CI logs | repo, run, job, workflow, event, time, failed node ID |
| `MANIFEST.json` | — | SHA-256, size and source of each file |

- **Excluded:**
  - Raw CI job logs.
  - Rerun setup, check and round logs.
  - Git clones.
  - Tokens. The script scans every output for GitHub token patterns and aborts if one is found.
- **Size:** the export is about 1.2 MB.
- **Check:** on 20 October 2026, `rerun_outcomes.csv` agreed with `labels.csv` on all 1,292
  labelled candidates. Label 1 holds exactly when any of the 30 rounds was `PASSED` or `XPASS`.

## Licence and archiving

- Licence: to be chosen by the team; see `LICENSE_OPTIONS.md`.
- Archive metadata: `.zenodo.json` holds the draft Zenodo metadata, for when release is approved.
