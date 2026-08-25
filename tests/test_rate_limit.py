import uuid

import pytest

from security.policy import RateLimitError, enforce_agent_rate_limit


def test_agent_rate_limit(monkeypatch):
    monkeypatch.setenv('SECURITY_AGENT_REQUESTS_PER_MINUTE', '2')
    key = f'test-{uuid.uuid4().hex}'
    enforce_agent_rate_limit(key)
    enforce_agent_rate_limit(key)
    with pytest.raises(RateLimitError):
        enforce_agent_rate_limit(key)
