from __future__ import annotations

from contextlib import contextmanager
import threading


class HeavyJobBusyError(RuntimeError):
    pass


_HEAVY_JOB_LOCK = threading.Lock()


@contextmanager
def heavy_job(kind: str):
    """Allow only one CPU/disk-heavy seismic job per application process.

    Imports and SU processing share this gate. Read-only inspection and agent
    reasoning do not use it.
    """
    if not _HEAVY_JOB_LOCK.acquire(blocking=False):
        raise HeavyJobBusyError(
            f'Another heavy seismic job is already running; {kind} was not started.'
        )
    try:
        yield
    finally:
        _HEAVY_JOB_LOCK.release()
