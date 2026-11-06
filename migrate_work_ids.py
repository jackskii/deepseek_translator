"""One-time migration: assign a stable work_id to each existing work.

Run once from the project root:
    python3 migrate_work_ids.py

It creates works/works.json mapping {work_id: work_dir_name} for every
existing work directory. Idempotent: if works.json already exists, it
leaves assigned ids alone and only adds ids for any new (un-mapped) work
directories. Safe to re-run.
"""
import json
import uuid
from pathlib import Path

WORKS_DIR = Path(__file__).resolve().parent / "works"
MANIFEST = WORKS_DIR / "works.json"


def main() -> None:
    WORKS_DIR.mkdir(exist_ok=True)
    # Load existing manifest (preserve already-assigned ids).
    manifest: dict[str, str] = {}
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                manifest = {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            manifest = {}

    # Map every existing work dir name -> some work_id (reverse lookup).
    name_to_id = {name: wid for wid, name in manifest.items()}

    changed = False
    for d in WORKS_DIR.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        if name in name_to_id:
            continue  # already has an id
        work_id = uuid.uuid4().hex[:8]
        while work_id in manifest:
            work_id = uuid.uuid4().hex[:8]
        manifest[work_id] = name
        name_to_id[name] = work_id
        changed = True

    if changed:
        MANIFEST.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=4), encoding="utf-8"
        )
        print(f"Wrote {MANIFEST} ({len(manifest)} works).")
    else:
        print(f"No changes; {len(manifest)} works already mapped in {MANIFEST}.")


if __name__ == "__main__":
    main()
