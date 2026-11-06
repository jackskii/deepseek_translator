import streamlit as st
from utils.file_operations import get_works, create_work

def show_work_selection_page():
    """Displays the full-width work selection page."""
    # Create new work section
    new_work_name = st.text_input("Work Name:", label_visibility="hidden",placeholder="Enter work name here...")

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Create Work", type="primary", use_container_width=True) and new_work_name.strip():
            create_work(new_work_name.strip())
            st.session_state.current_work = new_work_name.strip()
            st.session_state.selected_work = new_work_name.strip()
            st.session_state.sidebar_view = "chapters"
            st.session_state.page = "translator"
            st.rerun()

    st.divider()

    # Search function
    search_term = st.text_input("Search work titles:", placeholder="Type to search...")

    st.divider()

    # Display works
    works = get_works()

    if not works:
        st.info("No works found. Create your first work above!")
        return

    # Filter works based on search term
    if search_term:
        filtered_works = [work for work in works if search_term.lower() in work.lower()]
    else:
        filtered_works = works

    if not filtered_works:
        st.info(f"No works found matching '{search_term}'")
        return

    # Display works in 2 columns (bigger cards)
    n_cols = 2
    rows = (len(filtered_works) + n_cols - 1) // n_cols

    for row in range(rows):
        cols = st.columns(n_cols)
        for col_idx in range(n_cols):
            work_idx = row * n_cols + col_idx
            if work_idx < len(filtered_works):
                work = filtered_works[work_idx]
                with cols[col_idx]:
                    display_work = work if len(work) <= 25 else work[:25] + "..."

                    if st.button(
                        f"📁 {display_work}",
                        key=f"work_select_{work}",
                        use_container_width=True,
                        help=work,
                    ):
                        st.session_state.selected_work = work
                        st.session_state.sidebar_view = "chapters"
                        st.rerun()
