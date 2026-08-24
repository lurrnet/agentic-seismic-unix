from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentConfigurationError(RuntimeError):
    pass


class AgentProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def create_response(self, **kwargs: Any):
        raise NotImplementedError

    @property
    def display_name(self) -> str:
        return self.name

    def info(self) -> dict[str, Any]:
        return {"provider": self.name, "model": self.model}
