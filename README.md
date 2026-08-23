# Seismic Agent V0.2

V0.2 keeps the same visible MVP (SEG-Y → SU → sufilter → QC) but adds Tool Registry, Validator, Workflow Engine, Project State, and History/Provenance.

## Build

1. Put official `cwp_su_all_*.tgz` under `source/`.
2. Run `docker compose build`.
3. Run `docker compose up -d`.
4. Open port 8501 or route it through your existing tunnel.

## Architecture

`Streamlit → Workflow Engine → Tool Registry → Validator → SU Executor → Seismic Unix → QC`

Each project stores `project.json`, step-numbered SU files, and `history/workflow.json`.

## Next step

V0.3 can add a single SeismicAgent with structured tools: `inspect_dataset`, `inspect_frequency`, `apply_bandpass_filter`, and `compare_datasets`.
