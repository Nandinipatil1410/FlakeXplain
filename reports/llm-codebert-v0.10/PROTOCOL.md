# v0.10 LLM baseline (CodeBERT) on the realistic test-level dataset: protocol

Status: **DRAFT, not frozen.** Nothing has been trained. This protocol becomes binding only when a
team member approves it and the freeze is committed, before any CodeBERT score is computed.

## 1. Question

The synopsis (objectives 4 and 5) asks whether an LLM-based flaky-test classifier keeps its
reported accuracy when it is evaluated on a realistically imbalanced, leakage-free dataset outside
Java, and how it compares with a lightweight, explainable feature-based detector.

**RQ-L1.** On the FlakeXplain dataset (Python, natural flaky rate 0.72%), how does a fine-tuned
CodeBERT classifier given only the test's source code compare with the explainable Extra Trees
detector, under identical project-held-out folds?

## 2. Data (unchanged, already frozen)

- `dataset/v0.1`: 96,118 source-mapped pytest tests from 35 projects; 693 observed flaky
  (label = at least one PASS and one FAIL/ERROR in 25 or 27 detection rounds), 95,425 not observed
  flaky. No rebalancing, oversampling or duplication.
- **Input text:** the test function's source lines `source_start`..`source_end` from
  `metadata.csv.gz`, read from the pinned source archive of its project. The file's SHA-256 must
  equal `source_file_sha256`; a mismatch stops extraction. Nothing else is given to the model:
  no fixtures, no project name, no file path, no outcome counts, no rerun evidence.
- **Folds:** the five fixed outer project folds of `dataset/v0.1/splits_outer.csv`. A project is in
  exactly one test fold. `cross_project_exact_duplicates.csv` is empty, so identical test bodies do
  not cross folds.

## 3. Model

- `microsoft/codebert-base` (125M parameters), as in Flakify (Fatima et al., TSE 2023), with a
  single-logit classification head.
- Input: the test source, truncated to the first 256 tokens.
- Training per outer fold, on that fold's training projects only:
  - 90% of the training tests for fitting, 10% held out (stratified by label, seed 20261021) for
    epoch selection and the threshold;
  - 3 epochs, AdamW, learning rate 2e-5, weight decay 0.01, linear warm-up over 6% of steps,
    batch size 32, mixed precision;
  - binary cross-entropy with positive-class weight = negatives / positives of the fitting part.
    This changes the loss, not the data; the Extra Trees grid also allowed balanced class weights;
  - keep the epoch with the highest average precision (AP) on the 10% validation part.
- Threshold for F1, precision and recall: the value that maximises F1 on the validation part.
- Seed 20261021 for data order and initialisation. One run per fold; no tuning on test folds.

## 4. Comparator

The strongest explainable detector already evaluated on the same folds:
`extra_trees_v2_context` from `reports/development-v0.2` (body + context AST features).
Its out-of-fold scores are in `reports/development-v0.2/oof_predictions.csv.gz`; pooled AP 0.0552.
Its results were inspected during development; the CodeBERT results are new.

## 5. Metrics

- **Primary:** pooled out-of-fold average precision (AP) over all 96,118 tests.
- **Secondary:** per-fold AP; precision, recall, F1, MCC and macro-F1 at the validation-chosen
  threshold; recall at the top 10% of tests by score.
- **Inference:** ΔAP = AP(CodeBERT) − AP(Extra Trees), with a 95% project-bootstrap interval
  (2,000 resamples of the 35 projects, predictions held fixed, seed 20261021).
- Base rate for reference: AP of a random ranking equals the prevalence, 0.0072.

## 6. Decision rule (fixed before training)

- **CodeBERT better:** ΔAP ≥ +0.01 and the interval's lower bound > 0.
- **Extra Trees better:** ΔAP ≤ −0.01 and the interval's upper bound < 0.
- **No clear difference:** anything else.

Either outcome is reported. Macro-F1 is reported next to the 56% macro-F1 that the synopsis cites
for Java (Rahman et al., OOPSLA 2025) for context only; the datasets differ, so it is not a test.

## 7. Error analysis (descriptive)

- Overlap of the top-ranked 1% of tests between CodeBERT and Extra Trees, and their true positives.
- Per observed pattern (order-dependent-looking versus failures in original order), using the
  label evidence only after all scores are fixed. Patterns are provisional (dataset card), so this
  is descriptive.

## 8. Compute and integrity

- Runs on Google Colab (free T4 GPU), one outer fold per run. Each run writes
  `fold_<k>_predictions.csv` (example_id, score) and `fold_<k>_run.json` (versions, timings,
  selected epoch, threshold, input file SHA-256).
- The uploaded input file contains example_id, project, outer fold, label and test source only.
  The label is used for training and evaluation, never as input text.
- Analysis runs locally on the five prediction files, after all five exist.

## 9. What would change this protocol

Only problems found before any test-fold score is seen (for example, a crash or out-of-memory
error). Each change is recorded as a dated amendment, as in v0.8.
