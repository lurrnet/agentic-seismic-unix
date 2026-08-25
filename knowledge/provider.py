from __future__ import annotations

from typing import Any

from agent.providers.base import AgentProvider
from .su_docs import SUDocKnowledgeBase


class KnowledgeAugmentedProvider(AgentProvider):
    """Wrap an existing provider with bounded local SU documentation retrieval."""

    def __init__(self, provider: AgentProvider, knowledge: SUDocKnowledgeBase | None = None):
        self.provider = provider
        self.knowledge = knowledge or SUDocKnowledgeBase()
        self.name = provider.name
        self.model = provider.model

    def __getattr__(self, name: str):
        # Preserve provider-specific behavior such as OpenClaw tool_strategy,
        # agent_id, base_url, and future provider attributes.
        return getattr(self.provider, name)

    @staticmethod
    def _query_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get('content') or item.get('text')
                    if isinstance(text, str):
                        parts.append(text)
            return '\n'.join(parts)
        return str(value or '')

    def create_response(self, **kwargs: Any):
        query = self._query_text(kwargs.get('input'))
        context = self.knowledge.render_context(query)
        if context:
            instructions = str(kwargs.get('instructions') or '').rstrip()
            kwargs['instructions'] = instructions + '\n\n' + context
        return self.provider.create_response(**kwargs)

    def info(self) -> dict[str, Any]:
        info = dict(self.provider.info())
        info.update({
            'knowledge_layer': 'local_sudoc',
            'knowledge_docs_root': str(self.knowledge.doc_root),
            'knowledge_max_docs': self.knowledge.max_docs,
        })
        return info
