import copy,json,os,shutil,zipfile
from pathlib import Path
import numpy as np
import pytest
from risklab.services.experiments import execute
from risklab.core.export import save_run,load_run,export_archive,digest,write_json

@pytest.fixture
def completed(scenario,config):return execute(scenario,config)


def test_portable_reopen_without_sampling(completed,tmp_path,monkeypatch):
    r,i=completed;p=save_run(r,i,tmp_path/'original');q=tmp_path/'moved';shutil.copytree(p,q)
    from risklab.core import simulation
    monkeypatch.setattr(simulation,'simulate',lambda *a,**k:pytest.fail('opening must not sample'))
    from risklab.core import calibration
    monkeypatch.setattr(calibration,'fit_model',lambda *a,**k:pytest.fail('opening must not refit'))
    loaded,inputs=load_run(q)
    assert inputs==i;np.testing.assert_array_equal(loaded['terminal_equity'],r['terminal_equity'])
    archive=export_archive(q,tmp_path/'run.zip')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None

@pytest.mark.parametrize('filename',['summary.json','config.json','model_parameters.json','outcomes.npz','terminal_outcomes.csv','history.csv'])
def test_corrupt_payload_rejected(completed,tmp_path,filename):
    p=save_run(*completed,tmp_path);f=p/filename;f.write_bytes(f.read_bytes()+b'x')
    with pytest.raises((ValueError,OSError)):load_run(p)


def test_rehashed_false_summary_rejected(completed,tmp_path):
    p=save_run(*completed,tmp_path)
    s=json.loads((p/'summary.json').read_text());s['probability_of_loss']=.12345;write_json(p/'summary.json',s)
    m=json.loads((p/'manifest.json').read_text());m['files']['summary.json']=digest(p/'summary.json');write_json(p/'manifest.json',m)
    write_json(p/'COMPLETED',{'manifest_sha256':digest(p/'manifest.json')})
    with pytest.raises(ValueError,match='reconcile'):load_run(p)


def test_cancel_does_not_publish(completed,tmp_path):
    with pytest.raises(InterruptedError):save_run(*completed,tmp_path,cancel=lambda:True)
    assert not list(tmp_path.iterdir())


def test_fsync_writable_and_real_failure_cleanup(completed,tmp_path,monkeypatch):
    real=os.fsync
    def windows_style(fd):
        if os.name != 'nt':
            import fcntl
            assert fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE!=os.O_RDONLY
        return real(fd)
    monkeypatch.setattr(os,'fsync',windows_style);save_run(*completed,tmp_path/'good')
    def fail(fd):raise OSError('simulated disk sync error')
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises(OSError):save_run(*completed,tmp_path/'failed')
    assert not list((tmp_path/'failed').iterdir())


def test_failed_summary_never_publishes(completed,tmp_path):
    r,i=completed;r=dict(r);r['summary']=copy.deepcopy(r['summary']);r['summary']['n_paths']=1
    with pytest.raises(ValueError):save_run(r,i,tmp_path)
    assert not list(tmp_path.iterdir())


def test_two_saved_revisions_are_immutable(completed,tmp_path):
    p=save_run(*completed,tmp_path);before=digest(p/'manifest.json');q=save_run(*completed,tmp_path)
    assert p!=q and digest(p/'manifest.json')==before


def test_mapping_or_sampling_mismatch_rejected(completed,tmp_path):
    for field in ['canonical_symbols','sampling']:
        r,i=completed;r=dict(r)
        if field=='canonical_symbols':r[field]=list(reversed(r[field]))
        else:r[field]={**r[field],'seed':999}
        with pytest.raises(ValueError):save_run(r,i,tmp_path)
