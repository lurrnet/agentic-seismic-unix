#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil


DEFAULT_ROOT = Path('/data/projects')


def project_age(path: Path) -> timedelta:
    latest = path.stat().st_mtime
    for item in path.rglob('*'):
        try:
            latest = max(latest, item.stat().st_mtime)
        except OSError:
            pass
    modified = datetime.fromtimestamp(latest, tz=timezone.utc)
    return datetime.now(timezone.utc) - modified


def main():
    parser = argparse.ArgumentParser(description='Review or remove stale seismic projects.')
    parser.add_argument('--root', default=str(DEFAULT_ROOT))
    parser.add_argument('--older-than-days', type=int, default=30)
    parser.add_argument('--delete', action='store_true', help='Actually remove matching projects. Default is dry-run.')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    threshold = timedelta(days=max(1, args.older_than_days))
    if not root.exists():
        print(f'Project root does not exist: {root}')
        return

    matches = []
    for project in sorted(root.iterdir()):
        if not project.is_dir():
            continue
        age = project_age(project)
        if age >= threshold:
            matches.append((project, age))

    mode = 'DELETE' if args.delete else 'DRY-RUN'
    print(f'{mode}: {len(matches)} project(s) older than {threshold.days} days')
    for project, age in matches:
        print(f'{project}  age_days={age.days}')
        if args.delete:
            shutil.rmtree(project)


if __name__ == '__main__':
    main()
