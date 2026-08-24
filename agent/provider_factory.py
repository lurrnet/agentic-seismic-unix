from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .providers.base import AgentProvider, AgentConfigurationError
from .providers.openai_provider import OpenAIProvider
from .providers.openclaw_provider import OpenClawProvider


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "agent.yaml"


def load_agent_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path or os.getenv("AGENT_CONFIG_PATH") or default_config_path())
    if not config_path.exists():
        raise AgentConfigurationError(f"Agent config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    config["_config_path"] = str(config_path)
    return config


def create_provider(config: dict[str, Any] | None = None) -> AgentProvider:
    config = config or load_agent_config()
    provider_name = str(os.getenv("AGENT_PROVIDER") or config.get("provider") or "openclaw").lower()

    if provider_name == "openclaw":
        return OpenClawProvider(config.get("openclaw") or {})
    if provider_name == "openai":
        return OpenAIProvider(config.get("openai") or {})

    raise AgentConfigurationError(
        f"Unsupported agent provider: {provider_name}. Expected 'openclaw' or 'openai'."
    )


def provider_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_agent_config()
    provider_name = str(os.getenv("AGENT_PROVIDER") or config.get("provider") or "openclaw").lower()
    section = config.get(provider_name) or {}
    status = {
        "provider": provider_name,
        "config_path": config.get("_config_path"),
        "fallback_provider": config.get("fallback_provider"),
        "model": section.get("model"),
    }
    if provider_name == "openclaw":
        status.update({
            "base_url": section.get("base_url"),
            "agent_id": section.get("agent_id"),
            "credential_env": section.get("credential_env", "OPENCLAW_GATEWAY_TOKEN"),
        })
    elif provider_name == "openai":
        status.update({
            "credential_env": section.get("api_key_env", "OPENAI_API_KEY"),
        })
    return status
