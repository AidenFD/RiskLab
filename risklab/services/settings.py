"""Writable locations and safe persisted settings; resources never store runs."""
import os
from pathlib import Path
from risklab.core.inputs import read_json

def app_directory():
    override=os.environ.get('RISKLAB_WORKSPACE')
    if override:return Path(override).expanduser().resolve()
    if os.name=='nt':return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'QuantLab'/'RiskLab'
    return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'QuantLab'/'RiskLab'

def load_settings():
    base=app_directory();base.mkdir(parents=True,exist_ok=True)
    try:d=read_json(base/'settings.json')
    except (ValueError,OSError):d={}
    if not isinstance(d,dict):d={}
    return {'run_directory':str(d.get('run_directory',base/'runs'))}

def save_settings(settings):
    from risklab.core.export import write_json
    write_json(app_directory()/'settings.json',settings)
