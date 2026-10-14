import ast
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import HashingVectorizer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_development_features import code_tokens,extra_features
from train_development import HASH_PARAMS,build_model

class DevelopmentTests(unittest.TestCase):
    def test_text_masks_signature_docstrings_comments_and_literal_values(self):
        a=ast.parse('def test_flaky(secret):\n    "flaky documentation"\n    # outcome pass\n    assert action("failed") == 42\n').body[0]
        b=ast.parse('def completely_different(other):\n    "other documentation"\n    assert action("different") == 123\n').body[0]
        self.assertEqual(code_tokens(a,500),code_tokens(b,500))
        self.assertNotIn('failed',code_tokens(a,500))
        self.assertNotIn('secret',code_tokens(a,500))

    def test_framework_assertion_and_shared_state_features(self):
        tree=ast.parse('GLOBAL=[]\nclass Test:\n    state={}\n    def test_a(self):\n        self.assertEqual(GLOBAL, self.state)\n        self.state[0]=1\n        GLOBAL.append(1)\n')
        cls=tree.body[1]; node=cls.body[1]
        f=extra_features(node,tree,[cls])
        self.assertEqual(f['unittest_asserts'],1)
        self.assertEqual(f['subscript_writes'],1)
        self.assertEqual(f['mutable_ops'],1)
        self.assertGreater(f['module_shared_reads'],0)
        self.assertGreater(f['class_shared_reads'],0)

    def test_numeric_scaler_fits_training_partition_only(self):
        model=build_model('logistic',{'C':.1})
        train=np.array([[0.,1.],[1.,0.],[2.,1.],[3.,2.]])
        model.fit(train,np.array([0,0,1,1]))
        original=model.named_steps['scale'].mean_.copy()
        model.predict_proba(np.array([[100000.,200000.]]))
        np.testing.assert_array_equal(model.named_steps['scale'].mean_,original)
        np.testing.assert_allclose(original,np.log1p(train).mean(axis=0))

    def test_hashing_is_stateless_and_idf_sees_training_counts_only(self):
        hasher=HashingVectorizer(**HASH_PARAMS)
        train=hasher.transform(['alpha beta','alpha','gamma','gamma beta'])
        test=hasher.transform(['unseen unseen alpha'])
        self.assertFalse(hasattr(hasher,'vocabulary_'))
        model=build_model('text_logistic',{'C':1.})
        model.fit(train,np.array([0,0,1,1]))
        before=model.named_steps['tfidf'].idf_.copy()
        model.predict_proba(test)
        np.testing.assert_array_equal(model.named_steps['tfidf'].idf_,before)

if __name__=='__main__':
    unittest.main()
