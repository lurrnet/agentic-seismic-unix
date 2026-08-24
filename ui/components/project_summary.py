from pathlib import Path
import streamlit as st


def render_project_summary(state, metadata):
    st.markdown('### Project')
    st.caption(f'Project `{state.project_id[:12]}`')
    st.markdown(f'**Current:** `{Path(state.current_dataset).name}`')
    c1, c2 = st.columns(2)
    c1.metric('Step', state.current_step)
    c2.metric('dt', f'{metadata.dt_us:,} us')
    c3, c4 = st.columns(2)
    c3.metric('Samples', f'{metadata.ns:,}')
    c4.metric('Nyquist', f'{metadata.nyquist_hz:.1f} Hz')
