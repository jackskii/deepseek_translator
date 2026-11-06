import streamlit as st
from dotenv import load_dotenv
from config.settings import CSS_STYLES
from components.sidebar import render_sidebar
from pages.translator import show_translator_page
from pages.viewer import show_viewer_page
from pages.macro import show_macro_page
from pages.work_selection import show_work_selection_page
from utils.file_operations import delete_work

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


@st.dialog("Confirm delete work")
def confirm_delete_work_dialog(work_name):
    st.write(f"Are you sure you want to delete **{work_name}**?")
    st.write("This will permanently delete the work and all its chapters and terms.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Delete", type="primary", use_container_width=True):
            delete_work(work_name)
            if st.session_state.get("selected_work") == work_name:
                st.session_state.selected_work = None
                st.session_state.current_work = None
            st.session_state.sidebar_view = "works"
            st.session_state.page = "work_selection"
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# Conditional sidebar rendering
if st.session_state.sidebar_view == "works":
    # Show an intro/guide sidebar on the work selection page.
    with st.sidebar:
        st.markdown("## 📖 DeepSeek Translator")
        st.caption("一个简单的日语小说翻译工具")
        st.divider()

        st.markdown("### 快速上手")
        st.markdown(
            "1. 在上方输入框输入作品名，点击 **Create Work**。\n"
            "2. 进入翻译页面，左侧粘贴日文原文。\n"
            "3. 右侧填写章节标题（会作为文件名），点击 **Translate**。\n"
            "4. 翻译完成后在左侧栏点击章节查看或编辑。"
        )

        st.divider()
        st.markdown("### 名词表")
        st.markdown(
            "翻译时模型会自动识别新专有名词（人名、地名、术语）并添加到名词表。\n"
            "你可以在 **Manage Terms** 里手动编辑，手动修改不会被覆盖。"
        )

        st.divider()
        st.markdown("### 切换提供商")
        st.markdown(
            "在 `.env` 里设置 `LLM_PROVIDER` 为 `deepseek` 或 `openrouter`，\n"
            "并填入对应的 API Key 和模型名。"
        )

        st.divider()
        st.caption("按 Ctrl+C 或运行 ./stop.sh 停止服务。")
    show_work_selection_page()
else:
    # Render sidebar for other pages
    with st.sidebar:
        render_sidebar()

    # Top-right delete-work button (available on all work pages)
    _top_left, _top_right = st.columns([12, 1])
    with _top_right:
        if st.button("🗑 Delete Work", use_container_width=True, help="Delete this work"):
            confirm_delete_work_dialog(st.session_state.selected_work)

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
