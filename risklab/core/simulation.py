"""Bounded-memory correlated daily Gaussian log returns, with canonical symbols."""
from __future__ import annotations
import platform
import numpy as np
from .inputs import array, number, integer, symbols_checked, ValidationError
from .risk import vector, tail_indices, summarize


def factor_covariance(cov):
    original = array(cov,'Covariance',2)
    if original.shape[0] != original.shape[1]:
        raise ValidationError('Covariance must be square')
    tolerance = max(np.finfo(np.float64).tiny, 1e-10*float(np.max(np.abs(original))))
    asymmetry = float(np.max(np.abs(original-original.T)))
    if asymmetry > tolerance:
        raise ValidationError('Covariance is materially asymmetric')
    a = original/2 + original.T/2
    try:
        values, vectors = np.linalg.eigh(a)
    except np.linalg.LinAlgError as exc:
        raise ValidationError('Covariance factorization failed') from exc
    if not np.isfinite(values).all():
        raise ValidationError('Covariance eigenvalues are nonfinite')
    tolerance = max(np.finfo(np.float64).tiny, 1e-10*float(np.max(np.abs(values))))
    if values[0] < -tolerance:
        raise ValidationError('Covariance is not positive semidefinite')
    clipped = np.maximum(values,0)
    factor = vectors*np.sqrt(clipped)
    effective = factor@factor.T
    if not np.isfinite(effective).all():
        raise ValidationError('Effective covariance is nonfinite')
    return factor, {'original_covariance':original.tolist(), 'original_eigenvalues':values.tolist(),
                    'effective_eigenvalues':clipped.tolist(),'psd_tolerance':tolerance,
                    'symmetry_error':asymmetry,'symmetry_tolerance':max(np.finfo(np.float64).tiny,1e-10*float(np.max(np.abs(original)))),
                    'corrected':bool(np.any(values<0) or asymmetry>0),
                    'numerical_rank':int(np.count_nonzero(clipped>tolerance)),
                    'effective_covariance':effective.tolist(),'method':'eigh'}


def validate_config(n_paths=10000,n_steps=252,seed=42,batch_size=512,preview_count=20,confidences=('0.95','0.99')):
    for name,x,lo,hi in [('Paths',n_paths,1,200000),('Steps',n_steps,1,252),('Seed',seed,0,2**63-1),
                         ('Batch size',batch_size,1,4096),('Preview count',preview_count,0,100)]:
        integer(x,name,lo,hi)
    if not isinstance(confidences,(list,tuple)) or not confidences or len(confidences)>5 or len(set(map(str,confidences)))!=len(confidences):
        raise ValidationError('Select one to five distinct confidence levels')
    for c in confidences:
        _,q = tail_indices(n_paths,c)
        if q<100:
            raise ValidationError(f'{c} confidence has {q} tail paths; at least 100 required. Increase paths or lower confidence.')


def simulate(symbols,quantities,prices,cash,means,covariance,*,n_paths=10000,n_steps=252,seed=42,
             batch_size=512,preview_count=20,confidences=('0.95','0.99'),cancel=lambda:False,
             progress=lambda n,total:None):
    symbols = symbols_checked(symbols)
    validate_config(n_paths,n_steps,seed,batch_size,preview_count,confidences)
    q,p,m = [vector(x,name) for x,name in [(quantities,'Quantities'),(prices,'Prices'),(means,'Means')]]
    c = number(cash,'Cash',minimum=0)
    if any(len(x)!=len(symbols) for x in (q,p,m)) or (q<0).any() or (p<=0).any():
        raise ValidationError('Invalid portfolio dimensions or values')
    order = np.argsort(symbols)
    q,p,m = q[order],p[order],m[order]
    cov = array(covariance,'Covariance',2)
    if cov.shape != (len(symbols),len(symbols)):
        raise ValidationError('Covariance dimensions do not match symbols')
    factor,diagnostics = factor_covariance(cov[np.ix_(order,order)])
    with np.errstate(over='ignore',invalid='ignore'):
        v0 = float(c+p@q)
    if not np.isfinite(v0) or v0<=0:
        raise ValidationError('Initial equity must be finite and positive')
    rng = np.random.Generator(np.random.PCG64(seed))
    count = min(preview_count,n_paths)
    ids = np.linspace(0,n_paths-1,count,dtype=np.int64) if count else np.array([],dtype=np.int64)
    preview = np.empty((count,n_steps+1));preview[:,0]=v0
    terminal = np.empty(n_paths);drawdown=np.empty(n_paths)
    start,t = 0,0
    try:
        with np.errstate(over='raise',invalid='raise',under='ignore',divide='raise'):
            for start in range(0,n_paths,batch_size):
                end=min(n_paths,start+batch_size);size=end-start
                values=np.tile(p,(size,1));peak=np.full(size,v0);dd=np.zeros(size)
                pick=np.flatnonzero((ids>=start)&(ids<end));local=ids[pick]-start
                for t in range(n_steps):
                    if cancel():raise InterruptedError('Simulation cancelled; no result published')
                    values *= np.exp(m+rng.standard_normal((size,len(symbols)))@factor.T)
                    equity=c+values@q
                    if not np.isfinite(values).all() or (values<=0).any() or not np.isfinite(equity).all() or (equity<=0).any():
                        raise FloatingPointError('nonfinite or nonpositive prices/equity')
                    peak=np.maximum(peak,equity);dd=np.maximum(dd,(peak-equity)/peak)
                    preview[pick,t+1]=equity[local]
                terminal[start:end]=equity;drawdown[start:end]=dd
                progress(end,n_paths)
    except FloatingPointError as exc:
        raise ValidationError(f'Numeric failure at batch starting {start}, step {t+1}: {exc}') from exc
    if cancel():raise InterruptedError('Simulation cancelled; no result published')
    for a in (terminal,drawdown,ids,preview):a.setflags(write=False)
    return {'terminal_equity':terminal,'max_drawdowns':drawdown,'preview_ids':ids,'preview_equity':preview,
            'summary':summarize(terminal,drawdown,v0,confidences),'covariance_diagnostics':diagnostics,
            'canonical_symbols':sorted(symbols), 'declared_symbols':list(symbols),
            'canonical_to_declared':order.tolist(),
            'sampling':{'generator':'PCG64','seed':seed,'batch_size':batch_size,'numpy':np.__version__,
                        'python':platform.python_version(),'platform':platform.platform(),
                        'algorithm':'batch-major, step-major standard_normal @ eigh_factor.T',
                        'preview_rule':'evenly spaced path IDs; no RNG consumption',
                        'repeatability':'same NumPy build, hardware environment, algorithm, batch size and inputs'}}
