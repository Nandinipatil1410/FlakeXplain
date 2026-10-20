# Amendment B1 to the v0.8 protocol: re-run what CI actually tested

Dated 20 October 2026. Committed **before any re-run or label exists**. `PROTOCOL.md` remains in
force except as stated here.

**Why.** For `pull_request` events, GitHub Actions does not test the PR's head commit. It tests a
temporary merge of the head into the base branch. Re-running only the head commit could fail to
reproduce a real failure caused by that merge, and would then mislabel the failure as flaky.

**What changes.** Section 5's "rerun at that commit" becomes "rerun the code the CI job actually
tested":
- **push events:** re-run at `head_sha`;
- **pull_request events:** check out `merge_base`, merge `head_sha` with `--no-edit`, and re-run on
  that tree. Both shas come from the job's own checkout log line
  `HEAD is now at <sha> Merge <head> into <base>`.
- If the merge conflicts or a sha cannot be fetched, the execution is **excluded and reported** as
  a setup failure. It is never relabelled.

**Data.** `candidates.csv` gains two label-blind columns, `checkout` and `merge_base`. The rows are
unchanged (1,659), and each row's other fields are identical. The new file's SHA-256 is in
`amendment_B1.json`. All 1,544 PR candidates have a parsed merge line; 115 candidates are push runs. (An earlier version of this sentence stated 1,629 and 30 by mistake; corrected before any re-run.)
