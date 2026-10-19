# Q3/Q4 base-paper search, round 2 (19 October 2026)

Status: **Empirically Verified** for search coverage, as of 19 October 2026.

## Method

1. Downloaded SCImago's 2025 journal rankings (`journalrank.php?out=xls`, type = journal) for seven
   computer-science categories: Software, Computer Science Applications, Computer Science (misc.),
   Information Systems, Artificial Intelligence, Computational Theory and Mathematics, and Hardware
   and Architecture. That gives 1,876 journals. Of these, **743 are Q3 or Q4 in their best category**,
   with quartiles taken from SCImago's per-journal category list.
2. Ran OpenAlex searches (first 200 results each; deeper paging needs an API key) for the terms
   flaky test(s), test flakiness, flakiness, non-deterministic or nondeterministic test(s),
   intermittent test failures, order-dependent tests, test order dependency, test reruns and
   unstable tests. Kept every work that had any location in one of the 743 journals.
3. Searched Crossref for flaky-test book chapters, and checked SCImago quartiles for proceedings
   series and book series.

## Result

**Q3/Q4 journals:** the same five flaky-test papers as round 1. No other flaky-test paper appears in
any of the 743 Q3/Q4 CS journals. The other matches were unrelated work on nondeterministic automata.

| Paper | Venue (best quartile) | Machine-learning classifier? | Public data? |
|---|---|---|---|
| MDFlaker (2025) | Software Impacts (Q3) | yes (KNN plus a rule) | yes, used in v0.6/v0.7 |
| Adaptive latest-position execution, Android (2024) | IJSEKE (Q3) | no (dynamic scheduling) | no |
| JS-TOD, Jest order-dependency detector (2026) | Science of Computer Programming (Q3) | no (rerun/reorder tool) | tool |
| FlakyLoc (2020) | Journal of Web Engineering (Q3) | no (localization) | no |
| REST testing success factors (2018) | JCS&T Argentina (Q3) | no | no |

**Ranked book series (not journals).** LNCS is Q2 in 2025, so it doesn't qualify. CCIS, LNNS and
Smart Innovation (SIST) are Q4, and LNBIP is Q3. CEUR Workshop Proceedings and Procedia CS have no
quartile. Flaky-test chapters in Q3/Q4 series:
- LNNS 2026, Elgazzar et al., *A Machine Learning-Based Detection of Test Automation Flakiness*.
  It uses industrial Java tests (about 2,500 from six commercial projects) and **no public data**.
- CCIS 2021 (QUATIC), two experience or discussion papers, with no classifier.

## Conclusion

Within Q3/Q4 journals, MDFlaker is the only flaky-test prediction paper whose results could be
reproduced and compared against. v0.6 and v0.7 show that its released data cannot support an
improvement claim. Any further Q3/Q4 route therefore needs **new data**: either MDFlaker's task on
freshly collected CI failures, or a base paper in a Q3/Q4 journal from an adjacent topic.
