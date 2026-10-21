# v0.10 results: CodeBERT LLM baseline versus explainable Extra Trees

Status: **Empirically verified** for these runs (one training run per outer fold). Protocol
`PROTOCOL.md`, frozen 2026-10-21T17:37:00Z (`protocol.json`, `FREEZE_NOTE.md`), with
`AMENDMENT_1.md` (Colab A100 instead of T4, made before any CodeBERT score existed).
Analysis: `scripts/llm_v010_analyze.py`. Full numbers: `results.json`.

## Decision (protocol section 6)

| | Pooled out-of-fold AP |
|---|---:|
| CodeBERT (`microsoft/codebert-base`, test source only) | **0.0106** |
| Extra Trees `extra_trees_v2_context` (comparator) | **0.0552** |
| Random ranking (prevalence) | 0.0072 |
| **ΔAP = CodeBERT − Extra Trees** | **−0.0446** |
| 95% project-bootstrap interval (2,000 resamples of 35 projects, seed 20261021) | [−0.0765, +0.0048] |

**Outcome: no clear difference** under the frozen rule. ΔAP is below −0.01, but the interval's
upper bound is above 0, so the "Extra Trees better" condition is not met.

The point estimate strongly favours Extra Trees: CodeBERT's AP is about one fifth of Extra Trees'
and only 1.5 times the random baseline. The interval is wide because flaky tests are concentrated in
a few projects (airflow alone has 300 of the 693), and on airflow the two models are close
(AP 0.113 vs 0.118). Resamples that draw airflow many times can therefore produce a small
positive difference. We report the frozen outcome, not the point estimate, as the result.

## Secondary metrics (pooled, 96,118 tests, 693 observed flaky)

Thresholds: CodeBERT's per fold maximises F1 on its 10% validation part; Extra Trees' are its
inner-fold F1 thresholds from v0.2.

| Metric | CodeBERT | Extra Trees |
|---|---:|---:|
| Average precision | 0.0106 | 0.0552 |
| Precision at threshold | 0.0219 | 0.0133 |
| Recall at threshold | 0.0144 | 0.0722 |
| F1 | 0.0174 | 0.0225 |
| MCC | 0.0120 | 0.0146 |
| Macro-F1 | 0.506 | 0.500 |
| Predicted flaky (TP / FP) | 456 (10 / 446) | 3,753 (50 / 3,703) |
| False positives per 1,000 negatives | 4.7 | 38.8 |
| Recall in top 10% of tests by score | 0.140 | 0.442 |

Macro-F1 is about 0.50 for both, against the 56% that the synopsis cites for Java (Rahman et al.,
OOPSLA 2025). The datasets differ, so this is context only, not a test.

### Per fold

| Fold | Tests | Flaky | AP CodeBERT | AP Extra Trees | Top-10% recall CB / ET | CB best epoch | CB threshold |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 21,584 | 310 | 0.0247 | 0.1115 | 0.194 / 0.652 | 3 | 0.977 |
| 1 | 19,609 | 146 | 0.0084 | 0.0069 | 0.103 / 0.055 | 3 | 0.977 |
| 2 | 19,583 | 78 | 0.0084 | 0.0123 | 0.231 / 0.333 | 3 | 0.975 |
| 3 | 17,807 | 80 | 0.0166 | 0.0743 | 0.413 / 0.600 | 3 | 0.994 |
| 4 | 17,535 | 79 | 0.0049 | 0.0073 | 0.127 / 0.114 | 3 | 0.995 |

Extra Trees has the higher AP in 4 of 5 folds. Among the 29 projects with at least one flaky test,
Extra Trees has the higher per-project AP in 17 and CodeBERT in 12 (`results.json`, `per_project`;
most projects have very few flaky tests, so per-project AP is noisy).

## Validation versus held-out projects (descriptive)

CodeBERT's best validation AP per fold was 0.50, 0.30, 0.61, 0.60 and 0.56. The validation part is
a random 10% of the *training projects*, so it shares projects with the training data. On the
held-out projects the same models reach 0.005–0.025. Most of what CodeBERT learns from the test
source therefore does not transfer to unseen projects. This fits the dataset's motivation:
within-project splits overstate performance. It also explains the very high thresholds
(0.975–0.995) and the low recall at threshold. This is a description of these runs, not a
separate hypothesis test.

## Error analysis (protocol section 7, descriptive)

- **Top 1% overlap (962 tests per model):** the two models share only 19 tests. CodeBERT's top 1%
  holds 18 flaky tests, Extra Trees' 114; 4 are in both. The models rank tests very differently.
- **By label-evidence pattern** (used only after all scores were fixed; patterns are provisional):

| Pattern | Flaky tests | CB recall at threshold | ET recall at threshold | In top 10% CB / ET | In top 1% CB / ET |
|---|---:|---:|---:|---:|---:|
| Order-dependent-looking (failures only under reordering) | 687 | 0.015 | 0.071 | 93 / 305 | 18 / 114 |
| Fails in original order | 6 | 0.000 | 0.167 | 4 / 1 | 0 / 0 |

With only 6 tests that fail in the original order, no conclusion about non-order-dependent
flakiness is possible.

## Run record

| Fold | Fit (flaky) | Validation (flaky) | Validation AP by epoch | Training time |
|---:|---:|---:|---|---:|
| 0 | 67,080 (345) | 7,454 (38) | 0.215, 0.436, 0.498 | 432 s |
| 1 | 68,858 (492) | 7,651 (55) | 0.108, 0.135, 0.295 | 447 s |
| 2 | 68,881 (553) | 7,654 (62) | 0.515, 0.586, 0.608 | 445 s |
| 3 | 70,479 (552) | 7,832 (61) | 0.422, 0.524, 0.599 | 451 s |
| 4 | 70,724 (553) | 7,859 (61) | 0.387, 0.523, 0.558 | 454 s |

All runs: NVIDIA A100-SXM4-40GB, torch 2.11.0+cu130, transformers 5.20.1, scikit-learn 1.6.1,
Python 3.13.15; input SHA-256 `ff0e6d3b…3fd6` as frozen; settings as frozen. Total training about
37 minutes. The analysis script verified each run record (fold, not smoke, input SHA, frozen
settings, test projects, one A100 type) and that the five prediction files cover all 96,118 tests
exactly once. SHA-256 of each fold file: `results.json`, `input_files`. The fold files themselves
are in `local-evidence/llm-codebert-v0.10/` (not committed).

## Caveats

1. **Comparator inspected during development.** Extra Trees' scores come from v0.2, where results
   were seen while its configuration was developed; CodeBERT's are new. This favours Extra Trees
   if anything, and is one reason the rule needs an interval clear of zero.
2. **256-token truncation.** Only the first 256 tokens of each test are seen (median test length
   380 characters, 90th percentile 1,064, so most tests fit; long tests lose their end). No
   fixtures, file paths or context are given, unlike the Extra Trees context features.
3. **One run per fold, one seed.** Training randomness is not reflected in the interval, which
   holds the predictions fixed and resamples projects only.
4. **OD/NOD patterns are provisional** (dataset card) and only 6 flaky tests fail in the original
   order.
5. **Hardware amendment.** All runs used an A100 instead of the T4 named in the protocol
   (`AMENDMENT_1.md`); the method is unchanged.
6. **Smoke run.** The setup check trained a 1-epoch model on 2,000 tests and scored the first 1,000
   tests of fold 0's test part (airflow). No metric was computed on those scores; they are not results.
7. **Labels.** "Not observed flaky" means not observed in 25 or 27 detection rounds, not proven
   stable.
