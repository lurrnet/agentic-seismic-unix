from pathlib import Path
import streamlit as st

from agent.seismic_agent import SeismicAgent, AgentConfigurationError
from agent.provider_factory import load_agent_config
from agent.toolkit import AgentToolkit
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


VERSION = '0.7.0'
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
        'step_id': 0,
        'parent_step': None,
        'tool': 'segyread|segyclean',
        'input': str(raw),
        'output': str(su),
        'parameters': {},
        'reason': 'SEG-Y import',
        'status': 'success',
    })
    return project, state


def reset_chat_for_project():
    st.session_state.chat_messages = [{
        'role': 'assistant',
        'content': (
            'Dataset loaded. I can inspect sampling, frequency content, trace headers, '
            'and amplitude statistics; propose bandpass filtering, gain, AGC, or trace '
            'selection; and review the latest bandpass QC.'
        ),
    }]
    st.session_state.pending_action = None
    st.session_state.last_tool_trace = []
    st.session_state.last_reflection = None


def execute_pending_action(project, state, history, engine, action):
    current = Path(state.current_dataset)
    if action.get('status') != 'pending_approval':
        raise ValueError('This action is no longer pending approval.')
    if Path(action['input']) != current:
        raise ValueError(
            'The project dataset changed after this proposal was created. '
            'Ask the agent to inspect the current dataset and create a new proposal.'
        )

    tool_name = action['tool']
    operation = action.get('operation') or tool_name
    out = project.next_output_path(operation)
    rec = engine.run_processing_step(
        state,
        tool_name,
        current,
        out,
        action['parameters'],
        f"Agent proposal approved by user: {action.get('reason', '')}",
    )
    state.current_step = rec['step_id']
    state.current_dataset = str(out)
    state.metadata = read_su_metadata(out).to_dict()
    project.save_state(state)
    return rec, out


def run_reflection_after_filter(project, history, registry, out):
    reflection_message = f'Approved filter executed successfully as `{out.name}`.'
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
        toolkit = AgentToolkit(
            project,
            refreshed_state,
            history,
            registry,
            preview_traces=max_traces,
        )
        agent = SeismicAgent()
        reflection = agent.review_latest_filter(toolkit, max_traces=max_traces)
        st.session_state.last_reflection = reflection
        if reflection.get('pending_action') is not None:
            st.session_state.pending_action = reflection['pending_action']

        history.append({
            'step_id': refreshed_state.current_step,
            'parent_step': refreshed_state.current_step,
            'tool': 'qc_reflection',
            'input': str(out),
            'output': None,
            'parameters': {},
            'reason': reflection.get('reason', ''),
            'status': reflection.get('status', 'success'),
            'decision': reflection.get('decision'),
            'confidence': reflection.get('confidence'),
            'qc': reflection.get('qc'),
            'provider': reflection.get('provider'),
            'model': reflection.get('model'),
        })
        return reflection_message + '\n\n' + reflection['text']

    except Exception as exc:
        st.session_state.last_reflection = {
            'status': 'error',
            'decision': 'review_only',
            'error': str(exc),
        }
        return (
            reflection_message
            + '\n\nThe filter completed, but automatic QC reflection failed: '
            + f'`{exc}`. The QC page remains available.'
        )


def processing_success_message(action, out):
    display_name = action.get('display_name') or action.get('tool', 'Processing')
    params = action.get('parameters') or {}
    return (
        f'Approved **{display_name}** executed successfully as `{out.name}`.\n\n'
        f'Parameters: `{params}`. The new dataset is now the current project step.'
    )


def run_agent_turn(prompt, project, state, history):
    prior_history = list(st.session_state.chat_messages)
    st.session_state.chat_messages.append({'role': 'user', 'content': prompt})

    toolkit = AgentToolkit(project, state, history, registry, preview_traces=200)
    agent = SeismicAgent()
    result = agent.run_turn(prompt, prior_history, toolkit)

    st.session_state.chat_messages.append({
        'role': 'assistant',
        'content': result['text'],
    })
    st.session_state.last_tool_trace = result['tool_trace']
    if result['pending_action'] is not None:
        st.session_state.pending_action = result['pending_action']


# Initial state uses the same dual-panel workstation shell as the loaded state.
if 'project_id' not in st.session_state:
    agent_col, workspace_col = workstation_columns()

    with agent_col:
        render_agent_panel(
            provider_info=None,
            agent_ready=False,
            dataset_loaded=False,
        )

    with workspace_col:
        st.title(f'Agentic SeismicUnix V{VERSION}')
        st.caption('AI-native Seismic Unix workstation')
        st.subheader('Open Project')
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
    ('chat_messages', []),
    ('pending_action', None),
    ('last_tool_trace', []),
    ('last_reflection', None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

agent_ready = True
agent_error = None
provider_info = None
try:
    provider_info = SeismicAgent().provider_info
except AgentConfigurationError as exc:
    agent_ready = False
    agent_error = str(exc)
except Exception as exc:
    agent_ready = False
    agent_error = str(exc)

agent_col, workspace_col = workstation_columns()

with agent_col:
    prompt, decision = render_agent_panel(
        provider_info,
        agent_ready=agent_ready,
        agent_error=agent_error,
        dataset_loaded=True,
    )

if decision == 'reject':
    action = st.session_state.pending_action or {}
    display_name = action.get('display_name') or action.get('tool', 'processing')
    st.session_state.pending_action = None
    st.session_state.chat_messages.append({
        'role': 'assistant',
        'content': f'The pending **{display_name}** proposal was rejected and no processing was run.',
    })
    st.rerun()

if decision == 'approve':
    action = st.session_state.pending_action
    try:
        rec, out = execute_pending_action(project, state, history, engine, action)
        st.session_state.pending_action = None

        if action.get('tool') == 'sufilter':
            message = run_reflection_after_filter(project, history, registry, out)
        else:
            st.session_state.last_reflection = None
            message = processing_success_message(action, out)

        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': message,
        })
        st.rerun()
    except Exception as exc:
        st.error('Approved processing failed.')
        st.code(str(exc))

if prompt:
    if not agent_ready:
        st.error(agent_error or 'Agent is not configured.')
    else:
        try:
            run_agent_turn(prompt, project, state, history)
            st.rerun()
        except AgentConfigurationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error('Agent request failed.')
            st.code(str(exc))

state = project.load_state()
current = Path(state.current_dataset)
metadata = read_su_metadata(current)

with workspace_col:
    workspace_tab, processing_tab, qc_tab, history_tab = st.tabs(
        ['Workspace', 'Processing', 'QC', 'History']
    )

    new_project_requested = False
    with workspace_tab:
        new_project_requested = render_workspace(
            project, state, metadata, history, current, PREVIEW_TRACES
        )

    with processing_tab:
        render_processing(project, state, engine, metadata, current, PREVIEW_TRACES)

    with qc_tab:
        try:
            render_qc(state, history, current, metadata, PREVIEW_TRACES)
        except Exception as exc:
            st.warning('QC page could not be rendered for the current dataset.')
            st.code(str(exc))

    with history_tab:
        render_history(state, history, registry)

if new_project_requested:
    for key in [
        'project_id', 'upload_signature', 'chat_messages', 'pending_action',
        'last_tool_trace', 'last_reflection', 'workspace_page'
    ]:
        st.session_state.pop(key, None)
    st.rerun()
