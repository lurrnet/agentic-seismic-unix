import streamlit as st


APP_VERSION = '0.9.9'
SIDEBAR_WIDTH = 400


def apply_workstation_styles():
    """Apply only native Streamlit page configuration for the sidebar layout."""
    st.set_page_config(
        page_title=f'Agentic SeismicUnix V{APP_VERSION}',
        initial_sidebar_state=SIDEBAR_WIDTH,
    )


def workstation_columns():
    """Return the native sidebar and the full-width main workspace container.

    The function name is retained so the layout migration does not disturb the
    existing Knowledge Mode / Project Mode state, routing, approval, or
    processing logic in app.py.
    """
    apply_workstation_styles()
    return st.sidebar, st.container()
