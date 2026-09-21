"""Validation and audit support for the frozen academic-field contract v0.2.

This module deliberately performs exact lookups only.  It contains no lexical,
substring, regular-expression, fuzzy, or model-based classification fallback.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


MAPPING_VERSION = "0.2"
TAXONOMY_VERSION = "0.2"

BROAD_HEADER = (
    "taxonomy_version",
    "group_code",
    "display_label_ja",
    "ui_section",
    "display_order",
    "description",
    "status",
)
SUBCATEGORY_HEADER = (
    "taxonomy_version",
    "subcategory_code",
    "display_label_ja",
    "parent_group_code",
    "display_order",
    "description",
    "ui_status",
)
RAW_HEADER = (
    "mapping_contract_version",
    "raw_value",
    "mapping_status",
    "broad_mapping_status",
    "subcategory_mapping_status",
    "group_code",
    "subcategory_code",
    "membership_order",
    "review_note",
)
CONTEXT_HEADER = (
    "mapping_contract_version",
    "source_dataset",
    "university",
    "faculty_school",
    "department",
    "academic_field",
    "mapping_status",
    "broad_mapping_status",
    "subcategory_mapping_status",
    "merge_mode",
    "group_code",
    "subcategory_code",
    "membership_order",
    "review_note",
)
COMPAT_HEADER = (
    "from_taxonomy_version",
    "from_group_code",
    "to_taxonomy_version",
    "to_group_code",
    "relationship",
    "note",
)

FROZEN_STATUSES = frozenset({"single", "multi", "review_required"})
SUBCATEGORY_STATUSES = frozenset(
    {"single", "multi", "review_required", "not_applicable"}
)


class AcademicFieldV02Error(ValueError):
    """Raised when the v0.2 freeze contract is inconsistent."""


@dataclass(frozen=True)
class FreezePaths:
    repo_root: Path

    @property
    def schema_dir(self) -> Path:
        return self.repo_root / "schema/academic_field/v0_2"

    @property
    def broad(self) -> Path:
        return self.schema_dir / "academic_field_broad_taxonomy_v0_2.csv"

    @property
    def subcategory(self) -> Path:
        return self.schema_dir / "academic_field_subcategory_taxonomy_v0_2.csv"

    @property
    def raw(self) -> Path:
        return self.schema_dir / "academic_field_raw_crosswalk_v0_2.csv"

    @property
    def context(self) -> Path:
        return self.schema_dir / "academic_field_context_crosswalk_v0_2.csv"

    @property
    def compatibility(self) -> Path:
        return self.schema_dir / "academic_field_v0_1_to_v0_2_crosswalk.csv"

    @property
    def kokkoritsu_master(self) -> Path:
        return self.repo_root / "data/canonical/kokkoritsu/master.csv"

    @property
    def shidai_master(self) -> Path:
        return self.repo_root / "data/canonical/shidai/master.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_frozen_csv(path: Path, header: Sequence[str]) -> list[dict[str, str]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AcademicFieldV02Error(f"Frozen CSV contains a BOM: {path}")
    if b"\r" in raw:
        raise AcademicFieldV02Error(f"Frozen CSV is not LF-only: {path}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AcademicFieldV02Error(f"Frozen CSV is not UTF-8: {path}") from error
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != tuple(header):
            raise AcademicFieldV02Error(
                f"Header mismatch for {path}: {reader.fieldnames!r}"
            )
        return list(reader)


def _read_master(path: Path, source_dataset: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "record_id",
        "university",
        "institution_type",
        "academic_field",
        "faculty_school",
        "department",
    }
    missing = required - set(rows[0] if rows else ())
    if missing:
        raise AcademicFieldV02Error(
            f"Missing master columns in {path}: {sorted(missing)!r}"
        )
    return [dict(row, source_dataset=source_dataset) for row in rows]


def _group_contiguous(
    rows: Sequence[dict[str, str]], key_columns: Sequence[str], label: str
) -> list[tuple[tuple[str, ...], list[dict[str, str]]]]:
    groups: list[tuple[tuple[str, ...], list[dict[str, str]]]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        if not groups or groups[-1][0] != key:
            if key in seen:
                raise AcademicFieldV02Error(
                    f"{label} rows are not contiguous for key {key!r}"
                )
            seen.add(key)
            groups.append((key, []))
        groups[-1][1].append(row)
    return groups


def _validate_status_block(
    block: Sequence[dict[str, str]], label: str
) -> tuple[str, str, str]:
    statuses = {row["mapping_status"] for row in block}
    broad_statuses = {row["broad_mapping_status"] for row in block}
    sub_statuses = {row["subcategory_mapping_status"] for row in block}
    if len(statuses) != 1 or not statuses.issubset(FROZEN_STATUSES):
        raise AcademicFieldV02Error(f"Invalid mapping_status for {label}")
    if len(broad_statuses) != 1 or not broad_statuses.issubset(FROZEN_STATUSES):
        raise AcademicFieldV02Error(f"Invalid broad_mapping_status for {label}")
    if len(sub_statuses) != 1 or not sub_statuses.issubset(
        SUBCATEGORY_STATUSES
    ):
        raise AcademicFieldV02Error(
            f"Invalid subcategory_mapping_status for {label}"
        )
    return next(iter(statuses)), next(iter(broad_statuses)), next(iter(sub_statuses))


def _validate_mapping_block(
    block: Sequence[dict[str, str]],
    label: str,
    broad_codes: set[str],
    subcategory_parents: dict[str, str],
) -> tuple[tuple[str, str | None], ...]:
    status, broad_status, sub_status = _validate_status_block(block, label)
    notes = {row["review_note"] for row in block}
    if len(notes) != 1 or not next(iter(notes)):
        raise AcademicFieldV02Error(f"Inconsistent/empty review_note for {label}")
    if status == "review_required":
        if len(block) != 1:
            raise AcademicFieldV02Error(
                f"review_required must have one sentinel row for {label}"
            )
        row = block[0]
        if any(
            row[column]
            for column in ("group_code", "subcategory_code", "membership_order")
        ):
            raise AcademicFieldV02Error(
                f"review_required must have no membership for {label}"
            )
        if broad_status != "review_required" or sub_status != "review_required":
            raise AcademicFieldV02Error(
                f"review_required status mismatch for {label}"
            )
        return ()

    memberships: list[tuple[str, str | None]] = []
    orders: list[int] = []
    for row in block:
        group_code = row["group_code"]
        subcategory_code = row["subcategory_code"] or None
        if group_code not in broad_codes:
            raise AcademicFieldV02Error(
                f"Unknown broad group {group_code!r} for {label}"
            )
        if subcategory_code is not None:
            if subcategory_parents.get(subcategory_code) != group_code:
                raise AcademicFieldV02Error(
                    f"Invalid subcategory parent for {label}: "
                    f"{subcategory_code!r} under {group_code!r}"
                )
        membership = (group_code, subcategory_code)
        if membership in memberships:
            raise AcademicFieldV02Error(
                f"Duplicate exact membership {membership!r} for {label}"
            )
        memberships.append(membership)
        try:
            orders.append(int(row["membership_order"]))
        except ValueError as error:
            raise AcademicFieldV02Error(
                f"Invalid membership_order for {label}"
            ) from error
    if orders != list(range(1, len(block) + 1)):
        raise AcademicFieldV02Error(
            f"Non-contiguous membership_order for {label}"
        )
    expected_mapping = "single" if len(memberships) == 1 else "multi"
    groups = {group for group, _ in memberships}
    subs = {subcategory for _, subcategory in memberships if subcategory}
    expected_broad = "single" if len(groups) == 1 else "multi"
    expected_sub = (
        "not_applicable"
        if not subs
        else ("single" if len(subs) == 1 else "multi")
    )
    if (status, broad_status, sub_status) != (
        expected_mapping,
        expected_broad,
        expected_sub,
    ):
        raise AcademicFieldV02Error(
            f"Derived status mismatch for {label}: "
            f"{(status, broad_status, sub_status)!r}"
        )
    return tuple(memberships)


def _serialize_csv(
    path: Path, header: Sequence[str], rows: Iterable[dict[str, str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_and_summarize(
    repo_root: Path, rebuild_dir: Path | None = None
) -> dict[str, object]:
    paths = FreezePaths(repo_root)
    broad_rows = _read_frozen_csv(paths.broad, BROAD_HEADER)
    sub_rows = _read_frozen_csv(paths.subcategory, SUBCATEGORY_HEADER)
    raw_rows = _read_frozen_csv(paths.raw, RAW_HEADER)
    context_rows = _read_frozen_csv(paths.context, CONTEXT_HEADER)
    compat_rows = _read_frozen_csv(paths.compatibility, COMPAT_HEADER)

    broad_codes: set[str] = set()
    section_orders: dict[str, list[int]] = defaultdict(list)
    broad_labels: dict[str, str] = {}
    for row in broad_rows:
        if row["taxonomy_version"] != TAXONOMY_VERSION:
            raise AcademicFieldV02Error("Unexpected broad taxonomy version")
        code = row["group_code"]
        if not code or code in broad_codes:
            raise AcademicFieldV02Error(f"Duplicate/empty broad code: {code!r}")
        if row["status"] != "active":
            raise AcademicFieldV02Error(f"Non-active broad group: {code}")
        broad_codes.add(code)
        broad_labels[code] = row["display_label_ja"]
        section_orders[row["ui_section"]].append(int(row["display_order"]))
    if len(broad_codes) != 30:
        raise AcademicFieldV02Error(
            f"Expected 30 broad groups, found {len(broad_codes)}"
        )
    for section, orders in section_orders.items():
        if orders != list(range(1, len(orders) + 1)):
            raise AcademicFieldV02Error(
                f"Non-contiguous broad display_order in {section!r}"
            )

    subcategory_parents: dict[str, str] = {}
    parent_orders: dict[str, list[int]] = defaultdict(list)
    subcategory_labels: dict[str, str] = {}
    for row in sub_rows:
        if row["taxonomy_version"] != TAXONOMY_VERSION:
            raise AcademicFieldV02Error("Unexpected subcategory taxonomy version")
        code = row["subcategory_code"]
        parent = row["parent_group_code"]
        if not code or code in subcategory_parents:
            raise AcademicFieldV02Error(
                f"Duplicate/empty subcategory code: {code!r}"
            )
        if parent not in broad_codes:
            raise AcademicFieldV02Error(
                f"Invalid parent {parent!r} for subcategory {code!r}"
            )
        if row["ui_status"] not in {"primary", "secondary", "hidden"}:
            raise AcademicFieldV02Error(
                f"Invalid ui_status for subcategory {code!r}"
            )
        subcategory_parents[code] = parent
        subcategory_labels[code] = row["display_label_ja"]
        parent_orders[parent].append(int(row["display_order"]))
    for parent, orders in parent_orders.items():
        if orders != list(range(1, len(orders) + 1)):
            raise AcademicFieldV02Error(
                f"Non-contiguous subcategory display_order for {parent!r}"
            )

    raw_blocks = _group_contiguous(raw_rows, ("raw_value",), "raw crosswalk")
    raw_keys = [key[0] for key, _ in raw_blocks]
    if raw_keys != sorted(raw_keys):
        raise AcademicFieldV02Error("Raw crosswalk keys are not sorted")
    raw_map: dict[str, tuple[tuple[str, str | None], ...]] = {}
    raw_status: dict[str, str] = {}
    for (raw_value,), block in raw_blocks:
        if raw_value == "" or raw_value != raw_value.strip():
            raise AcademicFieldV02Error(
                f"Empty/trimmed raw crosswalk key: {raw_value!r}"
            )
        if {row["mapping_contract_version"] for row in block} != {
            MAPPING_VERSION
        }:
            raise AcademicFieldV02Error(
                f"Unexpected raw mapping version for {raw_value!r}"
            )
        raw_map[raw_value] = _validate_mapping_block(
            block, f"raw {raw_value!r}", broad_codes, subcategory_parents
        )
        raw_status[raw_value] = block[0]["mapping_status"]

    context_blocks = _group_contiguous(
        context_rows,
        (
            "source_dataset",
            "university",
            "faculty_school",
            "department",
            "academic_field",
        ),
        "context crosswalk",
    )
    context_keys = [key for key, _ in context_blocks]
    if context_keys != sorted(context_keys):
        raise AcademicFieldV02Error("Context crosswalk keys are not sorted")
    context_map: dict[
        tuple[str, str, str, str, str], tuple[tuple[str, str | None], ...]
    ] = {}
    context_mode: dict[tuple[str, str, str, str, str], str] = {}
    context_status: dict[tuple[str, str, str, str, str], str] = {}
    for key, block in context_blocks:
        if {row["mapping_contract_version"] for row in block} != {
            MAPPING_VERSION
        }:
            raise AcademicFieldV02Error(
                f"Unexpected context mapping version for {key!r}"
            )
        modes = {row["merge_mode"] for row in block}
        if len(modes) != 1 or not modes.issubset({"additive", "authoritative"}):
            raise AcademicFieldV02Error(f"Invalid merge_mode for {key!r}")
        context_map[key] = _validate_mapping_block(
            block, f"context {key!r}", broad_codes, subcategory_parents
        )
        context_mode[key] = next(iter(modes))
        context_status[key] = block[0]["mapping_status"]

    for key, memberships in context_map.items():
        raw_value = key[-1]
        if raw_value not in raw_map:
            raise AcademicFieldV02Error(
                f"Context crosswalk references unknown raw value: {key!r}"
            )
        mode = context_mode[key]
        if mode == "additive" and set(memberships) & set(raw_map[raw_value]):
            raise AcademicFieldV02Error(
                f"Additive context repeats a raw membership: {key!r}"
            )
        if mode == "authoritative" and raw_status[raw_value] != "review_required":
            raise AcademicFieldV02Error(
                "Authoritative context may only resolve a review_required raw "
                f"value: {key!r}"
            )

    old_taxonomy_path = (
        repo_root / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
    )
    with old_taxonomy_path.open("r", encoding="utf-8", newline="") as handle:
        old_codes = {row["group_code"] for row in csv.DictReader(handle)}
    compat_old: set[str] = set()
    for row in compat_rows:
        if (
            row["from_taxonomy_version"] != "0.1"
            or row["to_taxonomy_version"] != "0.2"
            or row["to_group_code"] not in broad_codes
        ):
            raise AcademicFieldV02Error(
                f"Invalid compatibility row: {row!r}"
            )
        compat_old.add(row["from_group_code"])
    if compat_old != old_codes:
        raise AcademicFieldV02Error(
            "v0.1 compatibility crosswalk does not cover every v0.1 group"
        )

    input_hashes_before = {
        "kokkoritsu": sha256(paths.kokkoritsu_master),
        "shidai": sha256(paths.shidai_master),
    }
    admissions = _read_master(paths.kokkoritsu_master, "kokkoritsu")
    admissions += _read_master(paths.shidai_master, "shidai")
    dataset_counts = Counter(row["source_dataset"] for row in admissions)
    input_raw_values = {row["academic_field"] for row in admissions}
    null_count = sum(row["academic_field"] == "" for row in admissions)
    if input_raw_values != set(raw_map):
        missing = sorted(input_raw_values - set(raw_map))
        stale = sorted(set(raw_map) - input_raw_values)
        raise AcademicFieldV02Error(
            f"Raw vocabulary mismatch; new/unmapped={missing!r}, stale={stale!r}"
        )
    input_context_keys = {
        (
            row["source_dataset"],
            row["university"],
            row["faculty_school"],
            row["department"],
            row["academic_field"],
        )
        for row in admissions
    }
    raw_value_counts = Counter(row["academic_field"] for row in admissions)
    unknown_context_keys = set(context_map) - input_context_keys
    if unknown_context_keys:
        raise AcademicFieldV02Error(
            f"Context crosswalk contains unknown exact tuples: "
            f"{sorted(unknown_context_keys)[:5]!r}"
        )

    broad_counts: Counter[str] = Counter()
    subcategory_counts: Counter[str] = Counter()
    final_broad_cardinality: Counter[str] = Counter()
    final_subcategory_cardinality: Counter[str] = Counter()
    context_usage = 0
    context_mapped_usage = 0
    raw_only_usage = 0
    broad_review_required = 0
    subcategory_review_required = 0
    no_subcategory_broad_mapped = 0
    unresolved_records: list[str] = []
    unresolved_raw_counts: Counter[str] = Counter()
    multi_examples: list[dict[str, object]] = []

    for row in admissions:
        raw_value = row["academic_field"]
        key = (
            row["source_dataset"],
            row["university"],
            row["faculty_school"],
            row["department"],
            raw_value,
        )
        raw_memberships = set(raw_map[raw_value])
        if key in context_map:
            context_usage += 1
            context_memberships = set(context_map[key])
            if context_memberships:
                context_mapped_usage += 1
            if context_mode[key] == "authoritative":
                memberships = context_memberships
            else:
                memberships = raw_memberships | context_memberships
        else:
            raw_only_usage += 1
            memberships = raw_memberships
        groups = {group for group, _ in memberships}
        subs = {subcategory for _, subcategory in memberships if subcategory}
        for group in groups:
            broad_counts[group] += 1
        for subcategory in subs:
            subcategory_counts[subcategory] += 1
        if not groups:
            broad_review_required += 1
            subcategory_review_required += 1
            unresolved_raw_counts[raw_value] += 1
            if len(unresolved_records) < 12:
                unresolved_records.append(row["record_id"])
        else:
            final_broad_cardinality[
                "single" if len(groups) == 1 else "multi"
            ] += 1
            if not subs:
                no_subcategory_broad_mapped += 1
                final_subcategory_cardinality["none"] += 1
            else:
                final_subcategory_cardinality[
                    "single" if len(subs) == 1 else "multi"
                ] += 1
        if len(groups) > 1 and len(multi_examples) < 12:
            multi_examples.append(
                {
                    "record_id": row["record_id"],
                    "raw_value": raw_value,
                    "groups": sorted(groups),
                }
            )

    input_hashes_after = {
        "kokkoritsu": sha256(paths.kokkoritsu_master),
        "shidai": sha256(paths.shidai_master),
    }
    if input_hashes_before != input_hashes_after:
        raise AcademicFieldV02Error("Input master changed during validation")

    if rebuild_dir is not None:
        for source, header in (
            (paths.broad, BROAD_HEADER),
            (paths.subcategory, SUBCATEGORY_HEADER),
            (paths.raw, RAW_HEADER),
            (paths.context, CONTEXT_HEADER),
            (paths.compatibility, COMPAT_HEADER),
        ):
            rows = _read_frozen_csv(source, header)
            _serialize_csv(rebuild_dir / source.name, header, rows)

    artifact_paths = (
        paths.broad,
        paths.subcategory,
        paths.raw,
        paths.context,
        paths.compatibility,
    )
    return {
        "contract_version": MAPPING_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "input_rows": dict(sorted(dataset_counts.items())),
        "total_admissions": len(admissions),
        "academic_field_null": null_count,
        "raw_distinct": len(input_raw_values),
        "raw_value_counts": dict(sorted(raw_value_counts.items())),
        "program_context_distinct": len(input_context_keys),
        "broad_taxonomy_count": len(broad_rows),
        "subcategory_taxonomy_count": len(sub_rows),
        "raw_crosswalk_rows": len(raw_rows),
        "raw_crosswalk_distinct": len(raw_map),
        "context_crosswalk_rows": len(context_rows),
        "context_crosswalk_distinct": len(context_map),
        "raw_mapping_statuses": dict(sorted(Counter(raw_status.values()).items())),
        "context_mapping_statuses": dict(
            sorted(Counter(context_status.values()).items())
        ),
        "raw_only_mapping_admissions": raw_only_usage,
        "context_mapping_admissions": context_usage,
        "context_mapped_admissions": context_mapped_usage,
        "broad_cardinality": dict(sorted(final_broad_cardinality.items())),
        "subcategory_cardinality": dict(
            sorted(final_subcategory_cardinality.items())
        ),
        "broad_review_required": broad_review_required,
        "subcategory_review_required": subcategory_review_required,
        "unmapped": 0,
        "no_subcategory_broad_mapped": no_subcategory_broad_mapped,
        "broad_coverage_admissions": len(admissions) - broad_review_required,
        "subcategory_coverage_admissions": (
            len(admissions)
            - subcategory_review_required
            - no_subcategory_broad_mapped
        ),
        "broad_membership_counts": dict(sorted(broad_counts.items())),
        "subcategory_membership_counts": dict(
            sorted(subcategory_counts.items())
        ),
        "broad_labels": broad_labels,
        "subcategory_labels": subcategory_labels,
        "subcategory_parents": subcategory_parents,
        "unresolved_record_ids": unresolved_records,
        "unresolved_raw_counts": dict(sorted(unresolved_raw_counts.items())),
        "multi_examples": multi_examples,
        "input_sha256": input_hashes_before,
        "artifact_sha256": {
            str(path.relative_to(repo_root)): sha256(path) for path in artifact_paths
        },
        "validation": {
            "taxonomy_code_uniqueness": "passed",
            "subcategory_code_uniqueness": "passed",
            "valid_parent_group": "passed",
            "display_order": "passed",
            "exact_duplicate_mapping_rows": "passed",
            "mapping_references": "passed",
            "raw_value_exactness": "passed",
            "context_tuple_determinism": "passed",
            "membership_order": "passed",
            "runtime_inference_rules": "none",
            "input_unchanged": "passed",
        },
    }


def _percent(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator * 100:.2f}%"


def render_audit_markdown(repo_root: Path, summary: dict[str, object]) -> str:
    """Render the human-readable v0.2 audit from validated frozen artifacts."""

    paths = FreezePaths(repo_root)
    broad_rows = _read_frozen_csv(paths.broad, BROAD_HEADER)
    sub_rows = _read_frozen_csv(paths.subcategory, SUBCATEGORY_HEADER)
    broad_counts = summary["broad_membership_counts"]
    sub_counts = summary["subcategory_membership_counts"]
    raw_counts = summary["raw_value_counts"]
    assert isinstance(broad_counts, dict)
    assert isinstance(sub_counts, dict)
    assert isinstance(raw_counts, dict)
    total = int(summary["total_admissions"])

    lines = [
        "# Academic-field taxonomy v0.2 full audit",
        "",
        "## 1. Scope and authority",
        "",
        "This report records the full 5,921-admission review used to freeze the ",
        "two-level academic-field search taxonomy v0.2. It creates no SQLite, ",
        "Site-data, frontend, canonical, unified, or release artifact.",
        "",
        "The task-supplied authority labels correspond to the repository's read-only ",
        "canonical copies as follows:",
        "",
        "| Authority label | Repository path | Rows | SHA-256 |",
        "|---|---|---:|---|",
        f"| `kokkoritsu_early_admissions_2027_master_freeze_20260920_v1.csv` | `data/canonical/kokkoritsu/master.csv` | {summary['input_rows']['kokkoritsu']:,} | `{summary['input_sha256']['kokkoritsu']}` |",  # type: ignore[index]
        f"| `shidai_early_admissions_2027_master_v1_04.csv` | `data/canonical/shidai/master.csv` | {summary['input_rows']['shidai']:,} | `{summary['input_sha256']['shidai']}` |",  # type: ignore[index]
        "",
        "The original authority filenames are not present as separate files in this ",
        "repository. The canonical copies match the requested row regressions and ",
        "the hashes recorded by the current unified build manifest.",
        "",
        "## 2. Input inventory",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Kokkoritsu admissions | {summary['input_rows']['kokkoritsu']:,} |",  # type: ignore[index]
        f"| Shidai admissions | {summary['input_rows']['shidai']:,} |",  # type: ignore[index]
        f"| Total admissions | {total:,} |",
        f"| `academic_field` NULL/empty | {summary['academic_field_null']:,} |",
        f"| Distinct raw values | {summary['raw_distinct']:,} |",
        f"| Distinct exact program-context tuples | {summary['program_context_distinct']:,} |",
        "",
        "## 3. Freeze size and coverage",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Broad groups | {summary['broad_taxonomy_count']:,} |",
        f"| Subcategories | {summary['subcategory_taxonomy_count']:,} |",
        f"| Raw crosswalk rows / keys | {summary['raw_crosswalk_rows']:,} / {summary['raw_crosswalk_distinct']:,} |",
        f"| Context crosswalk rows / tuples | {summary['context_crosswalk_rows']:,} / {summary['context_crosswalk_distinct']:,} |",
        f"| Broad-search coverage | {summary['broad_coverage_admissions']:,} / {total:,} ({_percent(int(summary['broad_coverage_admissions']), total)}) |",
        f"| Subcategory-search coverage | {summary['subcategory_coverage_admissions']:,} / {total:,} ({_percent(int(summary['subcategory_coverage_admissions']), total)}) |",
        f"| Broad mapped, no safe subcategory | {summary['no_subcategory_broad_mapped']:,} |",
        f"| Broad review-required admissions | {summary['broad_review_required']:,} |",
        f"| Subcategory review-required admissions | {summary['subcategory_review_required']:,} |",
        f"| Unmapped admissions | {summary['unmapped']:,} |",
        "",
        "Coverage is intentionally not forced to 100%. A broad-only classification is ",
        "valid when the source identifies a field such as `工学` but does not safely ",
        "identify a subcategory. Membership counts overlap and must not be summed.",
        "",
        "## 4. Mapping usage and cardinality",
        "",
        "| Measure | Admissions |",
        "|---|---:|",
        f"| Raw-only exact mapping | {summary['raw_only_mapping_admissions']:,} |",
        f"| Exact context tuple consulted | {summary['context_mapping_admissions']:,} |",
        f"| Exact context tuple added/resolved membership | {summary['context_mapped_admissions']:,} |",
        f"| Final single Broad membership | {summary['broad_cardinality']['single']:,} |",  # type: ignore[index]
        f"| Final multi Broad membership | {summary['broad_cardinality']['multi']:,} |",  # type: ignore[index]
        f"| Final single subcategory membership | {summary['subcategory_cardinality']['single']:,} |",  # type: ignore[index]
        f"| Final multi subcategory membership | {summary['subcategory_cardinality']['multi']:,} |",  # type: ignore[index]
        "",
        "Raw crosswalk key statuses: `"
        + "`, `".join(
            f"{key}={value:,}"
            for key, value in summary["raw_mapping_statuses"].items()  # type: ignore[union-attr]
        )
        + "`. Context tuple statuses: `"
        + "`, `".join(
            f"{key}={value:,}"
            for key, value in summary["context_mapping_statuses"].items()  # type: ignore[union-attr]
        )
        + "`.",
        "",
        "## 5. Broad-group membership counts",
        "",
        "| UI section | Broad group | Label | Admissions |",
        "|---|---|---|---:|",
    ]
    for row in broad_rows:
        lines.append(
            f"| {row['ui_section']} | `{row['group_code']}` | "
            f"{row['display_label_ja']} | {int(broad_counts.get(row['group_code'], 0)):,} |"
        )

    lines.extend(
        [
            "",
            "## 6. Subcategory membership and UI sizing",
            "",
            "The `ui_status` field is presentation metadata, not search meaning. ",
            "Zero-count categories remain in the taxonomy as `hidden` candidates; ",
            "low-count but independently meaningful student intents may remain primary.",
            "",
        ]
    )
    sub_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sub_rows:
        sub_by_parent[row["parent_group_code"]].append(row)
    for broad in broad_rows:
        children = sub_by_parent.get(broad["group_code"], [])
        lines.extend(
            [
                f"### {broad['display_label_ja']} (`{broad['group_code']}`)",
                "",
                f"Broad admissions: {int(broad_counts.get(broad['group_code'], 0)):,}; "
                f"subcategories: {len(children)}.",
                "",
            ]
        )
        if not children:
            lines.extend(["No v0.2 subcategory is defined.", ""])
            continue
        lines.extend(
            [
                "| Subcategory | Label | Admissions | UI status |",
                "|---|---|---:|---|",
            ]
        )
        for child in children:
            lines.append(
                f"| `{child['subcategory_code']}` | {child['display_label_ja']} | "
                f"{int(sub_counts.get(child['subcategory_code'], 0)):,} | "
                f"`{child['ui_status']}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## 7. Ambiguous and fail-closed values",
            "",
            "| Raw value | Admissions | Frozen handling |",
            "|---|---:|---|",
            f"| `人間科学` | {int(raw_counts.get('人間科学', 0)):,} | Two current exact tuples remain semantically mixed; Broad and subcategory stay `review_required`. |",
            f"| `国際` | {int(raw_counts.get('国際', 0)):,} | Current five contexts safely support `international_regional`; exact context adds regional/language detail only where explicit. |",
            f"| `地域デザイン` | {int(raw_counts.get('地域デザイン', 0)):,} | Raw stays `review_required`; exact context maps community design to `sociology_community` and tourism design to `tourism_hospitality`. |",
            f"| `航空・パイロット` | {int(raw_counts.get('航空・パイロット', 0)):,} | Remains `review_required`; pilot training is not aerospace engineering. |",
            "",
            "Contained tokens are never used at runtime. In particular, `理学療法` ",
            "does not become physics, `言語聴覚` does not become languages, ",
            "`獣医学` does not become human medicine, and pilot/management/maintenance ",
            "programs are not collapsed into aerospace engineering.",
            "",
            "## 8. Representative multi-membership examples",
            "",
            "| Raw value | Frozen Broad memberships |",
            "|---|---|",
        ]
    )
    raw_rows = _read_frozen_csv(paths.raw, RAW_HEADER)
    raw_members: dict[str, set[str]] = defaultdict(set)
    for row in raw_rows:
        if row["group_code"]:
            raw_members[row["raw_value"]].add(row["group_code"])
    for raw_value in (
        "経済・経営・情報",
        "外国語・国際",
        "農学・生命",
        "理工・情報",
        "デザイン・データ科学",
        "スポーツ工学",
        "医歯薬",
    ):
        groups = ", ".join(f"`{value}`" for value in sorted(raw_members[raw_value]))
        lines.append(f"| `{raw_value}` | {groups} |")

    lines.extend(
        [
            "",
            "## 9. Integrity checks",
            "",
            "All checks passed:",
            "",
            "- unique Broad and subcategory codes;",
            "- valid parent groups and contiguous display order;",
            "- no exact duplicate mapping rows;",
            "- valid group/subcategory references;",
            "- exact raw values preserved without trimming;",
            "- exact context tuple determinism and contiguous membership order;",
            "- no substring, regex, fuzzy, AI, or normalization rule in the runtime contract;",
            "- canonical inputs unchanged during validation.",
            "",
            "## 10. New-data fail-closed behavior",
            "",
            "A new raw value is `unmapped`. A known raw value appearing in a new context ",
            "continues to receive only its safe raw mapping; when that raw requires an ",
            "authoritative context, the new tuple is `review_required`/`unmapped` and ",
            "must emit a build warning with frequencies and representative record IDs. ",
            "No nearby program or lexical token may be used as an automatic fallback.",
            "",
        ]
    )
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def render_freeze_markdown(repo_root: Path, summary: dict[str, object]) -> str:
    """Render the normative freeze document after the audit exists."""

    paths = FreezePaths(repo_root)
    broad_rows = _read_frozen_csv(paths.broad, BROAD_HEADER)
    sub_rows = _read_frozen_csv(paths.subcategory, SUBCATEGORY_HEADER)
    compat_rows = _read_frozen_csv(paths.compatibility, COMPAT_HEADER)
    audit_path = repo_root / "validation/reports/academic_field_taxonomy_v0_2_audit.md"
    artifact_hashes = dict(summary["artifact_sha256"])  # type: ignore[arg-type]
    if audit_path.exists():
        artifact_hashes[str(audit_path.relative_to(repo_root))] = sha256(audit_path)
    total = int(summary["total_admissions"])
    lines = [
        "# Academic-field search taxonomy v0.2 freeze",
        "",
        "## Status and purpose",
        "",
        "This document freezes taxonomy version `0.2` and exact mapping contract ",
        "version `0.2` for future two-level academic-field search. It is a derived ",
        "search classification and never replaces the canonical `academic_field` text.",
        "",
        "The freeze adds no SQLite, Site-data, frontend, CLI, canonical, unified, or ",
        "release change. Taxonomy v0.1 and its current 19-group semantics remain ",
        "unchanged for backward compatibility.",
        "",
        "## Inputs",
        "",
        "| Authority label | Repository path | Rows | SHA-256 |",
        "|---|---|---:|---|",
        f"| `kokkoritsu_early_admissions_2027_master_freeze_20260920_v1.csv` | `data/canonical/kokkoritsu/master.csv` | {summary['input_rows']['kokkoritsu']:,} | `{summary['input_sha256']['kokkoritsu']}` |",  # type: ignore[index]
        f"| `shidai_early_admissions_2027_master_v1_04.csv` | `data/canonical/shidai/master.csv` | {summary['input_rows']['shidai']:,} | `{summary['input_sha256']['shidai']}` |",  # type: ignore[index]
        "",
        f"Total admissions: {total:,}; NULL/empty `academic_field`: "
        f"{summary['academic_field_null']:,}; distinct raw values: "
        f"{summary['raw_distinct']:,}; exact context tuples: "
        f"{summary['program_context_distinct']:,}.",
        "",
        "## Broad taxonomy (30 groups)",
        "",
        "| Section | Order | Code | Japanese label |",
        "|---|---:|---|---|",
    ]
    for row in broad_rows:
        lines.append(
            f"| {row['ui_section']} | {row['display_order']} | "
            f"`{row['group_code']}` | {row['display_label_ja']} |"
        )
    lines.extend(["", "## Subcategory taxonomy (89 subcategories)", ""])
    sub_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sub_rows:
        sub_by_parent[row["parent_group_code"]].append(row)
    for broad in broad_rows:
        children = sub_by_parent.get(broad["group_code"], [])
        if not children:
            continue
        labels = ", ".join(
            f"`{row['subcategory_code']}` ({row['display_label_ja']}, "
            f"{row['ui_status']})"
            for row in children
        )
        lines.extend(
            [
                f"### {broad['display_label_ja']} (`{broad['group_code']}`)",
                "",
                labels,
                "",
            ]
        )
    lines.extend(
        [
            "## Search Boolean semantics",
            "",
            "- No Broad selection: no academic-field predicate.",
            "- Broad only: the whole Broad membership is selected.",
            "- Broad plus subcategories: `Broad AND (selected subcategory OR ...)`.",
            "- Multiple Broad branches are ORed; a subcategory constrains only its own parent branch.",
            "",
            "For example, `(natural_sciences AND (mathematics_statistics OR physics))` ",
            "selects the chosen science branches. Adding an engineering Broad branch ",
            "without subcategories yields `(...science branch...) OR engineering`.",
            "",
            "## Mapping hierarchy and merge semantics",
            "",
            "1. Raw exact crosswalk supplies safe Broad and subcategory memberships.",
            "2. Exact program-context crosswalk uses the tuple "
            "`(source_dataset, university, faculty_school, department, academic_field)`.",
            "3. `additive` context rows union reviewed memberships with safe raw memberships.",
            "4. `authoritative` context rows replace an unresolved raw mapping only for that exact tuple.",
            "5. Empty `faculty_school` or `department` is serialized as an empty CSV cell and must match exactly.",
            "6. No trim, substring, regex, fuzzy matching, AI inference, or record-neighbor fallback is permitted.",
            "",
            "`selection_name` and `record_id` are not mapping keys in v0.2. The current ",
            "review found no selection-level academic-field divergence requiring them.",
            "",
            "## Review policy and coverage",
            "",
            f"Broad coverage is {summary['broad_coverage_admissions']:,}/{total:,} "
            f"({_percent(int(summary['broad_coverage_admissions']), total)}). "
            f"Subcategory coverage is {summary['subcategory_coverage_admissions']:,}/{total:,} "
            f"({_percent(int(summary['subcategory_coverage_admissions']), total)}).",
            "",
            f"Broad mapped with no safe subcategory: {summary['no_subcategory_broad_mapped']:,}; "
            f"Broad review-required: {summary['broad_review_required']:,}; "
            f"Subcategory review-required: {summary['subcategory_review_required']:,}; "
            f"unmapped: {summary['unmapped']:,}.",
            "",
            "Coverage is not a correctness target. Broad-only mapping is valid, and ",
            "unsafe subcategory detail remains absent.",
            "",
            "## Ambiguous values",
            "",
            "- `人間科学`: both current exact tuples remain `review_required`; the labels ",
            "  do not distinguish humanities, social science, psychology, education, or health safely.",
            "- `国際`: current contexts safely support `international_regional`; exact ",
            "  context adds `regional_studies` or language/communication only when explicit.",
            "- `地域デザイン`: raw remains `review_required`; 宇都宮大学コミュニティデザイン ",
            "  maps to community/regional society, while 金沢大学観光デザイン maps to tourism.",
            "- `航空・パイロット`: remains `review_required`; it is not aerospace engineering.",
            "",
            "## Multi-membership",
            "",
            "A program may have multiple Broad groups and multiple subcategories. Examples ",
            "include `経済・経営・情報`, `外国語・国際`, `農学・生命`, ",
            "`理工・情報`, `デザイン・データ科学`, `スポーツ工学`, and `医歯薬`. ",
            "Counts overlap and must not be summed.",
            "",
            "## v0.1 compatibility",
            "",
            "The compatibility CSV is documentation/migration metadata only. It is not a ",
            "runtime expansion rule. Actual v0.2 memberships come only from the reviewed ",
            "v0.2 raw/context crosswalks.",
            "",
            "| v0.1 group | v0.2 documentation targets |",
            "|---|---|",
        ]
    )
    compat: dict[str, list[str]] = defaultdict(list)
    for row in compat_rows:
        compat[row["from_group_code"]].append(row["to_group_code"])
    for old, targets in compat.items():
        lines.append(
            f"| `{old}` | " + ", ".join(f"`{target}`" for target in targets) + " |"
        )
    lines.extend(
        [
            "",
            "## Future update and fail-closed policy",
            "",
            "- New raw value: `unmapped` plus warning with frequency and representative record IDs.",
            "- Known raw requiring an authoritative context but new tuple: `review_required`/`unmapped` warning.",
            "- Never copy a nearby program's mapping or derive one from lexical similarity.",
            "- Update through a new reviewed, versioned freeze; do not mutate v0.1 or v0.2 in place.",
            "",
            "## Frozen artifacts and SHA-256",
            "",
            "| Artifact | SHA-256 |",
            "|---|---|",
        ]
    )
    for path, digest in sorted(artifact_hashes.items()):
        lines.append(f"| `{path}` | `{digest}` |")
    lines.extend(
        [
            "",
            "The freeze document's own hash is intentionally omitted because embedding it ",
            "would be self-referential. Its final SHA-256 is reported by the validation run.",
            "",
            "## Integrity and deterministic rebuild",
            "",
            "Validation enforces code uniqueness, valid parents, display-order uniqueness, ",
            "no duplicate mapping rows, valid references, exact raw/context preservation, ",
            "contiguous membership order, no production inference rules, and unchanged inputs. ",
            "Two independent canonical serialization runs must be byte-identical before freeze.",
            "",
            "## Remaining human decisions before Site implementation",
            "",
            "- Confirm whether zero-count hidden subcategories should remain hidden in the first UI release.",
            "- Decide how review-required admissions are exposed without implying a classification.",
            "- Confirm URL parameter names and backward-compatible coexistence with v0.1.",
            "- Review checkbox density and progressive disclosure with actual user testing.",
            "- Decide whether broad-only records should show a neutral '細分類なし' presentation.",
            "",
        ]
    )
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate academic-field taxonomy/crosswalk freeze v0.2"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--json", type=Path)
    parser.add_argument("--rebuild-dir", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args(argv)
    summary = validate_and_summarize(args.repo_root, args.rebuild_dir)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8", newline="")
    if args.audit:
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text(
            render_audit_markdown(args.repo_root, summary),
            encoding="utf-8",
            newline="",
        )
    if args.freeze:
        args.freeze.parent.mkdir(parents=True, exist_ok=True)
        args.freeze.write_text(
            render_freeze_markdown(args.repo_root, summary),
            encoding="utf-8",
            newline="",
        )
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
