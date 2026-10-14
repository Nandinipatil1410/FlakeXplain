"""Generate the guide-facing dataset card from verified exports only."""
import csv
import gzip
import json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dataset/v0.1'

def read(name):
    opener=gzip.open if name.endswith('.gz') else open
    with opener(OUT/name,'rt',encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def main():
    m=json.loads((OUT/'manifest.json').read_text())
    validation=json.loads((OUT/'validation.json').read_text())
    if validation['status']!='passed':
        raise ValueError('Validate the dataset before reporting')
    projects=read('project_summary.csv'); metadata=read('metadata.csv.gz'); labels=read('labels.csv.gz')
    schema=json.loads((OUT/'schema.json').read_text())
    by_id={r['example_id']:r for r in metadata}
    positives={r['example_id'] for r in labels if r['label']=='1'}
    positive_families={by_id[k]['source_family_id'] for k in positives}
    positive_projects={by_id[k]['project'] for k in positives}
    observations=Counter(r['effective_n'] for r in labels)
    unresolved=Counter(); bounded=0
    with gzip.open(OUT/'contexts.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            c=json.loads(line)
            unresolved.update(c['unresolved_fixture_references']); bounded+=c['bounded']
    reviews_path=ROOT/'reports/dataset-preparation/static_review.json'
    reviews=json.loads(reviews_path.read_text()) if reviews_path.exists() else {'reviews':[]}
    excluded=read('source_exclusions.csv.gz')
    candidate_positives=m['observed_flaky']+sum(r['label']=='observed_flaky' for r in excluded)
    stats={
        'cases':m['model_cases'],'observed_flaky':m['observed_flaky'],
        'not_observed_flaky':m['model_cases']-m['observed_flaky'],
        'observed_flaky_percent':100*m['observed_flaky']/m['model_cases'],
        'source_coverage_percent':100*m['model_cases']/m['candidate_cases'],
        'positive_source_coverage_percent':100*m['observed_flaky']/candidate_positives,
        'positive_source_families':len(positive_families),'positive_projects':len(positive_projects),
        'with_context_cases':sum(int(p['with_context']) for p in projects),
        'unresolved_fixture_candidate_cases':sum(int(p['unresolved_fixture_cases']) for p in projects),
        'bounded_context_cases':sum(int(p['bounded_cases']) for p in projects),
        'effective_n_distribution':dict(observations),
        'predictor_counts':{k:len(v) for k,v in schema['predictor_tables'].items()},
        'additional_projects':[p['project'] for p in projects if p['membership']=='additional'],
        'static_review_cases':len(reviews['reviews'])}
    lines=['# FlakeXplain dataset v0.1 — guide and pilot dataset card','',
        '**Status: implemented and automatically validated pilot dataset. No model has been trained in this preparation step.**','',
        '## Verified size and scope','',
        f"- {m['projects']} projects: all 30 CANNIER subjects (SunPy and urllib3 at changed revisions), plus {', '.join(stats['additional_projects'])}.",
        f"- Audited evidence candidates: {m['candidate_cases']:,}; uniquely source-mapped model cases: **{m['model_cases']:,}** ({stats['source_coverage_percent']:.2f}% coverage).",
        f"- **{m['observed_flaky']:,} observed-flaky** and **{stats['not_observed_flaky']:,} not-observed-flaky** cases; natural positive rate **{stats['observed_flaky_percent']:.4f}%**. No synthetic balancing or duplication.",
        f"- {m['source_families']:,} defining source-function families; {len(positive_families):,} positive source families across {len(positive_projects)} positive projects. Parameter cases and inherited collections share family identifiers; they are not independent causal examples.",
        f"- Effective detection observations per case: {dict(sorted(observations.items()))}. Baseline observations are not counted in N.",
        f"- {m['source_exclusions']:,} candidate cases, including {candidate_positives-m['observed_flaky']} observed positives, lack the required unique Python function join. They remain in source_exclusions.csv.gz and the evidence corpus. Rules are applied without selecting on the label.",
        '- Excluded positives: 13 generated Airflow cases, one SunPy documentation case and eight Xonsh-language cases. Non-Python tests and generated functions are outside this extractor version. This selection can affect prevalence and difficulty.','',
        '## Target and evidence','',
        'The target is outcome instability observed under the recorded protocol: at least one PASS and one FAIL/ERROR. The negative class means all-pass after its recorded N observations, with no skip, missing or duplicate rounds. It does not establish permanent non-flakiness. Legacy click/flask/fsspec, baseline-failed httpx and ambiguous identities remain outside the primary evidence cohort.',
        '',
        'All 1,168 frozen evidence files were rehashed successfully. Source archives are pinned to the recorded full commits; every extracted Python file was checked against its archive. Selected test and context source hashes are validated again in the exported artifact. Derived source node IDs are provided; original collection/execution order is not reconstructed.',
        '',
        'pytest-randomly changes runtime seeds as well as order. These data support observed-instability prediction; OD/NOD patterns are provisional and are not classifier inputs. Fresh execution labels are not interchangeable with the authors’ released CANNIER labels.','',
        '## Tables and safe model inputs','',
        '| File | Purpose |','|---|---|',
        '| labels.csv.gz | Binary target, effective N, outcome evidence and configuration-specific counts. Never a predictor table. |',
        '| metadata.csv.gz | Project, revision, environment, original JUnit identity, parameter suffix, source identity/location/hash, family and context joins. Never a predictor table. |',
        '| features_body.csv.gz | 22 numeric AST features from the test body. example_id is a join key, not an input. |',
        '| features_context.csv.gz | 33 added static features: fixture/helper/lifecycle counts, scope/autouse/dependency structure and aggregated context AST features. |',
        '| contexts.jsonl.gz | Source-linked context nodes, edges, bounds and unresolved-reference audit. Never a predictor table. |',
        '| splits_outer.csv / splits_inner.csv | Fixed project groups for five outer folds and four inner folds within each outer training cohort. |',
        '| source_exclusions.csv.gz / source_parse_errors.csv | Explicit source joins and parser limitations excluded from the model subset. |',
        '| source_manifest.json / manifest.json / schema.json / validation.json | Source provenance, checksums, predictor allowlists and validation result. |',
        '| manual_review_queue.csv | Deterministic broader review queue; pending rows do not imply human validation. |','',
        'Both planned Extra Trees ablations use exactly the same examples and outer/inner splits: body features versus body plus context (55 predictors). Outcome counts, patterns, seed values, JUnit durations, provenance and identifiers are prohibited as inputs. Fit preprocessing, tuning and thresholds only inside the corresponding training folds. No scaling, feature selection, imputation, vocabulary or model fitting was performed here.','',
        '## Context coverage and limitations','',
        f"{stats['with_context_cases']:,} cases have at least one resolved context node. {stats['unresolved_fixture_candidate_cases']:,} cases have unresolved candidate fixture references; {stats['bounded_context_cases']:,} reach a context bound. These counts are audit metadata, excluded from predictors.",
        '',
        'Implemented: nearest ancestor conftest/module/class fixture precedence, imported repository fixtures, literal usefixtures/parametrize, applicable autouse fixture names, fixture dependencies, selected named helpers and xunit/unittest lifecycle methods. Limits: fixture depth 4, helper depth 2 and 32 unique context functions. This is potential static context, not a runtime trace.',
        '',
        'Third-party fixtures and pytest_plugins registries are not expanded. Overridden fixtures depending on their own name are flagged rather than guessed. Hypothesis/mocking decorator-injected arguments can appear among unresolved candidate fixtures. Dynamic collection/dispatch, local/nested generated definitions, re-export chains, class/module initialization state, runtime conftest loading restrictions, stringified subprocess code and complete object call graphs are not resolved. Zero unresolved names does not prove complete context. Lexical call-category features are heuristics; they do not identify failure causes.',
        '',
        f"AI-assisted static spot review covers {len(reviews['reviews'])} cases (12 positives, four negatives) across 12 projects; see reports/dataset-preparation/static_review.json. It checks named source joins and selected context, not causal labels or complete runtime fixture graphs. The broader review queue and human cause annotation remain pending.",
        '',
        '## Evaluation split freeze','',
        '| Outer fold | Projects | Cases | Observed flaky |','|---|---:|---:|---:|']
    for f in m['folds']:
        lines.append(f"| {f['fold']} | {len(f['projects'])} | {f['cases']:,} | {f['positives']:,} |")
    lines += ['',schema['split_policy'],
        '',f"Substantive exact AST body families shared across projects: {m['cross_project_duplicate_bodies']}; any detected groups are kept together. Common bodies below three statements/20 AST nodes are not used to connect projects. Near-duplicate and fork genealogy audits remain incomplete; no claim of full benchmark independence is made.",
        '', 'Additional projects influenced preparation. Evaluate them with the same project-disjoint procedure; describe a later CANNIER-only training/additional-project evaluation as a secondary analysis, not untouched external validation. Airflow contributes many positives; report project-level and source-family-sensitive metrics rather than treating cases as independent.','',
        '## Reproduction','', 'From the repository root, with Python 3.11 and standard-library dependencies:', '', '```powershell',
        'python scripts/fetch_dataset_sources.py',
        r"python scripts/verify_frozen_evidence.py --repos-dir 'G:\My Drive\Academics\Final Year Project\repos'",
        'python scripts/prepare_dataset.py','python scripts/validate_dataset.py','python scripts/report_dataset.py','```','',
        'Raw workflow evidence and pinned third-party sources remain in local storage and are not embedded in the feature export. Network access is required to recreate source caches. Retain the evidence recovery reports and original archives. Verify upstream licences before releasing source snippets or third-party artifacts. Numerical tables and source references here do not grant upstream redistribution rights.','',
        '## Ready now and remaining work','',
        f"Automated dataset validation passed {len(validation['checks'])} checks. Repository unit tests passed (one platform-specific check skipped on Windows). Dataset preparation is ready for a bounded pilot using the declared limitations. Model results, performance improvements, CANNIER-compatible reproduction, causal annotation, broad human review and submission readiness are not established.",'']
    (OUT/'DATASET_CARD.md').write_text('\n'.join(lines),encoding='utf-8')
    definitions='''# Static feature definitions

Only the numeric columns allowlisted in schema.json are predictors. All counts are computed from source ASTs without importing subjects. No execution result is read by the feature functions.

The body tree contains the function's statements, excluding its decorators and signature. Nested function/class bodies and docstring expression nodes are included by ast.walk. `lines` is the inclusive span from the def line to the final function line, including the signature and any intervening blank/comment lines. This span is a size proxy.

| Feature suffix | Definition |
|---|---|
| lines | Inclusive function span described above |
| statements | ast.stmt nodes, including nested statements |
| calls | ast.Call nodes |
| asserts | ast.Assert statements; unittest assertion method calls are calls, not ast.Assert |
| branches | ast.If and ast.IfExp nodes |
| loops | ast.For, ast.AsyncFor, ast.While nodes |
| try_blocks | ast.Try nodes |
| raises | ast.Raise nodes |
| with_blocks | ast.With and ast.AsyncWith nodes |
| awaits | ast.Await nodes |
| yields | ast.Yield and ast.YieldFrom nodes |
| imports | ast.Import and ast.ImportFrom statements |
| globals | ast.Global and ast.Nonlocal statements |
| mutable_literals | ast.List, ast.Dict, ast.Set nodes |
| comprehensions | ListComp, SetComp, DictComp, GeneratorExp nodes |

The seven call categories count calls whose syntactic dotted name contains at least one listed exact token after lowercasing. Each call counts at most once in each category; categories can overlap. This is a lexical proxy, not semantic type inference. Unnamed/subscripted callables are not reliably identified.

| Category | Tokens |
|---|---|
| time_calls | time, sleep, datetime, monotonic, perf_counter, now, utcnow |
| random_calls | random, randint, choice, shuffle, seed, uuid4 |
| filesystem_calls | open, mkdir, unlink, remove, write_text, read_text, chdir, mkstemp |
| network_calls | socket, requests, urlopen, connect, httpx, getaddrinfo |
| mock_calls | patch, monkeypatch, mock, magicmock, setattr, setenv |
| process_calls | subprocess, popen, multiprocessing, thread, start, system |
| finalizer_calls | addfinalizer |

`body_` prefixes denote test-body measurements. `context_` prefixes sum the same 22 measurements over unique selected context functions. A selected function is counted once per context, even if multiple references reach it. The original test function is excluded from its context.

Additional context columns count unique fixture/helper/lifecycle nodes, statically autouse-decorated selected fixtures, selected fixtures by declared scope (function/class/module/package/session/other), and distinct fixture dependency edges whose parent is not the test body. Scope `other` includes dynamic/nonstandard declarations. No effective runtime execution count, runtime seed value, fixture timing, failure subtype or outcome is used.

The definitions intentionally omit parameter values, test-name tokens, project identifiers, source hashes, unresolved-count flags and bound flags from predictors. Those fields remain audit metadata. Both planned ablations use the same case join and project splits.
'''
    (OUT/'FEATURE_DEFINITIONS.md').write_text(definitions,encoding='utf-8')
    report_dir=ROOT/'reports/dataset-preparation'; report_dir.mkdir(parents=True,exist_ok=True)
    (report_dir/'statistics.json').write_text(json.dumps(stats,indent=2)+'\n')
    report=['# Dataset preparation report','',f"Implemented and validated: **{m['model_cases']:,} cases across {m['projects']} projects**, with **{m['observed_flaky']} observed-flaky cases** and **{stats['not_observed_flaky']:,} not-observed-flaky cases**.",'',
        'See [the dataset card](../../dataset/v0.1/DATASET_CARD.md) for labels, context coverage, feature definitions, split sizes, exclusions, reproduction and research limits. Machine-readable per-project totals are in [project_summary.csv](../../dataset/v0.1/project_summary.csv).','',
        'No model training was performed. The intended next pilot compares Extra Trees on test-body features against the same training procedure with fixture/helper/lifecycle context, using identical examples and frozen project-separated folds.','']
    (report_dir/'DATASET_PREPARATION_REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(stats,indent=2))

if __name__=='__main__':
    main()
