import os
import json
from config.settings import BASE_LOG_DIR

def load_macro(work_name):
    """Load macro translations for a work."""
    macro_file = os.path.join(BASE_LOG_DIR, work_name, "macro.json")
    if os.path.exists(macro_file):
        with open(macro_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_macro(work_name, macro_data):
    """Save macro translations for a work."""
    macro_file = os.path.join(BASE_LOG_DIR, work_name, "macro.json")
    with open(macro_file, 'w', encoding='utf-8') as f:
        json.dump(macro_data, f, ensure_ascii=False, indent=4)

def format_macro_for_prompt(work_name, input_text=""):
    """Format macro data for inclusion in the LLM prompt, only including terms found in input text."""
    macro_data = load_macro(work_name)
    if not macro_data or not input_text:
        return ""
    
    # Filter macro to only include terms that exist in the input text
    relevant_macro = {}
    for original, translation in macro_data.items():
        if original in input_text:
            relevant_macro[original] = translation
    
    if not relevant_macro:
        return ""
    
    macro_pairs = []
    for original, translation in relevant_macro.items():
        macro_pairs.append(f"{original}:{translation}")
    
    return f"以下是作品名词的翻译：{';'.join(macro_pairs)}\n\n"