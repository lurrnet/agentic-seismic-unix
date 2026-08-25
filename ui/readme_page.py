import streamlit as st


README_TEXT = r'''
# Agentic SeismicUnix

Agentic SeismicUnix is an AI-assisted seismic-processing workstation built around **Seismic Unix (SU)**, **Streamlit**, and **Plotly**. The application combines conversational guidance with deterministic processing tools, validation, project history, and QC so that an agent can help analyze and process seismic data without receiving arbitrary shell access.

## Typical workflow

1. Upload a SEG-Y file. The application converts it to SU and creates a project workspace.
2. Ask the agent to inspect the dataset, frequency content, amplitudes, headers, acquisition geometry, or prestack gather structure.
3. Ask for a processing recommendation, or give a fully specified processing command directly.
4. Review processing results in Workspace, QC, and History.
5. Continue from the latest dataset. Every successful operation creates a new SU step and refreshes metadata such as `ns`, `dt`, and Nyquist.

## Inspection tools

Read-only tools may run automatically.

- **inspect_dataset** — sampling interval, samples per trace, trace count, file size, endian information, and SU range information.
- **inspect_frequency** — bounded spectral analysis and Nyquist information.
- **inspect_headers** — summaries of selected SU trace headers.
- **inspect_geometry** — acquisition/geometry summary for `fldr`, `tracf`, `cdp`, `cdpt`, `offset`, `sx/sy`, `gx/gy`, and `scalco`.
- **inspect_amplitude** — amplitude min/max, mean, RMS, percentiles, and zero-sample fraction.
- **inspect_gathers** — bounded CDP or field-record gather structure and offset coverage for prestack decisions.
- **compare_datasets** — deterministic before/after QC for the latest bandpass-filter step.

## Processing tools

- **Bandpass Filter (`sufilter`)** — four-corner zero-phase bandpass using `f1/f2/f3/f4`.
- **Gain (`sugain`)** — deterministic gain using `tpow`, `gpow`, and `qclip`.
- **AGC (`sugain agc=1`)** — automatic gain control using `wagc` in seconds.
- **Trace Selection (`suwind`)** — select traces by header key and min/max limits.
- **Sort Dataset (`susort`)** — sort traces by one whitelisted SU header key.
- **Resample Dataset (`suresamp`)** — change the sample interval using `dt` in seconds.
- **Mute (`sumute`)** — bounded polygonal top or bottom mute. `mode=0` mutes above the curve and `mode=1` mutes below. `xmute` and `tmute` must contain the same number of points; `xmute` must increase strictly and `tmute` values must remain inside the trace time range.
- **Predictive Deconvolution (`supef`)** — Wiener predictive error filtering using `minlag`, `maxlag`, and `pnoise`. Lag values are in seconds and must remain inside the trace time range.
- **NMO (`sunmo`)** — normal moveout using a validated time-only RMS velocity function `tnmo/vnmo`, plus `smute`, `lmute`, and `sscale`. The application rejects NMO when inspected `offset` headers are all zero.
- **Stack (`sustack`)** — stack adjacent traces sharing `cdp`, `fldr`, or `ep`. For safety, the current dataset must be the direct output of `susort` using the same key immediately before stacking.
- **Set Header Constant (`sushw`)** — set one whitelisted header key to a constant integer for all traces. This operation always requires approval.

## Approval behavior

The application distinguishes between recommendations, explicit commands, and higher-risk metadata edits.

- `Recommend an AGC window.` → agent chooses parameters; proposal remains pending.
- `Apply AGC with a 0.5 s window.` → exact user command; may execute directly after validation.
- `Apply predictive decon minlag=0.12 maxlag=0.20 pnoise=0.001.` → exact user command; may execute directly after validation.
- `Apply NMO tnmo=0,1,2 vnmo=1500,2000,2600 smute=1.5 lmute=25 sscale=1.` → exact user command; may execute directly after validation and offset checks.
- `Sort the dataset by cdp.` → exact user command; may execute directly after validation.
- `Resample to 2 ms.` → exact user command; may execute directly after validation.
- `Set cdp header to 100.` → header rewrite; **always requires UI approval**.
- After a normal pending proposal, `apply it`, `go ahead`, or similar wording authorizes that exact proposal only when its tool policy allows explicit execution.

## Predictive-decon workflow

`supef` is exposed through bounded lag parameters rather than arbitrary command text. Both `minlag` and `maxlag` are interpreted in seconds, must lie inside the current trace time range, and must satisfy `minlag <= maxlag`. `pnoise` is restricted to the range 0–1.

Example:

`Apply predictive decon minlag=0.12 maxlag=0.20 pnoise=0.001.`

The agent should not infer a multiple period from spectrum evidence alone. Lag selection remains a geophysical interpretation and should be explained conservatively.

## NMO workflow

V0.9.0 exposes a deliberately constrained `sunmo` wrapper using one velocity function of time only. `tnmo` values are seconds and must be strictly increasing; `vnmo` values are positive RMS velocities and must contain the same number of entries.

Example:

`Apply NMO tnmo=0,1,2 vnmo=1500,2000,2600 smute=1.5 lmute=25 sscale=1.`

Before proposing or applying NMO, the application can inspect CDP gather structure and offset coverage. If the inspected `offset` header is zero for all traces, NMO is rejected. Lateral CDP-dependent velocity functions are intentionally not exposed in this release.

Velocity semblance analysis and velocity picking are also intentionally not treated as ordinary processing-lineage steps in V0.9.0; they produce analysis products rather than a replacement seismic dataset and are better handled by a dedicated analysis/QC workflow.

## Mute workflow

Mute is intentionally exposed as a high-level structured capability rather than raw `sumute` arguments. A typical explicit command is:

`Apply top mute key=offset xmute=0,1000,2000 tmute=0.10,0.20,0.35 ntaper=20.`

The application validates the header key, curve lengths, ordering, trace-time bounds, mode, and taper before execution.

## Stack workflow

`stack_traces` does not silently regroup arbitrary traces. `sustack` stacks adjacent traces with the same key, so this application requires an immediately preceding sort using that key.

Example:

1. `Sort the dataset by cdp.`
2. `Stack by cdp.`

If another processing step occurs between the sort and stack, the stack guard requires sorting again.

## Geometry notes

SU coordinate headers such as `sx`, `sy`, `gx`, and `gy` are stored as raw integer header values. Their physical interpretation depends on `scalco`: positive values multiply coordinates, negative values divide by the absolute value, and zero is treated as a scale of 1.

## Example requests

- `Inspect the acquisition geometry.`
- `Inspect the CDP gathers and offset coverage.`
- `Recommend a reasonable bandpass filter.`
- `Apply a bandpass of 8-15-50-60 Hz.`
- `Recommend an AGC window.`
- `Apply AGC with a 0.5 s window.`
- `Apply predictive decon minlag=0.12 maxlag=0.20 pnoise=0.001.`
- `Apply NMO tnmo=0,1,2 vnmo=1500,2000,2600 smute=1.5 lmute=25 sscale=1.`
- `Select traces with offset between -2000 and 2000.`
- `Sort the dataset by cdp.`
- `Resample to 2 ms.`
- `Recommend a top mute using offset.`
- `Apply top mute key=offset xmute=0,1000 tmute=0.1,0.25 ntaper=20.`
- `Stack by cdp.`
- `Set cdp header to 100.`

## Main tabs

- **Workspace** — selected seismic section, spectrum, metadata, processing status, and SU header information.
- **Processing** — manual processing controls and related processing views.
- **QC** — before/after seismic and spectrum for the selected processing step, with operation-specific metrics where available.
- **History** — provenance and processing-step history.
- **Agent Details** — provider/model, latest tool trace, actual executed SU command lines, latest reflection, and pending action.
- **Readme** — this help page.

## Safety model

The agent never receives unrestricted shell access. It works through structured application capabilities backed by validated SU commands. Processing writes new output datasets rather than silently overwriting the current file. Header rewriting is intentionally narrower than raw `sushw`, mute curves are bounded and validated, NMO checks for populated offsets, deconvolution lags are trace-bounded, stacking requires deterministic sort provenance, and project history records both processing lineage and the actual SU command line executed.
'''


def render_readme():
    st.markdown(README_TEXT)
