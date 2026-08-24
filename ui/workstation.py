import streamlit as st


WORKSTATION_CSS = r"""
<style>
/* V0.6.3: make the LEFT STREAMLIT COLUMN the sticky element.
   Sticky must live at the same layout level as the scrolling workspace column. */

div[data-testid="stHorizontalBlock"]:has(.st-key-agent_panel) {
    align-items: flex-start !important;
    overflow: visible !important;
}

div[data-testid="stColumn"]:has(.st-key-agent_panel) {
    position: sticky !important;
    top: 1.25rem !important;
    align-self: flex-start !important;
    height: calc(100vh - 2.5rem) !important;
    max-height: calc(100vh - 2.5rem) !important;
    overflow: visible !important;
    z-index: 20;
}

/* The panel itself now simply fills its sticky column. */
.st-key-agent_panel {
    position: relative;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 0.75rem;
    padding: 0;
}

.st-key-agent_panel_stack {
    position: absolute;
    inset: 0;
    overflow: hidden;
}

/* Header stays at the top and is intentionally compact. */
.st-key-agent_header {
    position: absolute;
    top: 0.8rem;
    left: 1rem;
    right: 1rem;
    height: 7.5rem;
    overflow: visible;
    z-index: 3;
}

/* Conversation owns the middle and is the only scroll surface on the left. */
.st-key-agent_history {
    position: absolute;
    top: 8.7rem;
    left: 1rem;
    right: 1rem;
    bottom: 13.2rem;
    min-height: 0;
    overflow-y: auto !important;
    overflow-x: hidden;
    overscroll-behavior: contain;
    border-top: 1px solid rgba(128, 128, 128, 0.16);
    border-bottom: 1px solid rgba(128, 128, 128, 0.16);
    padding: 0.55rem 0.2rem 0.8rem 0.2rem;
}

/* Composer stays pinned to the bottom of the viewport-height left column. */
.st-key-agent_composer {
    position: absolute;
    left: 1rem;
    right: 1rem;
    bottom: 0.8rem;
    height: 11.6rem;
    overflow-y: auto;
    z-index: 4;
    padding-top: 0.35rem;
    background: var(--background-color);
}

.st-key-agent_composer textarea {
    min-height: 4.4rem !important;
}

.st-key-workspace_panel {
    min-width: 0;
}

/* On narrow screens Streamlit stacks columns; disable sticky there. */
@media (max-width: 1000px) {
    div[data-testid="stColumn"]:has(.st-key-agent_panel) {
        position: relative !important;
        top: auto !important;
        height: 70vh !important;
        max-height: none !important;
    }

    .st-key-agent_panel {
        height: 100%;
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
