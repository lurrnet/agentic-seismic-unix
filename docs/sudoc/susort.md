# SUSORT — sort SU traces by header key

Source class: Seismic Unix selfdoc-derived application reference.

`SUSORT` orders traces according to one or more SU header keys. The application exposes a restricted one-key sort for whitelisted headers.

Guidance:

- inspect geometry/header evidence before choosing the key;
- choose `cdp`, `fldr`, `ep`, or another supported key according to the intended gather domain;
- sorting changes trace order, not trace sample values;
- stacking in this application requires the current dataset to be the direct output of sorting by the same stack key.

The application validates the key and constructs the command.
