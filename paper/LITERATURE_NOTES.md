# Literature notes for §3 (related work)

Compiled 21 October 2026 for `paper/DRAFT.md` §3. These are notes only; DRAFT.md has not been edited.

**How things were checked.** Bibliographic details (authors, title, venue, pages, year, DOI) come from the
Crossref record for each DOI (`https://api.crossref.org/works/<DOI>`). Where Crossref lacked a field, the
publisher's page was used and is linked. Summaries come from the published abstract (OpenAlex / Semantic
Scholar copies of the publisher abstract, or the arXiv abstract where stated). We have **not** read the
full texts. Numbers in summaries are the abstracts' own numbers. Anything that could not be checked is
marked **UNVERIFIED**.

"Relation to our work" refers to the FlakeXplain design: MDFlaker's five factors plus failure-evidence
features, a strict-history rule, and project-separated (cross-project) evaluation, with 30-rerun labels on
fresh CI failures.

---

## Part A. Failure-level classification and triage

These works decide whether a *given failed execution* (or failed job or build) is flaky. The draft's §3.4
covers mostly test-level predictors. This group is the closest prior work to our task.

### A1. DeFlaker (ICSE 2018), failure-level, no ML

- **Ref.** J. Bell, O. Legunsen, M. Hilton, L. Eloussi, T. Yung, D. Marinov, "DeFlaker: Automatically
  detecting flaky tests," in *Proc. 40th Int. Conf. on Software Engineering (ICSE)*, 2018, pp. 433–444.
  doi:10.1145/3180155.3180164.
- **Verified at:** https://api.crossref.org/works/10.1145/3180155.3180164 ; abstract on
  https://2024.esec-fse.org/details/icse-2018/icse-2018-Technical-Papers/99/DeFlaker-Automatically-Detecting-Flaky-Tests
  and the author PDF https://cs.cornell.edu/~legunsen/pubs/BellETAL18DeFlaker.pdf
- **Task:** failure-level (is this newly failing test execution flaky?).
- **Summary:** DeFlaker records coverage of the latest code change and marks a newly failing test that did
  not execute any changed code as flaky, with no rerun. On project histories it found 1,874 flaky tests
  among 4,846 failures with a 1.5% false-alarm rate. Its recall of confirmed flaky tests was 95.5%, against
  23% for Maven's rerun-based detector. A live run on 96 Travis CI projects found 87 previously unknown
  flaky tests in 10 projects.
- **Relation:** This is the classic failure-level baseline. It needs a coverage-instrumented build of each
  change, which we do not have. Our features are cheap: MDFlaker factors and failure text. DeFlaker's
  "did the failure touch the change?" signal is a possible future feature, but not one we use.

### A2. Mozilla "oranges" (ESEC/FSE 2021), failure/job-level, ML

- **Ref.** J. Lampel, S. Just, S. Apel, A. Zeller, "When life gives you oranges: Detecting and diagnosing
  intermittent job failures at Mozilla," in *Proc. 29th ACM Joint European Software Engineering Conf. and
  Symp. on the Foundations of Software Engineering (ESEC/FSE)*, 2021, pp. 1381–1392.
  doi:10.1145/3468264.3473931.
- **Verified at:** https://api.crossref.org/works/10.1145/3468264.3473931 (abstract via OpenAlex
  https://api.openalex.org/works/doi:10.1145/3468264.3473931)
- **Task:** failure-level (failing CI *jobs* classified as real bug or intermittent).
- **Summary:** The authors train classifiers on job telemetry, such as runtime, CPU load, OS version and
  platform, to decide whether a failing Mozilla CI job is a real bug or an intermittent failure. Average
  precision is 73% (up to 100% for some suites) and average recall is 82% (up to 94%).
- **Relation:** This is the nearest open-literature analogue to our task. It works at job granularity and
  uses infrastructure telemetry. We work at test-execution granularity and use code-change, history and
  failure-text factors. It is a single-organisation, within-suite evaluation, so it does not test
  cross-project transfer as our E2/E3 evaluations do.

