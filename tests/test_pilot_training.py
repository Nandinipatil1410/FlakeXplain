"""Check threshold/ranking metrics, joins, and feature isolation on small fixtures."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from sklearn.metrics import average_precision_score, matthews_corrcoef, precision_score, recall_score, f1_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from train_pilot import best_threshold, load_feature_table, metrics, weighted_ap

class PilotTests(unittest.TestCase):
    def test_metric_values_match_independent_sklearn_metrics(self):
        y=np.array([1,0,1,0,0]); score=np.array([.9,.8,.7,.6,.1]); pred=score>=.65
        values=metrics(y,score,pred,np.array(['a','b','c','d','e']))
        self.assertAlmostEqual(values['mcc'],matthews_corrcoef(y,pred))
        self.assertAlmostEqual(values['precision'],precision_score(y,pred))
        self.assertAlmostEqual(values['recall'],recall_score(y,pred))
        self.assertAlmostEqual(values['f1'],f1_score(y,pred))
        self.assertAlmostEqual(values['average_precision'],average_precision_score(y,score))
        self.assertEqual(values['fp'],1)

    def test_zero_positive_project_reports_undefined_ap_recall(self):
        r=metrics(np.array([0,0]),np.array([.8,.1]),np.array([True,False]),np.array(['a','b']))
        self.assertIsNone(r['average_precision']); self.assertIsNone(r['recall'])
        self.assertEqual(r['false_positives_per_1000_negative'],500)

    def test_threshold_maximizes_training_f1_and_uses_higher_tie(self):
        y=np.array([0,1,0,1]); scores=np.array([.1,.2,.3,.4])
        threshold,value=best_threshold(y,scores)
        candidates=[(.1,f1_score(y,scores>=.1)),(.2,f1_score(y,scores>=.2)),(.3,f1_score(y,scores>=.3)),(.4,f1_score(y,scores>=.4))]
        self.assertAlmostEqual(value,max(v for _,v in candidates))
        self.assertEqual(threshold,.2)
        # All threshold-zero tied probabilities must be considered together.
        t,f=best_threshold(np.array([1,0]),np.array([0.,0.]))
        self.assertEqual(t,0); self.assertAlmostEqual(f,2/3)

    def test_project_bootstrap_ap_handles_ties_and_zero_weight_groups(self):
        y=np.array([1,0,1,0,1,0]); s=np.array([.8,.8,.4,.4,.1,.1]); w=np.array([0.,0.,2.,1.,3.,1.])
        self.assertAlmostEqual(weighted_ap(y,s,w),average_precision_score(y,s,sample_weight=w))

    def test_top_budget_ties_use_identity_not_label(self):
        y=np.array([1,0,0,0,0,0,0,0,0,0]); s=np.ones(10)
        ids=np.array(['z','a','b','c','d','e','f','g','h','i'])
        r=metrics(y,s,np.zeros(10),ids)
        self.assertEqual(r['recall_at_top_10_percent'],0)

    def test_feature_loading_reorders_unique_join_and_rejects_label_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'features.csv'
            path.write_text('example_id,count\nb,2\na,1\n')
            data=load_feature_table(path,['count'],np.array(['a','b']))
            np.testing.assert_array_equal(data[:,0],[1,2])
            path.write_text('example_id,count,label\na,1,1\nb,2,0\n')
            with self.assertRaises(ValueError):
                load_feature_table(path,['count'],np.array(['a','b']))

if __name__=='__main__':
    unittest.main()
