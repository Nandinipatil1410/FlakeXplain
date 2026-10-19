"""Vectorized cost simulation must equal the authors' brute-force definitions."""
import importlib.util
from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
AVAILABLE=importlib.util.find_spec('imblearn') is not None
if AVAILABLE:
    import cannier_protocol as cp

def authors_simple(labels,preds,costs,fixed,tl,tu):
    perf=0;cost=0
    for p in preds:
        cat=np.zeros((len(labels),4));neg=p<tl;cat[neg,labels[neg]+0]=1;pos=p>=tu;cat[pos,labels[pos]+2]=1
        amb=~(neg+pos);cat[amb*~labels,0]=1;cat[amb*labels,3]=1
        perf+=cp.abs_mcc(*cat.sum(axis=0));cost+=costs[amb].sum()
    return perf/len(preds),cost/len(preds)+fixed

def authors_pareto(scores):
    front=np.arange(scores.shape[0]);i=0
    while i<scores.shape[0]:
        nd=np.any(scores<scores[i],axis=1);nd[i]=True;scores=scores[nd];front=front[nd];i=np.sum(nd[:i])+1
    return front

@unittest.skipUnless(AVAILABLE,'CANNIER protocol environment requires imbalanced-learn')
class CannierProtocolTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(3);self.n=60
        self.labels=rng.random(self.n)<.3;self.preds=np.round(rng.random((4,self.n)),2);self.costs=rng.random(self.n)*10

    def test_simple_grid_matches_brute_force(self):
        pts=cp.simple_front_points(self.labels,self.preds,self.costs,5.0)
        for perf,cost,tl,tu,n in pts[np.random.default_rng(1).choice(len(pts),60,replace=False)]:
            if n==0:continue
            ep,ec=authors_simple(self.labels,self.preds,self.costs,5.0,tl,tu)
            self.assertAlmostEqual(perf,ep,places=10);self.assertAlmostEqual(cost,ec,places=8)

    def test_pareto_matches_authors(self):
        pts=np.random.default_rng(9).random((300,5));pts[:,:2]=np.round(pts[:,:2],2)
        ours=cp.pareto(pts);flipped=pts.copy();flipped[:,0]=1-flipped[:,0]
        theirs=pts[authors_pareto(flipped[:,:2])]
        self.assertEqual({tuple(r) for r in ours[:,:2]},{tuple(r) for r in theirs[:,:2]})

    def test_pairwise_matches_brute_force(self):
        rng=np.random.default_rng(4);proj=np.r_[np.zeros(30,int),np.ones(30,int)];times=rng.random(60)
        deps=[np.array([[0,1],[2,3],[4,1]]),np.array([[5,6],[7,8]])]
        pv=np.round(rng.random((30,60)),2);pp=np.round(rng.random((30,60)),2)
        pts=cp.pairwise_front_points(proj,times,deps,pv,pp,1.0,2)
        for perf,cost,tv,tp,_ in pts[rng.choice(len(pts),25,replace=False)]:
            found=0;spent=0
            for i,j in cp.rng_pairs():
                for pid,d in enumerate(deps):
                    m=proj==pid;dense=np.zeros((30,30),int);dense[d[:,0],d[:,1]]=1
                    mv=pv[i][m]>=tv;mp=pp[j][m]>=tp;t=times[m]
                    found+=dense[mv][:,mp].sum();spent+=mp.sum()*t[mv].sum()+mv.sum()*t[mp].sum()
            self.assertAlmostEqual(perf,found/30/5,places=10);self.assertAlmostEqual(cost,spent/30+1.0,places=8)

    def test_context_never_changes_baseline_columns(self):
        x=np.arange(12.).reshape(3,4);ctx=np.ones((3,2))
        self.assertTrue(np.array_equal(np.hstack((x,ctx))[:,:4],x))

if __name__=='__main__':unittest.main()
