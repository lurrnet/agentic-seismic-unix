from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import numpy as np

from seismic.io import read_su_metadata, get_surange, load_preview_traces
from seismic.spectrum import summarize_frequency_content
from seismic.qc import compare_filter_result
from su.validator import validate_parameters


TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "inspect_dataset",
        "description": "Inspect the currently loaded SU dataset and return basic sampling/file metadata plus a bounded surange summary.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_frequency",
        "description": "Inspect mean amplitude-spectrum characteristics of the current SU dataset using preview traces.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_traces": {
                    "type": "integer",
                    "description": "Maximum traces to inspect. Use 200 unless there is a specific reason to use fewer or more.",
                    "minimum": 1,
                    "maximum": 1000,
                }
            },
            "required": ["max_traces"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "apply_bandpass_filter",
        "description": "Propose a four-corner sufilter bandpass. This does NOT execute processing; it creates a pending action that requires explicit user approval in the UI.",
        "parameters": {
            "type": "object",
            "properties": {
                "f1": {"type": "number", "description": "Low stop frequency in Hz."},
                "f2": {"type": "number", "description": "Low passband frequency in Hz."},
                "f3": {"type": "number", "description": "High passband frequency in Hz."},
                "f4": {"type": "number", "description": "High stop frequency in Hz."},
                "reason": {"type": "string", "description": "Short evidence-based reason for this recommendation."},
            },
            "required": ["f1", "f2", "f3", "f4", "reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_datasets",
        "description": "Compare the most recent sufilter input and output using machine-readable QC metrics.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


class AgentToolkit:
    def __init__(self, project, state, history, registry, preview_traces: int = 200):
        self.project = project
        self.state = state
        self.history = history
        self.registry = registry
        self.preview_traces = preview_traces
        self.pending_action: dict[str, Any] | None = None

    @property
    def current_path(self) -> Path:
        return Path(self.state.current_dataset)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "inspect_dataset":
            return self.inspect_dataset()
        if name == "inspect_frequency":
            return self.inspect_frequency(arguments)
        if name == "apply_bandpass_filter":
            return self.propose_bandpass(arguments)
        if name == "compare_datasets":
            return self.compare_datasets()
        raise KeyError(f"Unknown agent tool: {name}")

    def inspect_dataset(self) -> dict[str, Any]:
        m = read_su_metadata(self.current_path)
        raw = get_surange(self.current_path)
        # Keep model context bounded. The complete output remains visible in the Process tab.
        lines = raw.splitlines()
        return {
            "dataset": str(self.current_path),
            "samples_per_trace": m.ns,
            "sample_interval_us": m.dt_us,
            "sample_interval_s": m.dt_s,
            "nyquist_hz": m.nyquist_hz,
            "estimated_trace_count": m.estimated_trace_count,
            "file_size_bytes": m.file_size_bytes,
            "endian": m.endian,
            "surange_excerpt": "\n".join(lines[:80]),
            "surange_truncated": len(lines) > 80,
        }

    def inspect_frequency(self, arguments: dict[str, Any]) -> dict[str, Any]:
        requested = int(arguments.get("max_traces", self.preview_traces))
        requested = max(1, min(requested, 1000))
        m = read_su_metadata(self.current_path)
        traces = load_preview_traces(self.current_path, m, requested)
        summary = summarize_frequency_content(traces, m.dt_s)
        return {
            "dataset": str(self.current_path),
            "traces_analyzed": int(traces.shape[0]),
            "nyquist_hz": m.nyquist_hz,
            **summary,
        }

    def propose_bandpass(self, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = self.registry.get("sufilter")
        params = validate_parameters(
            spec,
            {k: arguments[k] for k in ("f1", "f2", "f3", "f4")},
            context=self.state.metadata,
        )
        pending = {
            "type": "sufilter",
            "tool": "sufilter",
            "input": str(self.current_path),
            "parameters": params,
            "reason": str(arguments["reason"]).strip(),
            "status": "pending_approval",
        }
        self.pending_action = pending
        return {
            "status": "pending_approval",
            "message": "Bandpass proposal created. The user must approve it in the UI before execution.",
            "proposal": pending,
        }

    def compare_datasets(self) -> dict[str, Any]:
        filters = [r for r in self.history.list() if r.get("tool") == "sufilter" and r.get("status") == "success"]
        if not filters:
            return {"status": "not_available", "message": "No completed sufilter step exists yet."}

        latest = filters[-1]
        before_path = Path(latest["input"])
        after_path = Path(latest["output"])
        bm = read_su_metadata(before_path)
        am = read_su_metadata(after_path)
        before = load_preview_traces(before_path, bm, self.preview_traces)
        after = load_preview_traces(after_path, am, self.preview_traces)
        p = latest["parameters"]
        qc = compare_filter_result(
            before,
            after,
            bm.dt_s,
            float(p["f2"]),
            float(p["f3"]),
            float(p["f4"]),
        )
        return {
            "status": "success",
            "step_id": latest["step_id"],
            "input": str(before_path),
            "output": str(after_path),
            "parameters": p,
            "traces_compared": int(min(before.shape[0], after.shape[0])),
            **qc,
        }
