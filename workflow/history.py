from pathlib import Path
from datetime import datetime,timezone
import json
class HistoryStore:
    def __init__(self,path): self.path=Path(path)
    def _load(self): return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
    def append(self,record):
        items=self._load(); items.append({**record,'created_at':datetime.now(timezone.utc).isoformat()}); self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps(items,indent=2),encoding='utf-8')
    def list(self): return self._load()
