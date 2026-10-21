import datetime
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from flakexplain import cli, detect, features, history, model

UTC = datetime.timezone.utc


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


# --- detect --------------------------------------------------------------------------------------

def od_project(tmp_path):
    """test_reads passes only if test_writes ran first: a classic order-dependent (OD) test."""
    write(tmp_path / "tests/test_state.py", """
        STATE = []

        def test_writes():
            STATE.append(1)

        def test_reads():
            assert STATE

        def test_stable():
            assert 1 + 1 == 2
    """)
    return tmp_path


def test_detect_finds_order_dependent_test(tmp_path):
    summary = detect.detect(od_project(tmp_path), tmp_path / "out", original=2, randomised=0, reverse=1, log=lambda *_: None)
    assert summary["total_rounds"] == 3
    flaky = {k.split("::")[-1]: v for k, v in summary["flaky"].items()}
    assert set(flaky) == {"test_reads"}
    assert flaky["test_reads"]["classification"] == "OD"
    assert summary["not_observed_flaky"] == 2
    assert "test_reads" in (tmp_path / "out/report.md").read_text(encoding="utf-8")


def collected(project, *extra):
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:randomly", *extra], cwd=project,
                         capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if "::" in line]


def test_order_plugin_is_seeded_and_reverses(tmp_path):
    write(tmp_path / "tests/test_many.py", "".join(f"def test_{i}():\n    pass\n" for i in range(12)))
    plugin = ["-p", "flakexplain.order_plugin"]
    original = collected(tmp_path)
    shuffled = collected(tmp_path, *plugin, "--fx-order=random", "--fx-seed=7")
    assert shuffled != original and sorted(shuffled) == sorted(original)
    assert shuffled == collected(tmp_path, *plugin, "--fx-order=random", "--fx-seed=7")
    assert collected(tmp_path, *plugin, "--fx-order=reverse") == original[::-1]
    summary = detect.detect(od_project(tmp_path), tmp_path / "out", original=1, randomised=2, reverse=0, seed=7, log=lambda *_: None)
    assert summary["rounds"] == {"original": 1, "random": 2, "reverse": 0}


def test_detect_stops_when_baseline_fails(tmp_path):
    write(tmp_path / "tests/test_broken.py", "def test_broken():\n    assert False\n")
    assert detect.detect(tmp_path, tmp_path / "out", original=1, randomised=0, reverse=0, log=lambda *_: None) is None
    assert cli.main(["detect", str(tmp_path), "--original", "1", "--random", "0", "--reverse", "0"]) == 2


def test_classify_nod_and_unlabelled():
    rounds = [("original-order", "o1", {"a": "PASS", "b": "FAIL", "c": "SKIP"}),
              ("original-order", "o2", {"a": "FAIL", "b": "FAIL", "c": "SKIP"})]
    flaky, not_observed, unlabelled = detect.classify(rounds)
    assert flaky["a"]["classification"] == "NOD" and not_observed == [] and sorted(unlabelled) == ["b", "c"]


# --- features ------------------------------------------------------------------------------------

LOG = """\
2026-07-23T06:54:47.1234567Z ============================= test session starts ==============================
2026-07-23T06:54:47.1234567Z ___________________________ TestThing.test_net ___________________________
2026-07-23T06:54:47.1234567Z tests/test_x.py:5: in test_net
2026-07-23T06:54:47.1234567Z     fetch()
2026-07-23T06:54:47.1234567Z /usr/lib/python3.12/socket.py:10: in connect
2026-07-23T06:54:47.1234567Z     raise TimeoutError
2026-07-23T06:54:47.1234567Z E   TimeoutError
2026-07-23T06:54:47.1234567Z =========================== short test summary info ============================
2026-07-23T06:54:47.1234567Z FAILED tests/test_x.py::TestThing::test_net - TimeoutError
2026-07-23T06:54:47.1234567Z ========================= 1 failed, 3 passed in 2.50s ==========================
"""


def test_from_log_parses_failures_frames_and_duration():
    failures, duration = features.from_log(LOG)
    assert failures == [("tests/test_x.py::TestThing::test_net", [("tests/test_x.py", 5), ("/usr/lib/python3.12/socket.py", 10)])]
    assert duration == 2.5


def test_flaky_frequency_counts_transitions():
    t = datetime.datetime(2026, 1, 1, tzinfo=UTC)
    past = [t, t + datetime.timedelta(hours=1), t + datetime.timedelta(hours=20)]
    assert features.flaky_frequency(past, t + datetime.timedelta(days=2)) == round(2 / 5, 2)
    assert features.flaky_frequency([], t) == 0.0


