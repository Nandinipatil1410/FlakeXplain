# Front matter for *Science of Computer Programming* (Elsevier)

**Draft, 20 October 2026. Not for submission.** Companion to `paper/DRAFT.md` (v2). Every number
below is copied from DRAFT.md or the v0.8 reports it cites. Items marked **[TEAM]** need a team
decision; items that depend on the v0.9 outcome point to `paper/V09_OUTCOME_TEXT.md`. Check all
limits against SCP's current Guide for Authors before submission (DRAFT.md, Team decisions, item 1).

---

## Highlights

Elsevier limit: 3–5 bullet points, at most 85 characters each, including spaces.

- MDFlaker's released data contain a label proxy and test and build shortcuts
- New dataset: 1,659 CI failures from 8 Python projects, labelled by 30 reruns
- Post hoc, on unseen tests: MCC 0.469 vs −0.160 for our MDFlaker reimplementation
- Margin over a per-project base-rate predictor is not significant
- Cross-project gain fails strict history; static test-code features never help

After v0.9 (see `V09_OUTCOME_TEXT.md`), replace the fourth highlight:
- (a) "A frozen prospective confirmation on {n_P} later failures met its rule"
- (b), (c) "A frozen prospective confirmation did not confirm the post-hoc gain"
- (d) "A frozen prospective confirmation lacked the sample to test the gain"

Then keep the base-rate caveat by merging it into the third highlight if needed, for example
"Post hoc, unseen tests: MCC 0.469 vs −0.160; not clearly above base rates" (73 characters).

## Keywords

Elsevier asks for 1–7 keywords.

Flaky tests; Continuous integration; Failure triage; Test reruns; Machine learning; Empirical evaluation

---

## CRediT authorship contribution statement

**[TEAM]** Fill in the roles for each author from the 14 CRediT roles and delete the unused ones.
Author order and affiliations are still open (DRAFT.md, Team decisions). If the project guide is
added as an author, add a row for them (typically Supervision; Writing – review & editing).

CRediT roles: Conceptualization; Data curation; Formal analysis; Funding acquisition;
Investigation; Methodology; Project administration; Resources; Software; Supervision; Validation;
Visualization; Writing – original draft; Writing – review & editing.

> **Nandini Patil:** [roles]. **Bhumika Mane:** [roles]. **Trusha Kulkarni:** [roles].
> **Pranavi Baad:** [roles].

## Declaration of competing interest

**[TEAM] To be confirmed by every author** (Elsevier's declaration tool can generate the official
form).

> The authors declare that they have no known competing financial interests or personal
> relationships that could have appeared to influence the work reported in this paper.

## Funding

**[TEAM] To confirm.** If there is no funding:

> This research did not receive any specific grant from funding agencies in the public, commercial,
> or not-for-profit sectors.

## Data availability

Matches DRAFT.md, Team decisions, item 8 (a proposal; **[TEAM] confirm with the guide** before
submission, and replace the bracketed parts with the DOI and licence).

> The derived data for the new dataset (candidate list, features, labels and rerun summaries) and
> the protocols, amendments, analysis scripts and result files will be archived with a DOI
> [Zenodo DOI] under an open licence [licence] at submission. Raw CI logs are not redistributed;
> they belong to the projects' GitHub Actions runs, and the archived run and job IDs let others
> re-download them while GitHub retains them. MDFlaker's released dataset, used in Section 4, is
> available from its authors' repository [R1].

## Declaration of generative AI and AI-assisted technologies in the writing process

Elsevier's required wording, filled in. **[TEAM] Confirm** that every author has reviewed the text,
and decide whether the Methods should also mention AI-assisted code or analysis (Elsevier's
declaration covers the writing process; use of AI tools in the research itself is described in the
Methods).

> During the preparation of this work the authors used Claude (Anthropic) in order to draft and edit
> the manuscript text. After using this tool, the authors reviewed and edited the content as needed
> and take full responsibility for the content of the published article.

---

## Abstract (≤ 250 words)

Shortened from DRAFT.md §1 (347 words). Same numbers and caveats; the spaCy proxy percentages and
the per-project median are left to the body, as is the Superset source problem. 225 words before
v0.9 (214 without the final sentence). After v0.9, replace the final sentence with the matching
short variant in `V09_OUTCOME_TEXT.md` §1 (22–31 words, so at most 245 in total) and recount.

> MDFlaker (Software Impacts, 2025) predicts whether a failed continuous integration (CI) test
> execution is flaky, that is, would pass on a rerun, using five factors and a rule plus
> k-nearest-neighbour classifier. We show that MDFlaker's released data cannot support a fair
> improvement claim: whether a traceback was stored is close to a label proxy, and failures from the same tests and builds make within-project evaluations
> optimistic. We therefore collect 1,659 failed pytest executions from the GitHub Actions logs of 8
> Python projects, each rerun 30 times on the code CI tested; 1,292 receive labels (409 flaky, 883
> not flaky). We add 17 failure-evidence features to MDFlaker's factors and train an Extra Trees
> model (ET-BF). Under a success rule frozen before labelling, ET-BF beats the best MDFlaker-style
> baseline within project (MCC 0.755 vs 0.239) and across projects (0.357 vs −0.014). Post-hoc
> checks show that these numbers are inflated by project base rates, repeated tests and a history
> feature that counts concurrent jobs. With strict history and only on tests unseen in training,
> ET-BF reaches MCC 0.469 against −0.160 for our MDFlaker reimplementation (+0.63, 95% interval
> [0.14, 0.94]), but its margin over a per-project base-rate predictor is not significant (+0.32
> [−0.29, 0.61]). The cross-project gain does not survive strict history, and static test-code
> features never help. A frozen prospective confirmation will be reported after 24 November 2026.
