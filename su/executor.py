from pathlib import Path
import subprocess,time
from .validator import validate_parameters
class SUExecutionError(RuntimeError): pass

def _decode(data): return (data or b'').decode('utf-8',errors='replace')

class SUExecutor:
    def __init__(self, registry): self.registry=registry
    def run_binary(self,args,stdin_path=None,stdout_path=None):
        fin=fout=None; started=time.perf_counter()
        try:
            if stdin_path is not None: fin=open(stdin_path,'rb')
            if stdout_path is not None: fout=open(stdout_path,'wb')
            p=subprocess.run(args,stdin=fin,stdout=fout if fout else subprocess.PIPE,stderr=subprocess.PIPE,check=False)
            if p.returncode != 0: raise SUExecutionError(f'Command failed ({p.returncode}): {" ".join(args)}\n{_decode(p.stderr)}')
            return {'status':'success','command':args,'duration_sec':time.perf_counter()-started,'stdout':_decode(p.stdout),'stderr':_decode(p.stderr)}
        finally:
            if fin: fin.close()
            if fout: fout.close()
    def execute_tool(self,tool_name,input_path,output_path,parameters,context=None):
        spec=self.registry.get(tool_name); params=validate_parameters(spec,parameters,context=context)
        ex=spec.get('execution',{}); executable=ex.get('executable')
        if not executable: raise SUExecutionError(f'Tool {tool_name} has no executable definition.')
        args=[executable]+[t.format(**params) for t in ex.get('argument_template',[])]
        output_path.parent.mkdir(parents=True,exist_ok=True)
        result=self.run_binary(args,stdin_path=input_path,stdout_path=output_path)
        if not output_path.exists() or output_path.stat().st_size==0: raise SUExecutionError(f'{tool_name} produced an empty output file.')
        result.update({'tool':tool_name,'input':str(input_path),'output':str(output_path),'parameters':params})
        return result
