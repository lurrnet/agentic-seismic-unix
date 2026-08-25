from __future__ import annotations

from typing import Any

from .provider_factory import create_provider
from .providers.base import AgentProvider


KNOWLEDGE_MODE_INSTRUCTIONS = """You are the knowledge-only mode of Agentic SeismicUnix.

No seismic dataset is loaded.

You may:
- explain Seismic Unix commands, parameters, concepts, workflows, and processing principles;
- use application-supplied local SU documentation as reference knowledge;
- discuss how a user could approach a processing problem in general terms.

You must not:
- claim to inspect, measure, visualize, or know anything about a dataset;
- invent dataset-specific sampling, frequency, amplitude, geometry, gather, velocity, or header facts;
- choose dataset-specific processing parameters as though they were validated recommendations;
- claim that any processing operation ran;
- emit SEISMIC_PROPOSAL envelopes or request application tool execution.

If the user asks for a dataset-specific recommendation or processing action, explain what information would be needed and tell them to load a SEG-Y dataset to enter Project Mode. You can still explain the relevant SU command and parameters in general terms.

Keep the distinction clear: Knowledge Mode explains; Project Mode inspects, validates, proposes, and processes.
"""


def _history_items(chat_history: list[dict[str, str]], user_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for message in chat_history[-20:]:
        role = message.get('role')
        content = message.get('content', '')
        if role in {'user', 'assistant'} and content:
            items.append({'role': role, 'content': content})
    items.append({'role': 'user', 'content': user_text})
    return items


def run_knowledge_turn(
    user_text: str,
    chat_history: list[dict[str, str]],
    provider: AgentProvider | None = None,
) -> dict[str, Any]:
    """Run a pre-upload turn with no seismic application tools available."""
    provider = provider or create_provider()
    kwargs: dict[str, Any] = {
        'instructions': KNOWLEDGE_MODE_INSTRUCTIONS,
        'input': _history_items(chat_history, user_text),
    }
    if provider.name == 'openclaw':
        kwargs['user'] = 'seismic-knowledge-mode'
    response = provider.create_response(**kwargs)
    text = (response.output_text or '').strip()
    if not text:
        text = 'Knowledge Mode completed the turn but returned no text.'
    return {
        'text': text,
        'pending_action': None,
        'tool_trace': [],
        'provider': provider.name,
        'model': provider.model,
        'provider_info': provider.info(),
    }
