"""File-based storage for works, chapters, and term macros.

On-disk JSON under works/: works.json, selection.json, and per-work
chapter_order.json, auto.json, stats, and chapter files.
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
UNIVERSAL_MACRO_PATH = BASE_LOG_DIR / "universal_macro.json"
SELECTION_PATH = BASE_LOG_DIR / "selection.json"


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
    """List of {id, name, chapterCount, wordCount, lastTranslated, lastRead, added}."""
    manifest = _load_manifest()
    out: list[dict] = []
    for wid, name in manifest.items():
        try:
            stats = get_work_stats(wid)
        except FileNotFoundError:
            stats = _empty_stats()
        out.append({"id": wid, "name": name, **stats})
    return out


def create_work(work_name: str) -> str:
    """Create a work directory with an empty macro.json and an empty
    chapter_order.json, register it in the manifest, and return its new
    work_id. Raises FileExistsError if the name (or its directory) is
    already used."""
    work_dir = BASE_LOG_DIR / work_name
    manifest = _load_manifest()
    if work_name in manifest.values() or work_dir.is_dir():
        raise FileExistsError(f"Work '{work_name}' already exists.")
    work_dir.mkdir(parents=True, exist_ok=True)
    macro_file = work_dir / "macro.json"
    if not macro_file.exists():
        macro_file.write_text("{}", encoding="utf-8")
    order_file = work_dir / "chapter_order.json"
    if not order_file.exists():
        order_file.write_text("[]", encoding="utf-8")
    work_id = uuid.uuid4().hex[:8]
    manifest = _load_manifest()
    taken_ids = set(manifest) | {
        str(e.get("id") or "")
        for e in (_load_selection().get("deleted") or [])
        if isinstance(e, dict)
    }
    while work_id in taken_ids:
        work_id = uuid.uuid4().hex[:8]
    manifest[work_id] = work_name
    _save_manifest(manifest)
    _drop_deleted_name(work_name)
    stats = _empty_stats()
    stats["added"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    _write_stats_file(work_id, stats)
    return work_id


def _load_selection() -> dict:
    empty = {"deleted": []}
    if not SELECTION_PATH.exists():
        return empty
    try:
        raw = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return empty
    if not isinstance(raw, dict):
        return empty
    deleted = raw.get("deleted")
    if not isinstance(deleted, list):
        deleted = []
    return {"deleted": deleted}


def _save_selection(data: dict) -> None:
    SELECTION_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def list_deleted_works() -> list[dict]:
    out: list[dict] = []
    for e in _load_selection().get("deleted") or []:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        out.append(
            {
                "id": str(e.get("id") or ""),
                "name": str(e.get("name") or ""),
                "status": "deleted",
                "chapterCount": int(e.get("chapterCount") or 0),
                "deletedAt": str(e.get("deletedAt") or ""),
            }
        )
    return out


def _drop_deleted_name(name: str) -> None:
    data = _load_selection()
    deleted = [e for e in (data.get("deleted") or []) if isinstance(e, dict)]
    kept = [e for e in deleted if str(e.get("name") or "") != name]
    if len(kept) != len(deleted):
        data["deleted"] = kept
        _save_selection(data)


def _record_deleted(work_id: str, name: str, chapter_count: int) -> None:
    data = _load_selection()
    deleted = [e for e in (data.get("deleted") or []) if isinstance(e, dict)]
    deleted = [
        e
        for e in deleted
        if str(e.get("id") or "") != work_id and str(e.get("name") or "") != name
    ]
    deleted.insert(
        0,
        {
            "id": work_id,
            "name": name,
            "status": "deleted",
            "chapterCount": int(chapter_count),
            "deletedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    data["deleted"] = deleted
    _save_selection(data)


def _drop_deleted_id(work_id: str) -> None:
    data = _load_selection()
    deleted = [e for e in (data.get("deleted") or []) if isinstance(e, dict)]
    kept = [e for e in deleted if str(e.get("id") or "") != work_id]
    if len(kept) != len(deleted):
        data["deleted"] = kept
        _save_selection(data)


def get_deleted_work(work_id: str) -> dict:
    for e in list_deleted_works():
        if e["id"] == work_id:
            return e
    raise FileNotFoundError(f"Deleted work '{work_id}' not found")


def delete_work(work_id: str) -> None:
    """Soft-delete: keep the directory, drop the manifest row, tombstone in selection.json."""
    manifest = _load_manifest()
    work_name = manifest.get(work_id)
    if work_name is None:
        return
    try:
        chapter_count = int(get_work_stats(work_id).get("chapterCount") or 0)
    except FileNotFoundError:
        chapter_count = 0
    _record_deleted(work_id, work_name, chapter_count)
    manifest.pop(work_id, None)
    _save_manifest(manifest)


def restore_work(work_id: str) -> dict:
    entry = get_deleted_work(work_id)
    name = entry["name"]
    work_dir = BASE_LOG_DIR / name
    if not work_dir.is_dir():
        raise FileNotFoundError(f"Work files for '{name}' are gone")
    manifest = _load_manifest()
    if name in manifest.values():
        raise FileExistsError(f"Work '{name}' already exists.")
    manifest[work_id] = name
    _save_manifest(manifest)
    _drop_deleted_id(work_id)
    return {"id": work_id, "name": name}


def purge_work(work_id: str) -> None:
    """Hard-delete: remove directory and tombstone."""
    name = ""
    try:
        entry = get_deleted_work(work_id)
        name = str(entry.get("name") or "")
    except FileNotFoundError:
        pass
    manifest = _load_manifest()
    if work_id in manifest:
        name = manifest.pop(work_id)
        _save_manifest(manifest)
    if name:
        work_dir = BASE_LOG_DIR / name
        if work_dir.is_dir():
            shutil.rmtree(work_dir)
    _drop_deleted_id(work_id)


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


# ---------------------------------------------------------------------------
# Chapter order list (new entry-based format)
# ---------------------------------------------------------------------------
#
# chapter_order.json is now a list of entries:
#   [{ "id": "<microsecond-timestamp>", "filename": "ep1.json" | null,
#      "status": "pending" | "done" | "retranslating" | "failed" }, ...]
#
# The list is maintained newest-first (the id is a microsecond timestamp, so
# index 0 is the newest). `id` is both the unique identifier and the sort key.
# Drag-to-reorder reorders this list. Renaming a chapter updates its
# `filename` field in place (position unchanged). Canceling a job removes its
# entry. Completing a job fills in `filename` and sets `status="done"`.

_ORDER_IGNORE = {"macro.json", "chapter_order.json", "auto.json", "stats.json"}


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


def _translated_empty(work_dir: Path, filename: str | None) -> bool:
    """True when a chapter has no translated text (missing file, unreadable
    file, or an empty/whitespace `translated` field)."""
    if not filename:
        return True
    path = work_dir / filename
    if not path.is_file():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    return not str(data.get("translated") or "").strip()


def get_chapter_list(work_name: str) -> list[dict]:
    """Return the unified entry list (the single source of truth for the
    sidebar). Migrates legacy format on first call.

    A finished chapter whose translated text is empty is reported as
    `failed` so the sidebar can flag API/parse failures. Pending and
    retranslating rows are left alone."""
    migrate_order(work_name)
    entries = _read_order(work_name)
    work_dir = _work_dir_or_404(work_name)
    for e in entries:
        if e["status"] in ("pending", "retranslating"):
            continue
        # Empty translation (no file, or a blank `translated` field) is the
        # failure signal. A previously failed row whose translation was later
        # filled in goes back to done.
        e["status"] = "failed" if _translated_empty(work_dir, e.get("filename")) else "done"
    return entries


def add_order_entry(
    work_name: str, entry_id: str, filename: str | None = None
) -> None:
    """Insert a pending entry at index 0 (newest first)."""
    entries = _read_order(work_name)
    if any(e["id"] == entry_id for e in entries):
        return
    entries.insert(0, {"id": entry_id, "filename": filename, "status": "pending"})
    _write_order(work_name, entries)


def _timestamp_stem(entry_id: str) -> str:
    """YYYY-MM-DD_HH-MM-SS from a microsecond entry id, or now if it isn't one."""
    if len(entry_id) >= 14 and entry_id[:14].isdigit():
        s = entry_id
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}_{s[8:10]}-{s[10:12]}-{s[12:14]}"
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def reserve_pending_chapter(work_name: str, entry_id: str, original_text: str) -> str:
    """Create the chapter file under a timestamp name and a pending order
    entry pointing at it. Returns the filename. The caller renames the file
    to the translation title once the job succeeds."""
    work_dir = _work_dir_writable(work_name)
    base = _timestamp_stem(entry_id)
    filename = f"{base}.json"
    i = 2
    while (work_dir / filename).exists():
        filename = f"{base}_{i}.json"
        i += 1
    (work_dir / filename).write_text(
        json.dumps(
            {"original": original_text, "translated": ""},
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )
    add_order_entry(work_name, entry_id, filename)
    return filename


def rename_chapter_to_title(work_name: str, filename: str, translated_text: str) -> str:
    """Rename a finished chapter file to the first non-empty line of its
    translation (30 chars). Returns the new filename, or the old one if there
    is nothing to name it with. Updates chapter_order.json in place."""
    sanitized = _sanitize_filename(title_from_translation(translated_text))
    if not sanitized:
        return filename
    work_dir = _work_dir_or_404(work_name)
    new_name = f"{sanitized}.json"
    if new_name == filename:
        return filename
    if (work_dir / new_name).exists():
        base = sanitized
        i = 2
        while (work_dir / f"{base}_{i}.json").exists():
            i += 1
        new_name = f"{base}_{i}.json"
    (work_dir / filename).rename(work_dir / new_name)
    rename_in_order(work_name, filename, new_name)
    return new_name


def complete_order_entry(
    work_name: str, entry_id: str, filename: str, status: str = "done"
) -> None:
    """Fill in an entry's filename and set its status (position unchanged).
    `status` is "done" on success and "failed" when the translation is empty."""
    entries = _read_order(work_name)
    for e in entries:
        if e["id"] == entry_id:
            e["filename"] = filename
            e["status"] = status
            break
    _write_order(work_name, entries)
    refresh_work_stats(work_name)


def cancel_order_entry(work_name: str, entry_id: str) -> None:
    """Remove an entry (used on job cancel/error)."""
    entries = _read_order(work_name)
    entries = [e for e in entries if e["id"] != entry_id]
    _write_order(work_name, entries)


def add_finished_chapter(work_name: str, filename: str) -> None:
    """Insert a done entry at the top for a chapter saved outside the job
    flow (e.g. the Stop button saving a partial translation)."""
    entry_id = _mtime_id(_work_dir_or_404(work_name) / filename)
    add_order_entry(work_name, entry_id, filename)
    complete_order_entry(work_name, entry_id, filename)


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
    refresh_work_stats(work_name)


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


def get_chapter(work_name: str, chapter: str) -> dict:
    """Return {original, translated} for a chapter file."""
    path = _work_dir_or_404(work_name) / chapter
    if not path.exists():
        raise FileNotFoundError(f"Chapter '{chapter}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _empty_stats() -> dict:
    return {
        "chapterCount": 0,
        "wordCount": 0,
        "lastTranslated": "",
        "lastRead": "",
        "added": "",
        "finished": False,
        "lastDownload": "",
        "lastDownloadFrom": 0,
        "lastDownloadTo": 0,
    }


def _added_from_dir(work_id: str) -> str:
    work_dir = _work_dir_or_404(work_id)
    return datetime.fromtimestamp(work_dir.stat().st_ctime).strftime("%Y-%m-%dT%H:%M:%S")


def _read_stats_file(work_id: str) -> dict | None:
    path = _work_dir_or_404(work_id) / "stats.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return {
        "chapterCount": int(data.get("chapterCount") or 0),
        "wordCount": int(data.get("wordCount") or 0),
        "lastTranslated": str(data.get("lastTranslated") or ""),
        "lastRead": str(data.get("lastRead") or ""),
        "added": str(data.get("added") or ""),
        "finished": bool(data.get("finished")),
        "lastDownload": str(data.get("lastDownload") or ""),
        "lastDownloadFrom": int(data.get("lastDownloadFrom") or 0),
        "lastDownloadTo": int(data.get("lastDownloadTo") or 0),
    }


def _write_stats_file(work_id: str, stats: dict) -> None:
    path = _work_dir_writable(work_id) / "stats.json"
    path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def _compute_stats(work_id: str) -> dict:
    """Scan readable chapters once. lastRead is left empty for the caller."""
    work_dir = _work_dir_or_404(work_id)
    chapter_count = 0
    word_count = 0
    last_mtime: float | None = None
    for e in get_chapter_list(work_id):
        filename = e.get("filename")
        if not filename or e.get("status") not in ("done", "retranslating"):
            continue
        path = work_dir / filename
        try:
            data = get_chapter(work_id, filename)
        except FileNotFoundError:
            continue
        body = str(data.get("translated") or "")
        if not body.strip():
            continue
        chapter_count += 1
        word_count += sum(1 for c in body if not c.isspace())
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if last_mtime is None or mtime > last_mtime:
            last_mtime = mtime
    last_translated = ""
    if last_mtime is not None:
        last_translated = datetime.fromtimestamp(last_mtime).strftime("%Y-%m-%dT%H:%M:%S")
    stats = _empty_stats()
    stats["chapterCount"] = chapter_count
    stats["wordCount"] = word_count
    stats["lastTranslated"] = last_translated
    return stats


def refresh_work_stats(work_id: str) -> dict:
    prev = _read_stats_file(work_id) or {}
    stats = _compute_stats(work_id)
    stats["lastRead"] = str(prev.get("lastRead") or "")
    stats["added"] = str(prev.get("added") or "") or _added_from_dir(work_id)
    stats["finished"] = bool(prev.get("finished"))
    stats["lastDownload"] = str(prev.get("lastDownload") or "")
    stats["lastDownloadFrom"] = int(prev.get("lastDownloadFrom") or 0)
    stats["lastDownloadTo"] = int(prev.get("lastDownloadTo") or 0)
    _write_stats_file(work_id, stats)
    return stats


def get_work_stats(work_id: str) -> dict:
    existing = _read_stats_file(work_id)
    if existing is not None:
        if not existing.get("added"):
            existing["added"] = _added_from_dir(work_id)
            _write_stats_file(work_id, existing)
        return existing
    return refresh_work_stats(work_id)


def touch_last_read(work_id: str) -> dict:
    stats = get_work_stats(work_id)
    stats["lastRead"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    _write_stats_file(work_id, stats)
    return stats


def record_last_download(work_id: str, start: int, end: int) -> dict:
    stats = get_work_stats(work_id)
    stats["lastDownload"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    stats["lastDownloadFrom"] = int(start)
    stats["lastDownloadTo"] = int(end)
    _write_stats_file(work_id, stats)
    return stats


def set_finished(work_id: str, finished: bool) -> dict:
    stats = get_work_stats(work_id)
    stats["finished"] = bool(finished)
    _write_stats_file(work_id, stats)
    return stats


def export_chapters(work_id: str) -> tuple[str, list[tuple[str, str]]]:
    """Readable chapters in story order (oldest first): (work_name, [(title, body)]).

    Same set as the reader: done / retranslating rows that have a filename.
    """
    work_name = _resolve_work_name(work_id)
    chapters: list[tuple[str, str]] = []
    for e in reversed(get_chapter_list(work_id)):
        filename = e.get("filename")
        if not filename or e.get("status") not in ("done", "retranslating"):
            continue
        try:
            data = get_chapter(work_id, filename)
        except FileNotFoundError:
            continue
        title = filename[:-5] if filename.lower().endswith(".json") else filename
        body = str(data.get("translated") or "")
        chapters.append((title, body))
    return work_name, chapters


def export_translated_epub(
    work_id: str, start: int | None = None, end: int | None = None
) -> tuple[str, bytes]:
    """EPUB for a 1-based inclusive chapter range (story order).

    Filename/title is `{start}-{end} {work_name}` even when the range is
    the full book, so later chapters don't collide with an old file.
    """
    from .epub import build_epub

    work_name, chapters = export_chapters(work_id)
    n = len(chapters)
    if n == 0:
        raise FileNotFoundError("No translated chapters")
    s = 1 if start is None else int(start)
    e = n if end is None else int(end)
    s = max(1, min(s, n))
    e = max(s, min(e, n))
    book_title = f"{s}-{e} {work_name}"
    data = build_epub(book_title, chapters[s - 1 : e])
    record_last_download(work_id, s, e)
    return book_title, data


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
    refresh_work_stats(work_name)
    return filename


def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/\x00-\x1f]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name


def title_from_translation(translated_text: str, limit: int = 30) -> str:
    """First non-empty line of the translation, trimmed to `limit` characters.
    Empty or whitespace-only lines are skipped. Returns "" if there is none."""
    for line in (translated_text or "").splitlines():
        line = line.strip()
        if line:
            return line[:limit].strip()
    return ""


def save_chapter(
    work_name: str,
    original_text: str,
    translated_text: str,
    title: str | None = None,
) -> str:
    """Save a new chapter. If `title` is given it becomes the filename
    (sanitized), otherwise a timestamp is used. Returns the filename.
    Translation jobs do not use this for the final title: they reserve a
    timestamp file first and rename it after the translation is in."""
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
                refresh_work_stats(work_name)
                return new_name
    refresh_work_stats(work_name)
    return chapter


def delete_chapter(work_name: str, chapter: str) -> None:
    path = _work_dir_or_404(work_name) / chapter
    if path.exists():
        path.unlink()
    refresh_work_stats(work_name)


def _read_auto_file(work_name: str) -> dict | None:
    path = _work_dir_or_404(work_name) / "auto.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


_NCODE_URL_RE = re.compile(r"novel18\.syosetu\.com/(n[0-9a-z]+)", re.I)


def _work_url_from(*urls: str) -> str:
    for u in urls:
        m = _NCODE_URL_RE.search(u or "")
        if m:
            return f"https://novel18.syosetu.com/{m.group(1).lower()}/"
    return ""


def load_auto_progress(work_name: str) -> dict:
    empty = {"source": "novel18", "workUrl": "", "lastUrl": "", "nextUrl": ""}
    data = _read_auto_file(work_name)
    if not data:
        return empty
    last = str(data.get("lastUrl") or "")
    nxt = str(data.get("nextUrl") or "")
    work_url = str(data.get("workUrl") or "") or _work_url_from(last, nxt)
    return {
        "source": str(data.get("source") or "novel18"),
        "workUrl": work_url,
        "lastUrl": last,
        "nextUrl": nxt,
    }


def save_auto_progress(
    work_name: str,
    source: str,
    last_url: str,
    next_url: str,
    work_url: str | None = None,
) -> dict:
    prev = _read_auto_file(work_name) or {}
    prev_source = str(prev.get("source") or "").strip()
    prev_work = str(prev.get("workUrl") or "").strip()
    last = (last_url or "").strip()
    nxt = (next_url or "").strip()
    incoming_work = (work_url or "").strip()
    data = {
        "source": prev_source or (source or "novel18").strip() or "novel18",
        "workUrl": prev_work or incoming_work or _work_url_from(last, nxt),
        "lastUrl": last,
        "nextUrl": nxt,
    }
    work_dir = _work_dir_writable(work_name)
    (work_dir / "auto.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return data


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


def load_universal_macro() -> dict:
    if not UNIVERSAL_MACRO_PATH.exists():
        return {}
    try:
        data = json.loads(UNIVERSAL_MACRO_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_universal_macro(macro_data: dict) -> None:
    UNIVERSAL_MACRO_PATH.write_text(
        json.dumps(macro_data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def format_macro_for_prompt(work_name: str, input_text: str = "") -> str:
    if not input_text:
        return ""
    # Universal first, work overlay so a work-specific term wins on the same key.
    # Both are filtered the same way and emitted as one unlabeled work-term list.
    merged = {**load_universal_macro(), **load_macro(work_name)}
    relevant = {o: t for o, t in merged.items() if o in input_text}
    if not relevant:
        return ""
    pairs = [f"{o}:{t}" for o, t in relevant.items()]
    return f"以下是作品名词的翻译：{';'.join(pairs)}\n\n"
