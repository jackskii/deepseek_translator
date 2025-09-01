import streamlit as st
from dotenv import load_dotenv
from config.settings import CSS_STYLES
from components.sidebar import render_sidebar
from pages.translator import show_translator_page
from pages.viewer import show_viewer_page
from pages.macro import show_macro_page
from pages.work_selection import show_work_selection_page

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(layout="wide", page_title="DeepSeek Translator")

# Hide default Streamlit navigation
hide_navigation_css = """
<style>
[data-testid="stSidebarNav"] {
    display: none;
}
</style>
"""
st.markdown(hide_navigation_css, unsafe_allow_html=True)
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "work_selection"
if "selected_log" not in st.session_state:
    st.session_state.selected_log = None
if "current_work" not in st.session_state:
    st.session_state.current_work = None
if "selected_work" not in st.session_state:
    st.session_state.selected_work = None
if "sidebar_view" not in st.session_state:
    st.session_state.sidebar_view = "works"

# Conditional sidebar rendering
if st.session_state.sidebar_view == "works":
    # Don't render sidebar for work selection page - use full width
    show_work_selection_page()
else:
    # Render sidebar for other pages
    with st.sidebar:
        render_sidebar()
    
    # Display the selected page
    if st.session_state.page == "translator":
        show_translator_page()
    elif st.session_state.page == "viewer" and st.session_state.selected_log and st.session_state.selected_work:
        show_viewer_page(st.session_state.selected_work, st.session_state.selected_log)
    elif st.session_state.page == "macro" and st.session_state.selected_work:
        show_macro_page(st.session_state.selected_work)
    elif st.session_state.sidebar_view == "chapters" and st.session_state.selected_work:
        # Show a default chapter management page when in chapters view but no specific page selected
        st.title(f"📁 {st.session_state.selected_work}")
        st.info("Select an action from the sidebar or choose a chapter to view.")
    else:
        st.session_state.page = "work_selection"
        st.session_state.sidebar_view = "works"
        st.rerun()