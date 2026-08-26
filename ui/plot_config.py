from agent.provider_factory import load_agent_config


DEFAULT_COLORMAPS = [
    'Gray',
    'RdBu',
    'Spectral',
    'Jet',
    'Rainbow',
    'Hot',
    'Phase',
    'Twilight',
    'Balance',
]
DEFAULT_COLORMAP = 'Gray'
DEFAULT_FLIP_POLARITY = False


def load_plotting_config():
    """Return validated plotting UI options with safe built-in fallbacks."""
    try:
        cfg = (load_agent_config().get('plotting') or {})
    except Exception:
        cfg = {}

    colormaps = cfg.get('colormaps') or DEFAULT_COLORMAPS
    colormaps = [str(item).strip() for item in colormaps if str(item).strip()]
    if not colormaps:
        colormaps = list(DEFAULT_COLORMAPS)

    default_colormap = str(cfg.get('default_colormap') or DEFAULT_COLORMAP).strip()
    if default_colormap not in colormaps:
        default_colormap = colormaps[0]

    return {
        'colormaps': colormaps,
        'default_colormap': default_colormap,
        'default_flip_polarity': bool(
            cfg.get('default_flip_polarity', DEFAULT_FLIP_POLARITY)
        ),
    }
