class WorkflowEngine:
    def __init__(self,executor,history): self.executor=executor; self.history=history
    def run_processing_step(self,state,tool_name,input_path,output_path,parameters,reason):
        r=self.executor.execute_tool(tool_name,input_path,output_path,parameters,state.metadata)
        rec={'step_id':state.current_step+1,'parent_step':state.current_step,'tool':tool_name,'input':str(input_path),'output':str(output_path),'parameters':r['parameters'],'reason':reason,'status':r['status'],'duration_sec':r['duration_sec']}
        self.history.append(rec); return rec