### A3. Brown build detection (ICSE 2022), build-level, logs

- **Ref.** D. Olewicki, M. Nayrolles, B. Adams, "Towards language-independent brown build detection," in
  *Proc. 44th Int. Conf. on Software Engineering (ICSE)*, 2022, pp. 2177–2188.
  doi:10.1145/3510003.3510122.
- **Verified at:** https://api.crossref.org/works/10.1145/3510003.3510122 (abstract via OpenAlex)
- **Task:** failure-level at build granularity. A "brown" build is a false-positive build failure caused
  by flaky tests or build-script problems.
- **Summary:** The model flags brown builds by textual similarity of the build log to logs of earlier
  brown builds. It was tested on 6 closed-source game-industry projects and Graphviz. Mean F1 is 53%,
  about three times the best baseline and at least as good as human experts. Cross-project training
  helps a new project's onboarding phase. A 30-week training window worked best, and retraining every
  4–5 weeks kept F1 above the baseline.
- **Relation:** This work supports our use of failure-log text as evidence. Its training-window and
  retraining findings are a time-aware evaluation, close in spirit to our strict-history rule. Its
  cross-project onboarding result is the opposite direction to our E2 finding, where the gain did not
  survive strict history across projects. That contrast is worth stating.

### A4. Chromium: predict flaky *failures*, not flaky tests (ASE 2024)

- **Ref.** G. Haben, S. Habchi, J. Micco, M. Harman, M. Papadakis, M. Cordy, Y. Le Traon, "The
  importance of accounting for execution failures when predicting test flakiness," in *Proc. 39th
  IEEE/ACM Int. Conf. on Automated Software Engineering (ASE)*, 2024, pp. 1979–1989.
  doi:10.1145/3691620.3695261.
- **Verified at:** https://api.crossref.org/works/10.1145/3691620.3695261 (abstract via OpenAlex)
- **Task:** argues for failure-level over test-level prediction, using Chromium CI data.
- **Summary:** Tests that fail flakily in one release often fail *correctly* in another. Tests that are
  flaky at some point reveal more than 1/3 of all regression faults. Also, 76.2% of fault-revealing
  executions come from tests that existing predictors classify as flaky. The authors conclude that
  research should predict flaky *executions*, not flaky tests.
- **Arxiv version.** The earlier arXiv version, "The importance of discerning flaky from fault-triggering
  test failures: A case study on the Chromium CI" (arXiv:2302.10594, https://arxiv.org/abs/2302.10594),
  also reports failure-focused predictors, which raised MCC from 0.20 to 0.42. **UNVERIFIED whether the
  MCC result appears in the ASE 2024 paper**: the published abstract does not mention it. Cite the ASE
  version for the motivation only.
- **Relation:** This is the strongest published motivation for our task framing (§2). It also motivates
  our memorization concern: a test that was flaky before is not automatically flaky now.

### A5. Failure de-duplication on 230,439 failures (ICST 2024)

- **Ref.** A. Alshammari, P. Ammann, M. Hilton, J. Bell, "230,439 test failures later: An empirical
  evaluation of flaky failure classifiers," in *Proc. IEEE Conf. on Software Testing, Verification and
  Validation (ICST)*, 2024, pp. 257–268. doi:10.1109/ICST60714.2024.00031.
- **Verified at:** https://api.crossref.org/works/10.1109/icst60714.2024.00031 (abstract via OpenAlex)
- **Task:** failure-level (is this failure message flaky or a true failure?).
- **Summary:** They take 498 flaky tests from 22 open-source Java projects and collect 230,439 failure
  messages, both flaky and true failures, partly by mutation. They then evaluate failure de-duplication,
  which matches a new failure against previously seen flaky and true failures. It works very well for
  some projects (100% specificity) and not at all for others, because flaky and true failure symptoms can
  look alike.
