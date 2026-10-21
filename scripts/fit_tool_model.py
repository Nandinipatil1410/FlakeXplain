"""Fit the model shipped with the flakexplain CLI: the frozen v0.9 ET-BF (PROTOCOL section 5).

ExtraTreesClassifier(n_estimators=100, random_state=20261020) on B + F with flaky_frequency_strict,
trained once on all 1,292 v0.8 labelled failures. No v0.9 data is read. The model card records the
input checksums; the v0.9 confirmation is the first evaluation of this exact model on new failures.
Run with GH_TOKEN set to any value (mdflaker_v08_probe reads it at import; no API call is made).
"""
import csv,gzip,hashlib,io,json,sys,datetime
from pathlib import Path
import joblib,numpy as np,sklearn
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,SEED
from mdflaker_v08_features import CAND
from mdflaker_v08_robustness import strict_frequency
from sklearn.ensemble import ExtraTreesClassifier

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'tool/src/flakexplain/data'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    _,strict=strict_frequency(cands)
    X=np.array([[strict[i] if k=='flaky_frequency' else float(feat[i][k]) for k in B+F] for i in ids]);y=np.array([lab[i] for i in ids])
    if len(y)!=1292:raise ValueError(f'expected the 1,292 v0.8 labelled failures, got {len(y)}')
    model=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(X,y)
    buf=io.BytesIO();joblib.dump(dict(model=model,columns=B+F),buf,compress=3);raw=buf.getvalue()
    DATA.mkdir(parents=True,exist_ok=True);(DATA/'etbf-v0.8.joblib').write_bytes(raw)
    card=dict(name='ET-BF v0.8 (frozen v0.9 model)',file='etbf-v0.8.joblib',sha256=hashlib.sha256(raw).hexdigest(),
        fitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),sklearn=sklearn.__version__,
        estimator='ExtraTreesClassifier(n_estimators=100, random_state=20261020)',threshold=0.5,columns=B+F,
        training=dict(failures=int(len(y)),flaky=int(y.sum()),not_flaky=int((1-y).sum()),projects=sorted({r['repo'] for r in rows}),
            label='flaky = test passed in at least one of 30 reruns of the failing commit',flaky_frequency='strict: earlier workflow runs only'),
        evidence=dict(v08_results='reports/mdflaker-fresh-v0.8/RESULTS.md',v09_protocol='reports/mdflaker-confirm-v0.9/PROTOCOL.md',
            note='v0.8 E1/E2 numbers come from models trained on part of this data; this all-data fit has no held-out score until v0.9.'),
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [CAND,V8/'features.csv.gz',V8/'labels.csv',Path(__file__)]})
    (DATA/'model_card.json').write_text(json.dumps(card,indent=1)+'\n')
    print({k:card[k] for k in ('sha256','sklearn')},card['training'])

if __name__=='__main__':main()
