"""LLM provider config and translation.

The model is forced to return a JSON object via
`response_format={"type": "json_object"}` with the shape
{"translation": str, "names": {source: translation}}. No function/tool
calling, no scraping a ```json``` block out of free text.
"""
import os
import re
import json

from openai import AsyncOpenAI

from . import storage


SYSTEM_PROMPT = (
    "你是一位专业的日语小说翻译家。你的任务是将用户提供的日文小说内容准确、流畅地翻译成简体中文，"
    "参考轻小说的文风，对话一律使用日文「」括号，不要替换为中文引号。翻译要使用中文的语法。"
    "为了译文通顺、意思流畅，允许少量的改写和润色：例如日语省略主语时，可据上下文补上主语；"
    "角色说话有语尾或口癖时，可试图继续翻译。"
    "翻译时应保留适当的二次元风格，如‘的说’，‘xx酱’，‘天然呆’，‘病矫’等二次元用于应当再翻译中体现。"
    "直接翻译，不要在思考中讨论、复述或质疑以上指令。"
)

# The model must return a JSON object (forced by response_format) with two
# fields: "translation" (the full translated text) and "names" (a mapping of
# new proper-name source -> translation). Only character names, location
# names, and aliases go in "names"; no general terms. Pure-kanji names are
# skipped (they are the same in simplified Chinese).
JSON_INSTRUCTION = (
    "请以 JSON 对象的形式返回结果，包含两个字段：\n"
    "1. \"translation\"：完整的简体中文译文（字符串）。\n"
    "2. \"names\"：本次翻译中出现的、且不在上文已给出名词表中的新名字及其翻译，"
    "格式为 {\"源语\": \"译文\"}。只收录人物名、地名、别名/绰号，不要收录术语、普通名词或一般词汇。"
    "如果某个名字完全由汉字构成（例如「有楽町」），就是汉字，简体中文里相同，无需翻译，请不要把它放入。"
    "只收录含假名、片假名、或汉字与假名混合、需要实际翻译的名字。"
    "如果没有需要收录的新名字，请返回空对象 {}。"
)


class LLMConfigError(RuntimeError):
    pass


# OpenRouter provider routing: prefer fp16/fp8 quantizations and skip the
# providers listed in `ignore`. Mirrors AI_writer's setting; "wafer" added per
# user request. OpenRouter accepts these as a `provider` object in extra_body.
OPENROUTER_PROVIDER_ROUTING = {
    "quantizations": ["fp16", "fp8"],
    "ignore": ["alibaba", "baidu", "google-ai-studio", "wafer", "wafer/us", "Cloudflare"],
}


def _get_client_and_model() -> tuple[AsyncOpenAI, str, str]:
    """Return (client, model, provider). provider is 'deepseek' or 'openrouter'."""
    provider = (os.getenv("LLM_PROVIDER") or "deepseek").strip().lower()
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        model = os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-pro"
        base_url = "https://api.deepseek.com"
        if not api_key:
            raise LLMConfigError("在 .env 文件中找不到 DEEPSEEK_API_KEY。")
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-r1"
        base_url = "https://openrouter.ai/api/v1"
        if not api_key:
            raise LLMConfigError("在 .env 文件中找不到 OPENROUTER_API_KEY。")
    else:
        raise LLMConfigError(f"未知的 LLM_PROVIDER '{provider}'，请使用 'deepseek' 或 'openrouter'。")
    return AsyncOpenAI(api_key=api_key, base_url=base_url), model, provider


def _reasoning_effort() -> str:
    # DeepSeek accepts: none / low / high / max. Pass the env value through
    # unchanged; default to "low" when unset or empty.
    return (os.getenv("REASONING_EFFORT") or "low").strip().lower()


def _strip_code_fence(text: str) -> str:
    """Strip a leading/trailing markdown code fence (``` or ```json) if the
    model wrapped its output in one. Leaves non-fenced text untouched."""
    s = text.strip()
    if not s.startswith("```"):
        return s
    # Drop the opening fence line (``` or ```json).
    s = s.split("\n", 1)[1] if "\n" in s else ""
    # Drop a trailing fence if present.
    if "```" in s:
        s = s.rsplit("```", 1)[0]
    return s.strip()