- **Relation:** This is the closest open-source evaluation to ours: failure-level, open Java projects,
  failure-message evidence. Their per-project variability matches our per-project results. It is also a
  direct, simple baseline for our failure-evidence features: does a nearest-match on failure text beat
  the trained model? Note that their true failures are partly mutation-induced, while ours are real CI
  failures. **UNVERIFIED:** the share of mutation-induced failures (this comes from our memory of the
  paper; it is not in the abstract).

### A6. Failure-symptom matching at SAP HANA (ICSME 2024)

- **Ref.** G. An, J. Yoon, T. Bach, J. Hong, S. Yoo, "Just-in-time flaky test detection via abstracted
  failure symptom matching," in *Proc. IEEE Int. Conf. on Software Maintenance and Evolution (ICSME)*,
  2024, pp. 741–752. doi:10.1109/ICSME58944.2024.00078.
- **Verified at:** https://api.crossref.org/works/10.1109/icsme58944.2024.00078 ; abstract at
  https://arxiv.org/abs/2310.06298
- **Task:** failure-level, industrial.
- **Summary:** Error messages and stack traces are abstracted, then matched against symptoms of past
  flaky runs to flag recurring flaky failures without rerunning. On six months of SAP HANA CI data,
  precision is at least 96% and machine time is about 58% lower than a rerun strategy. False positives
  show that informative failure symptoms matter.
- **Relation:** This directly supports traceback and error-message features. Their method can only catch
  *recurring* symptoms, which is the same history dependence our strict-history analysis tries to
  control. It is single-system and industrial; we use open projects.

### A7. Presubmit Rescue at Google (FTW 2024)

- **Ref.** M. Hoang, A. Berding, "Presubmit Rescue: Automatically ignoring flaky test executions," in
  *Proc. 1st Int. Workshop on Flaky Tests (FTW)*, 2024, pp. 1–2. doi:10.1145/3643656.3643896.
- **Verified at:** https://api.crossref.org/works/10.1145/3643656.3643896 (abstract via OpenAlex)
- **Task:** failure-level, industrial.
- **Summary:** This is a two-page workshop paper. Google describes an ML model that predicts whether a
  *failed test execution* was caused by a flake, so that predicted flaky failures can be ignored instead
  of retried or debugged. The abstract reports no quantitative results.
- **Relation:** It shows industry demand for exactly our task. It is short and has no data or numbers,
  so cite it for motivation only.

### A8. Ericsson no-fault-found failures (ESEC/FSE 2021)

- **Ref.** M. H. U. Rehman, P. C. Rigby, "Quantifying no-fault-found test failures to prioritize
  inspection of flaky tests at Ericsson," in *Proc. 29th ACM Joint European Software Engineering Conf.
  and Symp. on the Foundations of Software Engineering (ESEC/FSE)*, 2021, pp. 1371–1380.
  doi:10.1145/3468264.3473930.
- **Verified at:** https://api.crossref.org/works/10.1145/3468264.3473930 (abstract via Semantic Scholar
  https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3468264.3473930)
- **Task:** triage via per-test failure rates. Test-level statistics are used to prioritise failures for
  rerun or investigation.
- **Summary:** The study covers 9.9 million runs of 10k tests across four Ericsson releases. It computes
  each test's no-fault-found failure rate, then uses a binomial test against the prior release's stable
  rate to flag statistically unstable tests for rerun or inspection. Ericsson testers adopted the method.
- **Relation:** This is a history-based triage baseline. It is close to MDFlaker's history factor, and
  it is what our strict-history rule restricts to *past* releases only.

### A9. Apple flakiness scores (ICSE-SEIP 2020)

- **Ref.** E. Kowalczyk, K. Nair, Z. Gao, L. Silberstein, T. Long, A. Memon, "Modeling and ranking flaky
  tests at Apple," in *Proc. ACM/IEEE 42nd Int. Conf. on Software Engineering: Software Engineering in
  Practice (ICSE-SEIP)*, 2020, pp. 110–119. doi:10.1145/3377813.3381370.
