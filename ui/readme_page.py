import streamlit as st


README_TEXT = r'''
# Agentic SeismicUnix

Agentic SeismicUnix is an AI-assisted seismic-processing workstation built around **Seismic Unix (SU)**, **Streamlit**, and **Plotly**. The application combines conversational guidance with deterministic processing tools, validation, project history, and QC so that an agent can help analyze and process seismic data without receiving arbitrary shell access.

## Typical workflow

1. Upload a SEG-Y file. The application converts it to SU and creates a project workspace.
2. Ask the agent to inspect the dataset, frequency content, headers, or amplitudes.
3. Ask for a processing recommendation, or give a fully specified processing command directly.
4. Review processing results in Workspace, QC, and History.
5. Continue processing from the latest dataset. Every successful operation creates a new SU step and is recorded in project history.

## Current tools

### Inspection tools

These tools are read-only and may run automatically because they do not modify seismic data.

- **inspect_dataset** — sampling interval, samples per trace, estimated trace count, file size, endian information, and an SU header-range overview.
- **inspect_frequency** — bounded spectral analysis of preview traces and Nyquist information.
- **inspect_headers** — summaries of common SU trace headers such as `fldr`, `tracf`, `cdp`, `offset`, `sx`, and `gx`.
- **inspect_amplitude** — amplitude minimum/maximum, mean, RMS, percentiles, and zero-sample fraction.
- **compare_datasets** — deterministic before/after QC for the latest bandpass-filter step.

### Processing tools

Processing tools create a new SU dataset and are validated before execution.

- **Bandpass Filter (`sufilter`)** — four-corner zero-phase bandpass with `f1`, `f2`, `f3`, and `f4`.
- **Gain (`sugain`)** — deterministic gain using `tpow`, `gpow`, and `qclip`.
- **AGC (`sugain agc=1`)** — automatic gain control using a `wagc` window in seconds.
- **Trace Selection (`suwind`)** — select traces by a validated SU header key and min/max limits.

## Approval behavior

The application distinguishes between a recommendation and an explicit user command.

- `Recommend an AGC window.` → the agent chooses parameters and the operation remains approval-gated.
- `Apply AGC.` → the agent may recommend parameters; approval is still required because the user did not specify the exact window.
- `Apply AGC with a 0.5 s window.` → the application can validate and execute directly because the action and complete parameters were explicitly supplied by the user.
- After the agent creates a pending proposal, follow-up commands such as `apply it`, `go ahead`, or `apply such an AGC` authorize that exact validated proposal and execute it directly.

Read-only inspection never requires approval. Future higher-risk tools such as geometry or header rewriting can be configured to always require approval.

## Example requests

### Inspect the data

- `Inspect this dataset.`
- `What is the frequency content?`
- `Inspect CDP and offset ranges.`
- `Show me the amplitude statistics.`

### Bandpass filtering

- `Recommend a reasonable bandpass filter.`
- `Apply a bandpass of 8-15-50-60 Hz.`

### Gain and AGC

- `Recommend a conservative gain.`
- `Recommend an AGC window.`
- `Apply AGC with a 0.5 s window.`

### Trace selection

- `Inspect the offset range.`
- `Select traces with offset between -2000 and 2000.`

## Main tabs

- **Workspace** — current seismic section, spectrum, metadata, processing status, and SU header information.
- **Processing** — manual processing controls and related processing views.
- **QC** — before/after seismic, spectrum, quantitative QC metrics, and agent reflection for filters.
- **History** — provenance and processing-step history.
- **Agent Details** — configured provider/model, latest tool trace, latest reflection, and any pending processing action.
- **Readme** — this help page.

## Safety model

The agent does not receive unrestricted shell access. It works through structured application tools. Tool parameters are validated, processing writes a new output dataset instead of silently overwriting the current one, and project history records the processing lineage.
'''


def render_readme():
    st.markdown(README_TEXT)