def test_norm_frame():
    assert features.norm_frame("/home/runner/work/rich/rich/tests/a.py", "rich") == ("tests/a.py", True)
    assert features.norm_frame("C:/work/proj/src/m.py", "proj", ["C:/work/proj"]) == ("src/m.py", True)
    assert features.norm_frame("/usr/lib/python3.12/json.py", "proj")[1] is False


def test_from_junit_maps_classname_to_file(tmp_path):
    xml = tmp_path / "r.xml"
    xml.write_text("""<testsuites><testsuite time="1.5">
      <testcase classname="tests.test_x.TestThing" name="test_net"><failure message="boom">tests/test_x.py:5: in test_net
    fetch()
E   TimeoutError</failure></testcase>
      <testcase classname="tests.test_x" name="test_ok"/></testsuite></testsuites>""", encoding="utf-8")
    failures, total = features.from_junit(xml, {"tests/test_x.py"})
    assert failures == [("tests/test_x.py::TestThing::test_net", [("tests/test_x.py", 5)])]
    assert total == 1.5


# --- triage end to end ---------------------------------------------------------------------------

def triage_repo(tmp_path):
    repo = tmp_path / "proj"
    write(repo / "tests/test_x.py", "import time\n\ndef test_net():\n    time.sleep(0.01)\n    assert True\n")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "one")
    write(repo / "tests/test_x.py", "import time\n\ndef test_net():\n    time.sleep(0.01)\n    assert False\n")
    git(repo, "commit", "-qam", "two")
    log = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-rA", "tests"], cwd=repo,
                         capture_output=True, text=True).stdout
    (tmp_path / "pytest.log").write_text(log, encoding="utf-8")
    return repo, tmp_path / "pytest.log"


def test_triage_end_to_end(tmp_path, capsys):
    repo, log = triage_repo(tmp_path)
    hist = tmp_path / "history.jsonl"
    args = ["triage", "--log", str(log), "--repo", str(repo), "--history", str(hist), "--format", "json", "--push"]
    assert cli.main(args + ["--run-id", "1"]) == 0
    first = json.loads(capsys.readouterr().out)
    (row,) = first["failures"]
    assert row["nodeid"] == "tests/test_x.py::test_net" and row["source_mapped"] == 1
    f = row["features"]
    assert f["own_test_file_changed"] == 1 and f["changed_lines"] == 2 and f["diff_available"] == 1
    assert f["test_smells"] >= 1 and f["flaky_frequency"] == 0.0
    assert row["verdict"] in ("likely flaky", "likely real failure") and 0 <= row["p_flaky"] <= 1
    assert len(row["reasons"]) == 4
    assert any("No failure history" in n for n in first["notes"])
    # The first run was recorded, so a later run sees one earlier failure of this test.
    assert cli.main(args + ["--run-id", "2"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["failures"][0]["features"]["flaky_frequency"] == round(1 / 3, 2)
    assert len(hist.read_text().splitlines()) == 2


def test_triage_markdown_and_no_failures(tmp_path, capsys):
    repo, log = triage_repo(tmp_path)
    assert cli.main(["triage", "--log", str(log), "--repo", str(repo), "--no-record", "--format", "markdown"]) == 0
    assert "### FlakeXplain triage" in capsys.readouterr().out
    empty = tmp_path / "empty.log"
    empty.write_text("===== 3 passed in 0.1s =====\n", encoding="utf-8")
    assert cli.main(["triage", "--log", str(empty), "--repo", str(repo)]) == 0
    assert "no failed tests" in capsys.readouterr().out


def test_model_card_checksum_and_attribution_add_up():
    m, card = model.load()
    assert card["training"]["failures"] == 1292 and card["columns"] == features.COLUMNS
    import numpy as np
    x = np.zeros(len(features.COLUMNS))
    base, contrib = model.tree_path_attribution(m, x)
    assert base + contrib.sum() == pytest.approx(m.predict_proba(x.reshape(1, -1))[0, 1])


def test_explanations_without_shap(monkeypatch):
    monkeypatch.setitem(sys.modules, "shap", None)  # import shap -> ImportError
    m, _ = model.load()
    row = dict(features={c: 0.0 for c in features.COLUMNS})
    method, (out,) = model.predict(m, [row])
    assert method == "tree-path attribution" and len(out["reasons"]) == 4
