"""Export confirmation cases as a separate component; never change frozen v0.1."""
import gzip,json
from train_pilot import ROOT,reader,sha,write_csv
from train_final_confirmation import OUT,PROJECTS
from dataset_static import digest

def main():
    target=ROOT/'dataset/confirmation-v0.3';target.mkdir(parents=True,exist_ok=True)
    if (target/'manifest.json').exists():raise ValueError('Confirmation export already frozen')
    if json.loads((OUT/'validation.json').read_text())['status']!='passed':raise ValueError('Validated results required')
    with gzip.open(OUT/'external_features.jsonl.gz','rt',encoding='utf-8') as f:rows=[json.loads(line) for line in f]
    schema=json.loads((ROOT/'dataset/development-v0.2/schema.json').read_text())
    labels=[];metadata=[];core=[];context=[]
    for r in rows:
        key=r['example_id'];source=r['source'];p=r['project']
        labels.append(dict(example_id=key,label=r['label'],label_name='observed_flaky' if r['label'] else 'not_observed_flaky',effective_n=r['effective_n']))
        metadata.append(dict(example_id=key,project=p,commit=PROJECTS[p]['commit'],junit_classname=r['junit_classname'],junit_name=r['junit_name'],source_path=source['source_path'],source_qualname=source['source_qualname'],source_file_sha256=source['source_file_sha256'],source_family_id=digest(p+'|'+PROJECTS[p]['commit']+'|'+source['source_path']+'::'+source['source_qualname']),body_ast_sha256=source['body_ast_sha256'],unresolved_fixture_count=source['unresolved_fixture_count'],context_bounded=source['context_bounded'],evidence_run_id=38429430361))
        core.append(dict(example_id=key,**{k:r['features'][k] for k in schema['body_columns']}))
        context.append(dict(example_id=key,**{k:r['features'][k] for k in schema['context_columns']}))
    for name,table in [('labels.csv.gz',labels),('metadata.csv.gz',metadata),('features_core.csv.gz',core),('features_context.csv.gz',context)]:write_csv(target/name,table,list(table[0]))
    (target/'schema.json').write_text(json.dumps(dict(core_columns=schema['body_columns'],additional_context_columns=schema['context_columns'],labels='Binary instability observed in 25 rounds; all other evidence quarantined from predictors.'),indent=2)+'\n')
    (target/'DATASET_CARD.md').write_text('# Independent confirmation component v0.3\n\n2,610 source-mapped all-pass cases across attrs, tenacity and werkzeug; zero observed positives after 25 rounds. Eleven attrs skip-only identities remain in the evidence audit and are excluded. No body-overlap or source-mapping exclusions among binary cases.\n\nThese cases were evaluated after freezing the 35-project development-only models. They are now included only in a separate deployment fit. Do not retune and call them untouched again.\n\nThe complete modelling corpus is the union of dataset/v0.1 labels and metadata (96,118 cases), dataset/development-v0.2 core/context features for those IDs, and this component (2,610 cases): 98,728 cases, 693 observed positives, 38 projects. No new split is assigned to this component; its role is prospective external confirmation.\n\nThe 30-feature core includes two scope-aware reads; context adds 66 more numeric features. IDs are joins only. Outcomes, identities and provenance cannot be predictors. Raw sources/XML and model binaries remain separately retained with checksums and references. Near-clone and human context validation remain incomplete.\n',encoding='utf-8')
    manifest=dict(cases=len(rows),positives=sum(r['label'] for r in rows),projects=PROJECTS,role='Prospective external confirmation; now also used by separate deployment fit',
        combined_deployment_cases=98728,combined_deployment_positives=693,combined_deployment_projects=38,
        development_labels_manifest_sha256=sha(ROOT/'dataset/v0.1/manifest.json'),development_features_manifest_sha256=sha(ROOT/'dataset/development-v0.2/manifest.json'),
        external_results_sha256=sha(OUT/'external_results.json'),extractor_sha256=sha(ROOT/'scripts/confirmation_features.py'),
        evidence_audit_manifest_sha256=sha(OUT/'evidence-audit/audit.json'),artifact_provenance_sha256=sha(OUT/'artifact_provenance.json'),
        files={p.name:sha(p) for p in target.iterdir() if p.is_file()})
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Frozen confirmation dataset:',len(rows),'cases; total union 98,728 cases')

if __name__=='__main__':main()
