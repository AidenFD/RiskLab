"""Schema-2 portable results: verified publication, immutable reopening, safe ZIP export."""
from __future__ import annotations
import csv
import hashlib
import json
import os
import platform
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from risklab import __version__
from .inputs import read_json,ValidationError
from .risk import summarize

SCHEMA=2
REQUIRED={'scenario.json','config.json','model_parameters.json','summary.json','outcomes.npz',
          'terminal_outcomes.csv','diagnostics.json','comparisons.json','sampling.json'}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def object_hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def write_json(path,obj):
    with Path(path).open('w',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def validate_result(result,inputs):
    from risklab.services.experiments import prepare
    args,normalized=prepare(inputs['scenario'],inputs['config'],persisted_model=inputs['resolved_model'])
    if normalized!=inputs:raise ValidationError('Saved resolved model does not match source inputs')
    from .simulation import factor_covariance
    order=np.argsort(args['symbols']);canonical=sorted(args['symbols'])
    _,expected_diagnostics=factor_covariance(np.array(args['covariance'])[np.ix_(order,order)])
    if result.get('canonical_symbols')!=canonical or result.get('declared_symbols')!=args['symbols'] or result.get('canonical_to_declared')!=order.tolist():
        raise ValidationError('Saved asset mapping mismatch')
    observed_cov=np.array(result['covariance_diagnostics']['effective_covariance'])
    if observed_cov.shape!=(len(canonical),len(canonical)) or not np.allclose(observed_cov,expected_diagnostics['effective_covariance'],rtol=1e-10,atol=1e-16):
        raise ValidationError('Saved effective covariance mismatch')
    sampling=result.get('sampling',{})
    if sampling.get('generator')!='PCG64' or sampling.get('seed')!=args['seed'] or sampling.get('batch_size')!=args['batch_size']:
        raise ValidationError('Saved sampling contract mismatch')
    s=result['summary'];n=args['n_paths'];steps=args['n_steps']
    arrays={k:np.asarray(result[k]) for k in ('terminal_equity','max_drawdowns','preview_ids','preview_equity')}
    terminal,dd,ids,preview=(arrays[k] for k in arrays)
    if terminal.shape!=(n,) or dd.shape!=(n,) or ids.shape!=(min(args['preview_count'],n),) or preview.shape!=(len(ids),steps+1):
        raise ValidationError('Saved result dimensions do not match configuration')
    if not np.issubdtype(ids.dtype,np.integer) or len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=n):
        raise ValidationError('Invalid preview path identifiers')
    expected_ids=np.linspace(0,n-1,min(args['preview_count'],n),dtype=np.int64) if args['preview_count'] else np.array([],dtype=np.int64)
    if not np.array_equal(ids,expected_ids):raise ValidationError('Preview selection rule does not reconcile')
    initial=float(args['cash']+np.dot(args['prices'],args['quantities']))
    if not np.isclose(initial,s['initial_equity'],rtol=1e-12,atol=1e-10):raise ValidationError('Initial equity mismatch')
    checked=summarize(terminal,dd,s['initial_equity'],args['confidences'])
    # Float summation can differ slightly after a move across hardware; compare within declared tolerance.
    def equal(a,b):
        if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(equal(a[k],b[k]) for k in a)
        if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
        if isinstance(a,(float,int)) and not isinstance(a,bool):return isinstance(b,(float,int)) and np.isclose(a,b,rtol=1e-11,atol=1e-9)
        return a==b
    if not equal(checked,s):raise ValidationError('Summary does not reconcile with complete stored outcomes')
    if not np.isfinite(preview).all() or (preview<=0).any():raise ValidationError('Invalid preview equity')
    if len(ids):
        from .valuation import maximum_drawdowns
        if not np.allclose(preview[:,0],initial,rtol=1e-12,atol=1e-10) or not np.array_equal(preview[:,-1],terminal[ids]) or not np.allclose(maximum_drawdowns(preview),dd[ids],rtol=1e-11,atol=1e-12):
            raise ValidationError('Preview paths do not reconcile with primary outcomes')
    if result.get('diagnostics',{}).get('status') not in ('NOT ASSESSED','NO INSTABILITY FLAG','INSTABILITY FLAGGED'):
        raise ValidationError('Incomplete diagnostics cannot be published as complete')
    return normalized


