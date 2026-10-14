"""Read imported evidence without running subjects; export auditable descriptive counts.

JUnit identities retain file, classname, and parameterized name. They are not
claimed to be canonical pytest node IDs or resolved source-function identities.
"""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import json
import random
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ('original', 'random', 'reverse')
SYMBOLS = {'PASS': 'P', 'FAIL': 'F', 'ERROR': 'E', 'SKIP': 'S', 'DUPLICATE': 'D'}


def read_json(path, issues):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        issues.append(f'Invalid JSON {path.name}: {type(exc).__name__}')
        return {}


def parse_junit(path):
    """Keep class identity and quarantine repeated testcase identities per XML."""
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag not in ('testsuite', 'testsuites'):
        raise ValueError('Not a JUnit testsuite/testsuites document')
    cases = defaultdict(list)
    raw = Counter()
    missing = 0
    for tc in root.iter('testcase'):
        identity = tuple(tc.get(k, '') for k in ('file', 'classname', 'name'))
        status = ('FAIL' if tc.find('failure') is not None else
                  'ERROR' if tc.find('error') is not None else
                  'SKIP' if tc.find('skipped') is not None else 'PASS')
        # pytest emits named module-collection skips without classname/file.
        # Retain those skip records; they never become a binary target.
        if not identity[2] or (not (identity[0] or identity[1]) and status != 'SKIP'):
            missing += 1
        raw[status] += 1
        cases[identity].append(status)
    if not cases:
        raise ValueError('No testcase observations')
    outcomes = {key: values[0] if len(values) == 1 else 'DUPLICATE'
                for key, values in cases.items()}
    return outcomes, raw, missing


def label_outcomes(values):
    active = set(values) - {'SKIP', 'MISSING'}
    if 'DUPLICATE' in active:
        return 'ambiguous_duplicate'
    if 'PASS' in active and active & {'FAIL', 'ERROR'}:
        return 'observed_flaky'
    if active == {'PASS'}:
        return 'not_observed_flaky' if set(values) == {'PASS'} else 'pass_with_skips_or_missing'
    if active & {'FAIL', 'ERROR'}:
        return 'failure_only'
    return 'skip_only'


def normalize(name):
    return re.sub('[^a-z0-9]', '', name.lower())


