import streamlit as st

from seismic.io import get_surange, load_preview_traces
from seismic.plotting import section_figure, spectrum_figure
from ui.plot_config import load_plotting_config


@st.fragment
def _render_workspace_plots(current_path, metadata, preview_traces):
    try:
        traces = load_preview_traces(current_path, metadata, preview_traces)
        plot_cfg = load_plotting_config()
        colormaps = plot_cfg['colormaps']
        default_colormap = plot_cfg['default_colormap']

        st.caption('Plot controls')
        clip_col, cmap_col, polarity_col = st.columns([2, 1, 1])
        with clip_col:
            clip_percentile = st.slider(
                'Amplitude clip percentile',
                min_value=90.0,
                max_value=100.0,
                value=99.0,
                step=0.5,
                key='workspace_seismic_clip_percentile',
            )
        with cmap_col:
            colorscale = st.selectbox(
                'Colormap',
                colormaps,
                index=colormaps.index(default_colormap),
                key='workspace_seismic_colormap',
            )
        with polarity_col:
            flip_polarity = st.toggle(
                'Flip polarity',
                value=plot_cfg['default_flip_polarity'],
                key='workspace_flip_polarity',
                help='Display-only polarity reversal; the SU dataset is not modified.',
            )

        st.plotly_chart(
            section_figure(
                traces,
                metadata.dt_s,
                'Current seismic section',
                clip_percentile=clip_percentile,
                colorscale=colorscale,
                flip_polarity=flip_polarity,
            ),
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

    _render_workspace_plots(current_path, metadata, preview_traces)

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
