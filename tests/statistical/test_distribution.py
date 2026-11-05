import math
import numpy as np
from risklab.core.simulation import simulate


def test_one_asset_lognormal_analytical_moments():
    n,steps=40000,60;m=.0003;var=.0004
    r=simulate(['A'],[1],[100],0,[m],[[var]],n_paths=n,n_steps=steps,seed=839,preview_count=0)
    log_change=np.log(r['terminal_equity']/100)
    assert abs(log_change.mean()-steps*m)<5.5*math.sqrt(steps*var/n)
    assert abs(log_change.var(ddof=1)-steps*var)<5.5*steps*var*math.sqrt(2/(n-1))
    expected=100*math.exp(steps*(m+var/2))
    sd=expected*math.sqrt(math.expm1(steps*var))
    assert abs(r['terminal_equity'].mean()-expected)<5.5*sd/math.sqrt(n)


def test_requested_covariance_and_log_means():
    n=50000;cov=np.array([[.0001,.00006],[.00006,.0004]])
    base=dict(symbols=['A','B'],prices=[100,100],cash=0,means=[.0002,-.0001],covariance=cov,n_paths=n,n_steps=1,seed=78,preview_count=0)
    a=simulate(quantities=[1,0],**base);b=simulate(quantities=[0,1],**base)
    observed=np.column_stack((np.log(a['terminal_equity']/100),np.log(b['terminal_equity']/100)))
    means=np.array(base['means']);sample=np.cov(observed,rowvar=False,ddof=1)
    assert np.all(np.abs(observed.mean(axis=0)-means)<5.5*np.sqrt(np.diag(cov)/n))
    se=np.sqrt((cov**2+np.outer(np.diag(cov),np.diag(cov)))/(n-1))
    assert np.all(np.abs(sample-cov)<5.5*se)
