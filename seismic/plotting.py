import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .spectrum import mean_amplitude_spectrum


def _section_clip(*datasets):
    values = [np.abs(data) for data in datasets if data is not None and data.size]
    if not values:
        return 1.0
    clip = float(np.percentile(np.concatenate([value.ravel() for value in values]), 99.0))
    return clip if np.isfinite(clip) and clip > 0 else 1.0


def section_figure(traces, dt_s, title):
    clip = _section_clip(traces)
    t = np.arange(traces.shape[1]) * dt_s
    fig = go.Figure(
        data=go.Heatmap(
            z=traces.T,
            x=np.arange(traces.shape[0]),
            y=t,
            colorscale='Gray',
            zmin=-clip,
            zmax=clip,
            colorbar=dict(title='Amp'),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title='Preview trace index',
        yaxis_title='Time (s)',
        height=600,
    )
    fig.update_yaxes(autorange='reversed')
    return fig


def section_comparison_figure(before, after, before_dt_s, after_dt_s, before_title, after_title):
    """Render before/after seismic sections in one figure with synchronized zoom."""
    clip = _section_clip(before, after)
    before_t = np.arange(before.shape[1]) * before_dt_s
    after_t = np.arange(after.shape[1]) * after_dt_s

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_xaxes=False,
        shared_yaxes=False,
        horizontal_spacing=0.05,
        subplot_titles=(before_title, after_title),
    )

    common_heatmap = dict(
        colorscale='Gray',
        zmin=-clip,
        zmax=clip,
        showscale=False,
        hovertemplate='Trace %{x}<br>Time %{y:.4f} s<br>Amp %{z:.4g}<extra></extra>',
    )
    fig.add_trace(
        go.Heatmap(
            z=before.T,
            x=np.arange(before.shape[0]),
            y=before_t,
            **common_heatmap,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Heatmap(
            z=after.T,
            x=np.arange(after.shape[0]),
            y=after_t,
            **common_heatmap,
        ),
        row=1,
        col=2,
    )

    # A single invisible helper heatmap owns the shared horizontal colorbar.
    fig.add_trace(
        go.Heatmap(
            z=[[ -clip, clip ]],
            x=[0, 1],
            y=[0],
            colorscale='Gray',
            zmin=-clip,
            zmax=clip,
            opacity=0,
            hoverinfo='skip',
            showscale=True,
            colorbar=dict(
                title=dict(text='Amplitude', side='top'),
                orientation='h',
                x=0.5,
                xanchor='center',
                y=-0.18,
                yanchor='top',
                len=0.72,
                thickness=14,
            ),
        ),
        row=1,
        col=1,
    )

    fig.update_xaxes(title_text='Preview trace index', matches='x')
    fig.update_yaxes(title_text='Time (s)', autorange='reversed', matches='y')
    fig.update_layout(
        title='Seismic comparison',
        height=650,
        margin=dict(b=115),
        showlegend=False,
    )
    return fig


def spectrum_figure(before, after, dt_s):
    f0, a0 = mean_amplitude_spectrum(before, dt_s)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=f0, y=a0, mode='lines', name='Before'))
    if after is not None:
        f1, a1 = mean_amplitude_spectrum(after, dt_s)
        fig.add_trace(go.Scatter(x=f1, y=a1, mode='lines', name='After'))
    fig.update_layout(
        title='Mean normalized amplitude spectrum',
        xaxis_title='Frequency (Hz)',
        yaxis_title='Normalized amplitude',
        height=420,
    )
    return fig


def spectrum_comparison_figure(before, after, before_dt_s, after_dt_s, before_title, after_title):
    """Render before/after spectra in one figure with synchronized zoom."""
    before_f, before_a = mean_amplitude_spectrum(before, before_dt_s)
    after_f, after_a = mean_amplitude_spectrum(after, after_dt_s)

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_xaxes=False,
        shared_yaxes=False,
        horizontal_spacing=0.07,
        subplot_titles=(before_title, after_title),
    )
    fig.add_trace(
        go.Scatter(x=before_f, y=before_a, mode='lines', name='Before', showlegend=False),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=after_f, y=after_a, mode='lines', name='After', showlegend=False),
        row=1,
        col=2,
    )
    fig.update_xaxes(title_text='Frequency (Hz)', matches='x')
    fig.update_yaxes(title_text='Normalized amplitude', matches='y')
    fig.update_layout(
        title='Mean normalized amplitude spectrum',
        height=460,
        showlegend=False,
    )
    return fig
