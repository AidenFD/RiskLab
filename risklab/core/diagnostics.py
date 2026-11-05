"""Monte Carlo sampling diagnostics, not assessments of model realism."""
import copy
import numpy as np
from .risk import tail_indices
from .inputs import integer,ValidationError
from .simulation import simulate


def assess_stability(result, arguments, *, resamples=300, cancel=lambda:False, progress=lambda phase,n,total:None):
    integer(resamples,'Bootstrap resamples',200,1000)
    primary=result['summary'];losses=primary['initial_equity']-result['terminal_equity']
    n=len(losses);levels=list(primary['tails'])
    stream=np.random.SeedSequence(arguments['seed'],spawn_key=(1701,))
    children=stream.spawn(3)
    bootstrap=np.random.Generator(np.random.PCG64(children[0]))
    ranks=[tail_indices(n,c) for c in levels]
    values={c:{'var':[],'es':[]} for c in levels}
    for b in range(resamples):
        if cancel():raise InterruptedError('Diagnostics cancelled; original primary result remains unchanged')
        sample=np.sort(losses[bootstrap.integers(0,n,size=n)])
        for c,(k,q) in zip(levels,ranks):
            values[c]['var'].append(float(sample[k-1]));values[c]['es'].append(float(np.mean(sample[-q:])))
        if b%5==0 or b==resamples-1:progress('Bootstrap',b+1,resamples)
    intervals={c:{metric:np.quantile(v,[.025,.975],method='linear').tolist() for metric,v in stats.items()} for c,stats in values.items()}
    replicates=[]
    for i,child in enumerate(children[1:],1):
        if cancel():raise InterruptedError('Diagnostics cancelled; original primary result remains unchanged')
        args=copy.deepcopy(arguments)
        derived=int(child.generate_state(1,dtype=np.uint64)[0]) & (2**63-1)
        args.update(seed=derived,preview_count=0)
        r=simulate(**args,cancel=cancel,progress=lambda done,total:progress(f'Independent replicate {i}/2',done,total))
        replicates.append({'seed':derived,'spawn_key':list(child.spawn_key),'summary':r['summary']})
    flags=[];comparisons=[]
    for c in levels:
        for metric in ('var','es'):
            estimates=[primary['tails'][c][metric]]+[r['summary']['tails'][c][metric] for r in replicates]
            spread=max(estimates)-min(estimates)
            lo,hi=intervals[c][metric]
            threshold=max(2*(hi-lo),.01*primary['initial_equity'])
            unstable=spread>threshold
            row={'confidence':c,'metric':metric,'estimate_range':spread,'threshold':threshold,'flag':unstable}
            comparisons.append(row)
            if unstable:flags.append(f'{c} {metric.upper()}: replicate range exceeds sampling tolerance')
    return {'status':'INSTABILITY FLAGGED' if flags else 'NO INSTABILITY FLAG',
            'bootstrap_resamples':resamples,'bootstrap_interval':'95% percentile; linear empirical quantile',
            'bootstrap_stream':{'entropy':arguments['seed'],'spawn_key':list(children[0].spawn_key)},
            'intervals':intervals,'replicates':replicates,'flags':flags,'comparisons':comparisons,
            'rule':'Flag if primary + two independent estimate range exceeds max(2 * primary 95% bootstrap interval width, 1% initial equity)',
            'limitations':'Heuristic finite-sample Monte Carlo stability check under one model; not a probability of correct real-world risk.'}
