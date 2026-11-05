"""Fixed holdings and per-path drawdowns for deterministic/reference fixtures."""
import numpy as np
from .inputs import array,number,ValidationError


def equity_paths(prices, quantities, cash):
    p = array(prices,'Prices',3)
    q = array(quantities,'Quantities')
    c = number(cash,'Cash',minimum=0)
    if p.shape[2]!=len(q) or (p<=0).any() or (q<0).any():
        raise ValidationError('Invalid price shape or quantity/price domain')
    with np.errstate(over='raise',invalid='raise'):
        result=c+p@q
    if not np.isfinite(result).all() or (result<=0).any():
        raise ValidationError('Equity must be finite and positive')
    return result


def maximum_drawdowns(equity):
    a=array(equity,'Equity paths',2)
    if (a<=0).any():raise ValidationError('Equity must be positive')
    peak=np.maximum.accumulate(a,axis=1)
    return np.max((peak-a)/peak,axis=1)