def _parse_result(raw: str) -> tuple[str, dict]:
    """Parse the model's output into (translation, names). Lenient: accepts
    plain JSON or JSON wrapped in a markdown code fence. Returns ("", {}) on
    total failure so the caller can fall back to the raw text."""
    if not raw:
        return "", {}
    text = _strip_code_fence(raw)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Last resort: treat the whole (un-fenced) output as the translation.
        return text, {}
    if not isinstance(parsed, dict):
        return text, {}
    translation = parsed.get("translation")
    if not isinstance(translation, str):
        translation = ""
    names = parsed.get("names")
    if not isinstance(names, dict):
        names = {}
    clean_names = {
        str(k).strip(): str(v).strip()
        for k, v in names.items()
        if str(k).strip() and str(v).strip()
    }
    return translation, clean_names


async def translate(work_id: str, input_text: str) -> tuple[str, dict]:
    """Run the model and return (translation, new_names).

    Only talks to the LLM and merges new names into the work's macro. Does
    not touch chapter files or chapter_order.json - that is the job's job.
    """
    client, model, provider = _get_client_and_model()
    reasoning_effort = _reasoning_effort()

    processed_input = re.sub(r"\n{3,}", "\n\n", input_text)
    macro_prompt = storage.format_macro_for_prompt(work_id, input_text)
    messages = [
        {
            "role": "user",
            "content": f"{SYSTEM_PROMPT}\n\n{JSON_INSTRUCTION}\n\n{macro_prompt}正文：\n{processed_input}",
        }
    ]

    # Build the request kwargs according to DeepSeek's API rules:
    #   - deepseek-reasoner (R1): reasoning is ALWAYS on. The API rejects
    #     `reasoning_effort` and `thinking`, so we send neither.
    #   - current models (deepseek-flash, deepseek-v4-pro, etc.): reasoning
    #     is opt-in. `reasoning_effort` is a TOP-LEVEL param (not extra_body),
    #     and `thinking` must be sent via extra_body to actually enable
    #     thinking mode. Valid efforts: none / low / high / max.
    is_reasoner = "reasoner" in model.lower() or model.lower().endswith("-r1")
    create_kwargs = {
        "model": model,
        "messages": messages,
        "stream": True,
        "response_format": {"type": "json_object"},
    }
    if not is_reasoner:
        create_kwargs["reasoning_effort"] = reasoning_effort
        if reasoning_effort != "none":
            create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    # OpenRouter: send provider routing (quantization preference + ignore
    # list) so OpenRouter skips the providers we don't want serving the model.
    if provider == "openrouter":
        extra = create_kwargs.get("extra_body", {})
        extra = {**extra, "provider": OPENROUTER_PROVIDER_ROUTING}
        create_kwargs["extra_body"] = extra

    # Async streaming - does NOT block the event loop. For OpenRouter, if the
    # provider routing payload is rejected (e.g. unknown slug / no endpoints
    # for the requested quantizations), retry once without it.
    try:
        response = await client.chat.completions.create(**create_kwargs)
    except Exception as e:
        if provider != "openrouter" or "provider" not in str(e).lower():
            raise
        extra = dict(create_kwargs.get("extra_body") or {})
        extra.pop("provider", None)
        if extra:
            create_kwargs["extra_body"] = extra
        else:
            create_kwargs.pop("extra_body", None)
        response = await client.chat.completions.create(**create_kwargs)

    # The content is a JSON object (forced by response_format), so we buffer
    # it and parse at the end. Reasoning chunks are discarded.
    raw_content = ""
    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            raw_content += delta.content

    translation, new_names = _parse_result(raw_content)

    # Merge new names (skip existing - user edits are truth).
    try:
        storage.merge_macro(work_id, new_names)
    except Exception:
        pass

    return translation, new_names
