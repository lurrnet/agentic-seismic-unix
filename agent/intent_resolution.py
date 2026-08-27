from __future__ import annotations

import json
from typing import Any

from .provider_factory import create_provider
from .providers.base import AgentProvider
from .reflection import extract_json_object, ReflectionParseError


APPROVE_PENDING = 'approve_pending_action'
REJECT_PENDING = 'reject_pending_action'
QUESTION_PENDING = 'question_about_pending_action'
MODIFY_PENDING = 'modify_pending_action'
NEW_REQUEST = 'new_request'
AMBIGUOUS = 'ambiguous'

_ALLOWED_INTENTS = {
    APPROVE_PENDING,
    REJECT_PENDING,
    QUESTION_PENDING,
    MODIFY_PENDING,
    NEW_REQUEST,
    AMBIGUOUS,
}


def fast_pending_intent(user_text: str) -> str | None:
    """Return only trivial zero-latency approvals/rejections.

    Natural-language variants intentionally do not belong here; they are handled
    by the semantic resolver so wording changes do not require regex growth.
    """
    text = user_text.strip().lower().strip(' .!')
    if text in {'yes', 'approve', 'approved', 'proceed'}:
        return APPROVE_PENDING
    if text in {'no', 'reject', 'rejected', 'cancel'}:
        return REJECT_PENDING
    return None


class PendingIntentResolver:
    def __init__(self, provider: AgentProvider | None = None):
        self.provider = provider or create_provider()

    @property
    def provider_info(self) -> dict[str, Any]:
        return self.provider.info()

    def resolve(
        self,
        user_text: str,
        pending_action: dict[str, Any],
        chat_history: list[dict[str, str]] | None = None,
        *,
        request_user: str | None = None,
    ) -> dict[str, Any]:
        history = []
        for message in (chat_history or [])[-10:]:
            role = message.get('role')
            content = str(message.get('content') or '').strip()
            if role in {'user', 'assistant'} and content:
                history.append({'role': role, 'content': content})

        payload = {
            'user_message': user_text,
            'pending_action': {
                'tool': pending_action.get('tool'),
                'display_name': pending_action.get('display_name'),
                'parameters': pending_action.get('parameters'),
                'reason': pending_action.get('reason'),
                'status': pending_action.get('status'),
                'approval_policy': pending_action.get('approval_policy'),
            },
            'recent_conversation': history,
        }
        instructions = (
            'You are the semantic authorization classifier inside a seismic processing application. '
            'A concrete validated processing proposal already exists as pending_action. Determine what '
            'the latest user message means with respect to THAT exact pending proposal. You never execute '
            'tools and never invent or change parameters. Return JSON only, with exactly these keys: '
            '{"intent":"approve_pending_action|reject_pending_action|question_about_pending_action|'
            'modify_pending_action|new_request|ambiguous","confidence":0.0,"references_pending":true,'
            '"reason":"short explanation"}. '
            'Classify approve_pending_action when the user clearly directs the application to carry out '
            'the existing proposal unchanged. Natural examples include: "go ahead with that", '
            '"use your recommendation", "sounds good, do it", "apply such an AGC", '
            '"apply the AGC using your suggested window", "run the filter you suggested", and '
            '"use those recommended parameters". These are execution authorizations, not new proposals. '
            'Classify reject_pending_action for refusal/cancellation. Classify question_about_pending_action '
            'when the user asks about the proposal without authorizing it. Classify modify_pending_action '
            'when the user requests any parameter or operation change. Classify new_request only when the '
            'message starts a genuinely different task that does not refer to the pending proposal. '
            'Use ambiguous only when meaning is genuinely unclear. Set references_pending=true whenever '
            'phrases such as your suggested, your recommendation, that, it, those parameters, such an AGC, '
            'or equivalent language refer back to pending_action. Be conservative about authorization, '
            'but do not treat an explicit imperative to apply/run/execute the existing recommendation as '
            'a request for another confirmation.'
        )
        kwargs: dict[str, Any] = {
            'instructions': instructions,
            'input': json.dumps(payload, ensure_ascii=False),
        }
        if self.provider.name == 'openclaw' and request_user:
            kwargs['user'] = request_user
        response = self.provider.create_response(**kwargs)
        raw = (response.output_text or '').strip()
        try:
            parsed = extract_json_object(raw)
        except ReflectionParseError as exc:
            return {
                'intent': AMBIGUOUS,
                'confidence': 0.0,
                'references_pending': False,
                'reason': f'Intent resolver returned unstructured output: {exc}',
                'raw_response': raw,
            }

        intent = str(parsed.get('intent') or AMBIGUOUS).strip()
        if intent not in _ALLOWED_INTENTS:
            intent = AMBIGUOUS
        try:
            confidence = float(parsed.get('confidence', 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        references_pending = bool(parsed.get('references_pending', False))
        reason = str(parsed.get('reason') or '').strip()
        return {
            'intent': intent,
            'confidence': confidence,
            'references_pending': references_pending,
            'reason': reason,
            'raw_response': raw,
            'provider': self.provider.name,
            'model': self.provider.model,
        }


def semantic_authorization(intent_result: dict[str, Any], *, threshold: float = 0.70) -> str | None:
    """Convert semantic classification into an application authorization decision.

    The LLM only classifies meaning. The application still owns the threshold,
    pending-state checks, registry validation, and execution.
    """
    if not intent_result.get('references_pending'):
        return None
    try:
        confidence = float(intent_result.get('confidence', 0.0))
    except (TypeError, ValueError):
        return None
    if confidence < threshold:
        return None
    intent = intent_result.get('intent')
    if intent == APPROVE_PENDING:
        return APPROVE_PENDING
    if intent == REJECT_PENDING:
        return REJECT_PENDING
    return None
