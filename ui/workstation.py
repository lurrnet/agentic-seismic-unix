import streamlit as st


WORKSTATION_CSS = r"""
<style>
/* V0.6 dual-panel workstation shell. Keys become stable st-key-* classes. */
.st-key-agent_panel {
    height: calc(100vh - 2.5rem);
    min-height: 680px;
    overflow: hidden;
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 0.75rem;
    padding: 0.9rem 1rem 0.8rem 1rem;
}

.st-key-agent_panel > div {
    height: 100%;
}

.st-key-agent_panel .st-key-agent_panel_stack {
    height: 100%;
}

.st-key-agent_panel .st-key-agent_panel_stack > div {
    height: 100%;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: 0.6rem;
}

.st-key-agent_history {
    min-height: 0;
    height: 100%;
    overflow-y: auto;
    border-top: 1px solid rgba(128, 128, 128, 0.16);
    border-bottom: 1px solid rgba(128, 128, 128, 0.16);
    padding: 0.5rem 0.15rem;
}

.st-key-agent_composer {
    align-self: end;
    padding-top: 0.1rem;
}

.st-key-workspace_panel {
    min-width: 0;
}

@media (max-width: 1000px) {
    .st-key-agent_panel {
        height: 70vh;
        min-height: 560px;
    }
}
</style>
"""


def apply_workstation_styles():
    st.markdown(WORKSTATION_CSS, unsafe_allow_html=True)


def workstation_columns():
    """Return the two first-class workstation panels."""
    apply_workstation_styles()
    return st.columns([1, 1], gap='medium')
