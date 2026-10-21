# v0.10 freeze note

`PROTOCOL.md` is **frozen**. Its header still says "DRAFT, not frozen" because the text was approved
unchanged, exactly as drafted. Editing the header would change the file's SHA-256, which is recorded at
freeze. The authoritative freeze record is `protocol.json`:

- approved by Nandini Patil, for the team;
- frozen at 2026-10-21T17:37:00Z, on top of commit `d87c01b`;
- `PROTOCOL.md` SHA-256 `2cb2a14fa35dce6df9d549c29a4276340bcbbb6b7563672b9e4d37d9acaecc5a`;
- Colab notebook, extraction script, extraction summary and input file hashes as listed there;
- comparator: `extra_trees_v2_context` out-of-fold predictions in `reports/development-v0.2`.

State at freeze:
- the input file (96,118 tests, 693 flaky) was extracted and every source file matched its recorded
  SHA-256 (`extraction_summary.json`);
- the notebook's data-loading cells were run locally for all five folds and in smoke mode, to check
  the splits (no project in both training and test; test folds sum to 96,118);
- **no CodeBERT model has been trained and no CodeBERT score exists.**

Any later change follows section 9 of the protocol: a dated amendment, made before any test-fold
score is seen.

This note was added on 21 October 2026. It changes nothing in the protocol.
