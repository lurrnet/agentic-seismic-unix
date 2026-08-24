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

    @staticmethod
    def _initial_tool_choice(user_text: str) -> dict[str, str] | str:
        """Choose a deterministic first inspection tool for data-specific requests.

        OpenClaw supports client-side function tools, but with tool_choice=auto a
        model is still allowed to answer without calling one. For seismic data
        questions we require evidence first, so obvious inspection intents are
        pinned to the appropriate read-only tool.
        """
        text = user_text.lower()

        if any(token in text for token in (
            "frequency", "spectrum", "spectral", "bandpass",
            "filter recommendation", "recommend a filter", "recommend filter",
        )):
            return {"type": "function", "name": "inspect_frequency"}

        if any(token in text for token in (
            "review the filter", "filter result", "filtering result",
            "did the filter", "compare datasets", "compare the result",
        )):
            return {"type": "function", "name": "compare_datasets"}

        if any(token in text for token in (
            "inspect", "dataset", "data set", "what do you see",
            "tell me what you see", "sampling", "trace count", "surange",
        )):
            return {"type": "function", "name": "inspect_dataset"}

        return "auto"

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

        # OpenClaw's OpenResponses endpoint is stricter than OpenAI's SDK
        # about array-item input schemas. For OpenClaw, send the current user
        # turn as the documented string input and let the Gateway maintain
        # per-project conversational state via the OpenResponses `user` key.
        # OpenAI direct mode keeps the explicit message-history array.
        request_user = None
        if self.provider.name == "openclaw":
            request_input = user_text
            project_id = getattr(getattr(toolkit, "project", None), "project_id", "default")
            request_user = f"seismic-project-{project_id}"
        else:
            request_input = input_items

        project_id = getattr(getattr(toolkit, "project", None), "project_id", "unknown")
        current_dataset = str(getattr(toolkit, "current_path", "unknown"))
        runtime_context = (
            "\n\nRuntime context supplied by the seismic application:\n"
            f"- A seismic dataset IS currently loaded for project {project_id}.\n"
            f"- Current dataset: {current_dataset}.\n"
            "- The client-side function tools listed in this request ARE available to you.\n"
            "- Do not ask the user to attach or load the dataset when an inspection tool can read it.\n"
            "- For data-specific claims, call the appropriate inspection tool and ground the answer in its result."
        )

        create_kwargs = {
            "instructions": SYSTEM_PROMPT + runtime_context,
            "input": request_input,
            "tools": TOOL_SCHEMAS,
            "tool_choice": self._initial_tool_choice(user_text),
        }
        if request_user is not None:
            create_kwargs["user"] = request_user

        response = self.provider.create_response(**create_kwargs)

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

            followup_kwargs = {
                "instructions": SYSTEM_PROMPT + runtime_context,
                "previous_response_id": response.id,
                "input": outputs,
                "tools": TOOL_SCHEMAS,
                "tool_choice": "auto",
            }
            if request_user is not None:
                followup_kwargs["user"] = request_user

            response = self.provider.create_response(**followup_kwargs)

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
