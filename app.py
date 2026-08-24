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
from seismic.io import read_su_metadata, get_surange, load_preview_traces
from seismic.qc import compare_filter_result
from seismic.plotting import section_figure, spectrum_figure


DATA_ROOT = Path('/data/projects')
TOOLS_DIR = Path('/app/tools')
PREVIEW_TRACES = None

st.set_page_config(page_title='Seismic Agent V0.4', page_icon='〰️', layout='wide')
st.title('Seismic Agent V0.4')
st.caption('Dual-provider Chat Agent + approval-gated SU processing + automatic QC reflection')

registry = ToolRegistry(TOOLS_DIR)
executor = SUExecutor(registry)


def get_reflection_config():
    try:
        return (load_agent_config().get('reflection') or {})
    except Exception:
        return {}


def create_project(uploaded):
    p = Project(DATA_ROOT)
    raw = p.raw_dir / Path(uploaded.name).name
    su = p.data_dir / 'step000_import.su'
    raw.write_bytes(uploaded.getbuffer())
    segy_to_su(raw, su)
    m = read_su_metadata(su)
    s = p.initialize(str(raw), str(su), m.to_dict())
    HistoryStore(p.history_dir / 'workflow.json').append({
        'step_id': 0,
        'parent_step': None,
        'tool': 'segyread|segyclean',
        'input': str(raw),
        'output': str(su),
        'parameters': {},
        'reason': 'SEG-Y import',
        'status': 'success',
    })
    return p, s


def reset_chat_for_project():
    st.session_state.chat_messages = [{
        'role': 'assistant',
        'content': (
            'Dataset loaded. You can ask me to inspect the data, inspect its frequency content, '
            'recommend a bandpass filter, or review the latest filter QC.'
        ),
    }]
    st.session_state.pending_action = None
    st.session_state.last_tool_trace = []
    st.session_state.last_reflection = None


def execute_pending_filter(p, s, hist, eng, action):
    current = Path(s.current_dataset)
    if action.get('status') != 'pending_approval':
        raise ValueError('This action is no longer pending approval.')
    if Path(action['input']) != current:
        raise ValueError(
            'The project dataset changed after this proposal was created. '
            'Ask the agent to inspect the current dataset and propose a new filter.'
        )

    out = p.next_output_path('filter')
    rec = eng.run_processing_step(
        s,
        'sufilter',
        current,
        out,
        action['parameters'],
        f"Agent proposal approved by user: {action.get('reason', '')}",
    )
    s.current_step = rec['step_id']
    s.current_dataset = str(out)
    p.save_state(s)
    return rec, out


u = st.file_uploader('Upload a SEG-Y file', type=['sgy', 'segy'])
if u is None:
    st.info('Upload a .sgy or .segy file to begin.')
    st.stop()

sig = f'{u.name}:{u.size}'
if st.session_state.get('upload_signature') != sig:
    try:
        with st.spinner('Creating project and converting SEG-Y to SU...'):
            p, s = create_project(u)
        st.session_state.upload_signature = sig
        st.session_state.project_id = p.project_id
        reset_chat_for_project()
    except Exception as e:
        st.error('Failed to initialize the project.')
        st.code(str(e))
        st.stop()

p = Project(DATA_ROOT, st.session_state.project_id)
s = p.load_state()
hist = HistoryStore(p.history_dir / 'workflow.json')
eng = WorkflowEngine(executor, hist)
current = Path(s.current_dataset)
m = read_su_metadata(current)

if 'chat_messages' not in st.session_state:
    reset_chat_for_project()
if 'pending_action' not in st.session_state:
    st.session_state.pending_action = None
if 'last_tool_trace' not in st.session_state:
    st.session_state.last_tool_trace = []
if 'last_reflection' not in st.session_state:
    st.session_state.last_reflection = None

chat_tab, process_tab, qc_tab, workflow_tab, history_tab = st.tabs(
    ['Chat Agent', 'Process', 'QC', 'Workflow', 'History']
)

