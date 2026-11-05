import copy,json
import numpy as np
import pytest
from risklab.core.inputs import validate_scenario,parse_json,array
from risklab.core.calibration import validate_history,fit_model
from risklab.services.experiments import prepare
from risklab.core.simulation import factor_covariance,validate_config
from risklab.core.risk import summarize,tail_indices

@pytest.mark.parametrize('text',['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'])
def test_strict_json(text):
    with pytest.raises(ValueError):parse_json(text)

@pytest.mark.parametrize('mutation',[
 lambda s:s['portfolio'].update(currency='EUR'),
 lambda s:s['portfolio'].update(cash='-1'),
 lambda s:s['portfolio'].update(cash=True),
 lambda s:s['portfolio'].update(cash='inf'),
 lambda s:s['portfolio'].update(as_of_session='2023-2-3'),
 lambda s:s['portfolio']['positions'][0].update(instrument_type='OPTION'),
 lambda s:s['portfolio']['positions'][0].update(quantity='-0.1'),
 lambda s:s['portfolio']['positions'][0].update(quantity=True),
 lambda s:s['portfolio']['positions'][0].update(initial_price=0),
 lambda s:s['portfolio']['positions'][0].update(symbol=''),
 lambda s:s['portfolio']['positions'][1].update(symbol='SYN-A'),
 lambda s:s['portfolio']['positions'][0].update(initial_price=1),
 lambda s:s['model'].update(kind='GBM_ARITHMETIC'),
 lambda s:s['history']['metadata'].update(price_basis='TOTAL_RETURN_INDEX'),
 lambda s:s['history']['metadata'].update(action_free=False),
 lambda s:s['history']['metadata'].update(source_kind='VERIFIED'),
 lambda s:s['history']['metadata'].update(calendar_id=''),
 lambda s:s['history']['metadata']['expected_sessions'].pop(20),
 lambda s:s['history'].update(csv_text=s['history']['csv_text'].replace('Date,SYN-A','Date,Date')),
 lambda s:s['history'].update(csv_text=s['history']['csv_text'].replace(',100.0,',',nan,',1)),
 lambda s:s.update(schema_version=True),
])
def test_bad_scenarios(scenario,mutation):
    mutation(scenario)
    with pytest.raises((ValueError,KeyError)):validate_scenario(scenario)

@pytest.mark.parametrize('bad',[[[1,2],[3]],[[True,0],[0,1]],[[float('nan')]],[[1,2,3],[1,2,3]]])
def test_covariance_shape_and_values(bad):
    with pytest.raises(ValueError):factor_covariance(bad)

@pytest.mark.parametrize('cov',[[[1,2],[2,1]],[[.0001,.0002],[.0002,.0001]],[[1,0],[.1,1]]])
def test_materially_invalid_covariance(cov):
    with pytest.raises(ValueError):factor_covariance(cov)


def test_tiny_correction_recorded():
    f,d=factor_covariance([[.0001,0],[0,-1e-17]])
    assert d['corrected'] and d['original_eigenvalues'][0]<0
    assert d['effective_eigenvalues'][0]==0
    np.testing.assert_allclose(f@f.T,d['effective_covariance'])


def test_sample_covariance_centering():
    r=np.array([[1.,2.],[3.,8.],[5.,5.]])
    m,c=fit_model(r)
    np.testing.assert_array_equal(m,[3,5]);np.testing.assert_array_equal(c,[[4,3],[3,9]])
    one_m,one_c=fit_model(r[:,:1]);assert one_c.shape==(1,1);assert one_c[0,0]==4


def test_zero_mode_preserves_estimated_covariance(scenario,config):
    a,ia=prepare(scenario,config);config['drift_mode']='ESTIMATED_LOG_MEAN';b,ib=prepare(scenario,config)
    assert a['covariance']==b['covariance'];assert a['means']==[0,0,0];assert b['means']!=a['means']
    assert ia['resolved_model']['estimated_daily_log_mean']==ib['resolved_model']['estimated_daily_log_mean']


def test_history_gap_no_intersection(scenario):
    rows=scenario['history']['csv_text'].splitlines();rows.pop(23);scenario['history']['csv_text']='\n'.join(rows)
    with pytest.raises(ValueError,match='session'):validate_scenario(scenario)


def test_weekend_adjacency_is_declared(scenario):
    v=validate_scenario(scenario);assert v['n_observations']==756

@pytest.mark.parametrize('keyword,value',[('n_paths',True),('n_steps',0),('seed',-1),('batch_size',4097),('preview_count',101),('n_paths',200001)])
def test_invalid_configuration(keyword,value):
    with pytest.raises(ValueError):validate_config(**{keyword:value})

@pytest.mark.parametrize('confidence',['0','1','NaN','Infinity',True,'-0.1'])
def test_invalid_confidence(confidence):
    with pytest.raises(ValueError):tail_indices(10000,confidence)


def test_tail_boundary_and_ties():
    assert tail_indices(10000,'0.99')==(9900,100)
    s=summarize([100,100,100],[0,0,0],100,['.8']);assert s['probability_of_loss']==0
    assert s['tails']['.8']['var']==s['tails']['.8']['es']==0
    assert s['probability_wilson_95'][1]>0


def test_minimum_history_and_unsupported_types(scenario):
    scenario['history']['metadata']['expected_sessions']=scenario['history']['metadata']['expected_sessions'][:30]
    scenario['history']['csv_text']='\n'.join(scenario['history']['csv_text'].splitlines()[:31])
    with pytest.raises(ValueError,match='60'):validate_scenario(scenario)


def test_frozen_prepare_input_copy(scenario,config):
    _,i=prepare(scenario,config);scenario['portfolio']['cash']='0';config['n_paths']=9999
    assert i['scenario']['portfolio']['cash']=='5000';assert i['config']['n_paths']==2000


def test_tiny_scale_materially_indefinite_is_not_repaired():
    with pytest.raises(ValueError):factor_covariance([[1e-20,2e-20],[2e-20,1e-20]])


def test_schema_integer_required(scenario):
    scenario['schema_version']=1.0
    with pytest.raises(ValueError):validate_scenario(scenario)
