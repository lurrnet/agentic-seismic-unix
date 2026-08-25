# SUPEF — predictive error filtering / predictive deconvolution

Source class: Seismic Unix selfdoc-derived application reference.

`SUPEF` performs Wiener predictive error filtering. In the application it is exposed as predictive deconvolution using:

- `minlag` in seconds
- `maxlag` in seconds
- `pnoise` relative additive noise/stabilization

The application requires lag values inside trace duration with `minlag <= maxlag` and validates `pnoise`.

Guidance:

- use sampling and frequency evidence before proposing lag values;
- lag selection is a geophysical interpretation and cannot be determined from spectrum alone;
- consider the expected periodicity of multiples/reverberations and desired prediction distance;
- compare spectrum, autocorrelation behavior, RMS, and noise amplification after processing when QC is available.

Execution remains application-controlled.
