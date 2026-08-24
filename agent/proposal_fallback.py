from __future__ import annotations

import re
from typing import Any


def _number(value: str) -> float:
    return float(value.replace(',', ''))


def parse_proposal_from_text(action: str, text: str) -> dict[str, Any] | None:
    """Best-effort deterministic parser for structured processing parameters.

    Parsed values never execute by themselves. They still pass through the
    toolkit/registry validator before either direct execution or approval.
    """
    if action == 'apply_bandpass_filter':
        labels = re.search(
            r'f1\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f2\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f3\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+'
            r'f4\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)',
            text,
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
            r'(?<![0-9.])'
            r'([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*'
            r'([0-9]+(?:\.[0-9]+)?)\s*Hz\b',
            text,
            flags=re.IGNORECASE,
        )
        if seq:
            vals = [float(x) for x in seq.groups()]
            return {
                'action': action,
                'parameters': {'f1': vals[0], 'f2': vals[1], 'f3': vals[2], 'f4': vals[3]},
                'reason': 'Bandpass parameters parsed from text.',
                'parsed_from': 'frequency_sequence',
            }

    if action == 'apply_agc':
        explicit = re.search(
            r'\bwagc\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)',
            text,
            flags=re.IGNORECASE,
        )
        if explicit:
            return {
                'action': action,
                'parameters': {'wagc': float(explicit.group(1))},
                'reason': 'AGC window parsed from text.',
                'parsed_from': 'wagc_label',
            }

        seconds = re.search(
            r'\b([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|secs|second|seconds)\b'
            r'(?:(?:\s+|-)(?:agc\s*)?window)?',
            text,
            flags=re.IGNORECASE,
        )
        if seconds:
            return {
                'action': action,
                'parameters': {'wagc': float(seconds.group(1))},
                'reason': 'AGC window parsed from text.',
                'parsed_from': 'seconds_window',
            }

        milliseconds = re.search(
            r'\b([0-9]+(?:\.[0-9]+)?)\s*(?:ms|msec|msecs|millisecond|milliseconds)\b'
            r'(?:(?:\s+|-)(?:agc\s*)?window)?',
            text,
            flags=re.IGNORECASE,
        )
        if milliseconds:
            return {
                'action': action,
                'parameters': {'wagc': float(milliseconds.group(1)) / 1000.0},
                'reason': 'AGC window parsed from text.',
                'parsed_from': 'milliseconds_window',
            }

    if action == 'apply_gain':
        values = {}
        for key in ('tpow', 'gpow', 'qclip'):
            match = re.search(
                rf'\b{key}\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?)',
                text,
                flags=re.IGNORECASE,
            )
            if match:
                values[key] = float(match.group(1))
        if all(key in values for key in ('tpow', 'gpow', 'qclip')):
            return {
                'action': action,
                'parameters': values,
                'reason': 'Gain parameters parsed from text.',
                'parsed_from': 'gain_labels',
            }

    if action == 'select_traces':
        key_match = re.search(
            r'\b(?:key\s*[:=]\s*)?(fldr|tracf|cdp|offset|sx|sy|gx|gy|tracl|tracr)\b',
            text,
            flags=re.IGNORECASE,
        )
        range_match = re.search(
            r'\b(?:between|from)\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(?:and|to|[-–—])\s*'
            r'(-?[0-9]+(?:\.[0-9]+)?)',
            text,
            flags=re.IGNORECASE,
        )
        if key_match and range_match:
            lo, hi = (_number(range_match.group(1)), _number(range_match.group(2)))
            return {
                'action': action,
                'parameters': {'key': key_match.group(1).lower(), 'min': lo, 'max': hi},
                'reason': 'Trace-selection bounds parsed from text.',
                'parsed_from': 'header_range',
            }

    return None


def parse_explicit_user_command(text: str) -> dict[str, Any] | None:
    """Return a complete processing command only when the USER explicitly authorizes it.

    This is deliberately stricter than the agent proposal parser. Recommendation
    language never qualifies, and every parameter required for direct execution
    must be present in the same user message.
    """
    lowered = text.lower()
    if any(token in lowered for token in (
        'recommend', 'suggest', 'what should', 'which should', 'what would',
        'reasonable', 'appropriate', 'best ', 'should i',
    )):
        return None

    action = None
    if re.search(r'\b(?:apply|run|execute)\b.*\b(?:bandpass|filter)\b', lowered):
        action = 'apply_bandpass_filter'
    elif re.search(r'\b(?:apply|run|execute)\b.*\bagc\b', lowered) or (
        'automatic gain control' in lowered and re.search(r'\b(?:apply|run|execute)\b', lowered)
    ):
        action = 'apply_agc'
    elif re.search(r'\b(?:apply|run|execute)\b.*\bgain\b', lowered):
        action = 'apply_gain'
    elif re.search(r'\b(?:select|keep|retain|window)\b.*\b(?:trace|traces|offset|cdp|fldr)\b', lowered):
        action = 'select_traces'

    if action is None:
        return None

    parsed = parse_proposal_from_text(action, text)
    if parsed is None:
        return None

    parsed['authorization'] = 'explicit_user_command'
    parsed['reason'] = 'Explicit user command with complete parameters.'
    return parsed
