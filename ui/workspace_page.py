import streamlit as st

from seismic.io import get_surange, load_preview_traces
from seismic.plotting import section_figure, spectrum_figure


def render_workspace(project, state, metadata, history, current_path, preview_traces=None):
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.header('Workspace')
    with top_right:
        new_project = st.button(
            'Load new dataset',
            use_container_width=True,
            key='workspace_load_new_dataset',
        )

    a, b, c, d = st.columns(4)
    a.metric('Samples / trace', f'{metadata.ns:,}')
    b.metric('Sample interval', f'{metadata.dt_us:,} us')
    c.metric('Nyquist', f'{metadata.nyquist_hz:.2f} Hz')
    d.metric('Estimated traces', f'{metadata.estimated_trace_count:,}')

    try:
        traces = load_preview_traces(current_path, metadata, preview_traces)
        st.plotly_chart(
            section_figure(traces, metadata.dt_s, 'Current seismic section'),
            use_container_width=True,
            key='workspace_current_section',
        )
        st.plotly_chart(
            spectrum_figure(traces, None, metadata.dt_s),
            use_container_width=True,
            key='workspace_current_spectrum',
        )
    except Exception as exc:
        st.warning('Current dataset preview could not be generated.')
        st.code(str(exc))

    recs = history.list()
    filters = [r for r in recs if r.get('tool') == 'sufilter' and r.get('status') == 'success']
    st.subheader('Processing status')
    st.write(
        f"Imported dataset: **Yes** · Successful bandpass steps: **{len(filters)}** "
        f"· Current step: **{state.current_step}**"
    )

    with st.expander('Dataset headers (surange)'):
        try:
            st.code(get_surange(current_path))
        except Exception as exc:
            st.warning(str(exc))

    with st.expander('System workflow'):
        st.code(
            'Agent / Manual request\n'
            '        -> Tool Registry -> Validator -> Workflow Engine\n'
            '        -> SU Executor -> SU result\n'
            '        -> Deterministic QC -> Agent Reflection\n'
            '        -> Accept or approval-gated adjustment'
        )

    return new_project
