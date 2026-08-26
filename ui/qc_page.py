from pathlib import Path
import streamlit as st

from seismic.io import read_su_metadata, load_preview_traces
from seismic.qc import compare_filter_result
from seismic.plotting import (
    section_figure,
    spectrum_figure,
    section_comparison_figure,
    spectrum_comparison_figure,
)
from ui.dataset_lineage import dataset_steps, TOOL_LABELS


def _step_label(step):
    return f"Step {step['step_id']} · {TOOL_LABELS.get(step['tool'], step['tool'])}"


def render_qc(state, history, selected_step, preview_traces=None):
    st.header('QC')

    steps = dataset_steps(history)
    if not steps or selected_step is None:
        st.info('No dataset step is available for QC.')
        return

    selected_id = int(selected_step['step_id'])
    selected_index = next(
        (i for i, item in enumerate(steps) if int(item['step_id']) == selected_id),
        None,
    )
    if selected_index is None:
        st.warning('The selected dataset step could not be resolved from project history.')
        return

    after_step = steps[selected_index]
    after_path = Path(after_step['output'])
    after_meta = read_su_metadata(after_path)
    after = load_preview_traces(after_path, after_meta, preview_traces)

    if selected_index == 0:
        st.caption(f"Viewing {_step_label(after_step)} · `{after_path.name}`")
        st.info('The import step has no previous dataset to compare against.')
        st.plotly_chart(
            section_figure(after, after_meta.dt_s, f'{_step_label(after_step)}'),
            use_container_width=True,
            key=f'qc_import_section_{selected_id}',
        )
        st.plotly_chart(
            spectrum_figure(after, None, after_meta.dt_s),
            use_container_width=True,
            key=f'qc_import_spectrum_{selected_id}',
        )
        return

    before_step = steps[selected_index - 1]
    before_path = Path(before_step['output'])
    before_meta = read_su_metadata(before_path)
    before = load_preview_traces(before_path, before_meta, preview_traces)

    st.caption(
        f"Before: {_step_label(before_step)} · `{before_path.name}`  →  "
        f"After: {_step_label(after_step)} · `{after_path.name}`"
    )

    view = st.segmented_control(
        'QC view',
        ['Seismic', 'Spectrum', 'Metrics'],
        default='Seismic',
        key='qc_view',
    )

    if view == 'Spectrum':
        st.plotly_chart(
            spectrum_comparison_figure(
                before,
                after,
                before_meta.dt_s,
                after_meta.dt_s,
                f'Before · {_step_label(before_step)}',
                f'After · {_step_label(after_step)}',
            ),
            use_container_width=True,
            key=f'qc_spectrum_comparison_{selected_id}',
        )

    elif view == 'Metrics':
        a, b, c, d = st.columns(4)
        a.metric('Before traces', f'{before_meta.estimated_trace_count:,}')
        b.metric('After traces', f'{after_meta.estimated_trace_count:,}')
        c.metric('Before dt', f'{before_meta.dt_us:,} us')
        d.metric('After dt', f'{after_meta.dt_us:,} us')

        if after_step.get('tool') == 'sufilter':
            p = after_step.get('parameters') or {}
            try:
                qc = compare_filter_result(
                    before,
                    after,
                    before_meta.dt_s,
                    float(p['f2']),
                    float(p['f3']),
                    float(p['f4']),
                )
                q1, q2, q3 = st.columns(3)
                q1.metric('Signal retention', f'{qc["signal_retention"]*100:.1f}%')
                q2.metric(
                    'High-frequency reduction',
                    f'{qc["high_frequency_reduction"]*100:.1f}%',
                )
                q3.metric('RMS ratio', f'{qc["rms_ratio"]:.3f}')
                st.json(qc)
            except Exception as exc:
                st.warning(f'Bandpass-specific QC metrics are unavailable: {exc}')
        else:
            st.caption(
                'Generic step comparison is shown here. Tool-specific metrics for this '
                'processing type can be added separately.'
            )

    else:
        st.plotly_chart(
            section_comparison_figure(
                before,
                after,
                before_meta.dt_s,
                after_meta.dt_s,
                f'Before · {_step_label(before_step)}',
                f'After · {_step_label(after_step)}',
            ),
            use_container_width=True,
            key=f'qc_section_comparison_{selected_id}',
        )

    reflection = st.session_state.get('last_reflection')
    if reflection and selected_id == int(state.current_step) and after_step.get('tool') == 'sufilter':
        st.subheader('Agent Review')
        st.markdown(f"**Decision:** {str(reflection.get('decision', 'review_only')).upper()}")
        if reflection.get('text'):
            st.write(reflection.get('text'))
        if reflection.get('confidence'):
            st.caption(f"Confidence: {reflection.get('confidence')}")
