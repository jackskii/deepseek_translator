import streamlit as st
from utils.file_operations import get_works, get_log_files, create_work

def render_sidebar():
    """Render the sidebar navigation."""
    works = get_works()
    
    # Only show chapters view in sidebar (works view is now full-width)
    if st.session_state.sidebar_view == "chapters":
        # Back to works button
        if st.button("← Back to Works", use_container_width=True):
            st.session_state.sidebar_view = "works"
            st.session_state.selected_work = None
            st.session_state.page = "work_selection"
            st.rerun()
        
        st.header(f"📁 {st.session_state.selected_work}")
        
        # Action buttons
        if st.button("📝 Translate New Chapter", type="primary", use_container_width=True):
            st.session_state.current_work = st.session_state.selected_work
            st.session_state.page = "translator"
            st.rerun()
        
        if st.button("📚 Manage Terms", use_container_width=True):
            st.session_state.page = "macro"
            st.rerun()
        
        st.divider()
        
        # Show existing chapters
        st.subheader("Chapters")
        
        log_files = get_log_files(st.session_state.selected_work)
        if not log_files:
            st.info("No chapters found. Create your first chapter!")
        else:
            for log_file in log_files:
                chapter_name = log_file.replace('.json', '')
                if st.button(f"📄 {chapter_name}", use_container_width=True, key=f"log_{log_file}"):
                    st.session_state.page = "viewer"
                    st.session_state.selected_log = log_file
                    st.rerun()