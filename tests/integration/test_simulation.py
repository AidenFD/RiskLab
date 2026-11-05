import math
import numpy as np
import pytest
from risklab.core.simulation import simulate
from risklab.services.experiments import execute,diagnose,compare


def test_all_cash_constant():
    r=simulate(['A'],[0],[100],25000,[0],[[.001]],n_paths=2000,n_steps=10,confidences=['.95'])
    np.testing.assert_array_equal(r['terminal_equity'],25000);np.testing.assert_array_equal(r['max_drawdowns'],0)


def test_perfect_dependence():
    args=dict(n_paths=2000,n_steps=10,confidences=['.95'],seed=8)
    a=simulate(['A','B'],[1,0],[100,100],0,[0,0],[[.001,.001],[.001,.001]],**args)
    b=simulate(['A','B'],[0,1],[100,100],0,[0,0],[[.001,.001],[.001,.001]],**args)
    np.testing.assert_allclose(a['terminal_equity'],b['terminal_equity'],rtol=1e-14)

@pytest.mark.parametrize('batch',[1,257,512])
def test_scalar_reference(batch):
    # Independent scalar valuation loop; normal stream contract duplicated explicitly,
    # without production valuation, drawdown or summary helpers.
    count,steps=2000,5
    r=simulate(['A','B'],[1.5,3],[100,50],25,[.001,-.0005],[[.0001,0],[0,.0004]],
               n_paths=count,n_steps=steps,batch_size=batch,seed=91,confidences=['.95'])
    rng=np.random.Generator(np.random.PCG64(91));terminal=[];drawdowns=[]
    for start in range(0,count,batch):
        n=min(batch,count-start);shocks=rng.standard_normal((steps,n,2))
        for path in range(n):
            a,b=100.,50.;peak=325.;dd=0.
            for t in range(steps):
                a*=math.exp(.001+.01*shocks[t,path,0]);b*=math.exp(-.0005+.02*shocks[t,path,1])
                v=25+1.5*a+3*b;peak=max(peak,v);dd=max(dd,(peak-v)/peak)
            terminal.append(v);drawdowns.append(dd)
    np.testing.assert_allclose(r['terminal_equity'],terminal,rtol=2e-14,atol=1e-12)
    np.testing.assert_allclose(r['max_drawdowns'],drawdowns,atol=1e-14)


def test_numeric_overflow_context():
    with pytest.raises(ValueError,match='batch starting 0, step 1'):
        simulate(['A'],[1],[100],0,[1000],[[0]],n_paths=2000,n_steps=1,confidences=['.95'])


def test_primary_arrays_readonly(scenario,config):
    r,_=execute(scenario,config)
    for k in ('terminal_equity','max_drawdowns','preview_ids','preview_equity'):
        assert not r[k].flags.writeable


def test_diagnostics_and_comparisons_preserve_primary(scenario,config):
    r,inputs=execute(scenario,config);before=r['terminal_equity'].copy();original_summary=r['summary'].copy()
    checked,_=diagnose(r,inputs,resamples=200)
    assert r['diagnostics']['status']=='NOT ASSESSED'
    assert checked['diagnostics']['status'] in ['NO INSTABILITY FLAG','INSTABILITY FLAGGED']
    reps=checked['diagnostics']['replicates'];assert len(reps)==2 and reps[0]['seed']!=reps[1]['seed']
    for rep in reps:assert rep['summary']['n_paths']==config['n_paths']
    compared,_=compare(checked,inputs);assert len(compared['comparisons'])==4
    assert all(x['summary']['initial_equity']==r['summary']['initial_equity'] for x in compared['comparisons'])
    assert compared['comparisons'][0]['summary']==r['summary']
    np.testing.assert_array_equal(before,r['terminal_equity']);assert r['summary']==original_summary


def test_diagnostics_cancellation_no_primary_mutation(scenario,config):
    r,i=execute(scenario,config)
    with pytest.raises(InterruptedError):diagnose(r,i,cancel=lambda:True,resamples=200)
    assert r['diagnostics']['status']=='NOT ASSESSED'


def test_unstable_seed_flag(monkeypatch,scenario,config):
    from risklab.core import diagnostics
    r,i=execute(scenario,config)
    real=diagnostics.simulate
    def shifted(**kwargs):
        result=real(**kwargs)
        for tail in result['summary']['tails'].values():tail['var']+=100000;tail['es']+=100000
        return result
    monkeypatch.setattr(diagnostics,'simulate',shifted)
    checked,_=diagnose(r,i,resamples=200)
    assert checked['diagnostics']['status']=='INSTABILITY FLAGGED'
    assert checked['diagnostics']['flags']


def test_stochastic_repeatability(scenario,config):
    a,_=execute(scenario,config);b,_=execute(scenario,config)
    np.testing.assert_array_equal(a['terminal_equity'],b['terminal_equity'])
    np.testing.assert_array_equal(a['preview_equity'],b['preview_equity'])
    assert a['summary']==b['summary']
