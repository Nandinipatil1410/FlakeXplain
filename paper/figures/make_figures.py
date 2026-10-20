"""Make the figures for paper/DRAFT.md from the stored v0.8 reports.

Reads only these files in reports/mdflaker-fresh-v0.8/:
results.json, robustness.json, diagnostics.json, posthoc_extra.json and
labels_summary.json. It does not train or rerun anything, and every number
it plots or prints comes from those files.

Outputs, written next to this script:
  fig1_pipeline, fig2_projects, fig3_mcc_original_vs_strict,
  fig4_unseen_per_project, fig5_shap_ranking  (.pdf and .png each)
  CAPTIONS.md

Run from the repository root:
  .venv-pilot/Scripts/python.exe paper/figures/make_figures.py
Pass --captions-only to check the reports and write CAPTIONS.md without
matplotlib.
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent.parent / "reports" / "mdflaker-fresh-v0.8"
SOURCE = "reports/mdflaker-fresh-v0.8"

# Okabe-Ito colours (colour-blind safe).
OI = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "grey": "#999999",
    "black": "#000000",
}

# Short names used in the draft: "MDFlaker" = MDF-paper-int, "KNN8" = KNN8-float.
ARMS = [
    ("MDF-paper-int", "MDFlaker", OI["vermillion"], "s"),
    ("KNN8-float", "KNN8", OI["blue"], "^"),
    ("ET-BF", "ET-BF (ours)", OI["green"], "o"),
]

SINGLE_COL = 3.5  # inches; typical single-column width

RCPARAMS = {
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "axes.titlesize": 8,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
}


def setup_matplotlib():
    """Import matplotlib only when figures are drawn."""
    global plt, FancyArrowPatch, FancyBboxPatch
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    plt.rcParams.update(RCPARAMS)


def load(name):
    with open(REPORTS / name, encoding="utf-8") as f:
        return json.load(f)


def short(repo):
    return repo.split("/", 1)[1]


def fmt(x):
    return f"{x:.3f}".replace("-", "−")


def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(
            HERE / f"{stem}.{ext}",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.02,
            metadata={"CreationDate": None} if ext == "pdf" else None,
        )
    plt.close(fig)


def check_close(a, b, what):
    if not math.isclose(a, b, abs_tol=1e-12):
        raise SystemExit(f"Inconsistent reports for {what}: {a} vs {b}")


# --------------------------------------------------------------------------
# Figure 1: pipeline


def fig_pipeline(labels, results, posthoc, draw=True):
    total = labels["total"]
    flaky = total["flaky"]
    not_flaky = total["not_flaky"]
    unlabelled = sum(v for k, v in total.items() if k.startswith("unlabelled"))
    candidates = labels["candidates_with_results"]
    if flaky + not_flaky + unlabelled != candidates:
        raise SystemExit("labels_summary.json totals do not add up")
    check_close(results["labelled"], flaky + not_flaky, "labelled count")
    n_projects = len(results["projects"])
    e1 = results["evaluations"]["E1"]["arms"]["ET-BF"]
    e2 = results["evaluations"]["E2"]["arms"]["ET-BF"]
    unseen = posthoc["strict"]["unseen_E1"]
    data = {
        "candidates": candidates, "flaky": flaky, "not_flaky": not_flaky,
        "unlabelled": unlabelled, "projects": n_projects,
        "e1_n": e1["n"], "e1_flaky": e1["positives"],
        "e2_n": e2["n"], "e2_flaky": e2["positives"],
        "unseen_n": unseen["n"], "unseen_flaky": unseen["flaky"],
    }
    if not draw:
        return data

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 13)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec=OI["black"], ls="-", fs=6.5):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0.02,rounding_size=0.18",
                fc=fc, ec=ec, lw=0.7, ls=ls,
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, linespacing=1.15)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(
            FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                            mutation_scale=7, lw=0.7, color=OI["black"],
                            shrinkA=0, shrinkB=0)
        )

    light = "#F2F2F2"
    data_c = "#DCEFFA"   # light sky
    model_c = "#D9F0E7"  # light green
    eval_c = "#FBEBD0"   # light orange

    # Row 1: data collection (top to bottom on the left)
    box(0.1, 11.3, 4.4, 1.4, "GitHub Actions CI logs\nfailed test executions", light)
    box(0.1, 9.1, 4.4, 1.6, f"Candidate failures\n{candidates:,} with rerun results\n"
        f"({n_projects} projects)", data_c)
    box(0.1, 6.9, 4.4, 1.6, "30 reruns per failure\non the commit CI tested", data_c)
    box(0.1, 4.2, 4.4, 2.1,
        f"Labels\nflaky {flaky:,} | not flaky {not_flaky:,}\n"
        f"unlabelled {unlabelled:,} (reported)", data_c)
    arrow(2.3, 11.3, 2.3, 10.7)
    arrow(2.3, 9.1, 2.3, 8.5)
    arrow(2.3, 6.9, 2.3, 6.3)

    # Right column: features and models
    box(5.5, 11.3, 4.4, 1.4, "Features at failure time\nB: MDFlaker's factors\n"
        "F: failure evidence", light, fs=6.2)
    box(5.5, 9.4, 4.4, 1.3, "C: static test context\n(ET-BFC arm only)", light,
        ls="--", fs=6.2)
    box(5.5, 6.6, 4.4, 2.2,
        "Models\nMDFlaker (B, rule + KNN)\nKNN8 (B)\nET-B, ET-BF (ours), ET-BFC",
        model_c, fs=6.2)
    arrow(7.7, 11.3, 7.7, 10.7)
    arrow(7.7, 9.4, 7.7, 8.8)
    arrow(4.5, 5.25, 5.5, 7.0)

    # Bottom: evaluations
    box(0.1, 0.4, 3.1, 2.9,
        f"E1\ntime-ordered\nwithin project\ntest n = {e1['n']:,}\n"
        f"({e1['positives']} flaky)", eval_c, fs=6.0)
    box(3.45, 0.4, 3.1, 2.9,
        f"E2\nleave-one-\nproject-out\nn = {e2['n']:,}\n({e2['positives']} flaky)",
        eval_c, fs=6.0)
    box(6.8, 0.4, 3.1, 2.9,
        f"Unseen tests\n(post hoc)\nE1 tests not in\ntraining, n = {unseen['n']}\n"
        f"({unseen['flaky']} flaky)", eval_c, ls="--", fs=6.0)
    arrow(7.7, 6.6, 1.65, 3.3)
    arrow(7.7, 6.6, 5.0, 3.3)
    arrow(7.7, 6.6, 8.35, 3.3)

    ax.text(5.0, 3.75, "original and strict (post hoc) flaky-frequency history",
            ha="center", va="center", fontsize=5.8, style="italic")

    save(fig, "fig1_pipeline")
    return data


# --------------------------------------------------------------------------
# Figure 2: per-project labelled and flaky counts


def fig_projects(results, labels, draw=True):
    projects = results["projects"]
    for repo, p in projects.items():
        by_repo = labels["by_repo"][repo]
        if by_repo["flaky"] != p["flaky"] or by_repo["flaky"] + by_repo["not_flaky"] != p["n"]:
            raise SystemExit(f"Count mismatch for {repo}")
    repos = sorted(projects, key=lambda r: projects[r]["n"])
    n = [projects[r]["n"] for r in repos]
    fl = [projects[r]["flaky"] for r in repos]
    y = range(len(repos))
    data = {"labelled": results["labelled"], "flaky": results["flaky"]}
    if not draw:
        return data

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.4))
    ax.barh(y, n, color=OI["sky"], height=0.7, label="labelled")
    ax.barh(y, fl, color=OI["blue"], height=0.7, label="flaky")
    for yi, ni, fi in zip(y, n, fl):
        ax.text(ni + 4, yi, f"{fi}/{ni} ({100 * fi / ni:.0f}%)", va="center", fontsize=6.3)
    ax.set_yticks(list(y))
    ax.set_yticklabels([short(r) for r in repos])
    ax.set_xlabel("Labelled test failures")
    ax.set_xlim(0, max(n) * 1.32)
    ax.legend(loc="lower right", frameon=False)
    save(fig, "fig2_projects")
    return data


# --------------------------------------------------------------------------
# Figure 3: MCC original vs strict history


def fig_original_vs_strict(robust, results, posthoc, draw=True):
    r1 = robust["R1_strict_history"]
    evals = [("E1", "E1 time-ordered"), ("E2", "E2 leave-one-project-out"),
             ("unseen_E1", "Unseen tests (E1 subset)")]

    # Cross-check: original-history values equal the frozen results, and the
    # unseen-test values agree with posthoc_extra.json.
    for arm, _, _, _ in ARMS:
        for e in ("E1", "E2"):
            check_close(r1["original"][e]["arms"][arm]["mcc"],
                        results["evaluations"][e]["arms"][arm]["mcc"], f"{e} {arm}")
        for v in ("original", "strict"):
            check_close(r1[v]["unseen_E1"]["arms"][arm]["mcc"],
                        posthoc[v]["unseen_E1"]["arms"][arm]["mcc"], f"unseen {v} {arm}")
    out = {(e, arm): (r1["original"][e]["arms"][arm]["mcc"], r1["strict"][e]["arms"][arm]["mcc"])
           for e, _ in evals for arm, _, _, _ in ARMS}
    if not draw:
        return out

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 3.0))
    rows, labels = [], []
    ypos = 0
    for e, title in evals:
        start = ypos
        for arm, name, colour, marker in ARMS:
            o, s = out[(e, arm)]
            ax.plot([o, s], [ypos, ypos], color=colour, lw=1.0, zorder=1)
            ax.scatter([o], [ypos], s=22, marker=marker, facecolor="white",
                       edgecolor=colour, lw=1.0, zorder=2)
            ax.scatter([s], [ypos], s=22, marker=marker, color=colour, zorder=3)
            ax.text(1.0, ypos, f"{fmt(o)} → {fmt(s)}", va="center", ha="right",
                    fontsize=6.0, color=OI["black"])
            labels.append(name)
            rows.append(ypos)
            ypos += 1
        ax.text(-0.5, start - 0.75, title, fontsize=6.8, weight="bold", ha="left",
                va="center")
        ypos += 1.2

    ax.axvline(0, color=OI["grey"], lw=0.6, ls=":", zorder=0)
    ax.set_yticks(rows)
    ax.set_yticklabels(labels)
    ax.set_ylim(ypos - 0.7, -1.4)
    ax.set_xlim(-0.5, 1.0)
    ax.set_xlabel("MCC")
    from matplotlib.lines import Line2D

    handles = [
        Line2D([], [], marker="o", ls="", mfc="white", mec=OI["black"], ms=4.5,
               label="original history"),
        Line2D([], [], marker="o", ls="", color=OI["black"], ms=4.5,
               label="strict history (post hoc)"),
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=2,
              frameon=False)
    save(fig, "fig3_mcc_original_vs_strict")
    return out


# --------------------------------------------------------------------------
# Figure 4: per-project unseen-test MCC, strict history


def fig_unseen_per_project(posthoc, draw=True):
    pp = posthoc["strict"]["unseen_E1_per_project"]
    repos = sorted(pp, key=lambda r: pp[r]["n"])
    if not draw:
        return pp
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.9))
    offsets = {"MDF-paper-int": -0.22, "KNN8-float": 0.0, "ET-BF": 0.22}
    for i, repo in enumerate(repos):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color="#F4F4F4", zorder=0, lw=0)
        for arm, name, colour, marker in ARMS:
            ax.scatter([pp[repo][arm]], [i + offsets[arm]], marker=marker, s=20,
                       color=colour, label=name if i == 0 else None, zorder=3)
    ax.axvline(0, color=OI["grey"], lw=0.6, ls=":", zorder=1)
    ax.set_yticks(range(len(repos)))
    ax.set_yticklabels([f"{short(r)}\n(n={pp[r]['n']}, {pp[r]['flaky']} flaky)" for r in repos],
                       fontsize=6.2)
    ax.set_ylim(-0.6, len(repos) - 0.4)
    ax.set_xlim(-1.05, 1.05)
    ax.set_xlabel("MCC on unseen tests, strict history (post hoc)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False,
              handletextpad=0.3, columnspacing=1.0)
    save(fig, "fig4_unseen_per_project")
    return pp


# --------------------------------------------------------------------------
# Figure 5: SHAP global ranking, original vs strict


def fig_shap(robust, draw=True):
    r2 = robust["R2_shap_E1"]
    orig = {d["feature"]: d["mean_abs_shap"] for d in r2["original"]["global_mean_abs_shap"]}
    strict = {d["feature"]: d["mean_abs_shap"] for d in r2["strict"]["global_mean_abs_shap"]}
    if set(orig) != set(strict):
        raise SystemExit("SHAP feature sets differ between original and strict")
    rank_o = {f: i + 1 for i, f in enumerate(sorted(orig, key=lambda f: -orig[f]))}
    rank_s = {f: i + 1 for i, f in enumerate(sorted(strict, key=lambda f: -strict[f]))}
    feats = sorted(orig, key=lambda f: -orig[f])
    if not draw:
        return orig, strict, rank_o, rank_s, r2

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 4.1))
    h = 0.38
    y = list(range(len(feats)))
    ax.barh([i - h / 2 for i in y], [orig[f] for f in feats], height=h,
            color=OI["orange"], label="original history")
    ax.barh([i + h / 2 for i in y], [strict[f] for f in feats], height=h,
            color=OI["blue"], label="strict history (post hoc)")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{f} ({rank_o[f]}→{rank_s[f]})" for f in feats], fontsize=6.0)
    ax.invert_yaxis()
    ax.set_xlabel("Mean |SHAP value| (ET-BF, E1 test part)")
    ax.legend(loc="lower right", frameon=False)
    save(fig, "fig5_shap_ranking")
    return orig, strict, rank_o, rank_s, r2


# --------------------------------------------------------------------------
# Captions


def write_captions(f1, f2, f3, pp, shap, diagnostics):
    orig, strict, rank_o, rank_s, r2 = shap
    top_o = min(rank_o, key=rank_o.get)
    top_s = min(rank_s, key=rank_s.get)
    d5 = diagnostics["D5_unseen_tests_E1"]
    check_close(d5["ETBF"], f3[("unseen_E1", "ET-BF")][0], "D5 unseen ET-BF")
    e_s = f3[("unseen_E1", "ET-BF")][1]
    m_s = f3[("unseen_E1", "MDF-paper-int")][1]
    k_s = f3[("unseen_E1", "KNN8-float")][1]
    shown = len(orig)

    lines = [
        "# Figure captions",
        "",
        "Generated by `paper/figures/make_figures.py` from "
        f"`{SOURCE}/` (results.json, robustness.json, diagnostics.json, posthoc_extra.json, "
        "labels_summary.json). Do not edit numbers by hand; re-run the script.",
        "",
        "**Figure 1.** Study pipeline. Failed test executions from GitHub Actions CI logs give "
        f"{f1['candidates']:,} candidate failures with rerun results in {f1['projects']} projects. "
        "Each is rerun 30 times on the commit CI tested; a failure is flaky if at least one rerun "
        f"passes and not flaky if all 30 fail ({f1['flaky']:,} flaky, {f1['not_flaky']:,} not "
        f"flaky, {f1['unlabelled']:,} unlabelled and reported). Feature sets B (MDFlaker's factors), "
        "F (failure evidence) and C (static test context, ET-BFC only) feed the compared models, "
        f"which are evaluated time-ordered within project (E1, test n = {f1['e1_n']}, "
        f"{f1['e1_flaky']} flaky), leave-one-project-out (E2, n = {f1['e2_n']:,}, "
        f"{f1['e2_flaky']} flaky) and on unseen tests (E1 test failures whose test is not in "
        f"training, n = {f1['unseen_n']}, {f1['unseen_flaky']} flaky). The unseen-test subset and "
        "the strict-history variant are post hoc (dashed and italic). "
        f"Source: `labels_summary.json`, `results.json`, `posthoc_extra.json`.",
        "",
        "**Figure 2.** Labelled test failures per project (light) and the flaky failures among "
        f"them (dark), with flaky/labelled counts and rate. Total {f2['labelled']:,} labelled, "
        f"{f2['flaky']} flaky. Source: `results.json` (projects), checked against "
        "`labels_summary.json`.",
        "",
        "**Figure 3.** MCC with the original flaky-frequency history (open markers, the frozen "
        "features) and with strict history, which counts only earlier workflow runs (filled "
        "markers), for MDFlaker (MDF-paper-int), KNN8 "
        "(KNN8-float) and ET-BF on E1, E2 and unseen tests. The strict-history runs and the "
        "unseen-test subset are post hoc analyses outside the frozen decision rule. On unseen "
        f"tests under strict history, ET-BF reaches MCC {fmt(e_s)} against {fmt(m_s)} for "
        f"MDFlaker and {fmt(k_s)} for KNN8. Source: `robustness.json` R1_strict_history; "
        "original-history E1/E2 values equal `results.json`.",
        "",
        "**Figure 4.** Per-project MCC on unseen tests under strict history (post hoc) for "
        "MDFlaker, KNN8 and ET-BF. Per-project subsets are small (n and flaky count on each row), "
        "so single-project MCC values are unstable; an MCC of 0 can mean the model predicted "
        "one class only. Source: `posthoc_extra.json` strict.unseen_E1_per_project.",
        "",
        f"**Figure 5.** Global SHAP ranking (mean |SHAP value|) of all {shown} ET-BF features on "
        f"the E1 test part (n = {r2['original']['test']}; trained on {r2['original']['train']}), "
        "with original history (orange) and strict history (blue, post hoc). Labels give the "
        f"rank under original → strict history. The top feature moves from `{top_o}` to "
        f"`{top_s}`; `flaky_frequency` falls from rank {rank_o['flaky_frequency']} to "
        f"{rank_s['flaky_frequency']}. SHAP {r2['shap_version']} TreeExplainer. Source: "
        "`robustness.json` R2_shap_E1.",
        "",
    ]
    (HERE / "CAPTIONS.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    results = load("results.json")
    robust = load("robustness.json")
    diagnostics = load("diagnostics.json")
    posthoc = load("posthoc_extra.json")
    labels = load("labels_summary.json")

    draw = "--captions-only" not in sys.argv[1:]
    if draw:
        setup_matplotlib()

    f1 = fig_pipeline(labels, results, posthoc, draw)
    f2 = fig_projects(results, labels, draw)
    f3 = fig_original_vs_strict(robust, results, posthoc, draw)
    pp = fig_unseen_per_project(posthoc, draw)
    shap = fig_shap(robust, draw)
    write_captions(f1, f2, f3, pp, shap, diagnostics)
    print("Wrote", "CAPTIONS.md" if not draw else "figures and CAPTIONS.md", "to", HERE)


if __name__ == "__main__":
    main()
