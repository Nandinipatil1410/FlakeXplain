# Pre-written v0.9 outcome text for `paper/DRAFT.md`

**Written 20 October 2026, after the v0.9 freeze (14:48:22 UTC) and before any v0.9 log was
downloaded.** No v0.9 number is known. Every `{placeholder}` below is filled from the v0.9 results
files at collection; every other number is copied from `paper/DRAFT.md` (v2) or the v0.8 reports it
cites. Writing all four versions now means the outcome cannot shape the wording.

How to use this file:
1. Decide the outcome mechanically with the table in Section 0. Do not choose wording first.
2. Replace the three DRAFT.md passages (abstract ending, §11 results, §12 conclusion) with the text
   for that outcome, fill the placeholders, and delete any bracketed `[If …]` sentence whose
   condition does not hold. Do not add claims that are not here without a new team discussion.
3. Update the smaller passages listed in Section 5.
4. Commit this file unchanged alongside the filled DRAFT.md, so reviewers can compare the two.

---

## 0. Which outcome applies

The rule is v0.9 `PROTOCOL.md` §7 (frozen; `protocol.json` → `rule`). C\* is the comparator
(MDF-paper-int, MDF-paper-float, KNN8-int, KNN8-float or the project prior) with the highest MCC on
the primary set P. Δ = MCC(ET-BF) − MCC(C\*) on P, with its 95% project-bootstrap interval
[{ci_lo}, {ci_hi}] (2,000 resamples, seed 20261020, predictions fixed).

| Check, in this order | Outcome |
|---|---|
| P has < 40 flaky, or < 40 not-flaky failures, or fewer than 4 projects with failures in P (after the single allowed extension to T2, if it was triggered) | **(d)** minimum sample not met, descriptive only |
| Δ ≥ +0.10 **and** {ci_lo} > 0 | **(a)** confirmed |
| Δ > 0 but not (a): Δ < +0.10, or {ci_lo} ≤ 0, or both | **(b)** not confirmed, ET-BF ahead |
| Δ ≤ 0 | **(c)** not confirmed, ET-BF not ahead |

Placeholders used throughout:

| Placeholder | Meaning |
|---|---|
| `{window_end}` | "24 November 2026" (T1) or "22 December 2026" (T2, if the label-blind extension was triggered) |
| `{n_cand}`, `{n_lab}`, `{n_unlab}` | v0.9 candidates, labelled, unlabelled (all of A) |
| `{n_A}`, `{flaky_A}` | labelled failures in A and how many are flaky (`{n_A}` = `{n_lab}`) |
| `{n_P}`, `{flaky_P}`, `{notflaky_P}`, `{proj_P}` | size of P, flaky and not-flaky counts, projects with failures in P |
| `{mcc_etbf}`, `{cstar}`, `{mcc_cstar}` | ET-BF MCC on P, name of C\*, C\* MCC on P |
| `{mcc_mdf}` | MCC on P of MDF-paper-int (our reimplementation of MDFlaker), if C\* is another arm |
| `{mcc_prior}` | MCC on P of the project prior |
| `{delta}`, `{ci_lo}`, `{ci_hi}` | Δ on P and its interval |
| `{delta_A}`, `{ci_lo_A}`, `{ci_hi_A}`, `{cstar_A}` | the same difference on A (supporting) and the best comparator on A |
| `{pp_median}`, `{pp_wins}`, `{pp_ties}`, `{pp_losses}`, `{pp_n}` | ET-BF per-project median MCC on P; projects where it beats, ties or loses to C\*; projects with both classes in P |
| `{pp_small}` | number of projects whose P subset has fewer than 5 flaky failures |
| `{f1_etbf}`, `{prec_etbf}`, `{rec_etbf}` | ET-BF F1, precision and recall on P |
| `{mcc_etbf_A}`, `{mcc_cstar_A}` | ET-BF and `{cstar_A}` MCC on A |
| `{met}` | "yes" or "no" for the rule on P; "n/a (descriptive)" in outcome (d) |
| `{mcc_lopo}` | ET-BF leave-one-project-out MCC on v0.9 (descriptive) |
| `{collection_date}`, `{weeks}` | date the v0.9 logs were downloaded; weeks between the end of the v0.8 window and `{window_end}` |
| `{n_P_cand_T1}` | label-blind count of primary-set candidates at T1 (only if the window was extended) |
| `{amendments_or_none}` | list of dated label-blind amendments, or "none" |
| `{tab_v09_unlabelled}`, `{shortfall_reason}`, `{outcome_text_commit}` | table number, main reason for a short sample, and the commit hash of this file |

