"""File-based storage for works, chapters, and term macros.

This is a direct port of the original Streamlit app's
`utils/file_operations.py` and `utils/macro_utils.py`, keeping the
exact same on-disk JSON format so existing `works/` data carries over
unchanged.
"""
import os
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

# Resolve the works directory relative to the project root (two levels up
# from this file: backend/services/storage.py -> backend/ -> project root).
BASE_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "works"
BASE_LOG_DIR.mkdir(exist_ok=True)

# Manifest mapping work_id -> work directory name. This is the source of
# truth for which works exist; URLs use the stable work_id, not the
# (possibly renameable) directory name.
MANIFEST_PATH = BASE_LOG_DIR / "works.json"


def _load_manifest() -> dict[str, str]:
    """Return the {work_id: work_name} manifest, building it lazily from
    existing work directories if the file is missing (one-time safety net so
    the app never breaks even if the explicit migration script wasn't run)."""
    if not MANIFEST_PATH.exists():
        manifest: dict[str, str] = {}
        if BASE_LOG_DIR.exists():
            for d in BASE_LOG_DIR.iterdir():
                if d.is_dir():
                    manifest[uuid.uuid4().hex[:8]] = d.name
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=4), encoding="utf-8"
        )
        return manifest
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def _save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=4), encoding="utf-8"
    )


def _resolve_work_name(work_id: str) -> str:
    """Resolve a work_id to its on-disk directory name, or raise."""
    manifest = _load_manifest()
    name = manifest.get(work_id)
    if name is None:
        raise FileNotFoundError(f"Work id '{work_id}' not found")
    return name


# ---------------------------------------------------------------------------
# Works
# ---------------------------------------------------------------------------

def get_works() -> list[dict]:
    """List of {id, name} for every work, sorted by name."""
    manifest = _load_manifest()
    return sorted(
        ({"id": wid, "name": name} for wid, name in manifest.items()),
        key=lambda x: x["name"],
    )


def create_work(work_name: str) -> str:
    """Create a work directory with an empty macro.json and an empty
    chapter_order.json, register it in the manifest, and return its new
    work_id."""
    work_dir = BASE_LOG_DIR / work_name
    work_dir.mkdir(parents=True, exist_ok=True)
    macro_file = work_dir / "macro.json"
    if not macro_file.exists():
        macro_file.write_text("{}", encoding="utf-8")
    order_file = work_dir / "chapter_order.json"
    if not order_file.exists():
        order_file.write_text("[]", encoding="utf-8")
    work_id = uuid.uuid4().hex[:8]
    manifest = _load_manifest()
    while work_id in manifest:
        work_id = uuid.uuid4().hex[:8]
    manifest[work_id] = work_name
    _save_manifest(manifest)
    return work_id


def delete_work(work_id: str) -> None:
    """Recursively delete a work directory and remove it from the manifest."""
    manifest = _load_manifest()
    work_name = manifest.get(work_id)
    if work_name is None:
        return
    work_dir = BASE_LOG_DIR / work_name
    if work_dir.is_dir():
        shutil.rmtree(work_dir)
    manifest.pop(work_id, None)
    _save_manifest(manifest)


def _work_dir_or_404(work_id: str) -> Path:
    work_name = _resolve_work_name(work_id)
    work_dir = BASE_LOG_DIR / work_name
    if not work_dir.is_dir():
        raise FileNotFoundError(f"Work '{work_name}' not found")
    return work_dir


def _work_dir_writable(work_id: str) -> Path:
    """Resolve work_id -> on-disk dir name and return the path, creating
    the directory if needed. Use this for WRITES so we never write to a
    phantom `works/<work_id>/` directory."""
    work_name = _resolve_work_name(work_id)
    work_dir = BASE_LOG_DIR / work_name
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

