# SUSHW — set SU trace-header values

Source class: Seismic Unix selfdoc-derived application reference.

`SUSHW` changes SU trace-header values. Header edits can alter geometry and processing semantics, so the application exposes only a restricted constant-value form for whitelisted headers.

Guidance:

- inspect the relevant header/geometry first;
- interpret coordinate headers together with `scalco`;
- never infer missing geometry from convenience alone;
- treat header rewriting as high risk.

The application requires UI approval for header edits even when the requested value is explicit.
