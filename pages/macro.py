import streamlit as st
from utils.macro_utils import load_macro, save_macro


def _key(prefix: str, term: str) -> str:
    """Build a stable widget key from a term so it doesn't reshuffle when
    rows are added/removed (index-based keys cause the wrong row to be
    affected after a delete)."""
    # Use abs(hash(...)) for a stable, filesystem-safe suffix.
    return f"{prefix}_{abs(hash(term))}"


def show_macro_page(work_name):
    """Displays the macro management interface."""
    st.subheader(f"📚 Macro - {work_name}")

    st.caption(
        "新名词会在翻译时自动添加到此处；你在这里的手动修改是最终版本，"
        "模型之后不会覆盖已有条目。"
    )

    macro_data = load_macro(work_name)

    # --- Add new term --------------------------------------------------------
    st.markdown("### Add New Term")
    col1, col2, col3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    with col1:
        new_original = st.text_input("Original Term (Japanese)", key="new_original")
    with col2:
        new_translation = st.text_input("Translation (Chinese)", key="new_translation")
    with col3:
        if st.button("Add", type="primary", use_container_width=True):
            if new_original.strip() and new_translation.strip():
                macro_data[new_original.strip()] = new_translation.strip()
                save_macro(work_name, macro_data)
                st.success("Term added!")
                st.rerun()
            else:
                st.warning("Please fill in both fields.")

    st.divider()

    # --- Current terms -------------------------------------------------------
    st.markdown("### Current Terms")
    if not macro_data:
        st.info("No terms defined yet. Add some terms above.")
        return

    for original, translation in macro_data.items():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1], vertical_alignment="bottom")

        with col1:
            edited_original = st.text_input(
                "Original", value=original, key=_key("orig", original)
            )
        with col2:
            edited_translation = st.text_input(
                "Translation", value=translation, key=_key("trans", original)
            )
        with col3:
            if st.button("Save", key=_key("save", original), use_container_width=True):
                eo = edited_original.strip()
                et = edited_translation.strip()
                if not eo or not et:
                    st.warning("Both fields must be filled to save.")
                else:
                    del macro_data[original]
                    macro_data[eo] = et
                    save_macro(work_name, macro_data)
                    st.success("Term updated!")
                    st.rerun()
        with col4:
            if st.button(
                "Delete",
                key=_key("del", original),
                use_container_width=True,
                type="secondary",
            ):
                # Always delete by the ORIGINAL (file) key, not the edited
                # value, so the right row is removed regardless of any
                # un-saved edits in the text inputs.
                macro_data.pop(original, None)
                save_macro(work_name, macro_data)
                st.success("Term deleted!")
                st.rerun()
