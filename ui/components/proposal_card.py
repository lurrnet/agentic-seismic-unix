import streamlit as st


def _format_parameters(action):
    tool = action.get('tool')
    params = action.get('parameters') or {}

    if tool == 'sufilter':
        return (
            f"**Bandpass:** `{params['f1']:g} / {params['f2']:g} / "
            f"{params['f3']:g} / {params['f4']:g} Hz`"
        )
    if tool == 'sugain':
        return (
            f"**Gain:** `tpow={params['tpow']:g}, gpow={params['gpow']:g}, "
            f"qclip={params['qclip']:g}`"
        )
    if tool == 'suagc':
        return f"**AGC:** `wagc={params['wagc']:g} s`"
    if tool == 'suwind':
        return (
            f"**Trace selection:** `{params['key']} = "
            f"{params['min']:g} .. {params['max']:g}`"
        )

    if not params:
        return None
    return '**Parameters:** `' + ', '.join(f'{k}={v}' for k, v in params.items()) + '`'


def render_proposal_card(action):
    if not action:
        return None

    st.markdown('### Pending Approval')
    st.caption(action.get('display_name') or action.get('tool', 'Processing'))

    summary = _format_parameters(action)
    if summary:
        st.markdown(summary)

    reason = action.get('reason')
    if reason:
        st.caption(reason)

    action_key = str(action.get('action') or action.get('tool') or 'processing')
    a, b = st.columns(2)
    approve = a.button(
        'Approve',
        type='primary',
        use_container_width=True,
        key=f'approve_{action_key}',
    )
    reject = b.button(
        'Reject',
        use_container_width=True,
        key=f'reject_{action_key}',
    )
    return 'approve' if approve else ('reject' if reject else None)
