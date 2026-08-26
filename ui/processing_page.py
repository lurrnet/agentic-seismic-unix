import streamlit as st


def render_processing(project, state, engine, metadata, current_path, preview_traces=None):
    st.header('Processing')
    st.caption(
        'Manual processing controls. Use this tab for operations you want to run directly '
        'without initiating them through agent chat.'
    )

    df4 = min(75.0, metadata.nyquist_hz * .90)
    df3 = min(60.0, df4 * .80)
    df2 = min(10.0, df3 * .50)
    df1 = min(5.0, df2 * .50)

    with st.container(border=True):
        st.subheader('Bandpass Filter')
        cs = st.columns(4)
        with cs[0]:
            f1 = st.number_input('F1 (Hz)', min_value=0.0, value=float(df1), key='proc_f1')
        with cs[1]:
            f2 = st.number_input('F2 (Hz)', min_value=0.0, value=float(df2), key='proc_f2')
        with cs[2]:
            f3 = st.number_input('F3 (Hz)', min_value=0.0, value=float(df3), key='proc_f3')
        with cs[3]:
            f4 = st.number_input('F4 (Hz)', min_value=0.0, value=float(df4), key='proc_f4')

        st.caption('Runs through Tool Registry -> Validator -> Workflow Engine -> SU Executor.')
        if st.button('Run sufilter', type='primary', key='manual_sufilter'):
            out = project.next_output_path('filter')
            rec = engine.run_processing_step(
                state,
                'sufilter',
                current_path,
                out,
                {'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4},
                'User-approved manual bandpass filter',
            )
            state.current_step = rec['step_id']
            state.current_dataset = str(out)
            project.save_state(state)
            st.session_state.pending_action = None
            st.success(f'Created {out.name}')
            st.rerun()