def get_chapters(work_name: str) -> list[str]:
    """Ordered list of chapter filenames (with .json), for legacy callers.

    Order: chapters listed in chapter_order.json (in that order) first, then
    any chapter files not in the order file, sorted by mtime desc (newest
    first) so freshly finished translations surface at the top until the user
    drags them."""
    work_dir = _work_dir_or_404(work_name)
    all_files = {
        f.name for f in work_dir.iterdir()
        if f.is_file() and f.suffix == ".json"
        and f.name != "macro.json"
        and f.name != "chapter_order.json"
    }
    order_path = work_dir / "chapter_order.json"
    ordered: list[str] = []
    if order_path.exists():
        try:
            saved = json.loads(order_path.read_text(encoding="utf-8"))
            if isinstance(saved, list):
                for name in saved:
                    if name in all_files and name not in ordered:
                        ordered.append(name)
        except (json.JSONDecodeError, ValueError):
            pass
    remaining = all_files - set(ordered)
    # Sort remaining by mtime desc (newest first).
    remaining_sorted = sorted(
        remaining,
        key=lambda n: (work_dir / n).stat().st_mtime,
        reverse=True,
    )
    return remaining_sorted + ordered


# ---------------------------------------------------------------------------
# Chapter order list (new entry-based format)
# ---------------------------------------------------------------------------
#
# chapter_order.json is now a list of entries:
#   [{ "id": "<microsecond-timestamp>", "filename": "ep1.json" | null,
#      "status": "pending" | "done" | "retranslating" }, ...]
#
# The list is maintained newest-first (the id is a microsecond timestamp, so
# index 0 is the newest). `id` is both the unique identifier and the sort key.
# Drag-to-reorder reorders this list. Renaming a chapter updates its
# `filename` field in place (position unchanged). Canceling a job removes its
# entry. Completing a job fills in `filename` and sets `status="done"`.

_ORDER_IGNORE = {"macro.json", "chapter_order.json"}


def _read_order(work_name: str) -> list[dict]:
    work_dir = _work_dir_or_404(work_name)
    path = work_dir / "chapter_order.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    # Normalize: accept dicts; ignore malformed entries.
    out = []
    for e in data:
        if isinstance(e, dict) and "id" in e:
            out.append({
                "id": str(e["id"]),
                "filename": e.get("filename"),
                "status": e.get("status", "done"),
            })
        elif isinstance(e, str):
            # Legacy string-format entry -> treat as a done chapter.
            out.append({"id": e, "filename": e, "status": "done"})
    return out


