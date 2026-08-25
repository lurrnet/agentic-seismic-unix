from __future__ import annotations

import json
import os
import shutil
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SecurityLimitError(RuntimeError):
    pass


class RateLimitError(SecurityLimitError):
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
        'import_timeout_seconds': _env_int('SECURITY_IMPORT_TIMEOUT_SECONDS', 1800),
        'min_free_bytes': _env_int('SECURITY_MIN_FREE_BYTES', 5 * 1024**3),
        'agent_requests_per_minute': _env_int('SECURITY_AGENT_REQUESTS_PER_MINUTE', 20),
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


def ensure_path_within(path: Path, root: Path) -> Path:
    resolved = Path(path).resolve()
    root_resolved = Path(root).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SecurityLimitError(
            f'Path escapes project workspace: {resolved}'
        ) from exc
    return resolved


def enforce_upload_limit(upload_size: int) -> None:
    limit = get_security_limits()['max_upload_bytes']
    if int(upload_size) > limit:
        raise SecurityLimitError(
            f'Upload size {int(upload_size)} bytes exceeds configured limit {limit} bytes.'
        )


def enforce_storage_headroom(storage_path: Path, expected_write_bytes: int = 0) -> None:
    limits = get_security_limits()
    usage = shutil.disk_usage(Path(storage_path))
    required = max(0, int(expected_write_bytes)) + limits['min_free_bytes']
    if usage.free < required:
        raise SecurityLimitError(
            f'Insufficient free space under {storage_path}: {usage.free} bytes free; '
            f'at least {required} bytes required including safety reserve.'
        )


def enforce_processing_limits(project, state, expected_output_bytes: int = 0) -> None:
    limits = get_security_limits()
    if int(state.current_step) >= limits['max_processing_steps']:
        raise SecurityLimitError(
            f'Project has reached the maximum of {limits["max_processing_steps"]} processing steps.'
        )
    used = directory_size_bytes(Path(project.root))
    projected = used + max(0, int(expected_output_bytes))
    if projected > limits['max_project_bytes']:
        raise SecurityLimitError(
            f'Projected project storage {projected} bytes exceeds configured limit '
            f'{limits["max_project_bytes"]} bytes.'
        )
    enforce_storage_headroom(Path(project.root), expected_output_bytes)


_RATE_LOCK = threading.Lock()
_RATE_EVENTS: dict[str, deque[float]] = {}


def enforce_agent_rate_limit(key: str) -> None:
    limit = get_security_limits()['agent_requests_per_minute']
    now = time.monotonic()
    cutoff = now - 60.0
    with _RATE_LOCK:
        events = _RATE_EVENTS.setdefault(str(key), deque())
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= limit:
            raise RateLimitError(
                f'Agent request rate exceeded: maximum {limit} requests per minute.'
            )
        events.append(now)


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
        pass
