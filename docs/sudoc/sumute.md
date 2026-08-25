# SUMUTE — polygonal mute

Source class: Seismic Unix selfdoc-derived application reference.

`SUMUTE` applies mute functions using a header-domain coordinate such as offset and a corresponding time curve.

Application-exposed parameters:

- `key`
- `xmute[]`
- `tmute[]` in seconds
- `mode`
- `ntaper`

The application requires equal-length `xmute`/`tmute` arrays, strictly increasing `xmute`, and mute times inside trace duration. `mode=0` is top/above mute; `mode=1` is bottom/below mute.

Inspect gather/header range and trace duration before recommending a mute. Mute design is interpretive and should not be inferred from metadata alone.
