# Repository and local evidence

Git tracks pipeline source, workflows, tests, pinned dependency recipes, required
small test fixtures with provenance, reports, and research documents.

Raw workflow downloads, logs, repository checkouts, virtual environments, and
debugging scratch files remain local. They are not a publication-ready dataset.
The post-workflow evidence audit must precede dataset release and pilot claims.

During cleanup on 12 October 2026, 193 disposable debugging scripts, temporary
dependency/check environments, and cache directories were removed. Another 105
items (including archives, run metadata, logs, source snapshots, and a historical
report backup) were preserved under `local-evidence/cleanup-2026-10-12/`.
Its local `cleanup-manifest.json` records actions and SHA-256 checksums of the
individual files. These checksums describe preservation, not evidence acceptance.
Existing `airflow-evidence/`, `dask-evidence/`, and `repos/` were preserved.

The old `iDFlakies_Report.md` deletion was already present before cleanup; its
history remains available in Git. The current tracked report is
`FlakeXplain_Flaky_Report.md`; historical counts are not a fresh corpus audit.

`POST_WORKFLOW_RESEARCH_HANDOFF.md` contains the current research handoff.
Earlier journal assessments and publication plans remain historical context;
their superseded recommendations do not override the current handoff.

Local verification: `python -m unittest discover -s tests -v`. These tests verify
pipeline behavior and do not rerun upstream projects or establish model results.
