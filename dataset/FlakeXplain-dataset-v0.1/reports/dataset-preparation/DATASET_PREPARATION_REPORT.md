# Dataset preparation report

Implemented and validated: **96,118 cases across 35 projects**, with **693 observed-flaky cases** and **95,425 not-observed-flaky cases**.

See [the dataset card](../../dataset/v0.1/DATASET_CARD.md) for labels, context coverage, feature definitions, split sizes, exclusions, reproduction and research limits. Machine-readable per-project totals are in [project_summary.csv](../../dataset/v0.1/project_summary.csv).

No model training was performed. The intended next pilot compares Extra Trees on test-body features against the same training procedure with fixture/helper/lifecycle context, using identical examples and frozen project-separated folds.
