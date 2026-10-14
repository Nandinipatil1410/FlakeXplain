"""Descriptive representation audit; labels never feed a model or feature table."""
from collections import Counter
import json
import numpy as np
from train_development import load_inputs
from train_pilot import ROOT,write_csv

def main():
    ids,y,meta,projects,folds,inner,xs,columns,manifest=load_inputs(); rows=[]
    for name,x in xs.items():
        _,inverse=np.unique(x,axis=0,return_inverse=True)
        totals=np.bincount(inverse); positives=np.bincount(inverse,weights=y)
        negatives=totals-positives; mixed=(positives>0)&(negatives>0)
        rows.append(dict(representation=name,features=x.shape[1],cases=len(y),unique_feature_vectors=len(totals),
                         mixed_label_vectors=int(mixed.sum()),positive_cases_in_mixed_vectors=int(positives[mixed].sum()),
                         negative_cases_in_mixed_vectors=int(negatives[mixed].sum()),
                         positive_fraction_in_mixed_vectors=float(positives[mixed].sum()/y.sum()),
                         unavoidable_training_misclassifications_for_identical_vectors=int(np.minimum(positives,negatives).sum())))
    out=ROOT/'reports/development-v0.2'; write_csv(out/'feature_collision_audit.csv',rows,list(rows[0]))
    (out/'feature_collision_audit_note.json').write_text(json.dumps(dict(purpose='Descriptive development audit only; full-corpus labels used to measure collisions, never to generate predictors or evaluate a trained oracle.',
        meaning='Identical numeric feature vectors with opposite observed labels cannot be perfectly separated using these representations. This does not establish causes, future outcomes or independent generalization.'),indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':
    main()
