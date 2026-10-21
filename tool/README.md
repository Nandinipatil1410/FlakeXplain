# FlakeXplain CLI

`flakexplain` is a command-line tool for Python teams that use pytest. It has two commands:

| Command | Question it answers | How |
|---|---|---|
| `flakexplain detect` | Which of our tests are flaky right now? | Reruns the suite in original, random and reverse order (the study's iDFlakies-style protocol) and labels each flaky test OD or NOD. |
| `flakexplain triage` | CI just failed. Is it a real bug, or just a flaky test? | Scores each failed test with the ET-BF model from the FlakeXplain study and explains each score. |

Status: **Implemented**. `detect` reproduces the study's protocol. `triage` ships the frozen v0.9 model.
That model has not yet been evaluated on new failures; the v0.9 confirmation (from 24 Nov 2026) is its first test.

## Install

```bash
pip install ./tool            # from this repository
pip install "./tool[shap]"    # optional: SHAP explanations instead of tree-path attributions
```

Install it into the same environment as the project under test: `detect` runs that environment's pytest.

## `flakexplain detect`

```bash
flakexplain detect                       # current directory: 12 original, 12 random, 1 reverse round
flakexplain detect path/to/project --original 5 --random 5 --reverse 1
flakexplain detect -- tests/unit -k "not slow"    # arguments after -- go to pytest
```

1. **Baseline gate.** The suite must pass cleanly in original order (up to 3 attempts). Otherwise
   detection stops (exit code 2), because flaky tests cannot be told apart from broken ones.
2. **Rounds.** Each round writes JUnit XML and a log to `.flakexplain/detect/` (change it with `--out`).
   Random order is a seeded shuffle of all collected tests (`--seed`, default 42). Reverse order
   reverses them. Both are done in memory by the `flakexplain.order_plugin` pytest plugin.
   `pytest-randomly` and `pytest-cov` are always disabled.
3. **Labels.**
   - **OD** (order-dependent): fails only when the order changes.
   - **NOD**: fails in original order too.
   - **Unclassified**: mixed behaviour.
   - **Not observed flaky**: passed every round. This is not proof that the test can never flake.

Outputs: `report.md` and `results.json`. Use `--fail-on-flaky` to exit 1 when a flaky test is found.

## `flakexplain triage`

```bash
pytest | tee pytest.log
flakexplain triage --log pytest.log              # or: --junit report.xml
flakexplain triage --log pytest.log --format markdown --output triage.md   # e.g. for a PR comment
```

Example output:

```text
LIKELY FLAKY         P(flaky)=0.81  tests/test_client.py::test_timeout
    +0.214 towards flaky earlier failures of this test in other runs = 0.33
    +0.061 towards flaky the failing test's own file changed = 0
    ...
```

The verdict is *likely flaky* when P(flaky) is at least 0.5. Each verdict lists the four features that
pushed the score most. Explanations use SHAP when `shap` is installed, and tree-path attributions otherwise.

### What it reads

Triage needs no test reruns. It uses only what exists when the failure happens:

- **Report**: the failed tests, their tracebacks and the number of failures in the job.
  `--log` (pytest console output) matches the training data best; `--junit` also works.
- **Git diff** between `--base` (default `HEAD^`) and `--head` (default `HEAD`). In GitHub Actions a
  pull request is checked out as a merge commit, so `HEAD^` is the base branch. Use `fetch-depth: 2`.
- **Test source**: MDFlaker's test smells and test size.
- **Failure history** (`.flakexplain/history.jsonl`): each triage adds its failures, unless you pass
  `--no-record`. Later runs then count earlier failures of the same test. **Keep this file between CI
  runs.** It is the strongest signal.
- **Run context**: `--previous-state` (the previous run of the workflow on this branch), `--job-duration`
  (seconds), and `--pr`/`--push`. The last two are read from `GITHUB_RUN_ID` and `GITHUB_EVENT_NAME`
  when they are set.

### GitHub Actions example

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 2 }
- run: echo "JOB_START=$(date +%s)" >> "$GITHUB_ENV"
- uses: actions/cache/restore@v4
  with: { path: .flakexplain/history.jsonl, key: flakexplain-${{ github.run_id }}, restore-keys: flakexplain- }
- run: pytest -p no:randomly | tee pytest.log
- if: failure()
  env: { GH_TOKEN: "${{ github.token }}" }
  run: |
    prev=$(gh run list --workflow "${{ github.workflow }}" --branch "${{ github.head_ref || github.ref_name }}" \
           --limit 2 --json conclusion -q '.[1].conclusion // "none"')
    case "$prev" in success) prev=passed;; failure) prev=failed;; none) ;; *) prev=other;; esac
    flakexplain triage --log pytest.log --previous-state "$prev" \
      --job-duration $(( $(date +%s) - JOB_START )) --format markdown --output triage.md
    cat triage.md >> "$GITHUB_STEP_SUMMARY"
- if: always()
  uses: actions/cache/save@v4
  with: { path: .flakexplain/history.jsonl, key: flakexplain-${{ github.run_id }} }
```

## How good is it? (from the study; read before trusting a score)

- **Model.** `ExtraTreesClassifier(n_estimators=100, random_state=20261020)` on MDFlaker's 5 factors
  and 17 failure-evidence features. It is trained on all 1,292 labelled CI failures (409 flaky) from 8
  projects. A failure is labelled flaky if the test passed at least once in 30 reruns of the failing commit.
  Details: `src/flakexplain/data/model_card.json`.
- **v0.8, within project (E1).** ET-BF beat the best MDFlaker-style comparator by +0.516 MCC.
  On tests not seen in training, ET-BF scored 0.57 MCC and KNN8 −0.08. On tests seen before, it scored 0.98.
  So the tool is **much more reliable for tests that have failed before**.
- **Strict history.** Only earlier runs count, as in this tool. On unseen tests, ET-BF scored
  0.469 MCC and MDFlaker −0.160. Across projects (leave-one-project-out), ET-BF reaches only
  0.100 MCC. Its gain over KNN8 there (+0.23) has a 95% interval that includes 0.
  On a project with no history, treat scores with care.
- **A project's base rate alone** reaches 0.52 MCC in E1. Part of what any model learns is how
  flaky a project is overall.
- **Scores are not proof.** A *likely flaky* failure can still be a real bug; rerun it before ignoring it.

Sources: `reports/mdflaker-fresh-v0.8/RESULTS.md` and `reports/mdflaker-confirm-v0.9/PROTOCOL.md`.
The tool's features are checked against the study's features by `scripts/check_tool_parity.py`.
On 21 Oct 2026, all 17 log, diff, history and run-context features matched for all 1,292 failures.
The 5 source features matched for the 25 failures from 12 randomly drawn source trees
(`reports/mdflaker-fresh-v0.8/tool_parity.json`). The check runs on saved pytest console logs. The
`--junit` input is unit-tested but has no parity check against the study.

## Develop

```bash
python -m venv tool/.venv && tool/.venv/Scripts/python -m pip install -e "./tool[shap]"
tool/.venv/Scripts/python -m pytest tool/tests
```

To rebuild the model from the study data (local evidence required), run
`GH_TOKEN=unused python scripts/fit_tool_model.py`.
