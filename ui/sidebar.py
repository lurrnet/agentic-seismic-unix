import streamlit as st

from .components.proposal_card import render_proposal_card


def render_sidebar(
    provider_info,
    agent_ready=True,
    agent_error=None,
    dataset_loaded=True,
):
    """Render the persistent conversational sidebar.

    V0.5.5 uses Streamlit's native stretch-height container for chat history.
    The chat composer is deliberately the final sidebar element so it stays at
    the bottom of the available sidebar layout.
    """
    with st.sidebar:
        st.markdown('### Seismic Agent')

        if not dataset_loaded:
            st.caption('Waiting for dataset')
            st.info('Upload a SEG-Y file in the main workspace to enable the agent.')
        elif agent_ready:
            provider = provider_info or {}
            label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
            st.caption(f"{label} · {provider.get('model', 'unknown model')}")
        else:
            st.warning(agent_error or 'Agent is not configured.')

        decision = None
        if dataset_loaded:
            decision = render_proposal_card(st.session_state.get('pending_action'))

        # Diagnostics belong above the conversation so the composer can remain
        # the final element in the sidebar.
        if dataset_loaded and (
            st.session_state.get('last_tool_trace')
            or st.session_state.get('last_reflection')
        ):
            with st.expander('Agent details'):
                if st.session_state.get('last_tool_trace'):
                    st.caption('Last tool trace')
                    st.json(st.session_state.last_tool_trace)

                if st.session_state.get('last_reflection'):
                    r = st.session_state.last_reflection
                    st.caption('Latest reflection')
                    st.markdown(
                        f"**Decision:** {str(r.get('decision', 'review_only')).upper()}"
                    )
                    if r.get('confidence'):
                        st.caption(f"Confidence: {r.get('confidence')}")
                    if r.get('error'):
                        st.error(r['error'])

        # Streamlit >=1.57 supports native stretch-height containers. This fills
        # the remaining sidebar height and becomes the independent scroll surface
        # for conversation history.
        chat = st.container(
            key='agent_chat_history',
            height='stretch',
            border=False,
            gap='small',
        )
        with chat:
            if not dataset_loaded:
                with st.chat_message('assistant'):
                    st.markdown(
                        'Load a SEG-Y dataset to start a seismic processing conversation.'
                    )
            else:
                for message in st.session_state.get('chat_messages', [])[-50:]:
                    with st.chat_message(message['role']):
                        st.markdown(message['content'])

        # Keep this as the LAST sidebar element. In a stretch-height sidebar,
        # the chat history consumes the flexible space and this stays below it.
        chat_enabled = dataset_loaded and agent_ready
        prompt = st.chat_input(
            'Ask about this dataset...'
            if dataset_loaded
            else 'Upload a SEG-Y file to enable chat',
            key='sidebar_chat_input',
            disabled=not chat_enabled,
        )

    return prompt, decision
