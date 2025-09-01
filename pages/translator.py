import streamlit as st
import os
import re
from openai import OpenAI
from utils.file_operations import save_translation_log
from utils.macro_utils import format_macro_for_prompt

def show_translator_page():
    """Displays the main translation interface."""
    st.title("📝 Japanese to Chinese Translator")

    # Work selection
    if "current_work" not in st.session_state or not st.session_state.current_work:
        st.warning("Please select or create a work in the sidebar first.")
        return

    st.subheader(f"Current Work: {st.session_state.current_work}")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("DEEPSEEK_API_KEY not found in your .env file.")
        st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    col1, col2 = st.columns(2)
    with col1:
        input_text = st.text_area("Input (Japanese)", placeholder="Paste Japanese text here...", key="main_input")

    translate_button = st.button("Translate", type="primary", use_container_width=True)

    with col2:
        st.markdown("<h5>Thinking Process</h5>", unsafe_allow_html=True)
        thinking_box = st.container(height=100, border=True)
        thinking_placeholder = thinking_box.empty()

        st.markdown("<h5>Translation (Chinese)</h5>", unsafe_allow_html=True)
        translation_box = st.container(height=600, border=True)
        translation_placeholder = translation_box.empty()

    if translate_button and input_text.strip():
        try:
            processed_input = re.sub(r'\n{3,}', '\n\n', input_text)
            system_prompt = "你是一位专业的日语小说翻译家。你的任务是将用户提供的日文小说内容准确、流畅地翻译成简体中文，参考轻小说的文风，不要改变原文结构和分段，保留日文对话使用的「」。翻译要使用中文的语法。"
            
            # Add macro translations to the prompt, only for terms found in input text
            macro_prompt = format_macro_for_prompt(st.session_state.current_work, input_text)
            
            messages = [{"role": "user", "content": f"{system_prompt}\n\n{macro_prompt}正文：\n{processed_input}"}]
            with st.spinner('Translating...'):
                response = client.chat.completions.create(model="deepseek-reasoner", messages=messages, stream=True)
                
                reasoning_content, translation_content = "", ""
                thinking_placeholder.markdown("...")
                translation_placeholder.markdown("...")

                for chunk in response:
                    if r_chunk := chunk.choices[0].delta.reasoning_content:
                        reasoning_content += r_chunk
                        thinking_placeholder.markdown(reasoning_content)
                    if t_chunk := chunk.choices[0].delta.content:
                        translation_content += t_chunk
                        translation_placeholder.markdown(f"<div class='output-text'>{translation_content}</div>", unsafe_allow_html=True)

            thinking_placeholder.markdown(reasoning_content)
            translation_placeholder.markdown(f"<div class='output-text'>{translation_content}</div>", unsafe_allow_html=True)
            
            save_translation_log(st.session_state.current_work, input_text, translation_content)
            
            st.success("Translation complete and saved to logs.")
            
            # Force a rerun to refresh the sidebar with new chapter
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {e}")