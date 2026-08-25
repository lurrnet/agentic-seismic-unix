from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from seismic.io import (
    read_su_metadata,
    get_surange,
    load_preview_traces,
    summarize_su_headers,
)
from seismic.spectrum import summarize_frequency_content
from seismic.qc import compare_filter_result
from su.validator import validate_parameters


TOOL_SCHEMAS = [
    {
        'type': 'function',
        'name': 'inspect_dataset',
        'description': 'Inspect the current SU dataset and return sampling/file metadata plus a bounded surange summary.',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'inspect_frequency',
        'description': 'Inspect mean amplitude-spectrum characteristics of the current SU dataset using preview traces.',
        'parameters': {
            'type': 'object',
            'properties': {'max_traces': {'type': 'integer', 'minimum': 1, 'maximum': 1000}},
            'required': ['max_traces'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'inspect_headers',
        'description': 'Inspect selected common SU trace-header keys and return bounded min/max/uniqueness summaries.',
        'parameters': {
            'type': 'object',
            'properties': {
                'keys': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 12},
                'max_traces': {'type': 'integer', 'minimum': 1, 'maximum': 10000},
            },
            'required': ['keys', 'max_traces'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'inspect_geometry',
        'description': 'Inspect common acquisition/geometry headers including field record, CDP, offset, coordinates and scalco.',
        'parameters': {
            'type': 'object',
            'properties': {'max_traces': {'type': 'integer', 'minimum': 1, 'maximum': 10000}},
            'required': ['max_traces'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'inspect_amplitude',
        'description': 'Compute bounded amplitude statistics from current SU preview traces.',
        'parameters': {
            'type': 'object',
            'properties': {'max_traces': {'type': 'integer', 'minimum': 1, 'maximum': 1000}},
            'required': ['max_traces'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'apply_bandpass_filter',
        'description': 'Propose a four-corner sufilter bandpass.',
        'parameters': {
            'type': 'object',
            'properties': {
                'f1': {'type': 'number'}, 'f2': {'type': 'number'},
                'f3': {'type': 'number'}, 'f4': {'type': 'number'}, 'reason': {'type': 'string'},
            },
            'required': ['f1', 'f2', 'f3', 'f4', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'apply_gain',
        'description': 'Propose deterministic sugain time/power gain and clipping.',
        'parameters': {
            'type': 'object',
            'properties': {
                'tpow': {'type': 'number'}, 'gpow': {'type': 'number'},
                'qclip': {'type': 'number'}, 'reason': {'type': 'string'},
            },
            'required': ['tpow', 'gpow', 'qclip', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'apply_agc',
        'description': 'Propose automatic gain control using sugain agc=1. wagc is in seconds.',
        'parameters': {
            'type': 'object',
            'properties': {'wagc': {'type': 'number'}, 'reason': {'type': 'string'}},
            'required': ['wagc', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'select_traces',
        'description': 'Propose selecting a subset of traces using suwind key/min/max.',
        'parameters': {
            'type': 'object',
            'properties': {
                'key': {'type': 'string'}, 'min': {'type': 'number'},
                'max': {'type': 'number'}, 'reason': {'type': 'string'},
            },
            'required': ['key', 'min', 'max', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'set_header_constant',
        'description': 'Propose setting one whitelisted SU header key to a constant integer for every trace. Always requires UI approval.',
        'parameters': {
            'type': 'object',
            'properties': {'key': {'type': 'string'}, 'value': {'type': 'integer'}, 'reason': {'type': 'string'}},
            'required': ['key', 'value', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'sort_dataset',
        'description': 'Propose sorting the current SU dataset by one whitelisted trace-header key.',
        'parameters': {
            'type': 'object',
            'properties': {'key': {'type': 'string'}, 'reason': {'type': 'string'}},
            'required': ['key', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'resample_dataset',
        'description': 'Propose resampling the current SU dataset to a new sample interval dt in seconds.',
        'parameters': {
            'type': 'object',
            'properties': {'dt': {'type': 'number'}, 'reason': {'type': 'string'}},
            'required': ['dt', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'apply_mute',
        'description': 'Propose a bounded top or bottom polygonal mute using key, xmute points, tmute seconds, mode, and ntaper.',
        'parameters': {
            'type': 'object',
            'properties': {
                'key': {'type': 'string'},
                'xmute': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 32},
                'tmute': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 32},
                'mode': {'type': 'integer'},
                'ntaper': {'type': 'integer'},
                'reason': {'type': 'string'},
            },
            'required': ['key', 'xmute', 'tmute', 'mode', 'ntaper', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'stack_traces',
        'description': 'Propose stacking adjacent traces sharing a gather key. Current dataset must be the direct output of sorting by the same key.',
        'parameters': {
            'type': 'object',
            'properties': {
                'key': {'type': 'string'}, 'normpow': {'type': 'number'}, 'reason': {'type': 'string'},
            },
            'required': ['key', 'normpow', 'reason'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'type': 'function',
        'name': 'compare_datasets',
        'description': 'Compare the most recent sufilter input and output using machine-readable QC metrics.',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        'strict': True,
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
        if name == 'inspect_dataset': return self.inspect_dataset()
        if name == 'inspect_frequency': return self.inspect_frequency(arguments)
        if name == 'inspect_headers': return self.inspect_headers(arguments)
        if name == 'inspect_geometry': return self.inspect_geometry(arguments)
        if name == 'inspect_amplitude': return self.inspect_amplitude(arguments)
        if name == 'apply_bandpass_filter': return self.propose_bandpass(arguments)
        if name == 'apply_gain': return self.propose_gain(arguments)
        if name == 'apply_agc': return self.propose_agc(arguments)
        if name == 'select_traces': return self.propose_trace_selection(arguments)
        if name == 'set_header_constant': return self.propose_header_constant(arguments)
        if name == 'sort_dataset': return self.propose_sort(arguments)
        if name == 'resample_dataset': return self.propose_resample(arguments)
        if name == 'apply_mute': return self.propose_mute(arguments)
        if name == 'stack_traces': return self.propose_stack(arguments)
        if name == 'compare_datasets': return self.compare_datasets()
        raise KeyError(f'Unknown agent tool: {name}')

    def inspect_dataset(self) -> dict[str, Any]:
        m = read_su_metadata(self.current_path)
        raw = get_surange(self.current_path)
        lines = raw.splitlines()
        return {
            'dataset': str(self.current_path),
            'samples_per_trace': m.ns,
            'sample_interval_us': m.dt_us,
            'sample_interval_s': m.dt_s,
            'nyquist_hz': m.nyquist_hz,
            'estimated_trace_count': m.estimated_trace_count,
            'file_size_bytes': m.file_size_bytes,
            'endian': m.endian,
            'surange_excerpt': '\n'.join(lines[:80]),
            'surange_truncated': len(lines) > 80,
        }

    def inspect_frequency(self, arguments: dict[str, Any]) -> dict[str, Any]:
        requested = max(1, min(int(arguments.get('max_traces', self.preview_traces)), 1000))
        m = read_su_metadata(self.current_path)
        traces = load_preview_traces(self.current_path, m, requested)
        summary = summarize_frequency_content(traces, m.dt_s)
        return {'dataset': str(self.current_path), 'traces_analyzed': int(traces.shape[0]), 'nyquist_hz': m.nyquist_hz, **summary}

    def inspect_headers(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = arguments.get('keys') or ['fldr', 'tracf', 'cdp', 'offset', 'sx', 'gx']
        requested = max(1, min(int(arguments.get('max_traces', 1000)), 10000))
        m = read_su_metadata(self.current_path)
        result = summarize_su_headers(self.current_path, m, keys, requested)
        return {'dataset': str(self.current_path), **result}

    def inspect_geometry(self, arguments: dict[str, Any]) -> dict[str, Any]:
        requested = max(1, min(int(arguments.get('max_traces', 2000)), 10000))
        keys = ['fldr', 'tracf', 'cdp', 'cdpt', 'offset', 'sx', 'sy', 'gx', 'gy', 'scalco']
        m = read_su_metadata(self.current_path)
        result = summarize_su_headers(self.current_path, m, keys, requested)
        return {
            'dataset': str(self.current_path),
            **result,
            'coordinate_note': (
                'sx/sy/gx/gy are raw SU header values. Interpret physical coordinates with scalco; '
                'positive scalco multiplies, negative scalco divides by its absolute value, and zero means 1.'
            ),
        }

    def inspect_amplitude(self, arguments: dict[str, Any]) -> dict[str, Any]:
        requested = max(1, min(int(arguments.get('max_traces', self.preview_traces)), 1000))
        m = read_su_metadata(self.current_path)
        traces = load_preview_traces(self.current_path, m, requested)
        flat = traces.astype(np.float64, copy=False).ravel()
        abs_flat = np.abs(flat)
        return {
            'dataset': str(self.current_path),
            'traces_analyzed': int(traces.shape[0]),
            'samples_analyzed': int(flat.size),
            'min': float(np.min(flat)), 'max': float(np.max(flat)), 'mean': float(np.mean(flat)),
            'rms': float(np.sqrt(np.mean(flat * flat))),
            'p50_abs': float(np.percentile(abs_flat, 50)),
            'p95_abs': float(np.percentile(abs_flat, 95)),
            'p99_abs': float(np.percentile(abs_flat, 99)),
            'zero_fraction': float(np.mean(flat == 0.0)),
        }

    def _propose_processing(self, *, action_name, registry_tool, parameters, reason, operation):
        spec = self.registry.get(registry_tool)
        if spec.get('approval_level') != 'processing':
            raise ValueError(f'{registry_tool} is not configured as processing.')
        params = validate_parameters(spec, parameters, context=self.state.metadata)
        pending = {
            'type': 'processing', 'action': action_name, 'tool': registry_tool,
            'operation': operation, 'display_name': spec.get('display_name', registry_tool),
            'category': spec.get('category', 'processing'),
            'approval_level': spec.get('approval_level', 'processing'),
            'approval_policy': spec.get('approval_policy', 'always'),
            'input': str(self.current_path), 'parameters': params,
            'reason': str(reason).strip(), 'status': 'pending_approval',
        }
        self.pending_action = pending
        return {'status': 'pending_approval', 'message': f"{pending['display_name']} proposal created.", 'proposal': pending}

    def propose_bandpass(self, arguments):
        return self._propose_processing(action_name='apply_bandpass_filter', registry_tool='sufilter', parameters={k: arguments[k] for k in ('f1', 'f2', 'f3', 'f4')}, reason=arguments['reason'], operation='filter')

    def propose_gain(self, arguments):
        return self._propose_processing(action_name='apply_gain', registry_tool='sugain', parameters={k: arguments[k] for k in ('tpow', 'gpow', 'qclip')}, reason=arguments['reason'], operation='gain')

    def propose_agc(self, arguments):
        return self._propose_processing(action_name='apply_agc', registry_tool='suagc', parameters={'wagc': arguments['wagc']}, reason=arguments['reason'], operation='agc')

    def propose_trace_selection(self, arguments):
        return self._propose_processing(action_name='select_traces', registry_tool='suwind', parameters={k: arguments[k] for k in ('key', 'min', 'max')}, reason=arguments['reason'], operation='select')

    def propose_header_constant(self, arguments):
        return self._propose_processing(action_name='set_header_constant', registry_tool='sushw_constant', parameters={'key': arguments['key'], 'value': arguments['value']}, reason=arguments['reason'], operation='header')

    def propose_sort(self, arguments):
        return self._propose_processing(action_name='sort_dataset', registry_tool='susort', parameters={'key': arguments['key']}, reason=arguments['reason'], operation='sort')

    def propose_resample(self, arguments):
        return self._propose_processing(action_name='resample_dataset', registry_tool='suresamp', parameters={'dt': arguments['dt']}, reason=arguments['reason'], operation='resample')

    def propose_mute(self, arguments):
        return self._propose_processing(
            action_name='apply_mute', registry_tool='sumute',
            parameters={k: arguments[k] for k in ('key', 'xmute', 'tmute', 'mode', 'ntaper')},
            reason=arguments['reason'], operation='mute')

    def _current_is_sorted_by(self, key: str) -> bool:
        current = str(self.current_path)
        successful = [r for r in self.history.list() if r.get('status') == 'success']
        if not successful:
            return False
        latest = successful[-1]
        return (
            latest.get('tool') == 'susort'
            and str(latest.get('output')) == current
            and str((latest.get('parameters') or {}).get('key')) == str(key)
        )

    def propose_stack(self, arguments):
        key = str(arguments['key'])
        if not self._current_is_sorted_by(key):
            raise ValueError(
                f'Current dataset is not the direct output of susort key={key}. '
                f'Sort by {key} immediately before stacking.'
            )
        return self._propose_processing(
            action_name='stack_traces', registry_tool='sustack',
            parameters={'key': key, 'normpow': arguments['normpow']},
            reason=arguments['reason'], operation='stack')

    def compare_datasets(self) -> dict[str, Any]:
        filters = [r for r in self.history.list() if r.get('tool') == 'sufilter' and r.get('status') == 'success']
        if not filters:
            return {'status': 'not_available', 'message': 'No completed sufilter step exists yet.'}
        latest = filters[-1]
        before_path = Path(latest['input'])
        after_path = Path(latest['output'])
        bm = read_su_metadata(before_path)
        am = read_su_metadata(after_path)
        before = load_preview_traces(before_path, bm, self.preview_traces)
        after = load_preview_traces(after_path, am, self.preview_traces)
        p = latest['parameters']
        qc = compare_filter_result(before, after, bm.dt_s, float(p['f2']), float(p['f3']), float(p['f4']))
        return {
            'status': 'success', 'step_id': latest['step_id'],
            'input': str(before_path), 'output': str(after_path), 'parameters': p,
            'traces_compared': int(min(before.shape[0], after.shape[0])), **qc,
        }
