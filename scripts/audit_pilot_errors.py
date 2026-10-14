"""Declare a bounded project-spread error review; preserve outcome labels."""
from collections import defaultdict
import json
from pathlib import Path
from train_pilot import ROOT, reader, sha, write_csv

def main():
    out=ROOT/'reports/development-v0.2'; out.mkdir(parents=True,exist_ok=True)
    predictions=list(reader(ROOT/'reports/pilot-v0.1/oof_predictions.csv.gz'))
    metadata={r['example_id']:r for r in reader(ROOT/'dataset/v0.1/metadata.csv.gz')}
    labels={r['example_id']:r for r in reader(ROOT/'dataset/v0.1/labels.csv.gz')}
    selected=[]
    for kind,y,pred in [('false_positive',0,1),('false_negative',1,0)]:
        groups=defaultdict(list)
        for r in predictions:
            if int(r['label'])==y and int(r['context_inner_prediction'])==pred:
                groups[r['project']].append(r)
        for project,rows in groups.items():
            rows.sort(key=lambda r:((-1 if kind=='false_positive' else 1)*float(r['context_score']),r['example_id']))
        used=set(); taken=0
        while taken<50:
            changed=False
            for project in sorted(groups):
                while groups[project] and metadata[groups[project][0]['example_id']]['source_family_id'] in used:
                    groups[project].pop(0)
                if groups[project] and taken<50:
                    r=groups[project].pop(0); m=metadata[r['example_id']]; evidence=labels[r['example_id']]
                    used.add(m['source_family_id']); taken+=1; changed=True
                    selected.append(dict(error_type=kind,example_id=r['example_id'],project=project,label=y,score=r['context_score'],
                                         source_path=m['source_path'],source_qualname=m['source_qualname'],source_start=m['source_start'],source_end=m['source_end'],
                                         source_file_sha256=m['source_file_sha256'],source_family_id=m['source_family_id'],context_id=m['context_id'],
                                         context_bounded=m['context_bounded'],unresolved_fixture_candidates=m['unresolved_fixture_count'],
                                         pass_count=evidence['pass_count'],fail_count=evidence['fail_count'],error_count=evidence['error_count'],
                                         effective_n=evidence['effective_n'],manual_review='pending; not cause-validated'))
            if not changed:
                break
    write_csv(out/'error_audit_sample.csv',selected,list(selected[0]))
    info=dict(sample_cases=len(selected),projects=len({r['project'] for r in selected}),
              rule='Up to 50 context-model false positives and 50 false negatives; round-robin sorted projects and distinct source families per error type; extreme scores within project.',
              purpose='Development error audit after original pilot, not an unbiased population sample or causal-label confirmation',
              pilot_predictions_sha256=sha(ROOT/'reports/pilot-v0.1/oof_predictions.csv.gz'),sample_sha256=sha(out/'error_audit_sample.csv'))
    (out/'error_audit_selection.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))

if __name__=='__main__':
    main()
