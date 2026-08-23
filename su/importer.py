from pathlib import Path
import subprocess
from .executor import SUExecutionError,_decode

def segy_to_su(segy_path:Path,su_path:Path):
    su_path.parent.mkdir(parents=True,exist_ok=True)
    with open(su_path,'wb') as fout:
        p1=subprocess.Popen(['segyread',f'tape={segy_path}','verbose=0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p1.stdout is not None and p1.stderr is not None
        p2=subprocess.Popen(['segyclean'],stdin=p1.stdout,stdout=fout,stderr=subprocess.PIPE)
        p1.stdout.close(); _,err2=p2.communicate(); err1=p1.stderr.read(); rc1=p1.wait()
        if rc1 != 0: raise SUExecutionError(f'segyread failed ({rc1}):\n{_decode(err1)}')
        if p2.returncode != 0: raise SUExecutionError(f'segyclean failed ({p2.returncode}):\n{_decode(err2)}')
    if not su_path.exists() or su_path.stat().st_size==0: raise SUExecutionError('SEG-Y conversion produced an empty SU file.')
