# SUFILTER — zero-phase frequency filtering

Source class: Seismic Unix selfdoc-derived application reference.

`SUFILTER` applies zero-phase sine-squared tapered frequency filtering to SU traces.

For the application's four-corner bandpass workflow, use four ordered frequencies in Hz:

- `f1`: lower stop corner
- `f2`: lower pass corner
- `f3`: upper pass corner
- `f4`: upper stop corner

The application requires `0 <= f1 < f2 < f3 < f4 < Nyquist` and validates the current dataset sampling before execution.

Operational guidance:

- inspect frequency content before recommending corners;
- preserve useful signal rather than choosing corners from convention alone;
- treat the spectrum as evidence, not as automatic proof of signal/noise separation;
- after filtering, compare before/after seismic and spectral QC.

Execution and approval remain application-controlled.
