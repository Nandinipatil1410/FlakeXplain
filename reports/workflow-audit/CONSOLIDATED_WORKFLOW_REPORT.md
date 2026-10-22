# Consolidated workflow evidence report

Generated 2026-10-12T22:53:11.698353+05:30. Evidence snapshot only; no subjects were rerun.

Inspected **39 imported project folders**. **35 pass the local protocol checks** below. Expected but absent folders: none.

Across locally protocol-complete projects: **104,223 distinct JUnit test identities**, **715 observed flaky**, **99,146 passed every detection round**, and **4,362 excluded from the strict binary denominator**. Observed-flaky percentage: **0.7160%**; positive:negative ratio **715:99,146**.

These projects contribute **883 detection rounds** and **42.83 recorded detection process-hours**, excluding baseline, setup, and scheduling overhead. Projects with three reverse rounds retain all 27 rounds.

Across all parsed folders, including unverified/ambiguous evidence: **117,432 JUnit identities in the per-project union**, **717 observed outcome-flip identities**, **103,119 all-pass identities**, **7,176 pass+skip/missing**, **6,412 skip-only**, **8 duplicate identities**. These are exploratory counts, not a frozen dataset size. Changing parameter IDs inflate the union for some projects; module-collection skips also appear as JUnit records.

Audit categories: 31 locally protocol-complete without identity exclusions; 4 complete with documented identity exclusions; 0 identity/other issues; 3 legacy unverified; 1 without detection evidence. Configured folders absent from this import: werkzeug.

## Imported-folder evidence and remaining gaps

Copying the entire artifact `repos/<project>/` folder is the right core import: retain results/execution_manifest.json, all original/random/reverse JUnit XML, logs (including baseline XML), environment.json, baseline_state.json, setup_state.json, env_snapshot.txt, setup_log.md, and any dependency snapshot/setup recipe. The packager does not include full upstream source; source must later be retrieved at the recorded commit for static features.

Also preserve the original downloaded ZIP and its sibling/top-level provenance.json, checksums.json, and system_packages.txt, ideally in a separate directory per workflow run ID and attempt. Copying only the nested project folder omits these archive-level records. Their recovery normally requires re-extracting the download, not rerunning tests. Do not merge attempts or overwrite differing environments.

Current project-specific recovery decisions are recorded in `reports/evidence-recovery/EVIDENCE_RECOVERY_REPORT.md`. Any `protocol_complete_with_exclusions` row retains only identities outside the commit-bound, source-hash-verified resolution rules. Original XML and original identifiers are preserved, with exclusions exported per identity. No changing parameter values are silently merged.

## Scope and interpretation

- Protocol-complete means a matching passing baseline XML, standalone/embedded environment identity, complete expected checkpoint records, valid XML, consistent retained JUnit identities, and expected ordering seeds. Source-verified exclusions are explicit where needed. It is a local structural audit, not a claim of fully verified archive provenance or causal validity.
- Primary descriptive target: at least one PASS and one FAIL/ERROR in parsed detection rounds. Strict negatives pass every recorded detection round. PASS+SKIP/missing, skip-only, failure-only, and ambiguous duplicate identities are separated. Project-level acceptance is required before considering these labels for a primary dataset.
- Baseline observations are gate evidence, excluded from detection outcome counts. Tests include parameterized JUnit cases; these are not independent source functions. File + classname + name are preserved to avoid class collisions, but canonical pytest/source mapping remains pending.
- Reordered-only failures are configuration patterns, not confirmed OD. pytest-randomly may affect runtime seeds as well as order. Mixed original outcomes also do not establish a causal NOD subtype.
- CANNIER membership/revision is compared against the vendored authors' inventory. Same revision does not mean identical environment, labels, execution budget, features, or full replication.
- Duration is the sum of checkpointed detection process durations, excluding setup/baseline. It is neither summed testcase time nor a measurement of hybrid-detection savings. Legacy durations are withheld.
- General archive provenance remains outside this folder audit. Graphene was separately recovered with a downloaded ZIP digest matching GitHub artifact metadata and retained workflow provenance; see the recovery report. Newly computed hashes for other imported files freeze the current snapshot rather than retrospectively verifying downloads. No workflow success badge or run URL is inferred for other projects.

Strict flaky percentage = `100 × flaky / (flaky + all-pass)`. F:N is the same unrebalanced positive:negative count ratio. `project_summary.csv` also gives an active-outcome percentage including pass+skip/missing records; this broader denominator is not the primary binary dataset.

## Locally protocol-complete cohort by repository group

| Group | Projects | JUnit identities | Observed flaky | All-pass | Excluded | Flaky % strict |
|---|---:|---:|---:|---:|---:|---:|
| CANNIER same revision | 28 | 91,478 | 641 | 87,426 | 3,411 | 0.7279 |
| CANNIER changed/unknown revision | 2 | 4,920 | 6 | 4,390 | 524 | 0.1365 |
| additional | 5 | 7,825 | 68 | 7,330 | 427 | 0.9192 |

## Per-project results

Project names in the table below link to their upstream GitHub repositories; the commit column gives the pinned revision that was tested.

Counts below describe all parsed identities, including exclusions and legacy evidence. Headline totals use only retained identities in the two protocol-complete categories. The eligibility table specifies the primary cohort.

