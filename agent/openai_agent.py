"""Backward-compatible import shim for V0.3 code."""
from .seismic_agent import SeismicAgent
from .providers.base import AgentConfigurationError

__all__ = ["SeismicAgent", "AgentConfigurationError"]
