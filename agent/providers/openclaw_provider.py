from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from .base import AgentProvider, AgentConfigurationError


class OpenClawProvider(AgentProvider):
    name = "openclaw"

    def __init__(self, config: dict[str, Any]):
        self.base_url = str(config.get("base_url") or "http://127.0.0.1:18789/v1").rstrip("/")
        self.model = str(config.get("model") or "openclaw/default")
        self.agent_id = config.get("agent_id")
        credential_env = str(config.get("credential_env") or "OPENCLAW_GATEWAY_TOKEN")
        credential = os.getenv(credential_env)
        if not credential:
            raise AgentConfigurationError(
                f"OpenClaw provider selected but {credential_env} is not configured. "
                "Set the Gateway token/password in .env and enable gateway.http.endpoints.responses."
            )
        self.credential_env = credential_env

        headers = {}
        if self.agent_id:
            headers["x-openclaw-agent-id"] = str(self.agent_id)

        # OpenClaw exposes an OpenResponses-compatible /v1/responses surface.
        # The OpenAI SDK is used only as the protocol client here; the request
        # is routed to the local OpenClaw Gateway, not to api.openai.com.
        self.client = OpenAI(
            api_key=credential,
            base_url=self.base_url,
            default_headers=headers or None,
        )

    def create_response(self, **kwargs: Any):
        kwargs.setdefault("model", self.model)
        return self.client.responses.create(**kwargs)

    def info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "agent_id": self.agent_id,
            "credential_env": self.credential_env,
        }
