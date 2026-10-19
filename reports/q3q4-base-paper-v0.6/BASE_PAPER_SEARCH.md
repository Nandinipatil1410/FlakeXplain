# Q3/Q4-journal base-paper search (v0.6)

Prepared 19 October 2026 on branch `research/q3q4-base-paper` (from `codex/independent-confirmation`).
Status: the literature search and SCImago checks are **Empirically Verified** (sources and dates below).
The recommended experiment is **Proposed**. Its protocol is frozen in `PROTOCOL.md`, and nothing has
been run under it yet. The CANNIER v0.5 result (`reports/cannier-protocol-v0.5/`) is untouched and
remains the fallback.

## Why this search was needed

CANNIER (Parry et al., *Empirical Software Engineering*, 2023) is in a **Q1** journal: SCImago lists
EMSE as Q1 in Software for 2022-2025. If the guide requires the base paper to come from a Q3/Q4
journal, CANNIER does not qualify, whatever the v0.5 result shows.

## Search method

1. OpenAlex: journal articles whose title or abstract matches "flaky test", "flaky tests" or
   "test flakiness" (around 1,800 records, most of them materials-science noise), filtered to
   software-testing titles.
2. Crossref: journal articles whose title matches "flaky test" or "flakiness test prediction", as a
   cross-check on OpenAlex coverage.
3. Web searches aimed at likely lower-quartile venues (IJSEKE, IET Software, e-Informatica, IJACSA,
   MDPI journals, PeerJ CS, Software Quality Journal, STVR, JSEP, ASE journal).
4. Each candidate venue was checked on SCImago (scimagojr.com journal pages, quartile tables for
   2022-2025, read 19 October 2026). Raw output is in `scimago_checks.json`.

Limits: OpenAlex and Crossref under-index some regional Scopus journals. A paper that names flaky
tests only in its body text, or uses another term (for example "non-deterministic tests"), could be
missed. ScienceDirect blocked full-text access with a CAPTCHA, so the full texts of the Software
Impacts and APSEC papers were **not** read.

## Candidates and verified quartiles

"Best quartile" is the best category quartile in SCImago's most recent year (2025).