with chat_tab:
    left, right = st.columns([3, 2])

    with left:
        st.subheader('Seismic Chat Agent')

        agent_ready = True
        agent_error = None
        try:
            cfg = load_agent_config()
            probe_agent = SeismicAgent()
            info = probe_agent.provider_info
            provider_label = 'OpenClaw (local)' if info['provider'] == 'openclaw' else 'OpenAI API'
            st.caption(f"Provider: {provider_label} · Model: {info.get('model')}")
            if info['provider'] == 'openclaw':
                st.caption(f"Gateway: {info.get('base_url')}")
        except AgentConfigurationError as exc:
            agent_ready = False
            agent_error = str(exc)
            st.warning(
                f'Chat Agent is not configured: {agent_error} '
                'The manual Process/QC tabs still work without an LLM.'
            )

        for message in st.session_state.chat_messages:
            with st.chat_message(message['role']):
                st.markdown(message['content'])

        prompt = st.chat_input(
            'Ask about the dataset or request a bandpass recommendation...',
            disabled=not agent_ready,
        )

        if prompt:
            prior_history = list(st.session_state.chat_messages)
            st.session_state.chat_messages.append({'role': 'user', 'content': prompt})

            try:
                toolkit = AgentToolkit(p, s, hist, registry, preview_traces=200)
                agent = SeismicAgent()
                with st.spinner('Agent is inspecting the project...'):
                    result = agent.run_turn(prompt, prior_history, toolkit)

                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': result['text'],
                })
                st.session_state.last_tool_trace = result['tool_trace']
                if result['pending_action'] is not None:
                    st.session_state.pending_action = result['pending_action']
                st.rerun()

            except AgentConfigurationError as e:
                st.error(str(e))
            except Exception as e:
                st.error('Agent request failed.')
                st.code(str(e))

    with right:
        st.subheader('Current Project')
        c1, c2 = st.columns(2)
        c1.metric('dt', f'{m.dt_us:,} µs')
        c2.metric('Nyquist', f'{m.nyquist_hz:.2f} Hz')
        c3, c4 = st.columns(2)
        c3.metric('Samples', f'{m.ns:,}')
        c4.metric('Step', f'{s.current_step}')
        st.caption(Path(s.current_dataset).name)

        action = st.session_state.pending_action
        if action:
            st.divider()
            st.subheader('Pending Approval')
            params = action['parameters']
            st.markdown(
                f"**sufilter:** `{params['f1']:g} - {params['f2']:g} - "
                f"{params['f3']:g} - {params['f4']:g} Hz`"
            )
            st.caption(action.get('reason', ''))

            approve_col, reject_col = st.columns(2)
            if approve_col.button('Approve & Run sufilter', type='primary', use_container_width=True):
                try:
                    with st.spinner('Running approved sufilter...'):
                        rec, out = execute_pending_filter(p, s, hist, eng, action)
                    st.session_state.pending_action = None

                    # v0.4: deterministic QC + provider reflection can run automatically
                    # after an agent-approved filter. A suggested adjustment is still
                    # approval-gated and is never executed here.
                    reflection_message = (
                        f"Approved filter executed successfully as `{out.name}`."
                    )
                    reflection_cfg = get_reflection_config()
                    auto_reflect = bool(
                        reflection_cfg.get('enabled', True)
                        and reflection_cfg.get('auto_after_agent_filter', True)
                    )
                    try:
                        if not auto_reflect:
                            raise RuntimeError('__REFLECTION_DISABLED__')
                        refreshed_state = p.load_state()
                        reflection_toolkit = AgentToolkit(
                            p, refreshed_state, hist, registry, preview_traces=int(reflection_cfg.get('max_preview_traces', 200))
                        )
                        reflection_agent = SeismicAgent()
                        with st.spinner('Running automatic QC reflection...'):
                            reflection = reflection_agent.review_latest_filter(
                                reflection_toolkit,
                                max_traces=int(reflection_cfg.get('max_preview_traces', 200)),
                            )
                        st.session_state.last_reflection = reflection
                        if reflection.get('pending_action') is not None:
                            st.session_state.pending_action = reflection['pending_action']
                        reflection_message += "\n\n" + reflection['text']

                        hist.append({
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
                    except Exception as reflection_exc:
                        if str(reflection_exc) == '__REFLECTION_DISABLED__':
                            st.session_state.last_reflection = None
                            reflection_message += (
                                "\n\nAutomatic QC reflection is disabled in `config/agent.yaml`."
                            )
                        else:
                            # The SU processing result remains valid even if the LLM
                            # reflection fails. Do not roll back successful processing.
                            st.session_state.last_reflection = {
                                'status': 'error',
                                'decision': 'review_only',
                                'error': str(reflection_exc),
                            }
                            reflection_message += (
                                "\n\nThe filter completed, but automatic QC reflection failed: "
                                f"`{reflection_exc}`. The QC tab remains available."
                            )

                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': reflection_message,
                    })
                    st.rerun()
                except Exception as e:
                    st.error('Approved processing failed.')
                    st.code(str(e))

            if reject_col.button('Reject', use_container_width=True):
                st.session_state.pending_action = None
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': 'The pending filter proposal was rejected and no processing was run.',
                })
                st.rerun()

        if st.session_state.last_tool_trace:
            with st.expander('Last agent tool trace'):
                st.json(st.session_state.last_tool_trace)

        if st.session_state.last_reflection:
            with st.expander('Latest QC reflection', expanded=True):
                reflection = st.session_state.last_reflection
                st.markdown(f"**Decision:** {str(reflection.get('decision', 'review_only')).upper()}")
                if reflection.get('confidence'):
                    st.caption(f"Confidence: {reflection.get('confidence')}")
                if reflection.get('qc'):
                    st.json(reflection.get('qc'))
                if reflection.get('error'):
                    st.error(reflection.get('error'))

