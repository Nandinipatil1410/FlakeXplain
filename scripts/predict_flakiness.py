"""Predict static risk for a named source function without importing project code."""
import argparse,json
from pathlib import Path
import joblib,numpy as np
from dataset_static import SourceIndex
from confirmation_features import extract
from evaluate_confirmation import tree_path_attribution
from train_pilot import ROOT,sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--path',required=True);parser.add_argument('--qualname',required=True);parser.add_argument('--collection-class');args=parser.parse_args()
    root=args.source_root.resolve();target=(root/args.path).resolve()
    if root not in target.parents:raise ValueError('Source path must remain inside source root')
    relative=target.relative_to(root).as_posix();index=SourceIndex(root)
    fn=index.functions[(relative,args.qualname)];cls=args.collection_class if args.collection_class is not None else args.qualname.rpartition('.')[0]
    core,context,source=extract(index,fn,cls,relative)
    card=json.loads((ROOT/'reports/final-confirmation-v0.3/deployment_model_card.json').read_text());path=ROOT/card['path']
    if sha(path)!=card['sha256']:raise ValueError('Deployment model checksum differs')
    payload=joblib.load(path);x=np.asarray([context[k] for k in payload['columns']],np.float32)
    score=float(payload['model'].predict_proba(x.reshape(1,-1))[0,1]);base,contributions=tree_path_attribution(payload['model'],x)
    evidence=sorted([dict(feature=k,value=float(v),contribution=float(c)) for k,v,c in zip(payload['columns'],x,contributions)],key=lambda z:-abs(z['contribution']))[:10]
    print(json.dumps(dict(risk_score=score,flagged=score>=payload['threshold'],threshold=payload['threshold'],base=base,source=source,leading_attributions=evidence,
        caveat='Uncalibrated observed-instability risk; a prediction is not a flaky label or causal diagnosis. Mean tree-path attributions are not SHAP.'),indent=2))

if __name__=='__main__':main()
