from pathlib import Path
import re
import streamlit as st

from agent.seismic_agent import SeismicAgent, AgentConfigurationError
from agent.provider_factory import load_agent_config
from agent.toolkit import AgentToolkit
from agent.proposal_fallback import parse_explicit_user_command
from project.project import Project
from workflow.history import HistoryStore
from workflow.engine import WorkflowEngine
from su.registry import ToolRegistry
from su.executor import SUExecutor
from su.importer import segy_to_su
from seismic.io import read_su_metadata
from ui.agent_panel import render_agent_panel
from ui.workstation import workstation_columns
from ui.workspace_page import render_workspace
from ui.processing_page import render_processing
from ui.qc_page import render_qc
from ui.history_page import render_history
from ui.agent_details_page import render_agent_details
from ui.readme_page import render_readme
from ui.dataset_lineage import render_dataset_lineage


VERSION = '0.8.7'
DATA_ROOT = Path('/data/projects')
TOOLS_DIR = Path('/app/tools')
PREVIEW_TRACES = None

st.set_page_config(
    page_title=f'Agentic SeismicUnix V{VERSION}',
    page_icon='〰️',
    layout='wide',
    initial_sidebar_state='collapsed',
)

registry = ToolRegistry(TOOLS_DIR)
executor = SUExecutor(registry)


def get_reflection_config():
    try:
        return load_agent_config().get('reflection') or {}
    except Exception:
        return {}


def create_project(uploaded):
    project = Project(DATA_ROOT)
    raw = project.raw_dir / Path(uploaded.name).name
    su = project.data_dir / 'step000_import.su'
    raw.write_bytes(uploaded.getbuffer())
    segy_to_su(raw, su)
    metadata = read_su_metadata(su)
    state = project.initialize(str(raw), str(su), metadata.to_dict())
    HistoryStore(project.history_dir / 'workflow.json').append({
        'step_id': 0, 'parent_step': None, 'tool': 'segyread|segyclean',
        'input': str(raw), 'output': str(su), 'parameters': {},
        'reason': 'SEG-Y import', 'status': 'success',
    })
    return project, state


def reset_chat_for_project():
    st.session_state.chat_messages = [{
        'role': 'assistant',
        'content': (
            'Dataset loaded. I can inspect data, frequency, amplitude and geometry; apply filters, '
            'gain, AGC or mute; select or sort traces; resample data; stack sorted gathers; '
            'and propose restricted header edits.'
        ),
    }]
    st.session_state.pending_action = None
    st.session_state.pending_user_prompt = None
    st.session_state.last_tool_trace = []
    st.session_state.last_reflection = None


def execute_pending_processing(project, state, history, engine, action):
    current = Path(state.current_dataset)
    if action.get('status') != 'pending_approval':
        raise ValueError('This action is no longer pending approval.')
    if Path(action['input']) != current:
        raise ValueError(
            'The project dataset changed after this proposal was created. '
            'Ask the agent to inspect the current dataset and propose a new operation.'
        )
    tool_name = action['tool']
    operation = action.get('operation', tool_name)
    out = project.next_output_path(operation)
    authorization = action.get('authorization')
    if authorization == 'explicit_user_command':
        reason = f"Explicit user command: {action.get('reason', '')}"
    elif authorization == 'explicit_followup_confirmation':
        reason = f"Explicit follow-up confirmation: {action.get('reason', '')}"
    else:
        reason = f"Agent proposal approved by user: {action.get('reason', '')}"
    rec = engine.run_processing_step(
        state, tool_name, current, out, action['parameters'], reason)
    refreshed = read_su_metadata(out)
    state.current_step = rec['step_id']
    state.current_dataset = str(out)
    state.metadata = refreshed.to_dict()
    project.save_state(state)
    return rec, out


