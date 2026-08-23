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
    max_traces=max(1,int(max_traces))
    sample_bytes=metadata.ns*4
    traces=[]
    with open(path,'rb') as fin:
        for _ in range(max_traces):
            header=fin.read(240)
            if not header: break
            if len(header)<240: break
            samples=fin.read(sample_bytes)
            if len(samples)<sample_bytes: break
            traces.append(np.frombuffer(samples,dtype=np.float32).copy())
    if not traces: raise ValueError('No complete traces extracted from the SU dataset.')
    return np.stack(traces)
