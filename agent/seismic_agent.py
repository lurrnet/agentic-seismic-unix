from __future__ import annotations

import json
import re
from typing import Any

from .prompts import SYSTEM_PROMPT
from .toolkit import TOOL_SCHEMAS, AgentToolkit
from .provider_factory import create_provider
from .providers.base import AgentProvider, AgentConfigurationError
from .reflection import extract_json_object, ReflectionParseError


class SeismicAgent:
    def __init__(self, provider: AgentProvider | None = None):
        self.provider = provider or create_provider()

    @staticmethod
    def _route_read_tool(user_text: str) -> str | None:
        text = user_text.lower()

        if any(token in text for token in (
            "review the filter", "filter result", "filtering result",
            "did the filter", "compare datasets", "compare the result",
        )):
            return "compare_datasets"

        if any(token in text for token in (
            "frequency", "spectrum", "spectral", "bandpass",
            "filter recommendation", "recommend a filter", "recommend filter",
        )):
            return "inspect_frequency"

        if any(token in text for token in (
            "inspect", "dataset", "data set", "what do you see",
            "tell me what you see", "sampling", "trace count", "surange",
        )):
            return "inspect_dataset"

        return None

    @staticmethod
    def _wants_bandpass_proposal(user_text: str) -> bool:
        text = user_text.lower()
        return any(token in text for token in (
            "recommend a reasonable bandpass",
            "recommend a bandpass",
            "recommend bandpass",
            "recommend a filter",
            "recommend filter",
            "filter recommendation",
            "suggest a bandpass",
            "suggest a filter",
            "what filter",
            "which filter",
        ))

    @staticmethod
    def _extract_application_proposal(text: str) -> dict[str, Any] | None:
        """Extract the application-routed proposal envelope from model text.

        OpenClaw compatibility mode intentionally does not depend on native
        client-side function calling. The model may therefore return one JSON
        object wrapped between stable markers; the application parses and
        validates it before creating a pending action.
        """
        start_marker = "<SEISMIC_PROPOSAL>"
        end_marker = "</SEISMIC_PROPOSAL>"
        start = text.find(start_marker)
        if start < 0:
            return None
        end = text.find(end_marker, start + len(start_marker))
        if end < 0:
            return None
        raw = text[start + len(start_marker):end].strip()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        return obj

    @staticmethod
    def _extract_bandpass_from_text(text: str) -> dict[str, Any] | None:
        """Best-effort deterministic fallback for OpenClaw prose recommendations.

        Accept common forms such as:
          8-15-50-60 Hz
          8 / 15 / 50 / 60 Hz
          f1=8, f2=15, f3=50, f4=60

        The returned values are still passed through the normal validator before
        a pending processing action can be created.
        """
        # Prefer explicit f1/f2/f3/f4 labels when present.
        labels = re.search(
            r"f1\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+"
            r"f2\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+"
            r"f3\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*[,; ]+"
            r"f4\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
            text,
            flags=re.IGNORECASE,
        )
        if labels:
            vals = [float(x) for x in labels.groups()]
            return {
                "action": "apply_bandpass_filter",
                "f1": vals[0], "f2": vals[1], "f3": vals[2], "f4": vals[3],
                "reason": "Bandpass recommendation parsed from the agent response.",
                "parsed_from": "labeled_text",
            }

        # Then accept a compact four-corner sequence followed by Hz.
        seq = re.search(
            r"(?<![0-9.])"
            r"([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*[-–—/]\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*Hz\b",
            text,
            flags=re.IGNORECASE,
        )
        if seq:
            vals = [float(x) for x in seq.groups()]
            return {
                "action": "apply_bandpass_filter",
                "f1": vals[0], "f2": vals[1], "f3": vals[2], "f4": vals[3],
                "reason": "Bandpass recommendation parsed from the agent response.",
                "parsed_from": "frequency_sequence",
            }

        return None

    @staticmethod
    def _strip_application_proposal(text: str) -> str:
        start_marker = "<SEISMIC_PROPOSAL>"
        end_marker = "</SEISMIC_PROPOSAL>"
        start = text.find(start_marker)
        if start < 0:
            return text.strip()
        end = text.find(end_marker, start + len(start_marker))
        if end < 0:
            return text.strip()
        return (text[:start] + text[end + len(end_marker):]).strip()

    @property
    def provider_info(self) -> dict[str, Any]:
        return self.provider.info()

    def _runtime_context(self, toolkit: AgentToolkit) -> str:
        project_id = getattr(getattr(toolkit, "project", None), "project_id", "unknown")
        current_dataset = str(getattr(toolkit, "current_path", "unknown"))
        return (
            "\n\nRuntime context supplied by the seismic application:\n"
            f"- A seismic dataset IS currently loaded for project {project_id}.\n"
            f"- Current dataset: {current_dataset}.\n"
            "- Never ask the user to upload/load the dataset again when the application has provided evidence.\n"
            "- Treat application-provided inspection results as authoritative observations for this turn.\n"
            "- Do not claim that a processing operation was executed unless the application says it was executed."
        )

    def _run_openclaw_application_routed(
        self,
        user_text: str,
        toolkit: AgentToolkit,
        *,
        max_tool_rounds: int,
    ) -> dict[str, Any]:
        """OpenClaw compatibility mode.

        Read-only evidence gathering is routed deterministically by the seismic
        application. OpenClaw then interprets the evidence. We still expose the
        client-side tools with tool_choice=auto so capable OpenClaw backends may
        make additional calls, but correctness no longer depends on a forced
        client-tool call.
        """
        request_user = f"seismic-project-{getattr(toolkit.project, 'project_id', 'default')}"
        runtime_context = self._runtime_context(toolkit)
        tool_trace: list[dict[str, Any]] = []

        routed_tool = self._route_read_tool(user_text)
        evidence = None
        if routed_tool is not None:
            try:
                result = toolkit.call(routed_tool, {})
            except Exception as exc:
                result = {"status": "error", "error": str(exc)}
            tool_trace.append({
                "tool": routed_tool,
                "arguments": {},
                "result": result,
                "routed_by": "application",
            })
            evidence = {
                "tool": routed_tool,
                "result": result,
            }

        if evidence is None:
            request_input = user_text
        else:
            request_input = (
                f"User request:\n{user_text}\n\n"
                "The seismic application already executed the appropriate read-only inspection tool. "
                "Use the following structured evidence to answer the user. Do not say you lack access "
                "to the dataset or tools.\n\n"
                f"APPLICATION_EVIDENCE:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}"
            )

        wants_proposal = self._wants_bandpass_proposal(user_text)
        routed_instructions = SYSTEM_PROMPT + runtime_context
        if wants_proposal:
            routed_instructions += (
                "\n\nOpenClaw compatibility mode is active. Do NOT claim that the bandpass-action "
                "tool is unavailable and do NOT depend on a native function call to create the proposal. "
                "If the supplied frequency evidence supports a bandpass recommendation, include exactly one "
                "machine-readable proposal envelope at the END of your answer using this exact format:\n"
                "<SEISMIC_PROPOSAL>\n"
                '{"action":"apply_bandpass_filter","f1":number,"f2":number,"f3":number,"f4":number,'
                '"reason":"short evidence-based reason"}\n'
                "</SEISMIC_PROPOSAL>\n"
                "The frequencies are in Hz and must satisfy 0 <= f1 < f2 < f3 < f4 < Nyquist. "
                "The application will validate the proposal and require human approval before execution. "
                "If evidence is insufficient for a defensible filter, do not emit the proposal envelope."
            )

        # In application-routed mode the app owns evidence gathering and proposal
        # creation. Passing no client tools avoids OpenClaw trying (and failing)
        # to turn a valid recommendation into a native function call.
        response = self.provider.create_response(
            instructions=routed_instructions,
            input=request_input,
            user=request_user,
        )

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
                    "routed_by": "openclaw",
                })
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                })

            response = self.provider.create_response(
                instructions=SYSTEM_PROMPT + runtime_context,
                previous_response_id=response.id,
                input=outputs,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                user=request_user,
            )

        if rounds >= max_tool_rounds and any(
            getattr(item, "type", None) == "function_call" for item in response.output
        ):
            raise RuntimeError("Agent exceeded the maximum tool-call rounds.")

        text = (response.output_text or "").strip()
        if not text:
            text = "The agent completed the turn but returned no final text."

        # OpenClaw application-routed proposal bridge. Convert the model's
        # structured recommendation into the SAME validator-backed pending
        # action used by native function-calling providers.
        proposal = self._extract_application_proposal(text) if wants_proposal else None
        proposal_source = "structured_envelope" if proposal is not None else None
        if wants_proposal and proposal is None:
            proposal = self._extract_bandpass_from_text(text)
            if proposal is not None:
                proposal_source = proposal.get("parsed_from", "text_fallback")

        if proposal is not None:
            try:
                if proposal.get("action") != "apply_bandpass_filter":
                    raise ValueError("Unsupported proposal action.")
                result = toolkit.propose_bandpass({
                    "f1": proposal.get("f1"),
                    "f2": proposal.get("f2"),
                    "f3": proposal.get("f3"),
                    "f4": proposal.get("f4"),
                    "reason": proposal.get("reason") or "OpenClaw recommended a bandpass from application evidence.",
                })
                tool_trace.append({
                    "tool": "apply_bandpass_filter",
                    "arguments": {k: proposal.get(k) for k in ("f1", "f2", "f3", "f4", "reason")},
                    "result": result,
                    "routed_by": "application_proposal_bridge",
                })
                clean_text = self._strip_application_proposal(text)
                p = toolkit.pending_action["parameters"]
                # If the fallback prose parser was needed, replace potentially
                # contradictory model language (for example, claims that the
                # action tool is unavailable) with an application-authored status.
                if proposal_source != "structured_envelope":
                    text = (
                        f"The agent recommended **{p['f1']:g} / {p['f2']:g} / "
                        f"{p['f3']:g} / {p['f4']:g} Hz**. "
                        "The application parsed and validated those four corners and created "
                        "a pending filter proposal. No processing has been executed yet. "
                        "Approve it in the UI to run sufilter."
                    )
                else:
                    text = (clean_text +
                            f"\n\nA validated pending filter proposal was created: "
                            f"**{p['f1']:g} / {p['f2']:g} / {p['f3']:g} / {p['f4']:g} Hz**. "
                            "It will not run until you approve it in the UI.").strip()
            except Exception as exc:
                clean_text = self._strip_application_proposal(text)
                text = (clean_text +
                        "\n\nThe model supplied a filter recommendation, but the application rejected it "
                        f"during validation: `{exc}`. No pending processing action was created.").strip()
                tool_trace.append({
                    "tool": "apply_bandpass_filter",
                    "arguments": proposal,
                    "result": {"status": "validation_error", "error": str(exc)},
                    "routed_by": "application_proposal_bridge",
                })

        return {
            "text": text,
            "pending_action": toolkit.pending_action,
            "tool_trace": tool_trace,
            "provider": self.provider.name,
            "model": self.provider.model,
            "provider_info": self.provider.info(),
        }

    def _run_native_function_calling(
        self,
        user_text: str,
        chat_history: list[dict[str, str]],
        toolkit: AgentToolkit,
        *,
        max_tool_rounds: int,
    ) -> dict[str, Any]:
        input_items: list[dict[str, Any]] = []
        for message in chat_history[-20:]:
            role = message.get("role")
            content = message.get("content", "")
            if role in {"user", "assistant"} and content:
                input_items.append({"role": role, "content": content})
        input_items.append({"role": "user", "content": user_text})

        runtime_context = self._runtime_context(toolkit)
        response = self.provider.create_response(
            instructions=SYSTEM_PROMPT + runtime_context,
            input=input_items,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
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
                    "routed_by": self.provider.name,
                })
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                })

            response = self.provider.create_response(
                instructions=SYSTEM_PROMPT + runtime_context,
                previous_response_id=response.id,
                input=outputs,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
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


    def review_latest_filter(
        self,
        toolkit: AgentToolkit,
        *,
        max_traces: int = 200,
    ) -> dict[str, Any]:
        """Run deterministic QC, then ask the configured agent provider to reflect.

        This method never executes another processing step. If the model recommends
        an adjustment, it is converted into the same approval-gated pending action
        used elsewhere in the application.
        """
        qc = toolkit.compare_datasets()
        if qc.get("status") != "success":
            return {
                "status": "not_available",
                "text": qc.get("message", "QC comparison is not available."),
                "decision": "review_only",
                "pending_action": None,
                "qc": qc,
            }

        # Inspect the current (filtered) dataset so the reflection sees both the
        # before/after QC metrics and the residual frequency distribution.
        try:
            after_frequency = toolkit.inspect_frequency({"max_traces": max_traces})
        except Exception as exc:
            after_frequency = {"status": "error", "error": str(exc)}

        runtime_context = self._runtime_context(toolkit)
        request_user = f"seismic-project-{getattr(toolkit.project, 'project_id', 'default')}"

        reflection_prompt = (
            "You are reviewing the result of an already executed Seismic Unix bandpass filter.\n"
            "The application, not the model, computed the evidence below.\n"
            "Decide whether the latest result should be ACCEPTED or whether a revised four-corner "
            "bandpass should be PROPOSED for human approval.\n\n"
            "Important constraints:\n"
            "- Do not claim to visually inspect plots; use only the supplied metrics.\n"
            "- Be conservative. A filter can reduce out-of-band energy while also damaging useful signal.\n"
            "- If evidence is insufficient or ambiguous, choose ACCEPT rather than inventing an adjustment.\n"
            "- If proposing an adjustment, require 0 <= f1 < f2 < f3 < f4 < Nyquist.\n"
            "- The adjustment will NOT execute automatically; it only becomes a pending user-approved proposal.\n"
            "- Return JSON only, with exactly this shape:\n"
            '{"decision":"accept|adjust","summary":"short user-facing summary",'
            '"reason":"evidence-based reason","confidence":"low|medium|high",'
            '"adjusted_filter":null_or_{"f1":number,"f2":number,"f3":number,"f4":number}}\n\n'
            f"QC_EVIDENCE:\n{json.dumps(qc, ensure_ascii=False, indent=2)}\n\n"
            f"FILTERED_DATA_FREQUENCY_EVIDENCE:\n{json.dumps(after_frequency, ensure_ascii=False, indent=2)}"
        )

        kwargs: dict[str, Any] = {
            "instructions": SYSTEM_PROMPT + runtime_context,
            "input": reflection_prompt,
        }
        if self.provider.name == "openclaw":
            kwargs["user"] = request_user

        response = self.provider.create_response(**kwargs)
        raw_text = (response.output_text or "").strip()

        try:
            parsed = extract_json_object(raw_text)
        except ReflectionParseError as exc:
            return {
                "status": "unstructured",
                "text": raw_text or "The agent returned no reflection text.",
                "decision": "review_only",
                "reason": str(exc),
                "confidence": "low",
                "pending_action": None,
                "qc": qc,
                "after_frequency": after_frequency,
                "raw_response": raw_text,
            }

        decision = str(parsed.get("decision", "accept")).strip().lower()
        if decision not in {"accept", "adjust"}:
            decision = "accept"

        summary = str(parsed.get("summary") or "QC review completed.").strip()
        reason = str(parsed.get("reason") or "").strip()
        confidence = str(parsed.get("confidence") or "low").strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"

        pending_action = None
        validation_error = None
        if decision == "adjust":
            adjusted = parsed.get("adjusted_filter")
            if isinstance(adjusted, dict):
                proposal_args = {
                    "f1": adjusted.get("f1"),
                    "f2": adjusted.get("f2"),
                    "f3": adjusted.get("f3"),
                    "f4": adjusted.get("f4"),
                    "reason": reason or "QC reflection recommended an adjusted bandpass.",
                }
                try:
                    proposal_result = toolkit.propose_bandpass(proposal_args)
                    pending_action = toolkit.pending_action
                except Exception as exc:
                    validation_error = str(exc)
                    decision = "accept"
                    pending_action = None
            else:
                validation_error = "Agent selected adjust but did not provide adjusted_filter."
                decision = "accept"

        text = summary
        if reason:
            text += f"\n\nReason: {reason}"
        text += f"\n\nReflection decision: **{decision.upper()}** · confidence: **{confidence}**."
        if pending_action is not None:
            p = pending_action["parameters"]
            text += (
                "\n\nSuggested follow-up filter (requires approval): "
                f"**{p['f1']:g} - {p['f2']:g} - {p['f3']:g} - {p['f4']:g} Hz**."
            )
        if validation_error:
            text += (
                "\n\nThe proposed adjustment failed application validation, so no new processing "
                f"proposal was created: `{validation_error}`"
            )

        return {
            "status": "success",
            "text": text,
            "decision": decision,
            "summary": summary,
            "reason": reason,
            "confidence": confidence,
            "pending_action": pending_action,
            "qc": qc,
            "after_frequency": after_frequency,
            "raw_response": raw_text,
            "validation_error": validation_error,
            "provider": self.provider.name,
            "model": self.provider.model,
        }

    def run_turn(
        self,
        user_text: str,
        chat_history: list[dict[str, str]],
        toolkit: AgentToolkit,
        *,
        max_tool_rounds: int = 8,
    ) -> dict[str, Any]:
        if self.provider.name == "openclaw" and getattr(
            self.provider, "tool_strategy", "application_routed"
        ) == "application_routed":
            return self._run_openclaw_application_routed(
                user_text,
                toolkit,
                max_tool_rounds=max_tool_rounds,
            )

        return self._run_native_function_calling(
            user_text,
            chat_history,
            toolkit,
            max_tool_rounds=max_tool_rounds,
        )
