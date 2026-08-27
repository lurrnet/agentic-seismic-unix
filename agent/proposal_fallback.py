from __future__ import annotations

import re
from typing import Any


_HEADER_KEYS = r'tracl|tracr|fldr|tracf|ep|cdp|cdpt|offset|sx|sy|gx|gy'


def normalize_processing_text(text: str) -> str:
    """Normalize common seismic-processing wording without inferring parameters."""
    normalized = text.lower()
    replacements = (
        (r'\bband[\s-]+pass\b', 'bandpass'),
        (r'\bre[\s-]+sample\b', 'resample'),
        (r'\bpre[\s-]+stack\b', 'prestack'),
        (r'\bpredictive[\s-]+deconvolution\b', 'predictive decon'),
        (r'\bpredictive[\s-]+decon\b', 'predictive decon'),
        (r'\bpredictive error filter\b', 'predictive decon'),
        (r'\bautomatic gain control\b', 'agc'),
        (r'\bnormal moveout\b', 'nmo'),
        (r'\bmoveout correction\b', 'nmo'),
        (r'\bsampling interval\b', 'sample interval'),
    )
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return normalized


def _number(value: str) -> float:
    return float(value.replace(',', ''))


def _number_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(',') if item.strip()]


def _time_to_seconds(value: str, unit: str | None) -> float:
    result = float(value)
    token = (unit or 's').lower()
    if token in {'us', 'usec', 'usecs', 'microsecond', 'microseconds'}:
        return result / 1_000_000.0
    if token in {'ms', 'msec', 'msecs', 'millisecond', 'milliseconds'}:
        return result / 1000.0
    return result


def _time_value_pattern(label: str) -> re.Pattern[str]:
    return re.compile(
        rf'\b{label}\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*'
        rf'(us|usec|usecs|microsecond|microseconds|ms|msec|msecs|millisecond|milliseconds|s|sec|secs|second|seconds)?\b',
        flags=re.IGNORECASE,
    )


