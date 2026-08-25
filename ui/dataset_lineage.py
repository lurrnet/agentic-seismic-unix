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


def _dataset_steps(history):
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
            'output': str(rec.get('output')),
        })
    rows.sort(key=lambda item: item['step_id'])
    return rows


def render_dataset_lineage(state, history):
    """Render all successful dataset-producing steps as compact pills above tabs."""
    steps = _dataset_steps(history)
    if not steps:
        return

    with st.container(key='dataset_lineage', border=False):
        st.caption('Datasets')
        labels = []
        current_label = None
        details = {}
        for item in steps:
            label = f"{item['step_id']} · {TOOL_LABELS.get(item['tool'], item['tool'])}"
            labels.append(label)
            details[label] = item
            if item['step_id'] == int(state.current_step):
                current_label = label

        selected = st.pills(
            'Dataset lineage',
            labels,
            default=current_label,
            selection_mode='single',
            label_visibility='collapsed',
            key='dataset_lineage_pills',
        )

        item = details.get(selected or current_label)
        if item:
            is_current = item['step_id'] == int(state.current_step)
            prefix = 'Current' if is_current else 'Step'
            st.caption(f"{prefix} {item['step_id']}: `{Path(item['output']).name}`")
