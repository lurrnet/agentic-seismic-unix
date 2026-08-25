from pathlib import Path
import streamlit as st

from seismic.io import read_su_metadata, load_preview_traces
from seismic.qc import compare_filter_result
from seismic.plotting import section_figure, spectrum_figure


def render_qc(state, history, current_path, metadata, preview_traces=None):
    st.header('QC')
    recs = history.list()
    filters = [r for r in recs if r.get('tool') == 'sufilter' and r.get('status') == 'success']

    if not filters:
        try:
            tr = load_preview_traces(current_path, metadata, preview_traces)
            st.plotly_chart(
                section_figure(tr, metadata.dt_s, 'Current dataset'),
                use_container_width=True,
                key='qc_current_section',
            )
            st.plotly_chart(
                spectrum_figure(tr, None, metadata.dt_s),
                use_container_width=True,
                key='qc_current_spectrum',
            )
        except Exception as exc:
            st.warning(str(exc))
        st.info('Apply a filter to enable before/after QC.')
        return

    r = filters[-1]
    bp, ap = Path(r['input']), Path(r['output'])
    bm, am = read_su_metadata(bp), read_su_metadata(ap)
    before = load_preview_traces(bp, bm, preview_traces)
    after = load_preview_traces(ap, am, preview_traces)

    view = st.segmented_control(
        'QC view',
        ['Seismic', 'Spectrum', 'Metrics'],
        default='Seismic',
        key='qc_view',
    )

    pp = r['parameters']
    qc = compare_filter_result(
        before, after, bm.dt_s,
        float(pp['f2']), float(pp['f3']), float(pp['f4'])
    )

    if view == 'Spectrum':
        st.plotly_chart(
            spectrum_figure(before, after, bm.dt_s),
            use_container_width=True,
            key='qc_compare_spectrum',
        )
    elif view == 'Metrics':
        q1, q2, q3 = st.columns(3)
        q1.metric('Signal retention', f'{qc["signal_retention"]*100:.1f}%')
        q2.metric('High-frequency reduction', f'{qc["high_frequency_reduction"]*100:.1f}%')
        q3.metric('RMS ratio', f'{qc["rms_ratio"]:.3f}')
        st.json(qc)
    else:
        l, rr = st.columns(2)
        with l:
            st.plotly_chart(
                section_figure(before, bm.dt_s, 'Before'),
                use_container_width=True,
                key='qc_before_section',
            )
        with rr:
            st.plotly_chart(
                section_figure(after, am.dt_s, 'After'),
                use_container_width=True,
                key='qc_after_section',
            )
        st.plotly_chart(
            spectrum_figure(before, after, bm.dt_s),
            use_container_width=True,
            key='qc_seismic_compare_spectrum',
        )

    reflection = st.session_state.get('last_reflection')
    if reflection:
        st.subheader('Agent Review')
        st.markdown(f"**Decision:** {str(reflection.get('decision', 'review_only')).upper()}")
        if reflection.get('text'):
            st.write(reflection.get('text'))
        if reflection.get('confidence'):
            st.caption(f"Confidence: {reflection.get('confidence')}")
