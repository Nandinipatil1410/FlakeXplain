"""Checks for signed-MCC selection and explicit sampling separation."""
import importlib.util
from pathlib import Path
import sys,unittest
import numpy as np
from sklearn.metrics import matthews_corrcoef
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
AVAILABLE=importlib.util.find_spec('imblearn') is not None
if AVAILABLE:
    from train_cannier_matched import mcc_threshold,fit

@unittest.skipUnless(AVAILABLE,'Matched replication environment requires imbalanced-learn')
class MatchedTests(unittest.TestCase):
    def test_mcc_threshold_matches_exhaustive_signed_metric(self):
        rng=np.random.default_rng(14)
        for _ in range(20):
            y=np.r_[np.zeros(25,int),np.ones(7,int)];score=np.round(rng.random(len(y)),1)
            candidates=np.unique(score);values=[matthews_corrcoef(y,score>=t) for t in candidates];best=max(values)
            expected=max(t for t,value in zip(candidates,values) if abs(value-best)<1e-12)
            self.assertEqual(mcc_threshold(y,score),expected)

    def test_negative_mcc_is_not_converted_to_positive(self):
        y=np.array([0,0,1,1]);score=np.array([.9,.8,.2,.1])
        cut=mcc_threshold(y,score)
        self.assertGreaterEqual(matthews_corrcoef(y,score>=cut),0)
        self.assertLess(matthews_corrcoef(y,score>=.5),0)

    def test_primary_preserves_cases_and_sensitivity_is_explicit(self):
        rng=np.random.default_rng(5);x=rng.random((26,3));y=np.r_[np.zeros(20,int),np.ones(6,int)];before=x.copy()
        model,counts=fit(x,y,'Victim-vs-Rest','natural',14)
        self.assertEqual(counts['actual_fit_cases'],26);self.assertEqual(counts['actual_fit_positives'],6)
        model,counts=fit(x,y,'Victim-vs-Rest','author_smote_sensitivity',14)
        self.assertEqual(counts['actual_fit_cases'],40);self.assertEqual(counts['actual_fit_positives'],20)
        np.testing.assert_array_equal(x,before)

    def test_default_smote_infeasibility_is_not_silently_repaired(self):
        with self.assertRaisesRegex(ValueError,'infeasible'):
            fit(np.arange(30).reshape(10,3),np.r_[np.zeros(7,int),np.ones(3,int)],'NOD-vs-Rest','author_smote_sensitivity',14)

if __name__=='__main__':unittest.main()
