"""Reproducibly generate SYNTHETIC examples; no vendor history is implied."""
import csv,io,json,sys
from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab.core.calibration import validate_history


def generate(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    dates=[];d=date(2021,1,1)
    while len(dates)<757:
        if d.weekday()<5:dates.append(d.isoformat())
        d+=timedelta(days=1)
    symbols=['SYN-A','SYN-B','SYN-C']
    cov=np.array([[.0001,.00003,.00001],[.00003,.000225,.00002],[.00001,.00002,.000064]])
    vals,vec=np.linalg.eigh(cov);rng=np.random.Generator(np.random.PCG64(20260924))
    logs=np.array([.00015,.0001,.00008])+rng.standard_normal((756,3))@(vec*np.sqrt(vals)).T
    prices=np.vstack(([100,80,50],np.array([100,80,50])*np.exp(np.cumsum(logs,axis=0))))
    out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');writer.writerow(['Date']+symbols)
    for d,p in zip(dates,prices):writer.writerow([d]+[repr(float(x)) for x in p])
    text=out.getvalue();meta={'schema_version':1,'symbols':symbols,'currency':'USD','price_basis':'RAW',
        'action_free':True,'source_kind':'SYNTHETIC','calendar_id':'SYNTHETIC_WEEKDAYS_NOT_EXCHANGE_VERIFIED',
        'expected_sessions':dates,'generator':'PCG64','seed':20260924,
        'description':'Fictional action-free demo history, not real securities or observed market returns.'}
    portfolio={'as_of_session':dates[-1],'currency':'USD','cash':'5000',
        'positions':[{'symbol':s,'instrument_type':'EQUITY','quantity':str(q),'initial_price':repr(float(p))} for s,q,p in zip(symbols,[100,150,200],prices[-1])]}
    history={'schema_version':1,'name':'Correlated three-asset synthetic history','portfolio':portfolio,
        'model':{'kind':'HISTORY'},'history':{'csv_text':text,'metadata':meta}}
    (destination/'SYNTHETIC_3A.csv').write_text(text,encoding='utf-8')
    (destination/'SYNTHETIC_3A.meta.json').write_text(json.dumps(meta,indent=2))
    cases={'correlated_history':history}
    def manual(name,syms,quantities,initial,means,covariance,cash='5000'):
        return {'schema_version':1,'name':name,'portfolio':{'currency':'USD','as_of_session':dates[-1],'cash':cash,
            'positions':[{'symbol':s,'instrument_type':'EQUITY','quantity':str(q),'initial_price':str(p)} for s,q,p in zip(syms,quantities,initial)]},
            'model':{'kind':'MANUAL','symbols':syms,'daily_log_mean':means,'daily_log_cov':covariance}}
    cases['deterministic']=manual('Deterministic constant equity',['SYN-A'],[100],[100],[0],[[0]])
    cases['deterministic_growth']=manual('Deterministic log growth',['SYN-A'],[100],[100],[.0005],[[0]])
    cases['low_volatility']=manual('Low-volatility hypothetical',['SYN-A'],[100],[100],[0],[[.000025]])
    cases['high_volatility']=manual('High-volatility hypothetical',['SYN-A'],[100],[100],[0],[[.0004]])
    cases['singular']=manual('Perfectly correlated assets',['SYN-A','SYN-B'],[100,100],[100,100],[0,0],[[.0001,.0001],[.0001,.0001]])
    cases['all_cash']=manual('All-cash exposure',['SYN-A'],[0],[100],[0],[[.0004]],cash='25000')
    for name,obj in cases.items():(destination/f'{name}.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
    invalid=destination/'invalid';invalid.mkdir(exist_ok=True)
    bad=deepcopy(cases['singular']);bad['model']['daily_log_cov']=[[.0001,.0002],[.0002,.0001]]
    (invalid/'indefinite_covariance.json').write_text(json.dumps(bad,indent=2))
    for name,change in [('duplicate_symbol',lambda s:s['portfolio']['positions'][1].update(symbol='SYN-A')),
                        ('unsupported_instrument',lambda s:s['portfolio']['positions'][0].update(instrument_type='OPTION')),
                        ('negative_cash',lambda s:s['portfolio'].update(cash='-1'))]:
        bad=deepcopy(cases['singular']);change(bad);(invalid/f'{name}.json').write_text(json.dumps(bad,indent=2))
    bad=deepcopy(history);bad['history']['csv_text']='\n'.join(text.splitlines()[:20]+text.splitlines()[21:])+'\n'
    (invalid/'missing_session.json').write_text(json.dumps(bad,indent=2))
    bad=deepcopy(history);bad['history']['metadata']['price_basis']='TOTAL_RETURN_INDEX'
    (invalid/'unsupported_basis.json').write_text(json.dumps(bad,indent=2))
    (invalid/'nonfinite.json').write_text('{"schema_version":1,"cash":NaN}')
    (invalid/'insufficient_tail_config.json').write_text(json.dumps({'n_paths':2000,'confidences':['0.99']}))
    return cases

if __name__=='__main__':
    base=Path(__file__).resolve().parents[1]
    generate(base/'risklab'/'resources'/'examples')
    generate(base/'examples')
