# AGENTS.md — FlakeXplain Project Context & Agent Instructions

This document provides a comprehensive, single-source context for AI coding assistants working on the **FlakeXplain** project.

---

## 📌 Project Overview & Identity

- **Project Title**: **FlakeXplain: Realistic Flaky Test Detection Using Explainable and LLM-Based Classifiers**
- **Project Type**: Final-Year B.Tech Computer Engineering Capstone Project
- **Team Members**: Nandini Patil, Bhumika Mane, Trusha Kulkarni, Pranavi Baad
- **Primary Domain**: Software Engineering, Test Automation, Machine Learning, Explainable AI (XAI), Large Language Models (LLMs)
- **Primary Tech Stack**: Python 3.11+, Pytest, scikit-learn, SHAP, PyTorch/HuggingFace/OpenAI API, GitHub Git API

---

## 🎯 Problem Statement & Core Goals

### Problem
A **flaky test** passes or fails without any changes to the underlying program source code. Flaky tests erode developer confidence in CI/CD pipelines, waste compute and human time, and obscure real bugs.

### Goals
1. **Realistic Dataset Creation**: Build a reproducible, evidence-backed dataset of flaky and non-flaky Python tests without artificial rebalancing or synthetic duplication.
2. **Explainable Classifier**: Train lightweight, interpretable ML models (Logistic Regression, Decision Trees, Random Forest / XGBoost) using static code features and non-leaky baseline execution statistics.
3. **LLM Comparison**: Benchmark LLM classifiers against traditional ML on identical project-separated test splits using structured outputs.
4. **Explainability**: Output human-readable rule sets, feature importance rankings, and SHAP explanations for predicted flakiness.
5. **Rigorous Evaluation**: Prevent data leakage across project boundaries, separate dynamic detection evidence from features, and evaluate using Precision, Recall, F1, PR-AUC, and per-project breakdowns.

---

## 🔬 Detection Methodology (iDFlakies Pytest Adaptation)

We have ported the **iDFlakies methodology** (Lam et al., ICST 2019) from Java/JUnit to Python/Pytest across 5 core steps:

```
Step 1: Pin Environment (git commit, python venv, env_snapshot.txt, setup_log.md)
  │
Step 2: Clean Baseline Gate (pytest -p no:randomly --tb=short -q up to 3 attempts)
  ├── PASS  ──> Proceed to Step 3
  └── FAIL  ──> DISCARD MODULE (do not force pass or ignore failures)
  │
Step 3: Reordered Execution Engine (~25 rounds total)
  ├── Original-Order (12 rounds): pytest -p no:randomly --junitxml=results/original_run_N.xml
  ├── Random-Order (12 rounds):   pytest --randomly-seed=SEED --junitxml=results/random_run_N.xml
  └── Reverse-Order (1 round):    pytest -p conftest_reverse --junitxml=results/reverse_run_1.xml
  │
Step 4: Detect & Classify (parse results/*.xml)
  ├── Observed Flaky: Test flipped outcome (>= 1 PASS and >= 1 FAIL/ERROR)
  │     ├── OD  (Order-Dependent): Passes in original order; fails under reordering
  │     ├── NOD (Non-Order-Dependent): Fails in original order non-deterministically
  │     └── Unclassified: Inconsistent reordering behavior needing further rerun data
  └── Not Observed Flaky: Passed consistently across N runs (with explicit N-run caveat)
  │
Step 5: Empirical Reporting -> Exports FlakeXplain_Flaky_Report.md
```

---

## 🛠️ Codebase Structure & Pipeline Architecture

All project code resides in `g:/My Drive/Academics/Final Year Project`:

