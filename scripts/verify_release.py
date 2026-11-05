"""Source or packaged cold-start/restart smoke, with actual Qt evidence."""
import argparse,json,os,subprocess,sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--executable');parser.add_argument('--output',default='docs/source_smoke');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    command=[str(Path(args.executable).resolve())] if args.executable else [sys.executable,'-m','risklab']
    env=dict(os.environ);env['RISKLAB_SMOKE_DIR']=str(out);env['RISKLAB_WORKSPACE']=str(out/'workspace')
    subprocess.run(command+['--smoke-test'],cwd=root,env=env,check=True,timeout=200)
    report=json.loads((out/'smoke_report.json').read_text());assert report['success']
    env['RISKLAB_OPEN_RUN']=report['run_folder'];env['RISKLAB_SMOKE_DIR']=str(out/'restart')
    subprocess.run(command+['--smoke-test'],cwd=root,env=env,check=True,timeout=60)
    reopened=json.loads((out/'restart/smoke_report.json').read_text());assert reopened['success']
    assert reopened['reopened_summary']==report['primary_summary']
    print(json.dumps({'cold_start':True,'restart_reopen':True,'evidence_directory':str(out)},indent=2))

if __name__=='__main__':main()
