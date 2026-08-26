import streamlit as st

from .components.proposal_card import render_proposal_card
from .workstation import APP_VERSION


def render_agent_panel(
    provider_info,
    agent_ready=True,
    agent_error=None,
    dataset_loaded=True,
    version=None,
):
    """Render the first-class Agent panel used by the workstation."""
    with st.container(key='agent_panel', border=False):
        with st.container(key='agent_panel_stack', border=False):
            with st.container(key='agent_header', border=False):
                title = f'Agentic SeismicUnix · v{APP_VERSION}'
                st.markdown(f'### {title}')
                if not dataset_loaded:
                    if agent_ready:
                        provider = provider_info or {}
                        label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
                        st.caption(
                            f"Knowledge Mode · {label} · {provider.get('model', 'unknown model')}"
                        )
                    else:
                        st.warning(agent_error or 'Agent is not configured.')
                elif agent_ready:
                    provider = provider_info or {}
                    label = 'OpenClaw' if provider.get('provider') == 'openclaw' else 'OpenAI'
                    st.caption(
                        f"Project Mode · {label} · {provider.get('model', 'unknown model')}"
                    )
                else:
                    st.warning(agent_error or 'Agent is not configured.')

            with st.container(key='agent_history', border=False):
                messages = st.session_state.get('chat_messages', [])[-50:]
                if messages:
                    for message in messages:
                        with st.chat_message(message['role']):
                            st.markdown(message['content'])
                elif not dataset_loaded:
                    with st.chat_message('assistant'):
                        st.markdown(
                            'Knowledge Mode is available before loading data. Ask about Seismic Unix '
                            'commands, parameters, or processing concepts. Upload SEG-Y to unlock '
                            'dataset inspection and processing.'
                        )

            with st.container(key='agent_composer', border=False):
                decision = None
                if dataset_loaded:
                    decision = render_proposal_card(st.session_state.get('pending_action'))

                disabled = not agent_ready
                placeholder = (
                    'Ask about this dataset...'
                    if dataset_loaded
                    else 'Ask about Seismic Unix...'
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
