import streamlit as st
from utils.macro_utils import load_macro, save_macro

def show_macro_page(work_name):
    """Displays the macro management interface."""
    st.subheader(f"📚 Macro - {work_name}")
    
    macro_data = load_macro(work_name)
    
    st.markdown("### Add New Term")
    col1, col2, col3 = st.columns([2, 2, 1])
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
    
    st.markdown("### Current Terms")
    if not macro_data:
        st.info("No terms defined yet. Add some terms above.")
    else:
        for i, (original, translation) in enumerate(macro_data.items()):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                edited_original = st.text_input("Original", value=original, key=f"orig_{i}")
            with col2:
                edited_translation = st.text_input("Translation", value=translation, key=f"trans_{i}")
            with col3:
                if st.button("Save", key=f"save_{i}", use_container_width=True):
                    del macro_data[original]
                    if edited_original.strip() and edited_translation.strip():
                        macro_data[edited_original.strip()] = edited_translation.strip()
                        save_macro(work_name, macro_data)
                        st.success("Term updated!")
                        st.rerun()
            with col4:
                if st.button("Delete", key=f"del_{i}", use_container_width=True, type="secondary"):
                    del macro_data[original]
                    save_macro(work_name, macro_data)
                    st.success("Term deleted!")
                    st.rerun()