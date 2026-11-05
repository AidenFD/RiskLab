"""Batched correlated daily log returns; batch size is part of RNG contract."""
import numpy as np
from .risk import vector, tail_indices, summarize


def factor_covariance(cov):
    a = np.asarray(cov,dtype=np.float64)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not len(a) or not np.isfinite(a).all():
        raise ValueError('invalid covariance dimensions or values')
    tolerance = max(1e-16,1e-10*float(np.max(np.abs(a))))
    if np.max(np.abs(a-a.T)) > tolerance:
        raise ValueError('covariance is materially asymmetric')
    a = (a+a.T)/2
    values, vectors = np.linalg.eigh(a)
    tolerance = max(1e-16,1e-10*float(np.max(np.abs(values))))
    if values[0] < -tolerance:
        raise ValueError('covariance is not positive semidefinite')
    clipped = np.maximum(values,0)
    factor = vectors*np.sqrt(clipped)
    return factor, {'original_eigenvalues':values.tolist(),'effective_eigenvalues':clipped.tolist(),
                    'psd_tolerance':tolerance,'effective_covariance':(factor@factor.T).tolist(),
                    'method':'eigh'}


def simulate(symbols, quantities, prices, cash, means, covariance, *, n_paths=10000,
             n_steps=252, seed=42, batch_size=512, preview_count=20, confidences=('0.95','0.99'),
             cancel=lambda:False, progress=lambda n,total:None):
    if not 1<=len(symbols)<=10 or len(set(symbols))!=len(symbols) or any(not isinstance(s,str) or not s.strip() for s in symbols):
        raise ValueError('one to ten unique symbols required')
    for name,x,lo,hi in [('paths',n_paths,1,1000000),('steps',n_steps,1,252),('seed',seed,0,2**63-1),
                         ('batch size',batch_size,1,10000),('preview count',preview_count,0,100)]:
        if isinstance(x,bool) or not isinstance(x,int) or not lo<=x<=hi:
            raise ValueError(f'invalid {name}')
    if not confidences or any(tail_indices(n_paths,c)[1]<100 for c in confidences):
        raise ValueError('each selected tail requires at least 100 paths')
    q,p,m = [vector(x,name) for x,name in [(quantities,'quantities'),(prices,'prices'),(means,'means')]]
    c = vector([cash],'cash')[0]
    if any(len(x)!=len(symbols) for x in (q,p,m)) or (q<0).any() or (p<=0).any() or c<0:
        raise ValueError('invalid portfolio or means')
    order=np.argsort(symbols); q,p,m=q[order],p[order],m[order]
    cov=np.asarray(covariance,dtype=np.float64)
    if cov.shape!=(len(symbols),len(symbols)):
        raise ValueError('covariance dimensions do not match symbols')
    factor,diagnostics=factor_covariance(cov[np.ix_(order,order)])
    v0=float(c+p@q)
    if not np.isfinite(v0) or v0<=0:
        raise ValueError('initial equity must be finite and positive')
    rng=np.random.Generator(np.random.PCG64(seed))
    count=min(preview_count,n_paths)
    # Deterministic evenly spaced IDs do not consume simulation RNG.
    ids=np.linspace(0,n_paths-1,count,dtype=int) if count else np.array([],dtype=int)
    preview=np.empty((count,n_steps+1)); preview[:,0]=v0
    terminal=np.empty(n_paths); drawdown=np.empty(n_paths)
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        for start in range(0,n_paths,batch_size):
            end=min(n_paths,start+batch_size); size=end-start
            values=np.tile(p,(size,1)); peak=np.full(size,v0); dd=np.zeros(size)
            pick=np.flatnonzero((ids>=start)&(ids<end)); local=ids[pick]-start
            for t in range(n_steps):
                if cancel(): raise InterruptedError('simulation cancelled')
                values*=np.exp(m+rng.standard_normal((size,len(symbols)))@factor.T)
                equity=c+values@q
                if not np.isfinite(values).all() or (values<=0).any() or not np.isfinite(equity).all() or (equity<=0).any():
                    raise ValueError(f'numeric failure at batch {start}, step {t+1}')
                peak=np.maximum(peak,equity); dd=np.maximum(dd,(peak-equity)/peak)
                preview[pick,t+1]=equity[local]
            terminal[start:end]=equity; drawdown[start:end]=dd
            progress(end,n_paths)
    return {'terminal_equity':terminal,'max_drawdowns':drawdown,'preview_ids':ids,'preview_equity':preview,
            'summary':summarize(terminal,drawdown,v0,confidences),'covariance_diagnostics':diagnostics,
            'canonical_symbols':sorted(symbols)}
