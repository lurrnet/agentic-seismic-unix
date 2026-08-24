import streamlit as st


SIDEBAR_CHAT_CSS = r"""
<style>
/* V0.5.4: make the sidebar behave like a full-height agent chat panel. */
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    height: calc(100vh - 1rem);
    overflow: hidden;
}

section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] > div {
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

/* The marked chat container grows to consume all remaining vertical space. */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:has(#agent-chat-history-marker) {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(#agent-chat-history-marker) {
    min-height: 100%;
}

/* Keep the composer visually anchored at the bottom of the sidebar. */
section[data-testid="stSidebar"] div[data-testid="stChatInput"] {
    position: sticky;
    bottom: 0;
    z-index: 20;
    flex: 0 0 auto;
    padding-top: 0.5rem;
    padding-bottom: 0.25rem;
    background: var(--background-color);
}

/* Diagnostic details should not push the composer away from the bottom. */
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    flex: 0 0 auto;
}
</style>
"""


def apply_sidebar_chat_styles():
    st.markdown(SIDEBAR_CHAT_CSS, unsafe_allow_html=True)
