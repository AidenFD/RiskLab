"""Frozen-input experiments, scenario comparison, and provenance."""
from __future__ import annotations
import copy
import json
from dataclasses import asdict
import numpy as np
from risklab.core.inputs import validate_scenario,ValidationError,parse_json
from risklab.core.models import SimulationConfig
from risklab.core.simulation import validate_config,simulate
from risklab.core.diagnostics import assess_stability


def default_config():
    d=asdict(SimulationConfig());d['confidences']=list(d['confidences']);return d


def prepare(scenario,config,*,persisted_model=None):
    # Serialization creates an owned input graph, rejecting NaN/Infinity and unsupported objects.
    try:
        scenario=parse_json(json.dumps(scenario,allow_nan=False))
        config=parse_json(json.dumps(config,allow_nan=False))
    except (TypeError,ValueError) as exc:
        raise ValidationError(f'Configuration cannot be serialized: {exc}') from exc
    expected=set(default_config())
    if set(config)!=expected:raise ValidationError(f'Config must contain exactly {sorted(expected)}')
    if config['drift_mode'] not in ('ZERO_LOG_MEAN','ESTIMATED_LOG_MEAN'):
        raise ValidationError('Unsupported drift mode')
    normalized={k:v for k,v in config.items() if k!='drift_mode'}
    validate_config(**normalized)
    v=validate_scenario(scenario,calibrated_parameters=persisted_model)
    means=v['estimated_mean'] if config['drift_mode']=='ESTIMATED_LOG_MEAN' else np.zeros(len(v['symbols']))
    arguments={k:v[k] for k in ('symbols','quantities','prices','cash')}
    arguments.update(means=means.tolist(),covariance=v['covariance'].tolist(),**normalized)
    resolved={'asset_order':v['symbols'],'estimated_daily_log_mean':v['estimated_mean'].tolist(),
              'applied_daily_log_mean':means.tolist(),'daily_log_cov':v['covariance'].tolist(),
              'source_kind':v['provenance'],'estimation_dates':v['estimation_dates'],
              'n_observations':v['n_observations'],'model_id':'daily-gaussian-log-fixed-holdings-v1'}
    return arguments,{'scenario':scenario,'config':config,'resolved_model':resolved}


def execute(scenario,config,*,cancel=lambda:False,progress=lambda phase,n,total:None):
    args,inputs=prepare(scenario,config)
    r=simulate(**args,cancel=cancel,progress=lambda n,t:progress('Primary simulation',n,t))
    r['diagnostics']={'status':'NOT ASSESSED'}
    r['comparisons']=[]
    return r,inputs


def diagnose(result,inputs,*,cancel=lambda:False,progress=lambda phase,n,total:None,resamples=300):
    args,_=prepare(inputs['scenario'],inputs['config'],persisted_model=inputs['resolved_model'])
    diagnostics=assess_stability(result,args,resamples=resamples,cancel=cancel,progress=progress)
    updated=dict(result);updated['diagnostics']=diagnostics
    return updated,copy.deepcopy(inputs)


def compare(result,inputs,*,cancel=lambda:False,progress=lambda phase,n,total:None):
    records=[]
    for label,mode,scale in [('Zero log mean','ZERO_LOG_MEAN',1.),('Estimated log mean','ESTIMATED_LOG_MEAN',1.),
                             ('Low volatility (0.5x)','ZERO_LOG_MEAN',.5),('High volatility (2x)','ZERO_LOG_MEAN',2.)]:
        config=copy.deepcopy(inputs['config']);config['drift_mode']=mode
        args,resolved=prepare(inputs['scenario'],config,persisted_model=inputs['resolved_model'])
        args['covariance']=(np.array(args['covariance'])*scale**2).tolist()
        args['preview_count']=0
        r=simulate(**args,cancel=cancel,progress=lambda n,t,lab=label:progress(lab,n,t))
        records.append({'label':label,'drift_mode':mode,'volatility_scale':scale,
                        'summary':r['summary'],'seed':args['seed'],'n_steps':args['n_steps'],
                        'covariance':args['covariance'],'applied_mean':args['means'],
                        'comparison_design':'paired common random seed, not independent stability replicates'})
    updated=dict(result);updated['comparisons']=records
    return updated,copy.deepcopy(inputs)