def configured_names():
    tree = ast.parse((ROOT / 'scripts/runtime.py').read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REPOS' for t in node.targets):
            return ast.literal_eval(node.value)
    return []


def csv_writer(path, fields, compressed=False):
    handle = gzip.open(path, 'wt', encoding='utf-8', newline='') if compressed else path.open('w', encoding='utf-8', newline='')
    writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    return handle, writer


def audit_project(repo, writers, inventory, resolution=None, source_root=None):
    rounds_writer, tests_writer, hashes_writer = writers
    issues = []
    hashed = set()

    def hash_file(path):
        if path.is_file() and path not in hashed:
            hashed.add(path)
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
            hashes_writer.writerow(dict(project=repo.name, evidence_path=path.relative_to(repo).as_posix(), bytes=path.stat().st_size, sha256=h.hexdigest()))

    for name in ('environment.json', 'baseline_state.json', 'setup_state.json', 'setup_log.md',
                 'env_snapshot.txt', 'cannier_setup_recipe.json', 'cannier_dependency_snapshot.txt'):
        hash_file(repo / name)
    manifest_path = repo / 'results/execution_manifest.json'
    hash_file(manifest_path)
    manifest = read_json(manifest_path, issues)
    baseline = read_json(repo / 'baseline_state.json', issues)
    environment = read_json(repo / 'environment.json', issues)
    embedded = manifest.get('environment', {})
    commit = environment.get('commit', embedded.get('commit', 'UNKNOWN'))
    log = (repo / 'setup_log.md').read_text(encoding='utf-8-sig', errors='replace') if (repo / 'setup_log.md').exists() else ''
    if commit == 'UNKNOWN':
        match = re.search(r'Pinned Commit Hash[^:]*:\s*`?([a-f0-9]{7,40})', log)
        if match:
            commit = match[1]
    exclusion_identities = {}
    exclusion_functions = {}
    resolution_verified = False
    if resolution:
        errors = []
        if resolution.get('commit') != commit:
            errors.append('Resolution policy commit does not match evidence')
        if not source_root or not resolution.get('source_evidence'):
            errors.append('Resolution policy requires pinned source files and hashes')
        else:
            for source in resolution['source_evidence']:
                path = source_root / source['path']
                if source_root.resolve() not in path.resolve().parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
                    errors.append('Resolution source hash missing/mismatched: ' + source['path'])
        if errors:
            issues.extend(errors)
        else:
            resolution_verified = True
            exclusion_identities = {tuple(r['identity']): r['reason'] for r in resolution.get('excluded_identities', [])}
            exclusion_functions = {(r['classname'], r['function']): r['reason'] for r in resolution.get('excluded_functions', [])}

    def exclusion_reason(identity):
        return exclusion_identities.get(identity) or exclusion_functions.get((identity[1], identity[2].split('[', 1)[0]), '')

    def retained(outcomes):
        return {key: value for key, value in outcomes.items() if not exclusion_reason(key)}

    def invalid_identity(outcomes):
        return any(not key[2] or (not (key[0] or key[1]) and value != 'SKIP') for key, value in outcomes.items())
    baseline_text = baseline.get('status', 'UNKNOWN')
    if baseline_text == 'UNKNOWN':
        match = re.search(r'Baseline Gate Status[^:]*:\s*(.+)', log)
        if match:
            baseline_text = match[1].strip('` ')
    member = inventory.get(normalize(repo.name))
    membership = ('additional' if member is None else 'CANNIER same revision' if commit == member['commit'] else 'CANNIER changed/unknown revision')
    modern = bool(manifest.get('environment_id'))
    baseline_valid = False
    baseline_ids = set()
    if modern:
        if baseline.get('status') != 'PASSED' or baseline.get('environment_id') != manifest['environment_id']:
            issues.append('Baseline status/environment does not match manifest')
        elif environment.get('id') != manifest['environment_id'] or embedded.get('id') != manifest['environment_id']:
            issues.append('Environment metadata ID mismatch or absent')
        elif environment != embedded:
            issues.append('Standalone and embedded environment snapshots differ')
        else:
            relative = baseline.get('xml_file', '').replace('\\', '/')
            path = repo / relative
            if not relative or not path.is_file() or repo.resolve() not in path.resolve().parents:
                issues.append('Passing baseline XML missing or unsafe path')
            else:
                hash_file(path)
                try:
                    outcomes, counts, missing = parse_junit(path)
                    eligible_outcomes = retained(outcomes)
                    baseline_ids = set(eligible_outcomes)
                    baseline_valid = (bool(eligible_outcomes) and sum(counts.values()) == baseline.get('collected_count') == manifest.get('collected_count')
                                      and not counts['FAIL'] and not counts['ERROR'] and not invalid_identity(eligible_outcomes)
                                      and 'DUPLICATE' not in eligible_outcomes.values())
                    if not baseline_valid:
                        issues.append('Passing baseline XML counts/outcomes/identities invalid')
                except (ET.ParseError, ValueError, OSError) as exc:
                    issues.append(f'Invalid passing baseline XML: {type(exc).__name__}')
    else:
        issues.append('Recorded baseline failed; excluded without detection rounds' if baseline.get('status') == 'FAILED'
                      else 'Legacy/missing environment-bound manifest and passing baseline XML verification')

    records = []
    for config in CONFIGS:
        values = manifest.get(config + '_rounds', [])
        if config == 'reverse' and 'reverse_rounds' not in manifest:
            values = [manifest['reverse_round']] if manifest.get('reverse_round') else []
        for record in values:
            records.append((config, record))
    files = sorted((repo / 'results').glob('*_run_*.xml'))
    tracked = {r.get('xml_file') for _, r in records}
    if modern:
        extras = [p.name for p in files if p.name not in tracked]
        if extras:
            issues.append('Uncheckpointed XML excluded: ' + ', '.join(extras))
    else:
        # Legacy counts are explicitly descriptive; no fabricated checkpoint records.
        records = [(p.name.split('_')[0], dict(xml_file=p.name)) for p in files]
    series = []
    round_counts = Counter()
    raw_totals = Counter()
    duration = 0.0
    failed_rounds = Counter()
    seen = set()
    seeds = random.Random(42 + len(repo.name))
    expected_seeds = {n: seeds.randint(100000, 999999) for n in range(1, 13)}
    def round_key(item):
        match = re.search(r'(\d+)\.xml$', item[1].get('xml_file', ''))
        number = item[1].get('round')
        return CONFIGS.index(item[0]), number if isinstance(number, int) else int(match[1]) if match else 0
    for config, record in sorted(records, key=round_key):
        filename = record.get('xml_file', '')
        path = repo / 'results' / filename
        entry = dict(project=repo.name, config=config, round=record.get('round'), xml_file=filename,
                     exit_code=record.get('exit_code'), seed=record.get('seed'), duration_seconds=record.get('duration_seconds'), valid=False)
        problems = []
        if not filename or Path(filename).name != filename or filename in seen:
            problems.append('Unsafe/missing/repeated round filename')
        seen.add(filename)
        if modern:
            number = record.get('round')
            if record.get('config') != config + '-order' or filename != f'{config}_run_{number}.xml':
                problems.append('Round configuration/name mismatch')
            if record.get('exit_code') not in (0, 1):
                problems.append('Invalid round exit code')
            if config == 'random' and (number not in expected_seeds or record.get('seed') != expected_seeds.get(number)):
                problems.append('Random seed does not match runner plan')
            if config != 'random' and record.get('seed') is not None:
                problems.append('Unexpected seed for original/reverse round')
        try:
            if problems:
                raise ValueError('; '.join(problems))
            hash_file(path)
            outcomes, counts, missing = parse_junit(path)
            eligible_outcomes = retained(outcomes)
            entry.update(testcase_rows=sum(counts.values()), unique_identities=len(outcomes), **{k.lower(): counts[k] for k in ('PASS', 'FAIL', 'ERROR', 'SKIP')})
            if modern and sum(counts.values()) != manifest.get('collected_count'):
                problems.append('Raw testcase row count differs from manifest')
            if modern and baseline_ids and set(eligible_outcomes) != baseline_ids:
                problems.append('Retained identity set differs from passing baseline')
            if 'DUPLICATE' in eligible_outcomes.values():
                problems.append('Repeated JUnit identity (ambiguous phases or duplicates)')
            if invalid_identity(eligible_outcomes):
                problems.append('Testcase lacks name or file/class identity')
            if modern and record.get('exit_code') == 0 and (counts['FAIL'] or counts['ERROR']):
                problems.append('Exit 0 contradicts failed/error testcase')
            # Preserve parsed ambiguous rounds descriptively, while withholding protocol acceptance.
            series.append((config, filename, outcomes))
            round_counts[config] += 1
            raw_totals.update(counts)
            if counts['FAIL'] or counts['ERROR']:
                failed_rounds[config] += 1
            duration += float(record.get('duration_seconds') or 0)
            entry['valid'] = not problems
        except (ET.ParseError, ValueError, OSError) as exc:
            problems.append(f'{type(exc).__name__}: {str(exc)[:160]}')
        entry['issues'] = '; '.join(problems)
        rounds_writer.writerow(entry)
        if problems:
            issues.append(filename + ': ' + '; '.join(problems))
    identities = set().union(*(set(values) for _, _, values in series)) if series else set()
    labels = Counter()
    eligible_labels = Counter()
    exclusion_counts = Counter()
    patterns = Counter()
    effective = Counter()
    for identity in sorted(identities):
        values = [outcomes.get(identity, 'MISSING') for _, _, outcomes in series]
        label = label_outcomes(values)
        labels[label] += 1
        reason = exclusion_reason(identity)
        if reason:
            exclusion_counts[reason] += 1
        else:
            eligible_labels[label] += 1
        counts = Counter(values)
        effective[counts['PASS'] + counts['FAIL'] + counts['ERROR']] += 1
        by_config = {c: Counter(v for v, (cfg, _, _) in zip(values, series) if cfg == c) for c in CONFIGS}
        pattern = ''
        if label == 'observed_flaky':
            original = by_config['original']
            if original['PASS'] and (original['FAIL'] or original['ERROR']):
                pattern = 'mixed_original_outcomes'
            elif original['FAIL'] or original['ERROR']:
                pattern = 'original_failure_pass_elsewhere'
            elif original['PASS']:
                pattern = 'failure_only_in_reordered_configuration'
            else:
                pattern = 'unclassified_configuration_pattern'
            patterns[pattern] += 1
        tests_writer.writerow(dict(project=repo.name, commit=commit, file=identity[0], classname=identity[1], name=identity[2],
            label=label, pattern=pattern, pass_count=counts['PASS'], fail_count=counts['FAIL'], error_count=counts['ERROR'],
            skip_count=counts['SKIP'], missing_count=counts['MISSING'], duplicate_rounds=counts['DUPLICATE'],
            effective_n=counts['PASS'] + counts['FAIL'] + counts['ERROR'],
            eligible_identity=not bool(reason), exclusion_reason=reason,
            outcomes=''.join(SYMBOLS.get(v, 'M') for v in values)))
    complete_plan = (round_counts['original'] == 12 and round_counts['random'] == 12 and round_counts['reverse'] in (1, 3)
                     and all({r.get('round') for c, r in records if c == config} == set(range(1, round_counts[config] + 1)) for config in CONFIGS))
    if not series:
        status = 'baseline_failed' if str(baseline_text).startswith('FAILED') else 'no_detection_evidence'
    elif not modern:
        status = 'legacy_unverified'
    elif not issues and baseline_valid and complete_plan:
        status = 'protocol_complete_with_exclusions' if exclusion_counts else 'protocol_complete_local_checks'
    else:
        status = 'incomplete_or_ambiguous'
        if not complete_plan:
            issues.append('Expected 12 original + 12 random + 1 (or recorded 3) reverse rounds not verified')
    labelled = labels['observed_flaky'] + labels['not_observed_flaky']
    # This descriptive denominator also includes pass+skip cases; primary negatives are stricter.
    descriptive = labelled + labels['pass_with_skips_or_missing']
    metadata = {name: (repo / name).is_file() for name in ('environment.json', 'baseline_state.json', 'setup_state.json', 'env_snapshot.txt', 'setup_log.md', 'cannier_setup_recipe.json', 'cannier_dependency_snapshot.txt')}
    return dict(project=repo.name, membership=membership, cannier_commit=member['commit'] if member else None,
        commit=commit, environment_id=manifest.get('environment_id'), python=environment.get('python', embedded.get('python')),
        platform=environment.get('platform', embedded.get('platform')), baseline_status=baseline_text,
        baseline_verified=baseline_valid, baseline_collected=baseline.get('collected_count'),
        status=status, tests=len(identities), rounds=dict(round_counts), raw_observations=dict(raw_totals),
        eligible_tests=sum(eligible_labels.values()), eligible_labels=dict(eligible_labels),
        excluded_identity_count=sum(exclusion_counts.values()), exclusion_reasons=dict(exclusion_counts), resolution_verified=resolution_verified,
        failed_rounds=dict(failed_rounds), detection_seconds=round(duration, 2) if modern else None,
        manifest_total_seconds=manifest.get('total_wall_clock_seconds'), labels=dict(labels), patterns=dict(patterns),
        effective_n_histogram=dict(sorted(effective.items())), labelled_strict=labelled,
        flaky_percentage_strict=100 * labels['observed_flaky'] / labelled if labelled else None,
        flaky_percentage_active=100 * labels['observed_flaky'] / descriptive if descriptive else None,
        metadata_present=metadata, issues=issues,
        round_order=[filename for _, filename, _ in series],
        archive_root_provenance_verified=False)


def generate_report(summaries, absent, out, generated):
    accepted = [s for s in summaries if s['status'] in ('protocol_complete_local_checks', 'protocol_complete_with_exclusions')]
    def totals(rows, eligible=True):
        labels = Counter()
        observations = Counter()
        for row in rows:
            labels.update(row.get('eligible_labels', row['labels']) if eligible else row['labels'])
            observations.update(row['raw_observations'])
        return sum(s.get('eligible_tests', s['tests']) if eligible else s['tests'] for s in rows), labels, observations
    n, labels, observations = totals(accepted)
    denominator = labels['observed_flaky'] + labels['not_observed_flaky']
    ratio = f"{100 * labels['observed_flaky'] / denominator:.4f}%" if denominator else 'undefined'
    all_n, all_labels, all_observations = totals(summaries, eligible=False)
    statuses = Counter(s['status'] for s in summaries)
    present = {normalize(s['project']) for s in summaries}
    configured_absent = [name for name in configured_names() if normalize(name) not in present]
    complete_rounds = sum(sum(s['rounds'].values()) for s in accepted)
    complete_hours = sum(s['detection_seconds'] or 0 for s in accepted) / 3600
    md = ['# Consolidated workflow evidence report', '', f'Generated {generated}. Evidence snapshot only; no subjects were rerun.', '',
          f'Inspected **{len(summaries)} imported project folders**. **{len(accepted)} pass the local protocol checks** below. '
          f'Expected but absent folders: {", ".join(absent) or "none"}.', '',
          f'Across locally protocol-complete projects: **{n:,} distinct JUnit test identities**, '
          f'**{labels["observed_flaky"]:,} observed flaky**, **{labels["not_observed_flaky"]:,} passed every detection round**, '
          f'and **{n - denominator:,} excluded from the strict binary denominator**. Observed-flaky percentage: **{ratio}**; '
          f'positive:negative ratio **{labels["observed_flaky"]:,}:{labels["not_observed_flaky"]:,}**.', '',
          f'These projects contribute **{complete_rounds:,} detection rounds** and **{complete_hours:.2f} recorded detection process-hours**, '
          'excluding baseline, setup, and scheduling overhead. Projects with three reverse rounds retain all 27 rounds.', '',
          f'Across all parsed folders, including unverified/ambiguous evidence: **{all_n:,} JUnit identities in the per-project union**, '
          f'**{all_labels["observed_flaky"]:,} observed outcome-flip identities**, **{all_labels["not_observed_flaky"]:,} all-pass identities**, '
          f'**{all_labels["pass_with_skips_or_missing"]:,} pass+skip/missing**, **{all_labels["skip_only"]:,} skip-only**, '
          f'**{all_labels["ambiguous_duplicate"]:,} duplicate identities**. These are exploratory counts, not a frozen dataset size. '
          'Changing parameter IDs inflate the union for some projects; module-collection skips also appear as JUnit records.', '',
          f'Audit categories: {statuses["protocol_complete_local_checks"]} locally protocol-complete without identity exclusions; '
          f'{statuses["protocol_complete_with_exclusions"]} complete with documented identity exclusions; '
          f'{statuses["incomplete_or_ambiguous"]} identity/other issues; {statuses["legacy_unverified"]} legacy unverified; '
          f'{statuses["no_detection_evidence"] + statuses["baseline_failed"]} without detection evidence. '
          f'Configured folders absent from this import: {", ".join(configured_absent) or "none"}.', '',
          '## Imported-folder evidence and remaining gaps', '',
          'Copying the entire artifact `repos/<project>/` folder is the right core import: retain results/execution_manifest.json, '
          'all original/random/reverse JUnit XML, logs (including baseline XML), environment.json, baseline_state.json, '
          'setup_state.json, env_snapshot.txt, setup_log.md, and any dependency snapshot/setup recipe. '
          'The packager does not include full upstream source; source must later be retrieved at the recorded commit for static features.', '',
          'Also preserve the original downloaded ZIP and its sibling/top-level provenance.json, checksums.json, and system_packages.txt, '
          'ideally in a separate directory per workflow run ID and attempt. Copying only the nested project folder omits these archive-level '
          'records. Their recovery normally requires re-extracting the download, not rerunning tests. Do not merge attempts or overwrite differing environments.', '',
          'Current project-specific recovery decisions are recorded in `reports/evidence-recovery/EVIDENCE_RECOVERY_REPORT.md`. '
          'Any `protocol_complete_with_exclusions` row retains only identities outside the commit-bound, source-hash-verified resolution rules. '
          'Original XML and original identifiers are preserved, with exclusions exported per identity. No changing parameter values are silently merged.', '',
          '## Scope and interpretation', '',
          '- Protocol-complete means a matching passing baseline XML, standalone/embedded environment identity, complete expected checkpoint records, valid XML, consistent retained JUnit identities, and expected ordering seeds. Source-verified exclusions are explicit where needed. It is a local structural audit, not a claim of fully verified archive provenance or causal validity.',
          '- Primary descriptive target: at least one PASS and one FAIL/ERROR in parsed detection rounds. Strict negatives pass every recorded detection round. PASS+SKIP/missing, skip-only, failure-only, and ambiguous duplicate identities are separated. Project-level acceptance is required before considering these labels for a primary dataset.',
          '- Baseline observations are gate evidence, excluded from detection outcome counts. Tests include parameterized JUnit cases; these are not independent source functions. File + classname + name are preserved to avoid class collisions, but canonical pytest/source mapping remains pending.',
          '- Reordered-only failures are configuration patterns, not confirmed OD. pytest-randomly may affect runtime seeds as well as order. Mixed original outcomes also do not establish a causal NOD subtype.',
          '- CANNIER membership/revision is compared against the vendored authors\' inventory. Same revision does not mean identical environment, labels, execution budget, features, or full replication.',
          '- Duration is the sum of checkpointed detection process durations, excluding setup/baseline. It is neither summed testcase time nor a measurement of hybrid-detection savings. Legacy durations are withheld.',
          '- General archive provenance remains outside this folder audit. Graphene was separately recovered with a downloaded ZIP digest matching GitHub artifact metadata and retained workflow provenance; see the recovery report. Newly computed hashes for other imported files freeze the current snapshot rather than retrospectively verifying downloads. No workflow success badge or run URL is inferred for other projects.', '',
          'Strict flaky percentage = `100 × flaky / (flaky + all-pass)`. F:N is the same unrebalanced positive:negative count ratio. '
          '`project_summary.csv` also gives an active-outcome percentage including pass+skip/missing records; this broader denominator is not the primary binary dataset.', '',
          '## Locally protocol-complete cohort by repository group', '',
          '| Group | Projects | JUnit identities | Observed flaky | All-pass | Excluded | Flaky % strict |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for group in ('CANNIER same revision', 'CANNIER changed/unknown revision', 'additional'):
        rows = [s for s in accepted if s['membership'] == group]
        size, counts, _ = totals(rows)
        den = counts['observed_flaky'] + counts['not_observed_flaky']
        pct = f'{100 * counts["observed_flaky"] / den:.4f}' if den else 'N/A'
        md.append(f'| {group} | {len(rows)} | {size:,} | {counts["observed_flaky"]:,} | {counts["not_observed_flaky"]:,} | {size-den:,} | {pct} |')
    md += ['',
          '## Per-project results', '',
          'Counts below describe all parsed identities, including exclusions and legacy evidence. Headline totals use only retained identities in the two protocol-complete categories. The eligibility table specifies the primary cohort.', '',
          '| Project | Audit status | CANNIER relation | Commit | JUnit identities (union) | O/R/Rev | Flaky | All-pass | Pass+skip/missing | Skip-only | Fail-only | Duplicate | Flaky % strict | F:N |',
          '|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for s in summaries:
        l = Counter(s['labels']); r = Counter(s['rounds'])
        pct = f'{s["flaky_percentage_strict"]:.4f}' if s['flaky_percentage_strict'] is not None else 'N/A'
        md.append(f'| {s["project"]} | {s["status"]} | {s["membership"]} | `{s["commit"][:8]}` | {s["tests"]:,} | {r["original"]}/{r["random"]}/{r["reverse"]} | {l["observed_flaky"]:,} | {l["not_observed_flaky"]:,} | {l["pass_with_skips_or_missing"]:,} | {l["skip_only"]:,} | {l["failure_only"]:,} | {l["ambiguous_duplicate"]:,} | {pct} | {l["observed_flaky"]}:{l["not_observed_flaky"]} |')
    md += ['', '## Retained identities and primary cohort eligibility', '',
           '| Project | Retained identities | Excluded identities | Eligible flaky | Eligible all-pass | Flaky % strict | Primary project eligible |',
           '|---|---:|---:|---:|---:|---:|---|']
    for s in summaries:
        l=Counter(s.get('eligible_labels',s['labels'])); den=l['observed_flaky']+l['not_observed_flaky']
        pct=f'{100*l["observed_flaky"]/den:.4f}' if den else 'N/A'
        md.append(f'| {s["project"]} | {s.get("eligible_tests",s["tests"]):,} | {s.get("excluded_identity_count",0):,} | {l["observed_flaky"]:,} | {l["not_observed_flaky"]:,} | {pct} | {"yes" if s in accepted else "no"} |')
    md += ['', '## Raw detection observations and timing', '',
           'These are repeated testcase rows, not distinct tests. Repeated identities are retained in these raw totals but quarantined from labels.', '',
           '| Project | Baseline | Recorded baseline count | PASS rows | FAIL rows | ERROR rows | SKIP rows | Rounds with FAIL/ERROR O/R/Rev | Detection hours |',
           '|---|---|---:|---:|---:|---:|---:|---|---:|']
    for s in summaries:
        o=Counter(s['raw_observations']); f=Counter(s['failed_rounds'])
        hours=f'{s["detection_seconds"]/3600:.3f}' if s['detection_seconds'] is not None else 'unverified'
        md.append(f'| {s["project"]} | {s["baseline_status"]} | {s["baseline_collected"] if s["baseline_collected"] is not None else "unavailable"} | {o["PASS"]:,} | {o["FAIL"]:,} | {o["ERROR"]:,} | {o["SKIP"]:,} | {f["original"]}/{f["random"]}/{f["reverse"]} | {hours} |')
    md += ['', '## Configuration patterns among observed flaky tests', '',
           '| Project | Mixed original outcomes | Failure only under reordering | Original failure/pass elsewhere | Other |',
           '|---|---:|---:|---:|---:|']
    for s in summaries:
        p=Counter(s['patterns'])
        md.append(f'| {s["project"]} | {p["mixed_original_outcomes"]} | {p["failure_only_in_reordered_configuration"]} | {p["original_failure_pass_elsewhere"]} | {p["unclassified_configuration_pattern"]} |')
    md += ['', '## Project audit details and effective observation budgets', '']
    for s in summaries:
        md += [f'### {s["project"]}', '', f'- Commit: `{s["commit"]}`; CANNIER inventory commit: `{s["cannier_commit"] or "not a listed subject"}`.',
               f'- Environment ID: `{s["environment_id"] or "unavailable"}`; Python: {s["python"] or "unavailable"}; platform: {s["platform"] or "unavailable"}.',
               f'- Effective non-skip observations per test (N: number of tests): `{s["effective_n_histogram"]}`.',
               '- Missing project metadata: ' + (', '.join(k for k,v in s['metadata_present'].items() if not v) or 'none') + '.',
               '- Local audit issues: ' + ('; '.join(s['issues']) or 'none found by implemented checks') + '.', '']
        if s.get('exclusion_reasons'):
            md += ['- Documented identity exclusions: ' + str(s['exclusion_reasons']) + '.', '']
    md += ['## Deliverables and reproduction', '',
           '- `project_summary.csv` and `audit.json`: project counts, statuses, membership, exclusions, and issues.',
           '- `rounds.csv`: each checkpoint/file, ordering seed, exit code, raw outcomes, timing, and validation issues.',
           '- `test_details.csv.gz`: every original test identity, descriptive label, effective N, outcomes, exclusion reason, project audit status, and primary eligibility. Only primary_eligible=True rows qualify for the binary cohort; eligible_identity alone does not override a legacy/failed project status. Decompress with any gzip tool or Python gzip.open. P=PASS, F=FAIL, E=ERROR, S=SKIP, D=duplicate identity, M=missing; character positions follow each project\'s round_order in audit.json.',
           '- `evidence_hashes.csv`: SHA-256 of parsed baseline/detection XML and supporting project metadata. Raw files remain unchanged.',
           '- `observed_flaky_tests.csv`: a convenient uncompressed subset of the test export; project audit status must accompany its interpretation.', '',
           'Reproduce with `python scripts/consolidate_workflow_evidence.py --repos-dir <imported-repos> --output reports/workflow-audit --resolution-rules reports/evidence-recovery/identity_resolution_rules.json --source-root <pinned-source-root>`. Omit resolution arguments for the conservative audit without source-verified exclusions.', '',
           'This report supersedes historical aggregate counts for this imported snapshot. It does not yet constitute a source-resolved training dataset or model-training result.']
    (out / 'CONSOLIDATED_WORKFLOW_REPORT.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repos-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/workflow-audit')
    parser.add_argument('--resolution-rules', type=Path)
    parser.add_argument('--source-root', type=Path)
    args=parser.parse_args()
    out=args.output
    out.mkdir(parents=True, exist_ok=True)
    subjects=json.loads((ROOT/'cannier-replication/inventory.json').read_text(encoding='utf-8-sig'))['subjects']
    inventory={normalize(s['slug']): s for s in subjects}
    inventory[normalize('djangorestframework')]=next(s for s in subjects if s['repository']=='encode/django-rest-framework')
    policies=json.loads(args.resolution_rules.read_text(encoding='utf-8-sig'))['projects'] if args.resolution_rules else {}
    projects=sorted(p for p in args.repos_dir.iterdir() if p.is_dir() and ((p/'results').is_dir() or (p/'setup_log.md').exists() or (p/'baseline_state.json').exists()))
    absent=sorted(s['slug'] for s in subjects if normalize(s['slug']) not in {normalize(p.name) for p in projects} and not (s['repository']=='encode/django-rest-framework' and any(p.name=='djangorestframework' for p in projects)))
    handles=[]
    fields=['project','commit','file','classname','name','label','pattern','pass_count','fail_count','error_count','skip_count','missing_count','duplicate_rounds','effective_n','outcomes','eligible_identity','exclusion_reason']
    specs=[('rounds.csv',['project','config','round','xml_file','exit_code','seed','duration_seconds','valid','testcase_rows','unique_identities','pass','fail','error','skip','issues'],False),
           ('test_details.csv.gz',fields,True), ('evidence_hashes.csv',['project','evidence_path','bytes','sha256'],False)]
    writers=[]
    try:
        for name, columns, compressed in specs:
            handle,writer=csv_writer(out/name,columns,compressed); handles.append(handle); writers.append(writer)
        summaries=[]
        for repo in projects:
            print(f'Auditing {repo.name} ...',flush=True)
            summaries.append(audit_project(repo,writers,inventory,policies.get(repo.name),args.source_root))
    finally:
        for handle in handles: handle.close()
    from datetime import timedelta
    generated=datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
    audit_metadata=dict(generated_at=generated, evidence_root=str(args.repos_dir),
                        resolution_rules_sha256=hashlib.sha256(args.resolution_rules.read_bytes()).hexdigest() if args.resolution_rules else None,
                        source_root=str(args.source_root) if args.source_root else None,
                        expected_subjects_absent=absent, projects=summaries)
    (out/'audit.json').write_text(json.dumps(audit_metadata,indent=2)+'\n',encoding='utf-8')
    columns=['project','status','membership','commit','baseline_status','baseline_verified','baseline_collected','tests','eligible_tests','excluded_identity_count','eligible_observed_flaky','eligible_all_pass','original','random','reverse','observed_flaky','not_observed_flaky','pass_with_skips_or_missing','skip_only','failure_only','ambiguous_duplicate','flaky_percentage_strict','flaky_percentage_active','detection_seconds','issues']
    handle,writer=csv_writer(out/'project_summary.csv',columns)
    with handle:
        for s in summaries:
            writer.writerow(dict(s,**s['rounds'],**s['labels'],eligible_observed_flaky=s['eligible_labels'].get('observed_flaky',0),eligible_all_pass=s['eligible_labels'].get('not_observed_flaky',0),issues='; '.join(s['issues'])))
    final_fields=fields+['project_audit_status','primary_eligible']
    statuses={s['project']:s['status'] for s in summaries}
    handle,writer=csv_writer(out/'test_details.final.csv.gz',final_fields,compressed=True)
    with handle, gzip.open(out/'test_details.csv.gz','rt',encoding='utf-8',newline='') as source:
        for row in csv.DictReader(source):
            row['project_audit_status']=statuses[row['project']]
            row['primary_eligible']=(row['eligible_identity']=='True' and row['label'] in ('observed_flaky','not_observed_flaky')
                                     and statuses[row['project']] in ('protocol_complete_local_checks','protocol_complete_with_exclusions'))
            writer.writerow(row)
    (out/'test_details.final.csv.gz').replace(out/'test_details.csv.gz')
    handle,writer=csv_writer(out/'observed_flaky_tests.csv',final_fields)
    with handle, gzip.open(out/'test_details.csv.gz','rt',encoding='utf-8',newline='') as source:
        for row in csv.DictReader(source):
            if row['label']=='observed_flaky': writer.writerow(row)
    generate_report(summaries,absent,out,generated)
    print(json.dumps(dict(projects=len(summaries),statuses=dict(Counter(s['status'] for s in summaries)),missing=absent)))


if __name__=='__main__':
    main()