- **Verified at:** https://api.crossref.org/works/10.1145/3377813.3381370 (abstract via OpenAlex)
- **Task:** test-level scoring from execution history, used to triage in CI.
- **Summary:** Flakiness is modelled as a rankable score from result entropy and temporal *flipRate*,
  aggregated over time. It is deployed on two large Apple services. The authors report near-perfect
  ranking accuracy and a 44% reduction in flakiness with less than 1% loss in fault detection.
- **Relation:** Flip-rate history features are the industrial version of MDFlaker's history factor. This
  is a useful contrast for our finding that history inflates scores unless strictly time-ordered.

---

## Part B. Systemic and co-occurring flaky failures

### B1. Systemic flakiness (EASE 2025)

- **Ref.** O. Parry, G. M. Kapfhammer, M. Hilton, P. McMinn, "Systemic flakiness: An empirical analysis
  of co-occurring flaky test failures," in *Proc. 29th Int. Conf. on Evaluation and Assessment in
  Software Engineering (EASE)*, 2025, pp. 476–487. doi:10.1145/3756681.3756945.
- **Verified at:** https://api.crossref.org/works/10.1145/3756681.3756945 (abstract via OpenAlex)
- **Task:** failure-level empirical study (clusters of co-occurring flaky failures).
- **Summary:** They use an existing dataset of 10,000 test-suite runs of 24 Java projects, with 810 flaky
  tests. Flaky failures often occur in clusters that share a root cause ("systemic flakiness"). A
  mixed-method analysis finds this significant and widespread.
- **Relation:** This supports a co-failure feature: how many other tests failed in the same run. It also
  warns that failures in one run are not independent, so evaluation splits should keep a run's failures
  together. We should check whether our splits do this. The dataset appears to be FlakeFlagger's
  10,000-rerun data [R7]; **UNVERIFIED**, inferred from the matching numbers only.

### B2. Intermittent failures in embedded systems (ISSTA 2020)

- **Ref.** P. E. Strandberg, T. J. Ostrand, E. J. Weyuker, W. Afzal, D. Sundmark, "Intermittently failing
  tests in the embedded systems domain," in *Proc. 29th ACM SIGSOFT Int. Symp. on Software Testing and
  Analysis (ISSTA)*, 2020, pp. 337–348. doi:10.1145/3395363.3397359.
- **Verified at:** https://api.crossref.org/works/10.1145/3395363.3397359 (abstract via OpenAlex)
- **Task:** test-level labelling and root causes at system-test level.
- **Summary:** In more than half a million verdicts from an industrial embedded system, 1–3% of test cases
  were intermittently failing, identified with a new intermittence metric. The authors identify nine
  factors associated with intermittence. Fixing a consistently failing test removed more failures in
  *other* tests than fixing an intermittent one.
- **Relation:** The cross-test effect relates to systemic failures (B1). The intermittence metric is an
  alternative to rerun labels.

---

## Part C. Rerun-based labelling and rerun practice

### C1. 4,000 reruns per suite (ISSRE 2020)

- **Ref.** W. Lam, S. Winter, A. Astorga, V. Stodden, D. Marinov, "Understanding reproducibility and
  characteristics of flaky tests through test reruns in Java projects," in *Proc. IEEE 31st Int. Symp. on
  Software Reliability Engineering (ISSRE)*, 2020, pp. 403–413. doi:10.1109/ISSRE5003.2020.00045.
- **Verified at:** https://api.crossref.org/works/10.1109/issre5003.2020.00045 (abstract via OpenAlex)
- **Summary:** Each Maven Surefire suite was re-executed 4,000 times, and a test was labelled flaky if it
  both passed and failed. This gave 107 flaky tests. Many tests previously called non-order-dependent do
  depend on order, with failure rates that differ greatly by order.
