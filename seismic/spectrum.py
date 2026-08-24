import numpy as np


def mean_amplitude_spectrum(traces,dt_s):
    x=traces-np.mean(traces,axis=1,keepdims=True)
    amp=np.mean(np.abs(np.fft.rfft(x,axis=1)),axis=0)
    freq=np.fft.rfftfreq(traces.shape[1],d=dt_s)
    peak=float(np.max(amp)) if amp.size else 0.0
    if peak>0: amp=amp/peak
    return freq,amp


def summarize_frequency_content(traces, dt_s):
    freq, amp = mean_amplitude_spectrum(traces, dt_s)
    if amp.size == 0 or not np.any(np.isfinite(amp)):
        raise ValueError('Spectrum is empty or invalid.')

    safe = np.nan_to_num(amp, nan=0.0, posinf=0.0, neginf=0.0)
    peak_idx = int(np.argmax(safe))
    power = safe ** 2
    total = float(np.sum(power))

    if total > 0:
        cdf = np.cumsum(power) / total
        def percentile_freq(q):
            idx = int(np.searchsorted(cdf, q, side='left'))
            idx = min(max(idx, 0), len(freq)-1)
            return float(freq[idx])
        f05 = percentile_freq(0.05)
        f10 = percentile_freq(0.10)
        f50 = percentile_freq(0.50)
        f90 = percentile_freq(0.90)
        f95 = percentile_freq(0.95)
    else:
        f05=f10=f50=f90=f95=0.0

    return {
        'peak_frequency_hz': float(freq[peak_idx]),
        'energy_percentile_hz': {
            'p05': f05,
            'p10': f10,
            'p50': f50,
            'p90': f90,
            'p95': f95,
        },
        'interpretation_note': (
            'Percentiles are computed from the mean preview-spectrum power and are descriptive, '
            'not an automatic definition of signal versus noise.'
        ),
    }
