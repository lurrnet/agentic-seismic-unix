from __future__ import annotations

import json
import re
from typing import Any


class ReflectionParseError(ValueError):
    pass


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract one JSON object from a model response.

    The reflection prompt asks for JSON-only output, but this parser tolerates
    a fenced JSON block or a small amount of surrounding prose. It never
    executes model-generated content.
    """
    raw = (text or "").strip()
    if not raw:
        raise ReflectionParseError("Empty reflection response.")

    # Remove a single fenced block when present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        raw = fenced.group(1)

    # First try the full text.
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # Then find the first balanced top-level JSON object.
    start = raw.find("{")
    if start < 0:
        raise ReflectionParseError("Reflection response did not contain a JSON object.")

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = raw[start:i + 1]
                try:
                    value = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ReflectionParseError(f"Invalid reflection JSON: {exc}") from exc
                if not isinstance(value, dict):
                    raise ReflectionParseError("Reflection JSON must be an object.")
                return value

    raise ReflectionParseError("Unterminated JSON object in reflection response.")