- **Relation:** This is the main reference for justifying, and caveating, our 30-rerun label. Some flaky
  failures have low reproduction rates, so 30 reruns give "not observed flaky", not "non-flaky".

### C2. Restarted and flaky builds on Travis CI (MSR 2020)

- **Ref.** T. Durieux, C. Le Goues, M. Hilton, R. Abreu, "Empirical study of restarted and flaky builds on
  Travis CI," in *Proc. 17th Int. Conf. on Mining Software Repositories (MSR)*, 2020, pp. 254–264.
  doi:10.1145/3379597.3387460.
- **Verified at:** https://api.crossref.org/works/10.1145/3379597.3387460 (abstract via Semantic Scholar)
- **Summary:** Developers restart at least 1.72% of builds (56,522 restarted builds). Restarts are mostly
  of builds that failed because of tests, network problems or Travis limits such as timeouts. In 54.42%
  of cases the restart happens within an hour, and restarts triple median pull-request merge time (16h
  to 48h).
- **Relation:** This quantifies the cost of rerun-based triage that a failure-level classifier aims to
  cut.

### C3. Cost of flaky tests in industrial CI (ICST 2024)

- **Ref.** F. Leinen, D. Elsner, A. Pretschner, A. Stahlbauer, M. Sailer, E. Jürgens, "Cost of flaky tests
  in continuous integration: An industrial case study," in *Proc. IEEE Conf. on Software Testing,
  Verification and Validation (ICST)*, 2024, pp. 329–340. doi:10.1109/ICST60714.2024.00037.
- **Verified at:** https://api.crossref.org/works/10.1109/icst60714.2024.00037 (abstract via OpenAlex)
- **Summary:** The authors build a cost model and apply it to five years of history of a project with
  about 30 developers and about 1M SLoC. Flaky tests cost at least 2.5% of productive developer time,
  including 1.1% spent investigating potentially flaky failures. An automatic rerun costs about $0.0002
  (0.02 cents). A manual investigation costs about $5.
- **Relation:** This matters for our framing. In this setting reruns are cheap and *investigation* is the
  cost, so a classifier's value lies in triage and explanation (our SHAP output), not in saving machine
  time.

### C4. Detected and undetected flaky failures in CI (TSE 2026), content UNVERIFIED

- **Ref.** F. Leinen, M. Gruber, S. S. Erdogan, A. Stahlbauer, A. Pretschner, "An empirical study of
  detected and undetected flaky test failures in real-world CI pipelines," *IEEE Transactions on Software
  Engineering*, 2026, pp. 1–21 (early access). doi:10.1109/TSE.2026.3729363.
- **Verified at:** https://api.crossref.org/works/10.1109/tse.2026.3729363 (bibliographic record only).
- **Content: UNVERIFIED.** No abstract was available through Crossref, Semantic Scholar or IEEE Xplore
  when checked. Read the paper before citing it for any claim. Judging by the title, it is directly about
  flaky *failures* in CI and whether reruns catch them, which makes it likely essential for §3 and for
  label validity.

### C5. Flaky tests in Python (ICST 2021)

- **Ref.** M. Gruber, S. Lukasczyk, F. Krois, G. Fraser, "An empirical study of flaky tests in Python," in
  *Proc. 14th IEEE Conf. on Software Testing, Verification and Validation (ICST)*, 2021, pp. 148–158.
  doi:10.1109/ICST49551.2021.00026.
- **Verified at:** https://api.crossref.org/works/10.1109/icst49551.2021.00026 (abstract via OpenAlex)
- **Task:** test-level, rerun-based labelling in Python.
- **Summary:** The study reruns 876,186 tests from 22,352 PyPI projects and finds 7,571 flaky tests. Of
  these, 59% are order-dependent, 28% come from test-infrastructure problems and most of the rest from
  network and randomness APIs. The authors estimate that 95% confidence that a passing test is not flaky
  needs 170 reruns on average.
