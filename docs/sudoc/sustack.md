# SUSTACK — stack traces in adjacent ensembles

Source class: Seismic Unix selfdoc-derived application reference.

`SUSTACK` stacks traces that belong to the same adjacent ensemble/header value.

The application exposes stacking by a restricted gather key such as `cdp`, `fldr`, or `ep`, with normalization control.

Safety rule specific to this application: stacking is allowed only when the current dataset is the direct output of sorting by the same key. This prevents accidental stacking of non-contiguous ensembles.

Inspect gather structure and offset/fold evidence before recommending stack. Stacking is normally meaningful after appropriate prestack corrections; it should not be treated as a generic amplitude operation.
