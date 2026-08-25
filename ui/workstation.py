import streamlit as st


WORKSTATION_CSS = r"""
<style>
/* Sticky dual-panel workstation. */
div[data-testid="stHorizontalBlock"]:has(.st-key-agent_panel) {
    align-items: flex-start !important;
    overflow: visible !important;
}

div[data-testid="stColumn"]:has(.st-key-agent_panel) {
    position: sticky !important;
    top: 1.25rem !important;
    align-self: flex-start !important;
    overflow: visible !important;
    z-index: 20;
    min-width: 0 !important;
}

.st-key-agent_panel,
.st-key-agent_panel *,
.st-key-agent_history,
.st-key-agent_composer,
.st-key-proposal_card {
    box-sizing: border-box !important;
}

.st-key-agent_panel {
    position: relative;
    height: calc(100vh - 2.5rem);
    min-height: 680px;
    width: 100%;
    max-width: 100%;
    overflow: hidden;
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 0.75rem;
    padding: 0;
}

.st-key-agent_panel_stack {
    position: absolute;
    inset: 0;
    width: 100%;
    max-width: 100%;
    overflow: hidden;
}

.st-key-agent_header {
    position: absolute;
    top: 0.8rem;
    left: 1rem;
    right: 1rem;
    height: 7.5rem;
    min-width: 0;
    max-width: calc(100% - 2rem);
    overflow: visible;
    z-index: 3;
}

.st-key-agent_history {
    position: absolute;
    top: 8.7rem;
    left: 1rem;
    right: 1rem;
    bottom: 13.2rem;
    min-width: 0;
    min-height: 0;
    max-width: calc(100% - 2rem);
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain;
    border-top: 1px solid rgba(128, 128, 128, 0.16);
    border-bottom: 1px solid rgba(128, 128, 128, 0.16);
    padding: 0.55rem 0.35rem 0.8rem 0.2rem;
}

.st-key-agent_history [data-testid="stChatMessage"],
.st-key-agent_history [data-testid="stChatMessageContent"],
.st-key-agent_history .stMarkdown,
.st-key-agent_history pre,
.st-key-agent_history code {
    max-width: 100% !important;
    min-width: 0 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word;
}

.st-key-agent_history pre {
    overflow-x: auto !important;
}

.st-key-agent_composer {
    position: absolute;
    left: 1rem;
    right: 1rem;
    bottom: 0.8rem;
    height: 11.6rem;
    min-width: 0;
    max-width: calc(100% - 2rem);
    overflow-y: auto;
    overflow-x: hidden;
    z-index: 4;
    padding: 0.35rem 0.35rem 0 0;
    background: var(--background-color);
}

/* Pending approval needs more vertical room than the normal composer. */
.st-key-agent_composer:has(.st-key-proposal_card) {
    height: 19rem;
}

.st-key-agent_panel:has(.st-key-proposal_card) .st-key-agent_history {
    bottom: 20.6rem;
}

.st-key-agent_composer form,
.st-key-agent_composer [data-testid="stForm"],
.st-key-agent_composer [data-testid="stTextArea"],
.st-key-agent_composer textarea,
.st-key-agent_composer button,
.st-key-proposal_card,
.st-key-proposal_card [data-testid="stHorizontalBlock"],
.st-key-proposal_card [data-testid="stColumn"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

.st-key-agent_composer textarea {
    min-height: 4.4rem !important;
}

.st-key-proposal_card {
    overflow-x: hidden !important;
    padding-right: 0.1rem;
}

.st-key-workspace_panel {
    min-width: 0;
}

@media (max-width: 1000px) {
    div[data-testid="stColumn"]:has(.st-key-agent_panel) {
        position: relative !important;
        top: auto !important;
    }

    .st-key-agent_panel {
        height: 70vh;
        min-height: 600px;
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
