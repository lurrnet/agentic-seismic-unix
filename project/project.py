from pathlib import Path
import uuid
from .state import ProjectState
class Project:
    def __init__(self,root,project_id=None):
        self.project_id=project_id or uuid.uuid4().hex; self.root=Path(root)/self.project_id
        self.raw_dir=self.root/'raw'; self.data_dir=self.root/'data'; self.qc_dir=self.root/'qc'; self.history_dir=self.root/'history'; self.state_path=self.root/'project.json'
        for d in [self.raw_dir,self.data_dir,self.qc_dir,self.history_dir]: d.mkdir(parents=True,exist_ok=True)
    def initialize(self,input_file,current_dataset,metadata):
        s=ProjectState(self.project_id,input_file,current_dataset,0,metadata); s.save(self.state_path); return s
    def load_state(self): return ProjectState.load(self.state_path)
    def save_state(self,state): state.save(self.state_path)
    def next_output_path(self,operation): return self.data_dir/f'step{self.load_state().current_step+1:03d}_{operation}.su'
