import streamlit as st


def render_agent_details(
    provider_info=None,
    agent_ready=True,
    agent_error=None,
    history=None,
):
    st.header('Agent Details')

    provider = provider_info or {}
    if agent_ready:
        label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
        st.markdown(f"**Provider:** {label}")
        st.markdown(f"**Model:** `{provider.get('model', 'unknown model')}`")
    else:
        st.warning(agent_error or 'Agent is not configured.')

    trace = st.session_state.get('last_tool_trace') or []
    reflection = st.session_state.get('last_reflection')
    pending = st.session_state.get('pending_action')

    records = history.list() if history is not None else []
    command_records = [
        rec for rec in records
        if rec.get('status') == 'success' and rec.get('command_line')
    ]

    st.subheader('Latest SU Command')
    if command_records:
        latest = command_records[-1]
        st.caption(
            f"Step {latest.get('step_id')} · {latest.get('tool', 'SU command')}"
        )
        st.code(latest['command_line'], language='bash')
    else:
        st.caption(
            'No persisted SU command line is available yet. '
            'Commands executed before this feature was added do not contain command-line provenance.'
        )

    with st.expander('Executed SU Commands', expanded=False):
        if command_records:
            for rec in reversed(command_records):
                st.markdown(
                    f"**Step {rec.get('step_id')} · {rec.get('tool', 'SU command')}**"
                )
                st.code(rec['command_line'], language='bash')
        else:
            st.caption('No persisted SU commands are available for this project yet.')

    st.subheader('Last Tool Trace')
    if trace:
        st.json(trace)
    else:
        st.caption('No agent tool trace is available yet.')

    st.subheader('Latest Reflection')
    if reflection:
        st.markdown(
            f"**Decision:** {str(reflection.get('decision', 'review_only')).upper()}"
        )
        if reflection.get('confidence'):
            st.markdown(f"**Confidence:** {reflection.get('confidence')}")
        if reflection.get('text'):
            st.write(reflection.get('text'))
        if reflection.get('error'):
            st.error(reflection.get('error'))
        with st.expander('Reflection payload'):
            st.json(reflection)
    else:
        st.caption('No agent reflection is available yet.')

    st.subheader('Pending Processing Action')
    if pending:
        st.json(pending)
    else:
        st.caption('No processing proposal is currently pending.')
