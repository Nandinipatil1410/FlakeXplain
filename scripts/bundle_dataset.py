"""Package the review artifact; omit raw upstream source and workflow XML."""
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
    dataset=ROOT/'dataset/v0.1'
    validation=json.loads((dataset/'validation.json').read_text())
    if validation['status']!='passed':
        raise ValueError('Dataset must pass validation first')
    paths=list(dataset.iterdir())+list((ROOT/'reports/dataset-preparation').iterdir())
    paths += [ROOT/'reports/workflow-audit'/name for name in
              ('audit.json','project_summary.csv','rounds.csv','evidence_hashes.csv','test_details.csv.gz','CONSOLIDATED_WORKFLOW_REPORT.md')]
    paths += [ROOT/'reports/evidence-recovery'/name for name in
              ('identity_resolution_rules.json','dataset_freeze_verification.json','EVIDENCE_RECOVERY_REPORT.md','cohort_decisions.csv')]
    paths += [ROOT/'scripts'/name for name in
              ('dataset_static.py','prepare_dataset.py','fetch_dataset_sources.py','verify_frozen_evidence.py','validate_dataset.py','report_dataset.py','bundle_dataset.py','setup_repos.py')]
    paths += [ROOT/'cannier-replication/remaining-configs.json', ROOT/'tests/test_dataset_preparation.py']
    paths=sorted({p for p in paths if p.is_file()})
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    manifest=json.loads((dataset/'manifest.json').read_text())
    if not all(sha(dataset/name)==value for name,value in manifest['files'].items()):
        raise ValueError('Export hashes differ before packaging')
    bundle=ROOT/'dataset/FlakeXplain-dataset-v0.1.zip'
    def info(name,compressed):
        value=zipfile.ZipInfo(name,date_time=(2026,10,13,0,0,0))
        value.compress_type=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
        return value
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in paths:
            archive.writestr(info(path.relative_to(ROOT).as_posix(),path.suffix!='gz'),path.read_bytes())
        archive.writestr(info('BUNDLE_CHECKSUMS.json',True),json.dumps(hashes,indent=2)+'\n')
        archive.writestr(info('READ_ME_FIRST.txt',True),
            'FlakeXplain v0.1 guide/pilot review bundle. Start with dataset/v0.1/DATASET_CARD.md.\n'
            'Labels, predictors, source joins, context audit, splits and evidence audit are included.\n'
            'Raw workflow XML and upstream source archives remain separate local evidence; this is not the complete public research release.\n'
            'Use the project repository plus retained raw evidence to reproduce. No model results are included.\n')
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for name,value in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=value:
                raise ValueError('ZIP member checksum differs: '+name)
    checksum=sha(bundle)
    bundle.with_suffix('.zip.sha256').write_text(checksum+'  '+bundle.name+'\n')
    print(json.dumps(dict(bundle=str(bundle),bytes=bundle.stat().st_size,sha256=checksum,verified_files=len(hashes)),indent=2))

if __name__=='__main__':
    main()
