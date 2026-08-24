import streamlit as st

from .components.proposal_card import render_proposal_card


def render_sidebar(provider_info, agent_ready=True, agent_error=None):
    """Render the persistent conversational sidebar.

    V0.5.1 intentionally reserves sidebar space for conversation and decisions.
    Project metadata, navigation, and dataset controls live in the main area.
    """
    with st.sidebar:
        st.markdown('### Seismic Agent')
        if agent_ready:
            provider = provider_info or {}
            label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
            st.caption(f"{label} · {provider.get('model', 'unknown model')}")
        else:
            st.warning(agent_error or 'Agent is not configured.')

        decision = render_proposal_card(st.session_state.get('pending_action'))

        # Give most of the sidebar to chat. Evidence and plots stay in the main workspace.
        chat = st.container(height=520)
        with chat:
            for message in st.session_state.get('chat_messages', [])[-20:]:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])

        prompt = st.chat_input(
            'Ask about this dataset...',
            key='sidebar_chat_input',
            disabled=not agent_ready,
        )

        # Keep diagnostic details available without consuming normal chat space.
        if st.session_state.get('last_tool_trace') or st.session_state.get('last_reflection'):
            with st.expander('Agent details'):
                if st.session_state.get('last_tool_trace'):
                    st.caption('Last tool trace')
                    st.json(st.session_state.last_tool_trace)

                if st.session_state.get('last_reflection'):
                    r = st.session_state.last_reflection
                    st.caption('Latest reflection')
                    st.markdown(f"**Decision:** {str(r.get('decision', 'review_only')).upper()}")
                    if r.get('confidence'):
                        st.caption(f"Confidence: {r.get('confidence')}")
                    if r.get('error'):
                        st.error(r['error'])

    return prompt, decision
