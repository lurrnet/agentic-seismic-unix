import streamlit as st


README_TEXT = r'''
# Agentic SeismicUnix

Agentic SeismicUnix is an AI-assisted seismic-processing workstation built around **Seismic Unix (SU)**, **Streamlit**, and **Plotly**. The application combines conversational guidance with deterministic processing tools, validation, project history, and QC so that an agent can help analyze and process seismic data without receiving arbitrary shell access.

## Typical workflow

1. Upload a SEG-Y file. The application converts it to SU and creates a project workspace.
2. Ask the agent to inspect the dataset, frequency content, amplitudes, headers, or acquisition geometry.
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
- **compare_datasets** — deterministic before/after QC for the latest bandpass-filter step.

## Processing tools

- **Bandpass Filter (`sufilter`)** — four-corner zero-phase bandpass using `f1/f2/f3/f4`.
- **Gain (`sugain`)** — deterministic gain using `tpow`, `gpow`, and `qclip`.
- **AGC (`sugain agc=1`)** — automatic gain control using `wagc` in seconds.
- **Trace Selection (`suwind`)** — select traces by header key and min/max limits.
- **Sort Dataset (`susort`)** — sort traces by one whitelisted SU header key.
- **Resample Dataset (`suresamp`)** — change the sample interval using `dt` in seconds. The application refreshes metadata after execution.
- **Set Header Constant (`sushw`)** — set one whitelisted header key to a constant integer for all traces. This is intentionally restricted and always approval-gated.

## Approval behavior

The application distinguishes between recommendations, explicit commands, and higher-risk metadata edits.

- `Recommend an AGC window.` → agent chooses parameters; proposal remains pending.
- `Apply AGC with a 0.5 s window.` → exact user command; may execute directly after validation.
- `Sort the dataset by cdp.` → exact user command; may execute directly after validation.
- `Resample to 2 ms.` → exact user command; may execute directly after validation.
- `Set cdp header to 100.` → header rewrite; **always requires UI approval** even though the value is explicit.
- After a normal pending proposal, `apply it`, `go ahead`, or similar wording authorizes that exact proposal only when its tool policy allows explicit execution.

## Geometry notes

SU coordinate headers such as `sx`, `sy`, `gx`, and `gy` are stored as raw integer header values. Their physical interpretation depends on `scalco`: positive values multiply coordinates, negative values divide by the absolute value, and zero is treated as a scale of 1. Geometry/header edits should therefore be inspected before modification.

## Example requests

### Inspection

- `Inspect this dataset.`
- `What is the frequency content?`
- `Inspect the acquisition geometry.`
- `Inspect CDP and offset ranges.`
- `Show me the amplitude statistics.`

### Processing

- `Recommend a reasonable bandpass filter.`
- `Apply a bandpass of 8-15-50-60 Hz.`
- `Recommend an AGC window.`
- `Apply AGC with a 0.5 s window.`
- `Select traces with offset between -2000 and 2000.`
- `Sort the dataset by cdp.`
- `Resample to 2 ms.`
- `Set cdp header to 100.`

## Main tabs

- **Workspace** — current seismic section, spectrum, metadata, processing status, and SU header information.
- **Processing** — manual processing controls and related processing views.
- **QC** — before/after seismic, spectrum, quantitative QC metrics, and agent reflection for filters.
- **History** — provenance and processing-step history.
- **Agent Details** — provider/model, latest tool trace, latest reflection, and pending action.
- **Readme** — this help page.

## Safety model

The agent never receives unrestricted shell access. It works through structured application capabilities backed by validated SU commands. Processing writes new output datasets rather than silently overwriting the current file. Header rewriting is intentionally narrower than raw `sushw`, and project history records the processing lineage.
'''


def render_readme():
    st.markdown(README_TEXT)