with process_tab:
    a, b, c, d = st.columns(4)
    a.metric('Samples / trace', f'{m.ns:,}')
    b.metric('Sample interval', f'{m.dt_us:,} µs')
    c.metric('Nyquist', f'{m.nyquist_hz:.2f} Hz')
    d.metric('Estimated traces', f'{m.estimated_trace_count:,}')

    with st.expander('Raw SU header range (surange)'):
        try:
            st.code(get_surange(current))
        except Exception as e:
            st.warning(str(e))

    st.subheader('Manual Bandpass Filter')
    df4 = min(75.0, m.nyquist_hz * .90)
    df3 = min(60.0, df4 * .80)
    df2 = min(10.0, df3 * .50)
    df1 = min(5.0, df2 * .50)
    cs = st.columns(4)
    with cs[0]:
        f1 = st.number_input('F1 (Hz)', min_value=0.0, value=float(df1))
    with cs[1]:
        f2 = st.number_input('F2 (Hz)', min_value=0.0, value=float(df2))
    with cs[2]:
        f3 = st.number_input('F3 (Hz)', min_value=0.0, value=float(df3))
    with cs[3]:
        f4 = st.number_input('F4 (Hz)', min_value=0.0, value=float(df4))

    st.caption('Manual execution uses the same Tool Registry -> Validator -> Workflow Engine path as agent-approved processing.')
    if st.button('Apply sufilter manually'):
        out = p.next_output_path('filter')
        try:
            rec = eng.run_processing_step(
                s,
                'sufilter',
                current,
                out,
                {'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4},
                'User-approved manual bandpass filter',
            )
            s.current_step = rec['step_id']
            s.current_dataset = str(out)
            p.save_state(s)
            st.session_state.pending_action = None
            st.success(f'Created {out.name}')
            st.rerun()
        except Exception as e:
            st.error('Filtering failed.')
            st.code(str(e))

with qc_tab:
    recs = hist.list()
    filters = [r for r in recs if r.get('tool') == 'sufilter' and r.get('status') == 'success']
    try:
        if not filters:
            tr = load_preview_traces(current, m, PREVIEW_TRACES)
            st.plotly_chart(section_figure(tr, m.dt_s, 'Current dataset'), use_container_width=True)
            st.plotly_chart(spectrum_figure(tr, None, m.dt_s), use_container_width=True)
            st.info('Apply a filter to enable before/after QC.')
        else:
            r = filters[-1]
            bp = Path(r['input'])
            ap = Path(r['output'])
            bm = read_su_metadata(bp)
            am = read_su_metadata(ap)
            before = load_preview_traces(bp, bm, PREVIEW_TRACES)
            after = load_preview_traces(ap, am, PREVIEW_TRACES)
            l, rr = st.columns(2)
            with l:
                st.plotly_chart(section_figure(before, bm.dt_s, 'Before'), use_container_width=True)
            with rr:
                st.plotly_chart(section_figure(after, am.dt_s, 'After'), use_container_width=True)
            st.plotly_chart(spectrum_figure(before, after, bm.dt_s), use_container_width=True)
            pp = r['parameters']
            qc = compare_filter_result(before, after, bm.dt_s, float(pp['f2']), float(pp['f3']), float(pp['f4']))
            q1, q2, q3 = st.columns(3)
            q1.metric('Signal retention', f'{qc["signal_retention"]*100:.1f}%')
            q2.metric('High-frequency reduction', f'{qc["high_frequency_reduction"]*100:.1f}%')
            q3.metric('RMS ratio', f'{qc["rms_ratio"]:.3f}')
    except Exception as e:
        st.warning('QC preview could not be generated for the current dataset.')
        st.code(str(e))

with workflow_tab:
    st.code(
        'User chat\n'
        '   ->\n'
        'SeismicAgent\n'
        '   ->\n'
        'Read-only inspection tools (auto)\n'
        '   ->\n'
        'Bandpass proposal\n'
        '   ->\n'
        'Human approval\n'
        '   ->\n'
        'Tool Registry\n'
        '   ->\n'
        'Validator\n'
        '   ->\n'
        'Workflow Engine\n'
        '   ->\n'
        'SU Executor\n'
        '   ->\n'
        'sufilter\n'
        '   ->\n'
        'Deterministic QC metrics\n'
        '   ->\n'
        'Agent reflection\n'
        '   ->\n'
        'Accept OR adjusted proposal\n'
        '   ->\n'
        'Human approval if adjusted\n'
        '   ->\n'
        'History'
    )
    st.markdown('**Registered processing/tool specs**')
    st.json(registry.list_tools())

with history_tab:
    recs = hist.list()
    for r in reversed(recs):
        with st.expander(f'Step {r["step_id"]}: {r["tool"]}'):
            st.json(r)
    st.markdown('**Project state**')
    st.json(s.to_dict())
