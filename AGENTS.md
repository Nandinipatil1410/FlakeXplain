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
1. **Realistic Dataset Creation**: Build a reproducible, evidence-backed dataset of observed-flaky and not-observed-flaky Python tests without artificial rebalancing or synthetic duplication.
2. **Explainable Classifier**: Train lightweight, interpretable ML models (Logistic Regression, Decision Trees, Random Forest / XGBoost) using static code features and permitted single-run baseline measurements.
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

## Codebase Structure & Pipeline Architecture

All project code resides in `g:/My Drive/Academics/Final Year Project`:

```text
g:/My Drive/Academics/Final Year Project/
|-- AGENTS.md
|-- EXECUTION_GUIDE.md
|-- run_all.py
|-- run_all.bat
|-- FlakeXplain_Flaky_Report.md
|-- pytest_report.md.md
|-- rich_report.md
|-- urllib_report.md
|-- .github/workflows/
|   |-- flakexplain.yml
|   |-- flakexplain-werkzeug.yml
|   |-- flakexplain-rich.yml
|   `-- flakexplain-pytest.yml
|-- scripts/
|   |-- setup_repos.py
|   |-- baseline_gate.py
|   |-- idflakies_runner.py
|   |-- parse_results.py
|   |-- reverse_plugin.py
|   `-- diagnose_repo.py
`-- repos/
    |-- click/
    |-- flask/
    |-- fsspec/
    |-- filelock/
    |-- httpx/
    |-- urllib3/
    |-- rich/
    `-- pytest/
```

---

## Current Empirical Findings

The combined report is regenerated from the JUnit evidence currently present under `repos/<repository>/results`. Percentages use `observed flaky / (observed flaky + not observed flaky) x 100`; skip-only and failure-only tests are unlabelled and excluded.

| Repository | Commit | Tests | Rounds O/R/Rev | Flaky | OD | NOD | Not observed | Flaky % | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `click` | `6aabf099` | 2,084 | 12/12/1 | 0 | 0 | 0 | 1,975 | 0.00% | Passed |
| `flask` | `d318b683` | 494 | 12/12/1 | 0 | 0 | 0 | 494 | 0.00% | Passed |
| `filelock` | `82f66d7b` | 1,342 | 12/12/1 | 2 | 2 | 0 | 1,104 | 0.18% | Passed |
| `fsspec` | `13b0bce8` | 1,779 | 12/12/1 | 2 | 2 | 0 | 1,492 | 0.13% | Passed |
| `httpx` | `b5addb64` | 0 | 0/0/0 | 0 | 0 | 0 | 0 | N/A | Discarded after baseline failure |
| `urllib3` | `a5d70ebf` | 2,633 | 12/12/1 | 4 | 3 | 1 | 2,337 | 0.17% | Passed |
| `werkzeug` | Unknown | 0 | 0/0/0 | 0 | 0 | 0 | 0 | N/A | Result evidence not imported |
| `rich` | `9d8f9a37` | 981 | 12/12/1 | 5 | 5 | 0 | 952 | 0.52% | Passed |
| `pytest` | `a315b97c` | 4,654 | 12/12/1 | 37 | 37 | 0 | 4,556 | 0.81% | Passed |

Across the seven repositories with completed evidence, 13,967 tests were collected. There are **50 observed flaky tests** (49 OD, 1 NOD), 12,910 not-observed-flaky tests, and 1,007 unlabelled tests. The combined observed-flaky percentage among labelled tests is **0.39%**.

The authoritative list of all observed flaky node IDs and their per-round outcomes is in `FlakeXplain_Flaky_Report.md`. The three downloaded workflow reports are retained as per-project source artifacts; their placeholder rows for repositories not run in that workflow are not empirical results.

### Dataset Positioning

The dataset novelty claim is the combined benchmark design, not the existence of Python flaky-test data. The planned release is a newly executed, pytest-specific benchmark combining fixture-aware source context, raw multi-order evidence, uncertainty-aware labels, manually validated cause annotations, and fixed project-disjoint splits. Until those proposed dataset fields and annotations are implemented, describe the present output as an empirical detection corpus.

Repeated-run outcomes, order-specific failures, seeds, and flip counts are label evidence only. They must never be copied into classifier features. Consistently passing tests are labelled `not observed flaky after N runs`, never proven non-flaky.

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

# Ubuntu/GitHub Actions targets
python run_all.py urllib3
python run_all.py werkzeug
python run_all.py rich
python run_all.py pytest
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
