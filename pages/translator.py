import streamlit as st
import os
import re
import json
from datetime import datetime
from openai import OpenAI
from utils.file_operations import save_translation_log
from utils.macro_utils import format_macro_for_prompt, merge_macro


# Matches a trailing fenced ```json ... ``` block (with optional preceding
# whitespace/newlines). The model is instructed to append exactly one such
# block at the very end of its output.
_KEYWORD_BLOCK_RE = re.compile(
    r"```json\s*(?P<body>\{.*?\})\s*```\s*\Z",
    re.DOTALL,
)


def _extract_keyword_block(text):
    """Split the model output into (display_translation, new_terms_dict).

    Finds the trailing ```json { ... } ``` block, parses it, and returns the
    text before it together with the parsed dict. If parsing fails or there
    is no block, returns (text, {}).
    """
    match = _KEYWORD_BLOCK_RE.search(text)
    if not match:
        return text, {}
    body = match.group("body")
    try:
        new_terms = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        # Malformed JSON - keep the raw text as-is so nothing is lost.
        return text, {}
    if not isinstance(new_terms, dict):
        return text, {}
    display = text[: match.start()].rstrip()
    return display, new_terms


def show_translator_page():
    """Displays the main translation interface."""
    st.title("📝 Japanese to Chinese Translator")

    # Work selection
    if "current_work" not in st.session_state or not st.session_state.current_work:
        st.warning("Please select or create a work in the sidebar first.")
        return

    st.subheader(f"Current Work: {st.session_state.current_work}")

    # --- Provider configuration ------------------------------------------------
    provider = (os.getenv("LLM_PROVIDER") or "deepseek").strip().lower()
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        model = os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner"
        base_url = "https://api.deepseek.com"
        if not api_key:
            st.error("DEEPSEEK_API_KEY not found in your .env file.")
            st.stop()
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-r1"
        base_url = "https://openrouter.ai/api/v1"
        if not api_key:
            st.error("OPENROUTER_API_KEY not found in your .env file.")
            st.stop()
    else:
        st.error(f"Unknown LLM_PROVIDER '{provider}'. Use 'deepseek' or 'openrouter'.")
        st.stop()
    client = OpenAI(api_key=api_key, base_url=base_url)

    # reasoning_effort: "none" -> "medium", "max" -> "high", else passthrough.
    _re = (os.getenv("REASONING_EFFORT") or "medium").strip().lower()
    reasoning_effort = {"none": "medium", "max": "high"}.get(_re, _re)

    col1, col2 = st.columns(2)
    with col1:
        input_text = st.text_area("Input (Japanese)", placeholder="Paste Japanese text here...", key="main_input")

    with col2:
        # Chapter title - drives the saved filename and the sidebar chapter list.
        # Defaults to a timestamp so existing workflows still work.
        # If a previous translation requested a reset, do it here BEFORE the
        # widget is instantiated (Streamlit forbids modifying a widget's
        # session-state key after the widget has rendered).
        if st.session_state.pop("_reset_chapter_title", False):
            st.session_state.chapter_title = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if "chapter_title" not in st.session_state:
            st.session_state.chapter_title = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        st.text_input(
            "Chapter Title",
            key="chapter_title",
            help="Used as the saved file name and shown in the sidebar chapter list.",
        )

        st.markdown("<h5>Thinking Process</h5>", unsafe_allow_html=True)
        thinking_box = st.container(height=100, border=True)
        thinking_placeholder = thinking_box.empty()

        st.markdown("<h5>Translation (Chinese)</h5>", unsafe_allow_html=True)
        translation_box = st.container(height=600, border=True)
        translation_placeholder = translation_box.empty()

    # Translate button: placed AFTER both columns so it renders full-width at
    # the bottom, aligned beneath the two-column block instead of wedged
    # between col1 and col2 (which broke the horizontal layout).
    translate_button = st.button("Translate", type="primary", use_container_width=True)

    if translate_button and input_text.strip():
        try:
            processed_input = re.sub(r'\n{3,}', '\n\n', input_text)
            system_prompt = (
                "你是一位专业的日语小说翻译家。你的任务是将用户提供的日文小说内容准确、流畅地翻译成简体中文，"
                "参考轻小说的文风，不要改变原文结构和分段，保留日文对话使用的「」。翻译要使用中文的语法。"
            )
            # Keyword extraction instruction: after the translation, the model
            # appends a fenced JSON block listing NEW proper nouns / names /
            # places / terms it translated in this passage. Existing terms
            # supplied via macro_prompt must NOT be repeated.
            keyword_instruction = (
                "\n\n在翻译完成之后，请在译文末尾另起一段，输出一个 ```json``` 代码块，"
                "列出本次翻译中出现的、且不在上文已给出名词表中的新专有名词（人物名、地名、术语等）及其翻译，"
                "格式为：\n```json\n{\"源语1\": \"译文1\", \"源语2\": \"译文2\"}\n```\n"
                "如果本次没有出现新的专有名词，请输出空的 ```json\n{}\n```。"
                "不要把这段 JSON 计入正文翻译中。"
            )

            # Add macro translations to the prompt, only for terms found in input text
            macro_prompt = format_macro_for_prompt(st.session_state.current_work, input_text)

            messages = [{"role": "user", "content": f"{system_prompt}{keyword_instruction}\n\n{macro_prompt}正文：\n{processed_input}"}]
            with st.spinner('Translating...'):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    extra_body={"reasoning_effort": reasoning_effort},
                )

                reasoning_content, translation_content = "", ""
                thinking_placeholder.markdown("...")
                translation_placeholder.markdown("...")

                for chunk in response:
                    delta = chunk.choices[0].delta
                    # reasoning_content is DeepSeek-specific; OpenRouter
                    # exposes it on some models via the same attribute,
                    # and on others not at all.
                    r_chunk = getattr(delta, "reasoning_content", None) or ""
                    if r_chunk:
                        reasoning_content += r_chunk
                        thinking_placeholder.markdown(reasoning_content)
                    if t_chunk := delta.content:
                        translation_content += t_chunk
                        translation_placeholder.markdown(f"<div class='output-text'>{translation_content}</div>", unsafe_allow_html=True)

            # --- Split off the trailing JSON keyword block --------------------
            # The model is instructed to append a ```json ... ``` block at the
            # very end. We extract it (for merging into macro.json) and strip it
            # from what the user sees / what gets saved.
            display_translation, new_terms = _extract_keyword_block(translation_content)

            thinking_placeholder.markdown(reasoning_content)
            translation_placeholder.markdown(f"<div class='output-text'>{display_translation}</div>", unsafe_allow_html=True)

            # --- Merge auto-detected terms (skip existing - user edits truth) -
            added_terms = []
            try:
                added_terms = merge_macro(st.session_state.current_work, new_terms)
            except Exception as merge_err:
                st.warning(f"Keyword merge skipped: {merge_err}")

            # --- Save with the user's title as the filename -------------------
            title = (st.session_state.get("chapter_title") or "").strip()
            save_translation_log(
                st.session_state.current_work,
                input_text,
                display_translation,
                title=title or None,
            )

            if added_terms:
                st.success(f"Translation complete and saved. Added {len(added_terms)} new term(s) to the keyword list.")
            else:
                st.success("Translation complete and saved to logs.")

            # Reset the title to a fresh timestamp for the next chapter. We
            # can't assign st.session_state.chapter_title directly here because
            # the widget with that key has already been rendered this run.
            # Set a flag and rerun; the flag is consumed at the top of the
            # col2 block above, before the widget re-renders.
            st.session_state._reset_chapter_title = True

            # Force a rerun to refresh the sidebar with new chapter
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {e}")