def run_reflection_after_filter(project, history, registry, out):
    reflection_message = f'Filter executed successfully as `{out.name}`.'
    reflection_cfg = get_reflection_config()
    auto_reflect = bool(
        reflection_cfg.get('enabled', True)
        and reflection_cfg.get('auto_after_agent_filter', True)
    )
    if not auto_reflect:
        st.session_state.last_reflection = None
        return reflection_message + '\n\nAutomatic QC reflection is disabled in `config/agent.yaml`.'
    try:
        refreshed_state = project.load_state()
        max_traces = int(reflection_cfg.get('max_preview_traces', 200))
        toolkit = AgentToolkit(project, refreshed_state, history, registry, preview_traces=max_traces)
        agent = SeismicAgent()
        reflection = agent.review_latest_filter(toolkit, max_traces=max_traces)
        st.session_state.last_reflection = reflection
        if reflection.get('pending_action') is not None:
            st.session_state.pending_action = reflection['pending_action']
        history.append({
            'step_id': refreshed_state.current_step, 'parent_step': refreshed_state.current_step,
            'tool': 'qc_reflection', 'input': str(out), 'output': None, 'parameters': {},
            'reason': reflection.get('reason', ''), 'status': reflection.get('status', 'success'),
            'decision': reflection.get('decision'), 'confidence': reflection.get('confidence'),
            'qc': reflection.get('qc'), 'provider': reflection.get('provider'), 'model': reflection.get('model'),
        })
        return reflection_message + '\n\n' + reflection['text']
    except Exception as exc:
        st.session_state.last_reflection = {'status': 'error', 'decision': 'review_only', 'error': str(exc)}
        return reflection_message + '\n\nThe filter completed, but automatic QC reflection failed: ' + f'`{exc}`. The QC page remains available.'


def run_agent_turn(prompt, project, state, history):
    prior_history = list(st.session_state.chat_messages)
    if prior_history and prior_history[-1].get('role') == 'user' and prior_history[-1].get('content') == prompt:
        prior_history = prior_history[:-1]
    toolkit = AgentToolkit(project, state, history, registry, preview_traces=200)
    agent = SeismicAgent()
    result = agent.run_turn(prompt, prior_history, toolkit)
    st.session_state.chat_messages.append({'role': 'assistant', 'content': result['text']})
    st.session_state.last_tool_trace = result['tool_trace']
    if result['pending_action'] is not None:
        st.session_state.pending_action = result['pending_action']


def build_explicit_processing_action(command, project, state, history):
    toolkit = AgentToolkit(project, state, history, registry, preview_traces=200)
    action = command['action']
    params = command['parameters']
    reason = command.get('reason') or 'Explicit user command with complete parameters.'
    if action == 'apply_bandpass_filter': toolkit.propose_bandpass({**params, 'reason': reason})
    elif action == 'apply_gain': toolkit.propose_gain({**params, 'reason': reason})
    elif action == 'apply_agc': toolkit.propose_agc({**params, 'reason': reason})
    elif action == 'select_traces': toolkit.propose_trace_selection({**params, 'reason': reason})
    elif action == 'sort_dataset': toolkit.propose_sort({**params, 'reason': reason})
    elif action == 'resample_dataset': toolkit.propose_resample({**params, 'reason': reason})
    elif action == 'apply_mute': toolkit.propose_mute({**params, 'reason': reason})
    elif action == 'stack_traces': toolkit.propose_stack({**params, 'reason': reason})
    else: raise ValueError(f'Unsupported explicit processing action: {action}')
    pending = toolkit.pending_action
    if pending is None:
        raise ValueError('Explicit command did not produce a processing action.')
    spec = registry.get(pending['tool'])
    if spec.get('approval_policy') != 'explicit_or_approval':
        raise ValueError(f"{pending.get('display_name', pending['tool'])} does not allow direct execution.")
    pending['authorization'] = 'explicit_user_command'
    return pending


