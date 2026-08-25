from agent.proposal_fallback import parse_explicit_user_command


def test_explicit_agc_command():
    result = parse_explicit_user_command('Apply AGC with a 0.5 s window.')
    assert result is not None
    assert result['action'] == 'apply_agc'
    assert result['parameters']['wagc'] == 0.5


def test_recommendation_is_not_direct_authorization():
    assert parse_explicit_user_command('Recommend an AGC window.') is None


def test_explicit_predictive_decon_command():
    result = parse_explicit_user_command(
        'Apply predictive decon minlag=0.04 maxlag=0.12 pnoise=0.001.'
    )
    assert result is not None
    assert result['action'] == 'apply_predictive_decon'
