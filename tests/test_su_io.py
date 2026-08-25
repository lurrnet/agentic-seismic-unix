import sys
from pathlib import Path

import numpy as np

from seismic.io import load_preview_traces, read_su_metadata


def _write_tiny_su(path: Path, traces=2, ns=4, dt_us=2000):
    endian = sys.byteorder
    sample_dtype = np.dtype('<f4' if endian == 'little' else '>f4')
    with path.open('wb') as fout:
        for trace_index in range(traces):
            header = bytearray(240)
            header[0:4] = int(trace_index + 1).to_bytes(4, endian, signed=True)
            header[114:116] = int(ns).to_bytes(2, endian, signed=False)
            header[116:118] = int(dt_us).to_bytes(2, endian, signed=False)
            fout.write(header)
            samples = np.arange(ns, dtype=np.float32) + trace_index
            fout.write(samples.astype(sample_dtype).tobytes())


def test_read_tiny_su_metadata_and_preview(tmp_path):
    path = tmp_path / 'tiny.su'
    _write_tiny_su(path)
    metadata = read_su_metadata(path)
    assert metadata.ns == 4
    assert metadata.dt_us == 2000
    assert metadata.estimated_trace_count == 2
    preview = load_preview_traces(path, metadata, max_traces=2)
    assert preview.shape == (2, 4)
    assert preview[1, 0] == 1.0
