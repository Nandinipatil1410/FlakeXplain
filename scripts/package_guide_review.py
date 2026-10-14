"""Assemble a checksum-verified guide pack without raw source or model binaries."""
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()

def main():
    report=ROOT/'reports/development-v0.2'
    if json.loads((report/'validation.json').read_text())['status']!='passed':
        raise ValueError('Development validation required')
    if json.loads((report/'pdf_visual_qa.json').read_text())['status']!='passed':
        raise ValueError('PDF visual inspection required')
    review=json.loads((report/'review_manifest.json').read_text())
    pdf=ROOT/review['pdf_path']
    if sha(pdf)!=review['pdf_sha256']:
        raise ValueError('PDF changed after review generation')
    for name,value in review['files'].items():
        if sha(report/name)!=value:
            raise ValueError('Report artifact changed: '+name)
    paths=[pdf]+[p for p in report.iterdir() if p.is_file()]
    paths += [ROOT/'scripts'/name for name in ['prepare_development_features.py','train_development.py','validate_development.py',
                  'audit_pilot_errors.py','audit_feature_collisions.py','build_guide_report.py','package_guide_review.py']]
    paths += [ROOT/'requirements-pilot.txt',ROOT/'dataset/development-v0.2/FEATURE_DEFINITIONS.md',
              ROOT/'dataset/development-v0.2/schema.json',ROOT/'dataset/development-v0.2/manifest.json',
              ROOT/'dataset/v0.1/DATASET_CARD.md',ROOT/'reports/pilot-v0.1/PILOT_RESULTS_REPORT.md',
              ROOT/'reports/pilot-v0.1/results.json']
    bundle=ROOT/'output/FlakeXplain_Guide_Review_Pack.zip'; paths=sorted(set(paths))
    checksums={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in paths:
            archive.write(path,path.relative_to(ROOT).as_posix(),compress_type=zipfile.ZIP_STORED if path.suffix=='.gz' else zipfile.ZIP_DEFLATED)
        archive.writestr('READ_ME_FIRST.txt',
            'Start with output/pdf/FlakeXplain_Guide_Progress_Report.pdf, then reports/development-v0.2/GUIDE_BRIEF.md.\n'
            'This review pack includes measured development results, original pilot comparison, error audit and reproduction source.\n'
            'It is not the complete replication package. Frozen datasets, raw workflow XML, upstream source archives, transformed source documents and serialized models remain separately retained locally.\n'
            'The folds were inspected during development. No independent final test or improvement over the published CANNIER detector is established.\n')
        archive.writestr('PACK_CHECKSUMS.json',json.dumps(checksums,indent=2)+'\n')
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        if not all(hashlib.sha256(archive.read(name)).hexdigest()==value for name,value in checksums.items()):
            raise ValueError('Pack member checksum differs')
    bundle.with_suffix('.zip.sha256').write_text(sha(bundle)+'  '+bundle.name+'\n')
    print(json.dumps(dict(bundle=str(bundle),bytes=bundle.stat().st_size,verified_files=len(paths),sha256=sha(bundle)),indent=2))

if __name__=='__main__':
    main()
