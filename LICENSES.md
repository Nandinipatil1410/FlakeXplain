# Licences in this repository

Decided by the team on 21 October 2026.

| What | Licence |
|---|---|
| Our code: `scripts/`, `.github/`, `tests/`, `rerun/`, `replication/*.py`, `paper/figures/make_figures.py`, `run_all.*` | **MIT**, see `LICENSE` |
| Our derived data: the files written to `replication/data/` and the reports and datasets we produced | **CC-BY-4.0**, see `replication/LICENSE-DATA.md` |

## Not covered by our licences

- **`cannier-replication/`** is CANNIER's released code, under its own MIT licence (`cannier-replication/LICENSE`, © 2022 Owain Parry).
- **`dataset/cannier-matched-v0.4/`** contains material derived from CANNIER's release. See its `THIRD_PARTY_LICENSE.txt`.
- **MDFlaker's released dataset**, used in v0.6, v0.7 and E3, is not redistributed here. It stays under its authors' terms; get it from the upstream repository.
- **Upstream projects** named in the data (for example urllib3, pytest and hypothesis) keep their own licences. Our data contain only identifiers such as repository names, commit SHAs, run and job IDs and pytest node IDs. They contain no project source code and no raw CI log text.