| Project | Audit status | CANNIER relation | Commit | JUnit identities (union) | O/R/Rev | Flaky | All-pass | Pass+skip/missing | Skip-only | Fail-only | Duplicate | Flaky % strict | F:N |
|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| [airflow](https://github.com/apache/airflow) | protocol_complete_local_checks | CANNIER same revision | `c743b95a` | 3,978 | 12/12/1 | 313 | 3,461 | 1 | 203 | 0 | 0 | 8.2936 | 313:3461 |
| [celery](https://github.com/celery/celery) | protocol_complete_local_checks | CANNIER same revision | `552e067b` | 2,381 | 12/12/1 | 7 | 2,325 | 0 | 49 | 0 | 0 | 0.3002 | 7:2325 |
| [cirq](https://github.com/quantumlib/Cirq) | protocol_complete_with_exclusions | CANNIER same revision | `782c14e0` | 20,948 | 12/12/1 | 16 | 12,175 | 7,092 | 1,665 | 0 | 0 | 0.1312 | 16:12175 |
| [click](https://github.com/pallets/click) | legacy_unverified | additional | `6aabf099` | 2,084 | 12/12/1 | 0 | 1,975 | 0 | 109 | 0 | 0 | 0.0000 | 0:1975 |
| [conan](https://github.com/conan-io/conan) | protocol_complete_local_checks | CANNIER same revision | `d5240749` | 4,083 | 12/12/1 | 24 | 3,663 | 0 | 396 | 0 | 0 | 0.6509 | 24:3663 |
| [dask](https://github.com/dask/dask) | protocol_complete_local_checks | CANNIER same revision | `d5bbad0b` | 10,132 | 12/12/1 | 1 | 8,525 | 0 | 1,606 | 0 | 0 | 0.0117 | 1:8525 |
| [djangorestframework](https://github.com/encode/django-rest-framework) | protocol_complete_local_checks | CANNIER same revision | `0323d6f8` | 1,403 | 12/12/1 | 1 | 1,401 | 0 | 1 | 0 | 0 | 0.0713 | 1:1401 |
| [electrum](https://github.com/spesmilo/electrum) | protocol_complete_local_checks | CANNIER same revision | `d8d2c180` | 545 | 12/12/1 | 0 | 542 | 0 | 3 | 0 | 0 | 0.0000 | 0:542 |
| [filelock](https://github.com/tox-dev/filelock) | protocol_complete_local_checks | additional | `82f66d7b` | 1,342 | 12/12/1 | 2 | 1,104 | 0 | 236 | 0 | 0 | 0.1808 | 2:1104 |
| [flask](https://github.com/pallets/flask) | legacy_unverified | additional | `d318b683` | 494 | 12/12/1 | 0 | 494 | 0 | 0 | 0 | 0 | 0.0000 | 0:494 |
| [flexget](https://github.com/Flexget/Flexget) | protocol_complete_local_checks | CANNIER same revision | `4fb25084` | 1,363 | 12/12/1 | 4 | 1,326 | 1 | 32 | 0 | 0 | 0.3008 | 4:1326 |
| [fonttools](https://github.com/fonttools/fonttools) | protocol_complete_local_checks | CANNIER same revision | `f3a90309` | 3,818 | 12/12/1 | 0 | 3,806 | 0 | 12 | 0 | 0 | 0.0000 | 0:3806 |
| [freezegun](https://github.com/spulec/freezegun) | protocol_complete_local_checks | additional | `b46da782` | 112 | 12/12/3 | 15 | 88 | 3 | 6 | 0 | 0 | 14.5631 | 15:88 |
| [fsspec](https://github.com/fsspec/filesystem_spec) | legacy_unverified | additional | `13b0bce8` | 1,779 | 12/12/1 | 2 | 1,492 | 0 | 285 | 0 | 0 | 0.1339 | 2:1492 |
| [graphene](https://github.com/graphql-python/graphene) | protocol_complete_local_checks | CANNIER same revision | `7d2af310` | 350 | 12/12/1 | 1 | 345 | 0 | 4 | 0 | 0 | 0.2890 | 1:345 |
| [httpx](https://github.com/encode/httpx) | baseline_failed | additional | `b5addb64` | 0 | 0/0/0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 0:0 |
| [hydra](https://github.com/facebookresearch/hydra) | protocol_complete_local_checks | CANNIER same revision | `69d31ebf` | 1,580 | 12/12/1 | 18 | 1,520 | 0 | 42 | 0 | 0 | 1.1704 | 18:1520 |
| [hypothesis](https://github.com/HypothesisWorks/hypothesis) | protocol_complete_with_exclusions | CANNIER same revision | `ccac4364` | 4,546 | 12/12/1 | 2 | 4,491 | 1 | 44 | 0 | 8 | 0.0445 | 2:4491 |
| [ipython](https://github.com/ipython/ipython) | protocol_complete_local_checks | CANNIER same revision | `95d2b79a` | 847 | 12/12/3 | 35 | 773 | 1 | 38 | 0 | 0 | 4.3317 | 35:773 |
| [kombu](https://github.com/celery/kombu) | protocol_complete_local_checks | CANNIER same revision | `2aeb7324` | 978 | 12/12/1 | 20 | 765 | 0 | 193 | 0 | 0 | 2.5478 | 20:765 |
| [libcloud](https://github.com/apache/libcloud) | protocol_complete_local_checks | CANNIER same revision | `449b315e` | 9,853 | 12/12/1 | 132 | 9,677 | 0 | 44 | 0 | 0 | 1.3457 | 132:9677 |
| [loguru](https://github.com/Delgan/loguru) | protocol_complete_local_checks | CANNIER same revision | `f31e9714` | 1,359 | 12/12/3 | 20 | 1,339 | 0 | 0 | 0 | 0 | 1.4717 | 20:1339 |
| [mitmproxy](https://github.com/mitmproxy/mitmproxy) | protocol_complete_local_checks | CANNIER same revision | `4511ea7c` | 1,232 | 12/12/1 | 2 | 1,230 | 0 | 0 | 0 | 0 | 0.1623 | 2:1230 |
| [pillow](https://github.com/python-pillow/Pillow) | protocol_complete_local_checks | CANNIER same revision | `92933b86` | 2,796 | 12/12/1 | 0 | 2,596 | 0 | 200 | 0 | 0 | 0.0000 | 0:2596 |
| [prefect](https://github.com/PrefectHQ/prefect) | protocol_complete_local_checks | CANNIER same revision | `6b59d989` | 7,076 | 12/12/1 | 12 | 7,034 | 1 | 29 | 0 | 0 | 0.1703 | 12:7034 |
| [pygithub](https://github.com/PyGithub/PyGithub) | protocol_complete_local_checks | CANNIER same revision | `31538337` | 711 | 12/12/1 | 0 | 711 | 0 | 0 | 0 | 0 | 0.0000 | 0:711 |
| [pyramid](https://github.com/Pylons/pyramid) | protocol_complete_local_checks | CANNIER same revision | `7b182045` | 2,633 | 12/12/1 | 1 | 2,632 | 0 | 0 | 0 | 0 | 0.0380 | 1:2632 |
| [pytest](https://github.com/pytest-dev/pytest) | protocol_complete_local_checks | additional | `a315b97c` | 4,654 | 12/12/1 | 37 | 4,556 | 0 | 61 | 0 | 0 | 0.8056 | 37:4556 |
| [reframe](https://github.com/eth-cscs/reframe) | protocol_complete_local_checks | additional | `576eb3f1` | 736 | 12/12/3 | 9 | 630 | 0 | 97 | 0 | 0 | 1.4085 | 9:630 |
| [requests](https://github.com/psf/requests) | protocol_complete_local_checks | CANNIER same revision | `a1a6a549` | 561 | 12/12/1 | 0 | 548 | 0 | 13 | 0 | 0 | 0.0000 | 0:548 |
| [rich](https://github.com/Textualize/rich) | protocol_complete_local_checks | additional | `9d8f9a37` | 981 | 12/12/1 | 5 | 952 | 0 | 24 | 0 | 0 | 0.5225 | 5:952 |
| [salt](https://github.com/saltstack/salt) | protocol_complete_local_checks | CANNIER same revision | `bac2d1e6` | 2,902 | 12/12/1 | 3 | 2,671 | 0 | 228 | 0 | 0 | 0.1122 | 3:2671 |
| [scikit_image](https://github.com/scikit-image/scikit-image) | protocol_complete_local_checks | CANNIER same revision | `8fbbb516` | 6,317 | 12/12/1 | 1 | 6,274 | 0 | 42 | 0 | 0 | 0.0159 | 1:6274 |
| [seaborn](https://github.com/mwaskom/seaborn) | protocol_complete_local_checks | CANNIER same revision | `703259f2` | 1,048 | 12/12/1 | 2 | 1,023 | 0 | 23 | 0 | 0 | 0.1951 | 2:1023 |
| [setuptools](https://github.com/pypa/setuptools) | protocol_complete_with_exclusions | CANNIER same revision | `4d64156d` | 842 | 12/12/1 | 7 | 703 | 0 | 132 | 0 | 0 | 0.9859 | 7:703 |
| [sunpy](https://github.com/sunpy/sunpy) | protocol_complete_local_checks | CANNIER changed/unknown revision | `b0712590` | 2,287 | 12/12/1 | 2 | 2,053 | 0 | 232 | 0 | 0 | 0.0973 | 2:2053 |
| [tornado](https://github.com/tornadoweb/tornado) | protocol_complete_local_checks | CANNIER same revision | `2047e7ae` | 1,154 | 12/12/1 | 0 | 1,103 | 0 | 51 | 0 | 0 | 0.0000 | 0:1103 |
| [urllib3](https://github.com/urllib3/urllib3) | protocol_complete_local_checks | CANNIER changed/unknown revision | `a5d70ebf` | 2,633 | 12/12/1 | 4 | 2,337 | 0 | 292 | 0 | 0 | 0.1709 | 4:2337 |
| [xonsh](https://github.com/xonsh/xonsh) | protocol_complete_with_exclusions | CANNIER same revision | `e9b12c8b` | 4,894 | 12/12/1 | 19 | 4,779 | 76 | 20 | 0 | 0 | 0.3960 | 19:4779 |

## Retained identities and primary cohort eligibility

| Project | Retained identities | Excluded identities | Eligible flaky | Eligible all-pass | Flaky % strict | Primary project eligible |
|---|---:|---:|---:|---:|---:|---|
| airflow | 3,978 | 0 | 313 | 3,461 | 8.2936 | yes |
| celery | 2,381 | 0 | 7 | 2,325 | 0.3002 | yes |
| cirq | 12,189 | 8,759 | 16 | 12,173 | 0.1313 | yes |
| click | 2,084 | 0 | 0 | 1,975 | 0.0000 | no |
| conan | 4,083 | 0 | 24 | 3,663 | 0.6509 | yes |
| dask | 10,132 | 0 | 1 | 8,525 | 0.0117 | yes |
| djangorestframework | 1,403 | 0 | 1 | 1,401 | 0.0713 | yes |
| electrum | 545 | 0 | 0 | 542 | 0.0000 | yes |
| filelock | 1,342 | 0 | 2 | 1,104 | 0.1808 | yes |
| flask | 494 | 0 | 0 | 494 | 0.0000 | no |
| flexget | 1,363 | 0 | 4 | 1,326 | 0.3008 | yes |
| fonttools | 3,818 | 0 | 0 | 3,806 | 0.0000 | yes |
| freezegun | 112 | 0 | 15 | 88 | 14.5631 | yes |
| fsspec | 1,779 | 0 | 2 | 1,492 | 0.1339 | no |
| graphene | 350 | 0 | 1 | 345 | 0.2890 | yes |
| httpx | 0 | 0 | 0 | 0 | N/A | no |
| hydra | 1,580 | 0 | 18 | 1,520 | 1.1704 | yes |
| hypothesis | 4,538 | 8 | 2 | 4,491 | 0.0445 | yes |
| ipython | 847 | 0 | 35 | 773 | 4.3317 | yes |
| kombu | 978 | 0 | 20 | 765 | 2.5478 | yes |
| libcloud | 9,853 | 0 | 132 | 9,677 | 1.3457 | yes |
| loguru | 1,359 | 0 | 20 | 1,339 | 1.4717 | yes |
| mitmproxy | 1,232 | 0 | 2 | 1,230 | 0.1623 | yes |
| pillow | 2,796 | 0 | 0 | 2,596 | 0.0000 | yes |
| prefect | 7,076 | 0 | 12 | 7,034 | 0.1703 | yes |
| pygithub | 711 | 0 | 0 | 711 | 0.0000 | yes |
| pyramid | 2,633 | 0 | 1 | 2,632 | 0.0380 | yes |
| pytest | 4,654 | 0 | 37 | 4,556 | 0.8056 | yes |
| reframe | 736 | 0 | 9 | 630 | 1.4085 | yes |
| requests | 561 | 0 | 0 | 548 | 0.0000 | yes |
| rich | 981 | 0 | 5 | 952 | 0.5225 | yes |
| salt | 2,902 | 0 | 3 | 2,671 | 0.1122 | yes |
| scikit_image | 6,317 | 0 | 1 | 6,274 | 0.0159 | yes |
| seaborn | 1,048 | 0 | 2 | 1,023 | 0.1951 | yes |
| setuptools | 841 | 1 | 7 | 702 | 0.9873 | yes |
| sunpy | 2,287 | 0 | 2 | 2,053 | 0.0973 | yes |
| tornado | 1,154 | 0 | 0 | 1,103 | 0.0000 | yes |
| urllib3 | 2,633 | 0 | 4 | 2,337 | 0.1709 | yes |
| xonsh | 4,810 | 84 | 19 | 4,770 | 0.3967 | yes |

## Raw detection observations and timing

These are repeated testcase rows, not distinct tests. Repeated identities are retained in these raw totals but quarantined from labels.

| Project | Baseline | Recorded baseline count | PASS rows | FAIL rows | ERROR rows | SKIP rows | Rounds with FAIL/ERROR O/R/Rev | Detection hours |
|---|---|---:|---:|---:|---:|---:|---|---:|
| airflow | PASSED | 3978 | 92,749 | 1,622 | 0 | 5,079 | 0/12/1 | 3.016 |
| celery | PASSED | 2381 | 58,261 | 39 | 0 | 1,225 | 0/11/1 | 0.330 |
| cirq | PASSED | 12609 | 313,140 | 135 | 0 | 1,950 | 0/12/1 | 1.271 |
| click | PASSED (Attempt 1, 11.44s) | unavailable | 49,375 | 0 | 0 | 2,725 | 0/0/0 | unverified |
| conan | PASSED | 4083 | 92,073 | 102 | 0 | 9,900 | 1/12/1 | 4.482 |
| dask | PASSED | 10132 | 213,141 | 9 | 0 | 40,150 | 0/8/1 | 3.894 |
| djangorestframework | PASSED | 1403 | 35,042 | 8 | 0 | 25 | 0/7/1 | 0.043 |
| electrum | PASSED | 545 | 13,550 | 0 | 0 | 75 | 0/0/0 | 0.325 |
| filelock | PASSED | 1342 | 27,647 | 3 | 0 | 5,900 | 0/2/0 | 7.943 |
| flask | PASSED (Attempt 1, 8.76s) | unavailable | 12,350 | 0 | 0 | 0 | 0/0/0 | unverified |
| flexget | PASSED | 1363 | 33,245 | 29 | 0 | 801 | 0/10/1 | 1.307 |
| fonttools | PASSED | 3818 | 95,150 | 0 | 0 | 300 | 0/0/0 | 0.124 |
| freezegun | PASSED | 112 | 2,796 | 57 | 0 | 171 | 0/9/3 | 0.005 |
| fsspec | PASSED (Attempt 1, 61.74s) | unavailable | 37,329 | 21 | 0 | 7,125 | 0/12/1 | unverified |
| graphene | PASSED | 350 | 8,641 | 9 | 0 | 100 | 0/8/1 | 0.055 |
| httpx | FAILED | 0 | 0 | 0 | 0 | 0 | 0/0/0 | unverified |
| hydra | PASSED | 1580 | 38,307 | 143 | 0 | 1,050 | 0/12/1 | 0.650 |
| hypothesis | PASSED | 4554 | 112,722 | 5 | 0 | 1,123 | 0/5/0 | 7.327 |
| ipython | PASSED | 847 | 21,510 | 321 | 0 | 1,038 | 0/12/3 | 0.231 |
| kombu | PASSED | 978 | 19,477 | 102 | 46 | 4,825 | 0/12/1 | 0.072 |
| libcloud | PASSED | 9853 | 244,570 | 655 | 0 | 1,100 | 0/12/1 | 0.299 |
| loguru | PASSED | 1359 | 36,583 | 110 | 0 | 0 | 0/8/3 | 0.295 |
| mitmproxy | PASSED | 1232 | 30,790 | 10 | 0 | 0 | 0/8/1 | 0.062 |
| pillow | PASSED | 2796 | 64,900 | 0 | 0 | 5,000 | 0/0/0 | 0.243 |
| prefect | PASSED | 7076 | 176,134 | 40 | 0 | 726 | 7/11/1 | 1.552 |
| pygithub | PASSED | 711 | 17,775 | 0 | 0 | 0 | 0/0/0 | 0.163 |
| pyramid | PASSED | 2633 | 65,823 | 2 | 0 | 0 | 0/2/0 | 0.065 |
| pytest | PASSED | 4654 | 114,728 | 97 | 0 | 1,525 | 0/12/1 | 1.687 |
| reframe | PASSED | 736 | 17,244 | 8 | 1 | 2,619 | 0/6/0 | 0.293 |
| requests | PASSED | 561 | 13,700 | 0 | 0 | 325 | 0/0/0 | 0.438 |
| rich | PASSED | 981 | 23,877 | 48 | 0 | 600 | 0/12/1 | 0.034 |
| salt | PASSED | 2902 | 66,832 | 18 | 0 | 5,700 | 0/10/1 | 0.796 |
| scikit_image | PASSED | 6317 | 156,867 | 8 | 0 | 1,050 | 0/7/1 | 0.767 |
| seaborn | PASSED | 1048 | 25,623 | 2 | 0 | 575 | 0/1/0 | 1.328 |
| setuptools | PASSED | 842 | 17,700 | 20 | 30 | 3,300 | 0/11/1 | 1.492 |
| sunpy | PASSED | 2287 | 51,361 | 14 | 0 | 5,800 | 0/12/1 | 0.949 |
| tornado | PASSED | 1154 | 27,575 | 0 | 0 | 1,275 | 0/0/0 | 0.111 |
| urllib3 | PASSED | 2633 | 58,506 | 18 | 1 | 7,300 | 1/10/1 | 0.586 |
| xonsh | PASSED | 4822 | 119,848 | 178 | 0 | 524 | 0/12/1 | 0.588 |

## Configuration patterns among observed flaky tests

| Project | Mixed original outcomes | Failure only under reordering | Original failure/pass elsewhere | Other |
|---|---:|---:|---:|---:|
| airflow | 0 | 313 | 0 | 0 |
| celery | 0 | 7 | 0 | 0 |
| cirq | 0 | 16 | 0 | 0 |
| click | 0 | 0 | 0 | 0 |
| conan | 1 | 23 | 0 | 0 |
| dask | 0 | 1 | 0 | 0 |
| djangorestframework | 0 | 1 | 0 | 0 |
| electrum | 0 | 0 | 0 | 0 |
| filelock | 0 | 2 | 0 | 0 |
| flask | 0 | 0 | 0 | 0 |
| flexget | 0 | 4 | 0 | 0 |
| fonttools | 0 | 0 | 0 | 0 |
| freezegun | 0 | 15 | 0 | 0 |
| fsspec | 0 | 2 | 0 | 0 |
| graphene | 0 | 1 | 0 | 0 |
| httpx | 0 | 0 | 0 | 0 |
| hydra | 0 | 18 | 0 | 0 |
| hypothesis | 0 | 2 | 0 | 0 |
| ipython | 0 | 35 | 0 | 0 |
| kombu | 0 | 20 | 0 | 0 |
| libcloud | 0 | 132 | 0 | 0 |
| loguru | 0 | 20 | 0 | 0 |
| mitmproxy | 0 | 2 | 0 | 0 |
| pillow | 0 | 0 | 0 | 0 |
| prefect | 4 | 8 | 0 | 0 |
| pygithub | 0 | 0 | 0 | 0 |
| pyramid | 0 | 1 | 0 | 0 |
| pytest | 0 | 37 | 0 | 0 |
| reframe | 0 | 9 | 0 | 0 |
| requests | 0 | 0 | 0 | 0 |
| rich | 0 | 5 | 0 | 0 |
| salt | 0 | 3 | 0 | 0 |
| scikit_image | 0 | 1 | 0 | 0 |
| seaborn | 0 | 2 | 0 | 0 |
| setuptools | 0 | 7 | 0 | 0 |
| sunpy | 0 | 2 | 0 | 0 |
| tornado | 0 | 0 | 0 | 0 |
| urllib3 | 1 | 3 | 0 | 0 |
| xonsh | 0 | 19 | 0 | 0 |

## Project audit details and effective observation budgets

### airflow

- Commit: `c743b95a02ba1ec04013635a56ad042ce98823d2`; CANNIER inventory commit: `c743b95a02ba1ec04013635a56ad042ce98823d2`.
- Environment ID: `738ae99d1aab1870a90d6133fccd6a50c1092b140363f892e4ec13b09e88b64a`; Python: Python 3.8.7; platform: Linux.
- Effective non-skip observations per test (N: number of tests): `{0: 203, 21: 1, 25: 3774}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### celery

- Commit: `552e067b40198429cd7c866a397069366ac8e530`; CANNIER inventory commit: `552e067b40198429cd7c866a397069366ac8e530`.
- Environment ID: `e7cd5fa838011dd5cac7d486179b8c032563a61fc1bde302817d33dd108441de`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 49, 25: 2332}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### cirq

- Commit: `782c14e0cc821794d21e82f30df8e6998f4b9992`; CANNIER inventory commit: `782c14e0cc821794d21e82f30df8e6998f4b9992`.
- Environment ID: `c876471aa87ee009c977dfe011c229b80501a1b1f2ad2872a388e77a31d79f8b`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 1665, 1: 6393, 2: 426, 3: 110, 4: 59, 5: 38, 6: 30, 7: 18, 8: 11, 9: 2, 12: 1, 14: 2, 23: 1, 24: 1, 25: 12191}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

- Documented identity exclusions: {'Source family has inconsistent parameterized identities across detection rounds; exact case/input correspondence cannot be verified.': 8759}.

### click

- Commit: `6aabf099bfdd4c1e75fe8d0e0d4241372b988ab1`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `unavailable`; Python: unavailable; platform: unavailable.
- Effective non-skip observations per test (N: number of tests): `{0: 109, 25: 1975}`.
- Missing project metadata: environment.json, baseline_state.json, setup_state.json, cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: Legacy/missing environment-bound manifest and passing baseline XML verification.

### conan

- Commit: `d524074945e840f9c9f1d4d6eba462bf6a1dc608`; CANNIER inventory commit: `d524074945e840f9c9f1d4d6eba462bf6a1dc608`.
- Environment ID: `c40612b06eceef0ffe63b7f048cd018758843122fb96a6048d24680cb05cb871`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 396, 25: 3687}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### dask

- Commit: `d5bbad0b1f32b3c904abc4fd020bef9c5092d2a3`; CANNIER inventory commit: `d5bbad0b1f32b3c904abc4fd020bef9c5092d2a3`.
- Environment ID: `890712fe0c63fd0d9ff11c254d9545fa5082b151b4eb375059f0788b32099134`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 1606, 25: 8526}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### djangorestframework

- Commit: `0323d6f8955f987771269506ca5da461e2e7a248`; CANNIER inventory commit: `0323d6f8955f987771269506ca5da461e2e7a248`.
- Environment ID: `2b0525ceb90d93c7b7ff9634323acf8a4a3f30c55715213b5266cd3694a6f2ec`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 1, 25: 1402}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### electrum

- Commit: `d8d2c180aafaec1ae9bc68c27a7d780df8de4348`; CANNIER inventory commit: `d8d2c180aafaec1ae9bc68c27a7d780df8de4348`.
- Environment ID: `e8a3fcccbf98373dee3e6914445c3b6ed1e9ca36a21017f1b91576752e6a7aa5`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 3, 25: 542}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### filelock

- Commit: `82f66d7b0aaa83755f8d71d0b0da88408b58ec4a`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `371316aad879f326b758a117edd65f06f630ced42db8a3718060dc19f0eadb90`; Python: Python 3.11.9; platform: Windows-10-10.0.26200-SP0.
- Effective non-skip observations per test (N: number of tests): `{0: 236, 25: 1106}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### flask

- Commit: `d318b683471101618febed18996405ad26462110`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `unavailable`; Python: unavailable; platform: unavailable.
- Effective non-skip observations per test (N: number of tests): `{25: 494}`.
- Missing project metadata: environment.json, baseline_state.json, setup_state.json, cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: Legacy/missing environment-bound manifest and passing baseline XML verification.

### flexget

- Commit: `4fb250844d59e73304b7d306457ad61e070e1261`; CANNIER inventory commit: `4fb250844d59e73304b7d306457ad61e070e1261`.
- Environment ID: `1a807e7c1b4aeeaf8b550c3925b4357f5fd0c1036b7251e8b89ce742fc245711`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 32, 24: 1, 25: 1330}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### fonttools

- Commit: `f3a903093a4600f3d757bf9b22f387a561fcb584`; CANNIER inventory commit: `f3a903093a4600f3d757bf9b22f387a561fcb584`.
- Environment ID: `f42866a3f6c0a38a97c72aa354f7a439b4b66f63c24549c05cad9734b648afb7`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 12, 25: 3806}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### freezegun

- Commit: `b46da782a7a051081fd51577749cfc0074db0cc6`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `0da8ecfbaadb3a84430abe45ec04adae62743a21a06cc6c316b35132b93453c5`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 6, 24: 3, 27: 103}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### fsspec

- Commit: `13b0bce86a52b7c9a393753fc0381f3c5a955622`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `unavailable`; Python: unavailable; platform: unavailable.
- Effective non-skip observations per test (N: number of tests): `{0: 285, 25: 1494}`.
- Missing project metadata: environment.json, baseline_state.json, setup_state.json, cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: Legacy/missing environment-bound manifest and passing baseline XML verification.

### graphene

- Commit: `7d2af3104e3c01ce4f9a1580faf40d8179079008`; CANNIER inventory commit: `7d2af3104e3c01ce4f9a1580faf40d8179079008`.
- Environment ID: `05489940fc9dac55ce4fd5240b670f7df6f4cfee2a9c7620f9aeacbc49bebb79`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 4, 25: 346}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### httpx

- Commit: `b5addb64f0161ff6bfe94c124ef76f6a1fba5254`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `unavailable`; Python: Python 3.11.9; platform: Windows-10-10.0.26200-SP0.
- Effective non-skip observations per test (N: number of tests): `{}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: Recorded baseline failed; excluded without detection rounds.

### hydra

- Commit: `69d31ebf79a93f0a8378d896a359fb47b09f5074`; CANNIER inventory commit: `69d31ebf79a93f0a8378d896a359fb47b09f5074`.
- Environment ID: `efab846ffb93c9d4d0429acb36f431063e0d259bfd5a1c71c74b9fcc4fd4087a`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 42, 25: 1538}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### hypothesis

- Commit: `ccac4364979effc2b22e2f943176b2b1f025c448`; CANNIER inventory commit: `ccac4364979effc2b22e2f943176b2b1f025c448`.
- Environment ID: `d0dbd58e75b7ad9946e1d347b7149592a46ee33e06dc005c9aed6a43896ecce7`; Python: Python 3.8.18; platform: Linux.
- Effective non-skip observations per test (N: number of tests): `{0: 52, 2: 1, 25: 4493}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

- Documented identity exclusions: {'Pinned source has duplicate parameter values; pytest-generated parameter IDs collide. Original repeated rows cannot be assigned reliably under reordered execution.': 8}.

### ipython

- Commit: `95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d`; CANNIER inventory commit: `95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d`.
- Environment ID: `9e2ed8560889f4fbfda319c37a494315813033120e6bb65e5926f08dc4ae9857`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 38, 15: 1, 27: 808}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### kombu

- Commit: `2aeb73248b4a0bf8ad3de81a0f40733e7cd42255`; CANNIER inventory commit: `2aeb73248b4a0bf8ad3de81a0f40733e7cd42255`.
- Environment ID: `131113883a7fce0f4981ab63a3176ee661ec3c31ea1757c366f64a798c79a198`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 193, 25: 785}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### libcloud

- Commit: `449b315ea47ba85f79b4062b1d398e94e545d273`; CANNIER inventory commit: `449b315ea47ba85f79b4062b1d398e94e545d273`.
- Environment ID: `4041d1ebd51ec348e4f45a1d856d456931f193bd5fa08550bb9c0e92cb41f8b5`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 44, 25: 9809}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### loguru

- Commit: `f31e97142adc1156693a26ecaf47208d3765a6e3`; CANNIER inventory commit: `f31e97142adc1156693a26ecaf47208d3765a6e3`.
- Environment ID: `a7e197e360752061c0d1bbad9d57abfd26f8b6ba82ba9fff1b773308245f3e13`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{27: 1359}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### mitmproxy

- Commit: `4511ea7c24a3d62373d6fa6d221ac96212ce11e4`; CANNIER inventory commit: `4511ea7c24a3d62373d6fa6d221ac96212ce11e4`.
- Environment ID: `de2bf3e98bc16fbe5247cf1b878a690baf67b1a804125fc300c736a9436a4fd8`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{25: 1232}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### pillow

- Commit: `92933b86574b9c80764bf52c357ed29e1ef53382`; CANNIER inventory commit: `92933b86574b9c80764bf52c357ed29e1ef53382`.
- Environment ID: `4bdaec17a6e078377de89da965ca0354515fdfe2f0eb89b2429caebc8439f693`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 200, 25: 2596}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### prefect

- Commit: `6b59d989dec33aad8c62ea2476fee519c32f5c63`; CANNIER inventory commit: `6b59d989dec33aad8c62ea2476fee519c32f5c63`.
- Environment ID: `584f10371453a0d2a952a55a21ea7eb9b6a8607648b3fa48a4471548c0654cd6`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 29, 24: 1, 25: 7046}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### pygithub

- Commit: `31538337faaa61e104afede75a5fac802c9a1ab3`; CANNIER inventory commit: `31538337faaa61e104afede75a5fac802c9a1ab3`.
- Environment ID: `9ddb1538d907e2f1bd9d058fb76b90e4108b92eb43c51b434ab79372efee5d24`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{25: 711}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### pyramid

- Commit: `7b182045ee77cdfb38fda5e55ccbdcd8ed1c9468`; CANNIER inventory commit: `7b182045ee77cdfb38fda5e55ccbdcd8ed1c9468`.
- Environment ID: `e83212b0305eb6b7e4fb37f52d53eb3af640bfbcfedc378f64e988780c3db660`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{25: 2633}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### pytest

- Commit: `a315b97ce61f158bef9957152c8415fe743aa553`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `dae24707ef4e2ae0a67ff754556188d4c044de89e60aa63489741c38bdef402d`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{0: 61, 25: 4593}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### reframe

- Commit: `576eb3f1dcc015d1e6d7a10602c748d4f810da68`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `9c96fe8e1575152af2a251daea86d03931ad7b6e7810f0fe1e7fa4c8e5427995`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 97, 27: 639}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### requests

- Commit: `a1a6a549a0143d9b32717dbe3d75cd543ae5a4f6`; CANNIER inventory commit: `a1a6a549a0143d9b32717dbe3d75cd543ae5a4f6`.
- Environment ID: `169f6bbff0725a0c5c7d3ecea5d9fc4f305212384bebbb73d37cc9d1646e7168`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 13, 25: 548}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### rich

- Commit: `9d8f9a372cc5916fd4781fec207ced7ddac2f08f`; CANNIER inventory commit: `not a listed subject`.
- Environment ID: `28d73a5ab2ba39c8b1ec88ed6cbafea7968caa168d74e6b9583ce7a808dc9fd7`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{0: 24, 25: 957}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### salt

- Commit: `bac2d1e6aeea8f12dd1712207b87ea2695f35b7c`; CANNIER inventory commit: `bac2d1e6aeea8f12dd1712207b87ea2695f35b7c`.
- Environment ID: `6fc0ce66629811a7895d910576fa356248c8a1ee70bd732e28a0d0964db9c5a6`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 228, 25: 2674}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### scikit_image

- Commit: `8fbbb5169b8da6fb26b107a0a8c6de46a93f37cc`; CANNIER inventory commit: `8fbbb5169b8da6fb26b107a0a8c6de46a93f37cc`.
- Environment ID: `ad86d3e579b1f15403720f2f5b0162605fad3d2aa7939c58eeb3e3fcb84944bc`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 42, 25: 6275}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### seaborn

- Commit: `703259f2dca711205f81d2d8f9e3fa45774eb0da`; CANNIER inventory commit: `703259f2dca711205f81d2d8f9e3fa45774eb0da`.
- Environment ID: `be194abc63eb1a9fa6ed5344918c37b98e5da7a0eb272c14571400bdcc383548`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 23, 25: 1025}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### setuptools

- Commit: `4d64156de17596dae33f2b12aaaea1d6c9327fd9`; CANNIER inventory commit: `4d64156de17596dae33f2b12aaaea1d6c9327fd9`.
- Environment ID: `9b606fd14e14200dcc525c72f0fcd7255ca0de401f0a7bbcfa3c279e7060332e`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 132, 25: 710}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

- Documented identity exclusions: {'pytest-checkdocs==2.7.1 CheckdocsItem named project is a package documentation check, not a source test function.': 1}.

### sunpy

- Commit: `b071259098e9ff1dbd9e66071999f60fdf9b0fd7`; CANNIER inventory commit: `7c6e51e85410f3647af81e601a4bb4c9073a50c8`.
- Environment ID: `cb9e435afd60e473d5eb94de8d53a4ffa7c678baa097e65d586acdd85d10d802`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 232, 25: 2055}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

### tornado

- Commit: `2047e7ae3c825bf52dad10cc8402d09e11091bc1`; CANNIER inventory commit: `2047e7ae3c825bf52dad10cc8402d09e11091bc1`.
- Environment ID: `a04fb26ecc9db0ed0544bc7827d231908a12cbc269625df771138c27a0fa3684`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.34.
- Effective non-skip observations per test (N: number of tests): `{0: 51, 25: 1103}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### urllib3

- Commit: `a5d70ebfd6a30ceba0e9cc322089a6497dcd643e`; CANNIER inventory commit: `ba95e9eac73452d3bccfb5413b00d9a4fe3e4c31`.
- Environment ID: `02a8b8a442a0ab97e6893c75b1cfb3d51fcd890f222389be30bcfe4fbcb5e544`; Python: Python 3.11.9; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39.
- Effective non-skip observations per test (N: number of tests): `{0: 292, 25: 2341}`.
- Missing project metadata: cannier_setup_recipe.json, cannier_dependency_snapshot.txt.
- Local audit issues: none found by implemented checks.

### xonsh

- Commit: `e9b12c8b701a75b5ecb8d20f3aad7d3e5aca64bf`; CANNIER inventory commit: `e9b12c8b701a75b5ecb8d20f3aad7d3e5aca64bf`.
- Environment ID: `687efaae0e9d711b65634ebfb6a28ececd7e734720634cf401fb07cb9ee76e99`; Python: Python 3.8.18; platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.2.5.
- Effective non-skip observations per test (N: number of tests): `{0: 20, 1: 76, 25: 4798}`.
- Missing project metadata: none.
- Local audit issues: none found by implemented checks.

- Documented identity exclusions: {'Source family has inconsistent parameterized identities across detection rounds; exact case/input correspondence cannot be verified.': 84}.

## Deliverables and reproduction

- `project_summary.csv` and `audit.json`: project counts, statuses, membership, exclusions, and issues.
- `rounds.csv`: each checkpoint/file, ordering seed, exit code, raw outcomes, timing, and validation issues.
- `test_details.csv.gz`: every original test identity, descriptive label, effective N, outcomes, exclusion reason, project audit status, and primary eligibility. Only primary_eligible=True rows qualify for the binary cohort; eligible_identity alone does not override a legacy/failed project status. Decompress with any gzip tool or Python gzip.open. P=PASS, F=FAIL, E=ERROR, S=SKIP, D=duplicate identity, M=missing; character positions follow each project's round_order in audit.json.
- `evidence_hashes.csv`: SHA-256 of parsed baseline/detection XML and supporting project metadata. Raw files remain unchanged.
- `observed_flaky_tests.csv`: a convenient uncompressed subset of the test export; project audit status must accompany its interpretation.

Reproduce with `python scripts/consolidate_workflow_evidence.py --repos-dir <imported-repos> --output reports/workflow-audit --resolution-rules reports/evidence-recovery/identity_resolution_rules.json --source-root <pinned-source-root>`. Omit resolution arguments for the conservative audit without source-verified exclusions.

This report supersedes historical aggregate counts for this imported snapshot. It does not yet constitute a source-resolved training dataset or model-training result.
