import streamlit as st

from .components.project_summary import render_project_summary
from .components.proposal_card import render_proposal_card


PAGES = ['Workspace', 'Processing', 'QC', 'History']


def render_sidebar(state, metadata, provider_info, agent_ready=True, agent_error=None):
    with st.sidebar:
        render_project_summary(state, metadata)
        new_project = st.button('Load new dataset', use_container_width=True, key='load_new_dataset')
        st.divider()

        page = st.radio(
            'Navigation',
            PAGES,
            key='workspace_page',
            label_visibility='visible',
        )

        st.divider()
        decision = render_proposal_card(st.session_state.get('pending_action'))

        st.divider()
        st.markdown('### Seismic Agent')
        if agent_ready:
            provider = provider_info or {}
            label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
            st.caption(f"{label} · {provider.get('model', 'unknown model')}")
        else:
            st.warning(agent_error or 'Agent is not configured.')

        # Keep sidebar chat intentionally compact. Full evidence/plots remain in main workspace.
        chat = st.container(height=330)
        with chat:
            for message in st.session_state.get('chat_messages', [])[-10:]:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])

        prompt = st.chat_input(
            'Ask about this dataset...',
            key='sidebar_chat_input',
            disabled=not agent_ready,
        )

        if st.session_state.get('last_tool_trace'):
            with st.expander('Last tool trace'):
                st.json(st.session_state.last_tool_trace)

        if st.session_state.get('last_reflection'):
            with st.expander('Latest reflection'):
                r = st.session_state.last_reflection
                st.markdown(f"**Decision:** {str(r.get('decision', 'review_only')).upper()}")
                if r.get('confidence'):
                    st.caption(f"Confidence: {r.get('confidence')}")
                if r.get('error'):
                    st.error(r['error'])

    return page, prompt, decision, new_project
