# Evidence recovery and cohort decisions

Final audit snapshot: 2026-10-12T22:53:11.698353+05:30.

**Implemented and empirically checked:** recovery of missing evidence, pinned-source identity review, and explicit cohort exclusions. No upstream tests were changed or rerun. No classifier was trained.

All **30 CANNIER subject folders** are present. **35 projects** qualify under the implemented local protocol checks, with **715 observed-flaky** and **99,146 all-pass** binary examples (**99,861 total**, **0.7160% positive**). These are source-unresolved candidate examples; fixture extraction and canonical source joins remain dataset-preparation work.

## Recovered evidence

- **Graphene:** downloaded the existing full-run artifact from [workflow run 37740852914](https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/37740852914), attempt 1, artifact 11533068947. The original ZIP is preserved locally; its SHA-256 matches the digest returned by GitHub. The nested archive contains workflow provenance, matching baseline/environment records, and all 25 detection rounds. Imported 350 JUnit identities: 1 observed-flaky, 345 all-pass, 4 skip-only. No rerun was needed. The older baseline-only artifact was not combined with this run.
- **Filelock:** located the complete earlier local execution in `C:/Users/Nandini/AppData/Local/FlakeXplain/5b4a364d/repos/filelock`. Imported only results/logs and environment/setup/baseline metadata, with per-file SHA-256 verification. All 25 rounds pass the checks: 2 observed-flaky, 1,104 all-pass, 236 skip-only. This is recovered local execution evidence, not a newly discovered GitHub workflow.
- **HTTPX:** recovered the failed baseline state and all three baseline-attempt XML files from the same local work directory. All three attempts failed. Retain the evidence and exclude the project; no negative labels or detection rounds are invented.
- Existing differing setup metadata was backed up under `local-evidence/recovery-2026-10-12/pre-import-metadata/`. The importer refused to overwrite differing raw result/log files. `recovery-import-manifest.json` records source, destination, and SHA-256 for all 131 imported files.

## Resolution of the four identity issues

The resolution does **not** recover identities that were never recorded. It permits inclusion of the stable subset after source-verified exclusions. Selection is based on identity quality, not prediction performance or whether a test is positive. Raw XML stays intact; exports retain the original identity groups, counts, and explicit exclusions.

| Project | Recorded baseline rows | Raw identity union | Retained identities | Excluded union identities | Eligible flaky | Eligible all-pass |
|---|---:|---:|---:|---:|---:|---:|
| cirq | 12,609 | 20,948 | 12,189 | 8,759 | 16 | 12,173 |
| xonsh | 4,822 | 4,894 | 4,810 | 84 | 19 | 4,770 |
| hypothesis | 4,554 | 4,546 | 4,538 | 8 | 2 | 4,491 |
| setuptools | 842 | 842 | 841 | 1 | 7 | 702 |

- **Cirq:** 17 source-function families have inconsistent parameterized IDs. Pinned code confirms examples of collection-time random inputs, generated class lists, and representation-dependent IDs. Exclude those entire families, including any IDs that happen to recur, because stripping suffixes would not establish input equivalence. The retained set matches baseline and every round. The 8,759 excluded union identities represent changing names across runs, not 8,759 independent collected cases; the baseline has 420 rows from these families.
- **xonsh:** `tests/test_history_json.py` builds `SEC_FROM_LATEST` using `time.time()` at collection and embeds it in three parameter IDs. Exclude the complete 12-case source family rather than using outcome-dependent or timestamp-stripping joins. Its 84 union identities collapse to 12 cases in a single baseline; the retained baseline and every round have the same identities.
- **Hypothesis:** the pinned `boundaries` parameter list repeats values. Four test functions generate eight colliding JUnit identity groups ending in `[10]` or `[31]`, with two testcase rows per group. Exclude these 16 baseline rows / 8 union groups. Other unambiguous cases remain. Reordered XML position cannot safely distinguish the collisions, and their duplicate rows are never copied into training examples.
- **setuptools:** the pinned environment uses `pytest-checkdocs==2.7.1`. Its verified package source creates `CheckdocsItem.from_parent(parent, name="project")`; the context-free `project` JUnit row is a package documentation check, not a test source function. Exclude this one row and retain the remaining stable test identities.

Exclusion policies are pinned to the exact evidence commits and SHA-256-verified source files. They cannot bypass a baseline failure, environment mismatch, changed raw testcase count, or an unexcluded identity mismatch. Regression tests cover those boundaries.

## Legacy evidence and other exclusions

- **Click, Flask, fsspec:** 25 XML files are present for each, but the imports lack `environment.json`, `baseline_state.json`, and `setup_state.json`. Narrative setup logs and package snapshots do not reconstruct a passing baseline XML bound to the detection environment. Keep their descriptive results, including fsspec's two observed-flip identities, but exclude all three from the primary cohort. No extra workflows were launched solely to enlarge the cohort.
- **HTTPX:** exclude due to the recorded baseline failure, not because of model performance.
- **Werkzeug:** no evidence folder is present. It is an additional configured candidate, not a missing CANNIER subject, and is not part of the cohort.
- **SunPy and urllib3:** retained experiments use revisions different from the released CANNIER inventory. Membership does not imply exact reproduction. The cohort table preserves this distinction.