- **Relation:** The 170-rerun estimate is the strongest published caveat on our 30-rerun labels. Our
  negative labels are "not observed flaky after 30 reruns". The paper is also the Python precedent for the
  team's earlier pytest pipeline.

---

## Part D. Possibly relevant, but not peer-reviewed or not checked

- W. Ge, C. Zhang, "Understanding and detecting flaky builds in GitHub Actions," **arXiv preprint**
  arXiv:2602.02307, 2026 (https://arxiv.org/abs/2602.02307). It covers 1,960 Java projects. 3.2% of builds
  are rerun and 67.73% of those reruns are flaky. The authors propose a job-level ML flaky-failure
  detector with F1 up to 20.3% above a baseline. **Not peer-reviewed as far as we could find**: Crossref
  has no record. Cite it as a preprint, or not at all.
- A. Memon et al., "Taming Google-scale continuous testing," ICSE-SEIP 2017, pp. 233–242,
  doi:10.1109/ICSE-SEIP.2017.16. The record is verified on Crossref, but its relevance to flaky failures
  was not checked.
- A. Berndt, T. Bach, S. Baltes, "Do test and environmental complexity increase flakiness? An empirical
  study of SAP HANA," ESEM 2024, pp. 572–581, doi:10.1145/3674805.3695407. Crossref verified, abstract not
  read.
- An earlier arXiv version of A4, "Discerning legitimate failures from false alerts: A study of Chromium's
  continuous integration" (arXiv:2111.03382), reportedly introduced a failure classifier called "Fair".
  **UNVERIFIED**: we found no peer-reviewed version.

---

## Part E. Fixes for DRAFT.md's [CITE NEEDED] references

All of these were checked against Crossref (`https://api.crossref.org/works/<DOI>`) unless another URL is
given. Suggested replacement text follows each one.

- **R2.** Verified: https://api.crossref.org/works/10.1109/apsec53868.2021.00041
  > A. Ahmad, F. Gomes de Oliveira Neto, Z. Shi, K. Sandahl, O. Leifler, "A multi-factor approach for flaky
  > test detection and automated root cause analysis," in *Proc. 28th Asia-Pacific Software Engineering
  > Conference (APSEC)*, 2021, pp. 338–348. doi:10.1109/APSEC53868.2021.00041.

  Note that the second author's surname is "Gomes de Oliveira Neto", not "Gomes".
- **R8.** Verified: https://api.crossref.org/works/10.1109/icst.2019.00038
  > W. Lam, R. Oei, A. Shi, D. Marinov, T. Xie, "iDFlakies: A framework for detecting and partially
  > classifying flaky tests," in *Proc. 12th IEEE Conf. on Software Testing, Validation and Verification
  > (ICST)*, 2019, pp. 312–322. doi:10.1109/ICST.2019.00038.

  Crossref gives the 2019 proceedings title as "...Testing, Validation and Verification", in that order.
- **R9.** Verified: https://api.crossref.org/works/10.1109/tse.2022.3201209
  > S. Fatima, T. A. Ghaleb, L. Briand, "Flakify: A black-box, language model-based predictor for flaky
  > tests," *IEEE Trans. Software Engineering*, vol. 49, no. 4, pp. 1912–1927, 2023.
  > doi:10.1109/TSE.2022.3201209.

  The year changes from 2022 to 2023 (issue date April 2023; the DOI dates from early access in 2022).
- **R14.** Verified: https://api.crossref.org/works/10.1142/s0218194024500232
  > W. Zhang, W. Wang, R. Zhao, "Flaky test detection based on adaptive latest position execution for
  > concurrent Android applications," *Int. J. Software Engineering and Knowledge Engineering*, vol. 34,
  > no. 8, pp. 1313–1338, 2024. doi:10.1142/S0218194024500232.
- **R15.** Verified: https://api.crossref.org/works/10.1016/j.scico.2026.103462
  > N. Hashemi, A. Tahir, S. Rasheed, A. Shi, R. Blagojevic, "JS-TOD: Detecting order-dependent flaky
  > tests in Jest," *Science of Computer Programming*, vol. 252, Art. 103462, 2026.
  > doi:10.1016/j.scico.2026.103462.

  The same authors have a related ICST 2025 paper, "Detecting and evaluating order-dependent flaky tests
  in JavaScript," pp. 13–24, doi:10.1109/ICST62969.2025.10988962.
- **R16.** Verified: https://api.crossref.org/works/10.13052/jwe1540-9589.1927 for the authors. Volume,
  issue and pages come from the publisher page
  https://journals.riverpublishers.com/index.php/JWE/article/view/3361 ("Vol 19 Iss 2";
  citation_firstpage 267, citation_lastpage 296).
  > J. Morán, C. Augusto, A. Bertolino, C. De La Riva, J. Tuya, "FlakyLoc: Flakiness localization for
  > reliable test suites in web applications," *Journal of Web Engineering*, vol. 19, no. 2,
  > pp. 267–296, 2020. doi:10.13052/jwe1540-9589.1927.
