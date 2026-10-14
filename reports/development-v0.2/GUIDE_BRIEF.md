# Talking points for the guide

- We have an audited, source-linked corpus: 35 projects, 96,118 model-ready cases, 693 observed positives. Labels preserve their finite-run uncertainty.
- The original static-context pilot was weak on unseen projects; this result is retained as a negative reference.
- We completed a bounded follow-up: targeted static revisions, regularized numeric/text baselines, and inner-project configuration selection.
- Highest observed development AP: 0.05516 (Tuned ET: context v2). Original body pilot AP: 0.00840. This is not a published-baseline victory.
- Revised context minus revised core AP: +0.04804; conditional interval [-0.00651, +0.08545].
- At a top-10% budget inside each project (9,628 cases total), captured positives are 63 original body / 103 revised core / 121 revised context, out of 693. Do not substitute pooled 44%-style recall for this project-level result.
- The error study covers 100 declared cases; 12 source excerpts were inspected. Original body-feature collisions affect 379 positive cases; revised full-context collisions affect 123.
- Proposed paper direction: fixture-aware static prediction across Python projects, framed against cross-project/static literature; retain CANNIER as related Python/hybrid work.
- Decisions requested in the meeting: agree the task/base-paper framing, choose a compatible comparison, and agree the final independent-evaluation evidence/time budget.

Bring the four-page PDF first; use DEVELOPMENT_RESULTS_REPORT.md and the CSV/JSON evidence for questions. Final training and submission readiness are not claimed.
