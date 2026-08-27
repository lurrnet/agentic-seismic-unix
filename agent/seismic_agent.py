from __future__ import annotations

import json
from typing import Any

from .prompts import SYSTEM_PROMPT
from .toolkit import TOOL_SCHEMAS, AgentToolkit
from .provider_factory import create_provider
from .providers.base import AgentProvider, AgentConfigurationError
from .proposal_fallback import normalize_processing_text, parse_proposal_from_text
from .reflection import extract_json_object, ReflectionParseError


class SeismicAgent:
    def __init__(self, provider: AgentProvider | None = None):
        self.provider = provider or create_provider()

    @staticmethod
    def _route_read_tool(user_text: str) -> tuple[str, dict[str, Any]] | None:
        text = normalize_processing_text(user_text)
        if any(token in text for token in ('review the filter', 'filter result', 'filtering result', 'did the filter', 'compare datasets', 'compare the result')):
            return 'compare_datasets', {}
        if any(token in text for token in ('gather', 'fold', 'prestack', 'nmo', 'velocity analysis')):
            return 'inspect_gathers', {'key': 'cdp', 'max_traces': 5000}
        if any(token in text for token in (
            'geometry', 'acquisition geometry', 'source coordinate', 'receiver coordinate',
            'set header', 'change header', 'rewrite header', 'sort dataset', 'sort traces',
            'sort by', 'sort on', 'order by', 'reorder', 'stack', 'stacking',
        )):
            return 'inspect_geometry', {'max_traces': 2000}
        if any(token in text for token in (
            'header', 'offset', 'cdp', 'fldr', 'tracf', 'select traces', 'keep offsets',
            'keep cdps', 'trace selection', 'subset traces', 'suwind', 'mute', 'xmute', 'tmute',
        )):
            return 'inspect_headers', {
                'keys': ['fldr', 'tracf', 'cdp', 'offset', 'sx', 'gx'],
                'max_traces': 1000,
            }
        if any(token in text for token in ('decon', 'deconvolution', 'predictive decon', 'pef', 'multiple suppression')):
            return 'inspect_frequency', {'max_traces': 200}
        if any(token in text for token in ('resample', 'change sample interval', 'change sampling', 'sample interval', 'sample rate', 'downsample', 'upsample')):
            return 'inspect_frequency', {'max_traces': 200}
        if any(token in text for token in ('amplitude', 'rms', 'dynamic range', 'gain', 'agc', 'clipping')):
            return 'inspect_amplitude', {'max_traces': 200}
        if any(token in text for token in ('frequency', 'spectrum', 'spectral', 'bandpass', 'filter recommendation', 'recommend a filter', 'recommend filter')):
            return 'inspect_frequency', {'max_traces': 200}
        if any(token in text for token in ('inspect', 'dataset', 'data set', 'what do you see', 'tell me what you see', 'sampling', 'trace count', 'surange')):
            return 'inspect_dataset', {}
        return None

    @staticmethod
    def _proposal_action(user_text: str) -> str | None:
        text = normalize_processing_text(user_text)
        if any(token in text for token in ('recommend a reasonable bandpass', 'recommend a bandpass', 'recommend bandpass', 'recommend a filter', 'recommend filter', 'filter recommendation', 'suggest a bandpass', 'suggest a filter', 'what filter', 'which filter', 'apply bandpass', 'run bandpass')):
            return 'apply_bandpass_filter'
        if any(token in text for token in ('apply agc', 'run agc', 'recommend agc', 'suggest agc')):
            return 'apply_agc'
        if any(token in text for token in ('apply gain', 'run gain', 'recommend gain', 'suggest gain', 'time gain', 'power gain')):
            return 'apply_gain'
        if any(token in text for token in ('select traces', 'trace selection', 'subset traces', 'window traces', 'keep offsets', 'keep cdps', 'apply suwind', 'run suwind')):
            return 'select_traces'
        if any(token in text for token in ('set header', 'change header', 'rewrite header', 'set cdp', 'set fldr', 'set offset', 'set sx', 'set sy', 'set gx', 'set gy')):
            return 'set_header_constant'
        if any(token in text for token in ('sort dataset', 'sort traces', 'sort by', 'sort on', 'cdp sort', 'offset sort', 'order by', 'reorder', 'recommend sort', 'recommend sorting')):
            return 'sort_dataset'
        if any(token in text for token in ('resample', 'change sample interval', 'change sampling', 'sample interval', 'sample rate', 'downsample', 'upsample')):
            return 'resample_dataset'
        if any(token in text for token in ('apply mute', 'run mute', 'recommend mute', 'suggest mute', 'top mute', 'bottom mute', 'xmute', 'tmute')):
            return 'apply_mute'
        if any(token in text for token in ('stack traces', 'stack dataset', 'stack by', 'cdp stack', 'fldr stack', 'ep stack', 'run stack', 'apply stack', 'recommend stack', 'recommend stacking')):
            return 'stack_traces'
        if any(token in text for token in ('apply decon', 'run decon', 'predictive decon', 'apply pef', 'run pef', 'recommend decon', 'suggest decon')):
            return 'apply_predictive_decon'
        if any(token in text for token in ('apply nmo', 'run nmo', 'recommend nmo', 'suggest nmo')):
            return 'apply_nmo'
        return None

    @staticmethod
    def _extract_application_proposal(text: str) -> dict[str, Any] | None:
        start_marker = '<SEISMIC_PROPOSAL>'
        end_marker = '</SEISMIC_PROPOSAL>'
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
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _strip_application_proposal(text: str) -> str:
        start_marker = '<SEISMIC_PROPOSAL>'
        end_marker = '</SEISMIC_PROPOSAL>'
        start = text.find(start_marker)
        if start < 0:
            return text.strip()
        end = text.find(end_marker, start + len(start_marker))
        if end < 0:
            return text.strip()
        return (text[:start] + text[end + len(end_marker):]).strip()

    @staticmethod
    def _proposal_instructions(action: str) -> str:
        formats = {
            'apply_bandpass_filter': '{"action":"apply_bandpass_filter","parameters":{"f1":number,"f2":number,"f3":number,"f4":number},"reason":"short evidence-based reason"}',
            'apply_gain': '{"action":"apply_gain","parameters":{"scale":number,"tpow":number,"gpow":number,"qclip":number},"reason":"short evidence-based reason"}',
            'apply_agc': '{"action":"apply_agc","parameters":{"wagc":number},"reason":"short evidence-based reason"}',
            'select_traces': '{"action":"select_traces","parameters":{"key":"header","min":number,"max":number},"reason":"short evidence-based reason"}',
            'set_header_constant': '{"action":"set_header_constant","parameters":{"key":"header","value":integer},"reason":"short evidence-based reason"}',
            'sort_dataset': '{"action":"sort_dataset","parameters":{"key":"header"},"reason":"short evidence-based reason"}',
            'resample_dataset': '{"action":"resample_dataset","parameters":{"dt":number},"reason":"short evidence-based reason"}',
            'apply_mute': '{"action":"apply_mute","parameters":{"key":"offset","xmute":[number,number],"tmute":[number,number],"mode":0,"ntaper":integer},"reason":"short evidence-based reason"}',
            'stack_traces': '{"action":"stack_traces","parameters":{"key":"cdp","normpow":number},"reason":"short evidence-based reason"}',
            'apply_predictive_decon': '{"action":"apply_predictive_decon","parameters":{"minlag":number,"maxlag":number,"pnoise":number},"reason":"short evidence-based reason"}',
            'apply_nmo': '{"action":"apply_nmo","parameters":{"tnmo":[number,number],"vnmo":[number,number],"smute":number,"lmute":integer,"sscale":1},"reason":"short evidence-based reason"}',
        }
        constraints = {
            'apply_bandpass_filter': 'Frequencies are Hz and must satisfy 0 <= f1 < f2 < f3 < f4 < Nyquist.',
            'apply_gain': 'Use scale for scalar amplitude multiplication; tpow/gpow are time/power gain controls and qclip is optional clipping.',
            'apply_agc': 'wagc is seconds and must be 0.01 to 10 seconds.',
            'select_traces': 'Use one inspected SU header key and require min <= max.',
            'set_header_constant': 'Only use a whitelisted header key. Header rewriting is high risk and always requires UI approval.',
            'sort_dataset': 'Use one whitelisted SU header key supported by the application.',
            'resample_dataset': 'dt is seconds. Use frequency/Nyquist evidence and avoid aliasing useful signal.',
            'apply_mute': 'Use 2-32 strictly increasing xmute points and the same number of tmute values in seconds. mode=0 mutes above; mode=1 mutes below.',
            'stack_traces': 'Only propose stack by cdp, fldr, or ep. The application rejects stacking unless the current dataset is the direct output of sorting by that same key.',
            'apply_predictive_decon': 'minlag and maxlag are seconds, must lie inside the trace duration, and minlag <= maxlag. pnoise is 0 to 1.',
            'apply_nmo': 'tnmo is seconds and strictly increasing; vnmo contains positive RMS velocities with equal length. The application requires populated offset headers. This v0.9 tool supports one time-only velocity function, not lateral CDP-dependent velocity functions.',
        }
        return (
            '\n\nOpenClaw compatibility mode is active. The application owns processing execution. '
            'Do not claim the processing tool is unavailable and do not claim processing ran. '
            'If the supplied evidence supports the requested processing proposal, include exactly one machine-readable envelope at the END of the answer:\n'
            '<SEISMIC_PROPOSAL>\n' + formats[action] + '\n</SEISMIC_PROPOSAL>\n' + constraints[action] +
            ' The application validates the proposal. Header rewriting always requires UI approval; other processing proposals remain pending unless the application has separate explicit user authorization. If evidence is insufficient, do not emit an envelope.'
        )

    @staticmethod
    def _create_pending_from_proposal(toolkit: AgentToolkit, proposal: dict[str, Any]) -> dict[str, Any]:
        action = proposal.get('action')
        params = proposal.get('parameters')
        if not isinstance(params, dict):
            params = proposal
        reason = proposal.get('reason') or 'Agent processing recommendation.'
        if action == 'apply_bandpass_filter': return toolkit.propose_bandpass({'f1': params.get('f1'), 'f2': params.get('f2'), 'f3': params.get('f3'), 'f4': params.get('f4'), 'reason': reason})
        if action == 'apply_gain': return toolkit.propose_gain({'scale': params.get('scale', 1.0), 'tpow': params.get('tpow', 0.0), 'gpow': params.get('gpow', 1.0), 'qclip': params.get('qclip', 1.0), 'reason': reason})
        if action == 'apply_agc': return toolkit.propose_agc({'wagc': params.get('wagc'), 'reason': reason})
        if action == 'select_traces': return toolkit.propose_trace_selection({'key': params.get('key'), 'min': params.get('min'), 'max': params.get('max'), 'reason': reason})
        if action == 'set_header_constant': return toolkit.propose_header_constant({'key': params.get('key'), 'value': params.get('value'), 'reason': reason})
        if action == 'sort_dataset': return toolkit.propose_sort({'key': params.get('key'), 'reason': reason})
        if action == 'resample_dataset': return toolkit.propose_resample({'dt': params.get('dt'), 'reason': reason})
        if action == 'apply_mute': return toolkit.propose_mute({'key': params.get('key'), 'xmute': params.get('xmute'), 'tmute': params.get('tmute'), 'mode': params.get('mode'), 'ntaper': params.get('ntaper', 0), 'reason': reason})
        if action == 'stack_traces': return toolkit.propose_stack({'key': params.get('key'), 'normpow': params.get('normpow', 1.0), 'reason': reason})
        if action == 'apply_predictive_decon': return toolkit.propose_predictive_decon({'minlag': params.get('minlag'), 'maxlag': params.get('maxlag'), 'pnoise': params.get('pnoise', 0.001), 'reason': reason})
        if action == 'apply_nmo': return toolkit.propose_nmo({'tnmo': params.get('tnmo'), 'vnmo': params.get('vnmo'), 'smute': params.get('smute', 1.5), 'lmute': params.get('lmute', 25), 'sscale': params.get('sscale', 1), 'reason': reason})
        raise ValueError(f'Unsupported proposal action: {action}')

    @property
    def provider_info(self) -> dict[str, Any]:
        return self.provider.info()

    def _runtime_context(self, toolkit: AgentToolkit) -> str:
        project_id = getattr(getattr(toolkit, 'project', None), 'project_id', 'unknown')
        current_dataset = str(getattr(toolkit, 'current_path', 'unknown'))
        return (
            '\n\nRuntime context supplied by the seismic application:\n'
            f'- A seismic dataset IS currently loaded for project {project_id}.\n'
            f'- Current dataset: {current_dataset}.\n'
            '- Never ask the user to upload/load the dataset again when the application has provided evidence.\n'
            '- Treat application-provided inspection results as authoritative observations for this turn.\n'
            '- Do not claim that a processing operation was executed unless the application says it was executed.'
        )

    def _run_openclaw_application_routed(self, user_text: str, toolkit: AgentToolkit, *, max_tool_rounds: int) -> dict[str, Any]:
        request_user = f"seismic-project-{getattr(toolkit.project, 'project_id', 'default')}"
        runtime_context = self._runtime_context(toolkit)
        tool_trace: list[dict[str, Any]] = []
        routed = self._route_read_tool(user_text)
        evidence = None
        if routed is not None:
            routed_tool, routed_args = routed
            try:
                result = toolkit.call(routed_tool, routed_args)
            except Exception as exc:
                result = {'status': 'error', 'error': str(exc)}
            tool_trace.append({'tool': routed_tool, 'arguments': routed_args, 'result': result, 'routed_by': 'application'})
            evidence = {'tool': routed_tool, 'result': result}
        request_input = user_text if evidence is None else (
            f'User request:\n{user_text}\n\nThe seismic application already executed the appropriate read-only inspection tool. '
            'Use the following structured evidence to answer the user. Do not say you lack access to the dataset or tools.\n\n'
            f'APPLICATION_EVIDENCE:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}'
        )
        proposal_action = self._proposal_action(user_text)
        routed_instructions = SYSTEM_PROMPT + runtime_context
        if proposal_action is not None:
            routed_instructions += self._proposal_instructions(proposal_action)
        response = self.provider.create_response(instructions=routed_instructions, input=request_input, user=request_user)
        rounds = 0
        while rounds < max_tool_rounds:
            calls = [item for item in response.output if getattr(item, 'type', None) == 'function_call']
            if not calls:
                break
            rounds += 1
            outputs = []
            for call in calls:
                arguments = {}
                try:
                    arguments = json.loads(call.arguments or '{}')
                    result = toolkit.call(call.name, arguments)
                except Exception as exc:
                    result = {'status': 'error', 'error': str(exc)}
                tool_trace.append({'tool': call.name, 'arguments': arguments, 'result': result, 'routed_by': 'openclaw'})
                outputs.append({'type': 'function_call_output', 'call_id': call.call_id, 'output': json.dumps(result, ensure_ascii=False)})
            response = self.provider.create_response(instructions=SYSTEM_PROMPT + runtime_context, previous_response_id=response.id, input=outputs, tools=TOOL_SCHEMAS, tool_choice='auto', user=request_user)
        if rounds >= max_tool_rounds and any(getattr(item, 'type', None) == 'function_call' for item in response.output):
            raise RuntimeError('Agent exceeded the maximum tool-call rounds.')
        text = (response.output_text or '').strip() or 'The agent completed the turn but returned no final text.'
        proposal = self._extract_application_proposal(text) if proposal_action else None
        proposal_source = 'structured_envelope' if proposal is not None else None
        if proposal_action is not None and proposal is None:
            proposal = parse_proposal_from_text(proposal_action, text)
            if proposal is not None:
                proposal_source = proposal.get('parsed_from', 'text_fallback')
        if proposal is not None:
            clean_text = self._strip_application_proposal(text)
            try:
                if proposal.get('action') != proposal_action:
                    raise ValueError(f"Proposal action {proposal.get('action')} does not match requested {proposal_action}.")
                result = self._create_pending_from_proposal(toolkit, proposal)
                tool_trace.append({'tool': proposal_action, 'arguments': proposal.get('parameters', proposal), 'result': result, 'routed_by': 'application_proposal_bridge'})
                pending = toolkit.pending_action or {}
                display_name = pending.get('display_name', pending.get('tool', 'processing'))
                params = pending.get('parameters', {})
                policy = pending.get('approval_policy', 'always')
                text = (
                    f'The application parsed and validated the agent recommendation for **{display_name}** with parameters `{params}`. A pending proposal was created; no processing has executed yet.'
                    if proposal_source != 'structured_envelope'
                    else (clean_text + f'\n\nA validated **{display_name}** proposal was created with parameters `{params}`.').strip()
                )
                text += ' This operation requires approval in the UI before execution.' if policy == 'always' else ' It remains pending until you approve it or explicitly authorize that exact proposal.'
            except Exception as exc:
                text = (clean_text + '\n\nThe model supplied a processing recommendation, but the application rejected it during validation: ' + f'`{exc}`. No pending action was created.').strip()
                tool_trace.append({'tool': proposal_action or proposal.get('action'), 'arguments': proposal, 'result': {'status': 'validation_error', 'error': str(exc)}, 'routed_by': 'application_proposal_bridge'})
        return {'text': text, 'pending_action': toolkit.pending_action, 'tool_trace': tool_trace, 'provider': self.provider.name, 'model': self.provider.model, 'provider_info': self.provider.info()}

    def _run_native_function_calling(self, user_text: str, chat_history: list[dict[str, str]], toolkit: AgentToolkit, *, max_tool_rounds: int) -> dict[str, Any]:
        input_items = []
        for message in chat_history[-20:]:
            role = message.get('role')
            content = message.get('content', '')
            if role in {'user', 'assistant'} and content:
                input_items.append({'role': role, 'content': content})
        input_items.append({'role': 'user', 'content': user_text})
        runtime_context = self._runtime_context(toolkit)
        response = self.provider.create_response(instructions=SYSTEM_PROMPT + runtime_context, input=input_items, tools=TOOL_SCHEMAS, tool_choice='auto')
        tool_trace = []
        rounds = 0
        while rounds < max_tool_rounds:
            calls = [item for item in response.output if getattr(item, 'type', None) == 'function_call']
            if not calls:
                break
            rounds += 1
            outputs = []
            for call in calls:
                arguments = {}
                try:
                    arguments = json.loads(call.arguments or '{}')
                    result = toolkit.call(call.name, arguments)
                except Exception as exc:
                    result = {'status': 'error', 'error': str(exc)}
                tool_trace.append({'tool': call.name, 'arguments': arguments, 'result': result, 'routed_by': self.provider.name})
                outputs.append({'type': 'function_call_output', 'call_id': call.call_id, 'output': json.dumps(result, ensure_ascii=False)})
            response = self.provider.create_response(instructions=SYSTEM_PROMPT + runtime_context, previous_response_id=response.id, input=outputs, tools=TOOL_SCHEMAS, tool_choice='auto')
        if rounds >= max_tool_rounds and any(getattr(item, 'type', None) == 'function_call' for item in response.output):
            raise RuntimeError('Agent exceeded the maximum tool-call rounds.')
        text = (response.output_text or '').strip() or 'I completed the tool calls, but the model returned no final text.'
        return {'text': text, 'pending_action': toolkit.pending_action, 'tool_trace': tool_trace, 'provider': self.provider.name, 'model': self.provider.model, 'provider_info': self.provider.info()}

    def review_latest_filter(self, toolkit: AgentToolkit, *, max_traces: int = 200) -> dict[str, Any]:
        qc = toolkit.compare_datasets()
        if qc.get('status') != 'success':
            return {'status': 'not_available', 'text': qc.get('message', 'QC comparison is not available.'), 'decision': 'review_only', 'pending_action': None, 'qc': qc}
        try:
            after_frequency = toolkit.inspect_frequency({'max_traces': max_traces})
        except Exception as exc:
            after_frequency = {'status': 'error', 'error': str(exc)}
        runtime_context = self._runtime_context(toolkit)
        request_user = f"seismic-project-{getattr(toolkit.project, 'project_id', 'default')}"
        reflection_prompt = (
            'You are reviewing the result of an already executed Seismic Unix bandpass filter.\n'
            'The application, not the model, computed the evidence below.\n'
            'Decide whether the latest result should be ACCEPTED or whether a revised four-corner bandpass should be PROPOSED for human approval.\n\n'
            'Important constraints:\n- Do not claim to visually inspect plots; use only the supplied metrics.\n- Be conservative. If evidence is insufficient or ambiguous, choose ACCEPT.\n'
            '- If proposing an adjustment, require 0 <= f1 < f2 < f3 < f4 < Nyquist.\n- The adjustment does not execute automatically.\n'
            '- Return JSON only, with exactly this shape:\n'
            '{"decision":"accept|adjust","summary":"short user-facing summary","reason":"evidence-based reason","confidence":"low|medium|high","adjusted_filter":null_or_{"f1":number,"f2":number,"f3":number,"f4":number}}\n\n'
            f'QC_EVIDENCE:\n{json.dumps(qc, ensure_ascii=False, indent=2)}\n\nFILTERED_DATA_FREQUENCY_EVIDENCE:\n{json.dumps(after_frequency, ensure_ascii=False, indent=2)}'
        )
        kwargs = {'instructions': SYSTEM_PROMPT + runtime_context, 'input': reflection_prompt}
        if self.provider.name == 'openclaw':
            kwargs['user'] = request_user
        response = self.provider.create_response(**kwargs)
        raw_text = (response.output_text or '').strip()
        try:
            parsed = extract_json_object(raw_text)
        except ReflectionParseError as exc:
            return {'status': 'unstructured', 'text': raw_text or 'The agent returned no reflection text.', 'decision': 'review_only', 'reason': str(exc), 'confidence': 'low', 'pending_action': None, 'qc': qc, 'after_frequency': after_frequency, 'raw_response': raw_text}
        decision = str(parsed.get('decision', 'accept')).strip().lower()
        if decision not in {'accept', 'adjust'}:
            decision = 'accept'
        summary = str(parsed.get('summary') or 'QC review completed.').strip()
        reason = str(parsed.get('reason') or '').strip()
        confidence = str(parsed.get('confidence') or 'low').strip().lower()
        if confidence not in {'low', 'medium', 'high'}:
            confidence = 'low'
        pending_action = None
        validation_error = None
        if decision == 'adjust':
            adjusted = parsed.get('adjusted_filter')
            if isinstance(adjusted, dict):
                try:
                    toolkit.propose_bandpass({'f1': adjusted.get('f1'), 'f2': adjusted.get('f2'), 'f3': adjusted.get('f3'), 'f4': adjusted.get('f4'), 'reason': reason or 'QC reflection recommended an adjusted bandpass.'})
                    pending_action = toolkit.pending_action
                except Exception as exc:
                    validation_error = str(exc)
                    decision = 'accept'
            else:
                validation_error = 'Agent selected adjust but did not provide adjusted_filter.'
                decision = 'accept'
        text = summary
        if reason:
            text += f'\n\nReason: {reason}'
        text += f'\n\nReflection decision: **{decision.upper()}** · confidence: **{confidence}**.'
        if pending_action is not None:
            p = pending_action['parameters']
            text += f"\n\nSuggested follow-up filter: **{p['f1']:g} - {p['f2']:g} - {p['f3']:g} - {p['f4']:g} Hz**."
        if validation_error:
            text += f'\n\nNo new proposal was created: `{validation_error}`'
        return {'status': 'success', 'text': text, 'decision': decision, 'summary': summary, 'reason': reason, 'confidence': confidence, 'pending_action': pending_action, 'qc': qc, 'after_frequency': after_frequency, 'raw_response': raw_text, 'validation_error': validation_error, 'provider': self.provider.name, 'model': self.provider.model}

    def run_turn(self, user_text: str, chat_history: list[dict[str, str]], toolkit: AgentToolkit, *, max_tool_rounds: int = 8) -> dict[str, Any]:
        if self.provider.name == 'openclaw' and getattr(self.provider, 'tool_strategy', 'application_routed') == 'application_routed':
            return self._run_openclaw_application_routed(user_text, toolkit, max_tool_rounds=max_tool_rounds)
        return self._run_native_function_calling(user_text, chat_history, toolkit, max_tool_rounds=max_tool_rounds)
