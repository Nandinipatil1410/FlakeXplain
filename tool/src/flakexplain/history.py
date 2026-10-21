"""Local failure history (JSON Lines): one record per failed test per triaged run.

This history feeds `flaky_frequency`. Keep the file between CI runs (for example with actions/cache);
without it every failure looks new, which the v0.8 study shows is the hardest case.
"""
from __future__ import annotations

import datetime
import json
from collections import defaultdict
from pathlib import Path

from .features import history_key


def load(path):
    """{history_key: [(datetime, run_id)]}; a missing file is an empty history."""
    out = defaultdict(list)
    path = Path(path)
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[history_key(rec["nodeid"])].append((datetime.datetime.fromisoformat(rec["when"]), str(rec["run_id"])))
    return out


def record(path, nodeids, run_id, when):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for nodeid in nodeids:
            f.write(json.dumps(dict(nodeid=nodeid, run_id=str(run_id), when=when.isoformat())) + "\n")
