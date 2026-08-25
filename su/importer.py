from pathlib import Path
import subprocess
import time

from security.job_control import heavy_job
from security.policy import get_security_limits
from .executor import SUExecutionError, _decode


def _terminate(process):
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=2)
        except Exception:
            pass


def segy_to_su(segy_path: Path, su_path: Path):
    """Convert SEG-Y to SU with bounded runtime and project-local sidecars."""
    segy_path = Path(segy_path)
    su_path = Path(su_path)
    su_path.parent.mkdir(parents=True, exist_ok=True)
    hfile = su_path.parent / f'.{su_path.stem}_segy_header.txt'
    bfile = su_path.parent / f'.{su_path.stem}_segy_binary.bin'
    timeout = get_security_limits()['import_timeout_seconds']
    p1 = p2 = None
    started = time.monotonic()

    try:
        with heavy_job('SEG-Y import'):
            with open(su_path, 'wb') as fout:
                p1 = subprocess.Popen(
                    [
                        'segyread',
                        f'tape={segy_path}',
                        f'hfile={hfile}',
                        f'bfile={bfile}',
                        'verbose=0',
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                assert p1.stdout is not None and p1.stderr is not None
                p2 = subprocess.Popen(
                    ['segyclean'],
                    stdin=p1.stdout,
                    stdout=fout,
                    stderr=subprocess.PIPE,
                )
                p1.stdout.close()
                try:
                    _, err2 = p2.communicate(timeout=timeout)
                    elapsed = time.monotonic() - started
                    remaining = max(0.1, timeout - elapsed)
                    rc1 = p1.wait(timeout=remaining)
                    err1 = p1.stderr.read()
                except subprocess.TimeoutExpired as exc:
                    _terminate(p2)
                    _terminate(p1)
                    raise SUExecutionError(
                        f'SEG-Y import exceeded security timeout of {timeout} seconds.'
                    ) from exc

                if rc1 != 0:
                    raise SUExecutionError(
                        f'segyread failed ({rc1}):\n{_decode(err1)}'
                    )
                if p2.returncode != 0:
                    raise SUExecutionError(
                        f'segyclean failed ({p2.returncode}):\n{_decode(err2)}'
                    )

        if not su_path.exists() or su_path.stat().st_size == 0:
            raise SUExecutionError('SEG-Y conversion produced an empty SU file.')
    except Exception:
        _terminate(p2)
        _terminate(p1)
        try:
            if su_path.exists():
                su_path.unlink()
        except OSError:
            pass
        raise
    finally:
        for sidecar in (hfile, bfile):
            try:
                if sidecar.exists():
                    sidecar.unlink()
            except OSError:
                pass
