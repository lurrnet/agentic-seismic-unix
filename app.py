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
from ui.sidebar import render_sidebar
from ui.workspace_page import render_workspace
from ui.processing_page import render_processing
from ui.qc_page import render_qc
from ui.history_page import render_history


VERSION = '0.5'
DATA_ROOT = Path('/data/projects')
TOOLS_DIR = Path('/app/tools')
PREVIEW_TRACES = None

st.set_page_config(
    page_title=f'Seismic Agent V{VERSION}',
    page_icon='〰️',
    layout='wide',
    initial_sidebar_state='expanded',
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
            'Dataset loaded. Ask me to inspect the data, inspect its frequency content, '
            'recommend a bandpass filter, or review the latest filter QC.'
        ),
    }]
    st.session_state.pending_action = None
    st.session_state.last_tool_trace = []
    st.session_state.last_reflection = None


def execute_pending_filter(project, state, history, engine, action):
    current = Path(state.current_dataset)
    if action.get('status') != 'pending_approval':
        raise ValueError('This action is no longer pending approval.')
    if Path(action['input']) != current:
        raise ValueError(
            'The project dataset changed after this proposal was created. '
            'Ask the agent to inspect the current dataset and propose a new filter.'
        )

    out = project.next_output_path('filter')
    rec = engine.run_processing_step(
        state,
        'sufilter',
        current,
        out,
        action['parameters'],
        f"Agent proposal approved by user: {action.get('reason', '')}",
    )
    state.current_step = rec['step_id']
    state.current_dataset = str(out)
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


# Initial state: keep upload in sidebar so the main workspace stays clean.
if 'project_id' not in st.session_state:
    st.title(f'Seismic Agent V{VERSION}')
    st.caption('AI-native Seismic Unix workstation')
    with st.sidebar:
        st.header('Open Project')
        uploaded = st.file_uploader('Upload a SEG-Y file', type=['sgy', 'segy'])
        st.caption('SEG-Y is converted to SU inside the project workspace.')

    if uploaded is None:
        st.info('Upload a `.sgy` or `.segy` file from the sidebar to begin.')
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

# Probe provider once for sidebar status. Manual processing remains usable if unavailable.
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

page, prompt, decision, new_project_requested = render_sidebar(
    state,
    metadata,
    provider_info,
    agent_ready=agent_ready,
    agent_error=agent_error,
)

# Sidebar actions are handled before rendering the main page so the right-hand workspace
# always reflects the current project state after rerun.
if new_project_requested:
    for key in [
        'project_id', 'upload_signature', 'chat_messages', 'pending_action',
        'last_tool_trace', 'last_reflection', 'workspace_page'
    ]:
        st.session_state.pop(key, None)
    st.rerun()

if decision == 'reject':
    st.session_state.pending_action = None
    st.session_state.chat_messages.append({
        'role': 'assistant',
        'content': 'The pending filter proposal was rejected and no processing was run.',
    })
    st.rerun()

if decision == 'approve':
    action = st.session_state.pending_action
    try:
        rec, out = execute_pending_filter(project, state, history, engine, action)
        st.session_state.pending_action = None
        reflection_message = run_reflection_after_filter(project, history, registry, out)
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': reflection_message,
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

# Refresh state in case a sidebar action changed it.
state = project.load_state()
current = Path(state.current_dataset)
metadata = read_su_metadata(current)

st.title(f'Seismic Agent V{VERSION}')
st.caption('Workstation UI · sidebar navigation/chat · full-width seismic visualization')

if page == 'Processing':
    render_processing(project, state, engine, metadata, current, PREVIEW_TRACES)
elif page == 'QC':
    try:
        render_qc(state, history, current, metadata, PREVIEW_TRACES)
    except Exception as exc:
        st.warning('QC page could not be rendered for the current dataset.')
        st.code(str(exc))
elif page == 'History':
    render_history(state, history, registry)
else:
    render_workspace(project, state, metadata, history, current, PREVIEW_TRACES)
