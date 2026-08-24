from __future__ import annotations

import json
from typing import Any

from .prompts import SYSTEM_PROMPT
from .toolkit import TOOL_SCHEMAS, AgentToolkit
from .provider_factory import create_provider
from .providers.base import AgentProvider, AgentConfigurationError


class SeismicAgent:
    def __init__(self, provider: AgentProvider | None = None):
        self.provider = provider or create_provider()

    @property
    def provider_info(self) -> dict[str, Any]:
        return self.provider.info()

    def run_turn(
        self,
        user_text: str,
        chat_history: list[dict[str, str]],
        toolkit: AgentToolkit,
        *,
        max_tool_rounds: int = 8,
    ) -> dict[str, Any]:
        input_items: list[dict[str, Any]] = []
        for message in chat_history[-20:]:
            role = message.get("role")
            content = message.get("content", "")
            if role in {"user", "assistant"} and content:
                input_items.append({"role": role, "content": content})
        input_items.append({"role": "user", "content": user_text})

        response = self.provider.create_response(
            instructions=SYSTEM_PROMPT,
            input=input_items,
            tools=TOOL_SCHEMAS,
        )

        tool_trace: list[dict[str, Any]] = []
        rounds = 0

        while rounds < max_tool_rounds:
            calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]
            if not calls:
                break

            rounds += 1
            outputs = []
            for call in calls:
                arguments = {}
                try:
                    arguments = json.loads(call.arguments or "{}")
                    result = toolkit.call(call.name, arguments)
                except Exception as exc:
                    result = {"status": "error", "error": str(exc)}

                tool_trace.append({
                    "tool": call.name,
                    "arguments": arguments,
                    "result": result,
                })
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                })

            response = self.provider.create_response(
                instructions=SYSTEM_PROMPT,
                previous_response_id=response.id,
                input=outputs,
                tools=TOOL_SCHEMAS,
            )

        if rounds >= max_tool_rounds and any(
            getattr(item, "type", None) == "function_call" for item in response.output
        ):
            raise RuntimeError("Agent exceeded the maximum tool-call rounds.")

        text = (response.output_text or "").strip()
        if not text:
            text = "I completed the tool calls, but the model returned no final text."

        return {
            "text": text,
            "pending_action": toolkit.pending_action,
            "tool_trace": tool_trace,
            "provider": self.provider.name,
            "model": self.provider.model,
            "provider_info": self.provider.info(),
        }
