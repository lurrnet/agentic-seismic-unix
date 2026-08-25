from pathlib import Path
import streamlit as st


TOOL_LABELS = {
    'segyread|segyclean': 'Import',
    'sufilter': 'Bandpass',
    'sugain': 'Gain',
    'suagc': 'AGC',
    'suwind': 'Select',
    'sushw_constant': 'Header',
    'susort': 'Sort',
    'suresamp': 'Resample',
    'sumute': 'Mute',
    'sustack': 'Stack',
}


def dataset_steps(history):
    rows = []
    for rec in history.list():
        if rec.get('status') != 'success' or not rec.get('output'):
            continue
        step_id = rec.get('step_id')
        if step_id is None:
            continue
        rows.append({
            'step_id': int(step_id),
            'tool': rec.get('tool', 'step'),
            'input': str(rec.get('input')) if rec.get('input') else None,
            'output': str(rec.get('output')),
            'parameters': rec.get('parameters') or {},
            'record': rec,
        })
    rows.sort(key=lambda item: item['step_id'])
    return rows


def render_dataset_lineage(state, history):
    """Render lineage pills and return the selected dataset-producing step."""
    steps = dataset_steps(history)
    if not steps:
        return None

    labels = []
    label_by_step = {}
    details = {}
    current_step = int(state.current_step)
    current_label = None

    for item in steps:
        label = f"{item['step_id']} · {TOOL_LABELS.get(item['tool'], item['tool'])}"
        labels.append(label)
        label_by_step[item['step_id']] = label
        details[label] = item
        if item['step_id'] == current_step:
            current_label = label

    pill_key = 'dataset_lineage_pills'
    active_key = 'dataset_lineage_active_step'
    stored_selected = st.session_state.get(pill_key)
    previous_active_step = st.session_state.get(active_key)

    if stored_selected not in labels:
        st.session_state.pop(pill_key, None)
        stored_selected = None

    # If processing created a new active step while the user was viewing the
    # previous active step, advance the pill automatically. If the user had
    # intentionally browsed to an older step, preserve that historical view.
    if previous_active_step is None:
        st.session_state[active_key] = current_step
        if stored_selected is None and current_label is not None:
            st.session_state[pill_key] = current_label
    elif int(previous_active_step) != current_step:
        previous_active_label = label_by_step.get(int(previous_active_step))
        if stored_selected is None or stored_selected == previous_active_label:
            if current_label is not None:
                st.session_state[pill_key] = current_label
        st.session_state[active_key] = current_step

    with st.container(key='dataset_lineage', border=False):
        label_col, pills_col = st.columns([1, 5], gap='small', vertical_alignment='center')
        with label_col:
            st.markdown('**Datasets**')
        with pills_col:
            selected = st.pills(
                'Dataset lineage',
                labels,
                default=current_label,
                selection_mode='single',
                label_visibility='collapsed',
                key=pill_key,
            )

        item = details.get(selected or current_label)
        if item:
            is_active = item['step_id'] == current_step
            prefix = 'Active' if is_active else 'Viewing'
            st.caption(f"{prefix} step {item['step_id']}: `{Path(item['output']).name}`")
            return item

    return None