| Paper | Venue | SCImago quartiles (2022 / 23 / 24 / 25) | Topic | Released data | Fit |
|---|---|---|---|---|---|
| Ahmad, *MDFlaker: a tool for multi-factor detection and root cause analysis of flaky tests*, 2025, doi:10.1016/j.simpa.2025.100794 | Software Impacts | Software: Q3/Q3/Q3/Q3 | KNN classifier of failed executions (flaky vs not), Python projects | **Yes**: GitHub `azeem59/MDFlakerForPaperUpdated` (Apache-2.0), 2,151 labelled rows, Travis build-to-commit maps | **Recommended** (see below) |
| Zhang, Wang, Zhao, *Flaky test detection based on adaptive latest position execution for concurrent Android applications*, 2024, doi:10.1142/s0218194024500232 | IJSEKE | Software: Q4/Q4/Q4/Q3; AI: Q4/Q4/Q4/Q3 | Dynamic event rescheduling, 16 Android flaky tests | Not found | No: Android, dynamic, no ML |
| Hashemi et al., *JS-TOD: detecting order-dependent flaky tests in Jest*, 2026, doi:10.1016/j.scico.2026.103462 | Science of Computer Programming | Software: Q3/Q3/Q3/Q3 | Rerun/reorder tool for JavaScript | Tool | No: JavaScript, no classifier |
| *FlakyLoc: flakiness localization for reliable test suites in web applications*, 2020, doi:10.13052/jwe1540-9589.1927 | Journal of Web Engineering | Software: Q4/Q4/Q3/Q3 | Web flakiness localization | Not checked | No: localization, not prediction |
| *Identifying key success factors in stopping flaky tests in automated REST service testing*, 2018, doi:10.24215/16666038.18.e16 | J. Computer Science & Technology (Argentina) | Software: Q4/Q3/Q4/Q4 | Practitioner success factors | No | No: no classifier |
| *Flaky test automation and mitigating test crashes in agile releases*, 2025, doi:10.22399/ijcesen.3644 | IJCESEN | Engineering (misc.): -/-/Q3/Q3 | Narrative mitigation overview | No | No: no method or evaluation |
| Dai et al., *HgtFlaky*, 2026, doi:10.3390/computers15060372 | Computers (MDPI) | Networks: Q2/Q2/Q2/**Q1**; HCI: Q3/Q3/Q2/Q2 | Graph transformer on CI runtime artifacts (Java benchmarks) | Not checked | Not Q3/Q4 |
| Afeltra et al., *Cross-project flaky test prediction*, 2024; Ahmad et al., *Linguistic diversity*, 2025; Ahmad & Sun, *LLMs for cross-language detection*, 2025; Verdecchia et al., *FLAST*, 2021 | IEEE Access | CS (misc.): Q1 every year 2014-2025 | Static or vocabulary prediction | Varies | Not Q3/Q4 |
| CANNIER (Parry et al., 2023), Pontillo et al. 2022 | Empirical Software Engineering | Software: Q1 | Hybrid rerun + ML; static prediction | Yes | Not Q3/Q4 (current base) |

Other venues checked: STVR is Q3 in Software for 2022-2024 and Q2 in 2025, and Q2 in its other
categories; its only flaky paper is a practitioner survey. *Software: Practice and Experience* is Q2.
*International Journal of Computer Applications* is not indexed in SCImago. The other
flaky-test-prediction journal papers found (TSE, TOSEM, JSS, IST, PACMPL/PACMSE) are all in Q1 venues.

**Finding: the strict Q3/Q4 pool is very thin.** Only one Q3/Q4 journal paper found is a flaky-test
*classifier* with released data, and it is MDFlaker.

## Recommendation: MDFlaker (Software Impacts, Q3)

### Why it is the most feasible to reproduce and beat

- **Python, released labels and code.** The 2,151 rows cover three Python projects: spaCy (1,080),
  django-rest-framework (536) and Superset (535). The released code is `F_Detector/evaluate.py`
  (KNN, k=8, p=1).
- **Labels are rerun-based.** In the released code, a failed test execution is labelled flaky when it
  did not fail in all 30 reruns (`failed_times != 30`).
- **Source context is recoverable.** Every one of the 62 django-rest-framework build IDs in the
  dataset appears in the released Travis build history, with its `commit_sha`, failing test file,
  directory and traceback. That is enough to check out each commit and run our existing extractor
  (`scripts/confirmation_features.py::extract`, the same function behind the v0.4/v0.5 66-column
  context table). The spaCy and Superset histories are also released; their coverage is checked by
  gate G1 in the protocol.
- **Our pipelines transfer directly.** We reuse the Extra Trees and Random Forest configurations, the
  paired repeated-CV harness and the frozen-rule discipline from v0.5. A secondary arm also uses the
  96,118-case corpus as a transfer prior (see the protocol).
- **The baseline is weak and has documented quirks.** The base model is unscaled KNN on 4-5 features.
  The released code casts every feature to `int`, which truncates flaky frequency (for example 0.38)
  to 0. It is evaluated on a single unseeded random 80-row hold-out, so there is real headroom. The
  protocol compares against the *stronger* of the as-released and as-described baselines, to avoid a
  straw man.

### Risks the guide should know before accepting it

1. **Software Impacts is a software-description journal.** The MDFlaker article is a short tool
   paper. Its empirical evaluation is in the APSEC 2021 conference paper (doi:10.1109/APSEC53868.2021.00041),
   which reports 2,166 executions against 2,151 released rows. The guide should confirm that a
   Q3 tool paper counts as a "base paper".
2. **Different task.** MDFlaker classifies *failed executions* (is this failure flaky?). FlakeXplain
   v0.1-v0.5 predicts *test-level* instability. The 96,118-case corpus and the matched CANNIER data
   are therefore not the evaluation data here; only the extractor, the pipelines and an optional prior
   transfer.
3. **Heavy repetition.** The 2,151 rows contain only 448 distinct test names; 1,991 rows belong to a
   test name that occurs more than once. Static features are constant per test, so a row-level split
   would let a forest memorize test identity. The frozen primary analysis therefore groups folds by
   test.
4. **Small and old.** There are 3 projects. The data come from Travis CI builds in 2020, and old
   commits must still be retrievable from GitHub.
5. **Published numbers not yet read.** The reproduction gate needs the precision, recall and F1 that
   the paper reports. Someone with library access must copy them from the PDFs into
   `published_reference.json` before stage 2 (see the protocol).

### If the guide accepts Q1/Q2 base papers after all

Keep CANNIER v0.5 as the base. Its frozen classification rule was not met (Victim-vs-Rest only), but
its cost rule was met. MDFlaker can still serve as a second, Q3 comparison.

## Sources

- SCImago journal pages for IEEE Access, Computers, IJSEKE, Science of Computer Programming,
  Software Impacts, Journal of Web Engineering, J. Computer Science & Technology (Argentina), IJCESEN,
  EMSE, JSS, STVR and SPE, read 19 October 2026 (`scimago_checks.json`).
- OpenAlex API (`api.openalex.org/works`) and Crossref API (`api.crossref.org/works`), queried
  19 October 2026.
- MDFlaker release: https://github.com/azeem59/MDFlakerForPaperUpdated at commit `618dc047`
  (2021-01-14). Dataset hashes are in `protocol.json`.
- APSEC 2021 record: https://research.chalmers.se/en/publication/547266