def execute_authorized_action(prompt, action, project, state, history, engine, routed_by):
    st.session_state.pending_action = None
    rec, out = execute_pending_processing(project, state, history, engine, action)
    if action.get('tool') == 'sufilter':
        completion_message = run_reflection_after_filter(project, history, registry, out)
    else:
        completion_message = (
            f"Executed **{action.get('display_name', action.get('tool', 'processing'))}** "
            f"with parameters `{action.get('parameters', {})}`. Output: `{out.name}`."
        )
        st.session_state.last_reflection = None
    st.session_state.last_tool_trace = [{
        'tool': action.get('action', action.get('tool')),
        'arguments': action.get('parameters', {}),
        'result': {'status': 'success', 'step_id': rec.get('step_id'), 'output': str(out)},
        'routed_by': routed_by,
    }]
    st.session_state.chat_messages.append({'role': 'assistant', 'content': completion_message})


def is_explicit_followup_confirmation(prompt, action):
    if not action or action.get('status') != 'pending_approval': return False
    spec = registry.get(action['tool'])
    if spec.get('approval_policy') != 'explicit_or_approval': return False
    text = prompt.strip().lower()
    patterns = (
        r'^(?:yes[, ]*)?(?:go ahead|proceed|do it|run it|execute it|apply it)[.! ]*$',
        r'^(?:yes[, ]*)?(?:apply|run|execute)\s+(?:that|this|such)(?:\s+(?:agc|gain|filter|bandpass|selection|sort|resample|mute|stack))?[.! ]*$',
        r'^(?:yes[, ]*)?(?:apply|run|execute)\s+(?:the\s+)?(?:recommended|proposed)\s+(?:agc|gain|filter|bandpass|selection|sort|resample|mute|stack)[.! ]*$',
    )
    return any(re.match(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


if 'project_id' not in st.session_state:
    agent_col, workspace_col = workstation_columns()
    with agent_col:
        render_agent_panel(
            provider_info=None,
            agent_ready=False,
            dataset_loaded=False,
            version=VERSION,
        )
    with workspace_col:
        with st.container(key='initial_load_panel', border=False):
            st.subheader('Load Data')
            uploaded = st.file_uploader(
                'Upload a SEG-Y file',
                type=['sgy', 'segy'],
                help='SEG-Y is converted to SU inside the project workspace.',
            )
            if uploaded is None:
                st.info('Upload a `.sgy` or `.segy` file to begin. Agent chat will unlock after loading.')
                st.stop()
            signature = f'{uploaded.name}:{uploaded.size}'
            try:
                with st.spinner('Creating project and converting SEG-Y to SU...'):
                    project, state = create_project(uploaded)
                st.session_state.upload_signature = signature
                st.session_state.project_id = project.project_id
                reset_chat_for_project()
                st.rerun()
            except Exception as exc:
                st.error('Failed to initialize the project.')
                st.code(str(exc))
                st.stop()

project = Project(DATA_ROOT, st.session_state.project_id)
state = project.load_state()
history = HistoryStore(project.history_dir / 'workflow.json')
engine = WorkflowEngine(executor, history)
current = Path(state.current_dataset)
metadata = read_su_metadata(current)
for key, default in [
    ('chat_messages', []), ('pending_action', None), ('pending_user_prompt', None),
    ('last_tool_trace', []), ('last_reflection', None),
]:
    if key not in st.session_state: st.session_state[key] = default

agent_ready = True
agent_error = None
provider_info = None
try: provider_info = SeismicAgent().provider_info
except AgentConfigurationError as exc:
    agent_ready = False; agent_error = str(exc)
except Exception as exc:
    agent_ready = False; agent_error = str(exc)

agent_col, workspace_col = workstation_columns()
with agent_col:
    prompt, decision = render_agent_panel(
        provider_info,
        agent_ready=agent_ready,
        agent_error=agent_error,
        dataset_loaded=True,
        version=VERSION,
    )

if prompt:
    st.session_state.chat_messages.append({'role': 'user', 'content': prompt})
    st.session_state.pending_user_prompt = prompt
    st.rerun()

if decision == 'reject':
    action = st.session_state.pending_action or {}
    st.session_state.pending_action = None
    st.session_state.chat_messages.append({'role': 'assistant', 'content': f"The pending {action.get('display_name', 'processing')} proposal was rejected and no processing was run."})
    st.rerun()

if decision == 'approve':
    action = st.session_state.pending_action
    try:
        rec, out = execute_pending_processing(project, state, history, engine, action)
        st.session_state.pending_action = None
        if action.get('tool') == 'sufilter': completion_message = run_reflection_after_filter(project, history, registry, out)
        else:
            completion_message = f"Approved **{action.get('display_name', action.get('tool', 'processing'))}** executed successfully as `{out.name}`."
            st.session_state.last_reflection = None
        st.session_state.chat_messages.append({'role': 'assistant', 'content': completion_message})
        st.rerun()
    except Exception as exc:
        st.error('Approved processing failed.')
        st.code(str(exc))

queued_prompt = st.session_state.pop('pending_user_prompt', None)
if queued_prompt:
    with st.spinner('Agent is working...'):
        pending = st.session_state.get('pending_action')
        if is_explicit_followup_confirmation(queued_prompt, pending):
            try:
                action = dict(pending)
                action['authorization'] = 'explicit_followup_confirmation'
                execute_authorized_action(
                    queued_prompt, action, project, state, history, engine,
                    routed_by='explicit_followup_confirmation')
                st.rerun()
            except Exception as exc:
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f'I recognized your follow-up as authorization for the pending proposal, but execution failed validation: `{exc}`. No processing was run.'})
                st.rerun()

        explicit_command = parse_explicit_user_command(queued_prompt)
        if explicit_command is not None:
            try:
                action = build_explicit_processing_action(explicit_command, project, state, history)
                execute_authorized_action(
                    queued_prompt, action, project, state, history, engine,
                    routed_by='explicit_user_command')
                st.rerun()
            except Exception as exc:
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f'I recognized an explicit processing command, but the application rejected it during validation: `{exc}`. No processing was run.'})
                st.rerun()
        elif not agent_ready:
            st.session_state.chat_messages.append({
                'role': 'assistant',
                'content': agent_error or 'Agent is not configured.',
            })
            st.rerun()
        else:
            try:
                run_agent_turn(queued_prompt, project, state, history)
                st.rerun()
            except AgentConfigurationError as exc:
                st.session_state.chat_messages.append({'role': 'assistant', 'content': str(exc)})
                st.rerun()
            except Exception as exc:
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f'Agent request failed: `{exc}`',
                })
                st.rerun()

