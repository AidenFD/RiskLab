import unittest
import numpy as np
from risklab.core.risk import summarize,tail_indices
from risklab.core.valuation import equity_paths,maximum_drawdowns
from risklab.core.simulation import simulate,factor_covariance

class Foundation(unittest.TestCase):
    def test_source_loss_fixture(self):
        r=summarize([800,900,1000,1100,1200],[0]*5,1000,['0.8'])
        self.assertEqual((r['tails']['0.8']['var'],r['tails']['0.8']['es'],r['probability_of_loss']),(100,200,.4))
    def test_drawdown_fixture(self):
        self.assertEqual(maximum_drawdowns([[1000,1200,900,1100]])[0],.25)
    def test_fractional_valuation(self):
        np.testing.assert_array_equal(equity_paths([[[100,20],[80,40]]],[1.5,2],10),[[200,210]])
    def test_exact_tail_boundary(self): self.assertEqual(tail_indices(10000,'.99'),(9900,100))
    def test_negative_var(self): self.assertLess(summarize([110,120],[0,0],100,['.5'])['tails']['.5']['var'],0)
    def test_indefinite(self):
        with self.assertRaises(ValueError):factor_covariance([[1,2],[2,1]])
    def test_singular(self):
        f,_=factor_covariance([[.01,.01],[.01,.01]])
        np.testing.assert_allclose(f@f.T,[[.01,.01],[.01,.01]])
    def run_model(self,**kw):
        args=dict(n_paths=2000,n_steps=3,confidences=('.95',),preview_count=5)
        args.update(kw)
        return simulate(['A'],[2],[100],10,[.001],[[0]],**args)
    def test_deterministic_growth(self):
        r=self.run_model()
        np.testing.assert_allclose(r['terminal_equity'],10+200*np.exp(.003))
    def test_reproducibility(self):
        a=self.run_model();b=self.run_model()
        np.testing.assert_array_equal(a['terminal_equity'],b['terminal_equity'])
    def test_cancel(self):
        with self.assertRaises(InterruptedError):self.run_model(cancel=lambda:True)
    def test_tail_guard(self):
        with self.assertRaises(ValueError): self.run_model(n_paths=100)
    def test_boolean_guard(self):
        with self.assertRaises(ValueError):self.run_model(seed=True)
    def test_permutation(self):
        opts=dict(n_paths=2000,n_steps=2,confidences=('.95',))
        a=simulate(['B','A'],[2,3],[40,50],10,[.001,.002],[[.02,.001],[.001,.01]],**opts)
        b=simulate(['A','B'],[3,2],[50,40],10,[.002,.001],[[.01,.001],[.001,.02]],**opts)
        np.testing.assert_array_equal(a['terminal_equity'],b['terminal_equity'])
    def test_preview_independence(self):
        a=self.run_model(preview_count=0);b=self.run_model(preview_count=20)
        np.testing.assert_array_equal(a['terminal_equity'],b['terminal_equity'])

if __name__=='__main__':unittest.main()
