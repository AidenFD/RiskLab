"""Explicit finite-sample risk conventions from the RiskLab design."""
from decimal import Decimal, ROUND_CEILING
import math
import numpy as np


def vector(values, name):
    if any(isinstance(v, (bool, np.bool_)) for v in np.asarray(values, dtype=object).flat):
        raise ValueError(f'{name}: booleans are not numbers')
    a = np.asarray(values, dtype=np.float64)
    if a.ndim != 1 or not len(a) or not np.isfinite(a).all():
        raise ValueError(f'{name}: expected nonempty finite vector')
    return a


def tail_indices(n, confidence):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('sample count must be a positive integer')
    try:
        alpha = Decimal(str(confidence))
        if not alpha.is_finite() or not 0 < alpha < 1:
            raise ValueError('confidence must lie strictly between zero and one')
    except Exception as exc:
        raise ValueError('invalid confidence') from exc
    ceil = lambda x: int(x.to_integral_value(rounding=ROUND_CEILING))
    return ceil(alpha*n), ceil((1-alpha)*n)


def summarize(terminal_equity, max_drawdowns, initial_equity, confidences=('0.95','0.99')):
    terminal = vector(terminal_equity, 'terminal equity')
    dd = vector(max_drawdowns, 'drawdowns')
    initial = vector([initial_equity], 'initial equity')[0]
    if initial <= 0 or (terminal <= 0).any() or terminal.shape != dd.shape or ((dd < 0)|(dd > 1)).any():
        raise ValueError('invalid equity or drawdown domain')
    losses = np.sort(initial-terminal)
    n = len(losses)
    p = float(np.mean(terminal < initial))
    z = 1.959963984540054
    denom = 1+z*z/n
    center = (p+z*z/(2*n))/denom
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    tails = {}
    for confidence in confidences:
        k,q = tail_indices(n, confidence)
        tails[str(confidence)] = {'var':float(losses[k-1]), 'es':float(np.mean(losses[-q:])),
                                 'rank':k,'tail_count':q,'tail_sufficient':q>=100}
    return {'initial_equity':float(initial),'n_paths':n,'probability_of_loss':p,
            'probability_se':math.sqrt(p*(1-p)/n),
            'probability_wilson_95':[max(0.,center-half),min(1.,center+half)],
            'mean_terminal_equity':float(np.mean(terminal)),
            'median_terminal_equity':float(np.median(terminal)),
            'tails':tails,'drawdown_quantile_method':'linear',
            'drawdown_quantiles':{str(q):float(np.quantile(dd,q,method='linear')) for q in (.5,.95,.99)},
            'stability':'NOT ASSESSED'}
