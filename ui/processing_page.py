import streamlit as st

from seismic.io import read_su_metadata


HEADER_KEYS = ['tracl', 'tracr', 'fldr', 'tracf', 'ep', 'cdp', 'cdpt', 'offset', 'sx', 'sy', 'gx', 'gy']
MUTE_KEYS = ['tracl', 'tracr', 'fldr', 'cdp', 'offset']
STACK_KEYS = ['cdp', 'fldr', 'ep']
HEADER_EDIT_KEYS = ['fldr', 'tracf', 'ep', 'cdp', 'cdpt', 'offset', 'sx', 'sy', 'gx', 'gy']

OPERATIONS = {
    'Bandpass Filter': 'sufilter',
    'Gain': 'sugain',
    'AGC': 'suagc',
    'Select Traces': 'suwind',
    'Sort Dataset': 'susort',
    'Resample Dataset': 'suresamp',
    'Mute': 'sumute',
    'Stack Traces': 'sustack',
    'Predictive Deconvolution': 'supef',
    'NMO': 'sunmo',
    'Set Header Constant': 'sushw_constant',
}


def _parse_float_list(text, label):
    try:
        values = [float(item.strip()) for item in text.split(',') if item.strip()]
    except ValueError as exc:
        raise ValueError(f'{label} must be a comma-separated list of numbers.') from exc
    if not values:
        raise ValueError(f'{label} cannot be empty.')
    return values


def _execute_manual(project, state, engine, current_path, tool_name, operation_name, parameters):
    out = project.next_output_path(operation_name)
    rec = engine.run_processing_step(
        state,
        tool_name,
        current_path,
        out,
        parameters,
        f'User-approved manual {operation_name}',
        project=project,
    )
    refreshed = read_su_metadata(out)
    state.current_step = rec['step_id']
    state.current_dataset = str(out)
    state.metadata = refreshed.to_dict()
    project.save_state(state)
    st.session_state.pending_action = None
    st.session_state.last_reflection = None
    st.success(f'Created {out.name}')
    st.rerun()


def _run_button(project, state, engine, current_path, tool_name, operation_name, parameters, *, disabled=False):
    if st.form_submit_button(
        f'Run {tool_name}',
        type='primary',
        use_container_width=True,
        disabled=disabled,
    ):
        try:
            _execute_manual(
                project,
                state,
                engine,
                current_path,
                tool_name,
                operation_name,
                parameters,
            )
        except Exception as exc:
            st.error(f'{operation_name} failed validation or execution.')
            st.code(str(exc))


