from types import SimpleNamespace

from agent.knowledge_mode import KNOWLEDGE_MODE_INSTRUCTIONS, run_knowledge_turn
from agent.providers.base import AgentProvider


class FakeProvider(AgentProvider):
    name = 'fake'
    model = 'fake-model'

    def __init__(self):
        self.calls = []

    def create_response(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text='SUPEF is a predictive error filter.')


def test_knowledge_mode_exposes_no_application_tools():
    provider = FakeProvider()
    result = run_knowledge_turn(
        'What does supef do?',
        [{'role': 'assistant', 'content': 'Knowledge Mode is active.'}],
        provider=provider,
    )

    assert result['pending_action'] is None
    assert result['tool_trace'] == []
    assert result['text'].startswith('SUPEF')

    call = provider.calls[0]
    assert 'tools' not in call
    assert 'tool_choice' not in call
    assert 'previous_response_id' not in call
    assert call['instructions'] == KNOWLEDGE_MODE_INSTRUCTIONS
    assert call['input'][-1] == {'role': 'user', 'content': 'What does supef do?'}


def test_knowledge_mode_instructions_forbid_dataset_claims_and_proposals():
    lowered = KNOWLEDGE_MODE_INSTRUCTIONS.lower()
    assert 'no seismic dataset is loaded' in lowered
    assert 'must not' in lowered
    assert 'seismic_proposal' in lowered
    assert 'project mode' in lowered
