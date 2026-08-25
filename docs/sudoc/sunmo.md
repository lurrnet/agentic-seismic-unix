# SUNMO — normal moveout correction

Source class: Seismic Unix selfdoc-derived application reference.

`SUNMO` applies normal moveout correction using offset headers and a velocity function.

Application-exposed parameters:

- `tnmo[]`: time picks in seconds
- `vnmo[]`: positive RMS velocities
- `smute`: stretch-mute factor
- `lmute`: mute-ramp length
- `sscale`: stretch scaling control

The application requires populated offset headers, equal-length `tnmo`/`vnmo`, strictly increasing `tnmo`, positive velocities, and times within trace duration.

The current application supports one time-only velocity function. It does not yet expose lateral CDP-dependent velocity functions or semblance picking.

Guidance:

- inspect CDP gather and offset coverage before NMO;
- do not invent velocities from metadata;
- velocity choice is interpretive and should come from supplied velocity evidence or explicit user input;
- inspect stretch/mute effects and gather flattening after NMO.

Execution and approval remain application-controlled.