- **R17.** Verified: https://api.crossref.org/works/10.3390/computers15060372
  > P. Dai, X. Ma, Y. Zhao, Y. Gong, "Heterogeneous graph transformer with multi-view representation
  > learning for flaky test detection," *Computers*, vol. 15, no. 6, Art. 372, 2026.
  > doi:10.3390/computers15060372.

  The full title does not contain the name "HgtFlaky". **UNVERIFIED** whether the paper uses that name
  for its tool; check before using the name in the text.
- **R18.** Verified: https://api.crossref.org/works/10.1007/978-3-032-15784-3_8 . Volume 1801 comes from
  the Springer page https://link.springer.com/chapter/10.1007/978-3-032-15784-3_8 .
  > M. ElGazzar, E. Hossny, F. A. Omara, "A machine learning-based detection of test automation
  > flakiness," in *Intelligent Systems, Blockchain, and Communication Technologies*, Lecture Notes in
  > Networks and Systems, vol. 1801, Springer, Cham, 2026, pp. 91–102.
  > doi:10.1007/978-3-032-15784-3_8.

  **UNVERIFIED:** the book's editors and conference name, which Crossref does not list.
- **R19.** Verified: https://api.crossref.org/works/10.1109/access.2025.3553626
  > A. Ahmad, X. Sun, M. R. Naeem, Y. Javed, M. Akour, K. Sandahl, "Understanding flaky tests through
  > linguistic diversity: A cross-language and comparative machine learning study," *IEEE Access*,
  > vol. 13, pp. 54561–54584, 2025. doi:10.1109/ACCESS.2025.3553626.
- **R20.** Verified: https://api.crossref.org/works/10.1109/access.2025.3639645
  > A. Ahmad, X. Sun, "Base, instruct, and fine-tune: Evaluating LLMs for cross-language flaky test
  > detection," *IEEE Access*, vol. 13, pp. 205254–205277, 2025. doi:10.1109/ACCESS.2025.3639645.

---

## Suggested use in §3

A new subsection, "3.5 Failure-level flaky classification", could cite the following:

- A4 (Haben et al.) for *why* failure-level prediction matters;
- A1, A2, A5, A6 and A7 for prior failure-level methods, grouped as:
  - coverage (DeFlaker);
  - telemetry (Mozilla);
  - failure text or de-duplication (Alshammari et al.; An et al.; brown builds, A3);
  - industrial ML (Presubmit Rescue);
- A8 and A9 for history-based triage;
- B1 for co-occurring failures;
- C1–C4 in §3.1 or §5.3 for rerun labelling and its cost and limits.

None of these evaluates failure-level classification with a strict-history (time-ordered) split *and*
project-separated transfer on open data. That is the gap we could claim. **This is a claim from abstracts
only.** It must be re-checked against the full texts of A2, A3, A5 and C4 before it goes into the paper.
