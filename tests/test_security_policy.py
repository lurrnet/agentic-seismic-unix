from pathlib import Path
from types import SimpleNamespace

import pytest

from project.project import Project
from security.policy import SecurityLimitError, ensure_path_within


def test_ensure_path_within_accepts_child(tmp_path):
    child = tmp_path / 'a' / 'b'
    child.parent.mkdir(parents=True)
    assert ensure_path_within(child, tmp_path) == child.resolve()


def test_ensure_path_within_rejects_escape(tmp_path):
    outside = tmp_path.parent / 'escape.su'
    with pytest.raises(SecurityLimitError):
        ensure_path_within(outside, tmp_path)


def test_project_rejects_invalid_id(tmp_path):
    with pytest.raises(ValueError):
        Project(tmp_path, '../escape')


def test_project_paths_stay_contained(tmp_path):
    project = Project(tmp_path)
    assert project.root.parent == tmp_path.resolve()
    with pytest.raises(SecurityLimitError):
        project.path(tmp_path.parent / 'outside.su')
