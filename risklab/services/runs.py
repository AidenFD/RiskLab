"""Run history inventory, including concise corrupt-entry diagnostics."""
from pathlib import Path
from risklab.core.inputs import read_json
from risklab.core.export import load_run


def list_runs(root):
    root=Path(root);records=[]
    if not root.exists():return records
    for path in sorted(root.iterdir(),reverse=True):
        if not path.is_dir() or path.name.startswith('.'):continue
        try:
            manifest=read_json(path/'manifest.json')
            if not (path/'COMPLETED').is_file():continue
            records.append({'path':str(path),'manifest':manifest,'error':None})
        except (OSError,ValueError,KeyError) as exc:
            records.append({'path':str(path),'manifest':{'run_id':path.name,'status':'UNREADABLE'},'error':str(exc)})
    return sorted(records,key=lambda x:x['manifest'].get('created_utc',''),reverse=True)