def parse_proposal_from_text(action: str, text: str) -> dict[str, Any] | None:
    """Best-effort deterministic parser for structured processing parameters."""
    normalized = normalize_processing_text(text)

    if action == 'apply_bandpass_filter':
        labels = re.search(
            r'f1\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f2\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f3\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f4\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)',
            normalized,
            flags=re.IGNORECASE,
        )
        if labels:
            vals = [float(x) for x in labels.groups()]
            return {
                'action': action,
                'parameters': {'f1': vals[0], 'f2': vals[1], 'f3': vals[2], 'f4': vals[3]},
                'reason': 'Bandpass parameters parsed from text.',
                'parsed_from': 'labeled_text',
            }
        seq = re.search(
            r'(?<![0-9.])([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*(?:hz)?\b',
            normalized,
            flags=re.IGNORECASE,
        )
        if seq and ('bandpass' in normalized or 'filter' in normalized or 'hz' in normalized):
            vals = [float(x) for x in seq.groups()]
            return {
                'action': action,
                'parameters': {'f1': vals[0], 'f2': vals[1], 'f3': vals[2], 'f4': vals[3]},
                'reason': 'Bandpass parameters parsed from text.',
                'parsed_from': 'frequency_sequence',
            }

    if action == 'apply_agc':
        explicit = _time_value_pattern('wagc').search(normalized)
        if explicit:
            return {
                'action': action,
                'parameters': {'wagc': _time_to_seconds(explicit.group(1), explicit.group(2))},
                'reason': 'AGC window parsed from text.',
                'parsed_from': 'wagc_label',
            }
        window = re.search(
            r'\b([0-9]+(?:\.[0-9]+)?)\s*'
            r'(ms|msec|msecs|millisecond|milliseconds|s|sec|secs|second|seconds)\b'
            r'(?:\s*(?:agc\s*)?window)?',
            normalized,
            flags=re.IGNORECASE,
        )
        if window and 'agc' in normalized:
            return {
                'action': action,
                'parameters': {'wagc': _time_to_seconds(window.group(1), window.group(2))},
                'reason': 'AGC window parsed from text.',
                'parsed_from': 'agc_window',
            }

    if action == 'apply_gain':
        values = {}
        for key in ('scale', 'tpow', 'gpow', 'qclip'):
            match = re.search(
                rf'\b{key}\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?)',
                normalized,
                flags=re.IGNORECASE,
            )
            if match:
                values[key] = float(match.group(1))
        if values:
            return {
                'action': action,
                'parameters': {
                    'scale': values.get('scale', 1.0),
                    'tpow': values.get('tpow', 0.0),
                    'gpow': values.get('gpow', 1.0),
                    'qclip': values.get('qclip', 1.0),
                },
                'reason': 'Gain parameters parsed from text.',
                'parsed_from': 'gain_labels',
            }
        scalar = re.search(
            r'\b(?:gain(?:\s+of)?|multiply(?:\s+(?:the\s+)?(?:data|amplitude|amplitudes))?\s+by|scale(?:\s+by)?)\s+'
            r'(-?[0-9]+(?:\.[0-9]+)?)\s*(?:x|times)?\b',
            normalized,
            flags=re.IGNORECASE,
        )
        if scalar:
            return {
                'action': action,
                'parameters': {
                    'scale': float(scalar.group(1)),
                    'tpow': 0.0,
                    'gpow': 1.0,
                    'qclip': 1.0,
                },
                'reason': 'Scalar gain parsed from explicit user command.',
                'parsed_from': 'scalar_gain',
            }

    if action == 'select_traces':
        key_match = re.search(rf'\b(?:key\s*[:=]\s*)?({_HEADER_KEYS})s?\b', normalized)
        range_match = re.search(
            r'\b(?:between|from)\s*(-?[0-9]+(?:\.[0-9]+)?)\s*'
            r'(?:and|to|[-–—])\s*(-?[0-9]+(?:\.[0-9]+)?)',
            normalized,
        )
        if not range_match:
            range_match = re.search(
                rf'\b(?:{_HEADER_KEYS})s?\b\s*(?:=|:)?\s*'
                r'(-?[0-9]+(?:\.[0-9]+)?)\s*(?:to|[-–—])\s*'
                r'(-?[0-9]+(?:\.[0-9]+)?)',
                normalized,
            )
        if key_match and range_match:
            lo, hi = (_number(range_match.group(1)), _number(range_match.group(2)))
            return {
                'action': action,
                'parameters': {'key': key_match.group(1).lower(), 'min': lo, 'max': hi},
                'reason': 'Trace-selection bounds parsed from text.',
                'parsed_from': 'header_range',
            }

    if action == 'set_header_constant':
        match = re.search(
            rf'\b({_HEADER_KEYS})\b(?:\s+(?:header|key))?\s*(?:to|=|:)\s*(-?[0-9]+)\b',
            normalized,
        )
        if match:
            return {
                'action': action,
                'parameters': {'key': match.group(1).lower(), 'value': int(match.group(2))},
                'reason': 'Header constant parsed from text.',
                'parsed_from': 'header_constant',
            }

    if action == 'sort_dataset':
        match = re.search(
            rf'\b(?:by|on|key\s*[:=]\s*)\s*({_HEADER_KEYS})\b',
            normalized,
        )
        if not match:
            match = re.search(rf'\b({_HEADER_KEYS})\s+sort\b', normalized)
        if match:
            return {
                'action': action,
                'parameters': {'key': match.group(1).lower()},
                'reason': 'Sort key parsed from text.',
                'parsed_from': 'sort_key',
            }

    if action == 'resample_dataset':
        dt = re.search(
            r'\b(?:dt\s*[:=]\s*|to\s+|sample interval\s*(?:to|=|:)\s*|sample rate\s*(?:to|=|:)\s*)?'
            r'([0-9]+(?:\.[0-9]+)?)\s*'
            r'(us|usec|usecs|microsecond|microseconds|ms|msec|msecs|millisecond|milliseconds|s|sec|secs|second|seconds)\b',
            normalized,
        )
        if dt:
            return {
                'action': action,
                'parameters': {'dt': _time_to_seconds(dt.group(1), dt.group(2))},
                'reason': 'Sample interval parsed from text.',
                'parsed_from': 'sample_interval',
            }

    if action == 'apply_mute':
        key = re.search(r'\bkey\s*[:=]\s*(tracl|tracr|fldr|cdp|offset)\b', normalized)
        xmute = re.search(r'\bxmute\s*[:=]\s*([-0-9.,\s]+)', normalized)
        tmute = re.search(r'\btmute\s*[:=]\s*([0-9.,\s]+)', normalized)
        ntaper = re.search(r'\bntaper\s*[:=]\s*([0-9]+)', normalized)
        mode_match = re.search(r'\bmode\s*[:=]\s*([01])\b', normalized)
        if not mode_match:
            if re.search(r'\b(?:top|above)\s+mute\b', normalized):
                mode = 0
            elif re.search(r'\b(?:bottom|below)\s+mute\b', normalized):
                mode = 1
            else:
                mode = None
        else:
            mode = int(mode_match.group(1))
        if key and xmute and tmute and mode is not None:
            return {
                'action': action,
                'parameters': {
                    'key': key.group(1).lower(),
                    'xmute': _number_list(xmute.group(1)),
                    'tmute': _number_list(tmute.group(1)),
                    'mode': mode,
                    'ntaper': int(ntaper.group(1)) if ntaper else 0,
                },
                'reason': 'Mute parameters parsed from text.',
                'parsed_from': 'mute_labels',
            }

        simple = re.search(
            r'\bmute\b.*?\b(above|before|top|below|after|bottom)\b.*?'
            r'([0-9]+(?:\.[0-9]+)?)\s*'
            r'(ms|msec|milliseconds?|s|sec|secs|seconds?)\b',
            normalized,
        )
        if not simple:
            simple = re.search(
                r'\b(above|before|top|below|after|bottom)\b.*?'
                r'([0-9]+(?:\.[0-9]+)?)\s*'
                r'(ms|msec|milliseconds?|s|sec|secs|seconds?)\b.*?\bmute\b',
                normalized,
            )
        if simple:
            direction = simple.group(1).lower()
            mute_time = _time_to_seconds(simple.group(2), simple.group(3))
            mode = 0 if direction in ('above', 'before', 'top') else 1
            return {
                'action': action,
                'parameters': {
                    'key': 'tracl',
                    'xmute': [0.0, 1.0],
                    'tmute': [mute_time, mute_time],
                    'mode': mode,
                    'ntaper': 0,
                },
                'reason': 'Constant whole-line mute parsed from explicit user command.',
                'parsed_from': 'simple_constant_mute',
            }

    if action == 'stack_traces':
        key = re.search(r'\b(?:by|key\s*[:=]\s*)(cdp|fldr|ep)\b', normalized)
        if not key:
            key = re.search(r'\b(cdp|fldr|ep)\s+(?:stack|stacking)\b', normalized)
        normpow = re.search(r'\bnormpow\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', normalized)
        if key:
            return {
                'action': action,
                'parameters': {
                    'key': key.group(1).lower(),
                    'normpow': float(normpow.group(1)) if normpow else 1.0,
                },
                'reason': 'Stack parameters parsed from text.',
                'parsed_from': 'stack_key',
            }

    if action == 'apply_predictive_decon':
        minlag = _time_value_pattern('minlag').search(normalized)
        maxlag = _time_value_pattern('maxlag').search(normalized)
        if not minlag:
            minlag = re.search(
                r'\b(?:prediction lag|prediction distance)\s*(?:of|=|:)?\s*'
                r'([0-9]+(?:\.[0-9]+)?)\s*'
                r'(ms|msec|msecs|millisecond|milliseconds|s|sec|secs|second|seconds)\b',
                normalized,
            )
        if not maxlag:
            maxlag = re.search(
                r'\bmax(?:imum)? lag\s*(?:of|=|:)?\s*'
                r'([0-9]+(?:\.[0-9]+)?)\s*'
                r'(ms|msec|msecs|millisecond|milliseconds|s|sec|secs|second|seconds)\b',
                normalized,
            )
        pnoise = re.search(r'\bpnoise\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', normalized)
        if minlag and maxlag:
            return {
                'action': action,
                'parameters': {
                    'minlag': _time_to_seconds(minlag.group(1), minlag.group(2)),
                    'maxlag': _time_to_seconds(maxlag.group(1), maxlag.group(2)),
                    'pnoise': float(pnoise.group(1)) if pnoise else 0.001,
                },
                'reason': 'Predictive-decon parameters parsed from text.',
                'parsed_from': 'decon_lags',
            }

    if action == 'apply_nmo':
        tnmo = re.search(r'\btnmo\s*[:=]\s*([0-9.,\s]+)', normalized)
        vnmo = re.search(r'\bvnmo\s*[:=]\s*([0-9.,\s]+)', normalized)
        smute = re.search(r'\bsmute\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)', normalized)
        lmute = re.search(r'\blmute\s*[:=]\s*([0-9]+)', normalized)
        sscale = re.search(r'\bsscale\s*[:=]\s*([01])\b', normalized)
        if tnmo and vnmo:
            return {
                'action': action,
                'parameters': {
                    'tnmo': _number_list(tnmo.group(1)),
                    'vnmo': _number_list(vnmo.group(1)),
                    'smute': float(smute.group(1)) if smute else 1.5,
                    'lmute': int(lmute.group(1)) if lmute else 25,
                    'sscale': int(sscale.group(1)) if sscale else 1,
                },
                'reason': 'NMO parameters parsed from text.',
                'parsed_from': 'nmo_labels',
            }

    return None


