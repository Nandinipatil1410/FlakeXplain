# CANNIER-protocol context experiment (v0.5): results

Status: **Empirically Verified** (19 October 2026): primary analysis and both pre-declared robustness
analyses are complete.
Protocol and success rule: `PROTOCOL.md`, frozen before any context prediction was computed
(`protocol.json` SHA-256 `f87ddaa1...c38780`). Machine-readable results: `results.json`,
`metrics_summary.csv`, `metrics_by_repeat.csv`, `metrics_by_project_primary.csv`, `front_*.csv`.

## Pre-run checks: passed

- **Cost simulator:** our reimplementation reproduces every released authors' Pareto point with
  n_F <= 1 (Rerun 176/176, iDFlakies 5/5, Pairwise 733/733); `cost_simulator_check.json`.
- **Baseline reproduction gate (tolerance +/-0.03):** all four tasks pass.

| Task | Authors' released mean abs MCC | Our 18-feature baseline | Gap |
|---|---:|---:|---:|
| NOD-vs-Rest | 0.5321 | 0.5339 | +0.0018 |
| NOD-vs-Victim | 0.6926 | 0.6929 | +0.0003 |
| Victim-vs-Rest | 0.5195 | 0.5186 | -0.0009 |
| Polluter-vs-Rest | 0.9458 | 0.9459 | +0.0001 |

## Primary classification result (30 paired repeats, 10-fold stratified CV, SMOTE, n_F = 1)

| Task | Cases / positives | Abs MCC 18 -> 18+67 | Delta (95% repeat CI) | Delta (95% project bootstrap) | AP 18 -> 18+67 | F1 18 -> 18+67 |
|---|---|---|---|---|---|---|
| NOD-vs-Rest | 89,668 / 158 | 0.534 -> 0.576 | **+0.042** [+0.032, +0.051] | [+0.014, +0.083] | 0.494 -> 0.581 | 0.531 -> 0.576 |
| NOD-vs-Victim | 1,130 / 131 | 0.693 -> 0.734 | **+0.042** [+0.033, +0.050] | [-0.002, +0.078] | 0.745 -> 0.820 | 0.729 -> 0.765 |
| Victim-vs-Rest | 89,668 / 1,015 | 0.519 -> 0.614 | **+0.096** [+0.092, +0.099] | [+0.059, +0.184] | 0.527 -> 0.652 | 0.522 -> 0.619 |
| Polluter-vs-Rest | 89,668 / 19,231 | 0.946 -> 0.975 | **+0.029** [+0.029, +0.030] | [+0.018, +0.065] | 0.987 -> 0.993 | 0.957 -> 0.980 |

All four tasks increase on every reported metric, and none is degraded. Victim-vs-Rest improves in
19 projects and declines in 8 (3 have undefined MCC).

### Verdict under the frozen rule

- **Victim-vs-Rest: improved, strong.** It clears the +0.05 practical threshold, and both the
  repeat and project-bootstrap intervals exclude 0.
- **NOD-vs-Rest, NOD-vs-Victim, Polluter-vs-Rest:** these are positive and their repeat intervals
  exclude 0, but the gains (+0.042, +0.042, +0.029) are **below the pre-declared +0.05 threshold**,
  so they do not count as "improved". NOD-vs-Victim's project-bootstrap interval also includes 0.
  Polluter-vs-Rest had little headroom (baseline 0.946).
- **The pre-declared "considerable improvement" classification claim (>= 2 tasks improved) is
  NOT met.** It must not be reported as met. Allowed wording: a consistent improvement across all
  four tasks, considerable (by the pre-set threshold) only for victim detection.

## Secondary result: simulated hybrid-detection cost (authors' cost model, n_F = 1 both arms)

| Technique | Baseline knee (MCC / ratio, cost s) | Context knee | Context cost to reach baseline-knee performance | Saving |
|---|---|---|---|---:|
| Rerun (NOD) | 0.914 @ 6.06e6 | 0.926 @ 5.97e6 | 4.31e6 | **28.9%** |
| iDFlakies (OD) | 0.962 @ 1.62e7 | 0.975 @ 1.50e7 | 1.31e7 | **19.1%** |
| Pairwise (polluter search) | 0.924 @ 1.42e7 | 0.976 @ 7.20e6 | 3.31e6 | **76.7%** |

The frozen cost rule (>= 20% saving for at least one technique, none worse by >= 20%) is
**met**. iDFlakies falls just short of 20%. These are offline simulations using the authors'
recorded run times, not measured CPU savings. Both arms are restricted to n_F = 1, a disclosed
compute adaptation; the authors' full multi-n_F fronts are a separate reference.

## Robustness analyses (pre-declared; 10 paired repeats each)

| Task | Primary delta | Mapped-only delta (no indicator, 86,781 cases) | Family-grouped delta (baseline -> context) |
|---|---:|---:|---:|
| NOD-vs-Rest | +0.042 | +0.043 [+0.026, +0.059] | **+0.060** [+0.050, +0.070] (0.456 -> 0.516) |
| NOD-vs-Victim | +0.042 | +0.063 [+0.050, +0.077] | +0.039 [+0.021, +0.056] (0.666 -> 0.705) |
| Victim-vs-Rest | +0.096 | +0.095 [+0.088, +0.102] | **+0.129** [+0.120, +0.137] (0.455 -> 0.583) |
| Polluter-vs-Rest | +0.029 | +0.032 [+0.031, +0.032] | +0.041 [+0.037, +0.044] (0.908 -> 0.949) |

Brackets are paired repeat 95% intervals. Project-bootstrap intervals are in `metrics_summary.csv`;
in the family-grouped analysis they exclude 0 for NOD-vs-Rest, Victim-vs-Rest and Polluter-vs-Rest,
and include 0 for NOD-vs-Victim.

- **Removing the context-available indicator** and the 2,887 unmapped cases leaves the gains intact.
  The gain comes from the context features, not from the missing-context flag.
- **Keeping all parameterized variants of one test function on the same side of each split** lowers
  *both* arms, so CANNIER's own case-level score is partly inflated by near-duplicate cases. The
  context gain does not shrink; it grows (Victim +0.129, NOD +0.060). The improvement is therefore not
  explained by memorizing shared fixtures across variants of the same test.
- These are secondary analyses. They do not change the frozen primary verdict.

## Limits

- Case-level cross-validation is the base paper's protocol. It does not test generalization to
  unseen projects. Under project-held-out folds (v0.4) neither arm generalizes well.
- This is a retrospective ablation; these projects and the context design influenced earlier work.
- Implementation note: after freezing, and before any context result existed, the fitting loop gained
  `del model; gc.collect()` and `n_jobs=-1` to avoid out-of-memory crashes. Neither changes any
  prediction: seeds are fixed and scikit-learn forests are deterministic across `n_jobs`.
