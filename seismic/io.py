from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import subprocess

import numpy as np

from su.executor import SUExecutionError, _decode


@dataclass(frozen=True)
class SUMetadata:
    ns: int
    dt_us: int
    dt_s: float
    nyquist_hz: float
    trace_bytes: int
    estimated_trace_count: int
    file_size_bytes: int
    endian: str

    def to_dict(self):
        return asdict(self)


# Common SU trace-header words. Offsets are zero-based byte positions in the
# 240-byte trace header. Types follow the conventional SEG-Y/SU header layout.
SU_HEADER_WORDS = {
    'tracl': (0, 4, True),
    'tracr': (4, 4, True),
    'fldr': (8, 4, True),
    'tracf': (12, 4, True),
    'ep': (16, 4, True),
    'cdp': (20, 4, True),
    'cdpt': (24, 4, True),
    'trid': (28, 2, True),
    'offset': (36, 4, True),
    'gelev': (40, 4, True),
    'selev': (44, 4, True),
    'sdepth': (48, 4, True),
    'scalel': (68, 2, True),
    'scalco': (70, 2, True),
    'sx': (72, 4, True),
    'sy': (76, 4, True),
    'gx': (80, 4, True),
    'gy': (84, 4, True),
    'ns': (114, 2, False),
    'dt': (116, 2, False),
}


def read_su_metadata(path: Path):
    size = path.stat().st_size
    if size < 240:
        raise ValueError('File too small for SU header.')
    h = path.open('rb').read(240)
    other = 'big' if sys.byteorder == 'little' else 'little'
    candidates = []
    with path.open('rb') as fin:
        for priority, endian in enumerate([sys.byteorder, other]):
            ns = int.from_bytes(h[114:116], endian)
            dt = int.from_bytes(h[116:118], endian)
            if not (1 <= ns <= 200000 and 1 <= dt <= 1000000):
                continue
            tb = 240 + ns * 4
            if tb > size:
                continue
            ntr, remainder = divmod(size, tb)
            if ntr < 1:
                continue
            consistency = 2
            if size >= tb + 240:
                fin.seek(tb)
                h2 = fin.read(240)
                if len(h2) == 240:
                    ns2 = int.from_bytes(h2[114:116], endian)
                    dt2 = int.from_bytes(h2[116:118], endian)
                    consistency = 0 if (ns2 == ns and dt2 == dt) else (
                        1 if 1 <= ns2 <= 200000 and 1 <= dt2 <= 1000000 else 2
                    )
            candidates.append(
                ((0 if remainder == 0 else 1, remainder, consistency, priority),
                 (ns, dt, tb, ntr, endian))
            )
    if not candidates:
        raise ValueError('Could not determine plausible ns/dt.')
    _, (ns, dt, tb, ntr, endian) = min(candidates, key=lambda item: item[0])
    dts = dt / 1_000_000.0
    return SUMetadata(ns, dt, dts, 1 / (2 * dts), tb, int(ntr), size, endian)


def get_surange(path):
    with open(path, 'rb') as fin:
        p = subprocess.run(
            ['surange'], stdin=fin, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    if p.returncode:
        raise SUExecutionError(_decode(p.stderr))
    return _decode(p.stdout)


def load_preview_traces(path, metadata, max_traces=200):
    max_traces = None if max_traces is None else max(1, int(max_traces))
    sample_bytes = metadata.ns * 4
    sample_dtype = np.dtype('<f4' if metadata.endian == 'little' else '>f4')
    traces = []
    with open(path, 'rb') as fin:
        while max_traces is None or len(traces) < max_traces:
            header = fin.read(240)
            if not header:
                break
            if len(header) < 240:
                break
            samples = fin.read(sample_bytes)
            if len(samples) < sample_bytes:
                break
            traces.append(np.frombuffer(samples, dtype=sample_dtype).astype(np.float32))
    if not traces:
        raise ValueError('No complete traces extracted from the SU dataset.')
    return np.stack(traces)


def summarize_su_headers(path, metadata, keys, max_traces=1000):
    """Return bounded numeric summaries for selected common SU header words."""
    normalized = []
    for key in keys:
        key = str(key).strip().lower()
        if key not in SU_HEADER_WORDS:
            allowed = ', '.join(sorted(SU_HEADER_WORDS))
            raise ValueError(f'Unsupported SU header key: {key}. Supported keys: {allowed}')
        if key not in normalized:
            normalized.append(key)
    if not normalized:
        raise ValueError('At least one header key is required.')

    max_traces = max(1, min(int(max_traces), 10000))
    values = {key: [] for key in normalized}
    trace_count = 0

    with open(path, 'rb') as fin:
        while trace_count < max_traces:
            header = fin.read(240)
            if not header or len(header) < 240:
                break
            fin.seek(metadata.ns * 4, 1)
            trace_count += 1

            for key in normalized:
                offset, width, signed = SU_HEADER_WORDS[key]
                values[key].append(
                    int.from_bytes(
                        header[offset:offset + width], metadata.endian, signed=signed
                    )
                )

    if trace_count == 0:
        raise ValueError('No complete trace headers found in the SU dataset.')

    summaries = {}
    for key, raw in values.items():
        arr = np.asarray(raw, dtype=np.int64)
        unique = np.unique(arr)
        summaries[key] = {
            'min': int(arr.min()),
            'max': int(arr.max()),
            'first': int(arr[0]),
            'last': int(arr[-1]),
            'unique_count': int(unique.size),
            'sample_values': [int(x) for x in unique[:12]],
            'sample_values_truncated': bool(unique.size > 12),
        }

    return {
        'traces_analyzed': trace_count,
        'available_trace_count': metadata.estimated_trace_count,
        'headers': summaries,
    }
