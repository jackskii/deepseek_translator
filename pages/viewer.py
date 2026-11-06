import streamlit as st
import os
import json
from config.settings import BASE_LOG_DIR

def show_viewer_page(work_name, log_file):
    """Displays the log viewer and editor."""
    display_filename = log_file.replace('.json', '')
    filepath = os.path.join(BASE_LOG_DIR, work_name, log_file)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    except Exception as e:
        st.error(f"Could not read log file: {e}")
        return

    # --- Top: chapter name + rename field ------------------------------------
    st.subheader(f"📄 {display_filename}")
    new_filename = st.text_input(
        "文件重命名",
        value=display_filename,
        label_visibility="collapsed",
        placeholder="文件重命名",
    )

    st.divider()

    # --- Body: original + translation side by side --------------------------
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h5>原文</h5>", unsafe_allow_html=True)
        edited_original = st.text_area(
            "原文",
            label_visibility="collapsed",
            value=log_data.get("original", ""),
            height=600,
        )

    with col2:
        st.markdown("<h5>翻译</h5>", unsafe_allow_html=True)
        edited_translation = st.text_area(
            "翻译",
            label_visibility="collapsed",
            value=log_data.get("translated", ""),
            height=600,
        )

    st.divider()

    # --- Bottom: save / delete ----------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", type="primary", use_container_width=True):
            log_data["original"] = edited_original
            log_data["translated"] = edited_translation
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=4)

            new_filename_with_ext = (new_filename or display_filename) + '.json'
            if new_filename_with_ext != log_file:
                new_filepath = os.path.join(BASE_LOG_DIR, work_name, new_filename_with_ext)
                os.rename(filepath, new_filepath)
                st.session_state.selected_log = new_filename_with_ext

            st.success("Changes saved successfully!")
            st.rerun()

    with col2:
        if st.button("Delete File", type="secondary", use_container_width=True):
            try:
                os.remove(filepath)
                st.success(f"File {log_file} deleted successfully!")
                st.session_state.page = "translator"
                st.session_state.selected_log = None
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting file: {e}")
