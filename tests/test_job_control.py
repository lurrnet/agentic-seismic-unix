import pytest

from security.job_control import HeavyJobBusyError, heavy_job


def test_heavy_job_is_single_concurrency():
    with heavy_job('outer'):
        with pytest.raises(HeavyJobBusyError):
            with heavy_job('inner'):
                pass
