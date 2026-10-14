"""Create a checksum-verified review pack for the matched CANNIER experiment."""
import json,zipfile,hashlib
from prepare_cannier_matched import OUT,DATA
from train_pilot import ROOT,sha

def main():
    pdf=ROOT/'output/pdf/CANNIER_Matched_Comparison_Addendum.pdf';qa=json.loads((OUT/'pdf_visual_qa.json').read_text())
    if qa['status']!='passed' or qa['sha256']!=sha(pdf):raise ValueError('PDF visual verification required')
    paths=[pdf,ROOT/'requirements-pilot.txt',ROOT/'requirements-cannier-matched.txt',ROOT/'cannier-replication/subjects.json',ROOT/'cannier-replication/LICENSE']
    paths += [p for p in DATA.iterdir() if p.is_file()]
    paths += [p for p in OUT.rglob('*') if p.is_file()]
    paths += [ROOT/'scripts'/name for name in ['fetch_cannier_release.py','fetch_dataset_sources.py','prepare_cannier_matched.py','train_cannier_matched.py','validate_cannier_matched.py','report_cannier_matched.py','audit_cannier_ranking.py','build_cannier_comparison_pdf.py','package_cannier_comparison.py','confirmation_features.py','dataset_static.py','prepare_dataset.py','prepare_development_features.py','train_pilot.py']]
    paths += [ROOT/'tests/test_cannier_matched.py',ROOT/'dataset/development-v0.2/schema.json']
    paths=sorted(set(paths));checksums={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    target=ROOT/'output/CANNIER_Matched_Comparison_Review.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix=='.gz' else zipfile.ZIP_DEFLATED)
        z.writestr('PACK_CHECKSUMS.json',json.dumps(checksums,indent=2)+'\n')
        z.writestr('READ_ME_FIRST.txt','Start with output/pdf/CANNIER_Matched_Comparison_Addendum.pdf and reports/cannier-matched-v0.4/MATCHED_COMPARISON_REPORT.md.\nThis is a retrospective matched classifier comparison, not untouched confirmation or full hybrid-detector reproduction. Natural imbalance is primary; author-SMOTE is a separate sensitivity variable.\nRaw authors archive, SQLite databases, pinned source archives and fitted models are not included. Retrieve the archive and sources with scripts/fetch_cannier_release.py. See REPRODUCTION.md for the full environment and steps.\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None or not all(hashlib.sha256(z.read(k)).hexdigest()==v for k,v in checksums.items()):raise ValueError('Review ZIP integrity failure')
    record=dict(path=str(target.relative_to(ROOT)),bytes=target.stat().st_size,sha256=sha(target),verified_files=len(paths))
    target.with_suffix('.zip.sha256').write_text(record['sha256']+'  '+target.name+'\n');(ROOT/'output/cannier_comparison_pack_manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
