"""Strict aligned price import and daily log calibration."""
import csv,json
from datetime import date
from pathlib import Path
import numpy as np

def load_history(path,symbols):
    path=Path(path)
    meta=json.loads(path.with_suffix('.meta.json').read_text())
    if meta.get('price_basis')!='RAW' or meta.get('currency')!='USD' or meta.get('action_free') is not True:
        raise ValueError('RAW USD action-free metadata required')
    if meta.get('source_kind') not in ('SYNTHETIC','USER_DECLARED'):
        raise ValueError('unsupported provenance')
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f); header=next(reader)
        if len(header)!=len(set(header)) or set(header)!=set(['Date']+list(symbols)):
            raise ValueError('CSV must contain Date and each symbol exactly once')
        rows=list(reader)
    if any(len(r)!=len(header) for r in rows):raise ValueError('ragged CSV')
    dates=[r[header.index('Date')] for r in rows]
    if dates!=meta.get('expected_sessions') or dates!=sorted(set(dates)):
        raise ValueError('session gap, duplicate or ordering error')
    for d in dates:date.fromisoformat(d)
    prices=np.array([[float(r[header.index(s)]) for s in symbols] for r in rows])
    if len(prices)<max(60,10*len(symbols))+1 or not np.isfinite(prices).all() or (prices<=0).any():
        raise ValueError('insufficient history or invalid prices')
    returns=np.diff(np.log(prices),axis=0)
    return {'dates':dates,'prices':prices,'estimated_mean':returns.mean(axis=0),
            'covariance':np.atleast_2d(np.cov(returns,rowvar=False,ddof=1)),'metadata':meta}
