"""The shipped ET-BF model: load with a checksum check, predict, and explain each prediction."""
from __future__ import annotations

import hashlib
import json
from importlib import resources

import numpy as np

from .features import COLUMNS

THRESHOLD = 0.5

# Plain-language names shown next to each explanation.
LABELS = {
    "flaky_frequency": "earlier failures of this test in other runs",
    "traceback_coverage": "traceback passes through a changed line",
    "test_smells": "flakiness-prone patterns in the test (sleep, network, randomness, ...)",
    "previous_state": "result of the previous run on this branch",
    "test_size": "test length (lines)",
    "build_failed_tests": "number of failed tests in this job",
    "same_file_cofailures": "other failures in the same test file",
    "job_duration_s": "job duration (s)",
    "pr_build": "pull-request build",
    "changed_files": "files changed",
    "changed_py_files": "Python files changed",
    "changed_test_py_files": "test files changed",
    "nonpy_only_change": "only non-Python files changed",
    "changed_lines": "Python lines changed",
    "own_test_file_changed": "the failing test's own file changed",
    "path_overlap_depth": "how close the change is to the test (shared folders)",
    "traceback_frames": "traceback length (frames)",
    "frames_in_changed_files": "traceback frames in changed files",
    "last_frame_in_test_file": "error raised inside the test file",
    "frames_outside_repo": "traceback frames outside the repository",
    "min_line_distance_to_change": "distance from traceback to nearest change (lines, capped at 1000)",
    "diff_available": "diff against the base commit available",
}


def load():
    data = resources.files("flakexplain") / "data"
    card = json.loads((data / "model_card.json").read_text(encoding="utf-8"))
    raw = (data / card["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != card["sha256"]:
        raise RuntimeError("The model file does not match its model card checksum; reinstall flakexplain.")
    import io
    import joblib
    payload = joblib.load(io.BytesIO(raw))
    if payload["columns"] != COLUMNS:
        raise RuntimeError("The model's feature columns differ from this version of flakexplain.")
    return payload["model"], card


def tree_path_attribution(model, x):
    """Exact decomposition of the forest probability along the observed tree paths (Saabas), not SHAP."""
    values, base = np.zeros(x.size), 0.0
    for est in model.estimators_:
        t, node = est.tree_, 0

        def prob(n):
            v = t.value[n, 0]
            return float(v[1] / v.sum())

        base += prob(0)
        while t.children_left[node] != t.children_right[node]:
            child = t.children_left[node] if x[t.feature[node]] <= t.threshold[node] else t.children_right[node]
            values[t.feature[node]] += prob(child) - prob(node)
            node = child
    return base / len(model.estimators_), values / len(model.estimators_)


def explain(model, X):
    """(method, base value, contributions per row) towards P(flaky): SHAP when installed, else tree paths."""
    try:
        import shap
    except ImportError:
        pairs = [tree_path_attribution(model, x) for x in X]
        return "tree-path attribution", float(pairs[0][0]) if pairs else 0.0, np.array([p[1] for p in pairs])
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else np.asarray(sv)[:, :, 1]  # class 1 = flaky
    return "SHAP", float(np.atleast_1d(explainer.expected_value)[1]), sv


def predict(model, rows, top=4):
    """Add probability, verdict and the leading reasons to each feature row."""
    if not rows:
        return "", rows
    X = np.array([[float(r["features"][c]) for c in COLUMNS] for r in rows], dtype=float)
    proba = model.predict_proba(X)[:, list(model.classes_).index(1)]
    method, _, contrib = explain(model, X)
    for r, x, p, c in zip(rows, X, proba, contrib):
        r["p_flaky"] = float(p)
        r["verdict"] = "likely flaky" if p >= THRESHOLD else "likely real failure"
        order = np.argsort(-np.abs(c))[:top]
        r["reasons"] = [dict(feature=COLUMNS[i], label=LABELS[COLUMNS[i]], value=float(x[i]), contribution=float(c[i]))
                        for i in order]
    return method, rows