def save_run(result,inputs,root,*,cancel=lambda:False):
    validate_result(result,inputs)
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.staging-',dir=root));run_id=uuid.uuid4().hex
    try:
        payloads={'scenario.json':inputs['scenario'],'config.json':inputs['config'],
                  'model_parameters.json':{'resolved':inputs['resolved_model'],'covariance':result['covariance_diagnostics'],
                     'canonical_symbols':result['canonical_symbols'],'declared_symbols':result['declared_symbols'],
                     'canonical_to_declared':result['canonical_to_declared']},
                  'summary.json':result['summary'],'sampling.json':result['sampling'],
                  'diagnostics.json':result.get('diagnostics',{'status':'NOT ASSESSED'}),
                  'comparisons.json':result.get('comparisons',[])}
        for name,obj in payloads.items():
            if cancel():raise InterruptedError('Cancelled before publication')
            write_json(staging/name,obj)
        with (staging/'outcomes.npz').open('wb') as f:
            np.savez_compressed(f,**{k:result[k] for k in ('terminal_equity','max_drawdowns','preview_ids','preview_equity')})
            f.flush();os.fsync(f.fileno())
        with (staging/'terminal_outcomes.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(['path_id','terminal_equity','loss','max_drawdown'])
            initial=result['summary']['initial_equity']
            for i,(v,dd) in enumerate(zip(result['terminal_equity'],result['max_drawdowns'])):
                writer.writerow([i,repr(float(v)),repr(float(initial-v)),repr(float(dd))])
            f.flush();os.fsync(f.fileno())
        names=set(REQUIRED)
        history=inputs['scenario'].get('history')
        if history is not None:
            with (staging/'history.csv').open('w',encoding='utf-8',newline='') as f:
                f.write(history['csv_text']);f.flush();os.fsync(f.fileno())
            write_json(staging/'history.meta.json',history['metadata']);names.update(['history.csv','history.meta.json'])
        manifest={'schema_version':SCHEMA,'run_id':run_id,'created_utc':datetime.now(timezone.utc).isoformat(),
                  'status':'COMPLETED','app_version':__version__,'python':platform.python_version(),
                  'numpy':np.__version__,'scenario_name':inputs['scenario'].get('name','Untitled'),
                  'source_kind':inputs['resolved_model']['source_kind'],'input_hash':object_hash(inputs['scenario']),
                  'config_hash':object_hash(inputs['config']),'n_paths':inputs['config']['n_paths'],
                  'n_steps':inputs['config']['n_steps'],'seed':inputs['config']['seed'],
                  'drift_mode':inputs['config']['drift_mode'],'symbols':inputs['resolved_model']['asset_order'],
                  'diagnostics_status':payloads['diagnostics.json']['status'],
                  'files':{n:digest(staging/n) for n in sorted(names)}}
        write_json(staging/'manifest.json',manifest)
        write_json(staging/'COMPLETED',{'manifest_sha256':digest(staging/'manifest.json')})
        load_run(staging)
        if cancel():raise InterruptedError('Cancelled before publication')
        # Atomic rename is the publication commit point. Cancellation after this is too late.
        target=root/run_id;staging.rename(target)
        return target
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True);raise


def load_run(path):
    path=Path(path)
    marker=read_json(path/'COMPLETED')
    if marker.get('manifest_sha256')!=digest(path/'manifest.json'):raise ValidationError('Manifest checksum mismatch')
    manifest=read_json(path/'manifest.json')
    names=set(manifest.get('files',{}))
    if manifest.get('schema_version')!=SCHEMA or manifest.get('status')!='COMPLETED' or names not in (REQUIRED,REQUIRED|{'history.csv','history.meta.json'}):
        raise ValidationError('Unsupported or incomplete manifest')
    for name,sha in manifest['files'].items():
        f=path/name
        if f.is_symlink() or not f.is_file() or digest(f)!=sha:raise ValidationError(f'Corrupt or missing payload: {name}')
    scenario,config=read_json(path/'scenario.json'),read_json(path/'config.json')
    if object_hash(scenario)!=manifest['input_hash'] or object_hash(config)!=manifest['config_hash']:
        raise ValidationError('Input/config fingerprint mismatch')
    model=read_json(path/'model_parameters.json')
    with zipfile.ZipFile(path/'outcomes.npz') as archive:
        if sum(x.file_size for x in archive.infolist())>10000000:
            raise ValidationError('Outcome arrays exceed the v1 resource limit')
    with np.load(path/'outcomes.npz',allow_pickle=False) as data:
        if set(data.files)!={'terminal_equity','max_drawdowns','preview_ids','preview_equity'}:raise ValidationError('Unexpected outcome arrays')
        r={k:data[k].copy() for k in data.files}
    r.update(summary=read_json(path/'summary.json'),sampling=read_json(path/'sampling.json'),
             covariance_diagnostics=model['covariance'],canonical_symbols=model['canonical_symbols'],
             declared_symbols=model['declared_symbols'],canonical_to_declared=model['canonical_to_declared'],
             diagnostics=read_json(path/'diagnostics.json'),comparisons=read_json(path/'comparisons.json'))
    inputs={'scenario':scenario,'config':config,'resolved_model':model['resolved']}
    validate_result(r,inputs)
    if 'history' in scenario:
        if (path/'history.csv').read_text(encoding='utf-8')!=scenario['history']['csv_text'].replace('\r\n','\n') or read_json(path/'history.meta.json')!=scenario['history']['metadata']:
            raise ValidationError('Saved history payload mismatch')
    elif 'history.csv' in names:raise ValidationError('Unexpected history payload')
    with (path/'terminal_outcomes.csv').open(newline='',encoding='utf-8') as f:
        reader=csv.reader(f)
        if next(reader)!=['path_id','terminal_equity','loss','max_drawdown']:raise ValidationError('Bad outcomes CSV header')
        count=0
        for count,row in enumerate(reader,1):
            i=count-1
            if i>=len(r['terminal_equity']) or len(row)!=4 or int(row[0])!=i:raise ValidationError('Bad CSV path ID/count')
            expected=[r['terminal_equity'][i],r['summary']['initial_equity']-r['terminal_equity'][i],r['max_drawdowns'][i]]
            if not np.array_equal(np.array(row[1:],dtype=float),expected):raise ValidationError('CSV outcomes do not reconcile')
        if count!=len(r['terminal_equity']):raise ValidationError('CSV path count mismatch')
    for k in ('terminal_equity','max_drawdowns','preview_ids','preview_equity'):r[k].setflags(write=False)
    return r,inputs


def export_archive(runpath,destination):
    load_run(runpath)
    runpath,destination=Path(runpath),Path(destination)
    if destination.resolve().is_relative_to(runpath.resolve()):raise ValidationError('Choose a ZIP outside the saved run folder')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        manifest=read_json(runpath/'manifest.json')
        for name in sorted(set(manifest['files'])|{'manifest.json','COMPLETED'}):
            archive.write(runpath/name,f'{runpath.name}/{name}')
    return destination
