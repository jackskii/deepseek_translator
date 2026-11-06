import os
import json
import re
from datetime import datetime
from config.settings import BASE_LOG_DIR

def get_works():
    """Get a sorted list of work directories."""
    return sorted([d for d in os.listdir(BASE_LOG_DIR) if os.path.isdir(os.path.join(BASE_LOG_DIR, d))])

def get_log_files(work_name):
    """Get a sorted list of log files for a specific work, excluding macro.json."""
    work_dir = os.path.join(BASE_LOG_DIR, work_name)
    if not os.path.exists(work_dir):
        return []
    return sorted([f for f in os.listdir(work_dir) if f.endswith('.json') and f != 'macro.json'], reverse=True)

def create_work(work_name):
    """Create a new work directory and macro file."""
    work_dir = os.path.join(BASE_LOG_DIR, work_name)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    
    # Create macro file for the work
    macro_file = os.path.join(work_dir, "macro.json")
    if not os.path.exists(macro_file):
        with open(macro_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    
    return work_dir

def delete_work(work_name):
    """Recursively delete a work directory and all its chapters/macros."""
    import shutil
    work_dir = os.path.join(BASE_LOG_DIR, work_name)
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir)

def _sanitize_filename(name):
    """Make a user-supplied string safe to use as a filename (no path separators,
    no control chars, trimmed). Returns the cleaned string (without extension)."""
    # Strip path separators and null/control chars.
    name = re.sub(r'[\\/\x00-\x1f]', '', name)
    # Collapse runs of whitespace into a single underscore.
    name = re.sub(r'\s+', '_', name).strip('_')
    return name

def save_translation_log(work_name, original_text, translated_text, title=None):
    """Saves the translation to a new log file in the work directory.

    If `title` is provided and non-empty, it is sanitized and used as the
    filename (with a .json extension). Otherwise a timestamp is generated
    as before.
    """
    work_dir = os.path.join(BASE_LOG_DIR, work_name)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    sanitized = _sanitize_filename(title) if title else ""
    if sanitized:
        filename = f"{sanitized}.json"
        # Avoid silently overwriting an existing chapter if the user reuses
        # a title; append a short suffix in that case.
        filepath = os.path.join(work_dir, filename)
        if os.path.exists(filepath):
            base = sanitized
            i = 2
            while os.path.exists(os.path.join(work_dir, f"{base}_{i}.json")):
                i += 1
            filename = f"{base}_{i}.json"
            filepath = os.path.join(work_dir, filename)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.json"
        filepath = os.path.join(work_dir, filename)

    log_data = {
        "original": original_text,
        "translated": translated_text
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    return filename