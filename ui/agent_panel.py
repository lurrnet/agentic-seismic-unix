import streamlit as st

from .components.proposal_card import render_proposal_card


def render_agent_panel(
    provider_info,
    agent_ready=True,
    agent_error=None,
    dataset_loaded=True,
):
    """Render the first-class Agent panel used by the V0.6 workstation."""
    with st.container(key='agent_panel', border=False):
        with st.container(key='agent_panel_stack', border=False):
            with st.container(key='agent_header', border=False):
                st.markdown('### Agentic SeismicUnix')
                if not dataset_loaded:
                    st.caption('Waiting for dataset')
                elif agent_ready:
                    provider = provider_info or {}
                    label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
                    st.caption(f"{label} · {provider.get('model', 'unknown model')}")
                else:
                    st.warning(agent_error or 'Agent is not configured.')

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

            with st.container(key='agent_history', border=False):
                if not dataset_loaded:
                    with st.chat_message('assistant'):
                        st.markdown(
                            'Load a SEG-Y dataset to start a seismic processing conversation.'
                        )
                else:
                    for message in st.session_state.get('chat_messages', [])[-50:]:
                        with st.chat_message(message['role']):
                            st.markdown(message['content'])

            with st.container(key='agent_composer', border=False):
                decision = None
                if dataset_loaded:
                    decision = render_proposal_card(st.session_state.get('pending_action'))

                disabled = not (dataset_loaded and agent_ready)
                placeholder = (
                    'Ask about this dataset...'
                    if dataset_loaded
                    else 'Upload a SEG-Y file to enable chat'
                )

                with st.form('agent_chat_form', clear_on_submit=True, border=False):
                    prompt_text = st.text_area(
                        'Message',
                        placeholder=placeholder,
                        label_visibility='collapsed',
                        height=88,
                        disabled=disabled,
                    )
                    submitted = st.form_submit_button(
                        'Send',
                        type='primary',
                        use_container_width=True,
                        disabled=disabled,
                    )

                prompt = prompt_text.strip() if submitted and prompt_text.strip() else None

    return prompt, decision
