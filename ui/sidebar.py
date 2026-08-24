import streamlit as st

from .components.proposal_card import render_proposal_card


def render_sidebar(
    provider_info,
    agent_ready=True,
    agent_error=None,
    dataset_loaded=True,
):
    """Render the persistent conversational sidebar.

    V0.5.2 keeps the sidebar visible from first launch. Before a dataset is loaded,
    the chat UI is present but disabled; project metadata and dataset controls stay
    in the main workspace.
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

        # Give most of the sidebar to chat. Evidence and plots stay in the main workspace.
        chat = st.container(height=520)
        with chat:
            if not dataset_loaded:
                with st.chat_message('assistant'):
                    st.markdown(
                        'Load a SEG-Y dataset to start a seismic processing conversation.'
                    )
            else:
                for message in st.session_state.get('chat_messages', [])[-20:]:
                    with st.chat_message(message['role']):
                        st.markdown(message['content'])

        chat_enabled = dataset_loaded and agent_ready
        prompt = st.chat_input(
            'Ask about this dataset...'
            if dataset_loaded
            else 'Upload a SEG-Y file to enable chat',
            key='sidebar_chat_input',
            disabled=not chat_enabled,
        )

        # Keep diagnostic details available without consuming normal chat space.
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

    return prompt, decision
