import streamlit as st


def render_proposal_card(action):
    if not action:
        return None

    st.markdown('### Pending Approval')
    params = action['parameters']
    st.markdown(
        f"**Bandpass:** `{params['f1']:g} / {params['f2']:g} / "
        f"{params['f3']:g} / {params['f4']:g} Hz`"
    )
    reason = action.get('reason')
    if reason:
        st.caption(reason)

    a, b = st.columns(2)
    approve = a.button(
        'Approve',
        type='primary',
        use_container_width=True,
        key='sidebar_approve_filter',
    )
    reject = b.button(
        'Reject',
        use_container_width=True,
        key='sidebar_reject_filter',
    )
    return 'approve' if approve else ('reject' if reject else None)
