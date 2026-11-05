"""Optional headless interface to the same validated desktop workflows."""
import argparse,json
from pathlib import Path
from .core.inputs import read_json
from .core.export import save_run
from .services.experiments import default_config,execute,diagnose,compare

def main(argv=None):
    parser=argparse.ArgumentParser(description='RiskLab fixed-holdings Monte Carlo research')
    parser.add_argument('--scenario',required=True);parser.add_argument('--config');parser.add_argument('--out',required=True)
    parser.add_argument('--diagnose',action='store_true');parser.add_argument('--compare',action='store_true')
    args=parser.parse_args(argv)
    r,inputs=execute(read_json(args.scenario),read_json(args.config) if args.config else default_config())
    if args.diagnose:r,inputs=diagnose(r,inputs)
    if args.compare:r,inputs=compare(r,inputs)
    path=save_run(r,inputs,args.out)
    print(json.dumps({'run_folder':str(path),'summary':r['summary'],'diagnostics_status':r['diagnostics']['status']},indent=2))
