"""Portable atomic run publication; no stochastic rerun when reopening."""
import hashlib,json,os,shutil,tempfile,uuid
from pathlib import Path
import numpy as np
from .risk import summarize

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,obj):
    with path.open('w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())

def save_run(result,inputs,root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.staging-',dir=root))
    run_id=uuid.uuid4().hex
    try:
        write_json(staging/'inputs.json',inputs)
        write_json(staging/'summary.json',result['summary'])
        write_json(staging/'model_diagnostics.json',result['covariance_diagnostics'])
        with (staging/'outcomes.npz').open('wb') as f:
            np.savez_compressed(f,**{k:result[k] for k in ['terminal_equity','max_drawdowns','preview_ids','preview_equity']})
            f.flush();os.fsync(f.fileno())
        np.savetxt(staging/'terminal_outcomes.csv',np.column_stack((np.arange(len(result['terminal_equity'])),result['terminal_equity'],result['summary']['initial_equity']-result['terminal_equity'],result['max_drawdowns'])),delimiter=',',header='path_id,terminal_equity,loss,max_drawdown',comments='')
        names=['inputs.json','summary.json','model_diagnostics.json','outcomes.npz','terminal_outcomes.csv']
        write_json(staging/'manifest.json',{'schema':1,'run_id':run_id,'numpy':np.__version__,'files':{n:digest(staging/n) for n in names}})
        write_json(staging/'COMPLETED',{'manifest_sha256':digest(staging/'manifest.json')})
        load_run(staging)
        target=root/run_id; staging.rename(target)
        return target
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True);raise

def load_run(path):
    path=Path(path)
    marker=json.loads((path/'COMPLETED').read_text())
    if marker['manifest_sha256']!=digest(path/'manifest.json'):raise ValueError('manifest checksum mismatch')
    manifest=json.loads((path/'manifest.json').read_text())
    required={'inputs.json','summary.json','model_diagnostics.json','outcomes.npz','terminal_outcomes.csv'}
    if manifest.get('schema')!=1 or set(manifest['files'])!=required:raise ValueError('unsupported or incomplete manifest')
    for name,sha in manifest['files'].items():
        if digest(path/name)!=sha:raise ValueError(f'corrupt payload: {name}')
    summary=json.loads((path/'summary.json').read_text())
    with np.load(path/'outcomes.npz',allow_pickle=False) as data:r={k:data[k].copy() for k in data.files}
    checked=summarize(r['terminal_equity'],r['max_drawdowns'],summary['initial_equity'],list(summary['tails']))
    if checked!=summary:raise ValueError('summary reconciliation failed')
    r['summary']=summary;r['covariance_diagnostics']=json.loads((path/'model_diagnostics.json').read_text())
    return r,json.loads((path/'inputs.json').read_text())
