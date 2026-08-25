# SUGAIN — trace gain and scaling

Source class: Seismic Unix selfdoc-derived application reference.

`SUGAIN` applies trace-amplitude scaling and related gain operations.

Application-exposed parameters:

- `tpow`: time-dependent power gain
- `gpow`: power applied to sample amplitudes
- `qclip`: clipping quantile control

Use gain conservatively and inspect amplitude statistics before recommending parameters. Gain changes display/dynamic range and can distort amplitudes if overused.

The application constrains `tpow`, `gpow`, and `qclip` and constructs the executable argument list itself. Do not add arbitrary `sugain` options outside the application schema.
