# Salt workflow recovery

Implemented on 2026-10-11:

- Preserve setup-python's `LD_LIBRARY_PATH` across the localhost SSH terminal login. Without it, the Python 3.8.18 executable loads Ubuntu's Python 3.8.10 shared library.
- Verify Python 3.8.18 inside the terminal session before starting the pipeline.
- Provision `/var/cache/salt` and `/etc/salt` for the unprivileged `cannier` experiment user. The pinned `test_minion_module_refresh` uses the default Salt cache.
- Execute Salt's entire baseline suite without `-x`. A failing baseline still blocks detection.
- Install `iproute2` for actual interface discovery and verify a global IPv4 address exists.
- Apply umask `0022` after the PAM SSH login so public TLS certificates have the expected `0644` mode.
- Default the Salt workflow to `full` (strict baseline, 12 original, 12 random, 1 reverse round).

Verified locally after shutdown repair: 59 pipeline unit tests pass; one Linux process-group integration test is skipped on Windows and required in Linux CI.

Evidence:

- Run 37968983576: Python version mismatch before subject setup.
- Run 38139660664: terminal preflight confirms the shared-library mismatch.
- Run 38139856911: Python issue resolved; baseline exposes `/var/cache/salt` permission failure.
- Run 38140250863: complete baseline exposed configuration-directory permissions, SSH umask and missing network-discovery tools (41 failures).
- Run 38160861122: baseline passed; 12 original and 7 random rounds committed. Random round 8 printed a complete summary but the process/output did not close; the workflow timed out at 300 minutes.
- Implemented a Salt-only pytest launcher: run all tests and teardown hooks, terminate leftover descendants, preserve the pytest exit code, and bound interpreter/process-group cleanup. The launcher hash is included in the environment fingerprint. A fresh full run is required; previous evidence is not silently reused.

No Salt source tests, assertions, or labels were changed. The full-run result must be verified before claiming success.

Latest fresh full verification run: https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/38213437450 (result pending).
