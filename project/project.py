from pathlib import Path
import re
import uuid

from security.policy import ensure_path_within
from .state import ProjectState


_PROJECT_ID_RE = re.compile(r'^[a-f0-9]{32}$')


class Project:
    def __init__(self, root, project_id=None):
        self.base_root = Path(root).resolve()
        if project_id is None:
            project_id = uuid.uuid4().hex
        project_id = str(project_id)
        if not _PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError('Invalid project id.')
        self.project_id = project_id
        self.root = ensure_path_within(self.base_root / project_id, self.base_root)
        self.raw_dir = self.root / 'raw'
        self.data_dir = self.root / 'data'
        self.qc_dir = self.root / 'qc'
        self.history_dir = self.root / 'history'
        self.state_path = self.root / 'project.json'
        for directory in [self.raw_dir, self.data_dir, self.qc_dir, self.history_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def path(self, value):
        return ensure_path_within(Path(value), self.root)

    def initialize(self, input_file, current_dataset, metadata):
        input_file = str(self.path(input_file))
        current_dataset = str(self.path(current_dataset))
        state = ProjectState(
            self.project_id, input_file, current_dataset, 0, metadata
        )
        state.save(self.state_path)
        return state

    def load_state(self):
        state = ProjectState.load(self.state_path)
        self.path(state.input_file)
        self.path(state.current_dataset)
        return state

    def save_state(self, state):
        self.path(state.input_file)
        self.path(state.current_dataset)
        state.save(self.state_path)

    def next_output_path(self, operation):
        safe_operation = re.sub(r'[^a-zA-Z0-9_-]+', '_', str(operation)).strip('_')
        if not safe_operation:
            raise ValueError('Invalid processing operation name.')
        path = self.data_dir / f'step{self.load_state().current_step + 1:03d}_{safe_operation}.su'
        return self.path(path)
