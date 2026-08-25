# SUWIND — trace/data windowing

Source class: Seismic Unix selfdoc-derived application reference.

`SUWIND` selects traces and/or sample windows according to SU header and time criteria.

The application currently exposes a restricted trace-selection form using one validated header key with `min` and `max` bounds.

Guidance:

- inspect the target header range before selecting;
- require `min <= max`;
- avoid assuming coordinate units without considering relevant header scaling;
- do not add arbitrary `suwind` options outside the application schema.

The application performs validation and command construction.
