# Licence options for the v0.8 replication package (draft for the team)

Status: **Proposed.** No licence has been chosen, and there is no `LICENSE` file. The team picks one
option for the code and one for the data. The guide approves the data release.

## Code (scripts, workflow, export script)

| Option | Summary | Pros | Cons |
|---|---|---|---|
| **MIT** | Permissive; keep the copyright notice | Shortest; most common for research tools; easy for the Software Impacts tool article | No explicit patent grant |
| **Apache-2.0** | Permissive, with an explicit patent grant and a NOTICE file | Patent clause; clear contribution terms | Longer; changed files must be marked |
| BSD-3-Clause | Permissive; bans using the authors' names for endorsement | Close to MIT | Rarely chosen over MIT in this area |
| GPL-3.0 | Copyleft | Derived tools stay open | Discourages reuse in industry and in other papers' pipelines |

**Suggestion:** MIT. It has the least friction for reviewers and reusers, and nothing in the code
raises a patent concern.

## Data (`replication/data/`)

| Option | Summary | Pros | Cons |
|---|---|---|---|
| **CC-BY-4.0** | Reuse with attribution | Zenodo default; journals accept it; citations come back to the paper | Attribution cannot be enforced in practice |
| CC0-1.0 | Public-domain dedication | Simplest reuse; common for benchmarks | No legal attribution requirement (citation by norm only) |
| ODC-BY-1.0 | Attribution licence for databases | Written for databases | Less familiar to SE reviewers |

**Suggestion:** CC-BY-4.0.

## Points to check before release

- **Third-party content in the data.**
  - Rows name public GitHub repositories, commit SHAs, workflow and job names, and pytest node IDs
    from those projects' public CI.
  - These are factual identifiers, and no project source code or raw log text is included. Our
    licence covers our compilation and the derived labels and features.
  - Upstream projects keep their own licences.
- **Data we do not redistribute.**
  - MDFlaker's released dataset, used for E3, stays under its authors' terms. Point to its upstream
    repository instead.
  - Raw CI logs are GitHub-hosted content and are excluded from the package.
- **Personal data.**
  - `failure_history.csv.gz` and `candidates.csv` contain no user names or e-mail addresses. They
    hold run, job and commit IDs only.
  - Before release, recheck that the workflow or job names contain no personal names.
- **Mixed licences.** The code and the data can carry different licences in the same Zenodo record.
  State both in the README and in `.zenodo.json` (`license` takes one ID, so name the other one in
  `notes`).