```
g:/My Drive/Academics/Final Year Project/
├── AGENTS.md                      # This context & instructions document
├── run_all.py                     # Master orchestrator (CLI: python run_all.py [repo_name])
├── run_all.bat                    # Windows batch launcher
├── FlakeXplain_Flaky_Report.md    # Main empirical report table & observed flaky logs
├── implementation_plan.md         # Technical implementation design document
├── walkthrough.md                 # System setup walkthrough & guide
├── scripts/
│   ├── setup_repos.py             # Step 1: Clone, pin git commit, venv & freeze env
│   ├── baseline_gate.py           # Step 2: Collected count & baseline verification (<= 3 runs)
│   ├── idflakies_runner.py        # Step 3: Original, Random, & Reverse reordering engine
│   ├── parse_results.py           # Step 4 & 5: JUnit XML parser & OD/NOD categorizer
│   ├── reverse_plugin.py          # Pytest plugin inverting item sequence in-memory
│   └── diagnose_repo.py           # Diagnostic runner capturing stdout/stderr
└── repos/                         # Isolated repository environments
    ├── click/
    ├── flask/
    ├── fsspec/
    ├── filelock/
    ├── httpx/
    └── urllib3/                    # Created in GitHub Actions execution storage
```

---

## 📊 Current Empirical Findings (Verified Baseline)

From running `run_all.py` across 5 candidate repositories:

| Repository | Commit Hash | Total Tests | Rounds (Orig / Rand / Rev) | Observed Flaky | OD | NOD | Not Observed Flaky | Flaky Ratio | Baseline Status |
|---|---|---|---|---|---|---|---|---|---|
| `click` | `6aabf099` | 2,084 | 12 / 12 / 1 | **0** | 0 | 0 | 2,084 | `0:2084` | `PASSED` |
| `flask` | `d318b683` | 494 | 12 / 12 / 1 | **0** | 0 | 0 | 494 | `0:494` | `PASSED` |
| `fsspec` | `13b0bce8` | 1,779 | 12 / 12 / 1 | **2** | **2** | 0 | 1,777 | **`2:1777`** (0.11%) | `PASSED` |
| `filelock`| `82f66d7b` | 950 | In Progress | — | — | — | — | — | Configured |
| `httpx` | `b5addb64` | — | 0 | — | — | — | — | — | `FAILED` on Windows (upstream tempfile incompatibility) |
| `urllib3` | `a5d70ebf` | — | Not started | — | — | — | — | — | Configured for Ubuntu GitHub Actions |

### Confirmed Flaky Tests (`fsspec` @ `13b0bce8`):
1. `fsspec.tests.test_mapping::test_keys_view` (Order-Dependent / **OD**)
2. `fsspec.tests.test_mapping::test_multi` (Order-Dependent / **OD**)

---

## ⚙️ How to Run & Commands

```powershell
# Run entire pipeline across all repositories
python run_all.py

# Run pipeline for a specific repository individually
python run_all.py click
python run_all.py flask
python run_all.py fsspec
python run_all.py filelock
python run_all.py httpx
# Ubuntu/GitHub Actions target
python run_all.py urllib3
```

---

## 🤖 Strict Guidelines for AI Agents

1. **Zero Hallucination Policy**:
   - Never invent test results, flaky labels, repository statistics, or model metrics.
   - Always state clearly whether a detail is **Proposed**, **Implemented**, or **Empirically Verified**.

2. **Feature-Label Isolation**:
   - Multi-run outcome flipping evidence is used **only** for generating the target label (`observed_flaky` = 1/0).
   - Input features for classifiers must come strictly from static code AST/parsing or single-run baseline metrics to prevent data leakage.

3. **No Unrealistic Rebalancing**:
   - Preserve natural class imbalance as observed in real software repos.
   - Do not use synthetic oversampling (SMOTE) or artificial test duplication unless explicitly analyzing its impact as an experiment variable.

4. **Environment Integrity**:
   - Always pass `PYTHONPATH` with `tasks`, `tests`, `src`, and `.` when spawning `pytest` subprocesses.
   - Always pass `-p no:cov` to avoid plugin crashes during reordering runs.
   - For reverse ordering, use `conftest_reverse.py` (in-memory item reversal) to avoid Windows `WinError 206` command-line length limits.
