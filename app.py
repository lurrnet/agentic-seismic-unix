from pathlib import Path
import streamlit as st
from project.project import Project
from workflow.history import HistoryStore
from workflow.engine import WorkflowEngine
from su.registry import ToolRegistry
from su.executor import SUExecutor
from su.importer import segy_to_su
from seismic.io import read_su_metadata,get_surange,load_preview_traces
from seismic.qc import compare_filter_result
from seismic.plotting import section_figure,spectrum_figure
DATA_ROOT=Path('/data/projects'); TOOLS_DIR=Path('/app/tools'); PREVIEW_TRACES=None
st.set_page_config(page_title='Seismic Agent V0.2',page_icon='〰️',layout='wide')
st.title('Seismic Agent V0.2'); st.caption('Tool Registry + Validator + Workflow Engine + Project State + History')
registry=ToolRegistry(TOOLS_DIR); executor=SUExecutor(registry)

def create_project(uploaded):
    p=Project(DATA_ROOT); raw=p.raw_dir/Path(uploaded.name).name; su=p.data_dir/'step000_import.su'; raw.write_bytes(uploaded.getbuffer()); segy_to_su(raw,su); m=read_su_metadata(su)
    s=p.initialize(str(raw),str(su),m.to_dict()); HistoryStore(p.history_dir/'workflow.json').append({'step_id':0,'parent_step':None,'tool':'segyread|segyclean','input':str(raw),'output':str(su),'parameters':{},'reason':'SEG-Y import','status':'success'}); return p,s

u=st.file_uploader('Upload a SEG-Y file',type=['sgy','segy'])
if u is None: st.info('Upload a .sgy or .segy file to begin.'); st.stop()
sig=f'{u.name}:{u.size}'
if st.session_state.get('upload_signature') != sig:
    try:
        with st.spinner('Creating project and converting SEG-Y to SU...'): p,s=create_project(u)
        st.session_state.upload_signature=sig; st.session_state.project_id=p.project_id
    except Exception as e: st.error('Failed to initialize the project.'); st.code(str(e)); st.stop()
p=Project(DATA_ROOT,st.session_state.project_id); s=p.load_state(); hist=HistoryStore(p.history_dir/'workflow.json'); eng=WorkflowEngine(executor,hist); current=Path(s.current_dataset); m=read_su_metadata(current)
t1,t2,t3,t4=st.tabs(['Process','QC','Workflow','History'])
with t1:
    a,b,c,d=st.columns(4); a.metric('Samples / trace',f'{m.ns:,}'); b.metric('Sample interval',f'{m.dt_us:,} µs'); c.metric('Nyquist',f'{m.nyquist_hz:.2f} Hz'); d.metric('Estimated traces',f'{m.estimated_trace_count:,}')
    with st.expander('Raw SU header range (surange)'):
        try: st.code(get_surange(current))
        except Exception as e: st.warning(str(e))
    st.subheader('Bandpass Filter')
    df4=min(75.0,m.nyquist_hz*.90); df3=min(60.0,df4*.80); df2=min(10.0,df3*.50); df1=min(5.0,df2*.50)
    cs=st.columns(4)
    with cs[0]: f1=st.number_input('F1 (Hz)',min_value=0.0,value=float(df1))
    with cs[1]: f2=st.number_input('F2 (Hz)',min_value=0.0,value=float(df2))
    with cs[2]: f3=st.number_input('F3 (Hz)',min_value=0.0,value=float(df3))
    with cs[3]: f4=st.number_input('F4 (Hz)',min_value=0.0,value=float(df4))
    st.caption('Execution is resolved through tools/sufilter.yaml and the Workflow Engine.')
    if st.button('Apply sufilter',type='primary'):
        out=p.next_output_path('filter')
        try:
            rec=eng.run_processing_step(s,'sufilter',current,out,{'f1':f1,'f2':f2,'f3':f3,'f4':f4},'User-approved bandpass filter'); s.current_step=rec['step_id']; s.current_dataset=str(out); p.save_state(s); st.success(f'Created {out.name}'); st.rerun()
        except Exception as e: st.error('Filtering failed.'); st.code(str(e))
with t2:
    recs=hist.list(); filters=[r for r in recs if r.get('tool')=='sufilter']
    try:
        if not filters:
            tr=load_preview_traces(current,m,PREVIEW_TRACES); st.plotly_chart(section_figure(tr,m.dt_s,'Current dataset'),use_container_width=True); st.plotly_chart(spectrum_figure(tr,None,m.dt_s),use_container_width=True); st.info('Apply a filter to enable before/after QC.')
        else:
            r=filters[-1]; bp=Path(r['input']); ap=Path(r['output']); bm=read_su_metadata(bp); am=read_su_metadata(ap); before=load_preview_traces(bp,bm,PREVIEW_TRACES); after=load_preview_traces(ap,am,PREVIEW_TRACES)
            l,rr=st.columns(2)
            with l: st.plotly_chart(section_figure(before,bm.dt_s,'Before'),use_container_width=True)
            with rr: st.plotly_chart(section_figure(after,am.dt_s,'After'),use_container_width=True)
            st.plotly_chart(spectrum_figure(before,after,bm.dt_s),use_container_width=True)
            pp=r['parameters']; qc=compare_filter_result(before,after,bm.dt_s,float(pp['f2']),float(pp['f3']),float(pp['f4'])); q1,q2,q3=st.columns(3); q1.metric('Signal retention',f'{qc["signal_retention"]*100:.1f}%'); q2.metric('High-frequency reduction',f'{qc["high_frequency_reduction"]*100:.1f}%'); q3.metric('RMS ratio',f'{qc["rms_ratio"]:.3f}')
    except Exception as e:
        st.warning('QC preview could not be generated for the current dataset.')
        st.code(str(e))
with t3:
    st.code("SEG-Y Import\\n   ->\\nInspect metadata / spectrum\\n   ->\\nBandpass proposal\\n   ->\\nUser approval\\n   ->\\nTool Registry\\n   ->\\nValidator\\n   ->\\nWorkflow Engine\\n   ->\\nSU Executor\\n   ->\\nsufilter\\n   ->\\nQC / History"); st.markdown('**Registered tools**'); st.json(registry.list_tools())
with t4:
    recs=hist.list()
    for r in reversed(recs):
        with st.expander(f'Step {r["step_id"]}: {r["tool"]}'): st.json(r)
    st.markdown('**Project state**'); st.json(s.to_dict())