def render_processing(project, state, engine, metadata, current_path, preview_traces=None):
    st.header('Processing')
    st.caption(
        'Manual processing controls. Each operation runs through the same Tool Registry, '
        'Validator, Workflow Engine, and SU Executor used by agent-triggered processing.'
    )

    operation_label = st.selectbox('Operation', list(OPERATIONS), key='manual_processing_operation')
    tool_name = OPERATIONS[operation_label]

    if tool_name == 'sufilter':
        df4 = min(75.0, metadata.nyquist_hz * 0.90)
        df3 = min(60.0, df4 * 0.80)
        df2 = min(10.0, df3 * 0.50)
        df1 = min(5.0, df2 * 0.50)
        with st.form('manual_sufilter_form'):
            st.subheader('Bandpass Filter')
            cols = st.columns(4)
            with cols[0]:
                f1 = st.number_input('F1 (Hz)', min_value=0.0, value=float(df1))
            with cols[1]:
                f2 = st.number_input('F2 (Hz)', min_value=0.0, value=float(df2))
            with cols[2]:
                f3 = st.number_input('F3 (Hz)', min_value=0.0, value=float(df3))
            with cols[3]:
                f4 = st.number_input('F4 (Hz)', min_value=0.0, value=float(df4))
            _run_button(project, state, engine, current_path, tool_name, 'filter', {
                'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4,
            })

    elif tool_name == 'sugain':
        with st.form('manual_sugain_form'):
            st.subheader('Gain')
            cols = st.columns(3)
            with cols[0]:
                tpow = st.number_input('Time power (tpow)', min_value=-5.0, max_value=5.0, value=0.0)
            with cols[1]:
                gpow = st.number_input('Amplitude power (gpow)', min_value=0.1, max_value=5.0, value=1.0)
            with cols[2]:
                qclip = st.number_input('Quantile clip (qclip)', min_value=0.0, max_value=1.0, value=1.0)
            _run_button(project, state, engine, current_path, tool_name, 'gain', {
                'tpow': tpow, 'gpow': gpow, 'qclip': qclip,
            })

    elif tool_name == 'suagc':
        with st.form('manual_suagc_form'):
            st.subheader('Automatic Gain Control')
            wagc = st.number_input('AGC window (s)', min_value=0.01, max_value=10.0, value=0.5)
            _run_button(project, state, engine, current_path, tool_name, 'agc', {'wagc': wagc})

    elif tool_name == 'suwind':
        with st.form('manual_suwind_form'):
            st.subheader('Select Traces')
            cols = st.columns(3)
            with cols[0]:
                key = st.selectbox('Header key', HEADER_KEYS)
            with cols[1]:
                minimum = st.number_input('Minimum', value=0.0)
            with cols[2]:
                maximum = st.number_input('Maximum', value=1000.0)
            _run_button(project, state, engine, current_path, tool_name, 'selection', {
                'key': key, 'min': minimum, 'max': maximum,
            })

    elif tool_name == 'susort':
        with st.form('manual_susort_form'):
            st.subheader('Sort Dataset')
            key = st.selectbox('Sort key', HEADER_KEYS, index=HEADER_KEYS.index('cdp'))
            _run_button(project, state, engine, current_path, tool_name, 'sort', {'key': key})

    elif tool_name == 'suresamp':
        with st.form('manual_suresamp_form'):
            st.subheader('Resample Dataset')
            dt = st.number_input(
                'New sample interval (s)',
                min_value=0.0001,
                max_value=0.1,
                value=float(metadata.dt_s),
                format='%.6f',
            )
            _run_button(project, state, engine, current_path, tool_name, 'resample', {'dt': dt})

    elif tool_name == 'sumute':
        with st.form('manual_sumute_form'):
            st.subheader('Polygonal Mute')
            key = st.selectbox('Header key', MUTE_KEYS, index=MUTE_KEYS.index('offset'))
            xmute_text = st.text_input('xmute', value='0,1000', help='Comma-separated header values.')
            tmute_text = st.text_input('tmute (s)', value='0.1,0.5', help='Comma-separated mute times in seconds.')
            cols = st.columns(2)
            with cols[0]:
                mode = st.selectbox('Mode', [0, 1], help='SUMUTE mode: top/bottom mute as validated by the registry.')
            with cols[1]:
                ntaper = st.number_input('Taper samples', min_value=0, max_value=1000, value=0, step=1)
            submitted = st.form_submit_button('Run sumute', type='primary', use_container_width=True)
            if submitted:
                try:
                    _execute_manual(project, state, engine, current_path, tool_name, 'mute', {
                        'key': key,
                        'xmute': _parse_float_list(xmute_text, 'xmute'),
                        'tmute': _parse_float_list(tmute_text, 'tmute'),
                        'mode': int(mode),
                        'ntaper': int(ntaper),
                    })
                except Exception as exc:
                    st.error('Mute failed validation or execution.')
                    st.code(str(exc))

    elif tool_name == 'sustack':
        with st.form('manual_sustack_form'):
            st.subheader('Stack Traces')
            st.caption('The current dataset must already be sorted by the same gather key.')
            cols = st.columns(2)
            with cols[0]:
                key = st.selectbox('Gather key', STACK_KEYS)
            with cols[1]:
                normpow = st.number_input('Normalization power', min_value=0.0, max_value=1.0, value=1.0)
            _run_button(project, state, engine, current_path, tool_name, 'stack', {
                'key': key, 'normpow': normpow,
            })

    elif tool_name == 'supef':
        with st.form('manual_supef_form'):
            st.subheader('Predictive Deconvolution')
            cols = st.columns(3)
            with cols[0]:
                minlag = st.number_input('Minimum lag (s)', min_value=0.0, value=0.02, format='%.4f')
            with cols[1]:
                maxlag = st.number_input('Maximum lag (s)', min_value=0.0, value=0.12, format='%.4f')
            with cols[2]:
                pnoise = st.number_input('Prewhitening (pnoise)', min_value=0.0, max_value=1.0, value=0.001, format='%.4f')
            _run_button(project, state, engine, current_path, tool_name, 'decon', {
                'minlag': minlag, 'maxlag': maxlag, 'pnoise': pnoise,
            })

    elif tool_name == 'sunmo':
        with st.form('manual_sunmo_form'):
            st.subheader('Normal Moveout')
            st.caption('Uses one time-only RMS velocity function and requires valid nonzero offset headers.')
            tnmo_text = st.text_input('tnmo (s)', value='0.0,1.0,2.0')
            vnmo_text = st.text_input('vnmo (m/s)', value='1500,2000,2500')
            cols = st.columns(3)
            with cols[0]:
                smute = st.number_input('Stretch mute (smute)', min_value=1.0, max_value=20.0, value=1.5)
            with cols[1]:
                lmute = st.number_input('Mute ramp (lmute)', min_value=0, max_value=1000, value=25, step=1)
            with cols[2]:
                sscale = st.selectbox('Stretch scaling (sscale)', [0, 1], index=1)
            submitted = st.form_submit_button('Run sunmo', type='primary', use_container_width=True)
            if submitted:
                try:
                    _execute_manual(project, state, engine, current_path, tool_name, 'nmo', {
                        'tnmo': _parse_float_list(tnmo_text, 'tnmo'),
                        'vnmo': _parse_float_list(vnmo_text, 'vnmo'),
                        'smute': smute,
                        'lmute': int(lmute),
                        'sscale': int(sscale),
                    })
                except Exception as exc:
                    st.error('NMO failed validation or execution.')
                    st.code(str(exc))

    else:
        with st.form('manual_sushw_form'):
            st.subheader('Set Header Constant')
            st.warning('This operation changes trace-header values for every trace and always requires explicit approval.')
            cols = st.columns(2)
            with cols[0]:
                key = st.selectbox('Header key', HEADER_EDIT_KEYS)
            with cols[1]:
                value = st.number_input('Constant value', value=0, step=1)
            confirmed = st.checkbox('I confirm this header edit should be applied to all traces.')
            _run_button(
                project,
                state,
                engine,
                current_path,
                tool_name,
                'header',
                {'key': key, 'value': int(value)},
                disabled=not confirmed,
            )
