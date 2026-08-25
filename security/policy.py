from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SecurityLimitError(RuntimeError):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SecurityLimitError(f'{name} must be an integer.') from exc
    if value <= 0:
        raise SecurityLimitError(f'{name} must be > 0.')
    return value


def get_security_limits() -> dict[str, int]:
    return {
        'max_upload_bytes': _env_int('SECURITY_MAX_UPLOAD_BYTES', 2 * 1024**3),
        'max_project_bytes': _env_int('SECURITY_MAX_PROJECT_BYTES', 20 * 1024**3),
        'max_processing_steps': _env_int('SECURITY_MAX_PROCESSING_STEPS', 100),
        'su_timeout_seconds': _env_int('SECURITY_SU_TIMEOUT_SECONDS', 1800),
    }


def directory_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for entry in path.rglob('*'):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def enforce_upload_limit(upload_size: int) -> None:
    limit = get_security_limits()['max_upload_bytes']
    if int(upload_size) > limit:
        raise SecurityLimitError(
            f'Upload size {int(upload_size)} bytes exceeds configured limit {limit} bytes.'
        )


def enforce_processing_limits(project, state) -> None:
    limits = get_security_limits()
    if int(state.current_step) >= limits['max_processing_steps']:
        raise SecurityLimitError(
            f'Project has reached the maximum of {limits["max_processing_steps"]} processing steps.'
        )
    used = directory_size_bytes(Path(project.root))
    if used >= limits['max_project_bytes']:
        raise SecurityLimitError(
            f'Project storage {used} bytes has reached configured limit '
            f'{limits["max_project_bytes"]} bytes.'
        )


def audit_event(project, event: str, *, severity: str = 'info', details: dict[str, Any] | None = None) -> None:
    try:
        audit_dir = Path(project.history_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)
        path = audit_dir / 'security_audit.jsonl'
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event': str(event),
            'severity': str(severity),
            'project_id': getattr(project, 'project_id', None),
            'details': details or {},
        }
        with path.open('a', encoding='utf-8') as fout:
            fout.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
    except Exception:
        # Security telemetry must never crash deterministic processing paths.
        pass