def parse_explicit_user_command(text: str) -> dict[str, Any] | None:
    """Return a complete direct-execution command only for explicit user authorization."""
    lowered = normalize_processing_text(text)
    if any(token in lowered for token in (
        'recommend', 'suggest', 'what should', 'which should', 'what would',
        'reasonable', 'appropriate', 'best ', 'should i',
    )):
        return None

    action = None
    if re.search(r'\b(?:apply|run|execute)\b.*\b(?:bandpass|filter)\b', lowered):
        action = 'apply_bandpass_filter'
    elif re.search(r'\b(?:apply|run|execute)\b.*\bagc\b', lowered):
        action = 'apply_agc'
    elif re.search(r'\b(?:apply|run|execute)\b.*\bgain\b', lowered) or re.search(
        r'\b(?:multiply|scale)\b.*\b(?:by|gain)\b', lowered
    ):
        action = 'apply_gain'
    elif re.search(
        rf'\b(?:select|keep|retain|window|only keep)\b.*\b(?:trace|traces|{_HEADER_KEYS})s?\b',
        lowered,
    ):
        action = 'select_traces'
    elif re.search(r'\b(?:sort|order|reorder)\b.*\b(?:by|on|key)\b', lowered) or re.search(
        rf'\b(?:{_HEADER_KEYS})\s+sort\b', lowered
    ):
        action = 'sort_dataset'
    elif re.search(r'\b(?:resample|change sample interval|change sampling|sample interval|sample rate)\b', lowered):
        action = 'resample_dataset'
    elif re.search(r'\bmute\b', lowered) and (
        re.search(r'\b(?:apply|run|execute)\b', lowered)
        or re.search(r'\b(?:above|before|top|below|after|bottom)\b', lowered)
        or re.search(r'\b(?:xmute|tmute|mode)\b', lowered)
    ):
        action = 'apply_mute'
    elif re.search(r'\b(?:stack|stacking)\b.*\b(?:by|key|cdp|fldr|ep)\b', lowered) or re.search(
        r'\b(?:cdp|fldr|ep)\s+(?:stack|stacking)\b', lowered
    ):
        action = 'stack_traces'
    elif re.search(r'\b(?:apply|run|execute)\b.*\b(?:decon|deconvolution|pef|predictive decon)\b', lowered):
        action = 'apply_predictive_decon'
    elif re.search(r'\b(?:apply|run|execute)\b.*\b(?:nmo)\b', lowered):
        action = 'apply_nmo'

    if action is None:
        return None
    parsed = parse_proposal_from_text(action, text)
    if parsed is None:
        return None
    parsed['authorization'] = 'explicit_user_command'
    parsed['reason'] = 'Explicit user command with complete parameters.'
    return parsed
