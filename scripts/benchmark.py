"""Documented process peak RSS and wall time for headless baseline or full workflow."""
import argparse,json,os,platform,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from risklab.core.simulation import simulate


def peak_memory():
    if os.name!='nt':
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value/(1024*1024 if sys.platform=='darwin' else 1024),'OS process peak RSS'
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    counter=Counters();counter.cb=ctypes.sizeof(counter)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(counter),counter.cb)
    return counter.PeakWorkingSetSize/(1024*1024),'Windows PeakWorkingSetSize'


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='docs/benchmark.json');args=p.parse_args()
    symbols=[f'SYN-{i:02}' for i in range(10)];cov=np.full((10,10),.00002);np.fill_diagonal(cov,.0001)
    start=time.perf_counter()
    result=simulate(symbols,[10]*10,[100]*10,10000,[0]*10,cov,n_paths=10000,n_steps=252,seed=42,batch_size=512,preview_count=20)
    seconds=time.perf_counter()-start;peak,method=peak_memory()
    cpu_model=platform.processor()
    if sys.platform.startswith('linux'):
        try:cpu_model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
        except (OSError,StopIteration):pass
    record={'cpu_model':cpu_model,'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),'processor':platform.processor(),
            'cpu_count':os.cpu_count(),'phase':'headless simulation including validation/factorization/summary; excludes Qt, input file parsing, diagnostics and publication',
            'paths':10000,'steps':252,'assets':10,'batch_size':512,'preview_count':20,'seed':42,
            'wall_seconds':seconds,'peak_rss_mib':peak,'memory_method':method,
            'thread_settings':{k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']},
            'numpy_build':str(np.__config__.CONFIG),
            'target_seconds':15,'target_peak_decimal_mb':300,'target_met_on_this_host':seconds<15 and peak*1048576<300000000}
    Path(args.output).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='numpy_build'},indent=2))

if __name__=='__main__':main()
