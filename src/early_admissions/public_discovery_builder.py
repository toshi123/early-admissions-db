"""Build the independently reviewed public discovery layer beside Site-data.

The input is a publication registry, not a projection of UpdateQueue. A row is
published only after its 2027 existence and official URL have been reviewed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_VERSION = "0.1"
INPUT_PATH = Path("data/publication/provisional_admissions_2027.csv")
SCHEMA_PATH = Path("schema/publication/provisional_admissions_schema_v0_1.json")
QUEUE_PATH = Path("data/operations/update_queue.csv")
OUTPUT_NAME = "provisional_admissions.json"
MANIFEST_NAME = "public_discovery_manifest.json"
NULLABLE = {"faculty_school", "previous_year_source_url", "previous_year_detail", "release_expected_text", "related_update_queue_id"}


class PublicDiscoveryError(ValueError):
    """Publication registry is unsafe or inconsistent with its inputs."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def validate_publication_registry(root: Path) -> list[dict[str, object]]:
    source = root / INPUT_PATH
    schema = json.loads((root / SCHEMA_PATH).read_text(encoding="utf-8"))
    expected = list(schema["required"])
    fields, raw_rows = _read_csv(source)
    if fields != expected:
        raise PublicDiscoveryError("provisional registry header differs from v0.1 schema")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    queue_fields, queue_rows = _read_csv(root / QUEUE_PATH)
    if "queue_id" not in queue_fields:
        raise PublicDiscoveryError("UpdateQueue has no queue_id")
    queue = {row["queue_id"]: row for row in queue_rows}
    ids: set[str] = set()
    rows: list[dict[str, object]] = []
    for line, raw in enumerate(raw_rows, 2):
        row: dict[str, object] = {
            key: (None if key in NULLABLE and value == "" else value)
            for key, value in raw.items()
        }
        row["information_year"] = int(str(row["information_year"]))
        errors = sorted(validator.iter_errors(row), key=lambda error: str(error.path))
        if errors:
            field = ".".join(str(part) for part in errors[0].path)
            raise PublicDiscoveryError(f"registry line {line} {field}: {errors[0].message}")
        provisional_id = str(row["provisional_id"])
        if provisional_id in ids:
            raise PublicDiscoveryError(f"duplicate provisional_id: {provisional_id}")
        ids.add(provisional_id)
        for key in ("official_source_url", "previous_year_source_url"):
            url = row[key]
            if url is not None and (urlparse(str(url)).scheme != "https" or not urlparse(str(url)).hostname):
                raise PublicDiscoveryError(f"registry line {line}: unsafe {key}")
        qid = row["related_update_queue_id"]
        if qid is not None:
            q = queue.get(str(qid))
            if q is None or q["university"] != row["university"] or q["action_status"] == "完了":
                raise PublicDiscoveryError(f"registry line {line}: invalid related UpdateQueue ID")
        rows.append(row)
    return rows


def _confirmed_keys(database: Path) -> set[tuple[str, str, str]]:
    with closing(sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)) as connection:
        return {
            (str(university), str(faculty or ""), str(selection or ""))
            for university, faculty, selection in connection.execute(
                "SELECT university, faculty_school, selection_name FROM admissions"
            )
        }


def build_public_discovery(root: Path, database: Path, output_dir: Path) -> dict[str, object]:
    root = root.resolve()
    database = database if database.is_absolute() else root / database
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    records = validate_publication_registry(root)
    confirmed = _confirmed_keys(database)
    published = []
    suppressed = []
    for row in records:
        university = str(row["university"])
        faculty = str(row["faculty_school"] or "")
        selection = str(row["selection_name"])
        matches = [key for key in confirmed if key[0] == university and key[2] == selection]
        if any(not faculty or key[1] == faculty for key in matches):
            suppressed.append(str(row["provisional_id"]))
        else:
            published.append(row)
    published.sort(key=lambda row: str(row["provisional_id"]))
    input_hash = _sha256(root / INPUT_PATH)
    database_hash = _sha256(database)
    queue_hash = _sha256(root / QUEUE_PATH)
    build_id = hashlib.sha256(_json_bytes([SCHEMA_VERSION, input_hash, database_hash, queue_hash])).hexdigest()[:20]
    payload = {"artifact": "early_admissions_public_discovery", "schema_version": SCHEMA_VERSION,
               "build_id": build_id, "records": published}
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / OUTPUT_NAME
    payload_path.write_bytes(_json_bytes(payload))
    manifest = {
        "artifact": "early_admissions_public_discovery_manifest",
        "schema_version": SCHEMA_VERSION,
        "build_id": build_id,
        "input_sha256": input_hash,
        "sqlite_sha256": database_hash,
        "update_queue_sha256": queue_hash,
        "registry_rows": len(records),
        "published_rows": len(published),
        "suppressed_confirmed_ids": suppressed,
        "output": {"path": OUTPUT_NAME, "sha256": _sha256(payload_path), "size_bytes": payload_path.stat().st_size},
    }
    (output_dir / MANIFEST_NAME).write_bytes(_json_bytes(manifest))
    return manifest