state = project.load_state()
current = Path(state.current_dataset)
metadata = read_su_metadata(current)
with workspace_col:
    selected_step = render_dataset_lineage(state, history)
    view_path = Path(selected_step['output']) if selected_step else current
    view_metadata = read_su_metadata(view_path)

    workspace_tab, processing_tab, qc_tab, history_tab, agent_details_tab, readme_tab = st.tabs(
        ['Workspace', 'Processing', 'QC', 'History', 'Agent Details', 'Readme']
    )
    new_project_requested = False
    with workspace_tab:
        new_project_requested = render_workspace(
            project, state, view_metadata, history, view_path, PREVIEW_TRACES
        )
    with processing_tab:
        render_processing(project, state, engine, metadata, current, PREVIEW_TRACES)
    with qc_tab:
        try:
            render_qc(state, history, selected_step, PREVIEW_TRACES)
        except Exception as exc:
            st.warning('QC page could not be rendered for the selected dataset step.')
            st.code(str(exc))
    with history_tab:
        render_history(state, history, registry)
    with agent_details_tab:
        render_agent_details(
            provider_info=provider_info,
            agent_ready=agent_ready,
            agent_error=agent_error,
            history=history,
        )
    with readme_tab:
        render_readme()

if new_project_requested:
    for key in [
        'project_id', 'upload_signature', 'chat_messages', 'pending_action',
        'pending_user_prompt', 'last_tool_trace', 'last_reflection', 'workspace_page',
        'dataset_lineage_pills', 'dataset_lineage_active_step',
    ]:
        st.session_state.pop(key, None)
    st.rerun()
