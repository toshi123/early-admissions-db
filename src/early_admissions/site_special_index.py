"""Versioned, hash-linked search projection of the four safe special flags."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


FLAGS = ("returnee_flag", "international_baccalaureate_flag",
         "private_foreign_student_flag", "adult_selection_flag")
VERSION = "0.1"


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_special_index(database: Path, output_dir: Path) -> dict[str, object]:
    """Create a complete row-keyed index; fail if SQLite flags are malformed."""
    with closing(sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)) as connection:
        rows = connection.execute(
            "SELECT source_dataset, source_version, record_id, " + ", ".join(FLAGS)
            + " FROM admissions ORDER BY source_dataset, source_version, record_id"
        ).fetchall()
    records = []
    seen = set()
    for source, version, record_id, *values in rows:
        key = (source, version, record_id)
        if key in seen or any(value not in (0, 1) for value in values):
            raise ValueError("duplicate identity or invalid special selection flag")
        seen.add(key)
        records.append({"source_dataset": source, "source_version": version,
                        "record_id": record_id,
                        "flags": dict(zip(FLAGS, (bool(value) for value in values)))})
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_hash = _sha(database)
    build_id = hashlib.sha256(_bytes([VERSION, sqlite_hash])).hexdigest()[:20]
    payload_path = output_dir / "special_selection_index.json"
    payload_path.write_bytes(_bytes({"artifact": "early_admissions_special_selection_index",
                                     "schema_version": VERSION, "build_id": build_id,
                                     "records": records}))
    manifest = {"artifact": "early_admissions_special_selection_manifest",
                "schema_version": VERSION, "build_id": build_id,
                "sqlite_sha256": sqlite_hash, "rows": len(records),
                "output": {"path": payload_path.name, "sha256": _sha(payload_path),
                           "size_bytes": payload_path.stat().st_size}}
    (output_dir / "special_selection_manifest.json").write_bytes(_bytes(manifest))
    return manifest
