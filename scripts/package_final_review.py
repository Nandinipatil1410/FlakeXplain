"""Create and verify a guide-review ZIP, excluding raw sources and models."""
import json,zipfile
from train_final_confirmation import OUT
from train_pilot import ROOT,sha

def main():
    qa=json.loads((OUT/'pdf_visual_qa.json').read_text());pdf=ROOT/'output/pdf/FlakeXplain_Final_Study_Report.pdf'
    if qa['status']!='passed' or qa['pdf_sha256']!=sha(pdf):raise ValueError('Final PDF QA required')
    if json.loads((OUT/'validation.json').read_text())['status']!='passed':raise ValueError('Final evaluation validation required')
    paths=[pdf,ROOT/'requirements-pilot.txt',ROOT/'RESEARCH_RESULTS.md']
    paths += [p for p in OUT.rglob('*') if p.is_file()]
    paths += list((ROOT/'scripts').glob('*.py'))
    paths += list((ROOT/'dataset/confirmation-v0.3').glob('*'))
    paths += [ROOT/'dataset/v0.1'/p for p in ['DATASET_CARD.md','FEATURE_DEFINITIONS.md','manifest.json']]
    paths += [ROOT/'dataset/development-v0.2'/p for p in ['FEATURE_DEFINITIONS.md','schema.json','manifest.json']]
    paths += [ROOT/'reports/development-v0.2'/p for p in ['DEVELOPMENT_RESULTS_REPORT.md','metrics_pooled.csv','metrics_by_project.csv','validation.json','manual_error_review.json']]
    paths=sorted(set(paths));checksums={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    target=ROOT/'output/FlakeXplain_Final_Guide_Review.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in paths:z.write(path,path.relative_to(ROOT).as_posix(),compress_type=zipfile.ZIP_STORED if path.suffix=='.gz' else zipfile.ZIP_DEFLATED)
        z.writestr('PACK_CHECKSUMS.json',json.dumps(checksums,indent=2)+'\n')
        z.writestr('READ_ME_FIRST.txt','Start with output/pdf/FlakeXplain_Final_Study_Report.pdf and reports/final-confirmation-v0.3/GUIDE_FINAL_BRIEF.md.\nThis pack contains final measured results, the prospective protocol, source-linked attributions, manuscript draft, scripts and the confirmation dataset component.\nIt excludes raw source/XML archives, model binaries and the full development dataset. It is not a complete replication release.\nIndependent confirmation has zero observed positive cases; recall gains and superiority to published systems remain unestablished.\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        if not all(__import__('hashlib').sha256(z.read(k)).hexdigest()==v for k,v in checksums.items()):raise ValueError('ZIP checksum mismatch')
    digest=sha(target);target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n')
    record=dict(path=str(target.relative_to(ROOT)),sha256=digest,bytes=target.stat().st_size,verified_members=len(paths))
    # Keep the pack record outside the packed tree to avoid a self-reference.
    (ROOT/'output/final_review_pack_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
