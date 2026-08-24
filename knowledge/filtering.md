# Bandpass Filtering Knowledge

Placeholder for future agent guidance: when/why to filter, F1-F4 semantics, Nyquist constraints, QC criteria, and failure modes.

## V0.4 QC reflection

After an approved `sufilter` step, the application computes deterministic before/after QC metrics first. The configured agent provider then receives those metrics as evidence and returns an `accept` or `adjust` recommendation.

An `adjust` recommendation never executes processing automatically. It becomes another pending bandpass proposal and must pass the normal validator and explicit human approval gate.

The current QC metrics are intentionally simple:

- signal-band retention over the previous F2-F3 interval
- high-frequency energy reduction above the previous F4 corner
- RMS amplitude ratio
- residual frequency-distribution summary for the filtered dataset

These metrics are useful for an MVP reflection loop but are not sufficient to replace visual/geophysical QC for production processing.
