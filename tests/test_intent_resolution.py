import json
import unittest

from agent.intent_resolution import (
    APPROVE_PENDING,
    REJECT_PENDING,
    PendingIntentResolver,
    fast_pending_intent,
    semantic_authorization,
)


class _FakeResponse:
    def __init__(self, payload):
        self.output_text = json.dumps(payload)


class _FakeProvider:
    name = 'fake'
    model = 'fake-intent-model'

    def __init__(self, payload):
        self.payload = payload
        self.last_kwargs = None

    def create_response(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self.payload)

    def info(self):
        return {'provider': self.name, 'model': self.model}


class PendingIntentResolutionTests(unittest.TestCase):
    def setUp(self):
        self.pending = {
            'tool': 'suagc',
            'display_name': 'Apply AGC',
            'parameters': {'wagc': 0.5},
            'reason': 'Amplitude inspection suggests balancing is useful.',
            'status': 'pending_approval',
            'approval_policy': 'explicit_or_approval',
        }

    def test_fast_path_is_intentionally_small(self):
        self.assertEqual(fast_pending_intent('yes'), APPROVE_PENDING)
        self.assertEqual(fast_pending_intent('cancel'), REJECT_PENDING)
        self.assertIsNone(fast_pending_intent('go ahead and apply such an AGC'))
        self.assertIsNone(fast_pending_intent('sounds good, do it'))
        self.assertIsNone(fast_pending_intent('Apply the AGC using your suggested window'))

    def test_semantic_approval_authorizes_high_confidence_reference(self):
        provider = _FakeProvider({
            'intent': APPROVE_PENDING,
            'confidence': 0.97,
            'references_pending': True,
            'reason': 'User clearly authorizes the existing AGC proposal.',
        })
        resolver = PendingIntentResolver(provider=provider)
        result = resolver.resolve(
            'go ahead and apply such an AGC',
            self.pending,
            [{'role': 'assistant', 'content': 'I recommend a 0.5 s AGC window.'}],
        )
        self.assertEqual(result['intent'], APPROVE_PENDING)
        self.assertEqual(semantic_authorization(result), APPROVE_PENDING)
        self.assertIn('pending_action', provider.last_kwargs['input'])

    def test_suggested_window_wording_authorizes_pending_agc(self):
        provider = _FakeProvider({
            'intent': APPROVE_PENDING,
            'confidence': 0.82,
            'references_pending': True,
            'reason': 'The imperative explicitly applies the AGC with the previously suggested window.',
        })
        resolver = PendingIntentResolver(provider=provider)
        result = resolver.resolve(
            'Apply the AGC using your suggested window',
            self.pending,
            [{'role': 'assistant', 'content': 'I suggest wagc=0.5 s.'}],
        )
        self.assertEqual(result['intent'], APPROVE_PENDING)
        self.assertTrue(result['references_pending'])
        self.assertEqual(semantic_authorization(result), APPROVE_PENDING)

    def test_semantic_rejection_authorizes_high_confidence_reference(self):
        provider = _FakeProvider({
            'intent': REJECT_PENDING,
            'confidence': 0.96,
            'references_pending': True,
            'reason': 'User rejects the existing proposal.',
        })
        resolver = PendingIntentResolver(provider=provider)
        result = resolver.resolve('no, do not use that recommendation', self.pending)
        self.assertEqual(semantic_authorization(result), REJECT_PENDING)

    def test_low_confidence_does_not_change_application_state(self):
        result = {
            'intent': APPROVE_PENDING,
            'confidence': 0.62,
            'references_pending': True,
        }
        self.assertIsNone(semantic_authorization(result))

    def test_unrelated_request_does_not_authorize_pending(self):
        result = {
            'intent': 'new_request',
            'confidence': 0.99,
            'references_pending': False,
        }
        self.assertIsNone(semantic_authorization(result))

    def test_question_does_not_authorize_pending(self):
        result = {
            'intent': 'question_about_pending_action',
            'confidence': 0.99,
            'references_pending': True,
        }
        self.assertIsNone(semantic_authorization(result))


if __name__ == '__main__':
    unittest.main()
