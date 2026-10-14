# Independent confirmation component v0.3

2,610 source-mapped all-pass cases across attrs, tenacity and werkzeug; zero observed positives after 25 rounds. Eleven attrs skip-only identities remain in the evidence audit and are excluded. No body-overlap or source-mapping exclusions among binary cases.

These cases were evaluated after freezing the 35-project development-only models. They are now included only in a separate deployment fit. Do not retune and call them untouched again.

The complete modelling corpus is the union of dataset/v0.1 labels and metadata (96,118 cases), dataset/development-v0.2 core/context features for those IDs, and this component (2,610 cases): 98,728 cases, 693 observed positives, 38 projects. No new split is assigned to this component; its role is prospective external confirmation.

The 30-feature core includes two scope-aware reads; context adds 66 more numeric features. IDs are joins only. Outcomes, identities and provenance cannot be predictors. Raw sources/XML and model binaries remain separately retained with checksums and references. Near-clone and human context validation remain incomplete.
