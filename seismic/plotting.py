import numpy as np
import plotly.graph_objects as go
from .spectrum import mean_amplitude_spectrum

def section_figure(traces,dt_s,title):
    clip=float(np.percentile(np.abs(traces),99.0)); clip=clip if np.isfinite(clip) and clip>0 else 1.0
    t=np.arange(traces.shape[1])*dt_s
    fig=go.Figure(data=go.Heatmap(z=traces.T,x=np.arange(traces.shape[0]),y=t,colorscale='Gray',zmin=-clip,zmax=clip,colorbar=dict(title='Amp')))
    fig.update_layout(title=title,xaxis_title='Preview trace index',yaxis_title='Time (s)',height=600); fig.update_yaxes(autorange='reversed'); return fig

def spectrum_figure(before,after,dt_s):
    f0,a0=mean_amplitude_spectrum(before,dt_s); fig=go.Figure(); fig.add_trace(go.Scatter(x=f0,y=a0,mode='lines',name='Before'))
    if after is not None:
        f1,a1=mean_amplitude_spectrum(after,dt_s); fig.add_trace(go.Scatter(x=f1,y=a1,mode='lines',name='After'))
    fig.update_layout(title='Mean normalized amplitude spectrum',xaxis_title='Frequency (Hz)',yaxis_title='Normalized amplitude',height=420); return fig
