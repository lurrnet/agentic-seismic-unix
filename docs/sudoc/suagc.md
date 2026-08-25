# AGC via SUGAIN

Source class: Seismic Unix selfdoc-derived application reference.

The application implements AGC with `sugain agc=1 wagc=<seconds>`.

Application parameter:

- `wagc`: AGC window length in seconds

Use amplitude inspection before recommending AGC when practical. Short windows can over-equalize local amplitudes and emphasize noise; long windows preserve broader amplitude trends but provide less local balancing.

The application validates `wagc` and remains responsible for execution and approval.
