# Matched CANNIER baseline/context component v0.4

This component reuses the authors' original CANNIER release at experiment revision `b96d6ed02e98d514eb6a92ca264a082234cb9728`, paired with context statically extracted from the exact original subject revisions. It is a separate retrospective comparison corpus, not an enlargement or relabelling of FlakeXplain v0.1/v0.3.

The author archive SHA-256 is `07d714a7e0f57863070d1ba6631191aa6e856fac1ad3ffc92765d6c1fc56f9f1`. The archive contains 89,668 eligible cases, original SQLite identities, labels, 30 instrumented feature measurements and released predictions. Every item row and all measurements are compared with the original arrays before the source join. Counts and exclusions for the matched component are in manifest.json and project_summary.csv.

## Labels and predictors

Author targets are retained as separate `nod`, `victim`, `nod_victim_domain` and `polluter` columns. The two matched tasks are NOD-vs-rest and victim-vs-rest. A negative in either task can be another type of flaky test; it must not be called non-flaky. These labels come from the authors' 2,500 baseline/shuffle protocol, not our 25/27-round observations.

`features_baseline.csv.gz` contains the genuine 18 measurements from the first stored instrumentation run, selected independently of outcomes. `features_context.csv.gz` adds 66 frozen static fixture/helper/lifecycle/class-state counts. IDs are joins only. Outcomes, failure counts, node IDs and project names never become predictors. No original runtime feature is approximated by an AST count.

The SQLite/plugin column order places `n_ext_mods` before `n_assert`; the framework's display names reverse those two labels. The actual numeric order is preserved and the SQLite names are used.

## Inclusion and evaluation

Both representations use the same uniquely source-mapped cases and labels. Paths collected inside subject subdirectories are resolved only by a unique exact path suffix. Parameter text is removed before parsing source names. Unresolved/generated/ambiguous identities are exported as source exclusions; no model-performance filter is used.

Five project-grouped outer folds and four inner project folds keep whole projects and any substantive exact-body duplicate project groups together. The primary experiment preserves natural imbalance without synthetic cases or class weighting. A separately named author-SMOTE sensitivity experiment changes training balance only, keeping held-out populations untouched. No synthetic case is written into this dataset.

These projects and the context extractor influenced prior development; this is not untouched external confirmation. Near-clone and human fixture validation remain incomplete. It does not establish full hybrid-detector efficiency or new independent recall evidence.

## Attribution and reproduction

Original data and implementation: Owain Parry and coauthors, CANNIER (2023), doi:10.1007/s10664-023-10307-w. Release: https://github.com/flake-it/cannier-experiment . The release repository provides the MIT licence, preserved in THIRD_PARTY_LICENSE.txt.

Raw archives, SQLite databases and fitted model binaries remain under ignored local-evidence/cannier-matched-v0.4. Public references, hashes, source checks, original array positions, splits and derived tables are exported. No upstream source code is imported or executed during preparation. NumPy arrays are read with allow_pickle=False; the dependencies pickle is not loaded.
