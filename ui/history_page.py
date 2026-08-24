import streamlit as st


def render_history(state, history, registry):
    st.header('History')
    recs = history.list()

    if not recs:
        st.info('No processing history yet.')
    else:
        st.subheader('Processing timeline')
        for r in recs:
            icon = '✅' if r.get('status') == 'success' else '⚠️'
            tool = r.get('tool', 'unknown')
            step = r.get('step_id')
            st.markdown(f"{icon} **Step {step}** · `{tool}`")
            params = r.get('parameters') or {}
            if params:
                st.caption(' · '.join(f'{k}={v}' for k, v in params.items()))

        st.divider()
        st.subheader('Detailed provenance')
        for r in reversed(recs):
            with st.expander(f"Step {r.get('step_id')}: {r.get('tool')}"):
                st.json(r)

    with st.expander('Project state'):
        st.json(state.to_dict())
    with st.expander('Registered tool specifications'):
        st.json(registry.list_tools())
