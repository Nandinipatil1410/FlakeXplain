"""Generate recovery decisions and cohort tables from the completed evidence audit."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/evidence-recovery'
LOCAL = ROOT / 'local-evidence/recovery-2026-10-12'
ACCEPTED = {'protocol_complete_local_checks', 'protocol_complete_with_exclusions'}


def main():
    audit = json.loads((ROOT / 'reports/workflow-audit/audit.json').read_text(encoding='utf-8'))
    projects = {p['project']: p for p in audit['projects']}
    rules = json.loads((OUT / 'identity_resolution_rules.json').read_text(encoding='utf-8'))
    assert audit['resolution_rules_sha256'] == hashlib.sha256((OUT/'identity_resolution_rules.json').read_bytes()).hexdigest()
    artifacts = json.loads((LOCAL / 'github-artifact-inventory.json').read_text(encoding='utf-8'))
    artifact = next(a for a in artifacts if a['id'] == 11533068947)
    archive = LOCAL / 'artifacts/11533068947/artifact.zip'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert artifact['digest'] == 'sha256:' + digest
    source_archives = []
    for source in sorted((LOCAL / 'pinned-sources').glob('*/FLAKEXPLAIN_SOURCE_PROVENANCE.json')):
        source_archives.append(json.loads(source.read_text(encoding='utf-8')))
    manifest = dict(graphene_artifact_id=artifact['id'], graphene_run_id=artifact['workflow_run']['id'],
                    graphene_archive_sha256=digest, github_digest_match=True,
                    graphene_archive_provenance=json.loads((LOCAL / 'artifacts/11533068947/evidence/provenance.json').read_text()),
                    source_archives=source_archives,
                    import_manifest='local-evidence/recovery-2026-10-12/recovery-import-manifest.json',
                    identity_rules_sha256=hashlib.sha256((OUT/'identity_resolution_rules.json').read_bytes()).hexdigest())
    (OUT / 'recovery_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    with (OUT / 'cohort_decisions.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['project','commit','membership','audit_status','primary_project','retained_identities','excluded_identities','observed_flaky','all_pass','binary_examples','decision']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for name, p in sorted(projects.items()):
            included = p['status'] in ACCEPTED
            labels = p['eligible_labels']
            writer.writerow(dict(project=name, commit=p['commit'], membership=p['membership'], audit_status=p['status'],
                primary_project=included, retained_identities=p['eligible_tests'], excluded_identities=p['excluded_identity_count'],
                observed_flaky=labels.get('observed_flaky',0) if included else 0,
                all_pass=labels.get('not_observed_flaky',0) if included else 0,
                binary_examples=(labels.get('observed_flaky',0)+labels.get('not_observed_flaky',0)) if included else 0,
                decision='Include stable, complete binary cases' if included else '; '.join(p['issues'])))
    eligible = [p for p in projects.values() if p['status'] in ACCEPTED]
    positives = sum(p['eligible_labels'].get('observed_flaky',0) for p in eligible)
    negatives = sum(p['eligible_labels'].get('not_observed_flaky',0) for p in eligible)
    md = ['# Evidence recovery and cohort decisions', '', f'Final audit snapshot: {audit["generated_at"]}.', '',
          '**Implemented and empirically checked:** recovery of missing evidence, pinned-source identity review, and explicit cohort exclusions. No upstream tests were changed or rerun. No classifier was trained.', '',
          f'All **30 CANNIER subject folders** are present. **{len(eligible)} projects** qualify under the implemented local protocol checks, '
          f'with **{positives:,} observed-flaky** and **{negatives:,} all-pass** binary examples (**{positives+negatives:,} total**, '
          f'**{100*positives/(positives+negatives):.4f}% positive**). These are source-unresolved candidate examples; fixture extraction and canonical source joins remain dataset-preparation work.', '',
          '## Recovered evidence', '',
          '- **Graphene:** downloaded the existing full-run artifact from [workflow run 37740852914](https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/37740852914), attempt 1, artifact 11533068947. The original ZIP is preserved locally; its SHA-256 matches the digest returned by GitHub. The nested archive contains workflow provenance, matching baseline/environment records, and all 25 detection rounds. Imported 350 JUnit identities: 1 observed-flaky, 345 all-pass, 4 skip-only. No rerun was needed. The older baseline-only artifact was not combined with this run.',
          '- **Filelock:** located the complete earlier local execution in `C:/Users/Nandini/AppData/Local/FlakeXplain/5b4a364d/repos/filelock`. Imported only results/logs and environment/setup/baseline metadata, with per-file SHA-256 verification. All 25 rounds pass the checks: 2 observed-flaky, 1,104 all-pass, 236 skip-only. This is recovered local execution evidence, not a newly discovered GitHub workflow.',
          '- **HTTPX:** recovered the failed baseline state and all three baseline-attempt XML files from the same local work directory. All three attempts failed. Retain the evidence and exclude the project; no negative labels or detection rounds are invented.',
          '- Existing differing setup metadata was backed up under `local-evidence/recovery-2026-10-12/pre-import-metadata/`. The importer refused to overwrite differing raw result/log files. `recovery-import-manifest.json` records source, destination, and SHA-256 for all 131 imported files.', '',
          '## Resolution of the four identity issues', '',
          'The resolution does **not** recover identities that were never recorded. It permits inclusion of the stable subset after source-verified exclusions. Selection is based on identity quality, not prediction performance or whether a test is positive. Raw XML stays intact; exports retain the original identity groups, counts, and explicit exclusions.', '',
          '| Project | Recorded baseline rows | Raw identity union | Retained identities | Excluded union identities | Eligible flaky | Eligible all-pass |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for name in ('cirq','xonsh','hypothesis','setuptools'):
        p=projects[name];l=p['eligible_labels']
        md.append(f'| {name} | {p["baseline_collected"]:,} | {p["tests"]:,} | {p["eligible_tests"]:,} | {p["excluded_identity_count"]:,} | {l.get("observed_flaky",0):,} | {l.get("not_observed_flaky",0):,} |')
    md += ['',
           '- **Cirq:** 17 source-function families have inconsistent parameterized IDs. Pinned code confirms examples of collection-time random inputs, generated class lists, and representation-dependent IDs. Exclude those entire families, including any IDs that happen to recur, because stripping suffixes would not establish input equivalence. The retained set matches baseline and every round. The 8,759 excluded union identities represent changing names across runs, not 8,759 independent collected cases; the baseline has 420 rows from these families.',
           '- **xonsh:** `tests/test_history_json.py` builds `SEC_FROM_LATEST` using `time.time()` at collection and embeds it in three parameter IDs. Exclude the complete 12-case source family rather than using outcome-dependent or timestamp-stripping joins. Its 84 union identities collapse to 12 cases in a single baseline; the retained baseline and every round have the same identities.',
           '- **Hypothesis:** the pinned `boundaries` parameter list repeats values. Four test functions generate eight colliding JUnit identity groups ending in `[10]` or `[31]`, with two testcase rows per group. Exclude these 16 baseline rows / 8 union groups. Other unambiguous cases remain. Reordered XML position cannot safely distinguish the collisions, and their duplicate rows are never copied into training examples.',
           '- **setuptools:** the pinned environment uses `pytest-checkdocs==2.7.1`. Its verified package source creates `CheckdocsItem.from_parent(parent, name="project")`; the context-free `project` JUnit row is a package documentation check, not a test source function. Exclude this one row and retain the remaining stable test identities.', '',
           'Exclusion policies are pinned to the exact evidence commits and SHA-256-verified source files. They cannot bypass a baseline failure, environment mismatch, changed raw testcase count, or an unexcluded identity mismatch. Regression tests cover those boundaries.', '',
           '## Legacy evidence and other exclusions', '',
           '- **Click, Flask, fsspec:** 25 XML files are present for each, but the imports lack `environment.json`, `baseline_state.json`, and `setup_state.json`. Narrative setup logs and package snapshots do not reconstruct a passing baseline XML bound to the detection environment. Keep their descriptive results, including fsspec\'s two observed-flip identities, but exclude all three from the primary cohort. No extra workflows were launched solely to enlarge the cohort.',
           '- **HTTPX:** exclude due to the recorded baseline failure, not because of model performance.',
           '- **Werkzeug:** no evidence folder is present. It is an additional configured candidate, not a missing CANNIER subject, and is not part of the cohort.',
           '- **SunPy and urllib3:** retained experiments use revisions different from the released CANNIER inventory. Membership does not imply exact reproduction. The cohort table preserves this distinction.', '',
           '## Provenance and reproducibility limits', '',
           f'Graphene ZIP SHA-256: `{digest}`. The recovered artifact has `provenance.json` but no `checksums.json`; the old packaging format must not be described as supplying that missing file. GitHub\'s matching ZIP digest and the recovered provenance are separately recorded in `recovery_manifest.json`.', '',
           'For other previously imported projects, top-level archive provenance/checksums have not all been recovered. The audit freezes the current project evidence with file hashes. This is sufficient to proceed with explicit local-cohort preparation, not to claim that all release-provenance work is finished.', '',
           'All upstream source was fetched at the exact recorded commit and inspected statically. Source archives and extracted copies remain local; no upstream test suite was imported/executed to manufacture new observations. The source references below support the exclusion decisions, not causal flaky-test diagnoses.', '',
           '### Source references', '']
    repos={'cirq':'quantumlib/Cirq','xonsh':'xonsh/xonsh','hypothesis':'HypothesisWorks/hypothesis'}
    for name in ('cirq','xonsh','hypothesis'):
        policy=rules['projects'][name]
        for entry in policy['source_evidence']:
            relative=entry['path'].split('/',1)[1]
            url=f'https://github.com/{repos[name]}/blob/{policy["commit"]}/{relative}'
            md.append(f'- [{name}: {relative}]({url}); SHA-256 `{entry["sha256"]}`.')
    md += ['- setuptools package-check source: the pinned pytest-checkdocs 2.7.1 wheel, verified against PyPI\'s SHA-256; its URL and digest are recorded in `recovery_manifest.json`.', '',
           '## Outputs and next stage', '',
           '- `identity_resolution_rules.json`: explicit commit-bound exclusions and source hashes.',
           '- `cohort_decisions.csv`: include/exclude decision and candidate binary counts for every project.',
           '- `recovery_manifest.json`: recovered artifact/source provenance and hashes.',
           '- `../workflow-audit/CONSOLIDATED_WORKFLOW_REPORT.md`: regenerated project/round/test statistics.',
           '- `../workflow-audit/test_details.csv.gz`: all original identities, exclusions, and `primary_eligible` flags. Only flagged binary rows belong to the current candidate cohort.', '',
           'The evidence gaps now have documented decisions; dataset preparation can proceed on the retained cohort. Next retrieve remaining pinned sources, establish canonical source-function joins, extract fixture/helper context with coverage checks, and freeze project-disjoint splits before the Extra Trees pilot. Final source joins may create further declared exclusions; current counts are candidate cohort counts, not guaranteed final training counts.']
    (OUT/'EVIDENCE_RECOVERY_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(f'Recovery report generated for {len(projects)} projects; {len(eligible)} eligible projects, {positives+negatives} candidate binary examples.')


if __name__ == '__main__':
    main()
