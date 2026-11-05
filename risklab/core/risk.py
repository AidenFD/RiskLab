"""Design-defined tail statistics. Losses may be negative; drawdown is per path."""
from decimal import Decimal, ROUND_CEILING
import math
import numpy as np
from .inputs import array, number, integer, ValidationError


def vector(values, name):
    return array(values, name)


def tail_indices(n, confidence):
    integer(n, 'Sample count', 1, 1000000)
    try:
        alpha = Decimal(str(confidence))
        if not alpha.is_finite() or not 0 < alpha < 1:
            raise ValueError()
    except Exception as exc:
        raise ValidationError('Confidence must lie strictly between zero and one') from exc
    ceil = lambda x: int(x.to_integral_value(rounding=ROUND_CEILING))
    return ceil(alpha*n), ceil((1-alpha)*n)


def summarize(terminal_equity, max_drawdowns, initial_equity, confidences=('0.95','0.99')):
    terminal, dd = vector(terminal_equity,'Terminal equity'), vector(max_drawdowns,'Maximum drawdowns')
    initial = number(initial_equity,'Initial equity',positive=True)
    if (terminal<=0).any() or terminal.shape != dd.shape or ((dd<0)|(dd>1)).any():
        raise ValidationError('Invalid equity or drawdown domain')
    if not confidences or len(set(map(str,confidences))) != len(confidences):
        raise ValidationError('Distinct confidence levels required')
    losses = np.sort(initial-terminal)
    n = len(losses)
    p = float(np.mean(terminal<initial))
    z = 1.959963984540054
    denom = 1+z*z/n
    center = (p+z*z/(2*n))/denom
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    tails = {}
    for confidence in confidences:
        k,q = tail_indices(n,confidence)
        tails[str(confidence)] = {'var':float(losses[k-1]),'es':float(np.mean(losses[-q:])),
                                 'var_fraction':float(losses[k-1]/initial),
                                 'es_fraction':float(np.mean(losses[-q:])/initial),
                                 'rank':k,'tail_count':q,'tail_sufficient':q>=100}
    result = {'initial_equity':initial,'n_paths':n,'probability_of_loss':p,
            'probability_se':math.sqrt(p*(1-p)/n),
            'probability_wilson_95':[max(0.,center-half),min(1.,center+half)],
            'mean_terminal_equity':float(np.mean(terminal)), 'median_terminal_equity':float(np.median(terminal)),
            'terminal_quantiles':{str(q):float(np.quantile(terminal,q,method='linear')) for q in (.01,.05,.5,.95,.99)},
            'loss_mean':float(np.mean(initial-terminal)),
            'tails':tails,'drawdown_quantile_method':'linear',
            'drawdown_quantiles':{str(q):float(np.quantile(dd,q,method='linear')) for q in (.5,.95,.99)},
            'loss_convention':'initial_equity - terminal_equity; gains are negative',
            'var_convention':'ascending loss at one-based ceil(alpha*N)',
            'es_convention':'mean of largest ceil((1-alpha)*N) losses; no zero floor',
            'stability':'NOT ASSESSED'}
    def check(value):
        if isinstance(value,dict):
            for x in value.values():check(x)
        elif isinstance(value,list):
            for x in value:check(x)
        elif isinstance(value,float) and not math.isfinite(value):
            raise ValidationError('Numeric failure: nonfinite summary statistic')
    check(result)
    return result
