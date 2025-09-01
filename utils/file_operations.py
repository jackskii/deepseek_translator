import os
import json
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

def save_translation_log(work_name, original_text, translated_text):
    """Saves the translation to a new log file in the work directory."""
    work_dir = os.path.join(BASE_LOG_DIR, work_name)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    
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