from pathlib import Path
import yaml
class ToolRegistry:
    def __init__(self, tools_dir: Path):
        self.tools_dir=Path(tools_dir); self._tools={}; self.reload()
    def reload(self):
        self._tools.clear()
        for p in sorted(self.tools_dir.glob('*.yaml')):
            spec=yaml.safe_load(p.read_text(encoding='utf-8'))
            if not spec.get('name'): raise ValueError(f'Missing tool name in {p}')
            self._tools[spec['name']]=spec
    def get(self,name):
        if name not in self._tools: raise KeyError(f'Unknown tool: {name}')
        return self._tools[name]
    def list_tools(self): return list(self._tools.values())