def _write_order(work_name: str, entries: list[dict]) -> None:
    work_dir = _work_dir_writable(work_name)
    (work_dir / "chapter_order.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def _mtime_id(path: Path) -> str:
    """Build a microsecond-timestamp id from a file's mtime."""
    st = path.stat()
    dt = datetime.fromtimestamp(st.st_mtime)
    return dt.strftime("%Y%m%d%H%M%S") + f"{st.st_mtime_ns % 1_000_000_000:09d}"


def migrate_order(work_name: str) -> None:
    """One-time, idempotent migration of chapter_order.json from the old
    list-of-filenames format to the new list-of-entries format. If the file
    is already in entry format (a list whose first item is a dict), do
    nothing. Otherwise build entries from the old string list + any on-disk
    chapter files, newest-first by mtime, and write back."""
    work_dir = _work_dir_or_404(work_name)
    path = work_dir / "chapter_order.json"
    existing = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            data = None
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return  # already migrated
        if isinstance(data, list):
            existing = [n for n in data if isinstance(n, str)]

    all_files = {
        f.name for f in work_dir.iterdir()
        if f.is_file() and f.suffix == ".json" and f.name not in _ORDER_IGNORE
    }
    # Preserve old order (already newest-first); append any on-disk files not
    # in the old list, newest-first by mtime.
    seen: set[str] = set()
    ordered_names: list[str] = []
    for n in existing:
        if n in all_files and n not in seen:
            seen.add(n)
            ordered_names.append(n)
    leftover = sorted(
        all_files - seen,
        key=lambda n: (work_dir / n).stat().st_mtime,
        reverse=True,
    )
    # leftover are the newest, so they go first.
    ordered_names = leftover + ordered_names

    entries = [
        {"id": _mtime_id(work_dir / n), "filename": n, "status": "done"}
        for n in ordered_names
    ]
    _write_order(work_name, entries)


def get_chapter_list(work_name: str) -> list[dict]:
    """Return the unified entry list (the single source of truth for the
    sidebar). Migrates legacy format on first call."""
    migrate_order(work_name)
    return _read_order(work_name)


def add_order_entry(work_name: str, entry_id: str) -> None:
    """Insert a pending entry at index 0 (newest first)."""
    entries = _read_order(work_name)
    if any(e["id"] == entry_id for e in entries):
        return
    entries.insert(0, {"id": entry_id, "filename": None, "status": "pending"})
    _write_order(work_name, entries)


def complete_order_entry(work_name: str, entry_id: str, filename: str) -> None:
    """Mark an entry done and fill in its filename (position unchanged)."""
    entries = _read_order(work_name)
    for e in entries:
        if e["id"] == entry_id:
            e["filename"] = filename
            e["status"] = "done"
            break
    _write_order(work_name, entries)


def cancel_order_entry(work_name: str, entry_id: str) -> None:
    """Remove an entry (used on job cancel/error)."""
    entries = _read_order(work_name)
    entries = [e for e in entries if e["id"] != entry_id]
    _write_order(work_name, entries)


def set_order_entry_status(work_name: str, entry_id: str, status: str) -> None:
    entries = _read_order(work_name)
    for e in entries:
        if e["id"] == entry_id:
            e["status"] = status
            break
    _write_order(work_name, entries)


def set_status_by_filename(work_name: str, filename: str, status: str) -> None:
    entries = _read_order(work_name)
    for e in entries:
        if e.get("filename") == filename:
            e["status"] = status
            break
    _write_order(work_name, entries)


def get_entry_id_by_filename(work_name: str, filename: str) -> str | None:
    """Return the order-list entry id for a given chapter filename, or None."""
    entries = _read_order(work_name)
    for e in entries:
        if e.get("filename") == filename:
            return e["id"]
    return None


def rename_in_order(work_name: str, old_filename: str, new_filename: str) -> None:
    """Update the filename field of the matching entry (position unchanged)."""
    entries = _read_order(work_name)
    for e in entries:
        if e.get("filename") == old_filename:
            e["filename"] = new_filename
            break
    _write_order(work_name, entries)


def delete_from_order(work_name: str, filename: str) -> None:
    entries = _read_order(work_name)
    entries = [e for e in entries if e.get("filename") != filename]
    _write_order(work_name, entries)


def save_chapter_order_by_ids(work_name: str, ids: list[str]) -> None:
    """Persist an explicit order (list of entry ids) from drag-to-reorder.
    Entries keep their filename/status; any ids not present are dropped;
    any existing entries not mentioned are appended at the end."""
    entries = _read_order(work_name)
    by_id = {e["id"]: e for e in entries}
    seen: set[str] = set()
    out: list[dict] = []
    for entry_id in ids:
        e = by_id.get(entry_id)
        if e and entry_id not in seen:
            seen.add(entry_id)
            out.append(e)
    for e in entries:
        if e["id"] not in seen:
            out.append(e)
    _write_order(work_name, out)


def save_chapter_order(work_name: str, order_list: list[str]) -> None:
    """Persist an explicit chapter order. Drops any filenames that don't
    exist on disk; appends any existing chapters the caller omitted (so the
    order file never hides chapters)."""
    work_dir = _work_dir_or_404(work_name)
    all_files = {
        f.name for f in work_dir.iterdir()
        if f.is_file() and f.suffix == ".json"
        and f.name != "macro.json"
        and f.name != "chapter_order.json"
    }
    seen: set[str] = set()
    out: list[str] = []
    for name in order_list:
        if name in all_files and name not in seen:
            seen.add(name)
            out.append(name)
    # Append any chapters not mentioned so they remain visible (newest first).
    leftover = sorted(
        all_files - seen,
        key=lambda n: (work_dir / n).stat().st_mtime,
        reverse=True,
    )
    out.extend(leftover)
    (work_dir / "chapter_order.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def get_chapter(work_name: str, chapter: str) -> dict:
    """Return {original, translated} for a chapter file."""
    path = _work_dir_or_404(work_name) / chapter
    if not path.exists():
        raise FileNotFoundError(f"Chapter '{chapter}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def save_chapter_at(
    work_name: str,
    filename: str,
    original_text: str,
    translated_text: str,
) -> str:
    """Overwrite an existing chapter file in place (used by retranslate).
    Keeps the same filename so chapter_order.json ordering is preserved."""
    work_dir = _work_dir_or_404(work_name)
    path = work_dir / filename
    path.write_text(
        json.dumps(
            {"original": original_text, "translated": translated_text},
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )
    return filename


def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/\x00-\x1f]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name


def save_chapter(
    work_name: str,
    original_text: str,
    translated_text: str,
    title: str | None = None,
) -> str:
    """Save a new chapter. If `title` is given it becomes the filename
    (sanitized), otherwise a timestamp is used. Returns the filename."""
    work_dir = _work_dir_writable(work_name)
    work_dir.mkdir(parents=True, exist_ok=True)

    sanitized = _sanitize_filename(title) if title else ""
    if sanitized:
        filename = f"{sanitized}.json"
        filepath = work_dir / filename
        if filepath.exists():
            base = sanitized
            i = 2
            while (work_dir / f"{base}_{i}.json").exists():
                i += 1
            filename = f"{base}_{i}.json"
            filepath = work_dir / filename
    else:
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        filepath = work_dir / filename

    filepath.write_text(
        json.dumps(
            {"original": original_text, "translated": translated_text},
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )
    return filename


def update_chapter(
    work_name: str,
    chapter: str,
    original: str,
    translated: str,
    new_title: str | None = None,
) -> str:
    """Overwrite a chapter's contents and optionally rename it. Returns the
    (possibly new) filename."""
    work_dir = _work_dir_or_404(work_name)
    path = work_dir / chapter
    if not path.exists():
        raise FileNotFoundError(f"Chapter '{chapter}' not found")

    path.write_text(
        json.dumps(
            {"original": original, "translated": translated},
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    if new_title:
        sanitized = _sanitize_filename(new_title)
        new_name = f"{sanitized}.json"
        if new_name != chapter and sanitized:
            new_path = work_dir / new_name
            if not new_path.exists():
                path.rename(new_path)
                return new_name
    return chapter


def delete_chapter(work_name: str, chapter: str) -> None:
    path = _work_dir_or_404(work_name) / chapter
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# Terms (macro.json)
# ---------------------------------------------------------------------------

def load_macro(work_name: str) -> dict:
    macro_file = _work_dir_or_404(work_name) / "macro.json"
    if not macro_file.exists():
        return {}
    return json.loads(macro_file.read_text(encoding="utf-8"))


def save_macro(work_name: str, macro_data: dict) -> None:
    work_dir = _work_dir_writable(work_name)
    (work_dir / "macro.json").write_text(
        json.dumps(macro_data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def merge_macro(work_name: str, new_terms: dict) -> list[str]:
    """Merge new terms into the macro, **overwriting** any existing entries.
    (New translations win over old ones - handles the race where the same
    term appears in two concurrent translations.) Returns the list of keys
    that were written (added or updated)."""
    if not new_terms:
        return []
    macro_data = load_macro(work_name)
    written: list[str] = []
    for original, translation in new_terms.items():
        original = str(original).strip()
        translation = str(translation).strip()
        if not original or not translation:
            continue
        macro_data[original] = translation  # overwrite
        written.append(original)
    if written:
        save_macro(work_name, macro_data)
    return written


def format_macro_for_prompt(work_name: str, input_text: str = "") -> str:
    macro_data = load_macro(work_name)
    if not macro_data or not input_text:
        return ""
    relevant = {
        o: t for o, t in macro_data.items() if o in input_text
    }
    if not relevant:
        return ""
    pairs = [f"{o}:{t}" for o, t in relevant.items()]
    return f"以下是作品名词的翻译：{';'.join(pairs)}\n\n"
