from dataclasses import dataclass,asdict
from pathlib import Path
import sys,subprocess,numpy as np
from su.executor import SUExecutionError,_decode
@dataclass(frozen=True)
class SUMetadata:
    ns:int; dt_us:int; dt_s:float; nyquist_hz:float; trace_bytes:int; estimated_trace_count:int; file_size_bytes:int
    def to_dict(self): return asdict(self)

def read_su_metadata(path:Path):
    size=path.stat().st_size
    if size<240: raise ValueError('File too small for SU header.')
    h=path.open('rb').read(240)
    for endian in [sys.byteorder,'big' if sys.byteorder=='little' else 'little']:
        ns=int.from_bytes(h[114:116],endian); dt=int.from_bytes(h[116:118],endian)
        if 1<=ns<=200000 and 1<=dt<=1000000: break
    else: raise ValueError('Could not determine plausible ns/dt.')
    dts=dt/1_000_000.0; tb=240+ns*4
    return SUMetadata(ns,dt,dts,1/(2*dts),tb,int(size//tb),size)

def get_surange(path):
    with open(path,'rb') as fin:
        p=subprocess.run(['surange'],stdin=fin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise SUExecutionError(_decode(p.stderr))
    return _decode(p.stdout)

def load_preview_traces(path,metadata,max_traces=200):
    fin=open(path,'rb')
    try:
        p1=subprocess.Popen(['suwind',f'count={int(max_traces)}'],stdin=fin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p1.stdout is not None and p1.stderr is not None
        p2=subprocess.Popen(['sustrip'],stdin=p1.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE); p1.stdout.close()
        out2,err2=p2.communicate(); err1=p1.stderr.read(); rc1=p1.wait()
    finally: fin.close()
    if rc1: raise SUExecutionError(f'suwind failed:\n{_decode(err1)}')
    if p2.returncode: raise SUExecutionError(f'sustrip failed:\n{_decode(err2)}')
    data=np.frombuffer(out2,dtype=np.float32); ntr=data.size//metadata.ns
    if not ntr: raise ValueError('No complete traces extracted.')
    return data[:ntr*metadata.ns].reshape(ntr,metadata.ns)
