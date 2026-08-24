from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from .base import AgentProvider, AgentConfigurationError


class OpenAIProvider(AgentProvider):
    name = "openai"

    def __init__(self, config: dict[str, Any]):
        self.model = str(config.get("model") or "gpt-5.6")
        key_env = str(config.get("api_key_env") or "OPENAI_API_KEY")
        api_key = os.getenv(key_env)
        if not api_key:
            raise AgentConfigurationError(
                f"OpenAI provider selected but {key_env} is not configured."
            )
        self.key_env = key_env
        self.client = OpenAI(api_key=api_key)

    def create_response(self, **kwargs: Any):
        kwargs.setdefault("model", self.model)
        return self.client.responses.create(**kwargs)

    def info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "credential_env": self.key_env,
        }
