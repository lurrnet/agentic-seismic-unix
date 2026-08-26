import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .spectrum import mean_amplitude_spectrum


def _section_clip(traces, percentile=99.0):
    if traces is None or not traces.size:
        return 1.0
    percentile = float(percentile)
    if percentile <= 0 or percentile > 100:
        raise ValueError('Clip percentile must be greater than 0 and at most 100.')
    clip = float(np.percentile(np.abs(traces), percentile))
    return clip if np.isfinite(clip) and clip > 0 else 1.0


def section_figure(traces, dt_s, title, clip_percentile=99.0, colorscale='Gray'):
    clip = _section_clip(traces, clip_percentile)
    t = np.arange(traces.shape[1]) * dt_s
    fig = go.Figure(
        data=go.Heatmap(
            z=traces.T,
            x=np.arange(traces.shape[0]),
            y=t,
            colorscale=colorscale,
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


def section_comparison_figure(
    before,
    after,
    before_dt_s,
    after_dt_s,
    before_title,
    after_title,
    clip_percentile=99.0,
    colorscale='Gray',
):
    """Render before/after seismic sections with synchronized zoom and independent amplitude scales."""
    before_clip = _section_clip(before, clip_percentile)
    after_clip = _section_clip(after, clip_percentile)
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

    fig.add_trace(
        go.Heatmap(
            z=before.T,
            x=np.arange(before.shape[0]),
            y=before_t,
            colorscale=colorscale,
            zmin=-before_clip,
            zmax=before_clip,
            showscale=True,
            colorbar=dict(
                title=dict(text='Before amplitude', side='top'),
                orientation='h',
                x=0.235,
                xanchor='center',
                y=-0.18,
                yanchor='top',
                len=0.42,
                thickness=14,
            ),
            hovertemplate='Trace %{x}<br>Time %{y:.4f} s<br>Amp %{z:.4g}<extra></extra>',
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Heatmap(
            z=after.T,
            x=np.arange(after.shape[0]),
            y=after_t,
            colorscale=colorscale,
            zmin=-after_clip,
            zmax=after_clip,
            showscale=True,
            colorbar=dict(
                title=dict(text='After amplitude', side='top'),
                orientation='h',
                x=0.765,
                xanchor='center',
                y=-0.18,
                yanchor='top',
                len=0.42,
                thickness=14,
            ),
            hovertemplate='Trace %{x}<br>Time %{y:.4f} s<br>Amp %{z:.4g}<extra></extra>',
        ),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text='Preview trace index', matches='x')
    fig.update_yaxes(title_text='Time (s)', autorange='reversed', matches='y')
    fig.update_layout(
        title=f'Seismic comparison · {float(clip_percentile):g}% amplitude clip',
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
    """Overlay before/after spectra on one shared set of axes."""
    before_f, before_a = mean_amplitude_spectrum(before, before_dt_s)
    after_f, after_a = mean_amplitude_spectrum(after, after_dt_s)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=before_f,
            y=before_a,
            mode='lines',
            name=before_title,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=after_f,
            y=after_a,
            mode='lines',
            name=after_title,
        )
    )
    fig.update_layout(
        title='Mean normalized amplitude spectrum',
        xaxis_title='Frequency (Hz)',
        yaxis_title='Normalized amplitude',
        height=460,
        legend=dict(orientation='h', x=0, y=1.02, xanchor='left', yanchor='bottom'),
    )
    return fig
