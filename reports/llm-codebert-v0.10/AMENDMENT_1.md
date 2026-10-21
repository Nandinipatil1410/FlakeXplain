# v0.10 amendment 1: train on a Colab A100 GPU instead of the free T4

Date: 2026-10-21T17:57:43Z. Requested by Nandini Patil, for the team.

## State when this amendment was made

- No CodeBERT model has been trained, not even the smoke run. **No CodeBERT score of any kind
  (validation or test fold) exists.**
- `PROTOCOL.md`, `protocol.json`, `FREEZE_NOTE.md` and the notebook are unchanged
  (notebook SHA-256 `78d3cfbef128b83531f39a1f4b3f1b787b4e45aa5da58bd39c861901dde5741b`, as frozen).

## Change

Protocol section 8 says the runs use "Google Colab (free T4 GPU)". All runs, the smoke run and the
five outer folds, will instead use a **Colab A100 GPU** paid from the team's Colab compute units.
All five folds use the same GPU type, so that their scores are comparable.

Reason: speed. The A100 is several times faster than the T4 for this fine-tuning, and the team has
compute units for it. The choice was made for practical reasons, before any result was seen.

## Unchanged

Everything in sections 2 to 7: input text, 256-token truncation, `microsoft/codebert-base`,
3 epochs, AdamW, learning rate 2e-5, weight decay 0.01, 6% warm-up, batch size 32, float16 mixed
precision, positive-class weight, 90/10 validation split, epoch and threshold selection, seed
20261021, folds, comparator, metrics and the decision rule. The notebook needs no edit: it runs on
any CUDA GPU and records the GPU name in each `fold_<k>_run.json`.

## Expected effect

None on the method. GPU kernels differ between T4 and A100, so scores can differ slightly from what
a T4 run would give at the same seed; this is not a source of bias between the two compared models.

## Check

`scripts/llm_v010_analyze.py` requires every `fold_<k>_run.json` to report the same GPU, and that
GPU to be an A100.