## Provenance and reproducibility limits

Graphene ZIP SHA-256: `665ab40cdbf3fa6e78b62d0984909e14daf3d5f27f0f81e7df2af30c937f9934`. The recovered artifact has `provenance.json` but no `checksums.json`; the old packaging format must not be described as supplying that missing file. GitHub's matching ZIP digest and the recovered provenance are separately recorded in `recovery_manifest.json`.

For other previously imported projects, top-level archive provenance/checksums have not all been recovered. The audit freezes the current project evidence with file hashes. This is sufficient to proceed with explicit local-cohort preparation, not to claim that all release-provenance work is finished.

All upstream source was fetched at the exact recorded commit and inspected statically. Source archives and extracted copies remain local; no upstream test suite was imported/executed to manufacture new observations. The source references below support the exclusion decisions, not causal flaky-test diagnoses.

### Source references

- [cirq: cirq-core/cirq/circuits/circuit_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/circuits/circuit_test.py); SHA-256 `a10496e565fbfc2b883c4f1b71c64675998af2e5e3a41a01783c5ba05dbdc9f8`.
- [cirq: cirq-core/cirq/contrib/acquaintance/gates_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/contrib/acquaintance/gates_test.py); SHA-256 `d773983c3ad81b4e97ba13a5237b132a5b76489b9345e6a1a346caccb03f6923`.
- [cirq: cirq-core/cirq/contrib/acquaintance/permutation_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/contrib/acquaintance/permutation_test.py); SHA-256 `758a2528da540ef48a6604bac77ae1998201c7998cf2d18f47781172d05fdcb1`.
- [cirq: cirq-core/cirq/contrib/routing/initialization_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/contrib/routing/initialization_test.py); SHA-256 `c8a89d9293046022aaf8b88fb9e3f27366f05bab2e43b0af463d62ae3cf49b14`.
- [cirq: cirq-core/cirq/contrib/routing/router_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/contrib/routing/router_test.py); SHA-256 `7964ef0377c673838323c67154e7e2f1cedb60c7fc676e1624a1b14c66c2a3a4`.
- [cirq: cirq-core/cirq/linalg/decompositions_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/linalg/decompositions_test.py); SHA-256 `999ce4cb16ca999010c8ac95866faddbbeb6e0bd331d96016171b6e02331bdf3`.
- [cirq: cirq-core/cirq/ops/common_gates_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/ops/common_gates_test.py); SHA-256 `35a320977c754c4c6fa27487bf7286a803bc381b06a168e496adb17dcadd22d2`.
- [cirq: cirq-core/cirq/optimizers/decompositions_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/optimizers/decompositions_test.py); SHA-256 `901b4b3a3bdb16d460a17eb23c845dc7921cd0c513725b2384df548271eba9d3`.
- [cirq: cirq-core/cirq/protocols/json_serialization_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/protocols/json_serialization_test.py); SHA-256 `62a8af84a1c30cdbc133dcba17dab95ae3195251cb94cb52cc14c7a3fbd6d93d`.
- [cirq: cirq-core/cirq/testing/random_circuit_test.py](https://github.com/quantumlib/Cirq/blob/782c14e0cc821794d21e82f30df8e6998f4b9992/cirq-core/cirq/testing/random_circuit_test.py); SHA-256 `781586e0144ac7bce001ba054d28b9098067425737320a1857fbc08c96606cc2`.
- [xonsh: tests/test_history_json.py](https://github.com/xonsh/xonsh/blob/e9b12c8b701a75b5ecb8d20f3aad7d3e5aca64bf/tests/test_history_json.py); SHA-256 `629f532e6a05ab52bd59e66d8c7c2d0394a2e9adaa681d645a4e02782e9739ba`.
- [hypothesis: hypothesis-python/tests/nocover/test_simple_numbers.py](https://github.com/HypothesisWorks/hypothesis/blob/ccac4364979effc2b22e2f943176b2b1f025c448/hypothesis-python/tests/nocover/test_simple_numbers.py); SHA-256 `d9a2ffb06fb99724ae77b29d2cb333a86894df994311ea83a3a86a84bf1208b5`.
- setuptools package-check source: the pinned pytest-checkdocs 2.7.1 wheel, verified against PyPI's SHA-256; its URL and digest are recorded in `recovery_manifest.json`.

## Outputs and next stage

- `identity_resolution_rules.json`: explicit commit-bound exclusions and source hashes.
- `cohort_decisions.csv`: include/exclude decision and candidate binary counts for every project.
- `recovery_manifest.json`: recovered artifact/source provenance and hashes.
- `../workflow-audit/CONSOLIDATED_WORKFLOW_REPORT.md`: regenerated project/round/test statistics.
- `../workflow-audit/test_details.csv.gz`: all original identities, exclusions, and `primary_eligible` flags. Only flagged binary rows belong to the current candidate cohort.

The evidence gaps now have documented decisions; dataset preparation can proceed on the retained cohort. Next retrieve remaining pinned sources, establish canonical source-function joins, extract fixture/helper context with coverage checks, and freeze project-disjoint splits before the Extra Trees pilot. Final source joins may create further declared exclusions; current counts are candidate cohort counts, not guaranteed final training counts.
