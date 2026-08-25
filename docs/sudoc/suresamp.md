# SURESAMP — resample SU traces

Source class: Seismic Unix selfdoc-derived application reference.

`SURESAMP` changes trace sampling. The application exposes a validated target sample interval `dt` in seconds.

Guidance:

- inspect the current sample interval and spectrum first;
- consider the target Nyquist frequency before downsampling;
- avoid choosing a coarser sample interval that would alias useful signal;
- verify output `dt`, `ns`, trace duration, and spectrum after resampling.

The application validates `dt` and controls execution.
