import streamlit as st

from security.policy import get_security_limits


def _human_bytes(value):
    value = float(value)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


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
        if provider.get('provider') == 'openclaw':
            st.markdown(f"**Pinned Agent:** `{provider.get('agent_id') or 'not set'}`")
            st.markdown(f"**Tool Strategy:** `{provider.get('tool_strategy', 'unknown')}`")
        if provider.get('knowledge_layer'):
            st.markdown(f"**Knowledge Layer:** `{provider.get('knowledge_layer')}`")
            st.caption(
                f"Local SU docs: {provider.get('knowledge_docs_root', 'unknown')} · "
                f"max {provider.get('knowledge_max_docs', 0)} docs/request"
            )
    else:
        st.warning(agent_error or 'Agent is not configured.')

    st.subheader('Security Policy')
    limits = get_security_limits()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric('Max Upload', _human_bytes(limits['max_upload_bytes']))
        st.metric('Max Processing Steps', limits['max_processing_steps'])
    with c2:
        st.metric('Max Project Storage', _human_bytes(limits['max_project_bytes']))
        st.metric('Free-space Reserve', _human_bytes(limits['min_free_bytes']))
    with c3:
        st.metric('SU Timeout', f"{limits['su_timeout_seconds']} s")
        st.metric('Import Timeout', f"{limits['import_timeout_seconds']} s")
    st.caption(
        f"Heavy seismic jobs are single-concurrency; agent requests are limited to "
        f"{limits['agent_requests_per_minute']}/minute per project. Processing and import are "
        'shell-free, timeout-bounded, path-contained, storage-guarded, and application-validated.'
    )

    trace = st.session_state.get('last_tool_trace') or []
    reflection = st.session_state.get('last_reflection')
    pending = st.session_state.get('pending_action')
    intent_resolution = st.session_state.get('last_intent_resolution')

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

    st.subheader('Last Intent Resolution')
    if intent_resolution:
        st.markdown(f"**Intent:** `{intent_resolution.get('intent', 'unknown')}`")
        if intent_resolution.get('confidence') is not None:
            st.markdown(f"**Confidence:** `{intent_resolution.get('confidence')}`")
        st.markdown(
            f"**References Pending Proposal:** `{bool(intent_resolution.get('references_pending'))}`"
        )
        st.markdown(f"**Source:** `{intent_resolution.get('source', 'unknown')}`")
        if intent_resolution.get('reason'):
            st.write(intent_resolution.get('reason'))
        with st.expander('Intent payload', expanded=False):
            st.json(intent_resolution)
    else:
        st.caption('No pending-action semantic intent resolution is available yet.')

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
