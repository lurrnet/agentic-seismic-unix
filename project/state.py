from dataclasses import dataclass,asdict
from pathlib import Path
import json
@dataclass
class ProjectState:
    project_id:str; input_file:str; current_dataset:str; current_step:int; metadata:dict
    def to_dict(self): return asdict(self)
    def save(self,path:Path): path.write_text(json.dumps(self.to_dict(),indent=2),encoding='utf-8')
    @classmethod
    def load(cls,path:Path): return cls(**json.loads(path.read_text(encoding='utf-8')))
