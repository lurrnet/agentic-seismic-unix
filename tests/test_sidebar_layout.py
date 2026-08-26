from ui import workstation


def test_sidebar_layout_uses_native_width(monkeypatch):
    calls = []
    sidebar = object()
    main = object()

    monkeypatch.setattr(workstation.st, 'set_page_config', lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(workstation.st, 'sidebar', sidebar)
    monkeypatch.setattr(workstation.st, 'container', lambda: main)

    agent_container, workspace_container = workstation.workstation_columns()

    assert workstation.APP_VERSION == '0.9.5'
    assert workstation.SIDEBAR_WIDTH == 400
    assert calls == [{
        'page_title': 'Agentic SeismicUnix V0.9.5',
        'initial_sidebar_state': 400,
    }]
    assert agent_container is sidebar
    assert workspace_container is main


def test_sidebar_layout_has_no_custom_css():
    assert not hasattr(workstation, 'WORKSTATION_CSS')
    assert not hasattr(workstation, 'SIDEBAR_CSS')
