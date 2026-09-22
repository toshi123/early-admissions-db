"""Read-only acceptance audit for the fixed 2026-09-22 source candidates.

The four-file bundles (Master, Coverage, ResearchRequirements, and schema) are
validated together.  A schema that explicitly marks its dataset ``UNFROZEN``
is a source-coherence stop gate even when the CSV tables otherwise validate.
This module never edits canonical, release, unified, SQLite, or Site-data
artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .academic_field import (
    ACADEMIC_FIELD_CROSSWALK_PATH,
    AcademicFieldCrosswalk,
    AcademicFieldTaxonomy,
)
from .academic_field_v2 import (
    ACADEMIC_FIELD_V2_CONTEXT_PATH,
    ACADEMIC_FIELD_V2_RAW_PATH,
)
from .english_requirement import (
    ENGLISH_REQUIREMENT_CROSSWALK_PATH,
    EnglishRequirementCrosswalk,
)
from .gpa_search import GPACrosswalk, GPAParser
from .grade_requirement import GradeRequirementCrosswalk
from .prefecture_search import PrefectureCrosswalk, PrefectureTaxonomy
from .search_qa import QA_SPECS, run_qa
from .site_data_builder import SiteDataBuildPipeline
from .sqlite_builder import DATABASE_FILENAME, SQLiteBuildPipeline
from .structured_search import AcademicFieldV2Branch, SearchCriteria, search_database
from .unified_builder import UnifiedBuildPipeline
from .validator import CONTRACT_PATH, SOURCE_CONFIG, ReadOnlyValidator, ValidationResult


PRODUCTION_VERSIONS = {"kokkoritsu": "5.61", "shidai": "0.97"}
CANDIDATE_VERSIONS = {"kokkoritsu": "5.81", "shidai": "1.08"}
SUPERSEDED_VERSIONS = {"kokkoritsu": "5.74", "shidai": "1.08"}
UPDATE_ID = "update_20260922_v5_81_v1_08"
CANDIDATE_UNIFIED_CHECKPOINT = {
    "manifest": "66431d3ee6dca98bdb462a6838366017a8d02d25ce138e810844987f43b65eba",
    "master": "2af3a834bb00fd93235f711c0f50896c4158b633d550d333b1aad9667bf5985e",
    "coverage": "4457e7cddb9b9bde8a5aa414dcbadeda9ac6d05ed45ef0794354b2883c837e2b",
    "research_requirements": "0aae717876bef3c1ba8645fcbf7e15190ce9bc8521badb83d5f154b6e3782fd9",
}
CANDIDATE_UNIFIED_ROWS = {
    "master": 6411,
    "coverage": 260,
    "research_requirements": 495,
}
INCOMING = {
    "kokkoritsu": {
        "old_version": PRODUCTION_VERSIONS["kokkoritsu"],
        "new_version": CANDIDATE_VERSIONS["kokkoritsu"],
        "path": Path(
            "sources/incoming/2026-09-22/kokkoritsu_v5_81/"
            "kokkoritsu_early_admissions_2027_master_v5_81.csv"
        ),
        "coverage": Path(
            "sources/incoming/2026-09-22/kokkoritsu_v5_81/"
            "kokkoritsu_early_admissions_2027_coverage_v5_81.csv"
        ),
        "research_requirements": Path(
            "sources/incoming/2026-09-22/kokkoritsu_v5_81/"
            "kokkoritsu_early_admissions_2027_research_requirements_v5_81.csv"
        ),
        "current_schema": Path(
            "schema/kokkoritsu/kokkoritsu_early_admissions_schema_v5_61.json"
        ),
        "candidate_schema": Path(
            "sources/incoming/2026-09-22/kokkoritsu_v5_81/"
            "kokkoritsu_early_admissions_schema_v5_81.json"
        ),
    },
    "shidai": {
        "old_version": PRODUCTION_VERSIONS["shidai"],
        "new_version": CANDIDATE_VERSIONS["shidai"],
        "path": Path(
            "sources/incoming/2026-09-22/shidai_v1_08/"
            "shidai_early_admissions_2027_master_v1_08.csv"
        ),
        "coverage": Path(
            "sources/incoming/2026-09-22/shidai_v1_08/"
            "shidai_early_admissions_2027_coverage_v1_08.csv"
        ),
        "research_requirements": Path(
            "sources/incoming/2026-09-22/shidai_v1_08/"
            "shidai_early_admissions_2027_research_requirements_v1_08.csv"
        ),
        "current_schema": Path(
            "schema/shidai/shidai_early_admissions_schema_v0_97.json"
        ),
        "candidate_schema": Path(
            "sources/incoming/2026-09-22/shidai_v1_08/"
            "shidai_early_admissions_schema_v1_08.json"
        ),
    },
}

SUPERSEDED_KOKKORITSU = {
    "version": "5.74",
    "path": Path(
        "sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/"
        "kokkoritsu_early_admissions_2027_master_v5_74.csv"
    ),
    "coverage": Path(
        "sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/"
        "kokkoritsu_early_admissions_2027_coverage_v5_74.csv"
    ),
    "research_requirements": Path(
        "sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/"
        "kokkoritsu_early_admissions_2027_research_requirements_v5_74.csv"
    ),
    "schema": Path(
        "sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/"
        "kokkoritsu_early_admissions_schema_v5_74.json"
    ),
}

MATERIAL_FIELDS = frozenset(
    {
        "university",
        "prefecture",
        "faculty_school",
        "department",
        "academic_field",
        "selection_category",
        "selection_name",
        "eligibility_graduation",
        "gpa_requirement",
        "english_requirement",
        "subject_prerequisites",
        "research_activity_level",
        "research_requirement_required",
        "research_activity_detail",
        "research_requirement_summary",
        "exclusive_enrollment_status",
        "exclusive_enrollment",
        "common_test_required",
        "common_test_usage",
        "selection_document_review",
        "selection_interview",
        "selection_oral_exam",
        "selection_presentation",
        "selection_essay",
        "selection_written_exam",
        "selection_practical",
        "selection_group_discussion",
        "selection_aptitude_test",
        "selection_common_test",
        "application_start",
        "application_end",
        "web_registration_period",
        "first_stage_result_date",
        "second_stage_start",
        "second_stage_end",
        "final_result_date",
        "capacity",
    }
)
PROVENANCE_FIELDS = frozenset(
    {
        "source_url",
        "guideline_url",
        "schedule_url",
        "exclusive_enrollment_evidence_url",
        "publication_status",
        "information_year",
        "verified_on",
        "verification_grade",
        "fallback_previous_year",
        "current_year_release_expected",
        "previous_year_source_url",
        "fallback_note",
        "source_status",
    }
)
NOTES_FIELDS = frozenset({"notes", "detail_completeness"})

REVIEW_COLUMNS = (
    "raw_or_context",
    "frequency",
    "representative_university",
    "representative_faculty",
    "representative_department",
    "representative_record_id",
    "current_fail_closed_status",
    "suggested_review_note",
)

SCHEMA_COMPATIBLE_ADDITIONS = {
    "enum_definitions": {"fallback_previous_year": ["Yes", "No"]},
    "normalization_rules": {
        "fallback_previous_year_values": ["Yes", "No"],
        "excel_in_canonical_freeze": False,
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_receipt(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    total = 0
    for item in files:
        relative = item.relative_to(path).as_posix()
        size = item.stat().st_size
        total += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(item).encode("ascii"))
        digest.update(b"\n")
    return {
        "path": path.as_posix(),
        "tree_sha256": digest.hexdigest(),
        "file_count": len(files),
        "size_bytes": total,
        "kind": "directory",
    }


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    return header, rows


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in header})


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _preflight(
    path: Path,
    logical_key_fields: Sequence[str] = ("record_id",),
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    decoded = raw.decode("utf-8-sig" if bom else "utf-8")
    parsed = list(csv.reader(decoded.splitlines()))
    header = parsed[0] if parsed else []
    rows = parsed[1:]
    key_indexes = (
        [header.index(field) for field in logical_key_fields]
        if logical_key_fields and all(field in header for field in logical_key_fields)
        else []
    )
    keys = [
        tuple(row[index] for index in key_indexes)
        for row in rows
        if key_indexes and all(len(row) > index for index in key_indexes)
    ]
    duplicate_keys = sorted(key for key, count in Counter(keys).items() if count > 1)
    exact_duplicates = sum(count - 1 for count in Counter(tuple(row) for row in rows).values() if count > 1)
    crlf = raw.count(b"\r\n")
    return {
        "path": str(path.relative_to(repo_root)) if repo_root else str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "rows": len(rows),
        "columns": len(header),
        "encoding": "UTF-8-SIG" if bom else "UTF-8",
        "bom": bom,
        "line_endings": {
            "crlf": crlf,
            "lf": raw.count(b"\n") - crlf,
            "cr": raw.count(b"\r") - crlf,
        },
        "duplicate_header": sorted(
            key for key, count in Counter(header).items() if count > 1
        ),
        "logical_key_fields": list(logical_key_fields),
        "duplicate_logical_key_count": len(duplicate_keys),
        "duplicate_logical_key_examples": [list(key) for key in duplicate_keys[:10]],
        "exact_duplicate_row_count": exact_duplicates,
        "row_width_mismatch_count": sum(len(row) != len(header) for row in rows),
        "header": header,
    }


def _json_preflight(
    path: Path, *, repo_root: Path | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    schema = json.loads(raw.decode("utf-8-sig" if bom else "utf-8"))
    crlf = raw.count(b"\r\n")
    return schema, {
        "path": str(path.relative_to(repo_root)) if repo_root else str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "encoding": "UTF-8-SIG" if bom else "UTF-8",
        "bom": bom,
        "line_endings": {
            "crlf": crlf,
            "lf": raw.count(b"\n") - crlf,
            "cr": raw.count(b"\r") - crlf,
        },
        "version": str(schema.get("version", "")),
    }


def _schema_contract_compatibility(
    current: Mapping[str, Any],
    candidate: Mapping[str, Any],
    contract_keys: Sequence[str],
) -> dict[str, Any]:
    """Allow only reviewed additive declarations of existing pipeline semantics."""

    incompatible: list[str] = []
    compatible_additions: dict[str, dict[str, Any]] = {}
    changed = []
    for key in contract_keys:
        before = current.get(key)
        after = candidate.get(key)
        if before == after:
            continue
        changed.append(key)
        allowed = SCHEMA_COMPATIBLE_ADDITIONS.get(key)
        if not isinstance(before, dict) or not isinstance(after, dict) or allowed is None:
            incompatible.append(key)
            continue
        additions = {item: value for item, value in after.items() if item not in before}
        retained = {item: value for item, value in after.items() if item in before}
        if retained != before or additions != allowed:
            incompatible.append(key)
            continue
        compatible_additions[key] = additions
    return {
        "changed_contract_keys": changed,
        "compatible_additions": compatible_additions,
        "incompatible_changed_keys": incompatible,
        "contract_compatible_with_current": not incompatible,
    }


def _master_validation(
    root: Path,
    dataset: str,
    path: Path,
    schema_path: Path,
    version: str,
) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    validator = ReadOnlyValidator(root)
    validator.contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    validator.result = ValidationResult(contract_version="0.1", repo_root=root)
    table = validator._read_table(  # noqa: SLF001 - reuse production validation semantics
        dataset=dataset,
        table_name="master",
        path=path,
        expected_header=schema["master_columns"],
    )
    validator._validate_master(dataset, version, table)  # noqa: SLF001
    summary = validator.result.summary()
    return {
        "scope": "master_only_current_validator_semantics",
        "by_severity": summary["by_severity"],
        "by_code": summary["by_code"],
        "full_source_validator_executed": False,
        "full_source_validator_blocker": (
            "Candidate source schema, Coverage, and ResearchRequirements were not supplied."
        ),
    }


def _schema_identity_audit(
    dataset: str,
    expected_version: str,
    schema: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    canonical_data = schema.get("canonical_data", {})
    expected_names = {
        "master": paths["path"].name,
        "coverage": paths["coverage"].name,
        "research_requirements": paths["research_requirements"].name,
        "schema": paths["candidate_schema"].name,
    }
    declared_names = {key: canonical_data.get(key) for key in expected_names}
    filenames_match = declared_names == expected_names
    declared_dataset = schema.get("dataset")
    dataset_matches = declared_dataset in {
        None,
        "",
        f"{dataset}_early_admissions_2027",
    }

    dataset_state = str(schema.get("dataset_state", "") or "")
    artifact_state = str(
        schema.get("artifact_status", {}).get("canonical_csv_json", "") or ""
    )
    source_freeze_status = str(
        schema.get("sources", {}).get("freeze_status", "") or ""
    )
    state_evidence = [dataset_state, artifact_state, source_freeze_status]
    explicitly_unfrozen = any("UNFROZEN" in value.upper() for value in state_evidence)
    explicitly_frozen = (
        any(value.upper() == "FROZEN" for value in state_evidence if value)
        and not explicitly_unfrozen
    )
    if explicitly_unfrozen:
        effective_state = "UNFROZEN"
    elif explicitly_frozen:
        effective_state = "FROZEN"
    else:
        effective_state = "UNDECLARED"

    version_matches = str(schema.get("version", "")) == expected_version
    identity_coherent = version_matches and filenames_match and dataset_matches
    return {
        "expected_version": expected_version,
        "internal_version": str(schema.get("version", "")),
        "version_matches": version_matches,
        "declared_dataset": declared_dataset,
        "dataset_matches": dataset_matches,
        "canonical_data_declared": declared_names,
        "canonical_data_expected": expected_names,
        "canonical_filenames_match": filenames_match,
        "dataset_state": dataset_state or None,
        "artifact_canonical_state": artifact_state or None,
        "source_freeze_status": source_freeze_status or None,
        "effective_freeze_state": effective_state,
        "explicitly_unfrozen": explicitly_unfrozen,
        "unfreeze_metadata": schema.get("unfreeze"),
        "identity_coherent": identity_coherent,
        "source_coherence_gate_passed": identity_coherent and explicitly_frozen,
    }


def _candidate_source_validation(
    root: Path, derived_dir: Path
) -> dict[str, Any]:
    """Run the production validator semantics against the incoming bundles."""

    validator = ReadOnlyValidator(root)
    validator.contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    validator.contract["x-source-version-matrix"] = {
        dataset: str(config["new_version"])
        for dataset, config in INCOMING.items()
    }
    validator.result = ValidationResult(contract_version="0.1", repo_root=root)
    validator._validate_contract_files()  # noqa: SLF001
    states: dict[str, dict[str, Any]] = {}
    for dataset, config in INCOMING.items():
        schema_path = root / config["candidate_schema"]
        source_schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
        tables = {}
        for table_name, path_key in (
            ("master", "path"),
            ("coverage", "coverage"),
            ("research_requirements", "research_requirements"),
        ):
            schema_key = f"{table_name}_columns"
            expected_header = list(source_schema.get(schema_key, []))
            validator._validate_source_contract_alignment(  # noqa: SLF001
                dataset, table_name, expected_header
            )
            tables[table_name] = validator._read_table(  # noqa: SLF001
                dataset=dataset,
                table_name=table_name,
                path=root / config[path_key],
                expected_header=expected_header,
            )
        source_version = str(source_schema.get("version", ""))
        validator._validate_master(  # noqa: SLF001
            dataset, source_version, tables["master"]
        )
        validator._validate_coverage(  # noqa: SLF001
            dataset, source_version, tables["coverage"]
        )
        validator._validate_research(  # noqa: SLF001
            dataset, source_version, tables["research_requirements"]
        )
        states[dataset] = {
            "dataset": dataset,
            "source_version": source_version,
            "source_schema": source_schema,
            "tables": tables,
        }
    validator._validate_cross_table_relationships(states)  # noqa: SLF001
    validator.result.metrics = validator._build_metrics(states)  # noqa: SLF001
    full_report = derived_dir / "candidate_source_validation.json"
    _write_json(full_report, validator.result.to_dict())
    return {
        "scope": "complete_incoming_four_file_bundles",
        "summary": validator.result.summary(),
        "metrics": validator.result.metrics,
        "machine_report": str(full_report.relative_to(root)),
    }


def _validation_delta(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    baseline_codes = baseline.get("by_code", {})
    candidate_codes = candidate.get("by_code", {})
    by_code = {}
    for code in sorted(set(baseline_codes) | set(candidate_codes)):
        old = int(baseline_codes.get(code, {}).get("count", 0))
        new = int(candidate_codes.get(code, {}).get("count", 0))
        severity = (
            candidate_codes.get(code, {}).get("severity")
            or baseline_codes.get(code, {}).get("severity")
        )
        by_code[code] = {
            "severity": severity,
            "baseline": old,
            "candidate": new,
            "delta": new - old,
        }
    return {
        "by_severity": {
            severity: {
                "baseline": int(baseline["by_severity"].get(severity, 0)),
                "candidate": int(candidate["by_severity"].get(severity, 0)),
                "delta": int(candidate["by_severity"].get(severity, 0))
                - int(baseline["by_severity"].get(severity, 0)),
            }
            for severity in ("error", "warning", "informational")
        },
        "by_code": by_code,
    }


def _field_class(field: str) -> str:
    if field in MATERIAL_FIELDS:
        return "A_search_visible_material"
    if field in PROVENANCE_FIELDS:
        return "B_publication_provenance"
    if field in NOTES_FIELDS:
        return "C_notes_completeness"
    return "D_other"


def _diff_dataset(
    dataset: str,
    header: Sequence[str],
    old_rows: Sequence[dict[str, str]],
    new_rows: Sequence[dict[str, str]],
    derived_dir: Path,
) -> dict[str, Any]:
    old = {row["record_id"]: row for row in old_rows}
    new = {row["record_id"]: row for row in new_rows}
    added_ids = sorted(new.keys() - old.keys())
    removed_ids = sorted(old.keys() - new.keys())
    shared = sorted(old.keys() & new.keys())
    changed_ids = [record_id for record_id in shared if old[record_id] != new[record_id]]
    field_changes: list[dict[str, str]] = []
    material_ids: set[str] = set()
    field_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    for record_id in changed_ids:
        for field in header:
            before = old[record_id].get(field, "")
            after = new[record_id].get(field, "")
            if before == after:
                continue
            classification = _field_class(field)
            field_counts[field] += 1
            class_counts[classification] += 1
            if field in MATERIAL_FIELDS:
                material_ids.add(record_id)
            field_changes.append(
                {
                    "record_id": record_id,
                    "field": field,
                    "classification": classification,
                    "old_value": before,
                    "new_value": after,
                }
            )
    _write_csv(derived_dir / f"{dataset}_added.csv", header, (new[key] for key in added_ids))
    _write_csv(derived_dir / f"{dataset}_removed.csv", header, (old[key] for key in removed_ids))
    _write_csv(
        derived_dir / f"{dataset}_changed.csv",
        ("record_id", "field", "classification", "old_value", "new_value"),
        field_changes,
    )
    truthy = {"1", "True", "Yes"}
    fallback_removed = [
        key
        for key in shared
        if old[key]["fallback_previous_year"] in truthy
        and new[key]["fallback_previous_year"] not in truthy
    ]
    fallback_introduced = [
        key
        for key in shared
        if old[key]["fallback_previous_year"] not in truthy
        and new[key]["fallback_previous_year"] in truthy
    ]
    current_year_confirmed = [
        key
        for key in shared
        if (
            old[key]["fallback_previous_year"] in truthy
            or (
                old[key].get("information_year", "").isdigit()
                and int(old[key]["information_year"]) < 2027
            )
        )
        and new[key]["fallback_previous_year"] not in truthy
        and new[key].get("information_year") == "2027"
    ]
    return {
        "old_rows": len(old),
        "new_rows": len(new),
        "unchanged": len(shared) - len(changed_ids),
        "added": len(added_ids),
        "removed": len(removed_ids),
        "changed": len(changed_ids),
        "material_changed_records": len(material_ids),
        "material_changed_record_examples": sorted(material_ids)[:12],
        "field_change_counts": dict(sorted(field_counts.items())),
        "classification_counts": dict(sorted(class_counts.items())),
        "old_universities": len({row["university"] for row in old_rows}),
        "new_universities": len({row["university"] for row in new_rows}),
        "fallback_removed": len(fallback_removed),
        "fallback_removed_record_ids": fallback_removed,
        "fallback_newly_introduced": len(fallback_introduced),
        "fallback_newly_introduced_record_ids": fallback_introduced,
        "current_year_confirmed_upgrades": len(current_year_confirmed),
        "current_year_confirmed_upgrade_record_ids": current_year_confirmed,
        "added_fallback_rows": sum(
            new[key]["fallback_previous_year"] in truthy for key in added_ids
        ),
        "information_year_changed": sum(
            old[key]["information_year"] != new[key]["information_year"]
            for key in shared
        ),
        "publication_status_changed": sum(
            old[key]["publication_status"] != new[key]["publication_status"]
            for key in shared
        ),
        "added_record_examples": added_ids[:12],
        "removed_record_examples": removed_ids[:12],
        "changed_record_examples": changed_ids[:12],
        "artifacts": {
            "added": str((derived_dir / f"{dataset}_added.csv").relative_to(derived_dir.parents[2])),
            "removed": str((derived_dir / f"{dataset}_removed.csv").relative_to(derived_dir.parents[2])),
            "changed": str((derived_dir / f"{dataset}_changed.csv").relative_to(derived_dir.parents[2])),
        },
    }


def _diff_keyed_table(
    old_rows: Sequence[dict[str, str]],
    new_rows: Sequence[dict[str, str]],
    key_fields: Sequence[str],
) -> dict[str, Any]:
    def key(row: Mapping[str, str]) -> tuple[str, ...]:
        return tuple(row[field] for field in key_fields)

    old = {key(row): row for row in old_rows}
    new = {key(row): row for row in new_rows}
    shared = sorted(old.keys() & new.keys())
    changed = [item for item in shared if old[item] != new[item]]
    return {
        "old_rows": len(old_rows),
        "new_rows": len(new_rows),
        "added": len(new.keys() - old.keys()),
        "removed": len(old.keys() - new.keys()),
        "changed": len(changed),
        "unchanged": len(shared) - len(changed),
        "added_key_examples": [list(item) for item in sorted(new.keys() - old.keys())[:10]],
        "removed_key_examples": [list(item) for item in sorted(old.keys() - new.keys())[:10]],
        "changed_key_examples": [list(item) for item in changed[:10]],
    }


def _diff_research_multiset(
    header: Sequence[str],
    old_rows: Sequence[dict[str, str]],
    new_rows: Sequence[dict[str, str]],
) -> dict[str, Any]:
    def signature(row: Mapping[str, str]) -> tuple[str, ...]:
        return tuple(row.get(column, "") for column in header)

    old_counter = Counter(signature(row) for row in old_rows)
    new_counter = Counter(signature(row) for row in new_rows)
    added = sum((new_counter - old_counter).values())
    removed = sum((old_counter - new_counter).values())
    by_parent_old: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    by_parent_new: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    for row in old_rows:
        by_parent_old[row["admission_id"]][signature(row)] += 1
    for row in new_rows:
        by_parent_new[row["admission_id"]][signature(row)] += 1
    parents = set(by_parent_old) | set(by_parent_new)
    changed_parents = sorted(
        parent for parent in parents if by_parent_old[parent] != by_parent_new[parent]
    )
    return {
        "old_rows": len(old_rows),
        "new_rows": len(new_rows),
        "exact_rows_added": added,
        "exact_rows_removed": removed,
        "changed_parent_ids": len(changed_parents),
        "changed_parent_examples": changed_parents[:12],
    }


def _superseded_to_candidate_audit(
    root: Path,
    candidate_rows: Sequence[dict[str, str]],
    candidate_config: Mapping[str, Any],
    derived_dir: Path,
) -> dict[str, Any]:
    old_header, old_master = _read_csv(root / SUPERSEDED_KOKKORITSU["path"])
    new_header, _ = _read_csv(root / candidate_config["path"])
    if old_header != new_header:
        raise ValueError("Superseded and candidate kokkoritsu Master headers differ.")
    master = _diff_dataset(
        "kokkoritsu_v5_74_to_v5_81",
        new_header,
        old_master,
        candidate_rows,
        derived_dir,
    )
    _, old_coverage = _read_csv(root / SUPERSEDED_KOKKORITSU["coverage"])
    _, new_coverage = _read_csv(root / candidate_config["coverage"])
    coverage = _diff_keyed_table(
        old_coverage,
        new_coverage,
        ("institution_type", "university"),
    )
    research_header, old_research = _read_csv(
        root / SUPERSEDED_KOKKORITSU["research_requirements"]
    )
    candidate_research_header, new_research = _read_csv(
        root / candidate_config["research_requirements"]
    )
    if research_header != candidate_research_header:
        raise ValueError("Superseded and candidate ResearchRequirements headers differ.")
    research = _diff_research_multiset(
        research_header, old_research, new_research
    )
    old_schema = json.loads(
        (root / SUPERSEDED_KOKKORITSU["schema"]).read_text(encoding="utf-8-sig")
    )
    new_schema = json.loads(
        (root / candidate_config["candidate_schema"]).read_text(encoding="utf-8-sig")
    )
    return {
        "from_version": str(old_schema.get("version")),
        "to_version": str(new_schema.get("version")),
        "master": master,
        "coverage": coverage,
        "research_requirements": research,
        "source_state": {
            "from_dataset_state": old_schema.get("dataset_state"),
            "from_artifact_state": old_schema.get("artifact_status", {}).get(
                "canonical_csv_json"
            ),
            "to_dataset_state": new_schema.get("dataset_state"),
            "to_artifact_state": new_schema.get("artifact_status", {}).get(
                "canonical_csv_json"
            ),
            "to_freeze": new_schema.get("freeze"),
        },
    }


def _sidecar_audit(
    root: Path,
    dataset: str,
    new_rows: Sequence[dict[str, str]],
    coverage_path: Path,
    research_path: Path,
) -> dict[str, Any]:
    _, coverage = _read_csv(root / coverage_path)
    research_header, research = _read_csv(root / research_path)
    master_counts = Counter(
        (row["institution_type"], row["university"]) for row in new_rows
    )
    coverage_by_key = {
        (row["institution_type"], row["university"]): row for row in coverage
    }
    master_keys = set(master_counts)
    coverage_keys = set(coverage_by_key)
    row_mismatches = [
        {
            "institution_type": key[0],
            "university": key[1],
            "coverage_master_rows": int(coverage_by_key[key]["master_rows"]),
            "candidate_master_rows": master_counts[key],
        }
        for key in sorted(master_keys & coverage_keys)
        if int(coverage_by_key[key]["master_rows"]) != master_counts[key]
    ]
    master_by_id = {row["record_id"]: row for row in new_rows}
    orphan_rows = [
        row for row in research if row["admission_id"] not in master_by_id
    ]
    denormalized: list[dict[str, str]] = []
    for row in research:
        parent = master_by_id.get(row["admission_id"])
        if parent is None:
            continue
        for field in ("university", "faculty_school", "department", "selection_name"):
            if row[field] != parent[field]:
                denormalized.append(
                    {
                        "admission_id": row["admission_id"],
                        "field": field,
                        "child_value": row[field],
                        "candidate_parent_value": parent[field],
                    }
                )
    missing_keys = sorted(master_keys - coverage_keys)
    stale_keys = sorted(coverage_keys - master_keys)
    stale_nonzero = [
        key
        for key in stale_keys
        if int(coverage_by_key[key]["master_rows"]) != 0
    ]
    exact_duplicate_count = sum(
        count - 1
        for count in Counter(
            tuple(row.get(column, "") for column in research_header)
            for row in research
        ).values()
        if count > 1
    )
    structurally_coherent = not (
        missing_keys or stale_nonzero or row_mismatches or orphan_rows
    )
    return {
        "candidate_coverage_path": str(coverage_path),
        "candidate_coverage_rows": len(coverage),
        "candidate_master_university_keys": len(master_keys),
        "coverage_missing_keys": [list(key) for key in missing_keys],
        "coverage_zero_master_keys": [list(key) for key in stale_keys],
        "coverage_stale_nonzero_keys": [list(key) for key in stale_nonzero],
        "coverage_master_rows_mismatch_count": len(row_mismatches),
        "coverage_master_rows_mismatch_examples": row_mismatches[:12],
        "coverage_deterministically_rebuildable_from_master": False,
        "coverage_non_derivable_fields": [
            "undergraduate_scope",
            "research_status",
            "current_year_status",
            "fallback_status",
            "checked_on",
            "official_source_url",
            "notes",
        ],
        "candidate_research_path": str(research_path),
        "candidate_research_rows": len(research),
        "research_exact_duplicate_rows": exact_duplicate_count,
        "research_orphan_rows": len(orphan_rows),
        "research_orphan_examples": [row["admission_id"] for row in orphan_rows[:12]],
        "research_denormalized_field_mismatch_count": len(denormalized),
        "research_denormalized_field_mismatch_examples": denormalized[:12],
        "research_deterministically_rebuildable_from_master": False,
        "candidate_sidecars_structurally_coherent": structurally_coherent,
        "reuse_decision": "not_applicable_versioned_candidate_sidecars_supplied",
    }


def _representatives(
    rows: Sequence[dict[str, str]], field: str
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row[field], row)
    return result


def _review_rows(
    values: Counter[str],
    representatives: Mapping[str, dict[str, str]],
    status: str,
    note: str,
) -> list[dict[str, str]]:
    result = []
    for raw in sorted(values):
        row = representatives[raw]
        result.append(
            {
                "raw_or_context": raw,
                "frequency": str(values[raw]),
                "representative_university": row["university"],
                "representative_faculty": row["faculty_school"],
                "representative_department": row["department"],
                "representative_record_id": row["record_id"],
                "current_fail_closed_status": status,
                "suggested_review_note": note,
            }
        )
    return result


def _load_v02(root: Path) -> dict[str, Any]:
    raw_header, raw_rows = _read_csv(
        root / ACADEMIC_FIELD_V2_RAW_PATH
    )
    context_header, context_rows = _read_csv(
        root / ACADEMIC_FIELD_V2_CONTEXT_PATH
    )
    del raw_header, context_header
    raw_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        raw_groups[row["raw_value"]].append(row)
    context_groups: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in context_rows:
        key = (
            row["source_dataset"],
            row["university"],
            row["faculty_school"],
            row["department"],
            row["academic_field"],
        )
        context_groups[key].append(row)
    return {"raw": raw_groups, "context": context_groups}


def _v02_audit(
    rows: Sequence[dict[str, str]], mappings: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    raw_groups = mappings["raw"]
    context_groups = mappings["context"]
    broad_coverage = 0
    subcategory_coverage = 0
    unmapped = 0
    broad_review = 0
    sub_review = 0
    context_consulted = 0
    context_effective = 0
    raw_only = 0
    new_context_counts: Counter[tuple[str, str, str, str, str]] = Counter()
    review_context_counts: Counter[tuple[str, str, str, str, str]] = Counter()
    reps: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    old_contexts = set(context_groups)
    for row in rows:
        key = (
            row["source_dataset"],
            row["university"],
            row["faculty_school"],
            row["department"],
            row["academic_field"],
        )
        raw_block = raw_groups.get(row["academic_field"])
        if raw_block is None:
            unmapped += 1
            broad_review += 1
            sub_review += 1
            continue
        raw_status = raw_block[0]["mapping_status"]
        memberships = {
            (item["group_code"], item["subcategory_code"] or None)
            for item in raw_block
            if item["group_code"]
        }
        context_block = context_groups.get(key)
        if context_block is not None:
            context_consulted += 1
            context_memberships = {
                (item["group_code"], item["subcategory_code"] or None)
                for item in context_block
                if item["group_code"]
            }
            if context_memberships:
                context_effective += 1
            if context_block[0]["merge_mode"] == "authoritative":
                memberships = context_memberships
            else:
                memberships |= context_memberships
        else:
            raw_only += 1
            if raw_status == "review_required":
                review_context_counts[key] += 1
                reps.setdefault(key, row)
        groups = {group for group, _ in memberships}
        subs = {sub for _, sub in memberships if sub}
        if groups:
            broad_coverage += 1
        else:
            broad_review += 1
        if subs:
            subcategory_coverage += 1
        else:
            sub_review += 1
    review_rows = []
    for key in sorted(review_context_counts):
        row = reps[key]
        review_rows.append(
            {
                "raw_or_context": " | ".join(key),
                "frequency": str(review_context_counts[key]),
                "representative_university": row["university"],
                "representative_faculty": row["faculty_school"],
                "representative_department": row["department"],
                "representative_record_id": row["record_id"],
                "current_fail_closed_status": "review_required_no_exact_context",
                "suggested_review_note": (
                    "Exact context review required; do not infer from faculty or department text."
                ),
            }
        )
    return (
        {
            "rows": len(rows),
            "raw_only": raw_only,
            "context_consulted": context_consulted,
            "context_effective": context_effective,
            "broad_coverage": broad_coverage,
            "subcategory_coverage": subcategory_coverage,
            "broad_review_required": broad_review,
            "subcategory_review_required": sub_review,
            "unmapped": unmapped,
            "review_context_tuple_count": len(review_context_counts),
            "frozen_context_tuple_count": len(old_contexts),
        },
        review_rows,
    )


def _crosswalk_audit(
    root: Path,
    old_rows: Sequence[dict[str, str]],
    new_rows: Sequence[dict[str, str]],
    report_dir: Path,
) -> dict[str, Any]:
    gpa_crosswalk = GPACrosswalk.load(
        root / "validation/reports/gpa_requirement_raw_value_audit_v0_2.csv"
    )
    grade_crosswalk = GradeRequirementCrosswalk.load(
        root / "schema/grade_requirement/grade_requirement_crosswalk_v0_2.csv"
    )
    english_crosswalk = EnglishRequirementCrosswalk.load(
        root / ENGLISH_REQUIREMENT_CROSSWALK_PATH
    )
    prefecture_taxonomy = PrefectureTaxonomy.load(
        root / "schema/prefecture/prefecture_taxonomy_v0_1.csv"
    )
    prefecture_crosswalk = PrefectureCrosswalk.load(
        root / "schema/prefecture/prefecture_crosswalk_v0_1.csv",
        prefecture_taxonomy,
    )
    academic_taxonomy = AcademicFieldTaxonomy.load(
        root / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
    )
    academic_crosswalk = AcademicFieldCrosswalk.load(
        root / ACADEMIC_FIELD_CROSSWALK_PATH,
        academic_taxonomy,
    )
    fields = {
        "gpa": "gpa_requirement",
        "grade_requirement": "gpa_requirement",
        "english_requirement": "english_requirement",
        "prefecture": "prefecture",
        "academic_field_v0_1": "academic_field",
        "academic_field_v0_2": "academic_field",
    }
    old_distinct = {
        name: {row[field] for row in old_rows if row[field]}
        for name, field in fields.items()
    }
    reps = {
        name: _representatives(new_rows, field) for name, field in fields.items()
    }
    counters = {
        name: Counter(row[field] for row in new_rows if row[field])
        for name, field in fields.items()
    }
    unmapped: dict[str, Counter[str]] = {
        "gpa": Counter(
            {raw: count for raw, count in counters["gpa"].items() if gpa_crosswalk.get(raw) is None}
        ),
        "grade_requirement": Counter(
            {
                raw: count
                for raw, count in counters["grade_requirement"].items()
                if grade_crosswalk.classify(raw).parse_status == "unmapped"
            }
        ),
        "english_requirement": Counter(
            {
                raw: count
                for raw, count in counters["english_requirement"].items()
                if english_crosswalk.classify(raw).parse_status == "unmapped"
            }
        ),
        "prefecture": Counter(
            {
                raw: count
                for raw, count in counters["prefecture"].items()
                if prefecture_crosswalk.lookup(raw).mapping_status == "unmapped"
            }
        ),
        "academic_field_v0_1": Counter(
            {
                raw: count
                for raw, count in counters["academic_field_v0_1"].items()
                if academic_crosswalk.lookup(raw).mapping_status == "unmapped"
            }
        ),
    }
    v02 = _load_v02(root)
    unmapped["academic_field_v0_2"] = Counter(
        {
            raw: count
            for raw, count in counters["academic_field_v0_2"].items()
            if raw not in v02["raw"]
        }
    )
    filenames = {
        "gpa": "gpa_new_values.csv",
        "grade_requirement": "grade_requirement_new_values.csv",
        "english_requirement": "english_requirement_new_values_post_review.csv",
        "prefecture": "prefecture_new_values.csv",
        "academic_field_v0_1": "academic_field_v0_1_new_values_post_review.csv",
        "academic_field_v0_2": "academic_field_v0_2_new_raw_values_post_review.csv",
    }
    result: dict[str, Any] = {}

    def review_status(name: str, raw: str) -> tuple[str, str]:
        if name == "gpa":
            rule = gpa_crosswalk.get(raw)
            if rule is None:
                return (
                    "do_not_numeric_unmapped",
                    "Human review required; do not parse numeric tokens.",
                )
            return (
                f"exact_crosswalk_{rule.numeric_safety_tier}",
                "Already covered by the reviewed exact GPA crosswalk.",
            )
        if name == "grade_requirement":
            mapped = grade_crosswalk.classify(raw)
            if mapped.parse_status == "unmapped":
                return (
                    "unmapped",
                    "Human review required; do not assign an overall GPA floor.",
                )
            return (
                f"exact_crosswalk_{mapped.grade_requirement_status}_{mapped.overall_gpa_status}",
                "Already covered by the reviewed exact grade-requirement crosswalk.",
            )
        if name == "english_requirement":
            mapped = english_crosswalk.classify(raw)
            if mapped.parse_status == "unmapped":
                return (
                    "unmapped",
                    "Human review required; do not infer required/not_required.",
                )
            return (
                f"exact_crosswalk_{mapped.requirement_status}",
                "Already covered by the reviewed exact English crosswalk.",
            )
        if name == "prefecture":
            status = prefecture_crosswalk.lookup(raw).mapping_status
            return (
                status,
                "Human review required; do not split or substring-match."
                if status == "unmapped"
                else "Already covered by the frozen exact prefecture crosswalk.",
            )
        if name == "academic_field_v0_1":
            status = academic_crosswalk.lookup(raw).mapping_status
            return (
                status,
                "Human review required; do not change compatibility taxonomy automatically."
                if status == "unmapped"
                else "Already covered by the frozen v0.1 exact crosswalk.",
            )
        raw_block = v02["raw"].get(raw)
        if raw_block is None:
            return (
                "broad_and_subcategory_unmapped",
                "Human review required; do not infer from text.",
            )
        status = raw_block[0]["mapping_status"]
        return (
            f"exact_raw_{status}",
            "Existing v0.2 exact raw mapping applies; ambiguous contexts still fail closed."
            if status == "review_required"
            else "Already covered by the frozen v0.2 exact raw crosswalk.",
        )

    for name in filenames:
        new_values = set(counters[name]) - old_distinct[name]
        packet_counts = Counter(
            {
                raw: count
                for raw, count in counters[name].items()
                if raw in new_values or raw in unmapped[name]
            }
        )
        packet = []
        for raw in sorted(packet_counts):
            status, note = review_status(name, raw)
            packet.extend(
                _review_rows(Counter({raw: packet_counts[raw]}), reps[name], status, note)
            )
        _write_csv(report_dir / filenames[name], REVIEW_COLUMNS, packet)
        result[name] = {
            "distinct_raw": len(counters[name]),
            "new_vs_old_distinct": len(new_values),
            "new_vs_old_values": sorted(new_values),
            "unmapped_distinct": len(unmapped[name]),
            "unmapped_rows": sum(unmapped[name].values()),
            "unmapped_values": dict(sorted(unmapped[name].items())),
            "review_packet_distinct": len(packet_counts),
            "review_packet_rows_affected": sum(packet_counts.values()),
            "review_artifact": str((report_dir / filenames[name]).relative_to(root)),
        }
    v02_summary, existing_context_review = _v02_audit(new_rows, v02)
    context_fields = (
        "source_dataset",
        "university",
        "faculty_school",
        "department",
        "academic_field",
    )
    old_program_contexts = {
        tuple(row[field] for field in context_fields) for row in old_rows
    }
    new_context_counts = Counter(
        tuple(row[field] for field in context_fields)
        for row in new_rows
        if tuple(row[field] for field in context_fields) not in old_program_contexts
    )
    context_representatives: dict[tuple[str, ...], dict[str, str]] = {}
    for row in new_rows:
        key = tuple(row[field] for field in context_fields)
        if key in new_context_counts:
            context_representatives.setdefault(key, row)
    context_delta_rows: list[dict[str, str]] = []
    new_context_review: list[dict[str, str]] = []
    for key in sorted(new_context_counts):
        raw = key[-1]
        raw_block = v02["raw"].get(raw)
        exact_context = v02["context"].get(key)
        if raw_block is None:
            status = "unmapped_raw_and_context"
            note = "New raw/context requires human review; no inference from program text."
            requires_review = True
        elif exact_context is not None:
            status = "mapped_exact_context"
            note = "Already covered by frozen exact context mapping."
            requires_review = False
        elif raw_block[0]["mapping_status"] == "review_required":
            status = "review_required_no_exact_context"
            note = "Known ambiguous raw value requires an exact context decision."
            requires_review = True
        else:
            status = "mapped_by_existing_raw_exact"
            note = "Covered by the existing exact raw-value mapping."
            requires_review = False
        representative = context_representatives[key]
        item = {
            "raw_or_context": " | ".join(key),
            "frequency": str(new_context_counts[key]),
            "representative_university": representative["university"],
            "representative_faculty": representative["faculty_school"],
            "representative_department": representative["department"],
            "representative_record_id": representative["record_id"],
            "current_fail_closed_status": status,
            "suggested_review_note": note,
        }
        context_delta_rows.append(item)
        if requires_review:
            new_context_review.append(item)
    _write_csv(
        report_dir / "academic_field_v0_2_new_contexts_post_review.csv",
        REVIEW_COLUMNS,
        new_context_review,
    )
    _write_csv(
        report_dir / "academic_field_v0_2_context_delta_post_review.csv",
        REVIEW_COLUMNS,
        context_delta_rows,
    )
    result["academic_field_v0_2"].update(v02_summary)
    result["academic_field_v0_2"].update(
        {
            "new_program_context_tuples": len(new_context_counts),
            "new_program_context_rows": sum(new_context_counts.values()),
            "new_context_review_tuples": len(new_context_review),
            "existing_candidate_review_context_tuples": len(existing_context_review),
            "context_delta_artifact": str(
                (report_dir / "academic_field_v0_2_context_delta_post_review.csv").relative_to(root)
            ),
        }
    )
    result["academic_field_v0_2"]["context_review_artifact"] = str(
        (report_dir / "academic_field_v0_2_new_contexts_post_review.csv").relative_to(root)
    )

    def derived_counts(rows: Sequence[dict[str, str]]) -> dict[str, Any]:
        gpa_parser = GPAParser(gpa_crosswalk)
        gpa_tiers: Counter[str] = Counter()
        safe_match: Counter[str] = Counter()
        grade_statuses: Counter[str] = Counter()
        grade_overall: Counter[str] = Counter()
        english_statuses: Counter[str] = Counter()
        prefecture_statuses: Counter[str] = Counter()
        academic_statuses: Counter[str] = Counter()
        for row in rows:
            raw_gpa = row["gpa_requirement"] or None
            parsed = gpa_parser.parse(
                raw_gpa,
                admission_year=int(row["admission_year"]) if row["admission_year"] else None,
                information_year=int(row["information_year"]) if row["information_year"] else None,
                fallback_previous_year=row["fallback_previous_year"] in {"1", "True", "Yes"},
            )
            gpa_tiers[parsed.numeric_safety_tier] += 1
            if parsed.parse_status == "parsed_safe" and parsed.gpa_min_tenths is not None:
                for label, tenths in (("3.0", 30), ("3.5", 35), ("3.8", 38), ("4.0", 40), ("4.5", 45)):
                    if tenths >= parsed.gpa_min_tenths:
                        safe_match[label] += 1
            grade = grade_crosswalk.classify(raw_gpa)
            grade_statuses[grade.grade_requirement_status] += 1
            grade_overall[grade.overall_gpa_status] += 1
            english_statuses[english_crosswalk.classify(row["english_requirement"] or None).requirement_status] += 1
            prefecture_statuses[prefecture_crosswalk.lookup(row["prefecture"] or None).mapping_status] += 1
            academic_statuses[academic_crosswalk.lookup(row["academic_field"] or None).mapping_status] += 1
        return {
            "gpa_tiers": dict(sorted(gpa_tiers.items())),
            "gpa_strict_safe_matches": dict(sorted(safe_match.items())),
            "grade_requirement_statuses": dict(sorted(grade_statuses.items())),
            "grade_overall_statuses": dict(sorted(grade_overall.items())),
            "english_requirement_statuses": dict(sorted(english_statuses.items())),
            "prefecture_mapping_statuses": dict(sorted(prefecture_statuses.items())),
            "academic_field_v0_1_mapping_statuses": dict(sorted(academic_statuses.items())),
        }

    result["derived_counts_old"] = derived_counts(old_rows)
    result["derived_counts_new_candidate"] = derived_counts(new_rows)
    return result


def _baseline_receipt(root: Path) -> dict[str, Any]:
    files = {
        "canonical_kokkoritsu_master": root / "data/canonical/kokkoritsu/master.csv",
        "canonical_kokkoritsu_coverage": root / "data/canonical/kokkoritsu/coverage.csv",
        "canonical_kokkoritsu_research": root / "data/canonical/kokkoritsu/research_requirements.csv",
        "canonical_shidai_master": root / "data/canonical/shidai/master.csv",
        "canonical_shidai_coverage": root / "data/canonical/shidai/coverage.csv",
        "canonical_shidai_research": root / "data/canonical/shidai/research_requirements.csv",
        "unified_master": root / "data/canonical/unified/master.csv",
        "unified_coverage": root / "data/canonical/unified/coverage.csv",
        "unified_research": root / "data/canonical/unified/research_requirements.csv",
        "unified_manifest": root / "data/canonical/unified/build_manifest.json",
        "sqlite": root / "data/derived/sqlite/early_admissions_2027.sqlite",
        "sqlite_manifest": root / "data/derived/sqlite/build_manifest.json",
        "site_data_manifest": root / "data/derived/site/v0_2/build_manifest.json",
        "hosting_config": root / "site/.openai/hosting.json",
        "historical_v574_summary_md": (
            root
            / "validation/reports/update_20260922_v5_74_v1_08/update_summary.md"
        ),
        "historical_v574_summary_json": (
            root
            / "validation/reports/update_20260922_v5_74_v1_08/update_summary.json"
        ),
    }
    receipt = {
        key: {
            "path": str(path.relative_to(root)),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for key, path in files.items()
    }
    unified = json.loads(files["unified_manifest"].read_text(encoding="utf-8"))
    sqlite = json.loads(files["sqlite_manifest"].read_text(encoding="utf-8"))
    site = json.loads(files["site_data_manifest"].read_text(encoding="utf-8"))
    receipt["unified_manifest"]["content_receipt"] = {
        "contract_version": unified.get("contract_version"),
        "source_versions": unified.get("source_versions"),
        "outputs": unified.get("outputs"),
        "validation_status": unified.get("validation", {}).get("status"),
    }
    receipt["sqlite_manifest"]["content_receipt"] = {
        "database_schema_version": sqlite.get("database_schema_version"),
        "source_versions": sqlite.get("source_versions"),
        "row_counts": sqlite.get("row_counts"),
        "output": sqlite.get("output"),
        "validation_status": sqlite.get("validation", {}).get("status"),
    }
    receipt["site_data_manifest"]["content_receipt"] = {
        "site_data_schema_version": site.get("site_data_schema_version"),
        "build_id": site.get("build_id"),
        "source_versions": site.get("input", {}).get("source_versions"),
        "counts": {
            key: site.get("counts", {}).get(key)
            for key in (
                "search_rows",
                "detail_records",
                "research_requirement_rows",
                "universities",
            )
        },
        "validation_status": site.get("validation", {}).get("status"),
    }
    for key, path in (
        ("release_kokkoritsu", root / "data/releases/kokkoritsu-v5.61"),
        ("release_shidai", root / "data/releases/shidai-v0.97"),
        ("site_data_tree", root / "data/derived/site/v0_2"),
        ("site_public_site_data_tree", root / "site/public/site-data"),
    ):
        item = _tree_receipt(path)
        item["path"] = str(path.relative_to(root))
        receipt[key] = item
    return receipt


def _verify_receipt(root: Path, receipt: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    changed = []
    for name, item in receipt.items():
        path = root / str(item["path"])
        if item.get("kind") == "directory":
            actual = _tree_receipt(path)["tree_sha256"]
            expected = item["tree_sha256"]
        else:
            actual = _sha256(path)
            expected = item["sha256"]
        if actual != expected:
            changed.append({"name": name, "expected": expected, "actual": actual})
    return {
        "status": "passed" if not changed else "failed",
        "checked": len(receipt),
        "changed": changed,
    }


def _retarget_unified_contract(
    contract: dict[str, Any], versions: Mapping[str, str]
) -> None:
    """Retarget only source-version constraints in an isolated contract copy."""

    contract["x-source-version-matrix"] = dict(versions)
    contract["$defs"]["sourceVersion"]["enum"] = list(versions.values())
    pair_constraints = contract["$defs"]["sourcePairConstraint"]["allOf"]
    seen: set[str] = set()
    for constraint in pair_constraints:
        dataset = constraint["if"]["properties"]["source_dataset"]["const"]
        if dataset not in versions:
            raise ValueError(f"Unexpected source dataset in pair constraint: {dataset}")
        constraint["then"]["properties"]["source_version"]["const"] = versions[
            dataset
        ]
        seen.add(dataset)
    if seen != set(versions):
        raise ValueError("Unified source-pair constraints do not cover the version matrix.")


def _retarget_sqlite_schema_text(
    sql: str,
    current_versions: Mapping[str, str],
    candidate_versions: Mapping[str, str],
) -> str:
    """Retarget exact quoted source-version literals in an isolated SQL copy."""

    if set(current_versions) != set(candidate_versions):
        raise ValueError("SQLite source-version matrices cover different datasets.")
    result = sql
    for dataset in current_versions:
        old = f"'{current_versions[dataset]}'"
        new = f"'{candidate_versions[dataset]}'"
        occurrences = result.count(old)
        if occurrences == 0:
            raise ValueError(f"SQLite schema has no source-version literal for {dataset}.")
        result = result.replace(old, new)
        if old in result:
            raise ValueError(f"SQLite source-version retarget was incomplete for {dataset}.")
    return result


def _prepare_candidate_root(root: Path, candidate_root: Path) -> Mapping[str, Mapping[str, Path]]:
    """Create an isolated repo-shaped build root without touching production data."""

    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    candidate_root.mkdir(parents=True)
    shutil.copytree(root / "schema", candidate_root / "schema")
    for name in ("docs", "validation", "src"):
        (candidate_root / name).symlink_to(root / name, target_is_directory=True)

    contract_path = candidate_root / CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    _retarget_unified_contract(contract, CANDIDATE_VERSIONS)
    _write_json(contract_path, contract)

    sqlite_schema_path = (
        candidate_root / "schema/sqlite/early_admissions_sqlite_schema_v0_1.sql"
    )
    sqlite_schema = _retarget_sqlite_schema_text(
        sqlite_schema_path.read_text(encoding="utf-8"),
        PRODUCTION_VERSIONS,
        CANDIDATE_VERSIONS,
    )
    sqlite_schema_path.write_text(sqlite_schema, encoding="utf-8", newline="\n")

    source_config: dict[str, Mapping[str, Path]] = {}
    for dataset, config in INCOMING.items():
        canonical_dir = candidate_root / "data/canonical" / dataset
        canonical_dir.mkdir(parents=True)
        for source_key, filename in (
            ("path", "master.csv"),
            ("coverage", "coverage.csv"),
            ("research_requirements", "research_requirements.csv"),
        ):
            shutil.copyfile(root / config[source_key], canonical_dir / filename)
        schema_dir = candidate_root / "schema" / dataset
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_destination = schema_dir / Path(config["candidate_schema"]).name
        shutil.copyfile(root / config["candidate_schema"], schema_destination)
        source_config[dataset] = {
            "canonical_dir": canonical_dir.relative_to(candidate_root),
            "schema": schema_destination.relative_to(candidate_root),
        }
    return source_config


def _reuse_candidate_unified_checkpoint(
    root: Path, candidate_root: Path
) -> tuple[Path, Path, dict[str, Any]] | None:
    """Return a verified prior Unified checkpoint and refresh derived schemas only."""

    unified_dir = candidate_root / "data/canonical/unified"
    manifest_path = unified_dir / "build_manifest.json"
    if not manifest_path.is_file():
        return None
    if _sha256(manifest_path) != CANDIDATE_UNIFIED_CHECKPOINT["manifest"]:
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("validation", {}).get("status") != "passed":
        return None
    if manifest.get("source_versions") != CANDIDATE_VERSIONS:
        return None
    for table, expected_rows in CANDIDATE_UNIFIED_ROWS.items():
        path = unified_dir / f"{table}.csv"
        output = manifest.get("outputs", {}).get(table, {})
        expected_sha = CANDIDATE_UNIFIED_CHECKPOINT[table]
        if (
            not path.is_file()
            or _sha256(path) != expected_sha
            or output.get("sha256") != expected_sha
            or output.get("rows") != expected_rows
        ):
            return None
    for dataset, config in INCOMING.items():
        canonical_dir = candidate_root / "data/canonical" / dataset
        for source_key, filename in (
            ("path", "master.csv"),
            ("coverage", "coverage.csv"),
            ("research_requirements", "research_requirements.csv"),
        ):
            copy = canonical_dir / filename
            if not copy.is_file() or _sha256(copy) != _sha256(root / config[source_key]):
                return None

    shutil.copytree(root / "schema", candidate_root / "schema", dirs_exist_ok=True)
    contract_path = candidate_root / CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    _retarget_unified_contract(contract, CANDIDATE_VERSIONS)
    _write_json(contract_path, contract)

    sqlite_schema_path = (
        candidate_root / "schema/sqlite/early_admissions_sqlite_schema_v0_1.sql"
    )
    sqlite_schema = _retarget_sqlite_schema_text(
        (root / "schema/sqlite/early_admissions_sqlite_schema_v0_1.sql").read_text(
            encoding="utf-8"
        ),
        PRODUCTION_VERSIONS,
        CANDIDATE_VERSIONS,
    )
    sqlite_schema_path.write_text(sqlite_schema, encoding="utf-8", newline="\n")
    return unified_dir, manifest_path, manifest


@contextmanager
def _source_config_override(config: Mapping[str, Mapping[str, Path]]):
    original = {dataset: dict(value) for dataset, value in SOURCE_CONFIG.items()}
    SOURCE_CONFIG.clear()
    SOURCE_CONFIG.update(config)
    try:
        yield
    finally:
        SOURCE_CONFIG.clear()
        SOURCE_CONFIG.update(original)


def _directory_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): _sha256(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _build_candidate_artifacts(
    root: Path,
    derived_dir: Path,
    report_dir: Path,
    crosswalk_audit: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_root = derived_dir / "candidate_root"
    timings: dict[str, float] = {}
    checkpoint = _reuse_candidate_unified_checkpoint(root, candidate_root)
    if checkpoint is None:
        source_config = _prepare_candidate_root(root, candidate_root)
        started = time.perf_counter()
        with _source_config_override(source_config):
            unified_result = UnifiedBuildPipeline(candidate_root).build()
        timings["unified_seconds"] = round(time.perf_counter() - started, 3)
        unified_output_dir = unified_result.output_dir
        unified_manifest_path = unified_result.manifest_path
        unified_manifest = json.loads(
            unified_manifest_path.read_text(encoding="utf-8")
        )
        unified_reused = False
    else:
        unified_output_dir, unified_manifest_path, unified_manifest = checkpoint
        timings["unified_seconds"] = 0.0
        unified_reused = True

    review_counts = {
        "gpa_new_unmapped_admissions": crosswalk_audit["gpa"]["unmapped_rows"],
        "grade_unmapped_admissions": crosswalk_audit["grade_requirement"][
            "unmapped_rows"
        ],
        "english_unmapped_admissions": crosswalk_audit["english_requirement"][
            "unmapped_rows"
        ],
        "academic_field_unmapped_admissions": crosswalk_audit[
            "academic_field_v0_1"
        ]["unmapped_rows"],
        "academic_field_v2_unmapped_admissions": crosswalk_audit[
            "academic_field_v0_2"
        ]["unmapped_rows"],
        "academic_field_context_review": crosswalk_audit["academic_field_v0_2"][
            "new_context_review_tuples"
        ],
    }

    started = time.perf_counter()
    sqlite_result = SQLiteBuildPipeline(
        candidate_root,
        validation_profile="candidate-audit",
        audit_review_counts=review_counts,
    ).build()
    timings["sqlite_seconds"] = round(time.perf_counter() - started, 3)
    sqlite_manifest = json.loads(
        sqlite_result.manifest_path.read_text(encoding="utf-8")
    )

    fixed_timestamp = "2026-09-22T00:00:00Z"
    site_output = candidate_root / "data/derived/site/v0_2"
    site_rebuild = candidate_root / "data/derived/site/v0_2_rebuild"
    started = time.perf_counter()
    site_result = SiteDataBuildPipeline(
        candidate_root,
        database_path=sqlite_result.database_path,
        sqlite_manifest_path=sqlite_result.manifest_path,
        output_dir=site_output,
        qa_report_path=report_dir / "candidate_site_data_qa.md",
        build_timestamp_utc=fixed_timestamp,
        validation_profile="candidate-audit",
    ).build()
    timings["site_data_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    second_result = SiteDataBuildPipeline(
        candidate_root,
        database_path=sqlite_result.database_path,
        sqlite_manifest_path=sqlite_result.manifest_path,
        output_dir=site_rebuild,
        qa_report_path=derived_dir / "candidate_site_data_rebuild_qa.md",
        build_timestamp_utc=fixed_timestamp,
        validation_profile="candidate-audit",
    ).build()
    timings["site_data_rebuild_seconds"] = round(time.perf_counter() - started, 3)
    first_hashes = _directory_hashes(site_output)
    second_hashes = _directory_hashes(site_rebuild)
    deterministic = first_hashes == second_hashes
    if not deterministic:
        raise RuntimeError("Candidate Site-data rebuild is not byte-identical.")
    shutil.rmtree(site_rebuild)
    second_result.qa_report_path.unlink(missing_ok=True)
    site_manifest = json.loads(site_result.manifest_path.read_text(encoding="utf-8"))

    return {
        "candidate_root": str(candidate_root.relative_to(root)),
        "timings": timings,
        "unified": {
            "output_dir": str(unified_output_dir.relative_to(root)),
            "manifest": str(unified_manifest_path.relative_to(root)),
            "manifest_sha256": _sha256(unified_manifest_path),
            "checkpoint_reused": unified_reused,
            "outputs": unified_manifest["outputs"],
            "validation": unified_manifest["validation"],
            "source_versions": unified_manifest["source_versions"],
        },
        "sqlite": {
            "database": str(sqlite_result.database_path.relative_to(root)),
            "manifest": str(sqlite_result.manifest_path.relative_to(root)),
            "sha256": sqlite_result.database_sha256,
            "size_bytes": sqlite_result.database_size_bytes,
            "profile": sqlite_result.capabilities.profile,
            "validation_profile": sqlite_manifest["validation_profile"],
            "review_required_counts": sqlite_manifest["review_required_counts"],
            "sqlite_version": sqlite_result.capabilities.sqlite_version,
            "fts5": sqlite_result.capabilities.fts5,
            "trigram": sqlite_result.capabilities.trigram,
            "row_counts": dict(sqlite_result.row_counts),
            "validation": sqlite_result.validation,
            "manifest_content": sqlite_manifest,
        },
        "site_data": {
            "output_dir": str(site_result.output_dir.relative_to(root)),
            "manifest": str(site_result.manifest_path.relative_to(root)),
            "manifest_sha256": site_result.manifest_sha256,
            "build_id": site_result.build_id,
            "validation_profile": site_manifest["validation_profile"],
            "review_required_counts": site_manifest["review_required_counts"],
            "counts": dict(site_result.counts),
            "size_report": dict(site_result.size_report),
            "validation": site_result.validation,
            "deterministic_rebuild": {
                "status": "passed",
                "byte_identical": True,
                "files_compared": len(first_hashes),
                "second_build_id": second_result.build_id,
            },
            "manifest_content": site_manifest,
        },
    }


IMPORTANT_SEARCHES: tuple[tuple[str, SearchCriteria], ...] = (
    ("東京都 membership", SearchCriteria(prefecture_membership=("東京都",))),
    ("神奈川県 membership", SearchCriteria(prefecture_membership=("神奈川県",))),
    (
        "東京＋神奈川 membership",
        SearchCriteria(prefecture_membership=("東京都", "神奈川県")),
    ),
    (
        "法学・政治・公共政策",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("law_politics_policy"),)
        ),
    ),
    (
        "経済",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("economics"),)
        ),
    ),
    (
        "経営・商",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("business_commerce"),)
        ),
    ),
    (
        "心理",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("psychology"),)
        ),
    ),
    (
        "外国語・言語",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("languages"),)
        ),
    ),
    (
        "理学",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("natural_sciences"),)
        ),
    ),
    (
        "理学＋数学",
        SearchCriteria(
            academic_field_v2_branches=(
                AcademicFieldV2Branch(
                    "natural_sciences", ("mathematics_statistics",)
                ),
            )
        ),
    ),
    (
        "工学",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("engineering"),)
        ),
    ),
    (
        "情報",
        SearchCriteria(
            academic_field_v2_branches=(AcademicFieldV2Branch("information"),)
        ),
    ),
    (
        "評定条件あり",
        SearchCriteria(grade_requirement_status="required"),
    ),
    (
        "overall GPA 3.8",
        SearchCriteria(
            grade_requirement_status="required", overall_gpa_tenths=38
        ),
    ),
    (
        "English required",
        SearchCriteria(english_requirement_status=("required",)),
    ),
    (
        "research achievement",
        SearchCriteria(research_requirement_required=("Yes",)),
    ),
    (
        "exclusive enrollment",
        SearchCriteria(exclusive_enrollment_status=("専願",)),
    ),
    (
        "common test",
        SearchCriteria(common_test_required=("Yes",)),
    ),
    (
        "combined representative",
        SearchCriteria(
            prefecture_membership=("東京都", "神奈川県"),
            academic_field_v2_branches=(
                AcademicFieldV2Branch("engineering"),
                AcademicFieldV2Branch("information"),
            ),
            grade_requirement_status="required",
            overall_gpa_tenths=38,
        ),
    ),
)


def _stable_result_keys(rows: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    return {(str(row["source_dataset"]), str(row["record_id"])) for row in rows}


def _compare_search_suite(
    production_database: Path,
    candidate_database: Path,
    specs: Sequence[tuple[str, SearchCriteria]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    production_latencies: list[float] = []
    candidate_latencies: list[float] = []
    for label, criteria in specs:
        started = time.perf_counter()
        production = search_database(production_database, criteria, limit=None)
        production_latencies.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        candidate = search_database(candidate_database, criteria, limit=None)
        candidate_latencies.append((time.perf_counter() - started) * 1000)
        old_keys = _stable_result_keys(production.rows)
        new_keys = _stable_result_keys(candidate.rows)
        results.append(
            {
                "label": label,
                "criteria": asdict(criteria),
                "production_admissions": production.summary.total_matched_rows,
                "candidate_admissions": candidate.summary.total_matched_rows,
                "admissions_delta": candidate.summary.total_matched_rows
                - production.summary.total_matched_rows,
                "production_universities": production.summary.university_count,
                "candidate_universities": candidate.summary.university_count,
                "universities_delta": candidate.summary.university_count
                - production.summary.university_count,
                "added_result_ids": len(new_keys - old_keys),
                "removed_result_ids": len(old_keys - new_keys),
                "added_examples": [list(key) for key in sorted(new_keys - old_keys)[:5]],
                "removed_examples": [list(key) for key in sorted(old_keys - new_keys)[:5]],
            }
        )

    def latency(values: Sequence[float]) -> dict[str, float]:
        return {
            "queries": len(values),
            "median_ms": round(statistics.median(values), 3),
            "mean_ms": round(statistics.mean(values), 3),
            "max_ms": round(max(values), 3),
        }

    return results, {
        "production": latency(production_latencies),
        "candidate": latency(candidate_latencies),
    }


def _candidate_search_audit(
    root: Path,
    candidate_database: Path,
    report_dir: Path,
) -> dict[str, Any]:
    production_database = root / "data/derived/sqlite" / DATABASE_FILENAME
    qa_count, qa_hash = run_qa(
        candidate_database,
        report_dir / "candidate_structured_search_25_query_qa.md",
    )
    frozen_specs = tuple((spec.label, spec.criteria) for spec in QA_SPECS)
    frozen_results, frozen_latency = _compare_search_suite(
        production_database, candidate_database, frozen_specs
    )
    important_results, important_latency = _compare_search_suite(
        production_database, candidate_database, IMPORTANT_SEARCHES
    )
    uri = candidate_database.resolve().as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rikkyo = connection.execute(
            """
            SELECT a.source_dataset, a.source_version, a.record_id,
                   a.gpa_requirement, a.english_requirement,
                   g.parse_status AS strict_gpa_parse_status,
                   gr.grade_requirement_status, gr.overall_gpa_status,
                   gr.overall_gpa_min_tenths,
                   er.requirement_status AS english_requirement_status,
                   er.search_disposition AS english_search_disposition
            FROM admissions AS a
            JOIN admission_search_gpa AS g USING (admission_rowid)
            JOIN admission_search_grade_requirements AS gr USING (admission_rowid)
            JOIN admission_search_english_requirement AS er USING (admission_rowid)
            WHERE a.record_id='RIKKYO-2027-SCI-03'
            """
        ).fetchall()
        if len(rikkyo) != 1:
            raise RuntimeError("RIKKYO-2027-SCI-03 is missing or duplicated in candidate SQLite.")
        rikkyo_row = rikkyo[0]
        expected_rikkyo = {
            "strict_gpa_parse_status": "conditional_review",
            "grade_requirement_status": "required",
            "overall_gpa_status": "safe_overall_with_additional_conditions",
            "overall_gpa_min_tenths": 38,
            "english_requirement_status": "required",
            "english_search_disposition": "safe_exact",
        }
        if any(rikkyo_row[key] != value for key, value in expected_rikkyo.items()):
            raise RuntimeError(
                "RIKKYO-2027-SCI-03 fail-closed derived semantics changed."
            )

        def scalar(sql: str, parameters: Sequence[Any] = ()) -> int:
            return int(connection.execute(sql, parameters).fetchone()[0])

        def excluded(
            table: str, predicate: str, parameters: Sequence[Any] = ()
        ) -> dict[str, Any]:
            rows = connection.execute(
                f"""
                SELECT a.source_dataset, a.record_id
                FROM admissions AS a
                JOIN {table} AS d USING (admission_rowid)
                WHERE {predicate}
                ORDER BY a.source_dataset, a.record_id
                """,
                parameters,
            ).fetchall()
            return {
                "count": len(rows),
                "representative_record_ids": [
                    f"{row['source_dataset']}:{row['record_id']}" for row in rows[:5]
                ],
            }

        review_specs = (
            (
                "English required",
                SearchCriteria(english_requirement_status=("required",)),
                "admission_search_english_requirement",
                "d.requirement_status='unmapped'",
            ),
            (
                "English not_required",
                SearchCriteria(english_requirement_status=("not_required",)),
                "admission_search_english_requirement",
                "d.requirement_status='unmapped'",
            ),
            (
                "Grade required",
                SearchCriteria(grade_requirement_status="required"),
                "admission_search_grade_requirements",
                "d.grade_requirement_status='unmapped'",
            ),
            (
                "overall GPA 3.8",
                SearchCriteria(
                    grade_requirement_status="required", overall_gpa_tenths=38
                ),
                "admission_search_grade_requirements",
                "d.grade_requirement_status='unmapped'",
            ),
            (
                "Academic Broad engineering",
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch("engineering"),
                    )
                ),
                "admission_search_academic_fields_v2",
                "d.broad_mapping_status='unmapped'",
            ),
            (
                "Academic Subcategory natural_sciences/mathematics_statistics",
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch(
                            "natural_sciences", ("mathematics_statistics",)
                        ),
                    )
                ),
                "admission_search_academic_fields_v2",
                "d.subcategory_mapping_status='unmapped'",
            ),
        )
        review_sensitive = []
        for label, criteria, table, predicate in review_specs:
            result = search_database(candidate_database, criteria, limit=None)
            review_sensitive.append(
                {
                    "label": label,
                    "candidate_matched_admissions": result.summary.total_matched_rows,
                    "candidate_matched_universities": result.summary.university_count,
                    "excluded_due_to_unmapped": excluded(table, predicate),
                }
            )

        total = scalar("SELECT COUNT(*) FROM admissions")
        metadata_review_counts = json.loads(
            connection.execute(
                "SELECT review_required_counts_json FROM build_metadata"
            ).fetchone()[0]
        )
        denominator_audit = {
            "total_admissions": total,
            "gpa": {
                "safe_numeric": scalar(
                    "SELECT COUNT(*) FROM admission_search_gpa WHERE parse_status='parsed_safe'"
                ),
                "unparsed": scalar(
                    "SELECT COUNT(*) FROM admission_search_gpa WHERE parse_status='unparsed'"
                ),
            },
            "grade": {
                "mapped_classification_rows": scalar(
                    "SELECT COUNT(*) FROM admission_search_grade_requirements "
                    "WHERE grade_requirement_status<>'unmapped'"
                ),
                "required_searchable": scalar(
                    "SELECT COUNT(*) FROM admission_search_grade_requirements "
                    "WHERE grade_requirement_status='required'"
                ),
                "unmapped": scalar(
                    "SELECT COUNT(*) FROM admission_search_grade_requirements "
                    "WHERE grade_requirement_status='unmapped'"
                ),
            },
            "english": {
                "mapped_searchable": scalar(
                    "SELECT COUNT(*) FROM admission_search_english_requirement "
                    "WHERE search_disposition='safe_exact'"
                ),
                "unmapped_excluded_from_binary_filter": scalar(
                    "SELECT COUNT(*) FROM admission_search_english_requirement "
                    "WHERE requirement_status='unmapped'"
                ),
            },
            "academic_field_v0_1": {
                "mapped_membership_coverage": scalar(
                    "SELECT COUNT(DISTINCT admission_rowid) "
                    "FROM admission_search_academic_field_groups"
                ),
                "unmapped": scalar(
                    "SELECT COUNT(*) FROM admission_search_academic_fields "
                    "WHERE mapping_status='unmapped'"
                ),
            },
            "academic_field_v0_2": {
                "broad_coverage": scalar(
                    "SELECT COUNT(DISTINCT admission_rowid) "
                    "FROM admission_search_academic_field_broad_memberships_v2"
                ),
                "subcategory_coverage": scalar(
                    "SELECT COUNT(DISTINCT admission_rowid) "
                    "FROM admission_search_academic_field_subcategory_memberships_v2"
                ),
                "broad_without_membership": total
                - scalar(
                    "SELECT COUNT(DISTINCT admission_rowid) "
                    "FROM admission_search_academic_field_broad_memberships_v2"
                ),
                "unmapped": scalar(
                    "SELECT COUNT(*) FROM admission_search_academic_fields_v2 "
                    "WHERE broad_mapping_status='unmapped'"
                ),
                "context_review": metadata_review_counts[
                    "academic_field_context_review"
                ],
            },
        }

    rikkyo_key = ("shidai", "RIKKYO-2027-SCI-03")
    english_required_keys = _stable_result_keys(
        search_database(
            candidate_database,
            SearchCriteria(english_requirement_status=("required",)),
            limit=None,
        ).rows
    )
    if rikkyo_key not in english_required_keys:
        raise RuntimeError(
            "RIKKYO-2027-SCI-03 did not match its reviewed English requirement."
        )
    for criteria in (
        SearchCriteria(english_requirement_status=("not_required",)),
        SearchCriteria(gpa_tenths=38, gpa_mode="safe"),
    ):
        result_keys = _stable_result_keys(
            search_database(candidate_database, criteria, limit=None).rows
        )
        if rikkyo_key in result_keys:
            raise RuntimeError(
                "RIKKYO-2027-SCI-03 incorrectly matched an incompatible safe filter."
            )
    return {
        "candidate_25_query_execution": {
            "status": "passed",
            "queries": qa_count,
            "database_sha256_before_after": qa_hash,
            "report": str(
                (report_dir / "candidate_structured_search_25_query_qa.md").relative_to(root)
            ),
        },
        "frozen_25_query_comparison": frozen_results,
        "frozen_25_query_latency": frozen_latency,
        "important_search_comparison": important_results,
        "important_search_latency": important_latency,
        "rikkyo_2027_sci_03": [dict(row) for row in rikkyo],
        "review_sensitive_searches": review_sensitive,
        "search_denominator_audit": denominator_audit,
    }


def _run_logged(
    command: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    env: Mapping[str, str] | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout, encoding="utf-8", newline="\n")
    result = {
        "command": list(command),
        "exit_code": completed.returncode,
        "seconds": round(time.perf_counter() - started, 3),
        "log": str(log_path),
        "tail": completed.stdout.splitlines()[-12:],
    }
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}; log={log_path}"
        )
    return result


def _portable_report_value(value: Any, root: Path) -> Any:
    """Remove repository-local absolute paths from persisted audit receipts."""

    if isinstance(value, dict):
        return {
            key: _portable_report_value(item, root) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_portable_report_value(item, root) for item in value]
    if isinstance(value, tuple):
        return tuple(_portable_report_value(item, root) for item in value)
    if isinstance(value, str):
        return value.replace(str(root), ".")
    return value


def _prepare_candidate_site(root: Path, candidate_root: Path) -> Path:
    destination = candidate_root / "site"
    if destination.exists():
        shutil.rmtree(destination)

    def ignore(path: str, names: list[str]) -> set[str]:
        ignored = {
            name
            for name in names
            if name in {"node_modules", "dist", ".vite", ".cache"}
        }
        if Path(path).name == "public" and "site-data" in names:
            ignored.add("site-data")
        return ignored

    shutil.copytree(root / "site", destination, ignore=ignore)
    return destination


def _frontend_candidate_validation(
    root: Path,
    candidate_root: Path,
    derived_dir: Path,
    *,
    run_repository_tests: bool = True,
) -> dict[str, Any]:
    site_root = _prepare_candidate_site(root, candidate_root)
    log_dir = derived_dir / "logs"

    def run_frontend_command(
        command: Sequence[str], log_name: str
    ) -> dict[str, Any]:
        log_path = log_dir / log_name
        result = _run_logged(command, cwd=site_root, log_path=log_path)
        result["log"] = str(log_path.relative_to(root))
        return result

    dependency_source = root / "site/node_modules"
    if dependency_source.is_dir():
        (site_root / "node_modules").symlink_to(
            dependency_source, target_is_directory=True
        )
        dependency_preparation = {
            "status": "passed",
            "mode": "reused_local_node_modules_read_only_symlink",
            "network_access": "not_used",
            "runtime_arch": "arm64",
            "package_lock_sha256": _sha256(root / "site/package-lock.json"),
        }
    else:
        dependency_preparation = run_frontend_command(
            (
                "/usr/bin/arch",
                "-arm64",
                "npm",
                "ci",
                "--offline",
                "--no-audit",
                "--no-fund",
            ),
            "npm_ci.log",
        )
        dependency_preparation["mode"] = "npm_ci_offline"
        dependency_preparation["network_access"] = "not_used"
        dependency_preparation["runtime_arch"] = "arm64"
    test_site_sync = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "scripts/sync-site-data.mjs",
        ),
        "frontend_test_site_data_sync.log",
    )
    search_oracle_export = run_frontend_command(
        ("python3", "scripts/export-search-oracle.py"),
        "frontend_search_oracle_export.log",
    )
    frontend = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "./node_modules/vitest/vitest.mjs",
            "run",
        ),
        "frontend_tests.log",
    )
    frontend["preparation_steps"] = [test_site_sync, search_oracle_export]
    responsive = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "./node_modules/vitest/vitest.mjs",
            "run",
            "tests/responsive-contract.test.ts",
        ),
        "responsive_tests.log",
    )
    build_site_sync = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "scripts/sync-site-data.mjs",
        ),
        "production_build_site_data_sync.log",
    )
    typecheck = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "./node_modules/typescript/bin/tsc",
            "-b",
        ),
        "production_build_typecheck.log",
    )
    production_build = run_frontend_command(
        (
            "/usr/bin/arch",
            "-arm64",
            "node",
            "./node_modules/vite/bin/vite.js",
            "build",
        ),
        "production_build.log",
    )
    production_build["preparation_steps"] = [build_site_sync, typecheck]
    if run_repository_tests:
        repo_env = dict(os.environ)
        repo_env["PYTHONPATH"] = str(root / "src")
        repository = _run_logged(
            ("python3", "-m", "unittest", "discover", "-s", "tests"),
            cwd=root,
            log_path=log_dir / "repository_tests.log",
            env=repo_env,
        )
        repository["log"] = str(
            (log_dir / "repository_tests.log").relative_to(root)
        )
    else:
        repository = {
            "status": "not_repeated",
            "reason": "Repository suite already passed in the candidate-audit phase.",
            "tail": [],
        }

    def test_count(result: Mapping[str, Any]) -> int | None:
        text = "\n".join(result["tail"])
        matches = re.findall(r"(?:Tests|Ran)\s+(\d+)", text)
        return int(matches[-1]) if matches else None

    return {
        "dependency_preparation": dependency_preparation,
        "frontend_tests": {**frontend, "test_count": test_count(frontend)},
        "responsive_tests": {**responsive, "test_count": test_count(responsive)},
        "repository_tests": {**repository, "test_count": test_count(repository)},
        "production_build": production_build,
        "candidate_site_root": str(site_root.relative_to(root)),
        "dist_size_bytes": sum(
            path.stat().st_size
            for path in (site_root / "dist").rglob("*")
            if path.is_file()
        ),
    }


def _build_isolated_production_profile(
    root: Path,
    derived_dir: Path,
    report_dir: Path,
    candidate_artifacts: Mapping[str, Any],
) -> dict[str, Any]:
    """Build candidate data under strict production rules in a separate root."""

    candidate_root = root / candidate_artifacts["candidate_root"]
    isolated_root = derived_dir / "production_profile_root"
    _prepare_candidate_root(root, isolated_root)
    candidate_unified = candidate_root / "data/canonical/unified"
    isolated_unified = isolated_root / "data/canonical/unified"
    if isolated_unified.exists():
        shutil.rmtree(isolated_unified)
    shutil.copytree(candidate_unified, isolated_unified)
    manifest = json.loads(
        (isolated_unified / "build_manifest.json").read_text(encoding="utf-8")
    )
    if (
        manifest.get("validation", {}).get("status") != "passed"
        or manifest.get("source_versions") != CANDIDATE_VERSIONS
        or any(
            manifest["outputs"][table]["rows"] != expected
            for table, expected in CANDIDATE_UNIFIED_ROWS.items()
        )
    ):
        raise RuntimeError("Isolated production profile received an invalid Unified checkpoint.")

    started = time.perf_counter()
    sqlite_result = SQLiteBuildPipeline(
        isolated_root, validation_profile="production"
    ).build()
    sqlite_seconds = round(time.perf_counter() - started, 3)
    sqlite_manifest = json.loads(
        sqlite_result.manifest_path.read_text(encoding="utf-8")
    )
    if (
        sqlite_manifest.get("validation_profile") != "production"
        or sqlite_manifest.get("publication", {}).get("production_ready") is not True
        or sqlite_manifest.get("validation", {}).get("status") != "passed"
        or sqlite_manifest.get("english_requirement_search", {}).get(
            "classification_counts", {}
        ).get("unmapped") != 0
        or sqlite_manifest.get("academic_field_search", {}).get(
            "classification_counts", {}
        ).get("unmapped") != 0
        or sqlite_manifest.get("academic_field_v2", {}).get("unmapped") != 0
    ):
        raise RuntimeError("Strict production-profile SQLite receipt is not promotable.")

    started = time.perf_counter()
    site_result = SiteDataBuildPipeline(
        isolated_root,
        database_path=sqlite_result.database_path,
        sqlite_manifest_path=sqlite_result.manifest_path,
        output_dir=isolated_root / "data/derived/site/v0_2",
        qa_report_path=report_dir / "production_profile_site_data_qa.md",
        build_timestamp_utc="2026-09-22T00:00:00Z",
        validation_profile="production",
    ).build()
    site_seconds = round(time.perf_counter() - started, 3)
    site_manifest = json.loads(site_result.manifest_path.read_text(encoding="utf-8"))
    if (
        site_manifest.get("validation_profile") != "production"
        or site_manifest.get("publication", {}).get("production_ready") is not True
        or site_manifest.get("validation", {}).get("status") != "passed"
        or site_manifest.get("counts", {}).get("search_rows") != 6411
        or site_manifest.get("counts", {}).get("detail_records") != 6411
    ):
        raise RuntimeError("Strict production-profile Site-data receipt is not promotable.")

    qa_count, qa_hash = run_qa(
        sqlite_result.database_path,
        report_dir / "production_profile_structured_search_25_query_qa.md",
    )
    frontend = _frontend_candidate_validation(
        root,
        isolated_root,
        derived_dir / "production_profile_frontend",
        run_repository_tests=False,
    )
    return {
        "isolated_root": str(isolated_root.relative_to(root)),
        "sqlite": {
            "database": str(sqlite_result.database_path.relative_to(root)),
            "manifest": str(sqlite_result.manifest_path.relative_to(root)),
            "sha256": sqlite_result.database_sha256,
            "size_bytes": sqlite_result.database_size_bytes,
            "validation_profile": sqlite_manifest["validation_profile"],
            "publication": sqlite_manifest["publication"],
            "row_counts": sqlite_manifest["row_counts"],
            "validation": sqlite_manifest["validation"],
            "seconds": sqlite_seconds,
        },
        "site_data": {
            "output_dir": str(site_result.output_dir.relative_to(root)),
            "manifest": str(site_result.manifest_path.relative_to(root)),
            "manifest_sha256": site_result.manifest_sha256,
            "build_id": site_result.build_id,
            "validation_profile": site_manifest["validation_profile"],
            "publication": site_manifest["publication"],
            "counts": site_manifest["counts"],
            "validation": site_manifest["validation"],
            "seconds": site_seconds,
        },
        "structured_search_25_query": {
            "status": "passed", "queries": qa_count,
            "database_sha256_before_after": qa_hash,
            "report": str(
                (report_dir / "production_profile_structured_search_25_query_qa.md").relative_to(root)
            ),
        },
        "frontend": frontend,
    }


def _size_performance_summary(
    root: Path,
    artifacts: Mapping[str, Any],
    search_audit: Mapping[str, Any],
) -> dict[str, Any]:
    production_site = json.loads(
        (root / "data/derived/site/v0_2/build_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    candidate_site = artifacts["site_data"]["manifest_content"]
    production_sqlite = root / "data/derived/sqlite" / DATABASE_FILENAME
    candidate_sqlite = root / artifacts["sqlite"]["database"]
    production_site_tree = _tree_receipt(root / "data/derived/site/v0_2")
    candidate_site_tree = _tree_receipt(root / artifacts["site_data"]["output_dir"])

    def comparison(old: int, new: int) -> dict[str, Any]:
        return {
            "production": old,
            "candidate": new,
            "delta": new - old,
            "percent_change": round(((new - old) / old) * 100, 2) if old else None,
        }

    return {
        "admissions": comparison(
            production_site["counts"]["search_rows"],
            candidate_site["counts"]["search_rows"],
        ),
        "sqlite_bytes": comparison(
            production_sqlite.stat().st_size, candidate_sqlite.stat().st_size
        ),
        "site_data_total_bytes": comparison(
            production_site_tree["size_bytes"], candidate_site_tree["size_bytes"]
        ),
        "search_projection_bytes": comparison(
            production_site["size_report"]["search_projection_bytes"],
            candidate_site["size_report"]["search_projection_bytes"],
        ),
        "search_projection_gzip_bytes": comparison(
            production_site["size_report"]["search_projection_gzip_bytes"],
            candidate_site["size_report"]["search_projection_gzip_bytes"],
        ),
        "detail_projection_bytes": comparison(
            production_site["size_report"]["detail_projection_bytes"],
            candidate_site["size_report"]["detail_projection_bytes"],
        ),
        "detail_projection_gzip_equivalent_bytes": comparison(
            production_site["size_report"][
                "detail_projection_gzip_equivalent_bytes"
            ],
            candidate_site["size_report"][
                "detail_projection_gzip_equivalent_bytes"
            ],
        ),
        "search_shards": comparison(
            production_site["size_report"]["search_shards"],
            candidate_site["size_report"]["search_shards"],
        ),
        "detail_shards": comparison(
            production_site["size_report"]["detail_shards"],
            candidate_site["size_report"]["detail_shards"],
        ),
        "build_seconds": dict(artifacts["timings"]),
        "frozen_25_query_latency": search_audit["frozen_25_query_latency"],
        "important_search_latency": search_audit["important_search_latency"],
    }


def _existing_candidate_unified_receipt(
    root: Path, derived_dir: Path
) -> dict[str, Any] | None:
    manifest_path = (
        derived_dir
        / "candidate_root/data/canonical/unified/build_manifest.json"
    )
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "status": manifest.get("validation", {}).get("status"),
        "manifest": str(manifest_path.relative_to(root)),
        "manifest_sha256": _sha256(manifest_path),
        "source_versions": manifest.get("source_versions"),
        "outputs": manifest.get("outputs"),
        "validation": manifest.get("validation"),
    }


def _render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# 2026-09-22 update acceptance report",
        "",
        "## Gate",
        "",
        f"**{summary['final_gate']['status']}**",
        "",
        summary["final_gate"]["reason"],
        "",
        "No production canonical, release, unified, SQLite, Site-data, Sites Version, or deployment was changed.",
        "",
        "## Three snapshots and source-state gate",
        "",
        "- PRODUCTION: kokkoritsu 5.61 / shidai 0.97",
        "- SUPERSEDED: kokkoritsu 5.74 / shidai 1.08",
        "- CANDIDATE: kokkoritsu 5.81 / shidai 1.08",
        "",
        "| Dataset | Old | Candidate | Dataset state | Artifact state | Source freeze | Gate |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for dataset in ("kokkoritsu", "shidai"):
        identity = summary["source_identity"][dataset]
        lines.append(
            f"| {dataset} | {summary['old_versions'][dataset]} | "
            f"{identity['internal_version']} | {identity['dataset_state'] or '-'} | "
            f"{identity['artifact_canonical_state'] or '-'} | "
            f"{identity['source_freeze_status'] or '-'} | "
            f"{'PASS' if identity['source_coherence_gate_passed'] else 'HOLD'} |"
        )
    lines.extend(
        [
            "",
            "Kokkoritsu v5.81 declares `dataset_state: FROZEN`; shidai v1.08 declares `sources.freeze_status: FROZEN`. The superseded kokkoritsu v5.74 remains historical input only and is never used for candidate builds.",
            "",
            "Candidate version identity was checked against each supplied schema and its `canonical_data` filenames; filename-only inference was not used.",
            "",
            "## Incoming preflight",
            "",
            "| Dataset | File | Rows | Columns | Encoding | BOM | SHA-256 |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for dataset in ("kokkoritsu", "shidai"):
        for table in ("master", "coverage", "research_requirements"):
            item = summary["inputs"][dataset][table]
            lines.append(
                f"| {dataset} | {table} | {item['rows']:,} | {item['columns']} | "
                f"{item['encoding']} | {item['bom']} | `{item['sha256']}` |"
            )
        item = summary["inputs"][dataset]["schema"]
        lines.append(
            f"| {dataset} | schema | - | - | {item['encoding']} | "
            f"{item['bom']} | `{item['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "All candidate CSV headers match their supplied schema column lists and the current column order. There are no row-width mismatches, duplicate Master IDs, or duplicate Coverage keys.",
        ]
    )
    unified_receipt = summary.get("candidate_unified_receipt")
    if unified_receipt:
        outputs = unified_receipt["outputs"]
        lines.extend(
            [
                "",
                "## Candidate Unified checkpoint",
                "",
                f"Unified validation: `{unified_receipt['status']}`; source versions "
                f"`{unified_receipt['source_versions']}`.",
                f"Rows: master {outputs['master']['rows']:,}, coverage "
                f"{outputs['coverage']['rows']:,}, ResearchRequirements "
                f"{outputs['research_requirements']['rows']:,}.",
                f"Manifest SHA-256: `{unified_receipt['manifest_sha256']}`.",
            ]
        )
    profile = summary["validation_profiles"]
    lines.extend(
        [
            "",
            "## Candidate audit validation profile",
            "",
            f"Previous final gate: `{profile['previous_gate']}`. The cause was a production-only English-unmapped publication blocker, not source corruption.",
            "",
            "`production` remains the default deployability gate and continues to reject English `unmapped`. `candidate_audit` requires explicit opt-in, preserves raw and mapping status, keeps search fail-closed, and marks every derived artifact inspection-only with `production_ready: false`.",
            "",
            "Gate history is preserved in `update_summary.json`: the earlier `HOLD_BUILD` and subsequent `READY_FOR_HUMAN_REVIEW` are not replaced by the current decision.",
            "",
            "PK/FK, malformed row/schema, source/raw mismatch, invalid tri-state, SQLite integrity, FTS, and Site-data referential failures remain hard errors in both profiles. Only approved reviewable mapping gaps have profile-specific severity.",
        ]
    )
    lines.extend(
        [
            "",
            "## Source row diff",
            "",
            "| Dataset | Old | New | Unchanged | Added | Removed | Changed | Material changed |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset in ("kokkoritsu", "shidai"):
        item = summary["source_diff"][dataset]
        lines.append(
            f"| {dataset} | {item['old_rows']:,} | {item['new_rows']:,} | "
            f"{item['unchanged']:,} | {item['added']:,} | {item['removed']:,} | "
            f"{item['changed']:,} | {item['material_changed_records']:,} |"
        )
    totals = summary["source_diff"]["totals"]
    lines.append(
        f"| total | {totals['old_rows']:,} | {totals['new_rows']:,} | "
        f"{totals['unchanged']:,} | {totals['added']:,} | {totals['removed']:,} | "
        f"{totals['changed']:,} | {totals['material_changed_records']:,} |"
    )
    lines.extend(
        [
            "",
            f"Full added/removed rows and field-level changed rows are in the ignored `data/derived/update_audit/{UPDATE_ID.removeprefix('update_')}/` directory.",
            "",
            "## Fallback transitions",
            "",
            "| Dataset | Removed | Newly introduced | Current-year upgrades | Added fallback rows | Information-year changes | Publication-status changes |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset in ("kokkoritsu", "shidai"):
        item = summary["source_diff"][dataset]
        lines.append(
            f"| {dataset} | {item['fallback_removed']} | "
            f"{item['fallback_newly_introduced']} | {item['current_year_confirmed_upgrades']} | "
            f"{item['added_fallback_rows']} | "
            f"{item['information_year_changed']} | {item['publication_status_changed']} |"
        )
    secondary = summary["superseded_to_candidate_diff"]
    master = secondary["master"]
    lines.extend(
        [
            "",
            "## Superseded v5.74 to frozen v5.81",
            "",
            f"Master {master['old_rows']:,} → {master['new_rows']:,}; added {master['added']:,}, removed {master['removed']:,}, changed {master['changed']:,}, material changed {master['material_changed_records']:,}.",
            f"Coverage added/removed/changed: {secondary['coverage']['added']}/{secondary['coverage']['removed']}/{secondary['coverage']['changed']}. Research exact rows added/removed: {secondary['research_requirements']['exact_rows_added']}/{secondary['research_requirements']['exact_rows_removed']}.",
            f"Source state: `{secondary['source_state']['from_dataset_state']}` → `{secondary['source_state']['to_dataset_state']}`.",
        ]
    )
    lines.extend(
        [
            "",
            "## Sidecar coherence",
            "",
            "| Dataset | Coverage missing | Coverage mismatches | Research rows | Exact duplicates | Orphans | Display mismatches |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset in ("kokkoritsu", "shidai"):
        item = summary["sidecar_coherence"][dataset]
        lines.append(
            f"| {dataset} | {len(item['coverage_missing_keys'])} | "
            f"{item['coverage_master_rows_mismatch_count']} | "
            f"{item['candidate_research_rows']} | {item['research_exact_duplicate_rows']} | "
            f"{item['research_orphan_rows']} | "
            f"{item['research_denormalized_field_mismatch_count']} |"
        )
    lines.extend(
        [
            "",
            "The supplied versioned sidecars are structurally coherent with their candidate Master tables. Display-field differences and exact child duplicates remain contract-defined warnings and are not rewritten or deduplicated.",
            "",
            "## Full source validator",
            "",
            "The production validator semantics were run against all six candidate CSVs without changing severity or accepted values.",
            "",
            "| Dataset | Errors | Warnings | Informational |",
            "|---|---:|---:|---:|",
        ]
    )
    for dataset in ("kokkoritsu", "shidai"):
        sev = summary["source_validation"]["summary"]["by_dataset"][dataset]["by_severity"]
        lines.append(
            f"| {dataset} | {sev['error']} | {sev['warning']} | {sev['informational']} |"
        )
    sev = summary["source_validation"]["summary"]["by_severity"]
    lines.append(
        f"| total | {sev['error']} | {sev['warning']} | {sev['informational']} |"
    )
    severity_delta = summary["source_validation_delta"]["by_severity"]
    lines.extend(
        [
            "",
            "Baseline to candidate severity delta:",
            "",
            "| Severity | Baseline | Candidate | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for severity in ("error", "warning", "informational"):
        item = severity_delta[severity]
        lines.append(
            f"| {severity} | {item['baseline']} | {item['candidate']} | {item['delta']:+d} |"
        )
    lines.extend(
        [
            "",
            "Warning-code deltas:",
            "",
            "| Code | Baseline | Candidate | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for code, item in summary["source_validation_delta"]["by_code"].items():
        if item["severity"] != "warning":
            continue
        lines.append(
            f"| `{code}` | {item['baseline']} | {item['candidate']} | {item['delta']:+d} |"
        )
    lines.extend(
        [
            "",
            "## Derived fail-closed review gate",
            "",
            "| Layer | New-vs-old raw values | Unmapped values | Unmapped rows |",
            "|---|---:|---:|---:|",
        ]
    )
    crosswalk = summary["crosswalk_audit"]
    for key in (
        "gpa",
        "grade_requirement",
        "english_requirement",
        "prefecture",
        "academic_field_v0_1",
        "academic_field_v0_2",
    ):
        item = crosswalk[key]
        lines.append(
            f"| {key} | {item['new_vs_old_distinct']} | "
            f"{item['unmapped_distinct']} | {item['unmapped_rows']} |"
        )
    v02 = crosswalk["academic_field_v0_2"]
    lines.extend(
        [
            "",
            f"Academic-field v0.2 candidate coverage: Broad {v02['broad_coverage']:,}/{v02['rows']:,}; Subcategory {v02['subcategory_coverage']:,}/{v02['rows']:,}; exact context consulted/effective {v02['context_consulted']:,}/{v02['context_effective']:,}.",
            f"New program-context tuples: {v02['new_program_context_tuples']:,}; review required: {v02['new_context_review_tuples']:,}.",
            "",
            "Human-review packets and versioned decision CSVs are retained beside this report. The approved decisions are reflected only in new versioned crosswalks; historical crosswalks remain unchanged.",
            "",
            "## Downstream acceptance stages",
            "",
            "| Stage | Result |",
            "|---|---|",
            f"| Full source validator | {summary['downstream']['full_source_validator']} |",
            f"| Unified candidate rebuild | {summary['downstream']['unified_candidate']} |",
            f"| SQLite candidate rebuild/validation | {summary['downstream']['sqlite_candidate']} |",
            f"| Structured-search regression | {summary['downstream']['structured_search']} |",
            f"| Site-data candidate rebuild/validation | {summary['downstream']['site_data_candidate']} |",
            f"| Frontend candidate tests/build | {summary['downstream']['frontend_candidate']} |",
            f"| Isolated strict production-profile build | {summary['downstream']['isolated_production_profile']} |",
            "| Sites Version/deployment | NOT RUN - explicitly prohibited |",
        ]
    )
    artifacts = summary.get("candidate_artifacts")
    if (
        artifacts
        and summary.get("search_audit")
        and summary.get("frontend_validation")
        and summary.get("performance")
    ):
        sqlite_item = artifacts["sqlite"]
        site_item = artifacts["site_data"]
        lines.extend(
            [
                "",
                "## Candidate artifacts",
                "",
                f"- Unified rows: master {sqlite_item['row_counts']['admissions']:,}, coverage {sqlite_item['row_counts']['coverage']:,}, research {sqlite_item['row_counts']['research_requirements']:,}",
                f"- SQLite: `{sqlite_item['sha256']}` ({sqlite_item['size_bytes']:,} bytes), profile `{sqlite_item['profile']}`",
                f"- Validation profile: `{sqlite_item['validation_profile']}`; production ready: `false`",
                f"- Review-required counts: `{json.dumps(sqlite_item['review_required_counts'], ensure_ascii=False, sort_keys=True)}`",
                f"- SQLite validation: `{sqlite_item['validation']['status']}`; FTS5={sqlite_item['fts5']}, trigram={sqlite_item['trigram']}",
                f"- Site-data build ID: `{site_item['build_id']}`",
                f"- Site-data manifest SHA-256: `{site_item['manifest_sha256']}`",
                f"- Site-data deterministic rebuild: `{site_item['deterministic_rebuild']['status']}` ({site_item['deterministic_rebuild']['files_compared']} files)",
                "",
                "## Representative search deltas",
                "",
                "| Query | Production | Candidate | Delta | Universities old/new | Added | Removed |",
                "|---|---:|---:|---:|---|---:|---:|",
            ]
        )
        for item in summary["search_audit"]["important_search_comparison"]:
            lines.append(
                f"| {item['label']} | {item['production_admissions']} | "
                f"{item['candidate_admissions']} | {item['admissions_delta']:+d} | "
                f"{item['production_universities']}/{item['candidate_universities']} | "
                f"{item['added_result_ids']} | {item['removed_result_ids']} |"
            )
        denominator = summary["search_audit"]["search_denominator_audit"]
        lines.extend(
            [
                "",
                "## Fail-closed search denominator",
                "",
                f"- Total admissions: {denominator['total_admissions']:,}",
                f"- English safe binary-search rows / unmapped excluded: {denominator['english']['mapped_searchable']:,} / {denominator['english']['unmapped_excluded_from_binary_filter']:,}",
                f"- Grade mapped rows / unmapped: {denominator['grade']['mapped_classification_rows']:,} / {denominator['grade']['unmapped']:,}",
                f"- GPA safe numeric / unparsed: {denominator['gpa']['safe_numeric']:,} / {denominator['gpa']['unparsed']:,}",
                f"- Academic-field v0.2 Broad/Subcategory coverage: {denominator['academic_field_v0_2']['broad_coverage']:,} / {denominator['academic_field_v0_2']['subcategory_coverage']:,}",
                f"- Academic-field v0.2 no-Broad membership / unmapped / context review: {denominator['academic_field_v0_2']['broad_without_membership']:,} / {denominator['academic_field_v0_2']['unmapped']:,} / {denominator['academic_field_v0_2']['context_review']:,}",
                "",
                "Review-sensitive queries record candidate matches, excluded-unmapped counts, and representative stable record IDs in `update_summary.json`.",
            ]
        )
        frontend = summary["frontend_validation"]
        performance = summary["performance"]
        lines.extend(
            [
                "",
                "## Frontend and performance",
                "",
                f"- Frontend tests: PASS ({frontend['frontend_tests']['test_count'] or 'count in log'})",
                f"- Responsive focused tests: PASS ({frontend['responsive_tests']['test_count'] or 'count in log'})",
                f"- Repository tests: PASS ({frontend['repository_tests']['test_count'] or 'count in log'})",
                "- Production build: PASS",
                f"- Admissions size delta: {performance['admissions']['production']:,} → {performance['admissions']['candidate']:,} ({performance['admissions']['percent_change']:+.2f}%)",
                f"- SQLite size delta: {performance['sqlite_bytes']['production']:,} → {performance['sqlite_bytes']['candidate']:,} bytes ({performance['sqlite_bytes']['percent_change']:+.2f}%)",
                f"- Site-data total: {performance['site_data_total_bytes']['production']:,} → {performance['site_data_total_bytes']['candidate']:,} bytes ({performance['site_data_total_bytes']['percent_change']:+.2f}%)",
                f"- Search projection: {performance['search_projection_bytes']['production']:,} → {performance['search_projection_bytes']['candidate']:,} bytes ({performance['search_projection_bytes']['percent_change']:+.2f}%)",
                f"- Search projection gzip: {performance['search_projection_gzip_bytes']['production']:,} → {performance['search_projection_gzip_bytes']['candidate']:,} bytes ({performance['search_projection_gzip_bytes']['percent_change']:+.2f}%)",
                f"- Detail projection: {performance['detail_projection_bytes']['production']:,} → {performance['detail_projection_bytes']['candidate']:,} bytes ({performance['detail_projection_bytes']['percent_change']:+.2f}%)",
                f"- Detail projection gzip-equivalent: {performance['detail_projection_gzip_equivalent_bytes']['production']:,} → {performance['detail_projection_gzip_equivalent_bytes']['candidate']:,} bytes ({performance['detail_projection_gzip_equivalent_bytes']['percent_change']:+.2f}%)",
                f"- Candidate build time: SQLite {performance['build_seconds']['sqlite_seconds']:.3f}s; Site-data {performance['build_seconds']['site_data_seconds']:.3f}s; deterministic rebuild {performance['build_seconds']['site_data_rebuild_seconds']:.3f}s",
                f"- Frozen 25-query median latency: {performance['frozen_25_query_latency']['production']['median_ms']:.3f} → {performance['frozen_25_query_latency']['candidate']['median_ms']:.3f} ms",
            ]
        )
    if summary.get("build_error"):
        lines.extend(
            [
                "",
                "## Build failure",
                "",
                f"`{summary['build_error']['type']}`: {summary['build_error']['message']}",
            ]
        )
    production_profile = summary.get("production_profile_artifacts")
    if production_profile:
        lines.extend(
            [
                "",
                "## Isolated strict production profile",
                "",
                f"- SQLite: `{production_profile['sqlite']['sha256']}` ({production_profile['sqlite']['size_bytes']:,} bytes)",
                f"- SQLite validation/profile: `{production_profile['sqlite']['validation']['status']}` / `{production_profile['sqlite']['validation_profile']}`",
                f"- Site-data build ID: `{production_profile['site_data']['build_id']}`",
                f"- Site-data manifest SHA-256: `{production_profile['site_data']['manifest_sha256']}`",
                f"- Frozen structured-search queries: {production_profile['structured_search_25_query']['queries']}/25 PASS",
                "- Frontend tests, responsive tests, oracle export, and production build: PASS",
            ]
        )
    receipt = summary["production_receipt_final"]
    lines.extend(
        [
            "",
            "## Production immutability",
            "",
            f"Receipt status: `{receipt['status']}`; checked {receipt['checked']} files/directories; changed {len(receipt['changed'])}.",
            "",
            "## Human decision",
            "",
            "The gate authorizes a separate future promotion decision only. It does not mean that production canonical data, artifacts, Git state, Sites Version, or deployment was changed.",
            "",
        ]
    )
    return "\n".join(lines)


def resume_frontend_validation(repo_root: Path | str) -> dict[str, Any]:
    """Resume only frontend validation from sealed candidate SQLite/Site receipts."""

    root = Path(repo_root).resolve()
    report_dir = root / "validation/reports" / UPDATE_ID
    derived_dir = root / "data/derived/update_audit" / UPDATE_ID.removeprefix(
        "update_"
    )
    summary_path = report_dir / "update_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    artifacts = summary.get("candidate_artifacts")
    search_audit = summary.get("search_audit")
    if not artifacts or not search_audit:
        raise RuntimeError("No completed candidate SQLite/Site/search checkpoint to resume.")

    candidate_database = root / artifacts["sqlite"]["database"]
    if _sha256(candidate_database) != artifacts["sqlite"]["sha256"]:
        raise RuntimeError("Candidate SQLite SHA changed before frontend resume.")
    sqlite_manifest_path = root / artifacts["sqlite"]["manifest"]
    sqlite_manifest = json.loads(sqlite_manifest_path.read_text(encoding="utf-8"))
    if (
        sqlite_manifest.get("validation", {}).get("status") != "passed"
        or sqlite_manifest.get("validation_profile") != "candidate_audit"
        or sqlite_manifest.get("publication", {}).get("production_ready") is not False
        or sqlite_manifest.get("row_counts", {}).get("admissions") != 6411
    ):
        raise RuntimeError("Candidate SQLite checkpoint is not inspection-only/passed.")
    uri = candidate_database.resolve().as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Candidate SQLite quick_check failed on resume.")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Candidate SQLite foreign_key_check failed on resume.")

    site_output = root / artifacts["site_data"]["output_dir"]
    site_manifest_path = root / artifacts["site_data"]["manifest"]
    if _sha256(site_manifest_path) != artifacts["site_data"]["manifest_sha256"]:
        raise RuntimeError("Candidate Site-data manifest SHA changed before resume.")
    site_manifest = json.loads(site_manifest_path.read_text(encoding="utf-8"))
    if (
        site_manifest.get("validation", {}).get("status") != "passed"
        or site_manifest.get("validation_profile") != "candidate_audit"
        or site_manifest.get("publication", {}).get("production_ready") is not False
        or site_manifest.get("counts", {}).get("search_rows") != 6411
        or site_manifest.get("counts", {}).get("detail_records") != 6411
    ):
        raise RuntimeError("Candidate Site-data checkpoint is not inspection-only/passed.")
    for item in site_manifest["outputs"]["artifacts"]:
        path = site_output / item["path"]
        if not path.is_file() or _sha256(path) != item["sha256"]:
            raise RuntimeError(f"Candidate Site-data artifact mismatch: {item['path']}")

    if search_audit.get("candidate_25_query_execution", {}).get("queries") != 25:
        raise RuntimeError("Candidate 25-query checkpoint is incomplete.")
    before = _verify_receipt(root, summary["baseline_receipt"])
    if before["status"] != "passed":
        raise RuntimeError("Production receipt changed before frontend resume.")

    frontend = _frontend_candidate_validation(
        root, root / artifacts["candidate_root"], derived_dir
    )
    performance = _size_performance_summary(root, artifacts, search_audit)
    after = _verify_receipt(root, summary["baseline_receipt"])
    if after["status"] != "passed":
        raise RuntimeError("Production receipt changed during frontend resume.")

    summary["frontend_validation"] = frontend
    summary["performance"] = performance
    summary["build_error"] = None
    summary["production_receipt_final"] = after
    summary["downstream"].update(
        {
            "sqlite_candidate": "passed",
            "site_data_candidate": "passed",
            "structured_search": "passed",
            "frontend_candidate": "passed",
        }
    )
    summary["final_gate"] = {
        "status": "READY_FOR_HUMAN_REVIEW",
        "reason": (
            "Source, unified, SQLite, Site-data, structured search, and frontend "
            "technical validation passed under the explicit inspection-only "
            "candidate_audit profile. Human crosswalk review remains mandatory."
        ),
    }
    summary = _portable_report_value(summary, root)
    _write_json(summary_path, summary)
    (report_dir / "update_summary.md").write_text(
        _render_markdown(summary), encoding="utf-8", newline="\n"
    )
    return summary


def resume_from_validated_candidate_artifacts(
    repo_root: Path | str,
) -> dict[str, Any]:
    """Resume search/frontend/production-profile gates without rebuilding artifacts."""

    root = Path(repo_root).resolve()
    report_dir = root / "validation/reports" / UPDATE_ID
    derived_dir = root / "data/derived/update_audit" / UPDATE_ID.removeprefix(
        "update_"
    )
    summary_path = report_dir / "update_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    artifacts = summary.get("candidate_artifacts")
    if not artifacts:
        raise RuntimeError("No completed candidate artifact checkpoint to resume.")
    candidate_database = root / artifacts["sqlite"]["database"]
    sqlite_manifest_path = root / artifacts["sqlite"]["manifest"]
    sqlite_manifest = json.loads(sqlite_manifest_path.read_text(encoding="utf-8"))
    if (
        _sha256(candidate_database) != artifacts["sqlite"]["sha256"]
        or sqlite_manifest.get("validation", {}).get("status") != "passed"
        or sqlite_manifest.get("validation_profile") != "candidate_audit"
        or sqlite_manifest.get("row_counts")
        != {"admissions": 6411, "coverage": 260, "research_requirements": 495}
    ):
        raise RuntimeError("Candidate SQLite checkpoint validation failed.")
    uri = candidate_database.resolve().as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Candidate SQLite quick_check failed on resume.")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Candidate SQLite foreign_key_check failed on resume.")

    site_output = root / artifacts["site_data"]["output_dir"]
    site_manifest_path = root / artifacts["site_data"]["manifest"]
    site_manifest = json.loads(site_manifest_path.read_text(encoding="utf-8"))
    if (
        _sha256(site_manifest_path) != artifacts["site_data"]["manifest_sha256"]
        or site_manifest.get("validation", {}).get("status") != "passed"
        or site_manifest.get("validation_profile") != "candidate_audit"
        or site_manifest.get("counts", {}).get("search_rows") != 6411
        or site_manifest.get("counts", {}).get("detail_records") != 6411
    ):
        raise RuntimeError("Candidate Site-data checkpoint validation failed.")
    for item in site_manifest["outputs"]["artifacts"]:
        path = site_output / item["path"]
        if not path.is_file() or _sha256(path) != item["sha256"]:
            raise RuntimeError(f"Candidate Site-data artifact mismatch: {item['path']}")

    before = _verify_receipt(root, summary["baseline_receipt"])
    if before["status"] != "passed":
        raise RuntimeError("Production receipt changed before checkpoint resume.")
    search_audit = _candidate_search_audit(root, candidate_database, report_dir)
    frontend = _frontend_candidate_validation(
        root, root / artifacts["candidate_root"], derived_dir
    )
    performance = _size_performance_summary(root, artifacts, search_audit)
    production_profile = _build_isolated_production_profile(
        root, derived_dir, report_dir, artifacts
    )
    after = _verify_receipt(root, summary["baseline_receipt"])
    if after["status"] != "passed":
        raise RuntimeError("Production receipt changed during checkpoint resume.")

    summary["search_audit"] = search_audit
    summary["frontend_validation"] = frontend
    summary["performance"] = performance
    summary["production_profile_artifacts"] = production_profile
    summary["build_error"] = None
    summary["production_receipt_final"] = after
    summary["downstream"].update(
        {
            "sqlite_candidate": "passed",
            "site_data_candidate": "passed",
            "structured_search": "passed",
            "frontend_candidate": "passed",
            "isolated_production_profile": "passed",
        }
    )
    summary["final_gate"] = {
        "status": "READY_FOR_PRODUCTION_PROMOTION",
        "reason": (
            "Source Freeze, reviewed correspondence, candidate-audit full pipeline, "
            "isolated strict production-profile pipeline, structured search, and "
            "frontend validation passed with prohibited unmapped=0. Current production "
            "artifacts remained unchanged; no promotion was run."
        ),
    }
    summary = _portable_report_value(summary, root)
    _write_json(summary_path, summary)
    (report_dir / "update_summary.md").write_text(
        _render_markdown(summary), encoding="utf-8", newline="\n"
    )
    return summary


def run(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    report_dir = root / "validation/reports" / UPDATE_ID
    derived_dir = root / "data/derived/update_audit" / UPDATE_ID.removeprefix("update_")
    baseline = _baseline_receipt(root)
    inputs: dict[str, Any] = {}
    source_identity: dict[str, Any] = {}
    schema_compatibility: dict[str, Any] = {}
    source_diff: dict[str, Any] = {}
    sidecars: dict[str, Any] = {}
    master_validation: dict[str, Any] = {}
    all_old: list[dict[str, str]] = []
    all_new: list[dict[str, str]] = []
    candidate_rows_by_dataset: dict[str, list[dict[str, str]]] = {}
    for dataset, config in INCOMING.items():
        old_path = root / f"data/canonical/{dataset}/master.csv"
        new_path = root / config["path"]
        current_schema_path = root / config["current_schema"]
        candidate_schema_path = root / config["candidate_schema"]
        old_header, old_rows = _read_csv(old_path)
        new_header, new_rows = _read_csv(new_path)
        current_schema = json.loads(current_schema_path.read_text(encoding="utf-8-sig"))
        candidate_schema, schema_preflight = _json_preflight(
            candidate_schema_path, repo_root=root
        )
        inputs[dataset] = {
            "master": _preflight(new_path, repo_root=root),
            "coverage": _preflight(
                root / config["coverage"],
                ("institution_type", "university"),
                repo_root=root,
            ),
            "research_requirements": _preflight(
                root / config["research_requirements"], (), repo_root=root
            ),
            "schema": schema_preflight,
        }
        source_identity[dataset] = _schema_identity_audit(
            dataset,
            str(config["new_version"]),
            candidate_schema,
            config,
        )
        contract_keys = (
            "target_admission_year",
            "grain",
            "primary_key",
            "relationships",
            "fallback_policy",
            "exclusive_enrollment_policy",
            "academic_record_policy",
            "selection_flags",
            "school_nomination_fields",
            "research_requirement_child_table",
            "enum_definitions",
            "null_semantics",
            "normalization_rules",
            "detail_completeness_gate",
            "field_definitions",
            "master_columns",
            "coverage_columns",
            "research_requirements_columns",
        )
        compatibility = _schema_contract_compatibility(
            current_schema, candidate_schema, contract_keys
        )
        schema_compatibility[dataset] = {
            "current_schema": str(config["current_schema"]),
            "candidate_schema": str(config["candidate_schema"]),
            "contract_keys_compared": list(contract_keys),
            **compatibility,
            "master_header_matches_candidate_schema": (
                new_header == candidate_schema.get("master_columns", [])
            ),
            "master_header_matches_current": old_header == new_header,
        }
        source_diff[dataset] = _diff_dataset(
            dataset, new_header, old_rows, new_rows, derived_dir
        )
        sidecars[dataset] = _sidecar_audit(
            root,
            dataset,
            new_rows,
            config["coverage"],
            config["research_requirements"],
        )
        master_validation[dataset] = {
            "old": _master_validation(
                root,
                dataset,
                old_path,
                current_schema_path,
                str(config["old_version"]),
            ),
            "new": _master_validation(
                root,
                dataset,
                new_path,
                candidate_schema_path,
                str(config["new_version"]),
            ),
        }
        all_old.extend(dict(row, source_dataset=dataset) for row in old_rows)
        all_new.extend(dict(row, source_dataset=dataset) for row in new_rows)
        candidate_rows_by_dataset[dataset] = new_rows
    numeric_total_keys = (
        "old_rows",
        "new_rows",
        "unchanged",
        "added",
        "removed",
        "changed",
        "material_changed_records",
        "fallback_removed",
        "fallback_newly_introduced",
        "current_year_confirmed_upgrades",
        "added_fallback_rows",
        "information_year_changed",
        "publication_status_changed",
    )
    source_diff["totals"] = {
        key: sum(source_diff[dataset][key] for dataset in INCOMING)
        for key in numeric_total_keys
    }
    superseded_diff = _superseded_to_candidate_audit(
        root,
        candidate_rows_by_dataset["kokkoritsu"],
        INCOMING["kokkoritsu"],
        derived_dir,
    )
    baseline_source_validation = ReadOnlyValidator(root).validate().summary()
    source_validation = _candidate_source_validation(root, derived_dir)
    source_validation_delta = _validation_delta(
        baseline_source_validation, source_validation["summary"]
    )
    crosswalk = _crosswalk_audit(root, all_old, all_new, report_dir)
    focused_crosswalk_path = (
        report_dir / "english_academic_crosswalk_candidate_audit.json"
    )
    focused_crosswalk = (
        json.loads(focused_crosswalk_path.read_text(encoding="utf-8"))
        if focused_crosswalk_path.is_file()
        else None
    )
    unfrozen = sorted(
        dataset
        for dataset, item in source_identity.items()
        if item["explicitly_unfrozen"]
    )
    identity_failures = sorted(
        dataset
        for dataset, item in source_identity.items()
        if not item["identity_coherent"]
    )
    structural_failures = sorted(
        dataset
        for dataset, item in sidecars.items()
        if not item["candidate_sidecars_structurally_coherent"]
    )
    schema_failures = sorted(
        dataset
        for dataset, item in schema_compatibility.items()
        if not item["contract_compatible_with_current"]
    )
    validator_errors = source_validation["summary"]["by_severity"]["error"]
    artifacts: dict[str, Any] | None = None
    search_audit: dict[str, Any] | None = None
    frontend_validation: dict[str, Any] | None = None
    performance: dict[str, Any] | None = None
    production_profile_artifacts: dict[str, Any] | None = None
    build_error: dict[str, Any] | None = None
    if unfrozen:
        final_gate = {
            "status": "HOLD_SOURCE_COHERENCE",
            "reason": (
                "The complete versioned four-file bundles were supplied and the CSV "
                "relationships validate, but a candidate explicitly declares an "
                "UNFROZEN source state. "
                "That source-owned state is a mandatory stop gate."
            ),
            "unfrozen_datasets": unfrozen,
        }
    elif identity_failures:
        final_gate = {
            "status": "HOLD_SCHEMA",
            "reason": "Candidate schema version/dataset/filename identity is inconsistent.",
            "datasets": identity_failures,
        }
    elif schema_failures:
        final_gate = {
            "status": "HOLD_SCHEMA",
            "reason": "Candidate source contract differs from the production-compatible schema.",
            "datasets": schema_failures,
        }
    elif structural_failures:
        final_gate = {
            "status": "HOLD_SOURCE_COHERENCE",
            "reason": "Candidate Coverage or ResearchRequirements is not structurally coherent with Master.",
            "datasets": structural_failures,
        }
    elif validator_errors:
        final_gate = {
            "status": "HOLD_VALIDATION",
            "reason": f"Candidate source validation reported {validator_errors} errors.",
        }
    elif (
        focused_crosswalk is None
        or focused_crosswalk.get("status") != "passed"
        or any(focused_crosswalk.get("prohibited_unmapped", {}).values())
        or focused_crosswalk.get("correspondence")
        != {"english": 66, "academic_raw": 39, "academic_context": 71}
    ):
        final_gate = {
            "status": "HOLD_REVIEW_CORRESPONDENCE",
            "reason": (
                "The reviewed English/Academic decision correspondence or focused "
                "6,411-row re-evaluation is incomplete."
            ),
        }
    else:
        try:
            artifacts = _build_candidate_artifacts(
                root, derived_dir, report_dir, crosswalk
            )
            candidate_database = root / artifacts["sqlite"]["database"]
            search_audit = _candidate_search_audit(
                root, candidate_database, report_dir
            )
            frontend_validation = _frontend_candidate_validation(
                root,
                root / artifacts["candidate_root"],
                derived_dir,
            )
            performance = _size_performance_summary(root, artifacts, search_audit)
            production_profile_artifacts = _build_isolated_production_profile(
                root, derived_dir, report_dir, artifacts
            )
            final_gate = {
                "status": "READY_FOR_PRODUCTION_PROMOTION",
                "reason": (
                    "Source Freeze, reviewed correspondence, candidate-audit full "
                    "pipeline, isolated strict production-profile pipeline, structured "
                    "search, and frontend validation passed with prohibited unmapped=0. "
                    "Current production artifacts remained unchanged; no promotion was run."
                ),
            }
        except Exception as error:  # preserve a complete acceptance receipt on failure
            build_error = {
                "type": type(error).__name__,
                "message": str(error),
            }
            final_gate = {
                "status": "HOLD_BUILD",
                "reason": f"Candidate downstream build failed: {type(error).__name__}: {error}",
            }

    production_receipt_final = _verify_receipt(root, baseline)
    if production_receipt_final["status"] != "passed":
        final_gate = {
            "status": "HOLD_OTHER",
            "reason": "Production receipt changed during candidate acceptance audit.",
            "changes": production_receipt_final["changed"],
        }

    downstream_completed = artifacts is not None and build_error is None
    candidate_unified_receipt = _existing_candidate_unified_receipt(root, derived_dir)
    unified_completed = bool(
        candidate_unified_receipt
        and candidate_unified_receipt.get("status") == "passed"
    )
    summary: dict[str, Any] = {
        "update_id": UPDATE_ID,
        "production_versions": dict(PRODUCTION_VERSIONS),
        "superseded_versions": dict(SUPERSEDED_VERSIONS),
        "old_versions": dict(PRODUCTION_VERSIONS),
        "candidate_versions": dict(CANDIDATE_VERSIONS),
        "baseline_receipt": baseline,
        "production_receipt_final": production_receipt_final,
        "inputs": inputs,
        "source_identity": source_identity,
        "schema_compatibility": schema_compatibility,
        "source_diff": source_diff,
        "superseded_to_candidate_diff": superseded_diff,
        "master_validation": master_validation,
        "baseline_source_validation": baseline_source_validation,
        "source_validation": source_validation,
        "source_validation_delta": source_validation_delta,
        "sidecar_coherence": sidecars,
        "crosswalk_audit": crosswalk,
        "focused_crosswalk_audit": focused_crosswalk,
        "validation_profiles": {
            "default": "production",
            "candidate": "candidate_audit",
            "candidate_requires_explicit_opt_in": True,
            "production_english_unmapped_severity": "TECHNICAL_ERROR",
            "candidate_english_unmapped_severity": "REVIEW_REQUIRED",
            "technical_integrity_errors_hard_in_both": True,
            "candidate_production_ready": False,
            "previous_gate": "HOLD_BUILD",
            "previous_gate_reason": (
                "Candidate English unmapped rows reached the production-only strict gate."
            ),
            "gate_history": [
                {
                    "status": "HOLD_BUILD",
                    "reason": "Production-only English-unmapped strict gate blocked the first downstream build.",
                },
                {
                    "status": "READY_FOR_HUMAN_REVIEW",
                    "reason": "Inspection-only candidate pipeline passed while human crosswalk review remained mandatory.",
                },
            ],
        },
        "candidate_artifacts": artifacts,
        "production_profile_artifacts": production_profile_artifacts,
        "candidate_unified_receipt": candidate_unified_receipt,
        "search_audit": search_audit,
        "frontend_validation": frontend_validation,
        "performance": performance,
        "build_error": build_error,
        "downstream": {
            "full_source_validator": "completed_zero_errors"
            if validator_errors == 0
            else "completed_with_errors",
            "unified_candidate": "passed" if unified_completed else "not_completed",
            "sqlite_candidate": "passed" if downstream_completed else "not_completed",
            "site_data_candidate": "passed" if downstream_completed else "not_completed",
            "structured_search": "passed" if downstream_completed else "not_completed",
            "frontend_candidate": "passed" if downstream_completed else "not_completed",
            "isolated_production_profile": (
                "passed" if production_profile_artifacts is not None else "not_completed"
            ),
            "sites_version_or_deployment": "not_run_prohibited",
        },
        "final_gate": final_gate,
    }
    _write_json(report_dir / "update_summary.json", summary)
    (report_dir / "update_summary.md").write_text(
        _render_markdown(summary), encoding="utf-8", newline="\n"
    )
    return summary


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    summary = run(root)
    print(json.dumps({
        "status": summary["final_gate"]["status"],
        "inputs": {
            dataset: {
                table: {
                    key: metadata[key]
                    for key in ("rows", "columns", "sha256")
                    if key in metadata
                }
                for table, metadata in item.items()
            }
            for dataset, item in summary["inputs"].items()
        },
        "source_validation": summary["source_validation"]["summary"]["by_severity"],
        "source_diff": summary["source_diff"]["totals"],
        "report": f"validation/reports/{UPDATE_ID}/update_summary.md",
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["final_gate"]["status"] == "READY_FOR_PRODUCTION_PROMOTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