Round MCC values to 3 decimals and differences and interval bounds to 2, as in DRAFT.md §8.1.

---

## 1. Abstract: replacement for the final sentence

In DRAFT.md §1, replace the last sentence ("A prospective confirmation on failures occurring after
20 October 2026 is frozen and will be reported after collection on 24 November 2026.") with the text
for the outcome. Everything before it stays, including "Post-hoc checks show…" and the base-rate
sentence. A shorter variant for the ≤ 250-word abstract in `FRONT_MATTER.md` follows each one.

### (a) Confirmed

> Because this finding was identified post hoc, we tested it in a confirmation study frozen in
> advance, on {n_P} failures of new tests occurring between 20 October and {window_end} in the same
> 8 projects. ET-BF, trained only on the original data, reached MCC {mcc_etbf} against {mcc_cstar}
> for the best comparator ({cstar}; difference {delta} [{ci_lo}, {ci_hi}]), meeting the frozen rule.
> The confirmation covers new failures in projects seen in training, measured by pooled MCC, which
> partly rewards differences in base rates between projects.

Short variant:

> A frozen confirmation on {n_P} later failures of new tests met its rule: ET-BF reached MCC
> {mcc_etbf} against {mcc_cstar} for the best comparator ({delta} [{ci_lo}, {ci_hi}]), in seen
> projects only.

### (b) Not confirmed, ET-BF still ahead

> Because this finding was identified post hoc, we tested it in a confirmation study frozen in
> advance, on {n_P} failures of new tests occurring between 20 October and {window_end} in the same
> 8 projects. ET-BF reached MCC {mcc_etbf} against {mcc_cstar} for the best comparator ({cstar};
> difference {delta} [{ci_lo}, {ci_hi}]). This does not meet the frozen rule (a difference of at
> least +0.10 with an interval above 0), so the within-project improvement is **not confirmed**.

Short variant:

> A confirmation study frozen in advance, on {n_P} later failures of new tests, did **not confirm**
> it: ET-BF led the best comparator by {delta} [{ci_lo}, {ci_hi}], short of the frozen rule.

### (c) Not confirmed, ET-BF not ahead

> Because this finding was identified post hoc, we tested it in a confirmation study frozen in
> advance, on {n_P} failures of new tests occurring between 20 October and {window_end} in the same
> 8 projects. There, ET-BF reached MCC {mcc_etbf} against {mcc_cstar} for the best comparator
> ({cstar}; difference {delta} [{ci_lo}, {ci_hi}]), so the within-project improvement is **not
> confirmed** and did not carry over to new failures.

Short variant:

> A confirmation study frozen in advance, on {n_P} later failures of new tests, did **not confirm**
> it: ET-BF did not beat the best comparator ({delta} [{ci_lo}, {ci_hi}]).

### (d) Minimum sample not met

> Because this finding was identified post hoc, we froze a confirmation study on failures occurring
> between 20 October and {window_end}. Too few failures of new tests were labelled ({flaky_P}
> flaky and {notflaky_P} not flaky in {proj_P} projects; the frozen minimum was 40, 40 and 4), so
> its results are descriptive only and the within-project finding remains **untested**.

Short variant:

> A frozen confirmation study collected too few new-test failures ({flaky_P} flaky, {notflaky_P}
> not flaky) to test it, so the finding remains **untested**.

---

## 2. §11 Confirmation study: replacement for the heading, status and results

In all four outcomes:
- change the heading from "Confirmation study (v0.9) — planned, results TBD" to
  **"Confirmation study (v0.9)"**;
- keep the **Status**, **Purpose**, **Design**, **Success rule** and **A caution known in advance**
  paragraphs exactly as they are, except the sentence "No v0.9 data have been collected or looked
  at.", which becomes: "This section's outcome text was written before any v0.9 data were collected
  (`paper/V09_OUTCOME_TEXT.md`, commit {outcome_text_commit})."
- if the window was extended, add to Design: "At T1 there were {n_P_cand_T1} primary-set candidates
  (fewer than 300, counted label-blind), so the window was extended once to T2 = 22 December 2026."
- replace "**Results: TBD after collection on 24 November 2026.**" and the TBD table with the text
  below, and fill the table (A rows: the comparator is the best one on A, `{cstar_A}`).

Common opening paragraph (all outcomes):

> **Collection and labels.** Logs were downloaded once, on {collection_date}, for workflow runs created
> between 20 October 2026 14:48 UTC and {window_end}. Of {n_cand} candidates, {n_lab} received labels
> and {n_unlab} were unlabelled; reasons are listed in Table {tab_v09_unlabelled}, as for v0.8. P has
> {n_P} failures ({flaky_P} flaky) from {proj_P} projects; A has {n_A} ({flaky_A} flaky). No feature,
> model, threshold or rule was changed after the freeze; the amendments made were {amendments_or_none}.

| | n | Flaky | ET-BF MCC | C\* | C\* MCC | Δ [95% CI] | Met |
|---|---:|---:|---:|---|---:|---|---|
| Primary set P | {n_P} | {flaky_P} | {mcc_etbf} | {cstar} | {mcc_cstar} | {delta} [{ci_lo}, {ci_hi}] | {met} |
| All A (supporting) | {n_A} | {flaky_A} | {mcc_etbf_A} | {cstar_A} | {mcc_cstar_A} | {delta_A} [{ci_lo_A}, {ci_hi_A}] | — |

Add a per-project table for P (columns as in the §8.1 per-project table: n, flaky, MDFlaker, KNN8,
project prior, ET-BF) and the descriptive leave-one-project-out and ET-BFC − ET-BF results, as
required by v0.9 PROTOCOL §6–7.

### (a) Confirmed

> **Outcome: confirmed.** On P, ET-BF reached MCC {mcc_etbf} (F1 {f1_etbf}, precision {prec_etbf},
> recall {rec_etbf}). The best comparator was {cstar} with MCC {mcc_cstar}, so the difference is
> {delta} [{ci_lo}, {ci_hi}]: at least +0.10 with an interval above 0, as the frozen rule requires.
> Our reimplementation of MDFlaker (MDF-paper-int) scored {mcc_mdf}, and the project prior
> {mcc_prior}. On all v0.9 failures (A), the supporting difference is {delta_A} [{ci_lo_A},
> {ci_hi_A}].
>
> What this confirmation does and does not show:
> - **The hypothesis came from post-hoc analysis.** The unseen-tests subset and the strict history
>   feature were defined after the v0.8 frozen results were known (Sections 7.2, 7.5 and 10). v0.9
>   tests that hypothesis on new data under a rule fixed in advance; it does not make the v0.8
>   numbers in Section 8.1 any less post hoc.
> - **Pooled MCC still partly rewards base-rate differences.** As Section 8.1 explains, pooled MCC
>   rewards separating projects with different flaky rates as well as discriminating within a
>   project. The project prior was one of the comparators, so ET-BF exceeds a base-rate predictor
>   on P, which v0.8 could not show. That comparator only partly removes the concern, however.
>   Per project, ET-BF's median MCC on P is {pp_median}; it beats C\* in {pp_wins} of {pp_n}
>   projects, ties in {pp_ties} and loses in {pp_losses}, and {pp_small} projects have fewer than 5
>   flaky failures in P. [If the per-project median is near 0 or ET-BF loses in at least half of the
>   projects: "The pooled confirmation therefore rests largely on differences between projects, and
>   we do not read it as evidence of within-project discrimination."]
> - **Scope.** The confirmation covers failures of tests not seen in training, in the 8 projects used
>   for training, about {weeks} weeks after the training window. It says nothing about unseen
>   projects: leave-one-project-out was descriptive only in v0.9 (MCC {mcc_lopo}), and the
>   cross-project gain did not survive strict history in v0.8 (Section 8.5).
> - **Wide intervals.** With 8 projects, the bootstrap interval is wide and its bounds vary by a few
>   hundredths between draws (Section 7.3). [If {ci_lo} < 0.05: "The lower bound is close to 0, so
>   the confirmation is narrow."]

### (b) Not confirmed, ET-BF still ahead

> **Outcome: not confirmed.** On P, ET-BF reached MCC {mcc_etbf} (F1 {f1_etbf}, precision
> {prec_etbf}, recall {rec_etbf}). The best comparator was {cstar} with MCC {mcc_cstar}, so the
> difference is {delta} [{ci_lo}, {ci_hi}]. [Use the matching sentence: "The difference is below the
> frozen +0.10 threshold." / "The difference meets the +0.10 threshold, but its interval includes
> 0." / "The difference is below +0.10 and its interval includes 0."] The frozen rule is therefore
> not met, and we report the within-project result of Section 8.1 as **not confirmed**. Our
> reimplementation of MDFlaker (MDF-paper-int) scored {mcc_mdf}, and the project prior {mcc_prior}.
> On all v0.9 failures (A), the supporting difference is {delta_A} [{ci_lo_A}, {ci_hi_A}].
>
> ET-BF remained ahead of every comparator on P, which is consistent with a real but smaller or less
> certain advantage than v0.8 suggested. We do not claim that advantage: the rule was fixed in
> advance precisely so that a positive but inconclusive result is not reinterpreted afterwards.
> Per project, ET-BF's median MCC on P is {pp_median}; it beats C\* in {pp_wins} of {pp_n} projects,
> ties in {pp_ties} and loses in {pp_losses}. [If {cstar} is the project prior: "The best comparator
> was the per-project base rate, which matches the v0.8 finding that ET-BF's margin over that
> predictor was not significant (Section 8.1)."] The most likely explanations, which we cannot
> separate with these data, are that the post-hoc v0.8 subset favoured ET-BF by chance, that pooled
> MCC in v0.8 partly reflected base-rate differences between projects, and that the projects' flaky
> rates or failure types changed between the two windows. {If available, one sentence on the v0.9
> per-project flaky rates versus Section 5.4.}

### (c) Not confirmed, ET-BF not ahead

> **Outcome: not confirmed.** On P, ET-BF reached MCC {mcc_etbf} (F1 {f1_etbf}, precision
> {prec_etbf}, recall {rec_etbf}). The best comparator was {cstar} with MCC {mcc_cstar}, so ET-BF did
> not beat it: the difference is {delta} [{ci_lo}, {ci_hi}]. Our reimplementation of MDFlaker
> (MDF-paper-int) scored {mcc_mdf}, and the project prior {mcc_prior}. On all v0.9 failures (A), the
> supporting difference is {delta_A} [{ci_lo_A}, {ci_hi_A}]. We therefore report the within-project
> result of Section 8.1 as **not confirmed**: on failures that occurred after the freeze, adding
> failure-evidence features to MDFlaker's factors did not improve on the best simple comparator.
>
> Per project, ET-BF's median MCC on P is {pp_median}; it beats C\* in {pp_wins} of {pp_n} projects,
> ties in {pp_ties} and loses in {pp_losses}. [If {cstar} is the project prior: "The best comparator
> was the per-project base rate, so on new failures ET-BF added nothing beyond each project's flaky
> rate. This is consistent with the v0.8 finding that its margin over that predictor was not
> significant (Section 8.1)."] We read this as evidence that the v0.8 post-hoc result was at least
> partly an artefact of how the subset and the strict feature were chosen after the frozen results
> were known, of pooled MCC rewarding base-rate differences, or of a change in the projects' failures
> between the two windows; these data do not let us separate the three. The frozen v0.8 results
> (Section 8.2) stand as reported, with the qualifications of Section 8.3.

### (d) Minimum sample not met

> **Outcome: minimum sample not met; descriptive only.** P has {flaky_P} flaky and {notflaky_P}
> not-flaky failures from {proj_P} projects, below the frozen minimum of 40 flaky, 40 not flaky and
> 4 projects [if extended: ", even after the single allowed extension of the window to 22 December
> 2026"]. Following the protocol, we make no confirmation claim either way, and the within-project
> result of Section 8.1 remains a post-hoc finding that has **not been tested** prospectively.
>
> For completeness, and without inference, on P ET-BF reached MCC {mcc_etbf} against {mcc_cstar} for
> the best comparator ({cstar}); the difference is {delta} [{ci_lo}, {ci_hi}]. With this few
> failures these values are unstable (Section 10, conclusion validity) and should not be read as
> support for or against the finding. The shortfall came mainly from {shortfall_reason} (see the
> unlabelled-reasons table). A larger prospective study, with a longer window or more projects, is
> needed; any such study would need its own frozen protocol.

---

## 3. §12 Conclusion: replacement for the last sentence

In DRAFT.md §12, keep everything up to "…and what else failed alongside it." and replace "Whether
the within-project result holds on future failures is the question of the frozen v0.9 study, to be
reported after 24 November 2026." with the text for the outcome.

### (a) Confirmed

> Because the within-project result came from post-hoc analysis, we tested it in a confirmation
> study frozen in advance, on {n_P} later failures of new tests in the same 8 projects. It met its
> rule: ET-BF reached MCC {mcc_etbf} against {mcc_cstar} for the best comparator, {cstar} ({delta}
> [{ci_lo}, {ci_hi}]). We therefore consider the within-project improvement confirmed for projects
> seen in training, with two limits: pooled MCC still partly rewards differences between projects'
> flaky rates (per-project median {pp_median}), and nothing here supports a claim about unseen
> projects. The results suggest that a team which has labelled some of its own CI failures may
> benefit from failure-evidence features when triaging failures of tests it has not labelled yet;
> they give no such indication for a team without that history.

### (b) Not confirmed, ET-BF still ahead

> Because the within-project result came from post-hoc analysis, we tested it in a confirmation
> study frozen in advance, on {n_P} later failures of new tests in the same 8 projects. ET-BF stayed
> ahead of the best comparator, {cstar} ({delta} [{ci_lo}, {ci_hi}]), but did not meet the frozen
> rule, so the improvement is **not confirmed**. Taken together, our results support a narrower
> conclusion than the frozen v0.8 numbers suggest: failure evidence may help within a project, but
> the advantage is smaller or less certain than the post-hoc analysis indicated, and it has not been
> shown to exceed what project base rates explain. The main contributions of this paper are therefore
> the evaluation lessons from MDFlaker's data, the new rerun-labelled dataset and the two negative
> results.

### (c) Not confirmed, ET-BF not ahead

> Because the within-project result came from post-hoc analysis, we tested it in a confirmation
> study frozen in advance, on {n_P} later failures of new tests in the same 8 projects. There ET-BF
> did not beat the best comparator, {cstar} ({delta} [{ci_lo}, {ci_hi}]), so the improvement is **not
> confirmed**. We therefore do not claim that our features improve on MDFlaker's approach. The main
> contributions of this paper are the evaluation lessons from MDFlaker's data, the new rerun-labelled
> dataset and the negative results, including this one: a post-hoc result that looked robust under
> several checks did not hold on new failures, which is itself a reason to freeze confirmations
> before claiming improvements in flaky-test prediction.

### (d) Minimum sample not met

> Because the within-project result came from post-hoc analysis, we froze a confirmation study on
> later failures in the same 8 projects. It collected too few failures of new tests ({flaky_P}
> flaky, {notflaky_P} not flaky; minimum 40 and 40) to apply its rule, so the result remains
> **untested** and should be read as a post-hoc finding only. The main contributions of this paper
> are the evaluation lessons from MDFlaker's data, the new rerun-labelled dataset and the two
> negative results.

---

## 4. Wording rules for whoever fills this in

- "Confirmed" is used only in outcome (a). Do not write "partially confirmed", "trend towards" or
  "nearly significant" in (b)–(d).
- Do not drop the post-hoc and base-rate sentences from (a); they are what keeps a confirmed result
  honest.
- Do not move v0.9 results into the abstract's earlier sentences or the highlights as if they were
  the main result in (b)–(d). The v0.8 post-hoc result stays labelled post hoc in every outcome.
- If C\* or any value is not what a sentence assumes (for example C\* = MDF-paper-int, so
  `{mcc_mdf}` equals `{mcc_cstar}`), drop the redundant clause rather than inventing a new comparison.
- Leave-one-project-out and ET-BFC vs ET-BF are reported descriptively and never as a claim
  (v0.9 PROTOCOL §7).

## 5. Other passages in DRAFT.md to update after v0.9

- Header (lines 3–4): remove "Section 11 is completed after the v0.9 collection…"; set the draft date.
- §2 Contributions, item 5: "(a) A frozen prospective confirmation (Section 11) that confirms the
  within-project result" / "(b, c) … that does not confirm the within-project result" / "(d) … whose
  minimum sample was not met".
- §2, last paragraph: for (b)–(d), add "The prospective confirmation did not support (or could not
  test) the within-project gain."
- §7.2, last sentence: unchanged (it describes the design).
- §10 Internal validity, "Post-hoc analyses": replace "v0.9 tests it prospectively" with "v0.9
  confirmed it prospectively (Section 11)" / "v0.9 did not confirm it (Section 11)" / "v0.9 could not
  test it (Section 11)".
- `FRONT_MATTER.md`: the highlights and the short abstract (see the short variants in Section 1).
- Team decisions, item 2: record the collection date and the outcome.
