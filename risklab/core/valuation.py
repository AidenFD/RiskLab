"""Fixed-share valuation. No display rounding in the numerical model."""
import numpy as np
from .risk import vector


def equity_paths(prices, quantities, cash):
    p = np.asarray(prices,dtype=np.float64)
    q = vector(quantities,'quantities')
    c = vector([cash],'cash')[0]
    if p.ndim != 3 or p.shape[2] != len(q) or not p.shape[0] or not p.shape[1]:
        raise ValueError('prices must have shape paths, steps including zero, assets')
    if not np.isfinite(p).all() or (p<=0).any() or (q<0).any() or c<0:
        raise ValueError('invalid price, quantity or cash')
    with np.errstate(over='raise',invalid='raise'):
        result = c + p@q
    if not np.isfinite(result).all() or (result<=0).any():
        raise ValueError('equity must be finite and positive')
    return result


def maximum_drawdowns(equity):
    a = np.asarray(equity,dtype=np.float64)
    if a.ndim != 2 or not a.shape[0] or not a.shape[1] or not np.isfinite(a).all() or (a<=0).any():
        raise ValueError('equity must be a positive finite paths-by-steps matrix')
    peaks = np.maximum.accumulate(a,axis=1)
    return np.max((peaks-a)/peaks,axis=1)
