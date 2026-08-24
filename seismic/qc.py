import numpy as np
from .spectrum import mean_amplitude_spectrum


def _energy(f, a, lo, hi=None):
    mask = (f >= lo) if hi is None else ((f >= lo) & (f <= hi))
    return float(np.trapz(a[mask], f[mask])) if np.any(mask) else 0.0


def compare_filter_result(before, after, dt_s, passband_low, passband_high, noise_low):
    # Quantitative QC must preserve relative spectral amplitudes. Do not
    # independently normalize before and after spectra here.
    f0, a0 = mean_amplitude_spectrum(before, dt_s, normalize=False)
    f1, a1 = mean_amplitude_spectrum(after, dt_s, normalize=False)

    pb0 = _energy(f0, a0, passband_low, passband_high)
    pb1 = _energy(f1, a1, passband_low, passband_high)
    nb0 = _energy(f0, a0, noise_low)
    nb1 = _energy(f1, a1, noise_low)

    r0 = float(np.sqrt(np.mean(before ** 2)))
    r1 = float(np.sqrt(np.mean(after ** 2)))

    return {
        'signal_retention': pb1 / pb0 if pb0 else 0.0,
        'high_frequency_reduction': 1 - nb1 / nb0 if nb0 else 0.0,
        'rms_before': r0,
        'rms_after': r1,
        'rms_ratio': r1 / r0 if r0 else 0.0,
        'clipping_detected': False,
        'metric_note': (
            'Spectral retention/reduction ratios use unnormalized mean amplitude spectra. '
            'Plotting spectra may still be normalized independently for visual comparison.'
        ),
    }
