#!/usr/bin/env python3
"""
Step 4 & Step 5: Detect & Classify Flaky Tests & Generate FlakeXplain Report
Parses all JUnit XML files in repos/<repo>/results/*.xml.
Tracks per-test outcomes across all runs and configurations.
Classifies observed flaky tests into OD, NOD, or Unclassified.
Generates empirical table and exports FlakeXplain_Flaky_Report.md.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

from runtime import BASE_DIR, REPOS_DIR, complete_xml, read_json

REPOS = [
    "click", "flask", "filelock", "fsspec", "httpx", "urllib3", "werkzeug",
    "rich", "pytest", "ipython", "reframe", "loguru", "freezegun",
]

def parse_xml_file(xml_path):
    outcomes = {}
    if not xml_path.exists():
        return outcomes

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        testcases = root.findall(".//testcase")
        for tc in testcases:
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            file_attr = tc.get("file", "")
            
            if file_attr:
                test_id = f"{file_attr}::{name}"
            elif classname:
                test_id = f"{classname}::{name}"
            else:
                test_id = name

            if tc.find("failure") is not None:
                status = "FAIL"
            elif tc.find("error") is not None:
                status = "ERROR"
            elif tc.find("skipped") is not None:
                status = "SKIP"
            else:
                status = "PASS"

            outcomes[test_id] = status
    except Exception as e:
        print(f"Warning: Failed to parse XML file {xml_path}: {e}")

    return outcomes

def analyze_repo_results(repo_name):
    repo_dir = REPOS_DIR / repo_name
    if not repo_dir.exists():
        repo_dir = BASE_DIR / "repos" / repo_name  # Separate legacy evidence, never merged.
    results_dir = repo_dir / "results"
    manifest_path = results_dir / "execution_manifest.json"
    setup_log_path = repo_dir / "setup_log.md"

    commit_hash = "UNKNOWN"
    gate_status = "UNKNOWN"
    if setup_log_path.exists():
        with open(setup_log_path, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.splitlines():
                if "Pinned Commit Hash" in line and ":" in line:
                    commit_hash = line.split(":", 1)[1].strip().strip("`")
                if "Baseline Gate Status" in line:
                    gate_status = line.split(":", 1)[1].strip().strip("`")

    environment = read_json(repo_dir / "environment.json")
    if commit_hash == "UNKNOWN" and environment.get("commit"):
        commit_hash = environment["commit"]

    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            try:
                manifest = json.load(f)
            except Exception:
                manifest = {}

    xml_files = list(results_dir.glob("*_run_*.xml"))
    if manifest.get("environment_id"):
        state = read_json(repo_dir / "baseline_state.json")
        records = manifest.get("original_rounds", []) + manifest.get("random_rounds", [])
        reverse_records = manifest.get("reverse_rounds")
        if reverse_records is None:
            reverse_records = (
                [manifest["reverse_round"]] if manifest.get("reverse_round") else []
            )
        records.extend(reverse_records)
        valid_gate = (state.get("status") == "PASSED" and
                      state.get("environment_id") == manifest["environment_id"])
        xml_files = [results_dir / r["xml_file"] for r in records
                     if valid_gate and r.get("exit_code") in (0, 1)
                     and complete_xml(results_dir / r["xml_file"], manifest["collected_count"])]
        if not valid_gate:
            gate_status = "UNVERIFIED (environment/baseline mismatch)"
    if not xml_files:
        return {
            "repo_name": repo_name,
            "execution_directory": str(repo_dir),
            "commit_hash": commit_hash,
            "gate_status": gate_status,
            "total_tests_collected": read_json(repo_dir / "baseline_state.json").get("collected_count", 0),
            "orig_rounds": 0,
            "rand_rounds": 0,
            "rev_rounds": 0,
            "total_rounds": 0,
            "wall_clock_seconds": 0.0,
            "observed_flaky_count": 0,
            "od_count": 0,
            "nod_count": 0,
            "unclassified_count": 0,
            "not_observed_flaky_count": 0,
            "unlabelled_count": 0,
            "flaky_ratio": "DISCARDED" if "FAILED" in gate_status else "NOT RUN",
            "observed_flaky_percentage": None,
            "observed_flaky_details": {}
        }

    test_outcomes = defaultdict(list)
    xml_by_config = defaultdict(list)

    for xml_file in sorted(xml_files):
        filename = xml_file.name
        if filename.startswith("original_"):
            config = "original-order"
        elif filename.startswith("random_"):
            config = "random-order"
        elif filename.startswith("reverse_"):
            config = "reverse-order"
        else:
            config = "other"

        xml_by_config[config].append(xml_file)
        parsed = parse_xml_file(xml_file)

        for test_id, status in parsed.items():
            test_outcomes[test_id].append({
                "config": config,
                "file": filename,
                "status": status
            })

    total_tests_collected = len(test_outcomes)
    observed_flaky = {}
    not_observed_flaky = {}
    unlabelled = {}

    for test_id, records in test_outcomes.items():
        active_statuses = set(r["status"] for r in records if r["status"] != "SKIP")
        has_pass = "PASS" in active_statuses
        has_fail_or_err = bool(active_statuses.intersection({"FAIL", "ERROR"}))

        if has_pass and has_fail_or_err:
            orig_statuses = set(r["status"] for r in records if r["config"] == "original-order" and r["status"] != "SKIP")
            rand_statuses = set(r["status"] for r in records if r["config"] == "random-order" and r["status"] != "SKIP")
            rev_statuses = set(r["status"] for r in records if r["config"] == "reverse-order" and r["status"] != "SKIP")

            if "FAIL" in orig_statuses or "ERROR" in orig_statuses:
                classification = "NOD"
                reason = "Fails in original order non-deterministically (order independent)"
            elif ("FAIL" in rand_statuses or "ERROR" in rand_statuses or "FAIL" in rev_statuses or "ERROR" in rev_statuses) and orig_statuses == {"PASS"}:
                classification = "OD"
                reason = "Only fails under reordered/randomized configuration"
            else:
                classification = "Unclassified"
                reason = "Inconsistent behavior under mixed configurations without rerun verification"

            observed_flaky[test_id] = {
                "records": records,
                "classification": classification,
                "reason": reason
            }
        elif active_statuses == {"PASS"}:
            not_observed_flaky[test_id] = records
        else:
            # Skip-only or failure-only evidence does not establish a negative label.
            unlabelled[test_id] = records

    orig_rounds_count = len(xml_by_config["original-order"])
    rand_rounds_count = len(xml_by_config["random-order"])
    rev_rounds_count = len(xml_by_config["reverse-order"])
    total_rounds = orig_rounds_count + rand_rounds_count + rev_rounds_count
    wall_clock_time = manifest.get("total_wall_clock_seconds", 0.0)

    od_count = sum(1 for data in observed_flaky.values() if data["classification"] == "OD")
    nod_count = sum(1 for data in observed_flaky.values() if data["classification"] == "NOD")
    unclassified_count = sum(1 for data in observed_flaky.values() if data["classification"] == "Unclassified")

    flaky_count = len(observed_flaky)
    non_flaky_count = len(not_observed_flaky)
    ratio = f"{flaky_count}:{non_flaky_count}"
    labelled_count = flaky_count + non_flaky_count
    flaky_percentage = (100.0 * flaky_count / labelled_count) if labelled_count else None

    summary = {
        "repo_name": repo_name,
            "execution_directory": str(repo_dir),
        "commit_hash": commit_hash,
        "gate_status": gate_status,
        "total_tests_collected": total_tests_collected,
        "orig_rounds": orig_rounds_count,
        "rand_rounds": rand_rounds_count,
        "rev_rounds": rev_rounds_count,
        "total_rounds": total_rounds,
        "wall_clock_seconds": wall_clock_time,
        "observed_flaky_count": flaky_count,
        "od_count": od_count,
        "nod_count": nod_count,
        "unclassified_count": unclassified_count,
        "not_observed_flaky_count": non_flaky_count,
        "unlabelled_count": len(unlabelled),
        "flaky_ratio": ratio,
        "observed_flaky_percentage": flaky_percentage,
        "observed_flaky_details": observed_flaky
    }

    return summary

def generate_report(summaries):
    report_path = BASE_DIR / "FlakeXplain_Flaky_Report.md"

    md = []
    md.append("# FlakeXplain: Empirical Flaky Test Detection Report")
    md.append("\n**Methodology Adaptation**: iDFlakies (Lam et al., ICST 2019) detection protocol ported from JUnit/Maven to Pytest/Python.")
    md.append("\n> [!CAUTION]")
    md.append("> **Non-Flaky Label Caveat**: Tests categorized as `not observed flaky` were not observed flipping outcome in the executed $N$ rounds under the pinned environment. This is **not** mathematical proof of permanent non-flakiness.\n")

    md.append("## Summary Table\n")
    md.append("Observed flaky percentage is calculated over labelled tests: `observed flaky / (observed flaky + not observed flaky) x 100`. Skip-only and failure-only tests are excluded from this denominator.\n")
    md.append("| Repository | Commit Hash | Total Tests Collected | Rounds (Orig / Rand / Rev) | Wall-Clock Time | Observed Flaky (Total) | OD | NOD | Unclassified | Not Observed Flaky (in N runs) | Observed Flaky Ratio | Observed Flaky % | Baseline Status |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    for s in summaries:
        if s is None:
            continue
        rounds_str = f"{s['orig_rounds']} / {s['rand_rounds']} / {s['rev_rounds']}"
        time_str = f"{s['wall_clock_seconds']:.2f}s" if s['wall_clock_seconds'] > 0 else "N/A"
        percentage_str = (f"{s['observed_flaky_percentage']:.2f}%"
                          if s['observed_flaky_percentage'] is not None else "N/A")
        md.append(
            f"| `{s['repo_name']}` | `{s['commit_hash'][:8]}` | {s['total_tests_collected']} | {rounds_str} | {time_str} | "
            f"**{s['observed_flaky_count']}** | {s['od_count']} | {s['nod_count']} | {s['unclassified_count']} | "
            f"{s['not_observed_flaky_count']} | **{s['flaky_ratio']}** | **{percentage_str}** | `{s['gate_status']}` |"
        )

    completed = [s for s in summaries if s and s["total_rounds"] > 0]
    if completed:
        total_flaky = sum(s["observed_flaky_count"] for s in completed)
        total_not_observed = sum(s["not_observed_flaky_count"] for s in completed)
        total_labelled = total_flaky + total_not_observed
        total_percentage = 100.0 * total_flaky / total_labelled if total_labelled else 0.0
        md.append("\n## Combined Completed-Run Totals\n")
        md.append(f"- **Repositories with completed detection rounds**: {len(completed)}")
        md.append(f"- **Tests collected**: {sum(s['total_tests_collected'] for s in completed)}")
        md.append(f"- **Observed flaky tests**: {total_flaky}")
        md.append(f"- **OD / NOD / Unclassified**: {sum(s['od_count'] for s in completed)} / {sum(s['nod_count'] for s in completed)} / {sum(s['unclassified_count'] for s in completed)}")
        md.append(f"- **Not observed flaky**: {total_not_observed}")
        md.append(f"- **Unlabelled** (skip-only or failure-only): {sum(s['unlabelled_count'] for s in completed)}")
        md.append(f"- **Observed flaky ratio**: `{total_flaky}:{total_not_observed}`")
        md.append(f"- **Observed flaky percentage among labelled tests**: **{total_percentage:.2f}%**")

    md.append("\n## Per-Repository Breakdown & Empirical Logs\n")
    for s in summaries:
        if s is None:
            continue
        md.append(f"### Repository: `{s['repo_name']}`")
        md.append(f"- **Pinned Commit Hash**: `{s['commit_hash']}`")
        md.append(f"- **Execution Directory**: `{s['execution_directory']}`")
        md.append(f"- **Baseline Gate Status**: `{s['gate_status']}`")
        md.append(f"- **Total Collected Tests**: {s['total_tests_collected']}")
        md.append(f"- **Unlabelled Tests** (skip-only or failure-only): {s['unlabelled_count']}")
        md.append(f"- **Total Rounds Run**: {s['total_rounds']} ({s['orig_rounds']} original, {s['rand_rounds']} random, {s['rev_rounds']} reverse)")
        md.append(f"- **Total Wall-Clock Time**: {s['wall_clock_seconds']:.2f} seconds")
        md.append(f"- **Observed Flaky Ratio**: `{s['flaky_ratio']}`")
        percentage_str = (f"{s['observed_flaky_percentage']:.2f}%"
                          if s['observed_flaky_percentage'] is not None else "N/A")
        md.append(f"- **Observed Flaky Percentage Among Labelled Tests**: `{percentage_str}`\n")

        if s['observed_flaky_count'] > 0:
            md.append("#### Observed Flaky Test Details:\n")
            md.append("| Test Node ID | Classification | Category Reason | Outcomes Across Runs |")
            md.append("|---|---|---|---|")
            for tid, info in s['observed_flaky_details'].items():
                outcomes_summary = ", ".join([f"{r['config']}:{r['status']}" for r in info['records']])
                md.append(f"| `{tid}` | **{info['classification']}** | {info['reason']} | `{outcomes_summary}` |")
        elif s["total_rounds"] == 0:
            md.append("*No completed detection rounds; flaky labels have not been assigned.*")
        else:
            md.append("*No tests flipped outcomes across the executed reordering configurations under this pinned environment.*")

        md.append("\n---")

    import uuid
    temporary = report_path.with_suffix("." + uuid.uuid4().hex + ".tmp")
    temporary.write_text("\n".join(md), encoding="utf-8")
    temporary.replace(report_path)

    print(f"\nGenerated report: {report_path}")
    return report_path

def main():
    summaries = []
    for name in REPOS:
        s = analyze_repo_results(name)
        if s:
            summaries.append(s)

    if summaries:
        generate_report(summaries)
        print("\nStep 4 & Step 5 Completed Successfully.")

if __name__ == "__main__":
    main()
