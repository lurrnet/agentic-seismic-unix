from dataclasses import dataclass,asdict
from pathlib import Path
import sys,subprocess,numpy as np
from su.executor import SUExecutionError,_decode
@dataclass(frozen=True)
class SUMetadata:
    ns:int; dt_us:int; dt_s:float; nyquist_hz:float; trace_bytes:int; estimated_trace_count:int; file_size_bytes:int; endian:str
    def to_dict(self): return asdict(self)

def read_su_metadata(path:Path):
    size=path.stat().st_size
    if size<240: raise ValueError('File too small for SU header.')
    h=path.open('rb').read(240)
    other='big' if sys.byteorder=='little' else 'little'
    candidates=[]
    with path.open('rb') as fin:
        for priority,endian in enumerate([sys.byteorder,other]):
            ns=int.from_bytes(h[114:116],endian); dt=int.from_bytes(h[116:118],endian)
            if not (1<=ns<=200000 and 1<=dt<=1000000): continue
            tb=240+ns*4
            if tb>size: continue
            ntr,remainder=divmod(size,tb)
            if ntr<1: continue
            consistency=2
            if size>=tb+240:
                fin.seek(tb)
                h2=fin.read(240)
                if len(h2)==240:
                    ns2=int.from_bytes(h2[114:116],endian); dt2=int.from_bytes(h2[116:118],endian)
                    consistency=0 if (ns2==ns and dt2==dt) else (1 if 1<=ns2<=200000 and 1<=dt2<=1000000 else 2)
            candidates.append(((0 if remainder==0 else 1,remainder,consistency,priority),(ns,dt,tb,ntr,endian)))
    if not candidates: raise ValueError('Could not determine plausible ns/dt.')
    _,(ns,dt,tb,ntr,endian)=min(candidates,key=lambda item:item[0])
    dts=dt/1_000_000.0
    return SUMetadata(ns,dt,dts,1/(2*dts),tb,int(ntr),size,endian)

def get_surange(path):
    with open(path,'rb') as fin:
        p=subprocess.run(['surange'],stdin=fin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise SUExecutionError(_decode(p.stderr))
    return _decode(p.stdout)

def load_preview_traces(path,metadata,max_traces=200):
    max_traces=None if max_traces is None else max(1,int(max_traces))
    sample_bytes=metadata.ns*4
    sample_dtype=np.dtype('<f4' if metadata.endian=='little' else '>f4')
    traces=[]
    with open(path,'rb') as fin:
        while max_traces is None or len(traces)<max_traces:
            header=fin.read(240)
            if not header: break
            if len(header)<240: break
            samples=fin.read(sample_bytes)
            if len(samples)<sample_bytes: break
            traces.append(np.frombuffer(samples,dtype=sample_dtype).astype(np.float32))
    if not traces: raise ValueError('No complete traces extracted from the SU dataset.')
    return np.stack(traces)
